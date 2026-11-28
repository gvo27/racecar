"""Pipeline test part: a plate with two through holes. Parameters: config/test_bracket.toml."""

from build123d import Box, Color, Compound, Cylinder, Pos

from rccar_mech import checks

STL_TOLERANCE = 0.01


def build(cfg: dict) -> Compound:
    plate = Box(cfg["length"], cfg["width"], cfg["thickness"])
    s = cfg["hole_spacing"] / 2
    for x in (-s, s):
        plate -= Pos(x, 0, 0) * Cylinder(cfg["hole_d"] / 2, cfg["thickness"])
    plate.label = "bracket"
    plate.color = Color(0.9, 0.55, 0.1)
    return Compound(children=[plate], label="test_bracket")


def acceptance(asm: Compound, cfg: dict) -> list[checks.Finding]:
    s = cfg["hole_spacing"] / 2
    return checks.expect_holes(asm, [(-s, 0.0, cfg["hole_d"]), (s, 0.0, cfg["hole_d"])])
