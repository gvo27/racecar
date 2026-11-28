"""Chassis interface: one function per type, with the same contract.

Each function returns an Interface: solids to add to the deck, solids to cut from it, extra printed parts (with a
label), the expected vertical holes (x, y, d) of all these for the acceptance check, and values for the acceptance
(info). The frame selects the type with `chassis_interface` in its config file.
"""

from dataclasses import dataclass, field

from build123d import Box, Cylinder, Pos, Shape

from rccar_mech.params import ParamError
from rccar_mech.parts import anchor


@dataclass
class Interface:
    add: list[Shape] = field(default_factory=list)
    cut: list[Shape] = field(default_factory=list)
    parts: list[Shape] = field(default_factory=list)
    holes: list[tuple[float, float, float]] = field(default_factory=list)
    info: dict = field(default_factory=dict)


def _posts(hw, front_only=False):
    bp = hw["body_posts"]
    sx, sy = bp["spacing_x"] / 2, bp["spacing_y"] / 2
    return [(x, y) for x in ((sx,) if front_only else (sx, -sx)) for y in (sy, -sy)]


def _post_holes(cfg, hw, pr, z0, thickness, front_only=False) -> Interface:
    d = hw["body_posts"]["diameter"] + 2 * cfg["post_clearance"] + pr["limits"]["hole_comp"]
    out = Interface()
    for x, y in _posts(hw, front_only):
        out.cut.append(Pos(x, y, z0 + thickness / 2) * Cylinder(d / 2, thickness))
        out.holes.append((x, y, d))
    return out


def body_posts(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    """The deck lies on the post stays. Each post goes through a hole. The stock body clips hold the deck down."""
    return _post_holes(cfg, hw, pr, z0, thickness)


def screw_pads(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    """Alternative: a pad at each post position with an M3 clearance hole for a screw into the damper stay."""
    d = cfg["pad_screw_d"] + pr["limits"]["hole_comp"]
    s = cfg["pad_size"]
    out = Interface()
    for x, y in _posts(hw):
        out.add.append(Pos(x, y, z0 + thickness / 2) * Box(s, s, thickness))
        out.cut.append(Pos(x, y, z0 + thickness / 2) * Cylinder(d / 2, thickness))
        out.holes.append((x, y, d))
    return out


def front_posts_anchor(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    """The front posts with the stock body clips, and a snap anchor screwed to the motor plate (parts/anchor.py).
    The anchor stays on the car. The deck releases from it without a tool."""
    out = _post_holes(cfg, hw, pr, z0, thickness, front_only=True)
    a = anchor.build(cfg, hw, pr, z0, thickness)
    out.cut.append(a.deck_cut)
    a.part.label = "anchor"
    out.parts.append(a.part)
    out.holes += a.holes
    out.info.update(snap_pin_top=a.pin_top, snap_strain=a.strain, clip_posts=["fl", "fr"])
    return out


TYPES = {"body_posts": body_posts, "screw_pads": screw_pads, "front_posts_anchor": front_posts_anchor}


def build(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    kind = cfg["chassis_interface"]
    if kind not in TYPES:
        raise ParamError(f"chassis_interface {kind}: use one of {', '.join(TYPES)}")
    return TYPES[kind](cfg, hw, pr, z0, thickness)
