"""Frame rev2: a one-piece deck on the front body posts and a snap anchor on the motor plate."""

import math

import pytest
from build123d import Box, Compound, Pos

from rccar_mech import checks, cli, kicad, models, params
from rccar_mech.parts import anchor as anchor_part

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


def _y_reach(shape, z, center_y):
    """Largest |y - center_y| of the shape in a thin horizontal cut at height z."""
    cut = shape & (Pos(0, center_y, z) * Box(1000, 100, 0.02))
    bb = (cut if not isinstance(cut, list) else Compound(cut)).bounding_box()
    return max(bb.max.Y - center_y, center_y - bb.min.Y)


def test_snap_lip_latches_at_the_deck_top(frame, hw, pr):
    """The lip is inside the deck slot below the deck top and reaches over the slot edge just above it."""
    asm, cfg = frame
    z_top = hw["body_posts"]["base_z"] + cfg["deck_thickness"]
    ay = hw["motor_plate_position"]["y"]
    half_slot = cfg["snap_pin_d"] / 2 + cfg["snap_clearance"] + pr["limits"]["hole_comp"] / 2
    anchor = _part(asm, "anchor")
    assert _y_reach(anchor, z_top - 0.05, ay) <= half_slot + 1e-6
    assert _y_reach(anchor, z_top + 0.2, ay) > half_slot + 0.1
    assert checks.interference([anchor, _part(asm, "deck")]) == []


def test_prong_strain_hand_value():
    """Circular segment r 4 cut at y 1: centroid 2.249, far fiber 1.751. Bend 0.4 mm over 11 mm."""
    assert anchor_part.prong_strain(4.0, 1.0, 0.4, 11.0) == pytest.approx(3 * 0.4 * 1.751 / 121, rel=1e-3)


def test_snap_strain_limit_is_checked():
    """A larger lip bends the prongs more: the acceptance must report the strain above the material limit."""
    asm, cfg = models.build(MODEL, overrides={"snap_lip": 2.0})
    assert "MECH-SNAP" in {f.id for f in models.acceptance(MODEL, asm, cfg)}


def test_snap_pin_leaves_room_under_the_boards():
    asm, cfg = models.build(MODEL, overrides={"pcb_standoff_h": 6.0})
    found = models.acceptance(MODEL, asm, cfg)
    assert any(f.id == "MECH-CLEAR" and "snap pin" in f.where for f in found)


def test_anchor_is_not_in_the_battery_lift_out_path(frame):
    """The anchor stays on the car, so it must not be above the battery footprint (clearances: acceptance)."""
    asm, _ = frame
    a, b = _part(asm, "anchor").bounding_box(), _part(asm, "ref_battery").bounding_box()
    assert a.max.Y < b.min.Y or a.min.Y > b.max.Y or a.max.X < b.min.X or a.min.X > b.max.X


def test_shorter_deck_and_anchor_clear_the_wheels(frame):
    asm, cfg = frame
    wheels = [p for p in checks.parts(asm) if p.label.startswith("ref_wheel_")]
    assert len(wheels) == 4
    for w in wheels:
        for label in ("deck", "anchor"):
            assert _part(asm, label).distance_to(w) >= cfg["clearance_min"] - 1e-6, (w.label, label)


def test_unknown_interface_is_rejected():
    with pytest.raises(params.ParamError):
        models.build(MODEL, overrides={"chassis_interface": "glue"})


def test_cli_check(tmp_path):
    assert cli.main(["build", MODEL, "--out", str(tmp_path), "--no-previews"]) == 0
    assert cli.main(["check", MODEL, "--out", str(tmp_path)]) == 0


def test_lip_passes_the_round_slot_ends(frame, hw, pr):
    """The prongs bend only in Y. In X the lip must stay inside the pin width, so it passes the slot end circles."""
    asm, cfg = frame
    z_top = hw["body_posts"]["base_z"] + cfg["deck_thickness"]
    ax = hw["motor_plate_position"]["x"] + cfg["snap_offset_x"]
    cut = _part(asm, "anchor") & (Pos(ax, 0, z_top + 0.3) * Box(100, 1000, 0.02))
    bb = (cut if not isinstance(cut, list) else Compound(cut)).bounding_box()
    assert max(bb.max.X - ax, ax - bb.min.X) <= cfg["snap_pin_d"] / 2 + 1e-6


def test_rev2_without_the_anchor_is_an_error():
    asm, cfg = models.build(MODEL, overrides={"chassis_interface": "body_posts"})
    assert "MECH-SNAP" in {f.id for f in models.acceptance(MODEL, asm, cfg)}


def test_bad_slot_width_is_rejected():
    with pytest.raises(params.ParamError):
        models.build(MODEL, overrides={"snap_slot_w": 8.0})


def _barrel_box(hw, grow=0.0, z_lo=None, z_hi=None):
    """The motor barrel envelope from the facts, larger by `grow` on each side in X and Y."""
    b, pos = hw["motor_barrel"], hw["motor_plate_position"]
    lo = pos["top_z"] if z_lo is None else z_lo
    hi = pos["top_z"] + b["height"] if z_hi is None else z_hi
    size = (b["length"] + 2 * grow, b["width"] + 2 * grow, hi - lo)
    return Pos(pos["x"], pos["y"], (lo + hi) / 2) * Box(*size)


def _volume(shape):
    if shape is None:
        return 0.0
    return sum(s.volume for s in shape) if isinstance(shape, list) else shape.volume


def test_motor_barrel_envelope_from_the_facts(frame, hw):
    asm, _ = frame
    b, pos = hw["motor_barrel"], hw["motor_plate_position"]
    bb = _part(asm, "ref_motor_barrel").bounding_box()
    assert (bb.center().X, bb.center().Y) == pytest.approx((pos["x"], pos["y"]))
    assert (bb.size.X, bb.size.Y) == pytest.approx((b["length"], b["width"]))
    assert (bb.min.Z, bb.max.Z) == pytest.approx((pos["top_z"], pos["top_z"] + b["height"]))


def test_barrel_stays_free(frame, hw):
    """The deck keeps clearance_min, the anchor its own gap, the boards room for their bottom parts."""
    asm, cfg = frame
    barrel = _part(asm, "ref_motor_barrel")
    assert _part(asm, "deck").distance_to(barrel) >= cfg["clearance_min"] - 1e-6
    assert _part(asm, "anchor").distance_to(barrel) >= cfg["anchor_barrel_gap"] - 1e-6
    for label, key in (("ref_pcb_rev3", "pcb_rev3_heights"), ("ref_pi5", "pi5_heights")):
        need = hw[key]["bottom"] + cfg["clearance_min"]
        assert _part(asm, label).distance_to(barrel) >= need - 1e-6, label


def test_anchor_is_a_u_open_to_the_rear(frame, hw):
    """No anchor material between the barrel and the rear end of the anchor, across the barrel width."""
    asm, cfg = frame
    b, pos = hw["motor_barrel"], hw["motor_plate_position"]
    x_rear = pos["x"] + cfg["anchor_x_min"] - 1
    x_barrel = pos["x"] - b["length"] / 2
    lane = Pos((x_rear + x_barrel) / 2, pos["y"], 45) * Box(x_barrel - x_rear, b["width"], 20)
    assert _volume(_part(asm, "anchor") & lane) < 1e-6
    # closed at the front: material in front of the barrel, across its width
    x_front = pos["x"] + b["length"] / 2 + cfg["anchor_barrel_gap"]
    bridge = Pos(x_front + 2, pos["y"], pos["top_z"] + 1) * Box(2, b["width"], 1)
    assert _volume(_part(asm, "anchor") & bridge) > 0


def test_deck_has_a_cutout_over_the_barrel(frame, hw):
    asm, cfg = frame
    z0 = hw["body_posts"]["base_z"]
    zone = _barrel_box(hw, grow=cfg["clearance_min"] - 0.01, z_lo=z0, z_hi=z0 + cfg["deck_thickness"])
    assert _volume(_part(asm, "deck") & zone) < 1e-6


def test_snap_pin_is_in_front_of_the_barrel(frame, hw):
    asm, cfg = frame
    pos = hw["motor_plate_position"]
    pin_d = cfg["snap_pin_d"] + 2 * cfg["snap_pocket_gap"]
    pocket = [h for h in checks.holes(_part(asm, "anchor")) if abs(h.diameter - pin_d) < 0.5]
    assert [(round(h.x, 3), round(h.y, 3)) for h in pocket] == [(pos["x"] + cfg["snap_offset_x"], pos["y"])]


def test_barrel_wider_than_the_u_is_rejected():
    """The U cutout is 14.2 mm: a 12 mm barrel with 1.2 mm gaps each side does not fit."""
    with pytest.raises(params.ParamError):
        models.build(MODEL, overrides={"anchor_barrel_gap": 1.2})


def test_web_to_the_snap_pin_is_guarded():
    """Moving the pin back toward the barrel leaves less than min_wall between the deck cutout and the snap slot."""
    with pytest.raises(params.ParamError):
        models.build(MODEL, overrides={"snap_offset_x": 22.0})
