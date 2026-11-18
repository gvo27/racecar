"""
launch_testing: car.launch.py with sim:=true keeps mcu_bridge and pushes the tuning.

The fake MCU stands in for the virtual ESP32 of the sim repo. Skipped automatically
where ROS 2 / launch_testing is not installed.
"""
import os
import sys
import time
import unittest

import pytest

pytest.importorskip('launch_testing')
pytest.importorskip('rclpy')

import launch  # noqa: E402,I100,I201,I202
from launch.actions import ExecuteProcess, IncludeLaunchDescription  # noqa: E402,I100,I201,I202
from launch.launch_description_sources import (  # noqa: E402,I100,I201,I202
    PythonLaunchDescriptionSource)
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
from rccar_mcu_bridge.tuning import firmware_commands, load_tuning  # noqa: E402,I100,I201,I202
import rclpy  # noqa: E402,I100,I201,I202
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402,I100,I201,I202
from std_msgs.msg import String  # noqa: E402,I100,I201,I202

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_MCU = os.path.join(HERE, 'fake_mcu.py')
LAUNCH = os.path.join(HERE, '..', 'launch', 'car.launch.py')
TUNING = os.path.abspath(os.path.join(HERE, '..', '..', 'tuning.toml'))


@pytest.mark.launch_test
def generate_test_description():
    return launch.LaunchDescription([
        ExecuteProcess(cmd=[sys.executable, FAKE_MCU], output='screen'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(LAUNCH),
            launch_arguments={'sim': 'true', 'use_sim_time': 'false',
                              'tuning_file': TUNING}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestSimBringup(unittest.TestCase):
    """With sim:=true the mcu_bridge node exists and sends every tuning command."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('sim_bringup_test')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_bridge_exists_and_pushes_tuning(self):
        if not os.path.isfile(TUNING):
            self.skipTest(f'{TUNING} not present')
        expected = firmware_commands(load_tuning(TUNING))
        self.assertTrue(expected, 'tuning file has no firmware keys')
        log = []
        self.node.create_subscription(
            String, '/fake_mcu/log', lambda m: log.append(m.data),
            QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        end = time.monotonic() + 30.0
        while time.monotonic() < end and not all(c in log for c in expected):
            rclpy.spin_once(self.node, timeout_sec=0.05)
        missing = [c for c in expected if c not in log]
        self.assertFalse(missing, f'tuning commands not pushed: {missing}')
        self.assertIn('mcu_bridge', self.node.get_node_names())
        self.assertNotIn('ARM', log, 'bringup must never arm')
