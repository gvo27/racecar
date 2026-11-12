"""SE(2) compose/invert."""
import math

import pytest

from rccar_drivers.slamtec import frames as f


def approx(t):
    return pytest.approx(t, abs=1e-9)


def test_compose_identity():
    assert f.compose((0, 0, 0), (1, 2, 0.3)) == approx((1, 2, 0.3))


def test_compose_rotation():
    assert f.compose((1, 0, math.pi / 2), (1, 0, 0)) == approx((1, 1, math.pi / 2))


def test_invert_roundtrip():
    a = (1.5, -2.0, 2.5)
    assert f.compose(a, f.invert(a)) == approx((0, 0, 0))
    assert f.compose(f.invert(a), a) == approx((0, 0, 0))


def test_yaw_wraps():
    assert f.compose((0, 0, 3.0), (0, 0, 3.0))[2] == approx(6.0 - 2 * math.pi)


def test_odom_to_base_offset_lidar():
    # lidar 0.2 m ahead of base, no rotation: base is 0.2 m behind the lidar pose
    assert f.odom_to_base((1.0, 2.0, 0.0), (0.2, 0.0, 0.0)) == approx((0.8, 2.0, 0.0))
    # robot facing +y: base is 0.2 m behind in -y
    assert f.odom_to_base((1.0, 2.0, math.pi / 2), (0.2, 0.0, 0.0)) == approx(
        (1.0, 1.8, math.pi / 2))
