"""
launch_testing: car.launch.py against a fake MCU (runs under colcon test).

Checks the lifecycle auto-activation of mcu_bridge and its tuning push once the
MCU service is reachable (the MCU READY event may predate the bridge). Never arms.
Skipped automatically where ROS 2 / launch_testing is not installed.
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
            launch_arguments={'tuning_file': TUNING}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestBringup(unittest.TestCase):
    """mcu_bridge reaches ACTIVE and pushes tuning.toml without a READY event."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('bringup_test')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_tuning_pushed_after_activation(self):
        if not os.path.isfile(TUNING):
            self.skipTest(f'{TUNING} not present')
        log = []
        self.node.create_subscription(
            String, '/fake_mcu/log', lambda m: log.append(m.data),
            QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        end = time.monotonic() + 20.0
        while time.monotonic() < end and not any(c.startswith('SET control_hz') for c in log):
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertTrue(any(c.startswith('CAL CENTER') for c in log), log)
        self.assertTrue(any(c.startswith('SET control_hz') for c in log), log)
        self.assertNotIn('ARM', log, 'bringup must never arm')
        self.assertNotIn('SAVE', log, 'save_after_push defaults to false')
