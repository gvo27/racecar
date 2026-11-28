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


def build(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Anchor:
    pos, mp = hw["motor_plate_position"], hw["motor_plate"]
    comp = pr["limits"]["hole_comp"]
    ax, ay, zb = pos["x"], pos["y"], pos["top_z"]
    s, floor = cfg["anchor_size"], cfg["anchor_floor"]
    h = z0 - zb
    zf = zb + floor
    ztop = z0 + thickness
    r = cfg["snap_pin_d"] / 2
    lip, lead = cfg["snap_lip"], cfg["snap_lead_h"]

    block = Pos(ax, ay, zb + h / 2) * Box(s, s, h)
    screw_d = mp["clearance_d"] + comp
    cbore_d = cfg["anchor_cbore_d"] + comp
    pocket_d = cfg["snap_pin_d"] + 2 * cfg["snap_pocket_gap"] + comp
    half = mp["pattern"] / 2
    screws = [(ax + sx * half, ay + sy * half) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y in screws:
        block -= Pos(x, y, zb + h / 2) * Cylinder(screw_d / 2, h)
        block -= Pos(x, y, zf + (z0 - zf) / 2) * Cylinder(cbore_d / 2, z0 - zf)
    block -= Pos(ax, ay, zf + (z0 - zf) / 2) * Cylinder(pocket_d / 2, z0 - zf)

    # pin from the pocket floor to the deck top, then the lip (retention cone up) and the lead-in cone
    pin = Pos(ax, ay, zf + (ztop - zf) / 2) * Cylinder(r, ztop - zf)
    pin += Pos(ax, ay, ztop + lip / 2) * Cone(r, r + lip, lip)
    pin += Pos(ax, ay, ztop + lip + lead / 2) * Cone(r + lip, r - lip, lead)
    pin_top = ztop + lip + lead
    pin -= Pos(ax, ay, zf + (pin_top - zf) / 2) * Box(2 * (r + lip) + 1, cfg["snap_slot_w"], pin_top - zf)
    part = block + pin

    # deck slot: long in X (play for the front-post position), tight in Y (the lips latch on its long edges)
    w = cfg["snap_pin_d"] + 2 * cfg["snap_clearance"] + comp
    play = cfg["snap_slot_play"]
    zc = z0 + thickness / 2
    cut = Pos(ax, ay, zc) * Box(2 * play, w, thickness)
    for sx in (-1, 1):
        cut += Pos(ax + sx * play, ay, zc) * Cylinder(w / 2, thickness)

    # prong strain: cantilever from the pocket floor to the lip, bent by the lip overlap past the slot edge
    t_prong = (cfg["snap_pin_d"] - cfg["snap_slot_w"]) / 2
    bend = lip - (w / 2 - r)
    length = ztop - zf
    strain = 1.5 * t_prong * bend / length**2

    holes = [(x, y, d) for x, y in screws for d in (screw_d, cbore_d)] + [(ax, ay, pocket_d)]
    return Anchor(part, cut, holes, pin_top, strain)
