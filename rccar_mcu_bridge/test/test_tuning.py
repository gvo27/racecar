"""Pure tuning core (no rclpy)."""
from pathlib import Path
import re

import pytest

from rccar_mcu_bridge import tuning as t

REPO = Path(__file__).resolve().parents[2]
TUNING = REPO / 'tuning.toml'
MAIN_CPP = REPO / 'firmware' / 'esp32' / 'src' / 'main.cpp'


def test_every_key_resolves_in_repo_tuning():
    if not TUNING.exists():
        pytest.skip('repo tuning.toml not found')
    tun = t.load_tuning(TUNING)
    for (table, key), _cmd in t.FIRMWARE_KEYS:
        t.tuning_value(tun, table, key)


def _firmware_source():
    if not MAIN_CPP.exists():
        if not TUNING.exists():
            pytest.skip('repo tree not found (installed-only tree)')
        pytest.fail('repo tree present but firmware/esp32/src/main.cpp missing '
                    '(ros.Dockerfile COPY / dockerignore?)')
    return MAIN_CPP.read_text()


def test_set_names_exist_in_firmware_setkey():
    src = _firmware_source()
    start = src.index('static bool setKey(')
    body = src[start:src.index('\n}\n', start)]
    fw_keys = set(re.findall(r'strcasecmp\(key,\s*"([^"]+)"\)', body))
    assert fw_keys, 'no strcasecmp(key, "...") found in setKey: pattern out of date?'
    wanted = {cmd.split()[1] for _k, cmd in t.FIRMWARE_KEYS if cmd.startswith('SET ')}
    assert wanted == fw_keys, 'FIRMWARE_KEYS SET names and main.cpp setKey keys differ'


def test_cal_points_handled_in_firmware_handleline():
    src = _firmware_source()
    start = src.index('static void handleLine(')
    body = src[start:src.index('\n}\n', start)]
    fw_points = set(re.findall(r'strcasecmp\(a1,\s*"([A-Z]+)"\)', body))
    wanted = {cmd.split()[1] for _k, cmd in t.FIRMWARE_KEYS if cmd.startswith('CAL ')}
    assert wanted == {'LEFT', 'CENTER', 'RIGHT'}
    assert wanted <= fw_points, 'CAL point missing in main.cpp handleLine'


def test_all_commands_are_set_or_cal():
    assert all(cmd.split()[0] in ('SET', 'CAL') for _k, cmd in t.FIRMWARE_KEYS)


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
