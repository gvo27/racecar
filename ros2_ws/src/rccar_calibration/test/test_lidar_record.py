"""Tests for lidar_record (no ROS needed)."""
import subprocess

import pytest
from rccar_calibration import lidar_record as lr


@pytest.mark.parametrize('value', ['0', '601', '-3', 'abc', '1.5', ''])
def test_parse_secs_invalid(value):
    with pytest.raises(ValueError):
        lr.parse_secs(value)


def test_parse_secs_valid():
    assert lr.parse_secs('1') == 1
    assert lr.parse_secs(600) == 600
    assert lr.parse_secs(' 30 ') == 30


def test_bag_dirname():
    assert lr.bag_dirname(0) == 'lidar_bag_19700101T000000Z'
    assert lr.bag_dirname(1700000000) == 'lidar_bag_20231114T221320Z'


def test_build_command():
    cmd = lr.build_command(lr.TOPICS, '/x/bag')
    assert cmd[:3] == ['ros2', 'bag', 'record']
    assert cmd[cmd.index('-s') + 1] == 'mcap'
    assert cmd[cmd.index('-o') + 1] == '/x/bag'
    for topic in lr.TOPICS:
        assert topic in cmd


def test_info_command():
    assert lr.info_command('/x/bag') == ['ros2', 'bag', 'info', '/x/bag']


def test_main_bad_out_dir(monkeypatch, tmp_path):
    def fail(*a, **k):
        raise AssertionError('subprocess must not run')
    monkeypatch.setattr(subprocess, 'Popen', fail)
    assert lr.main(['--out-dir', str(tmp_path / 'missing')]) == 2


def test_main_records_and_stops(tmp_path):
    calls = []

    class Proc:
        def poll(self):
            return None

        def send_signal(self, sig):
            calls.append('sigint')

        def wait(self, timeout=None):
            return 0

    def popen(cmd):
        calls.append(cmd)
        (tmp_path / 'lidar_bag_19700101T000000Z').mkdir()
        return Proc()

    ran = []
    rc = lr.main(['--secs', '2', '--out-dir', str(tmp_path)], popen=popen,
                 run=lambda cmd, check: ran.append(cmd), sleep=lambda s: None,
                 now=lambda: 0)
    assert rc == 0
    assert 'sigint' in calls
    assert ran == [lr.info_command(str(tmp_path / 'lidar_bag_19700101T000000Z'))]
