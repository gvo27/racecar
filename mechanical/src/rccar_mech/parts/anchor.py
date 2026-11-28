"""Motor-plate anchor: a block screwed to the motor plate (4 x M3, counterbored from the top) with a snap pin.

The snap pin goes up through a slot in the deck. A slot in the pin splits it into two prongs that bend in Y. Each
prong has a lip with a 45 degree retention face: the deck latches when it is pushed down and releases when it is
pulled up with a force of some tens of newtons (estimate; the test print gives the real value). No tool is
necessary. The deck slot is long in X, so the front posts set the deck position and the anchor does not fight
them. The prongs root on the floor of a pocket in the block, which gives them a bending length. The pin slot ends
in a round bottom (no sharp corner at the prong root).
"""

import math
from dataclasses import dataclass

from build123d import Box, Cone, Cylinder, Pos, Rot, Shape


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


def prong_strain(radius: float, half_slot: float, bend: float, length: float) -> float:
    """Surface strain of one prong: a circular segment (pin radius, cut at half_slot from the pin axis), held at
    the root and bent by `bend` at its free end. Cantilever: strain = 3 * bend * c / length**2, with c the
    distance from the section centroid to the far fiber."""
    theta = 2 * math.acos(half_slot / radius)
    centroid = 4 * radius * math.sin(theta / 2) ** 3 / (3 * (theta - math.sin(theta)))
    c = max(radius - centroid, centroid - half_slot)
    return 3 * bend * c / length**2


def build(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Anchor:
    pos, mp = hw["motor_plate_position"], hw["motor_plate"]
    comp = pr["limits"]["hole_comp"]
    ax, ay, zb = pos["x"], pos["y"], pos["top_z"]
    s = cfg["anchor_size"]
    zf = zb + cfg["anchor_floor"]
    ztop = z0 + thickness
    pin_d, slot_w = cfg["snap_pin_d"], cfg["snap_slot_w"]
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

    # deck slot: long in X (play for the front-post position), tight in Y (the lips latch on its long edges)
    w = pin_d + 2 * cfg["snap_clearance"] + comp
    play = cfg["snap_slot_play"]
    cut = Pos(ax, ay, z0 + thickness / 2) * Box(2 * play, w, thickness)
    for sx in (-1, 1):
        cut += _cyl(ax + sx * play, ay, z0, ztop, w)

    # pin from the pocket floor, then the lip (retention cone up) and the lead-in cone. The retention face touches
    # the slot edge at the deck top: no free play in Z at the nominal heights
    z_lip = ztop - (w / 2 - r)
    pin = _cyl(ax, ay, zf, z_lip, pin_d)
    pin += Pos(ax, ay, z_lip + lip / 2) * Cone(r, r + lip, lip)
    pin += Pos(ax, ay, z_lip + lip + lead / 2) * Cone(r + lip, r - lip, lead)
    pin_top = z_lip + lip + lead
    # keyhole relief at the slot bottom: wider than the slot, 1 mm deep in the pocket floor (no sharp prong root)
    relief_d = cfg["snap_relief_d"]
    z_root = zf - cfg["snap_relief_depth"] + relief_d / 2
    slot_len = 2 * (r + lip) + 1
    pin -= Pos(ax, ay, (z_root + pin_top) / 2) * Box(slot_len, slot_w, pin_top - z_root)
    # relief length: halfway between the prong ends and the min_wall limit to the pocket wall
    x_pin = math.sqrt(r**2 - (slot_w / 2) ** 2)
    x_wall = math.sqrt((pocket_d / 2 - pr["limits"]["min_wall"]) ** 2 - (relief_d / 2) ** 2)
    groove = Pos(ax, ay, z_root) * Rot(0, 90, 0) * Cylinder(relief_d / 2, x_pin + x_wall)

    # each prong bends from the pocket floor to the lip contact, by the printed lip overlap past the slot edge
    # (lip - clearance: hole_comp makes the printed slot the design size)
    strain = prong_strain(r, slot_w / 2, lip - cfg["snap_clearance"], ztop - z_root)

    holes = [(x, y, d) for x, y in screws for d in (screw_d, cbore_d)] + [(ax, ay, pocket_d)]
    return Anchor(block + pin - groove, cut, holes, pin_top, strain)
