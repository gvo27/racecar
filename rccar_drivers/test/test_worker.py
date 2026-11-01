"""MapperWorker against the fake Mapper: data flow, errors, reconnect (no rclpy)."""
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fake_mapper import FakeMapper  # noqa: E402
from rccar_drivers.slamtec.protocol import MapperClient  # noqa: E402
from rccar_drivers.slamtec.worker import MapperWorker  # noqa: E402

PERIODS = {'scan': 0.02, 'imu': 0.02, 'pose': 0.02, 'map': 0.05, 'health': 0.05}


class Sink:
    def __init__(self):
        self.scans, self.imus, self.poses, self.maps = [], [], [], []
        self.lock = threading.Lock()

    def scan(self, v):
        self.scans.append(v)

    def imu(self, v):
        self.imus.append(v)

    def pose(self, v):
        self.poses.append(v)

    def map(self, v):
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
    sink.scan = bad
    w.start()
    try:
        assert wait_for(lambda: len(calls) > 2)
        assert wait_for(lambda: len(sink.imus) > 2)
    finally:
        w.stop()
