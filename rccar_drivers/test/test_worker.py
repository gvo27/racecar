"""MapperWorker against the fake Mapper: data flow, errors, reconnect (no rclpy)."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_mapper import FakeMapper  # noqa: E402,I100,I201
import pytest  # noqa: E402,I100,I201
from rccar_drivers.slamtec.protocol import MapperClient  # noqa: E402
from rccar_drivers.slamtec.worker import MapperWorker  # noqa: E402

PERIODS = {'scan': 0.02, 'imu': 0.02, 'pose': 0.02, 'map': 0.05, 'health': 0.05}


class Sink:
    def __init__(self):
        self.scans, self.imus, self.poses, self.maps = [], [], [], []
        self.lock = threading.Lock()

    def on_scan(self, v):
        self.scans.append(v)

    def on_imu(self, v):
        self.imus.append(v)

    def on_pose(self, v):
        self.poses.append(v)

    def on_map(self, v):
        self.maps.append(v)


@pytest.fixture
def server():
    s = FakeMapper()
    yield s
    s.stop()


def wait_for(pred, timeout=5.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return False


def make(server, **kw):
    sink = Sink()
    client = MapperClient('127.0.0.1', server.port, timeout_s=0.3)
    w = MapperWorker(client, sink, PERIODS, reconnect_max_s=0.4, **kw)
    return w, sink


def lost(logs):
    return [t for lvl, t in logs if 'link lost' in t]


def test_data_flows_and_health(server):
    w, sink = make(server)
    w.start()
    try:
        assert wait_for(lambda: sink.scans and sink.imus and sink.poses and sink.maps)
        assert wait_for(lambda: w.snapshot()[2] is not None)
        up, ver, health, temp, age = w.snapshot()
        assert up and ver == 'fake-1.0' and temp == 40.0 and age is not None
        assert sink.maps[0].width == 4
    finally:
        w.stop()
    assert not w.snapshot()[0]


def test_requests_never_overlap(server):
    w, sink = make(server)
    w.start()
    try:
        assert wait_for(lambda: len(sink.scans) > 5)
    finally:
        w.stop()
    ids = [r['request_id'] for r in server.requests]
    assert ids == sorted(ids)  # single socket, strictly sequential ids


def test_empty_known_area_skips_map(server):
    server.results['getknownarea'] = {'min_x': 0.0, 'min_y': 0.0,
                                      'max_x': 0.0, 'max_y': 0.0}
    w, sink = make(server)
    w.start()
    try:
        assert wait_for(lambda: len(sink.scans) > 3)
    finally:
        w.stop()
    assert sink.maps == []
    assert not any(r['command'] == 'getmapdata' for r in server.requests)


def test_reconnects_after_drop(server):
    logs = []
    w, sink = make(server, log=lambda lvl, t: logs.append((lvl, t)))
    w.start()
    try:
        assert wait_for(lambda: len(sink.scans) > 2)
        server.drop_connections()
        assert wait_for(lambda: lost(logs), 3.0)
        n = len(sink.scans)
        assert wait_for(lambda: w.snapshot()[0] and len(sink.scans) > n + 2, 5.0)
    finally:
        w.stop()


def test_unreachable_stays_down():
    probe = FakeMapper()
    port = probe.port
    probe.stop()
    sink = Sink()
    w = MapperWorker(MapperClient('127.0.0.1', port, timeout_s=0.3), sink, PERIODS,
                     reconnect_max_s=0.3)
    w.start()
    try:
        time.sleep(0.5)
        assert not w.snapshot()[0] and not sink.scans
    finally:
        w.stop()


def test_handler_exception_does_not_kill_thread(server):
    w, sink = make(server)
    calls = []

    def bad(v):
        calls.append(v)
        raise RuntimeError('boom')
    sink.on_scan = bad
    w.start()
    try:
        assert wait_for(lambda: len(calls) > 2)
        assert wait_for(lambda: len(sink.imus) > 2)
    finally:
        w.stop()


def test_command_error_keeps_link_up_and_scans_flowing(server):
    server.results['getmapdata'] = {'code': 5}
    logs = []
    w, sink = make(server, log=lambda lvl, t: logs.append((lvl, t)))
    w.start()
    try:
        assert wait_for(lambda: any(r['command'] == 'getmapdata' for r in server.requests))
        n = len(sink.scans)
        assert wait_for(lambda: len(sink.scans) > n + 5)
        assert w.snapshot()[0]
    finally:
        w.stop()
    assert not lost(logs)
    assert sink.maps == []
    # one connect only: the command error never closed the socket
    assert sum(1 for r in server.requests if r['command'] == 'getsdpversion') == 1
    # throttled: far fewer warnings than failed calls
    nfail = sum(1 for r in server.requests if r['command'] == 'getmapdata')
    nwarn = sum(1 for lvl, t in logs if 'getmapdata' in t)
    assert 1 <= nwarn < max(nfail, 2)


def test_connect_then_fail_cycles_respect_backoff():
    # server answers getsdpversion but every scan fails at the link level
    srv = FakeMapper()
    srv.silent = False
    orig = srv._handle

    def handle(conn, req):
        if req['command'] == 'getlaserscan':
            srv.requests.append(req)
            conn.close()
            return
        orig(conn, req)
    srv._handle = handle
    w, sink = make(srv)
    w._reconnect_max_s = 5.0
    w.start()
    try:
        time.sleep(1.5)
    finally:
        w.stop()
        srv.stop()
    connects = sum(1 for r in srv.requests if r['command'] == 'getsdpversion')
    # backoff 0.2, 0.4, 0.8, ... => at most ~5 connects in 1.5 s (a tight loop gives hundreds)
    assert 2 <= connects <= 6


def test_backoff_resets_after_first_successful_scan(server):
    w, sink = make(server)
    w._backoff = 3.0
    w.start()
    try:
        assert wait_for(lambda: sink.scans)
        assert wait_for(lambda: w._backoff == 0.2)
    finally:
        w.stop()


def test_map_skipped_when_too_large(server):
    server.results['getknownarea'] = {'min_x': 0.0, 'min_y': 0.0,
                                      'max_x': 1000.0, 'max_y': 1000.0}
    logs = []
    sink = Sink()
    client = MapperClient('127.0.0.1', server.port, timeout_s=0.3)
    w = MapperWorker(client, sink, PERIODS, reconnect_max_s=0.4, map_max_cells=1_000_000,
                     log=lambda lvl, t: logs.append((lvl, t)))
    w.start()
    try:
        assert wait_for(lambda: len(sink.scans) > 5)
        assert wait_for(lambda: any('map_max_cells' in t for _, t in logs))
    finally:
        w.stop()
    assert not any(r['command'] == 'getmapdata' for r in server.requests)
    assert sink.maps == []


def test_map_origin_falls_back_to_requested_area(server):
    res = dict(server.results['getmapdata'])
    del res['real_x'], res['real_y']
    server.results['getmapdata'] = res
    w, sink = make(server)
    w.start()
    try:
        assert wait_for(lambda: sink.maps)
    finally:
        w.stop()
    assert (sink.maps[0].origin_x, sink.maps[0].origin_y) == (-1.0, -1.0)


def test_stop_with_stuck_thread_keeps_reference_and_blocks_start(server):
    w, sink = make(server)
    gate = threading.Event()
    sink.on_scan = lambda v: gate.wait(10.0)  # worker thread stuck in the sink
    w.stop_join_timeout_s = 0.2
    logs = []
    w._log = lambda lvl, t: logs.append((lvl, t))
    assert w.start()
    try:
        assert wait_for(lambda: server.requests)
        time.sleep(0.2)
        w.stop()
        assert any(lvl == 'error' for lvl, _ in logs)
        assert w.start() is False  # old thread still alive
    finally:
        gate.set()
    assert wait_for(lambda: not w._thread.is_alive(), 3.0)
    w.stop()
    assert w.start() is True
    w.stop()


def test_scan_age_counts_from_connect_when_no_scan_yet(server):
    now = [100.0]
    w, _ = make(server, clock=lambda: now[0])
    assert w.snapshot()[4] is None  # not connected: no age
    assert w.connect_once()
    assert w.snapshot()[4] == 0.0
    now[0] += 5.0
    assert w.snapshot()[4] == 5.0  # live link, never a scan: age grows (diagnostics WARN)
    w.stop()
