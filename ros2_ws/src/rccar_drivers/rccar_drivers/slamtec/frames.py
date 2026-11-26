"""Planar SE(2) transform helpers (x, y, yaw) for the Mapper TF chain (no rclpy)."""
import math


def wrap_pi(a):
    """Wrap an angle to [-pi, pi)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def compose(a, b):
    """Return a * b: pose `b` expressed in the frame of `a`; both (x, y, yaw)."""
    ax, ay, ayaw = a
    bx, by, byaw = b
    c, s = math.cos(ayaw), math.sin(ayaw)
    return (ax + c * bx - s * by, ay + s * bx + c * by, wrap_pi(ayaw + byaw))


def invert(a):
    """Return the inverse of an (x, y, yaw) transform."""
    ax, ay, ayaw = a
    c, s = math.cos(ayaw), math.sin(ayaw)
    return (-(c * ax + s * ay), -(-s * ax + c * ay), wrap_pi(-ayaw))


def odom_to_base(map_to_lidar, base_to_lidar):
    """Return base_link pose in the odom frame (map->odom is identity)."""
    return compose(map_to_lidar, invert(base_to_lidar))
