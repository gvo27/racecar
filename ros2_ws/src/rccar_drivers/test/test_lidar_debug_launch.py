"""
launch_testing: `lidar_snapshot` and `lidar_record` (rccar_calibration) against the fake Mapper.

mapper_driver (lifecycle, auto-activated) talks to fake_mapper.py; the two debug tools run as
subprocesses exactly like `make lidar-snapshot` / `make lidar-record` do in the tools container.
Skipped automatically where ROS 2 / launch_testing is not installed.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import pytest

pytest.importorskip('launch_testing')
pytest.importorskip('rclpy')

import launch  # noqa: E402,I100,I201,I202
from launch.actions import (  # noqa: E402,I100,I201,I202
    EmitEvent, ExecuteProcess, RegisterEventHandler)
from launch.event_handlers import OnProcessStart  # noqa: E402,I100,I201,I202
from launch.events import matches_action  # noqa: E402,I100,I201,I202
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
from launch_ros.actions import LifecycleNode  # noqa: E402,I100,I201,I202
from launch_ros.event_handlers import OnStateTransition  # noqa: E402,I100,I201,I202
from launch_ros.events.lifecycle import ChangeState  # noqa: E402,I100,I201,I202
from lifecycle_msgs.msg import Transition  # noqa: E402,I100,I201,I202
import yaml  # noqa: E402,I100,I201,I202

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_MAPPER = os.path.join(HERE, 'fake_mapper.py')
PORT = 18447
PNG_SIG = b'\x89PNG\r\n\x1a\n'


@pytest.mark.launch_test
def generate_test_description():
    driver = LifecycleNode(
        package='rccar_drivers', executable='mapper_driver', name='mapper_driver',
        namespace='', output='screen',
        parameters=[{'host': '127.0.0.1', 'port': PORT, 'scan_rate_hz': 10.0,
                     'map_period_s': 0.5, 'health_period_s': 0.5}])
    return launch.LaunchDescription([
        ExecuteProcess(cmd=[sys.executable, FAKE_MAPPER, '--port', str(PORT), '--m2m1-imu'],
                       output='screen'),
        driver,
        RegisterEventHandler(OnProcessStart(
            target_action=driver,
            on_start=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(driver),
                transition_id=Transition.TRANSITION_CONFIGURE))])),
        RegisterEventHandler(OnStateTransition(
            target_lifecycle_node=driver, goal_state='inactive',
            entities=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(driver),
                transition_id=Transition.TRANSITION_ACTIVATE))])),
        launch_testing.actions.ReadyToTest(),
    ])


class TestLidarDebugTools(unittest.TestCase):
    """Snapshot files and an mcap bag produced from the fake Mapper."""

    def setUp(self):
        self.out = tempfile.mkdtemp(prefix='lidar_debug_')

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def test_snapshot(self):
        proc = subprocess.run(
            ['ros2', 'run', 'rccar_calibration', 'lidar_snapshot', '--ros-args',
             '-p', f'log_dir:={self.out}', '-p', 'timeout_s:=30.0', '-p', 'window_s:=2.0'],
            capture_output=True, text=True, timeout=90)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        dirs = glob.glob(os.path.join(self.out, 'lidar_snapshot_*'))
        self.assertEqual(len(dirs), 1, os.listdir(self.out))
        snap = dirs[0]
        for name in ('map.png', 'scan.json', 'pose.json', 'imu.json', 'map_meta.json',
                     'diagnostics.json', 'summary.json', 'summary.txt'):
            self.assertTrue(os.path.isfile(os.path.join(snap, name)), name)
        with open(os.path.join(snap, 'map.png'), 'rb') as fh:
            self.assertEqual(fh.read(8), PNG_SIG)
        self.assertIn(snap, proc.stdout)

    def test_record(self):
        proc = subprocess.run(
            ['ros2', 'run', 'rccar_calibration', 'lidar_record', '--secs', '4',
             '--out-dir', self.out],
            capture_output=True, text=True, timeout=90)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        bags = glob.glob(os.path.join(self.out, 'lidar_bag_*'))
        self.assertEqual(len(bags), 1, os.listdir(self.out))
        self.assertTrue(glob.glob(os.path.join(bags[0], '*.mcap')), os.listdir(bags[0]))
        with open(os.path.join(bags[0], 'metadata.yaml'), encoding='utf-8') as fh:
            meta = yaml.safe_load(fh)['rosbag2_bagfile_information']
        counts = {t['topic_metadata']['name']: t['message_count']
                  for t in meta['topics_with_message_count']}
        self.assertGreater(counts.get('/rccar/lidar/scan', 0), 0, counts)
        self.assertGreater(counts.get('/rccar/mapper/map', 0), 0, counts)
