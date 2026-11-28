"""Motor-plate anchor: a block screwed to the motor plate (4 x M3, counterbored from the top) with a snap pin.

The snap pin goes up through a slot in the deck. A slot in the pin splits it into two prongs that bend in Y. Each
prong has a lip with a 45 degree retention face: the deck latches when it is pushed down and releases when it is
pulled up hard (no tool). The deck slot is long in X, so the front posts set the deck position and the anchor
does not fight them. The prongs root on the floor of a pocket in the block, which gives them a bending length.
"""

from dataclasses import dataclass

from build123d import Box, Cone, Cylinder, Pos, Shape


@dataclass
class Anchor:
    part: Shape
    deck_cut: Shape
    holes: list[tuple[float, float, float]]
    pin_top: float
    strain: float


def _cyl(x: float, y: float, z_lo: float, z_hi: float, d: float) -> Shape:
    """Vertical cylinder of diameter d from z_lo to z_hi."""
    return Pos(x, y, (z_lo + z_hi) / 2) * Cylinder(d / 2, z_hi - z_lo)


def prong_strain(thickness: float, bend: float, length: float) -> float:
    """Surface strain of a cantilever prong with a constant section, bent by `bend` at its free end."""
    return 1.5 * thickness * bend / length**2


def build(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Anchor:
    pos, mp = hw["motor_plate_position"], hw["motor_plate"]
    comp = pr["limits"]["hole_comp"]
    ax, ay, zb = pos["x"], pos["y"], pos["top_z"]
    s = cfg["anchor_size"]
    zf = zb + cfg["anchor_floor"]
    ztop = z0 + thickness
    pin_d = cfg["snap_pin_d"]
    r = pin_d / 2
    lip, lead = cfg["snap_lip"], cfg["snap_lead_h"]

    block = Pos(ax, ay, (zb + z0) / 2) * Box(s, s, z0 - zb)
    screw_d = mp["clearance_d"] + comp
    cbore_d = cfg["anchor_cbore_d"] + comp
    pocket_d = pin_d + 2 * cfg["snap_pocket_gap"] + comp
    half = mp["pattern"] / 2
    screws = [(ax + sx * half, ay + sy * half) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in screws:
        block -= _cyl(x, y, zb, z0, screw_d)
        block -= _cyl(x, y, zf, z0, cbore_d)
    block -= _cyl(ax, ay, zf, z0, pocket_d)

    # pin from the pocket floor to the deck top, then the lip (retention cone up) and the lead-in cone
    pin = _cyl(ax, ay, zf, ztop, pin_d)
    pin += Pos(ax, ay, ztop + lip / 2) * Cone(r, r + lip, lip)
    pin += Pos(ax, ay, ztop + lip + lead / 2) * Cone(r + lip, r - lip, lead)
    pin_top = ztop + lip + lead
    pin -= Pos(ax, ay, (zf + pin_top) / 2) * Box(2 * (r + lip) + 1, cfg["snap_slot_w"], pin_top - zf)

    # deck slot: long in X (play for the front-post position), tight in Y (the lips latch on its long edges)
    w = pin_d + 2 * cfg["snap_clearance"] + comp
    play = cfg["snap_slot_play"]
    cut = Pos(ax, ay, z0 + thickness / 2) * Box(2 * play, w, thickness)
    for sx in (-1, 1):
        cut += _cyl(ax + sx * play, ay, z0, ztop, w)

    # each prong bends from the pocket floor to the lip, by the lip overlap past the slot edge
    strain = prong_strain((pin_d - cfg["snap_slot_w"]) / 2, lip - (w / 2 - r), ztop - zf)

    holes = [(x, y, d) for x, y in screws for d in (screw_d, cbore_d)] + [(ax, ay, pocket_d)]
    return Anchor(block + pin, cut, holes, pin_top, strain)
