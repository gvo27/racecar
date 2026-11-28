"""Deck plate: a wide middle, narrow ends, split in two halves for the print bed, and the splice plate."""

from build123d import Axis, Box, Cylinder, Pos, Shape, fillet


def _rect(x0, x1, y0, y1, z0, t) -> Shape:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, z0 + t / 2) * Box(x1 - x0, y1 - y0, t)


def outline(cfg: dict, z0: float) -> Shape:
    """The whole deck plate, before the split. Vertical edges get the corner radius."""
    t = cfg["deck_thickness"]
    e = cfg["end_half_width"]
    plate = _rect(cfg["deck_x_rear"], cfg["deck_x_front"], -e, e, z0, t)
    plate += _rect(cfg["mid_x_min"], cfg["mid_x_max"], cfg["mid_y_min"], cfg["mid_y_max"], z0, t)
    if cfg["corner_r"] > 0:
        plate = fillet(plate.edges().filter_by(Axis.Z), radius=cfg["corner_r"])
    return plate


def halves(plate: Shape, cfg: dict, z0: float) -> tuple[Shape, Shape]:
    """Front (x > split_x) and rear (x < split_x) half, with all the features above and below the plate."""
    big = 1000.0
    sx = cfg["split_x"]
    front = plate & _rect(sx, big, -big, big, -big, 2 * big)
    rear = plate & _rect(-big, sx, -big, big, -big, 2 * big)
    return front, rear


def splice_bolts(cfg: dict) -> list[tuple[float, float]]:
    sx, dx = cfg["split_x"], cfg["splice_bolt_dx"]
    return [(sx + s * dx, y) for s in (-1, 1) for y in cfg["splice_bolt_y"]]


def splice(cfg: dict, z0: float) -> Shape:
    """Plate under the joint, from mid_y_min to mid_y_max. Its top touches the deck bottom at z0."""
    t = cfg["splice_thickness"]
    sx, half = cfg["split_x"], cfg["splice_length"] / 2
    return _rect(sx - half, sx + half, cfg["mid_y_min"], cfg["mid_y_max"], z0 - t, t)


def bolt_cutters(cfg: dict, d: float, z_bottom: float, z_top: float) -> list[Shape]:
    h = z_top - z_bottom
    return [Pos(x, y, z_bottom + h / 2) * Cylinder(d / 2, h) for x, y in splice_bolts(cfg)]
