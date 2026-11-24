"""Pose-derived planar kinematics (yaw rate, speed, accelerations) from synthetic poses."""
import math

from rccar_calibration.lidar_imu_pose import PlanarEstimator

HZ = 10.0


def run(est, n, fn):
    out = None
    for i in range(n):
        t = i / HZ
        x, y, yaw = fn(t)
        out = est.update(t, x, y, yaw)
    return out


def test_first_sample_has_heading_only():
    out = PlanarEstimator().update(0.0, 0.0, 0.0, 0.3)
    assert abs(out.heading - 0.3) < 1e-12
    assert out.yaw_rate is None and out.speed is None
    assert out.acc_long is None and out.acc_lat is None and not out.jump


def test_constant_turn_circle():
    r, v = 2.0, 1.0
    w = v / r

    def circle(t):
        return r * math.sin(w * t), r * (1 - math.cos(w * t)), w * t
    out = run(PlanarEstimator(), 40, circle)
    assert abs(out.yaw_rate - w) < 0.02
    assert abs(out.speed - v) < 0.02
    assert abs(out.acc_lat - v * v / r) < 0.03
    assert abs(out.acc_long) < 0.05
    assert not out.jump


def test_right_turn_negative_rate_and_acc_lat():
    r, v = 2.0, 1.0
    w = -v / r

    def circle(t):
        return -r * math.sin(w * t), -r * (1 - math.cos(w * t)), w * t
    out = run(PlanarEstimator(), 40, circle)
    assert out.yaw_rate < 0 and out.acc_lat < 0


def test_straight_line_acceleration():
    a = 0.5
    out = run(PlanarEstimator(), 40, lambda t: (0.5 * a * t * t, 0.0, 0.0))
    assert abs(out.acc_long - a) < 0.05
    assert abs(out.yaw_rate) < 1e-9 and abs(out.acc_lat) < 1e-6


def test_yaw_wrap_at_pi_is_continuous():
    w = 0.5

    def spin(t):
        yaw = (math.pi - 0.5 + w * t + math.pi) % (2 * math.pi) - math.pi
        return 0.0, 0.0, yaw
    est = PlanarEstimator()
    for i in range(40):
        t = i / HZ
        out = est.update(t, *spin(t))
        assert not out.jump
        if i >= 5:
            assert abs(out.yaw_rate - w) < 0.02, (i, out.yaw_rate)


def test_jump_gate_flags_and_resets():
    est = PlanarEstimator()
    out = None
    for i in range(20):
        out = est.update(i / HZ, 0.0, 0.0, 0.1)
    assert out.yaw_rate == 0.0 and not out.jump
    out = est.update(2.0, 0.0, 0.0, 0.1 + 0.8)  # 0.8 rad in one step
    assert out.jump
    assert out.yaw_rate is None and out.acc_lat is None and out.acc_long is None
    assert abs(out.heading - 0.9) < 1e-12
    out = est.update(2.1, 0.0, 0.0, 0.9)  # the estimate restarts from the jump sample
    assert not out.jump and out.yaw_rate == 0.0


def test_jump_threshold_is_between_samples_and_wrap_aware():
    est = PlanarEstimator()
    est.update(0.0, 0.0, 0.0, math.pi - 0.1)
    out = est.update(0.1, 0.0, 0.0, -math.pi + 0.1)  # 0.2 rad across the seam: no jump
    assert not out.jump


def test_stale_gap_resets():
    est = PlanarEstimator()
    for i in range(5):
        est.update(i / HZ, float(i), 0.0, 0.0)
    out = est.update(10.0, 100.0, 0.0, 0.0)  # 9.6 s gap: no speed from a stale pose
    assert out.speed is None and out.yaw_rate is None


def test_non_increasing_time_ignored_safely():
    est = PlanarEstimator()
    est.update(1.0, 0.0, 0.0, 0.0)
    out = est.update(1.0, 1.0, 0.0, 0.0)
    assert out.speed is None


def test_reset():
    est = PlanarEstimator()
    run(est, 10, lambda t: (t, 0.0, 0.0))
    est.reset()
    assert est.update(5.0, 0.0, 0.0, 0.0).speed is None
