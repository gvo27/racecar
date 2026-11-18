"""scripts/plugins_reset.py removes the session-only plugin enables (local scope) and keeps all other local settings."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('plugins_reset', ROOT / 'scripts' / 'plugins_reset.py')
plugins_reset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugins_reset)


def write(tmp_path, data):
    path = tmp_path / 'settings.local.json'
    path.write_text(json.dumps(data))
    return path


def test_removes_enabled_plugins_and_keeps_other_keys(tmp_path):
    path = write(tmp_path, {'enabledPlugins': {'plugin-dev@x': True, 'kicad-happy@kicad-happy': False},
                            'permissions': {'allow': ['Bash(ls)']}})
    removed = plugins_reset.reset(path)
    assert removed == ['kicad-happy@kicad-happy', 'plugin-dev@x']
    assert json.loads(path.read_text()) == {'permissions': {'allow': ['Bash(ls)']}}


def test_no_file_or_no_plugins_changes_nothing(tmp_path):
    assert plugins_reset.reset(tmp_path / 'missing.json') == []
    path = write(tmp_path, {'permissions': {}})
    before = path.read_text()
    assert plugins_reset.reset(path) == []
    assert path.read_text() == before


def test_unreadable_file_is_not_changed(tmp_path):
    path = tmp_path / 'settings.local.json'
    path.write_text('{not json')
    assert plugins_reset.reset(path) == []
    assert path.read_text() == '{not json'
