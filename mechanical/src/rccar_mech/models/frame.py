"""Frame rev1: the deck that carries the rev3 power board, the Pi 5 and the sensor rail blocks on the TT-02.

Design parameters: config/frame.toml. Facts: config/hardware.toml, config/print.toml, the rev3 board file.
The deck lies on the body-post stays and lifts off for the battery swap (chassis interface: parts/chassis_if.py).
"""

import copy

from build123d import Box, Color, Compound, Cylinder, Pos

from rccar_mech import checks, kicad, params, refs
from rccar_mech.parts import chassis_if, deck, mounts, moved, place

STL_TOLERANCE = 0.05

DECK_COLOR = Color(0.95, 0.55, 0.1)
SPLICE_COLOR = Color(0.3, 0.45, 0.75)
MAPPER_COLOR = Color(0.6, 0.2, 0.6, 0.45)
FASTENER_COLOR = Color(0.5, 0.5, 0.5, 0.8)


def _facts():
    hw = params.load_facts(params.config_path("hardware.toml"))
    pr = params.load_facts(params.config_path("print.toml"))
    board = kicad.read_board(params.repo_path(hw["pcb_rev3"]["board"]))
    return hw, pr, board


def layout(cfg: dict, hw: dict, pr: dict, board) -> dict:
    """All positions and hole lists of the frame, in the car frame. build() and acceptance() both use it."""
    z0 = hw["body_posts"]["base_z"]
    ztop = z0 + cfg["deck_thickness"]
    comp = pr["limits"]["hole_comp"]
    pcb_pts = moved(
        [(h.x, h.y, hw["fasteners"]["m3_insert_hole"]) for h in board.holes], cfg["pcb_x"], cfg["pcb_y"], cfg["pcb_rot"]
    )
    pi_pts = moved(
        [(x, y, hw["fasteners"]["m25_pilot"]) for x, y, _ in refs.pi5_holes(hw)],
        cfg["pi_x"],
        cfg["pi_y"],
        cfg["pi_rot"],
    )
    bolt_d = cfg["splice_bolt_d"] + comp
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


def _named(shape, label, color):
    shape.label, shape.color = label, color
    return shape


def build(cfg: dict) -> Compound:
    hw, pr, board = _facts()
    lay = layout(cfg, hw, pr, board)
    z0, ztop = lay["z0"], lay["ztop"]
    iface = chassis_if.build(cfg, hw, pr, z0, cfg["deck_thickness"])

    plate = deck.outline(cfg, z0)
    for s in iface.add:
        plate += s
    for s in mounts.standoffs(lay["pcb"], ztop, cfg["pcb_standoff_h"], cfg["pcb_standoff_od"]):
        plate += s
    for s in mounts.standoffs(lay["pi"], ztop, cfg["pi_standoff_h"], cfg["pi_standoff_od"]):
        plate += s
    plate += mounts.block(cfg["lidar_block_x"], cfg["lidar_block_y"], ztop, cfg["lidar_block_size"])
    plate += mounts.block(cfg["camera_block_x"], cfg["camera_block_y"], ztop, cfg["camera_block_size"])
    for s in mounts.blind_holes(
        lay["pcb"], ztop + cfg["pcb_standoff_h"], hw["fasteners"]["m3_insert_hole"], hw["fasteners"]["m3_insert_depth"]
    ):
        plate -= s
    for s in mounts.blind_holes(
        lay["pi"], ztop + cfg["pi_standoff_h"], hw["fasteners"]["m25_pilot"], hw["fasteners"]["m25_pilot_depth"]
    ):
        plate -= s
    for s in iface.cut + deck.bolt_cutters(cfg, lay["bolt_d"], z0, ztop):
        plate -= s
    front, rear = deck.halves(plate, cfg, z0)

    splice = deck.splice(cfg, z0)
    for s in deck.bolt_cutters(cfg, lay["bolt_d"], z0 - cfg["splice_thickness"], z0):
        splice -= s

    pcb = place(cfg["pcb_x"], cfg["pcb_y"], ztop + cfg["pcb_standoff_h"], cfg["pcb_rot"]) * refs.pcb_rev3(hw, board)
    pi = place(cfg["pi_x"], cfg["pi_y"], ztop + cfg["pi_standoff_h"], cfg["pi_rot"]) * refs.pi5(hw)
    m = hw["mapper"]
    block_top = ztop + cfg["lidar_block_size"][2]
    mapper = Pos(cfg["lidar_block_x"], cfg["lidar_block_y"], block_top + m["height"] / 2) * Box(
        m["body"], m["body"], m["height"]
    )
    children = [
        _named(front, "deck_front", DECK_COLOR),
        _named(rear, "deck_rear", DECK_COLOR),
        _named(splice, "splice", SPLICE_COLOR),
        _named(pcb, "ref_pcb_rev3", refs.REF_COLOR),
        _named(pi, "ref_pi5", refs.REF_COLOR),
        _named(mapper, "ref_mapper", MAPPER_COLOR),
        _named(fasteners(cfg, hw, z0, ztop), "ref_fasteners", FASTENER_COLOR),
        *refs.chassis(hw),
        *refs.wheels(hw),
    ]
    return Compound(children=children, label="frame")


def acceptance(asm: Compound, cfg: dict) -> list[checks.Finding]:
    hw, pr, board = _facts()
    lay = layout(cfg, hw, pr, board)
    iface = chassis_if.build(cfg, hw, pr, lay["z0"], cfg["deck_thickness"])
    every = checks.parts(asm)
    printed = [p for p in every if not p.label.startswith("ref_")]
    by = {p.label: p for p in every}
    out = []
    # every hole where the sources put it: board and Pi holes, chassis interface, splice bolts (deck and splice)
    expected = iface.holes + lay["pcb"] + lay["pi"] + lay["bolts"] + lay["bolts"]
    out += checks.expect_holes([copy.copy(p) for p in printed], expected)
    # the battery and its holder stay free (clearance), the boards have room under them
    for p in printed:
        for ref in ("ref_battery", "ref_battery_holder"):
            out += checks.clearance(p, by[ref], cfg["clearance_min"])
    need = max(hw["pcb_rev3_heights"]["standoff_min"], hw["pcb_rev3_heights"]["bottom"])
    if cfg["pcb_standoff_h"] < need:
        out.append(checks.Finding("MECH-CLEAR", "error", "pcb standoff", f"{cfg['pcb_standoff_h']} mm < {need} mm"))
    if cfg["pi_standoff_h"] < hw["pi5_heights"]["bottom"]:
        out.append(checks.Finding("MECH-CLEAR", "error", "pi standoff", "lower than the parts under the Pi"))
    # wheels: the deck, the boards and the lidar stay clear of the tyre envelopes (front: with the steer margin)
    wheels = [p for p in every if p.label.startswith("ref_wheel_")]
    for w in wheels:
        for p in [*printed, by["ref_pcb_rev3"], by["ref_pi5"], by["ref_mapper"]]:
            out += checks.clearance(p, w, cfg["clearance_min"])
    # clip access: room for a hand and a body clip next to each post
    for post in (p for p in every if p.label.startswith("ref_body_post_")):
        for label in ("ref_mapper", "ref_pcb_rev3", "ref_pi5"):
            out += checks.clearance(by[label], post, cfg["clip_clearance"])
    # splice bolt heads under the boards: room above the heads for the parts under each board
    f = hw["fasteners"]
    for name, h, bottom in (
        ("pcb", cfg["pcb_standoff_h"], hw["pcb_rev3_heights"]["bottom"]),
        ("pi", cfg["pi_standoff_h"], hw["pi5_heights"]["bottom"]),
    ):
        room = h - bottom - f["m3_head_h"]
        if room < cfg["clearance_min"]:
            out.append(checks.Finding("MECH-CLEAR", "error", f"{name} / bolt heads", f"{room:.2f} mm < clearance"))
    out += checks.clearance(by["ref_fasteners"], by["ref_battery_holder"], cfg["clearance_min"])
    # keep the printed parts low (handling)
    top = max(p.bounding_box().max.Z for p in printed)
    if top > cfg["printed_top_max"]:
        out.append(
            checks.Finding("MECH-HEIGHT", "error", "printed parts", f"top z {top:.1f} > {cfg['printed_top_max']}")
        )
    return out
