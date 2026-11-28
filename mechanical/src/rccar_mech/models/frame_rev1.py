"""Frame rev1 (kept for a later comparison): the deck on the four body-post stays, printed in two halves with a
splice plate. Successor: frame_rev2. Not printable as it is: rev1 does not model the motor housing
([motor_housing] in hardware.toml), and its deck crosses the housing envelope.

Design parameters: config/frame_rev1.toml. Facts: config/hardware.toml, config/print.toml, the rev3 board file.
The deck lies on the body-post stays and lifts off for the battery swap (chassis interface: parts/chassis_if.py).
"""

import copy

from build123d import Color, Compound, Cylinder, Pos

from rccar_mech import checks, refs
from rccar_mech.models import _frame, is_ref
from rccar_mech.parts import chassis_if, deck

STL_TOLERANCE = 0.05

SPLICE_COLOR = Color(0.3, 0.45, 0.75)


def layout(cfg: dict, hw: dict, pr: dict, board) -> dict:
    """All positions and hole lists of the frame, in the car frame. build() and acceptance() both use it."""
    z0 = hw["body_posts"]["base_z"]
    ztop = z0 + cfg["deck_thickness"]
    pcb_pts, pi_pts = _frame.board_points(cfg, hw, board)
    bolt_d = cfg["splice_bolt_d"] + pr["limits"]["hole_comp"]
    bolts = [(x, y, bolt_d) for x, y in deck.splice_bolts(cfg)]
    return {"z0": z0, "ztop": ztop, "pcb": pcb_pts, "pi": pi_pts, "bolts": bolts, "bolt_d": bolt_d}


def fasteners(cfg: dict, hw: dict, z0: float, ztop: float):
    """Splice bolt hardware: button heads on the deck top, nuts under the splice (envelopes, not printed)."""
    f = hw["fasteners"]
    z_nut = z0 - cfg["splice_thickness"] - f["m3_nut_h"] / 2
    out = None
    for x, y in deck.splice_bolts(cfg):
        head = Pos(x, y, ztop + f["m3_head_h"] / 2) * Cylinder(f["m3_head_d"] / 2, f["m3_head_h"])
        nut = Pos(x, y, z_nut) * Cylinder(f["m3_nut_w"] / 2, f["m3_nut_h"])
        out = head + nut if out is None else out + head + nut
    return out


def build(cfg: dict) -> Compound:
    hw, pr, board = _frame.facts()
    lay = layout(cfg, hw, pr, board)
    z0, ztop = lay["z0"], lay["ztop"]
    iface = chassis_if.build(cfg, hw, pr, z0, cfg["deck_thickness"])

    plate = deck.outline(cfg, z0)
    for s in iface.add:
        plate += s
    plate = _frame.add_mounts(plate, cfg, hw, lay["pcb"], lay["pi"], ztop)
    for s in iface.cut + deck.bolt_cutters(cfg, lay["bolt_d"], z0, ztop):
        plate -= s
    front, rear = deck.halves(plate, cfg, z0)

    splice = deck.splice(cfg, z0)
    for s in deck.bolt_cutters(cfg, lay["bolt_d"], z0 - cfg["splice_thickness"], z0):
        splice -= s

    children = [
        _frame.named(front, "deck_front", _frame.DECK_COLOR),
        _frame.named(rear, "deck_rear", _frame.DECK_COLOR),
        _frame.named(splice, "splice", SPLICE_COLOR),
        *_frame.payload_refs(cfg, hw, board, ztop),
        _frame.named(fasteners(cfg, hw, z0, ztop), "ref_fasteners", _frame.FASTENER_COLOR),
        *refs.chassis(hw),
        *refs.wheels(hw),
    ]
    return Compound(children=children, label="frame_rev1")


def acceptance(asm: Compound, cfg: dict) -> list[checks.Finding]:
    hw, pr, board = _frame.facts()
    lay = layout(cfg, hw, pr, board)
    iface = chassis_if.build(cfg, hw, pr, lay["z0"], cfg["deck_thickness"])
    every = checks.parts(asm)
    printed = [p for p in every if not is_ref(p)]
    by = {p.label: p for p in every}
    out = []
    # every hole where the sources put it: board and Pi holes, chassis interface, splice bolts (deck and splice)
    expected = iface.holes + lay["pcb"] + lay["pi"] + lay["bolts"] + lay["bolts"]
    out += checks.expect_holes([copy.copy(p) for p in printed], expected)
    out += _frame.shared_acceptance(asm, cfg, hw, iface.clip_posts)
    # splice bolt heads under the boards: room above the heads for the parts under each board
    out += _frame.room_under_boards(cfg, hw, hw["fasteners"]["m3_head_h"], "bolt heads")
    out += checks.clearance(by["ref_fasteners"], by["ref_battery_holder"], cfg["clearance_min"])
    return out
