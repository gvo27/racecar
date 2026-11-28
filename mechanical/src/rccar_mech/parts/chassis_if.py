"""Chassis interface: one function per type, with the same contract.

Each function returns an Interface: solids to add to the deck, solids to cut from it, and the expected vertical holes
(x, y, d) for the acceptance check. The frame selects the type with `chassis_interface` in frame.toml.
"""

from dataclasses import dataclass, field

from build123d import Box, Cylinder, Pos, Shape

from rccar_mech.params import ParamError


@dataclass
class Interface:
    add: list[Shape] = field(default_factory=list)
    cut: list[Shape] = field(default_factory=list)
    holes: list[tuple[float, float, float]] = field(default_factory=list)


def _posts(hw):
    bp = hw["body_posts"]
    sx, sy = bp["spacing_x"] / 2, bp["spacing_y"] / 2
    return [(x, y) for x in (sx, -sx) for y in (sy, -sy)]


def body_posts(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    """The deck lies on the post stays. Each post goes through a hole. The stock body clips hold the deck down."""
    d = hw["body_posts"]["diameter"] + 2 * cfg["post_clearance"] + pr["limits"]["hole_comp"]
    out = Interface()
    for x, y in _posts(hw):
        out.cut.append(Pos(x, y, z0 + thickness / 2) * Cylinder(d / 2, thickness))
        out.holes.append((x, y, d))
    return out


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


TYPES = {"body_posts": body_posts, "screw_pads": screw_pads}


def build(cfg: dict, hw: dict, pr: dict, z0: float, thickness: float) -> Interface:
    kind = cfg["chassis_interface"]
    if kind not in TYPES:
        raise ParamError(f"chassis_interface {kind}: use one of {', '.join(TYPES)}")
    return TYPES[kind](cfg, hw, pr, z0, thickness)
