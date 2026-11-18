"""
Single-thread Mapper IO loop (no rclpy).

The Mapper protocol is synchronous request/response over ONE socket, so every
request is issued from this one thread, never two at once. Decoded results go
to a sink object (on_scan/on_imu/on_pose/on_map methods); the ROS node's sink converts and
publishes directly from the worker thread (rclpy publish is thread-safe), so
no queue or executor hop is needed and rclpy callbacks never block on IO.

Link errors (MapperError/MapperTimeout) close the socket, mark the link down
and retry with exponential backoff capped at ``reconnect_max_s``. The backoff
is reset only by the first successful scan, so a connect-then-fail cycle keeps
backing off. A command error (nonzero result code, MapperCommandError) leaves
the link up: it is logged (throttled) and the loop continues; e.g. the map
calls fail before a map exists.
"""
import threading
import time

from rccar_drivers.slamtec.protocol import (
    decode_map, Health, ImuSample, MapperCommandError, MapperError, parse_scan, Pose)

BACKOFF_START_S = 0.2
WARN_THROTTLE_S = 10.0
DEFAULT_RESOLUTION = 0.05  # m/cell assumed until the first map reports one


class MapperWorker:
    """Schedule scan/imu/pose/map/health requests on one thread."""

    def __init__(self, client, sink, periods, reconnect_max_s=5.0,
                 log=None, clock=time.monotonic, map_max_cells=4_000_000):
        """
        Create the worker.

        periods: dict with keys scan, imu, pose, map, health -> period in s.
        log: callable(level, text) with level in debug/info/warn/error.
        map_max_cells: skip the map fetch when the known area exceeds this many cells.
        """
        self._client = client
        self._sink = sink
        self._periods = dict(periods)
        self._reconnect_max_s = reconnect_max_s
        self._log = log or (lambda level, text: None)
        self._clock = clock
        self._map_max_cells = map_max_cells
        self._map_res = DEFAULT_RESOLUTION
        self._warned = {}
        self.stop_join_timeout_s = 5.0
        self._stop_evt = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._link_up = False
        self._sdp_version = ''
        self._health = None
        self._temp_c = None
        self._last_scan = None
        self._connected_at = None
        self._backoff = BACKOFF_START_S
        self._due = {}
        self._handlers = {
            'scan': self._do_scan, 'imu': self._do_imu, 'pose': self._do_pose,
            'map': self._do_map, 'health': self._do_health}

    # -- state (read from any thread) ---------------------------------------
    def snapshot(self):
        """Return (link_up, sdp_version, health, temp_c, last_scan_age_s or None)."""
        with self._lock:
            # no scan yet on a live link: age counts from connect, so a link that never
            # delivers scans goes WARN/ERROR instead of staying OK forever
            ref = self._last_scan if self._last_scan is not None else (
                self._connected_at if self._link_up else None)
            age = None if ref is None else self._clock() - ref
            return self._link_up, self._sdp_version, self._health, self._temp_c, age

    # -- control ------------------------------------------------------------
    def start(self):
        """Start the IO thread; return False (refused) while an old one is still alive."""
        if self._thread is not None and self._thread.is_alive():
            self._log('error', 'mapper IO thread still alive; refusing to start another')
            return False
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, name='mapper_io', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop the thread and close the socket (keeps a stuck thread referenced)."""
        self._stop_evt.set()
        if self._thread is not None:
            self._thread.join(timeout=self.stop_join_timeout_s)
            if self._thread.is_alive():
                self._log('error', 'mapper IO thread did not stop within %.1f s'
                          % self.stop_join_timeout_s)
            else:
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
            self._connected_at = self._clock()
            self._sdp_version = str(version)
        self._log('info', 'mapper connected, sdp version %s' % version)
        return True

    def _run(self):
        now = self._clock()
        self._due = {k: now for k in self._handlers}
        while not self._stop_evt.is_set():
            if not self._client.connected or not self._link_up:
                if not self.connect_once():
                    self._wait_backoff()
                    continue
                now = self._clock()
                self._due = {k: now for k in self._handlers}
            name = min(self._due, key=self._due.get)
            wait = self._due[name] - self._clock()
            if wait > 0 and self._stop_evt.wait(wait):
                break
            self.step(name)
            if not self._link_up:
                self._wait_backoff()

    def _wait_backoff(self):
        self._stop_evt.wait(self._backoff)
        self._backoff = min(self._backoff * 2.0, self._reconnect_max_s)

    def _warn_throttled(self, key, text):
        now = self._clock()
        last = self._warned.get(key)
        if last is None or now - last >= WARN_THROTTLE_S:
            self._warned[key] = now
            self._log('warn', text)

    def step(self, name):
        """Run one task now and reschedule it (also used directly by tests)."""
        try:
            self._handlers[name]()
        except MapperCommandError as exc:  # device said no; link is fine
            self._warn_throttled(name, 'mapper %s: %s' % (name, exc))
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
        self._backoff = BACKOFF_START_S  # link proven by real data
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
        cells = (w / self._map_res) * (h / self._map_res)
        if cells > self._map_max_cells:
            self._warn_throttled(
                'map_size', 'known area %.0f x %.0f m = ~%.0f cells exceeds map_max_cells %d; '
                'map not fetched' % (w, h, cells, self._map_max_cells))
            return
        r = self._client.call('getmapdata', {
            'area': {'x': x0, 'y': y0, 'width': w, 'height': h},
            'type': 0, 'kind': 0, 'partially': False})
        m = decode_map(r, origin=(x0, y0))
        if m.resolution > 0.0:
            self._map_res = m.resolution
        self._sink.on_map(m)

    def _do_health(self):
        health = Health.from_result(self._client.call('getrobothealth'))
        res = self._client.call('getsystemresource')
        try:
            temp = float(res['board_temperature10']) / 10.0
        except (KeyError, TypeError, ValueError):
            temp = None
        with self._lock:
            self._health, self._temp_c = health, temp
