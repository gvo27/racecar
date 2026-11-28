"""Shared parts of the frame models (frame_rev1, frame_rev2): facts, board and Pi mounts, sensor blocks, references,
and the acceptance criteria that all frame revisions share. The registry skips this module (name starts with _)."""

from build123d import Box, Color, Pos, Shape

from rccar_mech import checks, kicad, params, refs
from rccar_mech.parts import mounts, moved, place

DECK_COLOR = Color(0.95, 0.55, 0.1)
MAPPER_COLOR = Color(0.6, 0.2, 0.6, 0.45)
FASTENER_COLOR = Color(0.5, 0.5, 0.5, 0.8)


def facts():
    hw = params.load_facts(params.config_path("hardware.toml"))
    pr = params.load_facts(params.config_path("print.toml"))
    board = kicad.read_board(params.repo_path(hw["pcb_rev3"]["board"]))
    return hw, pr, board


def named(shape: Shape, label: str, color: Color) -> Shape:
    shape.label, shape.color = label, color
    return shape


def board_points(cfg: dict, hw: dict, board) -> tuple[list, list]:
    """Car-frame (x, y, d) of the rev3 insert holes and the Pi pilot holes."""
    f = hw["fasteners"]
    pcb = moved([(h.x, h.y, f["m3_insert_hole"]) for h in board.holes], cfg["pcb_x"], cfg["pcb_y"], cfg["pcb_rot"])
    pi = moved([(x, y, f["m25_pilot"]) for x, y, _ in refs.pi5_holes(hw)], cfg["pi_x"], cfg["pi_y"], cfg["pi_rot"])
    return pcb, pi


def add_mounts(plate: Shape, cfg: dict, hw: dict, pcb_pts, pi_pts, ztop: float) -> Shape:
    """Board standoffs with their blind holes, and the two sensor rail blocks, on the deck top."""
    f = hw["fasteners"]
    for s in mounts.standoffs(pcb_pts, ztop, cfg["pcb_standoff_h"], cfg["pcb_standoff_od"]):
        plate += s
    for s in mounts.standoffs(pi_pts, ztop, cfg["pi_standoff_h"], cfg["pi_standoff_od"]):
        plate += s
    plate += mounts.block(cfg["lidar_block_x"], cfg["lidar_block_y"], ztop, cfg["lidar_block_size"])
    plate += mounts.block(cfg["camera_block_x"], cfg["camera_block_y"], ztop, cfg["camera_block_size"])
    for s in mounts.blind_holes(pcb_pts, ztop + cfg["pcb_standoff_h"], f["m3_insert_hole"], f["m3_insert_depth"]):
        plate -= s
    for s in mounts.blind_holes(pi_pts, ztop + cfg["pi_standoff_h"], f["m25_pilot"], f["m25_pilot_depth"]):
        plate -= s
    return plate


def payload_refs(cfg: dict, hw: dict, board, ztop: float) -> list[Shape]:
    """The rev3 board, the Pi 5 and the mapper (lidar) envelopes at their mounts."""
    pcb = place(cfg["pcb_x"], cfg["pcb_y"], ztop + cfg["pcb_standoff_h"], cfg["pcb_rot"]) * refs.pcb_rev3(hw, board)
    pi = place(cfg["pi_x"], cfg["pi_y"], ztop + cfg["pi_standoff_h"], cfg["pi_rot"]) * refs.pi5(hw)
    m = hw["mapper"]
    block_top = ztop + cfg["lidar_block_size"][2]
    mapper = Pos(cfg["lidar_block_x"], cfg["lidar_block_y"], block_top + m["height"] / 2) * Box(
        m["body"], m["body"], m["height"]
    )
    return [
        named(pcb, "ref_pcb_rev3", refs.REF_COLOR),
        named(pi, "ref_pi5", refs.REF_COLOR),
        named(mapper, "ref_mapper", MAPPER_COLOR),
    ]


def shared_acceptance(asm, cfg: dict, hw: dict, clip_posts: list[str]) -> list[checks.Finding]:
    """Battery and holder clearance, standoff minimums, wheel clearance, clip access at the posts in clip_posts
    (labels), and the printed top height."""
    every = checks.parts(asm)
    printed = [p for p in every if not p.label.startswith("ref_")]
    by = {p.label: p for p in every}
    out = []
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
    for w in (p for p in every if p.label.startswith("ref_wheel_")):
        for p in [*printed, by["ref_pcb_rev3"], by["ref_pi5"], by["ref_mapper"]]:
            out += checks.clearance(p, w, cfg["clearance_min"])
    # clip access: room for a hand and a body clip next to each post that holds the deck
    for post in clip_posts:
        for label in ("ref_mapper", "ref_pcb_rev3", "ref_pi5"):
            out += checks.clearance(by[label], by[post], cfg["clip_clearance"])
    # keep the printed parts low (handling)
    top = max(p.bounding_box().max.Z for p in printed)
    if top > cfg["printed_top_max"]:
        out.append(
            checks.Finding("MECH-HEIGHT", "error", "printed parts", f"top z {top:.1f} > {cfg['printed_top_max']}")
        )
    return out
