"""Guard hook .claude/hooks/hw_guard.py: command classification + path rules (no docker needed)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

HOOK = Path(__file__).resolve().parents[2] / '.claude' / 'hooks' / 'hw_guard.py'
spec = importlib.util.spec_from_file_location('hw_guard', HOOK)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


@pytest.mark.parametrize('cmd', [
    'make car-up', 'make drivers-start', 'make install-host', 'make flash',
    'make flash FW_ENV=esp32s3', 'make car-shutdown',
    'cd /x && make car-up', 'make config; make car-up', 'make car-down && make car-up',
    'FOO=1 make drivers-start', 'sudo make install-host',
    'docker compose up -d', 'docker compose -f deploy/car/compose.yaml --env-file e up -d drivers',
    'docker compose restart drivers', 'docker compose start', 'docker-compose up',
    'docker restart rccar-drivers-1', 'docker start x', 'docker container restart x',
    'sudo systemctl restart rccar.service', 'systemctl start rccar', 'systemctl enable rccar',
    'systemctl reboot', 'sudo reboot', 'poweroff', 'sudo shutdown -h now', 'halt',
    'bash -c "make car-up"', 'sh -c \'echo hi && docker compose up -d\'',
    'echo x | sudo env A=1 reboot', 'make -j2 car-up',
])
def test_ask(cmd):
    assert g.classify(cmd) == 'ask', cmd


@pytest.mark.parametrize('cmd', [
    'make drivers-stop', 'make car-down', 'docker compose stop', 'docker compose stop drivers',
    'docker compose -f deploy/car/compose.yaml stop drivers', 'docker stop x',
    'make lidar-hw-test', 'make ros-test', 'make unit', 'make car-ps',
    'git status', 'ls -la', 'echo "make car-up"', 'grep car-up Makefile',
    'systemctl status rccar', 'systemctl start nginx', 'docker ps', 'docker compose ps',
    'docker compose run --rm tools bash', 'make config', '',
])
def test_allow(cmd):
    assert g.classify(cmd) == 'allow', cmd


def test_build_detection():
    assert g.is_build('make ros-image')
    assert g.is_build('make setup')
    assert g.is_build('docker build -f docker/ros.Dockerfile .')
    assert g.is_build('docker compose build')
    assert not g.is_build('make ros-test')
    assert not g.is_build('make drivers-stop')


@pytest.mark.parametrize('path,expected', [
    ('rccar_drivers/rccar_drivers/mapper_node.py', True),
    ('rccar_description/urdf/rccar.urdf.xacro', True),
    ('docker/ros.Dockerfile', True),
    ('./rccar_drivers/setup.py', True),
    ('rccar_bringup/launch/drivers.launch.py', False),
    ('docs/setup.md', False),
    ('docker/firmware.Dockerfile', False),
    ('rccar_drivers_extra/x.py', False),
    ('', False),
])
def test_is_driver_path(path, expected):
    assert g.is_driver_path(path) is expected


def test_is_driver_path_absolute(tmp_path):
    root = str(tmp_path)
    assert g.is_driver_path(root + '/rccar_drivers/a.py', root)
    assert not g.is_driver_path(root + '/docs/a.md', root)
    assert not g.is_driver_path('/etc/passwd', root)


def test_decide():
    bash = lambda c: {'tool_name': 'Bash', 'tool_input': {'command': c}}  # noqa: E731
    edit = lambda p: {'tool_name': 'Edit', 'tool_input': {'file_path': p}}  # noqa: E731
    assert g.decide(bash('make car-up'), lambda: False)[0] == 'ask'
    assert g.decide(bash('make car-up'), lambda: True)[0] == 'ask'
    assert g.decide(bash('make drivers-stop'), lambda: True) is None
    assert g.decide(bash('make car-down'), lambda: True) is None
    assert g.decide(bash('make ros-image'), lambda: True)[0] == 'deny'
    assert g.decide(bash('make ros-image'), lambda: False) is None
    res = g.decide(edit('rccar_drivers/x.py'), lambda: True)
    assert res[0] == 'deny' and 'make drivers-stop' in res[1]
    assert g.decide(edit('rccar_drivers/x.py'), lambda: False) is None
    assert g.decide(edit('docs/x.md'), lambda: True) is None
    assert g.decide({'tool_name': 'Read', 'tool_input': {}}, lambda: True) is None


def test_main_output_schema():
    payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'make drivers-start'}})
    r = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True,
                       text=True, timeout=30)
    assert r.returncode == 0
    out = json.loads(r.stdout)['hookSpecificOutput']
    assert out['hookEventName'] == 'PreToolUse' and out['permissionDecision'] == 'ask'
    r = subprocess.run([sys.executable, str(HOOK)], input='{"tool_name": "Bash", '
                       '"tool_input": {"command": "make drivers-stop"}}',
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and r.stdout == ''
    r = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True,
                       text=True, timeout=30)
    assert r.returncode == 0 and r.stdout == ''
