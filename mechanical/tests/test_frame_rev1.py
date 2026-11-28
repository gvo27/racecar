"""Frame rev1: the board and Pi holes line up, the chassis interface is replaceable, the battery holder stays free."""

import math

import pytest

from rccar_mech import checks, cli, kicad, models, params


@pytest.fixture(scope="module")
def frame():
    return models.build("frame_rev1")


@pytest.fixture(scope="module")
def hw():
    return params.load_facts(params.config_path("hardware.toml"))


def _part(asm, label):
    return next(p for p in checks.parts(asm) if p.label == label)


def _turn(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def _vertical_holes(shape, d):
    return [h for h in checks.holes(shape) if abs(h.diameter - d) < 1e-3 and abs(abs(h.axis[2]) - 1) < 1e-6]


def test_parts_and_labels(frame):
    asm, _ = frame
    labels = {p.label for p in checks.parts(asm)}
    assert {"deck_front", "deck_rear", "splice"} <= labels
    assert {"ref_pcb_rev3", "ref_pi5", "ref_mapper", "ref_battery", "ref_battery_holder"} <= labels
    assert checks.labels(asm) == []


def test_acceptance_passes(frame):
    asm, cfg = frame
    assert models.acceptance("frame_rev1", asm, cfg) == []


def test_pcb_inserts_line_up_with_the_board_holes(frame, hw):
    """Independent calculation: board holes from the KiCad file, turned and moved by the frame parameters."""
    asm, cfg = frame
    board = kicad.read_board(params.repo_path(hw["pcb_rev3"]["board"]))
    want = sorted(
        (round(cfg["pcb_x"] + x, 3), round(cfg["pcb_y"] + y, 3))
        for x, y in (_turn(h.x, h.y, cfg["pcb_rot"]) for h in board.holes)
    )
    printed = [p for p in checks.parts(asm) if not models.is_ref(p)]
    got = sorted(
        (round(h.x, 3), round(h.y, 3)) for p in printed for h in _vertical_holes(p, hw["fasteners"]["m3_insert_hole"])
    )
    assert got == want


def test_pi_screw_holes_line_up(frame, hw):
    asm, cfg = frame
    p = hw["pi5"]
    x0, y0 = -p["length"] / 2 + p["hole_inset"], -p["width"] / 2 + p["hole_inset"]
    local = [(x0 + i * p["hole_dx"], y0 + j * p["hole_dy"]) for i in (0, 1) for j in (0, 1)]
    want = sorted(
        (round(cfg["pi_x"] + x, 3), round(cfg["pi_y"] + y, 3)) for x, y in (_turn(*q, cfg["pi_rot"]) for q in local)
    )
    printed = [q for q in checks.parts(asm) if not models.is_ref(q)]
    got = sorted(
        (round(h.x, 3), round(h.y, 3)) for q in printed for h in _vertical_holes(q, hw["fasteners"]["m25_pilot"])
    )
    assert got == want


def test_post_holes_at_the_body_posts(frame, hw):
    asm, cfg = frame
    bp = hw["body_posts"]
    pr = params.load_facts(params.config_path("print.toml"))
    d = bp["diameter"] + 2 * cfg["post_clearance"] + pr["limits"]["hole_comp"]
    printed = [p for p in checks.parts(asm) if not models.is_ref(p)]
    got = sorted((round(h.x, 3), round(h.y, 3)) for p in printed for h in _vertical_holes(p, d))
    sx, sy = bp["spacing_x"] / 2, bp["spacing_y"] / 2
    assert got == sorted((x, y) for x in (-sx, sx) for y in (-sy, sy))


def test_deck_sits_on_the_post_stays_above_the_holder(frame, hw):
    asm, cfg = frame
    deck = _part(asm, "deck_front")
    assert deck.bounding_box().min.Z == pytest.approx(hw["body_posts"]["base_z"])
    holder = _part(asm, "ref_battery_holder")
    for label in ("deck_front", "deck_rear", "splice"):
        assert _part(asm, label).distance_to(holder) >= cfg["clearance_min"] - 1e-6


def test_halves_fit_the_bed(frame):
    asm, _ = frame
    pr = params.load_facts(params.config_path("print.toml"))
    for label in ("deck_front", "deck_rear", "splice"):
        assert checks.bed_fit(_part(asm, label), pr) == []


def test_screw_pad_interface_is_a_drop_in(hw):
    asm, cfg = models.build("frame_rev1", overrides={"chassis_interface": "screw_pads"})
    assert models.acceptance("frame_rev1", asm, cfg) == []
    printed = [p for p in checks.parts(asm) if not models.is_ref(p)]
    bp = hw["body_posts"]
    pr = params.load_facts(params.config_path("print.toml"))
    d = cfg["pad_screw_d"] + pr["limits"]["hole_comp"]
    sx = hw["body_posts"]["spacing_x"] / 2
    # only the holes at the post positions (the splice bolts can have the same diameter)
    at_posts = [h for p in printed for h in _vertical_holes(p, d) if abs(abs(h.x) - sx) < 1e-6]
    got = sorted((round(h.x, 3), round(h.y, 3)) for h in at_posts)
    sx, sy = bp["spacing_x"] / 2, bp["spacing_y"] / 2
    assert got == sorted((x, y) for x in (-sx, sx) for y in (-sy, sy))


def test_unknown_interface_is_rejected():
    with pytest.raises(params.ParamError):
        models.build("frame_rev1", overrides={"chassis_interface": "glue"})


def test_moving_the_pcb_moves_its_inserts():
    asm, cfg = models.build("frame_rev1", overrides={"pcb_x": -10.0})
    assert models.acceptance("frame_rev1", asm, cfg) == []


def test_cli_check_frame(tmp_path):
    assert cli.main(["build", "frame_rev1", "--out", str(tmp_path), "--no-previews"]) == 0
    assert cli.main(["check", "frame_rev1", "--out", str(tmp_path)]) == 0


def test_split_keeps_the_features_above_the_plate(frame, hw):
    asm, cfg = frame
    ztop = hw["body_posts"]["base_z"] + cfg["deck_thickness"]
    front = _part(asm, "deck_front")
    assert front.bounding_box().max.Z == pytest.approx(ztop + cfg["camera_block_size"][2])


def test_wheels_stay_clear(frame, hw):
    asm, cfg = frame
    wheels = [p for p in checks.parts(asm) if p.label.startswith("ref_wheel_")]
    assert len(wheels) == 4
    # rear wheels on the wheelbase, centered between the posts
    rear = [w for w in wheels if w.bounding_box().center().X < 0]
    assert rear[0].bounding_box().center().X == pytest.approx(-hw["tt02"]["wheelbase"] / 2)
    for w in wheels:
        for label in ("deck_front", "deck_rear", "splice", "ref_pcb_rev3", "ref_pi5"):
            assert _part(asm, label).distance_to(w) >= cfg["clearance_min"] - 1e-6, (w.label, label)


def test_clip_access_at_the_posts(frame):
    """Room for a hand and a body clip next to each post, above the deck."""
    asm, cfg = frame
    posts = [p for p in checks.parts(asm) if p.label.startswith("ref_body_post_")]
    for post in posts:
        for label in ("ref_mapper", "ref_pcb_rev3", "ref_pi5"):
            assert _part(asm, label).distance_to(post) >= cfg["clip_clearance"] - 1e-6, (post.label, label)


def test_bolt_heads_leave_room_under_the_boards(frame, hw):
    asm, cfg = frame
    f = hw["fasteners"]
    for standoff, bottom in (
        (cfg["pcb_standoff_h"], hw["pcb_rev3_heights"]["bottom"]),
        (cfg["pi_standoff_h"], hw["pi5_heights"]["bottom"]),
    ):
        assert standoff - bottom - f["m3_head_h"] >= cfg["clearance_min"] - 1e-6
    heads = _part(asm, "ref_fasteners")
    assert heads.distance_to(_part(asm, "ref_battery_holder")) >= cfg["clearance_min"] - 1e-6
