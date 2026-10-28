"""Pure tuning core (no rclpy)."""
import importlib.util
from pathlib import Path

import pytest

from rccar_mcu_bridge import tuning as t

REPO = Path(__file__).resolve().parents[2]
TUNING = REPO / 'tuning.toml'
RCCAR_PY = REPO / 'tools' / 'rccar.py'


def test_firmware_keys_identical_to_tools_rccar():
    if not RCCAR_PY.exists():
        pytest.skip('tools/rccar.py not present (deleted after bench parity)')
    spec = importlib.util.spec_from_file_location('legacy_rccar', RCCAR_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert t.FIRMWARE_KEYS == mod.FIRMWARE_KEYS


def test_every_key_resolves_in_repo_tuning():
    if not TUNING.exists():
        pytest.skip('repo tuning.toml not found')
    tun = t.load_tuning(TUNING)
    for (table, key), _cmd in t.FIRMWARE_KEYS:
        t.tuning_value(tun, table, key)


def test_firmware_commands_formatting_and_order():
    tun = {'steering': {'heading_gain': 1.5, 'calibration': {'center_us': 1510}},
           'throttle': {'reverse_double_tap': True}}
    assert t.firmware_commands(tun) == [
        'CAL CENTER 1510', 'SET gain 1.5', 'SET revmode 1']


def test_firmware_commands_skips_missing_tables_and_keys():
    assert t.firmware_commands({}) == []
    assert t.firmware_commands({'steering': {'calibration': {}}}) == []


def test_firmware_commands_repo_file_all_present():
    if not TUNING.exists():
        pytest.skip('repo tuning.toml not found')
    cmds = t.firmware_commands(t.load_tuning(TUNING))
    assert len(cmds) == len(t.FIRMWARE_KEYS)
    assert cmds[0] == 'CAL CENTER 1500'
    assert all(len(c) <= 64 for c in cmds)


def test_update_tuning_file_keeps_comments(tmp_path):
    f = tmp_path / 'tuning.toml'
    f.write_text('[steering.calibration]\ncenter_us = 1500   # straight\nleft_us = 1200\n')
    t.update_tuning_file({'center_us': 1512}, f)
    assert f.read_text() == ('[steering.calibration]\n'
                             'center_us = 1512   # straight\nleft_us = 1200\n')


def test_update_tuning_file_missing_key(tmp_path):
    f = tmp_path / 'tuning.toml'
    f.write_text('a = 1\n')
    with pytest.raises(KeyError):
        t.update_tuning_file({'nope': 1}, f)


def test_parse_kv():
    assert t.parse_kv('CFG center=1500 gain=2.0 mode=x') == {
        'center': 1500.0, 'gain': 2.0, 'mode': 'x'}


def test_resolve_tuning_path_order(monkeypatch):
    monkeypatch.delenv('RCCAR_TUNING', raising=False)
    assert t.resolve_tuning_path('') == Path('/ws/src/racecar/tuning.toml')
    monkeypatch.setenv('RCCAR_TUNING', '/env/t.toml')
    assert t.resolve_tuning_path('') == Path('/env/t.toml')
    assert t.resolve_tuning_path('/param/t.toml') == Path('/param/t.toml')
