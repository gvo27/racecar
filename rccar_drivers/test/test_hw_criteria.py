"""Pure tests for rccar_drivers.hw_criteria (pass/fail evaluation of the physical lidar)."""
import math

from rccar_drivers import hw_criteria as c

INF = float('inf')


def test_link_ok_in_time():
    ok, detail = c.eval_link([(5.0, 2), (41.2, 0)])
    assert ok and '41.2' in detail


def test_link_late_or_never():
    assert not c.eval_link([(c.CONNECT_TIMEOUT_S + 1, 0)])[0]
    ok, detail = c.eval_link([(3.0, 2)])
    assert not ok and 'ERROR' in detail
    assert not c.eval_link([])[0]


def test_rate():
    times = [i * 0.1 for i in range(101)]  # 10 Hz over 10 s
    assert c.eval_rate(times, 10.0, 8.0)[0]
    assert not c.eval_rate(times[::2], 10.0, 8.0)[0]
    assert not c.eval_rate([], 10.0, 1.0)[0]


def test_gap():
    assert c.eval_gap([0.0, 0.1, 0.2])[0]
    ok, detail = c.eval_gap([0.0, 0.1, 1.3])
    assert not ok and '1.20' in detail
    assert not c.eval_gap([0.0])[0]


def test_scan_length():
    assert c.eval_scan_length([4, 4], 4)[0]
    assert not c.eval_scan_length([4, 3], 4)[0]


def test_finite_fraction():
    full = [1.0, INF, 2.0, INF]
    assert c.eval_finite_fraction([full], 0.3)[0]
    assert not c.eval_finite_fraction([[INF] * 4], 0.3)[0]
    assert not c.eval_finite_fraction([], 0.3)[0]


def test_range_bounds():
    assert c.eval_range_bounds([[0.2, INF, 39.0]], 0.15, 40.0)[0]
    assert not c.eval_range_bounds([[0.1, 1.0]], 0.15, 40.0)[0]
    assert not c.eval_range_bounds([[math.nan]], 0.15, 40.0)[0]


def test_frame_and_stamps():
    assert c.eval_frame(['lidar_link'] * 3, 'lidar_link')[0]
    assert not c.eval_frame(['lidar_link', 'x'], 'lidar_link')[0]
    assert c.eval_stamps_monotonic([1.0, 1.1, 1.1, 1.2])[0]
    assert not c.eval_stamps_monotonic([1.0, 0.9])[0]


def test_acc_units():
    assert c.classify_acc_units(9.81) == 'm/s^2'
    assert c.classify_acc_units(1.0) == 'g'
    assert c.classify_acc_units(4.0) == 'unknown'
    ok, detail = c.eval_acc_units([(0.0, 0.0, 9.8)] * 5)
    assert ok and 'm/s^2' in detail
    assert c.eval_acc_units([(0.0, 0.0, 1.0)] * 5)[0]
    ok, detail = c.eval_acc_units([(0.0, 0.0, 300.0)])
    assert not ok and 'units unknown' in detail
    assert not c.eval_acc_units([])[0]


def test_gyro_rest():
    assert c.eval_gyro_rest([0.01, -0.02, 0.0])[0]
    assert not c.eval_gyro_rest([0.3, 0.3])[0]
    assert not c.eval_gyro_rest([])[0]


def test_quat_norm():
    assert c.eval_quat_norm([(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.1, 0.995)])[0]
    assert not c.eval_quat_norm([(0.0, 0.0, 0.0, 0.0)])[0]


def test_pose_finite_and_drift():
    still = [(1.0, 2.0, 0.5)] * 10
    assert c.eval_pose_finite(still)[0]
    assert not c.eval_pose_finite([(1.0, math.nan, 0.0)])[0]
    assert c.eval_pose_drift(still)[0]
    moved = [(1.0, 2.0, 0.5), (1.1, 2.0, 0.5)]
    assert not c.eval_pose_drift(moved)[0]
    # yaw wraps: 179.9 deg -> -179.9 deg is a 0.2 deg change, not 360
    wrap = [(0.0, 0.0, math.radians(179.9)), (0.0, 0.0, math.radians(-179.9))]
    assert c.eval_pose_drift(wrap)[0]
    assert not c.eval_pose_drift([(0.0, 0.0, 0.0), (0.0, 0.0, math.radians(5))])[0]
    assert not c.eval_pose_drift([])[0]


def test_map():
    good = {'t': 3.0, 'width': 10, 'height': 10, 'resolution': 0.05,
            'data': [0] * 5 + [-1] * 95}
    assert c.eval_map_received(good)[0]
    assert not c.eval_map_received(None)[0]
    assert not c.eval_map_received(dict(good, t=31.0))[0]
    assert not c.eval_map_received(dict(good, width=0))[0]
    assert c.eval_map_resolution(good)[0]
    assert not c.eval_map_resolution(dict(good, resolution=0.1))[0]
    assert c.eval_map_known(good)[0]
    assert not c.eval_map_known(dict(good, data=[-1] * 100))[0]
    assert not c.eval_map_known(None)[0]


def test_tf():
    assert c.eval_tf(True)[0]
    assert not c.eval_tf(False)[0]


def test_publisher_precheck():
    assert c.eval_single_publisher(1)[0]
    ok, detail = c.eval_single_publisher(2)
    assert not ok and 'make drivers-stop' in detail
    assert not c.eval_single_publisher(0)[0]


# --- tri-state (PASS / FAIL / NA) ------------------------------------------------------
BENCH_AVAIL = 131  # quaternion + calibrated acc + 6dof fusion (inferred layout)


def test_status_constants():
    assert (c.PASS, c.FAIL, c.NA) == ('PASS', 'FAIL', 'NA')
    assert c.to_status(True) == 'PASS' and c.to_status(False) == 'FAIL'
    assert c.to_status('NA') == 'NA'


def test_overall_na_does_not_fail():
    assert c.overall(['PASS', 'NA', 'PASS']) == 'PASS'
    assert c.overall(['PASS', 'FAIL', 'NA']) == 'FAIL'
    assert c.overall([]) == 'FAIL'


def test_parse_avail():
    assert c.parse_avail('131') == 131
    assert c.parse_avail('') is None
    assert c.parse_avail(None) is None
    assert c.parse_avail('x') is None


def test_imu_acc_units_na_when_bit_absent():
    st, detail = c.eval_imu_acc_units([(0.0, 0.0, 0.003)], 1)  # quaternion only
    assert st == 'NA' and 'not provided' in detail


def test_imu_acc_units_evaluated_when_bit_present_or_unknown_bitmap():
    assert c.eval_imu_acc_units([(0.0, 0.0, 9.8)] * 3, BENCH_AVAIL)[0] == 'PASS'
    assert c.eval_imu_acc_units([(0.0, 0.0, 0.003)] * 3, BENCH_AVAIL)[0] == 'FAIL'
    assert c.eval_imu_acc_units([(0.0, 0.0, 9.8)] * 3, None)[0] == 'PASS'


def test_imu_acc_units_na_when_driver_does_not_provide_acc():
    # bench fw 2.6.0_dev: bitmap 131 flags CALIBRATED_ACC, but imu_trust_acc is false
    st, detail = c.eval_imu_acc_units([(0.0, 0.0, 0.003)] * 3, BENCH_AVAIL, False)
    assert st == 'NA' and 'imu_trust_acc' in detail


def test_imu_gyro_rest_na_when_bit_absent():
    assert c.eval_imu_gyro_rest([0.0] * 3, BENCH_AVAIL)[0] == 'NA'
    assert c.eval_imu_gyro_rest([0.0] * 3, BENCH_AVAIL | 4)[0] == 'PASS'
    assert c.eval_imu_gyro_rest([0.3] * 3, BENCH_AVAIL | 4)[0] == 'FAIL'
    assert c.eval_imu_gyro_rest([0.0] * 3, None)[0] == 'PASS'


def test_imu_quaternion_provided():
    assert c.eval_imu_quat_provided(BENCH_AVAIL)[0] == 'PASS'
    assert c.eval_imu_quat_provided(2)[0] == 'FAIL'
    assert c.eval_imu_quat_provided(None)[0] == 'NA'  # bitmap unobserved: cannot tell


def test_pose_yaw_rate_rest():
    still = [(0.1 * i, 0.5) for i in range(20)]
    st, detail = c.eval_pose_yaw_rate_rest(still)
    assert st == 'PASS' and 'rad/s' in detail
    turning = [(0.1 * i, 0.2 * 0.1 * i) for i in range(20)]  # 0.2 rad/s
    assert c.eval_pose_yaw_rate_rest(turning)[0] == 'FAIL'
    assert c.eval_pose_yaw_rate_rest([(0.0, 0.0)])[0] == 'FAIL'
    assert c.eval_pose_yaw_rate_rest([])[0] == 'FAIL'


def test_pose_yaw_rate_rest_wrap_small_step():
    # monotone slow rotation across the +-pi seam: 0.01 rad/s, passes
    poses = []
    for i in range(20):
        yaw = math.pi - 0.1 + 0.001 * i
        yaw = (yaw + math.pi) % (2 * math.pi) - math.pi
        poses.append((0.1 * i, yaw))
    assert c.eval_pose_yaw_rate_rest(poses)[0] == 'PASS'
