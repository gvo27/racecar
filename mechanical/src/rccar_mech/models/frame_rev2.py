"""Frame rev2: a one-piece deck for the rev3 power board, the Pi 5 and the sensor rail blocks on the TT-02.

The deck lies on the front body-post stays (stock body clips) and on a snap anchor that is screwed to the motor plate.
The span from the front posts to the anchor is shorter than the rev1 span between the four posts, and the deck has no
joint. The deck releases without a tool: pull the two front clips, then pull the deck up off the snap pin.

Design parameters: config/frame_rev2.toml. Facts: config/hardware.toml, config/print.toml, the rev3 board file.
Chassis interface: parts/chassis_if.py. Previous revision: frame_rev1.
"""

import copy

from build123d import Color, Compound

from rccar_mech import checks, refs
from rccar_mech.models import _frame, is_ref
from rccar_mech.parts import chassis_if, deck

STL_TOLERANCE = 0.05

ANCHOR_COLOR = Color(0.3, 0.45, 0.75)


def _interface(cfg, hw, pr):
    z0 = hw["body_posts"]["base_z"]
    return z0, chassis_if.build(cfg, hw, pr, z0, cfg["deck_thickness"])


def build(cfg: dict) -> Compound:
    hw, pr, board = _frame.facts()
    z0, iface = _interface(cfg, hw, pr)
    ztop = z0 + cfg["deck_thickness"]
    pcb_pts, pi_pts = _frame.board_points(cfg, hw, board)

    plate = deck.outline(cfg, z0)
    for s in iface.add:
        plate += s
    plate = _frame.add_mounts(plate, cfg, hw, pcb_pts, pi_pts, ztop)
    for s in iface.cut:
        plate -= s

    children = [
        _frame.named(plate, "deck", _frame.DECK_COLOR),
        *(_frame.named(p, label, ANCHOR_COLOR) for label, p in iface.parts.items()),
        *_frame.payload_refs(cfg, hw, board, ztop),
        *refs.chassis(hw),
        *refs.wheels(hw),
    ]
    return Compound(children=children, label="frame_rev2")


def acceptance(asm: Compound, cfg: dict) -> list[checks.Finding]:
    hw, pr, board = _frame.facts()
    z0, iface = _interface(cfg, hw, pr)
    pcb_pts, pi_pts = _frame.board_points(cfg, hw, board)
    printed = [p for p in checks.parts(asm) if not is_ref(p)]
    out = []
    # every hole where the sources put it: board and Pi holes, chassis interface (posts, anchor)
    out += checks.expect_holes([copy.copy(p) for p in printed], iface.holes + pcb_pts + pi_pts)
    out += _frame.shared_acceptance(asm, cfg, hw, iface.clip_posts)
    # snap pin: the prong strain stays in the material limit, and the pin top leaves room under the boards
    if iface.snap is not None:
        limit = pr["material"]["snap_strain_max"]
        if iface.snap.strain > limit:
            msg = f"prong strain {iface.snap.strain:.4f} > {limit}"
            out.append(checks.Finding("MECH-SNAP", "error", "anchor snap pin", msg))
        above = iface.snap.pin_top - (z0 + cfg["deck_thickness"])
        out += _frame.room_under_boards(cfg, hw, above, "snap pin")
    return out
