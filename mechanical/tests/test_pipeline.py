"""End to end on the test bracket: build, acceptance, export, report, diff, CLI exit codes."""

import json

import pytest

from rccar_mech import checks, cli, diff, export, models


@pytest.fixture(scope="module")
def bracket():
    return models.build("test_bracket")


def test_model_registry():
    assert "test_bracket" in models.names()
    with pytest.raises(KeyError):
        models.build("nope")


def test_bracket_dimensions_and_holes(bracket):
    asm, cfg = bracket
    bb = asm.bounding_box().size
    assert (bb.X, bb.Y, bb.Z) == pytest.approx((cfg["length"], cfg["width"], cfg["thickness"]))
    assert len(asm.solids()) == 1
    assert models.acceptance("test_bracket", asm, cfg) == []


def test_parameter_change_moves_the_holes():
    asm, cfg = models.build("test_bracket", overrides={"hole_spacing": 30.0})
    assert models.acceptance("test_bracket", asm, cfg) == []
    xs = sorted(round(h.x, 3) for h in checks.holes(asm))
    assert xs == [-15.0, 15.0]


def test_export_writes_every_file(tmp_path, bracket):
    asm, _ = bracket
    out = export.write_all(asm, tmp_path, "test_bracket", stl_tolerance=0.01, previews=True)
    for key in ("step", "stl", "svg_top", "svg_front", "svg_side", "svg_iso", "png_iso"):
        assert out[key].exists() and out[key].stat().st_size > 0, key


def test_cli_build_and_check(tmp_path):
    assert cli.main(["build", "test_bracket", "--out", str(tmp_path)]) == 0
    assert cli.main(["check", "test_bracket", "--out", str(tmp_path)]) == 0
    rep = json.loads((tmp_path / "report.json").read_text())
    assert rep["model"] == "test_bracket"
    assert rep["errors"] == 0
    assert len(rep["holes"]) == 2
    assert rep["mass_g"] > 0
    assert "print.toml" in " ".join(rep["assumed"])


def test_cli_check_fails_on_a_stale_step(tmp_path):
    assert cli.main(["build", "test_bracket", "--out", str(tmp_path)]) == 0
    other = tmp_path / "other"
    assert cli.main(["build", "test_bracket", "--out", str(other), "--set", "length=50"]) == 0
    (other / "test_bracket.step").replace(tmp_path / "test_bracket.step")
    assert cli.main(["check", "test_bracket", "--out", str(tmp_path)]) == 1


def test_diff_reports_changes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    cli.main(["build", "test_bracket", "--out", str(a)])
    cli.main(["build", "test_bracket", "--out", str(b), "--set", "hole_spacing=30"])
    d = diff.diff(a / "test_bracket.step", b / "test_bracket.step")
    assert d["volume_delta"] == pytest.approx(0, abs=1e-3)
    assert len(d["holes_removed"]) == 2 and len(d["holes_added"]) == 2
    assert diff.diff(a / "test_bracket.step", a / "test_bracket.step")["same"]


def test_printed_copy_keeps_the_model_tree(bracket):
    asm, _ = bracket
    before = [p.label for p in checks.parts(asm)]
    pr = cli.printed(asm)
    assert [p.label for p in checks.parts(asm)] == before
    assert [p.label for p in checks.parts(pr)] == before
