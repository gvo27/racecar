"""Reference envelopes: the boards, the battery and the chassis parts. They are not printed (label prefix ref_).

Board envelopes are in their own frame: board center at the origin, board bottom at z = 0, X along the board length.
Chassis envelopes are in the car frame (docs/mechanical/conventions.md). All values come from hardware.toml.
"""

from build123d import Box, Color, Cylinder, Pos, Shape

from rccar_mech.kicad import Board

REF_COLOR = Color(0.2, 0.55, 0.2, 0.45)
BAT_COLOR = Color(0.15, 0.25, 0.6, 0.6)
CHASSIS_COLOR = Color(0.35, 0.35, 0.35, 0.8)
HOLDER_BAR_WIDTH = 12.0  # display envelope only, not a fact: the bar sits on the pack
HOLDER_PIN_D = 8.0  # display envelope only, not a fact


def _named(shape: Shape, label: str, color: Color) -> Shape:
    shape.label, shape.color = label, color
    return shape


def _slab(length: float, width: float, thickness: float, holes) -> Shape:
    s = Pos(0, 0, thickness / 2) * Box(length, width, thickness)
    for x, y, d in holes:
        s -= Pos(x, y, thickness / 2) * Cylinder(d / 2, thickness)
    return s


def pcb_rev3(hw: dict, board: Board) -> Shape:
    """The rev3 board with its M3 holes and the envelope of its tallest parts above it."""
    t = hw["pcb_rev3"]["thickness"]
    top = hw["pcb_rev3_heights"]["top"]
    slab = _slab(board.width, board.height, t, [(h.x, h.y, h.d) for h in board.holes])
    parts = Pos(0, 0, t + top / 2) * Box(board.width, board.height, top)
    return _named(slab + parts, "ref_pcb_rev3", REF_COLOR)


def pi5_holes(hw: dict) -> list[tuple[float, float, float]]:
    """(x, y, d) of the 4 holes, board-centered. The ports are at +X."""
    p = hw["pi5"]
    x0 = -p["length"] / 2 + p["hole_inset"]
    y0 = -p["width"] / 2 + p["hole_inset"]
    return [(x0 + i * p["hole_dx"], y0 + j * p["hole_dy"], p["hole_d"]) for i in (0, 1) for j in (0, 1)]


def pi5(hw: dict) -> Shape:
    """The Pi 5 board with its holes, the part envelope above it and the port overhang at +X."""
    p, h = hw["pi5"], hw["pi5_heights"]
    t = h["thickness"]
    slab = _slab(p["length"], p["width"], t, pi5_holes(hw))
    top = Pos(p["port_overhang"] / 2, 0, t + h["top"] / 2) * Box(p["length"] + p["port_overhang"], p["width"], h["top"])
    return _named(slab + top, "ref_pi5", REF_COLOR)


def chassis(hw: dict) -> list[Shape]:
    """Body posts, battery and battery holder in the car frame."""
    bp, bat, hold = hw["body_posts"], hw["battery"], hw["battery_holder"]
    out = []
    post_h = bp["top_z"] - bp["base_z"]
    for name, sx, sy in (("fl", 1, 1), ("fr", 1, -1), ("rl", -1, 1), ("rr", -1, -1)):
        post = Pos(sx * bp["spacing_x"] / 2, sy * bp["spacing_y"] / 2, bp["base_z"] + post_h / 2) * Cylinder(
            bp["diameter"] / 2, post_h
        )
        out.append(_named(post, f"ref_body_post_{name}", CHASSIS_COLOR))
    cx, cy = bat["center_x"], bat["center_y"]
    top = bat["bottom_z"] + bat["height"]
    out.append(
        _named(
            Pos(cx, cy, bat["bottom_z"] + bat["height"] / 2) * Box(bat["length"], bat["width"], bat["height"]),
            "ref_battery",
            BAT_COLOR,
        )
    )
    bar_h = hold["bar_top_z"] - top
    holder = Pos(cx, cy, top + bar_h / 2) * Box(2 * hold["pin_x"], HOLDER_BAR_WIDTH, bar_h)
    pin_h = hold["pin_top_z"] - bat["bottom_z"]
    for sx in (1, -1):
        holder += Pos(cx + sx * hold["pin_x"], cy, bat["bottom_z"] + pin_h / 2) * Cylinder(HOLDER_PIN_D / 2, pin_h)
    out.append(_named(holder, "ref_battery_holder", CHASSIS_COLOR))
    return out
