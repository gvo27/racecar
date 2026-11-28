"""Generic geometry checks on small known shapes."""

import pytest
from build123d import Box, Compound, Cylinder, Pos

from rccar_mech import checks

PRINT = {
    "limits": {"min_wall": 1.6, "hole_comp": 0.2},
    "bed": {"x": 220.0, "y": 220.0, "z": 250.0},
}


def plate_with_hole(x=10.0, d=3.2, length=40.0):
    return Box(length, 20, 5) - Pos(x, 0, 0) * Cylinder(d / 2, 5)


def ids(findings):
    return sorted(f.id for f in findings)


def test_valid_solid_passes():
    assert checks.validity(Box(10, 10, 10)) == []


def test_empty_shape_fails():
    assert ids(checks.validity(Compound([]))) == ["MECH-VALID"]


def test_hole_inventory_finds_diameter_and_axis():
    holes = checks.holes(plate_with_hole(x=10.0))
    assert len(holes) == 1
    h = holes[0]
    assert h.diameter == pytest.approx(3.2, abs=1e-6)
    assert (h.x, h.y) == pytest.approx((10.0, 0.0), abs=1e-6)
    assert h.axis == pytest.approx((0, 0, 1), abs=1e-6) or h.axis == pytest.approx((0, 0, -1), abs=1e-6)


def test_boss_is_not_a_hole():
    boss = Box(20, 20, 2) + Pos(0, 0, 3) * Cylinder(3, 4)
    assert checks.holes(boss) == []


def test_expected_holes_match_and_mismatch():
    part = plate_with_hole(x=10.0)
    assert checks.expect_holes(part, [(10.0, 0.0, 3.2)], tol=0.01) == []
    assert ids(checks.expect_holes(part, [(12.0, 0.0, 3.2)], tol=0.01)) == ["MECH-HOLE", "MECH-HOLE"]


def test_thin_wall_is_found():
    # hole edge 0.4 mm from the end face: below min_wall
    part = plate_with_hole(x=20 - 0.4 - 1.6)
    assert "MECH-WALL" in ids(checks.walls(part, PRINT))
    assert checks.walls(plate_with_hole(x=0.0), PRINT) == []


def test_interference_between_labeled_parts():
    a, b = Box(10, 10, 10), Pos(5, 0, 0) * Box(10, 10, 10)
    a.label, b.label = "a", "b"
    assert ids(checks.interference([a, b])) == ["MECH-INTERFERE"]
    b2 = Pos(20, 0, 0) * Box(10, 10, 10)
    b2.label = "b"
    assert checks.interference([a, b2]) == []


def test_clearance():
    a, b = Box(10, 10, 10), Pos(12, 0, 0) * Box(10, 10, 10)
    a.label, b.label = "a", "b"
    assert checks.clearance(a, b, 1.5) == []
    assert ids(checks.clearance(a, b, 3.0)) == ["MECH-CLEAR"]


def test_bed_fit():
    assert checks.bed_fit(Box(200, 100, 10), PRINT) == []
    assert ids(checks.bed_fit(Box(300, 100, 10), PRINT)) == ["MECH-BED"]


def test_mesh_and_step_round_trip(tmp_path):
    from rccar_mech import export

    part = plate_with_hole()
    part.label = "plate"
    out = export.write_all(Compound(children=[part], label="t"), tmp_path, "t", stl_tolerance=0.01)
    assert checks.mesh(out["stl"]) == []
    assert checks.step_round_trip(Compound(children=[part], label="t"), out["step"]) == []


def test_round_trip_detects_a_different_file(tmp_path):
    from rccar_mech import export

    a = plate_with_hole()
    a.label = "plate"
    out = export.write_all(Compound(children=[a], label="t"), tmp_path, "t", stl_tolerance=0.01)
    b = Box(41, 20, 5)
    b.label = "plate"
    assert "MECH-STEP" in ids(checks.step_round_trip(Compound(children=[b], label="t"), out["step"]))
