"""Pure helpers for the calibration CLIs."""
import pytest

from rccar_calibration import helpers as h


def test_clamp():
    assert h.clamp_us(100) == 500
    assert h.clamp_us(9999) == 2500
    assert h.clamp_us(1500) == 1500


@pytest.mark.parametrize('text,us,kind,new_us', [
    ('+10', 1500, 'move', 1510),
    ('-2', 1500, 'move', 1498),
    ('=1620', 1500, 'move', 1620),
    ('=99999', 1500, 'move', 2500),
])
def test_parse_moves(text, us, kind, new_us):
    a = h.parse_command(text, us)
    assert (a.kind, a.us) == (kind, new_us)


@pytest.mark.parametrize('text', ['center', 'LEFT', 'right'])
def test_parse_store(text):
    a = h.parse_command(text, 1500)
    assert a.kind == 'store' and a.name == text.lower()


def test_parse_set():
    a = h.parse_command('maxdeg 31.5', 1500)
    assert (a.kind, a.name, a.value) == ('set', 'maxdeg', 31.5)
    a = h.parse_command('gain 2', 1500)
    assert (a.kind, a.name, a.value) == ('set', 'gain', 2.0)


@pytest.mark.parametrize('text,kind', [
    ('show', 'show'), ('save', 'save'), ('q', 'quit'), ('quit', 'quit'),
    ('exit', 'quit'), ('', 'help'), ('wat', 'help'), ('maxdeg', 'help'),
    ('gain abc', 'help'), ('+', 'help'), ('=x', 'help'),
])
def test_parse_misc(text, kind):
    assert h.parse_command(text, 1500).kind == kind


def test_toml_names_and_point_ids():
    assert h.CAL_TO_TOML == {'center': 'center_us', 'left': 'left_us', 'right': 'right_us',
                             'maxdeg': 'max_steer_deg', 'gain': 'heading_gain'}
    assert h.CAL_POINT_IDS == {'left': 0, 'center': 1, 'right': 2}


def test_sweep_plan():
    plan = h.sweep_plan(1500, 1200, 1800)
    assert [p[1] for p in plan] == [1500, 1200, 1500, 1800, 1500]
    assert all(500 <= us <= 2500 for _, us in plan)


def test_sweep_plan_from_tuning_uses_calibration():
    t = {'steering': {'calibration': {'center_us': 1510, 'left_us': 1210, 'right_us': 1790}}}
    assert h.sweep_from_tuning(t)[1][1] == 1210
    with pytest.raises(KeyError):
        h.sweep_from_tuning({})


@pytest.mark.parametrize('timeout_ms,hz,ok', [(300, 20, True), (90, 20, False), (150, 20, True)])
def test_timeout_margin(timeout_ms, hz, ok):
    # rule from tuning.toml: timeout >= 2 x period is the minimum we accept; 3x preferred
    assert h.timeout_margin_ok(timeout_ms, hz, factor=2.0) is ok


def test_timeout_margin_preferred_3x():
    assert h.timeout_margin_ok(300, 20, factor=3.0) is True
    assert h.timeout_margin_ok(140, 20, factor=3.0) is False


def test_missing_points_report():
    assert h.missing_points({'center'}) == ['left', 'right']
    assert h.missing_points({'center', 'left', 'right'}) == []
