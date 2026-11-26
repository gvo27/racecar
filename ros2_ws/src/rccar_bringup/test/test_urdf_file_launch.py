"""
launch_testing: drivers.launch.py urdf_file:= selects the robot_state_publisher model.

The test xacro has a link that rccar_description does not have. The mapper driver
gets an unreachable local port and only retries. Skipped automatically where
ROS 2 / launch_testing is not installed.
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
URDF = os.path.join(HERE, 'test_model.urdf.xacro')


@pytest.mark.launch_test
def generate_test_description():
    return launch.LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(LAUNCH),
            launch_arguments={'urdf_file': URDF, 'mapper_host': '127.0.0.1'}.items()),
        launch_testing.actions.ReadyToTest(),
    ])


class TestUrdfFile(unittest.TestCase):
    """robot_description holds the model from urdf_file, not the default one."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('urdf_file_test')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_robot_description_from_urdf_file(self):
        got = []
        self.node.create_subscription(
            String, '/robot_description', lambda m: got.append(m.data),
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        end = time.monotonic() + 20.0
        while time.monotonic() < end and not got:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertTrue(got, 'no /robot_description')
        self.assertIn('urdf_file_test_link', got[0])
        self.assertNotIn('lidar_link', got[0])
