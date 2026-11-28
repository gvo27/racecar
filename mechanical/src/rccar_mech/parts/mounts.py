"""Board standoffs (with a blind hole for an insert or a screw) and the sensor rail blocks (solid, drilled by hand)."""

from build123d import Box, Cylinder, Pos, Shape


def standoffs(points, z0: float, height: float, od: float) -> list[Shape]:
    """A solid standoff at each (x, y, _) point, from z0 up."""
    return [Pos(x, y, z0 + height / 2) * Cylinder(od / 2, height) for x, y, _ in points]


def blind_holes(points, z_top: float, d: float, depth: float) -> list[Shape]:
    """Cutters for a blind hole of diameter d, depth down from z_top, at each (x, y, _) point."""
    return [Pos(x, y, z_top - depth / 2) * Cylinder(d / 2, depth) for x, y, _ in points]


def block(x: float, y: float, z0: float, size) -> Shape:
    sx, sy, sz = size
    return Pos(x, y, z0 + sz / 2) * Box(sx, sy, sz)
