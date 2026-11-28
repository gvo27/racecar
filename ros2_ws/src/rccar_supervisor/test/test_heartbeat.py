"""Heartbeat-file helper."""
import os

from rccar_supervisor.heartbeat import touch


def test_disabled_when_empty(tmp_path):
    assert touch('') is False


def test_creates_dirs_and_refreshes(tmp_path):
    path = tmp_path / 'hb' / 'supervisor'
    assert touch(str(path)) is True
    os.utime(path, (0, 0))
    assert touch(str(path)) is True
    assert path.stat().st_mtime > 1


def test_unwritable_path_does_not_raise():
    assert touch('/proc/nope/hb') is False
