"""tuning.toml -> node parameter dicts (pure)."""
from pathlib import Path

from rccar_bringup.tuning_params import node_params
import tomllib

# repo root: the first parent with tuning.toml and ros2_ws/ (ros.Dockerfile copies both)
REPO = next((d for d in Path(__file__).resolve().parents
             if (d / 'tuning.toml').is_file() and (d / 'ros2_ws').is_dir()), None)


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
    assert REPO, 'tuning.toml not found in a parent of %s (ros.Dockerfile COPY?)' % __file__
    path = REPO / 'tuning.toml'
    with open(path, 'rb') as f:
        p = node_params(tomllib.load(f))
    assert p['supervisor']['send_hz'] == 20.0
