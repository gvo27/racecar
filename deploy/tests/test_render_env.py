"""deploy/render_env.py: .env + tuning.toml [platform.*] -> .env.generated (no hardware, no docker)."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_env as r  # noqa: E402

TUNING = {'platform': {'pi5': {'esp32_device': '/dev/rccar-esp32', 'arch': 'arm64'}}}


def _render(env, tuning=TUNING):
    return r.render(env, tuning, '/home/pi/ros2_ws/src/racecar', 1000, 1001, 20)


def test_parse_env_comments_quotes_and_blank():
    text = '# c\nTZ=Europe/Berlin   # zone\n\nTS_DOMAIN=\nX="a # b"\nexport Y=1\n'
    assert r.parse_env(text) == {'TZ': 'Europe/Berlin', 'TS_DOMAIN': '', 'X': 'a # b', 'Y': '1'}


def test_parse_env_rejects_garbage():
    with pytest.raises(r.ConfigError):
        r.parse_env('not a pair')
    with pytest.raises(r.ConfigError):
        r.parse_env('1BAD=x')


def test_render_defaults_and_platform():
    v = _render({'PLATFORM': 'pi5'})
    assert v['ESP32_DEVICE'] == '/dev/rccar-esp32'
    assert v['ROS_DOMAIN_ID'] == '0'
    assert v['TZ'] == 'UTC'
    assert v['RCCAR_ROS_IMAGE'] == 'rccar-ros:local'
    assert (v['HOST_UID'], v['HOST_GID'], v['DIALOUT_GID']) == ('1000', '1001', '20')
    assert v['REPO_DIR'] == '/home/pi/ros2_ws/src/racecar'


def test_render_env_overrides():
    v = _render({'PLATFORM': 'pi5', 'ROS_DOMAIN_ID': '42', 'TZ': 'Europe/Berlin',
                 'RCCAR_ROS_IMAGE': 'ghcr.io/x/rccar-ros:abc123'})
    assert (v['ROS_DOMAIN_ID'], v['TZ'], v['RCCAR_ROS_IMAGE']) == (
        '42', 'Europe/Berlin', 'ghcr.io/x/rccar-ros:abc123')


@pytest.mark.parametrize('domain', ['-1', '102', 'abc', '1.5'])
def test_render_rejects_bad_domain(domain):
    with pytest.raises(r.ConfigError, match='ROS_DOMAIN_ID'):
        _render({'PLATFORM': 'pi5', 'ROS_DOMAIN_ID': domain})


def test_render_unknown_or_empty_platform():
    with pytest.raises(r.ConfigError, match='no .platform.nope'):
        _render({'PLATFORM': 'nope'})
    with pytest.raises(r.ConfigError, match='PLATFORM is empty'):
        _render({})


def test_render_requires_device_path():
    with pytest.raises(r.ConfigError, match='esp32_device'):
        _render({'PLATFORM': 'pi5'}, {'platform': {'pi5': {'arch': 'arm64'}}})


def test_format_quotes_values_with_spaces():
    out = r.format_env({'A': '1', 'REPO_DIR': '/home/a b/x'})
    assert 'A=1\n' in out and 'REPO_DIR="/home/a b/x"\n' in out


def test_repo_tuning_has_confirmed_pi5_platform():
    import tomllib
    with open(Path(__file__).resolve().parents[2] / 'tuning.toml', 'rb') as f:
        tun = tomllib.load(f)
    assert set(tun['platform']['pi5']) == {'esp32_device', 'arch'}
    assert _render({'PLATFORM': 'pi5'}, tun)['ESP32_DEVICE'] == '/dev/rccar-esp32'


def test_main_missing_env_has_hint(tmp_path, capsys):
    rc = r.main(['--env', str(tmp_path / '.env'), '--out', str(tmp_path / 'o')])
    assert rc == 1
    assert 'cp .env.example .env' in capsys.readouterr().err


def test_main_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(r, 'dialout_gid', lambda: 20)
    env = tmp_path / '.env'
    env.write_text('PLATFORM=pi5\nROS_DOMAIN_ID=7  # x\n')
    out = tmp_path / 'sub' / '.env.generated'
    assert r.main(['--env', str(env), '--out', str(out), '--repo-dir', '/r']) == 0
    text = out.read_text()
    assert 'ROS_DOMAIN_ID=7\n' in text and 'REPO_DIR=/r\n' in text and 'DIALOUT_GID=20\n' in text


def test_main_dialout_gid_arg(tmp_path, monkeypatch):
    def boom():
        raise AssertionError('group lookup must not run when --dialout-gid is given')
    monkeypatch.setattr(r, 'dialout_gid', boom)
    env = tmp_path / '.env'
    env.write_text('PLATFORM=pi5\n')
    out = tmp_path / '.env.generated'
    assert r.main(['--env', str(env), '--out', str(out), '--repo-dir', '/r', '--dialout-gid', '994']) == 0
    assert 'DIALOUT_GID=994\n' in out.read_text()
