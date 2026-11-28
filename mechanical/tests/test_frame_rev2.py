"""Frame rev2: a one-piece deck on the front body posts and a snap anchor on the motor plate."""

import math

import pytest

from rccar_mech import checks, cli, kicad, models, params

MODEL = "frame_rev2"


@pytest.fixture(scope="module")
def frame():
    return models.build(MODEL)


@pytest.fixture(scope="module")
def hw():
    return params.load_facts(params.config_path("hardware.toml"))


@pytest.fixture(scope="module")
def pr():
    return params.load_facts(params.config_path("print.toml"))


def _part(asm, label):
    return next(p for p in checks.parts(asm) if p.label == label)


def _printed(asm):
    return [p for p in checks.parts(asm) if not models.is_ref(p)]


def _turn(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def _vertical_holes(shapes, d):
    return [h for s in shapes for h in checks.holes(s) if abs(h.diameter - d) < 1e-3 and abs(abs(h.axis[2]) - 1) < 1e-6]


def test_parts_and_labels(frame):
    asm, _ = frame
    labels = {p.label for p in checks.parts(asm)}
    assert {p.label for p in _printed(asm)} == {"deck", "anchor"}
    assert {"ref_pcb_rev3", "ref_pi5", "ref_mapper", "ref_battery", "ref_battery_holder"} <= labels
    assert checks.labels(asm) == []


def test_acceptance_passes(frame):
    asm, cfg = frame
    assert models.acceptance(MODEL, asm, cfg) == []


def test_deck_is_one_piece_on_the_bed(frame, pr):
    asm, _ = frame
    deck = _part(asm, "deck")
    assert len(deck.solids()) == 1
    for p in _printed(asm):
        assert checks.bed_fit(p, pr) == []


def test_pcb_inserts_line_up_with_the_board_holes(frame, hw):
    """Independent calculation: board holes from the KiCad file, turned and moved by the frame parameters."""
    asm, cfg = frame
    board = kicad.read_board(params.repo_path(hw["pcb_rev3"]["board"]))
    want = sorted(
        (round(cfg["pcb_x"] + x, 3), round(cfg["pcb_y"] + y, 3))
        for x, y in (_turn(h.x, h.y, cfg["pcb_rot"]) for h in board.holes)
    )
    got = sorted(
        (round(h.x, 3), round(h.y, 3)) for h in _vertical_holes(_printed(asm), hw["fasteners"]["m3_insert_hole"])
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
    got = sorted((round(h.x, 3), round(h.y, 3)) for h in _vertical_holes(_printed(asm), hw["fasteners"]["m25_pilot"]))
    assert got == want


def test_post_holes_only_at_the_front_posts(frame, hw, pr):
    asm, cfg = frame
    bp = hw["body_posts"]
    d = bp["diameter"] + 2 * cfg["post_clearance"] + pr["limits"]["hole_comp"]
    # the deck only: the anchor counterbores can have the same diameter
    got = sorted((round(h.x, 3), round(h.y, 3)) for h in _vertical_holes([_part(asm, "deck")], d))
    sx, sy = bp["spacing_x"] / 2, bp["spacing_y"] / 2
    assert got == [(sx, -sy), (sx, sy)]


def test_anchor_screw_holes_on_the_motor_plate_pattern(frame, hw, pr):
    asm, _ = frame
    mp, pos = hw["motor_plate"], hw["motor_plate_position"]
    d = mp["clearance_d"] + pr["limits"]["hole_comp"]
    half = mp["pattern"] / 2
    want = sorted((pos["x"] + sx * half, pos["y"] + sy * half) for sx in (-1, 1) for sy in (-1, 1))
    got = sorted((round(h.x, 3), round(h.y, 3)) for h in _vertical_holes([_part(asm, "anchor")], d))
    assert got == want


def test_deck_rests_on_the_stays_and_the_anchor(frame, hw):
    asm, _ = frame
    z0 = hw["body_posts"]["base_z"]
    deck, anchor = _part(asm, "deck").bounding_box(), _part(asm, "anchor").bounding_box()
    assert deck.min.Z == pytest.approx(z0)
    assert anchor.min.Z == pytest.approx(hw["motor_plate_position"]["top_z"])
    # the anchor body ends at the deck bottom: only the snap pin goes through the deck
    top_body = [f for f in _part(asm, "anchor").faces() if abs(f.normal_at().Z - 1) < 1e-6 and f.area > 100]
    assert top_body and all(f.center().Z == pytest.approx(z0) for f in top_body)


def test_snap_pin_goes_through_the_deck_and_latches(frame, hw):
    asm, cfg = frame
    z_deck_top = hw["body_posts"]["base_z"] + cfg["deck_thickness"]
    anchor, deck = _part(asm, "anchor"), _part(asm, "deck")
    assert anchor.bounding_box().max.Z == pytest.approx(z_deck_top + cfg["snap_lip"] + cfg["snap_lead_h"])
    # no overlap of the pin and the deck slot (checked by MECH-INTERFERE too), and the lip reaches over the slot edge
    assert anchor.intersect(deck) is None or sum(s.volume for s in anchor.intersect(deck)) < 1e-3
    assert cfg["snap_lip"] > cfg["snap_clearance"]


def test_snap_strain_limit_is_checked():
    """A larger lip bends the prongs more: the acceptance must report the strain above the material limit."""
    asm, cfg = models.build(MODEL, overrides={"snap_lip": 2.0})
    assert "MECH-SNAP" in {f.id for f in models.acceptance(MODEL, asm, cfg)}


def test_snap_pin_leaves_room_under_the_boards():
    asm, cfg = models.build(MODEL, overrides={"pcb_standoff_h": 6.0})
    found = models.acceptance(MODEL, asm, cfg)
    assert any(f.id == "MECH-CLEAR" and "snap pin" in f.where for f in found)


def test_anchor_stays_clear_of_the_battery(frame, hw):
    asm, cfg = frame
    anchor = _part(asm, "anchor")
    for label in ("ref_battery", "ref_battery_holder"):
        assert anchor.distance_to(_part(asm, label)) >= cfg["clearance_min"] - 1e-6
    # lift-out path: the anchor stays on the car, so it must not be above the battery footprint
    a, b = anchor.bounding_box(), _part(asm, "ref_battery").bounding_box()
    assert a.max.Y < b.min.Y or a.min.Y > b.max.Y or a.max.X < b.min.X or a.min.X > b.max.X


def test_wheels_stay_clear(frame):
    asm, cfg = frame
    wheels = [p for p in checks.parts(asm) if p.label.startswith("ref_wheel_")]
    assert len(wheels) == 4
    for w in wheels:
        for label in ("deck", "anchor", "ref_pcb_rev3", "ref_pi5"):
            assert _part(asm, label).distance_to(w) >= cfg["clearance_min"] - 1e-6, (w.label, label)


def test_unknown_interface_is_rejected():
    with pytest.raises(params.ParamError):
        models.build(MODEL, overrides={"chassis_interface": "glue"})


def test_cli_check(tmp_path):
    assert cli.main(["build", MODEL, "--out", str(tmp_path), "--no-previews"]) == 0
    assert cli.main(["check", MODEL, "--out", str(tmp_path)]) == 0
