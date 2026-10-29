"""tuning.toml -> node parameter dicts (pure)."""
from pathlib import Path

from rccar_bringup.tuning_params import node_params
import tomllib

REPO = Path(__file__).resolve().parents[2]


def test_send_hz_mapped_from_link():
    p = node_params({'link': {'send_hz': 20}})
    assert p['supervisor'] == {'send_hz': 20.0}


def test_only_present_keys_are_emitted():
    assert node_params({}) == {'supervisor': {}, 'mcu_bridge': {}}
    assert node_params({'link': {}, 'supervisor': {}})['supervisor'] == {}


def test_supervisor_table_mapped_when_present():
    p = node_params({'supervisor': {'admin_timeout_s': 0.25, 'captain_priority': 5,
                                    'unknown': 1}})
    assert p['supervisor'] == {'admin_timeout_s': 0.25, 'captain_priority': 5}


def test_mcu_bridge_save_after_push():
    p = node_params({'mcu_bridge': {'save_after_push': True}})
    assert p['mcu_bridge'] == {'save_after_push': True}


def test_repo_tuning_toml_maps_send_hz():
    path = REPO / 'tuning.toml'
    if not path.exists():
        return
    with open(path, 'rb') as f:
        p = node_params(tomllib.load(f))
    assert p['supervisor']['send_hz'] == 20.0
