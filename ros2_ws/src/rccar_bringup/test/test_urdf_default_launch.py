"""
launch_testing: drivers.launch.py without urdf_file:= keeps the rccar_description model.

Skipped automatically where ROS 2 / launch_testing is not installed.
"""
import os
import time
import unittest

import pytest

pytest.importorskip('launch_testing')
pytest.importorskip('rclpy')

import launch  # noqa: E402,I100,I201,I202
from launch.actions import IncludeLaunchDescription  # noqa: E402,I100,I201,I202
from launch.launch_description_sources import (  # noqa: E402,I100,I201,I202
    PythonLaunchDescriptionSource)
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
import rclpy  # noqa: E402,I100,I201,I202
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402,I100,I201,I202
from std_msgs.msg import String  # noqa: E402,I100,I201,I202

HERE = os.path.dirname(os.path.abspath(__file__))
LAUNCH = os.path.join(HERE, '..', 'launch', 'drivers.launch.py')


@pytest.mark.launch_test
def generate_test_description():
    return launch.LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(LAUNCH),
            launch_arguments={'mapper_host': '127.0.0.1'}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestUrdfDefault(unittest.TestCase):
    """robot_description holds the default car model."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('urdf_default_test')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_robot_description_default(self):
        got = []
        self.node.create_subscription(
            String, '/robot_description', lambda m: got.append(m.data),
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        end = time.monotonic() + 20.0
        while time.monotonic() < end and not got:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertTrue(got, 'no /robot_description')
        self.assertIn('lidar_link', got[0])
