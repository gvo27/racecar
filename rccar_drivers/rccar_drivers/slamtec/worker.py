"""
Single-thread Mapper IO loop (no rclpy).

The Mapper protocol is synchronous request/response over ONE socket, so every
request is issued from this one thread, never two at once. Decoded results go
to a sink object (on_scan/on_imu/on_pose/on_map methods); the ROS node's sink converts and
publishes directly from the worker thread (rclpy publish is thread-safe), so
no queue or executor hop is needed and rclpy callbacks never block on IO.

Link errors (MapperError/MapperTimeout) close the socket, mark the link down
and retry with exponential backoff capped at ``reconnect_max_s``.
"""
import threading
import time

from rccar_drivers.slamtec.protocol import (
    decode_map, Health, ImuSample, MapperError, parse_scan, Pose)

BACKOFF_START_S = 0.2


class MapperWorker:
    """Schedule scan/imu/pose/map/health requests on one thread."""

    def __init__(self, client, sink, periods, reconnect_max_s=5.0,
                 log=None, clock=time.monotonic):
        """
        Create the worker.

        periods: dict with keys scan, imu, pose, map, health -> period in s.
        log: callable(level, text) with level in debug/info/warn/error.
        """
        self._client = client
        self._sink = sink
        self._periods = dict(periods)
        self._reconnect_max_s = reconnect_max_s
        self._log = log or (lambda level, text: None)
        self._clock = clock
        self._stop_evt = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._link_up = False
        self._sdp_version = ''
        self._health = None
        self._temp_c = None
        self._last_scan = None
        self._backoff = BACKOFF_START_S
        self._due = {}
        self._handlers = {
            'scan': self._do_scan, 'imu': self._do_imu, 'pose': self._do_pose,
            'map': self._do_map, 'health': self._do_health}

    # -- state (read from any thread) ---------------------------------------
    def snapshot(self):
        """Return (link_up, sdp_version, health, temp_c, last_scan_age_s or None)."""
        with self._lock:
            age = None if self._last_scan is None else self._clock() - self._last_scan
            return self._link_up, self._sdp_version, self._health, self._temp_c, age

    # -- control ------------------------------------------------------------
    def start(self):
        """Start the IO thread."""
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, name='mapper_io', daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the thread and close the socket."""
        self._stop_evt.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self._client.close()
        with self._lock:
            self._link_up = False

    # -- loop -----------------------------------------------------------------
    def connect_once(self):
        """Try to connect + read the SDP version; return True on success."""
        try:
            self._client.connect()
            version = self._client.call('getsdpversion').get('sdp_version', '')
        except MapperError as exc:
            self._client.close()
            self._log('warn', 'mapper connect failed: %s' % exc)
            return False
        with self._lock:
            self._link_up = True
            self._sdp_version = str(version)
        self._backoff = BACKOFF_START_S
        self._log('info', 'mapper connected, sdp version %s' % version)
        return True

    def _run(self):
        now = self._clock()
        self._due = {k: now for k in self._handlers}
        while not self._stop_evt.is_set():
            if not self._client.connected or not self._link_up:
                if not self.connect_once():
                    self._stop_evt.wait(self._backoff)
                    self._backoff = min(self._backoff * 2.0, self._reconnect_max_s)
                    continue
                now = self._clock()
                self._due = {k: now for k in self._handlers}
            name = min(self._due, key=self._due.get)
            wait = self._due[name] - self._clock()
            if wait > 0 and self._stop_evt.wait(wait):
                break
            self.step(name)

    def step(self, name):
        """Run one task now and reschedule it (also used directly by tests)."""
        try:
            self._handlers[name]()
        except MapperError as exc:
            self._client.close()
            with self._lock:
                self._link_up = False
            self._log('warn', 'mapper link lost (%s): %s' % (name, exc))
        except Exception as exc:  # sink/conversion bug must not kill the IO thread
            self._log('error', 'mapper %s handler failed: %r' % (name, exc))
        period = self._periods[name]
        self._due[name] = max(self._due.get(name, 0.0) + period, self._clock())

    # -- tasks ----------------------------------------------------------------
    def _do_scan(self):
        r = self._client.call('getlaserscan')
        points = parse_scan(r['laser_points'])
        with self._lock:
            self._last_scan = self._clock()
        self._sink.on_scan(points)

    def _do_imu(self):
        self._sink.on_imu(ImuSample.from_result(
            self._client.call('getimuinrobotcoordinate')))

    def _do_pose(self):
        self._sink.on_pose(Pose.from_result(self._client.call('getpose')))

    def _do_map(self):
        area = self._client.call(
            'getknownarea', {'type': 0, 'kind': 0, 'partially': False})
        try:
            x0, y0 = float(area['min_x']), float(area['min_y'])
            w = float(area['max_x']) - x0
            h = float(area['max_y']) - y0
        except (KeyError, TypeError, ValueError) as exc:
            raise MapperError('bad known area: %r' % (exc,)) from exc
        if w <= 0.0 or h <= 0.0:
            return
        r = self._client.call('getmapdata', {
            'area': {'x': x0, 'y': y0, 'width': w, 'height': h},
            'type': 0, 'kind': 0, 'partially': False})
        self._sink.on_map(decode_map(r))

    def _do_health(self):
        health = Health.from_result(self._client.call('getrobothealth'))
        res = self._client.call('getsystemresource')
        try:
            temp = float(res['board_temperature10']) / 10.0
        except (KeyError, TypeError, ValueError):
            temp = None
        with self._lock:
            self._health, self._temp_c = health, temp
