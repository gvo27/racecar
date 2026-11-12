"""Pure lidar IMU formatting + planar helpers."""
import json
import math

from rccar_calibration import lidar_imu_format as f


def test_quat_yaw_identity_and_90():
    assert f.quat_to_yaw(0.0, 0.0, 0.0, 1.0) == 0.0
    s = math.sqrt(0.5)
    assert abs(f.quat_to_yaw(0.0, 0.0, s, s) - math.pi / 2) < 1e-9


def test_quat_yaw_ignores_roll_pitch():
    # pure roll of 30 deg has zero yaw
    h = math.radians(30) / 2
    assert abs(f.quat_to_yaw(math.sin(h), 0.0, 0.0, math.cos(h))) < 1e-9


def test_wrap_angle():
    assert abs(f.wrap_angle(3 * math.pi / 2) + math.pi / 2) < 1e-9
    assert abs(f.wrap_angle(-3 * math.pi / 2) - math.pi / 2) < 1e-9
    assert abs(f.wrap_angle(0.5) - 0.5) < 1e-12


def test_planar_speed():
    assert f.planar_speed((0.0, 0.0, 1.0), (3.0, 4.0, 2.0)) == 5.0


def test_planar_speed_degenerate_dt():
    assert f.planar_speed((0.0, 0.0, 1.0), (3.0, 4.0, 1.0)) is None
    assert f.planar_speed((0.0, 0.0, 2.0), (3.0, 4.0, 1.0)) is None


def test_format_line_full():
    out = f.format_line(1730300000.5, 90.0, 91.2, 12.34, 0.5, 0.1, -0.2, 49.9)
    assert out.startswith('pi 1730300000.500  heading 90.0 deg')
    assert 'imu_heading 91.2 deg' in out
    assert 'yaw_rate 12.3 dps' in out
    assert 'speed 0.50 m/s' in out
    assert 'acc_long 0.10' in out
    assert 'acc_lat -0.20' in out
    assert '49.9 Hz' in out
    assert 'JUMP' not in out
    assert 'imu_gyro n/a' in out and 'imu_acc n/a' in out


def test_format_line_no_pose():
    out = f.format_line(1.0, None, None, None, None, None, None, 50.0)
    for key in ('heading', 'imu_heading', 'yaw_rate', 'speed', 'acc_long', 'acc_lat'):
        assert f'{key} n/a' in out


def test_format_line_imu_columns_and_jump():
    out = f.format_line(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 50.0,
                        imu_gyro_dps=3.0, imu_acc=(0.5, -0.25), jump=True)
    assert 'imu_gyro 3.0 dps' in out
    assert 'imu_acc 0.50,-0.25' in out
    assert out.endswith('JUMP')


def test_record_is_json_serialisable():
    rec = f.make_record(1.5, 10.0, 11.0, 1.0, None, 0.1, 0.2, 50.0)
    assert rec['heading_deg'] == 10.0
    assert rec['speed_mps'] is None
    assert rec['jump'] is False
    assert json.loads(json.dumps(rec)) == rec
    assert set(rec) == {'pi_time_s', 'heading_deg', 'imu_heading_deg',
                        'yaw_rate_dps', 'speed_mps', 'acc_long', 'acc_lat',
                        'imu_rate_hz', 'imu_gyro_z_dps', 'imu_acc_x', 'imu_acc_y',
                        'source', 'jump'}


def test_record_sources_and_imu_not_provided():
    rec = f.make_record(1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 50.0)
    assert rec['imu_gyro_z_dps'] is None and rec['imu_acc_x'] is None
    for k in ('heading_deg', 'yaw_rate_dps', 'speed_mps', 'acc_long', 'acc_lat'):
        assert rec['source'][k] == 'pose'
    assert rec['source']['imu_heading_deg'] == 'imu'
    assert rec['source']['imu_gyro_z_dps'] == 'imu'
    rec = f.make_record(1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 50.0,
                        imu_gyro_dps=1.0, imu_acc=(0.1, 0.2), jump=True)
    assert rec['imu_gyro_z_dps'] == 1.0 and rec['imu_acc_y'] == 0.2 and rec['jump'] is True


def test_nan_becomes_none_in_record():
    rec = f.make_record(1.5, math.nan, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert rec['heading_deg'] is None


def test_log_filename():
    assert f.log_filename(0) == 'lidar_imu_19700101T000000Z.jsonl'


def test_throttle():
    t = f.Throttle(0.1)
    assert t.ready(0.0)
    assert not t.ready(0.05)
    assert t.ready(0.11)
