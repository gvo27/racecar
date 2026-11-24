"""Protocol: RLE, scan parser, map decode, client against FakeMapper."""
import base64
import json
import math
import socket
import struct

from fake_mapper import (DEFAULT_POINTS, DELIM, encode_scan, FakeMapper,
                         MAP_CELLS, rle_deflate)
import pytest

from rccar_drivers.slamtec import protocol as p


def b64(raw):
    return base64.b64encode(raw).decode().rstrip('=')


def header(n, s1=0x81, s2=0x7F):
    return b'RLE' + bytes([s1, s2]) + struct.pack('<I', n)


def test_rle_literal():
    assert p.rle_inflate(b64(header(3) + b'abc')) == b'abc'


def test_rle_run():
    assert p.rle_inflate(b64(header(5) + b'\x81\x05\x07')) == b'\x07' * 5


def test_rle_swap():
    # swap s1/s2, then 0x7f acts as the run marker
    body = b'\x81\x00\x7f' + b'\x7f\x03\x09' + b'\x81'
    assert p.rle_inflate(b64(header(4) + body)) == b'\x09\x09\x09\x81'


def test_rle_bad_header():
    with pytest.raises(p.MapperError):
        p.rle_inflate(b64(b'XYZ' + b'\x00' * 8))


def test_rle_roundtrip():
    data = bytes([0, 0, 0, 0, 0, 0x81, 1, 2, 2, 2, 2, 2, 0x81, 0x81]) * 7
    assert p.rle_inflate(rle_deflate(data)) == data


def test_parse_scan_recovers_points():
    pts = p.parse_scan(encode_scan(DEFAULT_POINTS))
    assert len(pts) == len(DEFAULT_POINTS)
    for (a, d, v), (ea, ed, ev) in zip(pts, sorted(DEFAULT_POINTS)):
        assert a == pytest.approx(ea, abs=1e-6)
        assert d == pytest.approx(ed, rel=1e-6)
        assert v == ev


def test_parse_scan_resyncs_on_stray_bytes():
    raw = struct.pack('<ffB3x', 2.0, 0.5, 1)
    raw2 = struct.pack('<ffB3x', 3.0, -0.5, 1)
    pts = p.parse_scan(rle_deflate(b'\xff\xff\xff\xff\xff' + raw + raw2))
    assert [round(a, 3) for a, _, _ in pts] == [-0.5, 0.5]


def test_decode_map():
    m = p.decode_map({'dimension_x': 4, 'dimension_y': 3, 'resolution': 0.05,
                      'real_x': -1.0, 'real_y': -2.0,
                      'map_data': rle_deflate(MAP_CELLS)})
    assert (m.width, m.height, m.origin_x, m.origin_y) == (4, 3, -1.0, -2.0)
    assert m.cells == MAP_CELLS


def test_decode_map_too_short():
    with pytest.raises(p.MapperError):
        p.decode_map({'dimension_x': 10, 'dimension_y': 10, 'resolution': 0.05,
                      'map_data': rle_deflate(MAP_CELLS)})


def test_from_result_defaults():
    assert p.Pose.from_result({}) == p.Pose(0.0, 0.0, 0.0, 0.0, 0.0)
    imu = p.ImuSample.from_result({'acc': {'x': 1.0}})
    assert imu.acc == (1.0, 0.0, 0.0) and imu.quat == (1.0, 0.0, 0.0, 0.0)
    assert p.Health.from_result({'hasLidarDisconnected': True}).has_lidar_disconnected
    h = p.Health.from_result({'has_error': True})
    assert h.has_error and not h.has_fatal and not h.has_lidar_disconnected


@pytest.fixture
def server():
    s = FakeMapper()
    yield s
    s.stop()


def client_for(srv, timeout_s=1.0):
    c = p.MapperClient('127.0.0.1', srv.port, timeout_s)
    c.connect()
    return c


def test_client_calls(server):
    c = client_for(server)
    assert c.connected
    assert c.call('getsdpversion')['sdp_version'] == 'fake-1.0'
    assert c.call('getpose')['yaw'] == 0.5
    area = c.call('getknownarea', {'type': 0, 'kind': 0, 'partially': False})
    assert area['max_x'] == 1.0
    assert server.requests[-1]['args']['kind'] == 0
    ids = [r['request_id'] for r in server.requests]
    assert ids == sorted(set(ids))
    c.close()
    assert not c.connected


def test_client_scan_and_map(server):
    c = client_for(server)
    assert len(p.parse_scan(c.call('getlaserscan')['laser_points'])) == 4
    assert p.decode_map(c.call('getmapdata')).cells == MAP_CELLS


def test_client_chunked_delivery():
    s = FakeMapper(chunk=7)
    try:
        c = client_for(s)
        assert c.call('getpose')['x'] == 1.0
        assert len(p.parse_scan(c.call('getlaserscan')['laser_points'])) == 4
    finally:
        s.stop()


def test_client_discards_stale_response():
    s = FakeMapper(stale_first=True)
    try:
        c = client_for(s)
        r = c.call('getpose')
        assert 'stale' not in r and r['x'] == 1.0
    finally:
        s.stop()


def test_client_multiple_messages_in_one_recv():
    class Sock:
        def __init__(self):
            self.sent = b''
            self.out = b''

        def settimeout(self, t):
            pass

        def sendall(self, data):
            req = json.loads(data[:-len(DELIM)])
            rid = req['request_id']
            msgs = [{'request_id': rid - 1, 'result': {'code': 1, 'old': 1}},
                    {'request_id': rid, 'result': {'code': 1, 'v': 7}},
                    {'request_id': rid + 1, 'result': {'code': 1, 'v': 8}}]
            self.out = b''.join(json.dumps(m).encode() + DELIM for m in msgs)

        def recv(self, n):
            out, self.out = self.out, b''
            return out

        def close(self):
            pass

    c = p.MapperClient('h', sock_factory=lambda addr, t: Sock())
    c.connect()
    assert c.call('x')['v'] == 7


def test_client_timeout_closes():
    s = FakeMapper()
    s.silent = True
    try:
        c = client_for(s, timeout_s=0.1)
        with pytest.raises(p.MapperTimeout):
            c.call('getpose')
        assert not c.connected
        s.silent = False
        c.connect()
        assert c.call('getpose')['x'] == 1.0
    finally:
        s.stop()


def test_client_unknown_command_error_keeps_socket(server):
    c = client_for(server)
    with pytest.raises(p.MapperCommandError):
        c.call('nonsense')
    assert c.connected


def test_client_link_drop(server):
    c = client_for(server)
    c.call('getpose')
    server.drop_connections()
    with pytest.raises(p.MapperError):
        c.call('getpose')
    assert not c.connected


def test_call_without_connect():
    with pytest.raises(p.MapperError):
        p.MapperClient('127.0.0.1', 1).call('x')


def test_connect_refused():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    with pytest.raises(p.MapperError):
        p.MapperClient('127.0.0.1', port, 0.2).connect()


def test_request_id_wraps():
    c = p.MapperClient('h')
    c._next_id = p.MAX_REQUEST_ID - 1
    assert c._new_id() == p.MAX_REQUEST_ID
    assert c._new_id() == 1
    assert math.isfinite(c._new_id())


def test_decode_map_origin_fallback():
    res = {'dimension_x': 4, 'dimension_y': 3, 'resolution': 0.05,
           'map_data': rle_deflate(bytes(12))}
    m = p.decode_map(res, origin=(-1.5, 2.5))
    assert (m.origin_x, m.origin_y) == (-1.5, 2.5)


def test_decode_map_missing_origin_without_fallback_raises():
    res = {'dimension_x': 4, 'dimension_y': 3, 'resolution': 0.05,
           'map_data': rle_deflate(bytes(12))}
    with pytest.raises(p.MapperError):
        p.decode_map(res)


def test_decode_map_real_origin_wins_over_fallback():
    res = {'dimension_x': 1, 'dimension_y': 1, 'resolution': 0.05,
           'real_x': 3.0, 'real_y': 4.0, 'map_data': rle_deflate(bytes(1))}
    m = p.decode_map(res, origin=(9.0, 9.0))
    assert (m.origin_x, m.origin_y) == (3.0, 4.0)


def test_command_error_keeps_socket_open():
    srv = FakeMapper(results={'getmapdata': {'code': 7}})
    try:
        c = p.MapperClient('127.0.0.1', srv.port, timeout_s=0.5)
        c.connect()
        with pytest.raises(p.MapperCommandError):
            c.call('getmapdata')
        assert c.connected
        assert c.call('getsdpversion')['sdp_version'] == 'fake-1.0'
        c.close()
    finally:
        srv.stop()


def test_command_error_is_a_mapper_error():
    assert issubclass(p.MapperCommandError, p.MapperError)


def test_imu_avail_parsed_sic_and_correct_spelling():
    assert p.ImuSample.from_result({'availibilityBitMap': 131}).avail == 131
    assert p.ImuSample.from_result({'availabilityBitmap': 3}).avail == 3
    assert p.ImuSample.from_result({}).avail is None
    assert p.ImuSample.from_result({'availibilityBitMap': 'x'}).avail is None
    assert p.ImuSample.from_result({'availibilityBitMap': True}).avail is None


def test_imu_bit_values_inferred_layout():
    assert p.ImuBit.QUATERNION_READY == 1
    assert p.ImuBit.CALIBRATED_ACC_READY == 2
    assert p.ImuBit.CALIBRATED_GYRO_READY == 4
    assert p.ImuBit.FUSION_6DOF_READY == 128
    assert p.ImuBit.FUSION_9DOF_READY == 256
    assert 'inferred' in p.ImuBit.__doc__


def test_imu_has_bench_bitmap_131():
    s = p.ImuSample.from_result({'availibilityBitMap': 131})
    assert s.has(p.ImuBit.QUATERNION_READY)
    assert s.has(p.ImuBit.CALIBRATED_ACC_READY)
    assert not s.has(p.ImuBit.CALIBRATED_GYRO_READY)
    assert not s.has(p.ImuBit.RAW_ACC_READY)


def test_imu_has_without_bitmap_is_legacy_all_available():
    s = p.ImuSample.from_result({})
    assert all(s.has(b) for b in p.ImuBit)
