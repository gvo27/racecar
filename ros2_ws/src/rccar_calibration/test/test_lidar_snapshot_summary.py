import math

from rccar_calibration.lidar_snapshot_summary import (
    build_summary, diag_summary, format_summary, imu_summary, json_safe, map_stats,
    scan_map_agreement, scan_stats, snapshot_dirname, topic_stats)

META = {'width': 4, 'height': 4, 'resolution': 0.5, 'origin_x': 0.0, 'origin_y': 0.0,
        'origin_yaw': 0.0}
# occupied wall on the bottom row (grid row 0), rest free, one unknown
DATA = [100] * 4 + [0] * 11 + [-1]


def test_scan_stats_invalid_beams():
    scan = {'ranges': [1.0, 3.0, math.inf, math.nan, 0.01, 99.0],
            'range_min': 0.1, 'range_max': 10.0, 'angle_increment': math.radians(1)}
    s = scan_stats(scan)
    assert s['beams'] == 6
    assert abs(s['finite_fraction'] - 2 / 6) < 1e-9
    assert (s['min_range'], s['median_range'], s['max_range']) == (1.0, 2.0, 3.0)
    assert abs(s['angle_span_deg'] - 5.0) < 1e-9


def test_scan_stats_none_valid():
    s = scan_stats({'ranges': [math.inf], 'range_min': 0.1, 'range_max': 10.0,
                    'angle_increment': 0.1})
    assert s['min_range'] is None and s['median_range'] is None
    assert s['finite_fraction'] == 0.0


def test_map_stats():
    s = map_stats(META, DATA)
    assert (s['unknown'], s['free'], s['occupied']) == (1, 11, 4)
    assert abs(s['known_area_m2'] - 15 * 0.25) < 1e-9


def test_agreement():
    on_wall = [(0.25, 0.25), (1.25, 0.25), (1.25, 0.6)]
    assert scan_map_agreement(on_wall, META, DATA) == 1.0
    assert scan_map_agreement([(1.25, 1.75)], META, DATA) == 0.0
    assert scan_map_agreement([(1.25, 0.25), (1.25, 1.75)], META, DATA) == 0.5
    assert scan_map_agreement([(50.0, 50.0)], META, DATA) == 0.0
    assert scan_map_agreement([], META, DATA) is None
    assert scan_map_agreement([(0.25, 0.25)], None, None) is None


def test_imu_summary():
    imu = {'orientation': [0.0, 0.0, math.sin(math.pi / 4), math.cos(math.pi / 4)],
           'orientation_covariance0': 0.01, 'angular_velocity_covariance0': -1.0,
           'linear_acceleration_covariance0': -1.0}
    s = imu_summary(imu)
    assert abs(s['yaw_deg'] - 90.0) < 1e-6
    assert s['provided'] == {'orientation': True, 'angular_velocity': False,
                             'linear_acceleration': False}
    assert imu_summary(None) is None


def test_diag_summary():
    st = [{'name': 'other', 'level': 0, 'message': '', 'values': {}},
          {'name': 'mapper_driver: link', 'level': 2, 'message': 'lost',
           'values': {'a': '1'}}]
    d = diag_summary(st)
    assert d['level'] == 'ERROR' and d['message'] == 'lost' and d['values'] == {'a': '1'}
    assert diag_summary(st[:1]) is None
    assert diag_summary(None) is None
    for lvl, name in enumerate(('OK', 'WARN', 'ERROR', 'STALE')):
        assert diag_summary([dict(st[1], level=lvl)])['level'] == name


def test_topic_stats():
    s = topic_stats({'/a': 11, '/b': 1, '/c': 0}, {'/a': (0.0, 1.0), '/b': (2.0, 2.0)}, 4.0)
    assert abs(s['/a']['rate_hz'] - 10.0) < 1e-9 and s['/a']['age_s'] == 3.0
    assert s['/b']['rate_hz'] is None and s['/b']['age_s'] == 2.0
    assert s['/c']['age_s'] is None


def test_dirname():
    assert snapshot_dirname(0) == 'lidar_snapshot_19700101T000000Z'
    assert snapshot_dirname(1700000000) == 'lidar_snapshot_20231114T221320Z'


def test_format_summary_missing_and_legend():
    text = format_summary(build_summary(None, None, None, None, None, None, {}, {}, 0.0))
    assert 'n/a' in text
    assert 'red = current scan endpoints' in text
    assert '+X right, +Y up (map frame)' in text
    assert 'scan_angle_sign' in text


def test_build_summary_full():
    scan = {'angle_min': 0.0, 'angle_increment': 0.1, 'ranges': [0.25],
            'range_min': 0.1, 'range_max': 10.0}
    pose = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
    s = build_summary(scan, pose, None, META, DATA, None, {'/s': 1}, {'/s': (1.0, 1.0)},
                      2.0, 0)
    assert s['agreement'] == 1.0
    assert s['time_utc'] == '19700101T000000Z'
    assert 'agreement: 1.00' in format_summary(s)


class _NumpyLike:
    """Stands in for a numpy scalar (rclpy array fields hand those out)."""

    def __init__(self, v):
        self.v = v

    def item(self):
        return self.v


def test_json_safe_converts_numpy_like_scalars():
    import json
    out = json_safe({'flag': _NumpyLike(True), 'x': [_NumpyLike(float('inf')), 1.5]})
    assert json.loads(json.dumps(out)) == {'flag': True, 'x': [None, 1.5]}
