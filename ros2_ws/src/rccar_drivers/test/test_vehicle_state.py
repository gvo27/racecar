"""Planar vehicle-state helpers."""
import math

import pytest

from rccar_drivers.slamtec import convert, vehicle_state as v


def test_quat_yaw_roundtrip():
    for yaw in (-3.0, -0.5, 0.0, 1.0, 3.0):
        x, y, z, w = convert.yaw_to_quat(yaw)
        assert v.quat_to_yaw(w, x, y, z) == pytest.approx(yaw)


def test_wrap_pi():
    assert v.wrap_pi(0.0) == 0.0
    assert v.wrap_pi(3 * math.pi / 2) == pytest.approx(-math.pi / 2)
    assert v.wrap_pi(-3 * math.pi / 2) == pytest.approx(math.pi / 2)
    assert v.wrap_pi(2 * math.pi) == pytest.approx(0.0, abs=1e-12)


def test_speed_none_until_two_samples():
    e = v.SpeedEstimator()
    assert e.update(0.0, 0.0, 0.0) is None
    assert e.update(0.1, 0.3, 0.4) == pytest.approx(5.0)


def test_speed_ignores_nonpositive_dt():
    e = v.SpeedEstimator()
    e.update(1.0, 0.0, 0.0)
    assert e.update(1.0, 5.0, 5.0) is None
    assert e.update(0.5, 5.0, 5.0) is None
    assert e.update(2.0, 1.0, 0.0) == pytest.approx(1.0)


def test_speed_window_forgets_old():
    e = v.SpeedEstimator(window_s=0.3)
    for i in range(10):
        e.update(i * 0.1, 0.0, 0.0)
    for i in range(10, 20):
        s = e.update(i * 0.1, (i - 9) * 0.2, 0.0)  # 2 m/s
    assert s == pytest.approx(2.0)


def test_reset():
    e = v.SpeedEstimator()
    e.update(0.0, 0.0, 0.0)
    e.update(1.0, 1.0, 0.0)
    e.reset()
    assert e.speed() is None


def test_planar_from_imu():
    assert v.planar_from_imu((1.0, 2.0, 9.8), (0.0, 0.0, 0.3)) == (1.0, 2.0, 0.3)
