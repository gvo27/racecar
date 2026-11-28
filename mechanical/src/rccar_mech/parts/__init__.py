"""Printed part features. Each function returns solids in the car frame. Values come from the design and fact files."""

import math

from build123d import Location, Pos, Rot, Vector


def place(x: float, y: float, z: float, rot: float) -> Location:
    """Move to (x, y, z) after a turn of rot degrees about Z."""
    return Pos(x, y, z) * Rot(0, 0, rot)


def turn_point(x: float, y: float, rot: float) -> tuple[float, float]:
    a = math.radians(rot)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def moved(points, x: float, y: float, rot: float):
    """Board-frame (px, py, d) points -> car-frame (x, y, d)."""
    out = []
    for px, py, d in points:
        tx, ty = turn_point(px, py, rot)
        out.append((x + tx, y + ty, d))
    return out


__all__ = ["Vector", "moved", "place", "turn_point"]
