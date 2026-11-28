"""Hardware facts, the KiCad board reader and the reference envelopes."""

import pytest
from build123d import Compound

from rccar_mech import checks, kicad, params, refs


@pytest.fixture(scope="module")
def hw():
    return params.load_facts(params.config_path("hardware.toml"))


@pytest.fixture(scope="module")
def board(hw):
    return kicad.read_board(params.repo_path(hw["pcb_rev3"]["board"]))


def test_hardware_file_loads(hw):
    assert hw["pi5"]["status"] == "confirmed"
    assert "body_posts" in params.assumed(hw)


def test_rev3_outline_and_holes(board):
    assert (board.width, board.height) == pytest.approx((66.0, 140.0))
    assert len(board.holes) == 4
    # footprint MountingHole_3.2mm_M3, drill 3.4 in the board file (snapped to the lab drill set)
    assert {round(h.d, 3) for h in board.holes} == {3.4}
    xs = sorted({round(h.x, 3) for h in board.holes})
    ys = sorted({round(h.y, 3) for h in board.holes})
    # board-centered, y up: 59 x 133 mm pattern, symmetric about the center
    assert xs == [-29.5, 29.5] and ys == [-66.5, 66.5]


def test_reader_flips_kicad_y(tmp_path):
    p = tmp_path / "b.kicad_pcb"
    p.write_text(
        '(kicad_pcb (gr_rect (start 0 0) (end 20 10) (layer "Edge.Cuts"))\n'
        '(footprint "MountingHole:MountingHole_3.2mm_M3" (layer "F.Cu") (at 5 2)\n'
        '  (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) (layers "*.Cu")))\n)\n'
    )
    b = kicad.read_board(p)
    assert (b.width, b.height) == (20.0, 10.0)
    # KiCad (5, 2) with y down -> centered (-5, +3) with y up
    assert (b.holes[0].x, b.holes[0].y) == pytest.approx((-5.0, 3.0))


def test_reader_rejects_a_board_without_outline(tmp_path):
    p = tmp_path / "b.kicad_pcb"
    p.write_text("(kicad_pcb)\n")
    with pytest.raises(ValueError):
        kicad.read_board(p)


def test_pcb_ref_has_the_board_holes(hw, board):
    r = refs.pcb_rev3(hw, board)
    assert r.label == "ref_pcb_rev3"
    bb = r.bounding_box().size
    t = hw["pcb_rev3"]["thickness"]
    assert (bb.X, bb.Y) == pytest.approx((66.0, 140.0))
    assert bb.Z == pytest.approx(t + hw["pcb_rev3_heights"]["top"])
    expect = [(h.x, h.y, h.d) for h in board.holes]
    assert checks.expect_holes(r, expect) == []


def test_pi5_ref_has_the_hole_pattern(hw):
    r = refs.pi5(hw)
    p = hw["pi5"]
    bb = r.bounding_box().size
    assert bb.X == pytest.approx(p["length"] + p["port_overhang"])
    assert bb.Y == pytest.approx(p["width"])
    holes = checks.holes(r)
    assert len(holes) == 4 and {round(h.diameter, 3) for h in holes} == {p["hole_d"]}
    xs = sorted({round(h.x, 3) for h in holes})
    ys = sorted({round(h.y, 3) for h in holes})
    assert xs[1] - xs[0] == pytest.approx(p["hole_dx"]) and ys[1] - ys[0] == pytest.approx(p["hole_dy"])


def test_chassis_refs_are_at_the_car_positions(hw):
    parts = refs.chassis(hw)
    labels = sorted(p.label for p in parts)
    assert labels == [
        "ref_battery",
        "ref_battery_holder",
        "ref_body_post_fl",
        "ref_body_post_fr",
        "ref_body_post_rl",
        "ref_body_post_rr",
    ]
    bp = hw["body_posts"]
    post = next(p for p in parts if p.label == "ref_body_post_fl")
    c = post.bounding_box().center()
    assert (c.X, c.Y) == pytest.approx((bp["spacing_x"] / 2, bp["spacing_y"] / 2))
    assert post.bounding_box().min.Z == pytest.approx(bp["base_z"])
    holder = next(p for p in parts if p.label == "ref_battery_holder")
    assert holder.bounding_box().max.Z == pytest.approx(hw["battery_holder"]["pin_top_z"])
    assert checks.interference(parts) == []
    assert checks.labels(Compound(children=parts)) == []
