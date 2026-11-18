"""
launch_testing: mapper_driver (lifecycle) against the fake Mapper TCP server.

Asserts scan, imu, map, TF odom->base_link and the diagnostics link status.
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
from launch.actions import (  # noqa: E402,I100,I201,I202
    EmitEvent, ExecuteProcess, RegisterEventHandler)
from launch.event_handlers import OnProcessStart  # noqa: E402,I100,I201,I202
from launch.events import matches_action  # noqa: E402,I100,I201,I202
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
from launch_ros.actions import LifecycleNode, Node  # noqa: E402,I100,I201,I202
from launch_ros.event_handlers import OnStateTransition  # noqa: E402,I100,I201,I202
from launch_ros.events.lifecycle import ChangeState  # noqa: E402,I100,I201,I202
from lifecycle_msgs.msg import Transition  # noqa: E402,I100,I201,I202
import rclpy  # noqa: E402,I100,I201,I202
from rclpy.qos import (  # noqa: E402,I100,I201,I202
    DurabilityPolicy, qos_profile_sensor_data, QoSProfile, ReliabilityPolicy)

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_MAPPER = os.path.join(HERE, 'fake_mapper.py')
PORT = 18445


@pytest.mark.launch_test
def generate_test_description():
    driver = LifecycleNode(
        package='rccar_drivers', executable='mapper_driver', name='mapper_driver',
        namespace='', output='screen',
        parameters=[{'host': '127.0.0.1', 'port': PORT, 'scan_rate_hz': 20.0,
                     'map_period_s': 0.5, 'health_period_s': 0.5}])
    return launch.LaunchDescription([
        ExecuteProcess(cmd=[sys.executable, FAKE_MAPPER, '--port', str(PORT)],
                       output='screen'),
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--x', '0.2', '--frame-id', 'base_link',
                        '--child-frame-id', 'lidar_link']),
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


class TestMapperDriver(unittest.TestCase):
    """Topics, TF and diagnostics produced from the fake Mapper."""

    @classmethod
    def setUpClass(cls):
        from diagnostic_msgs.msg import DiagnosticArray
        from nav_msgs.msg import OccupancyGrid
        from sensor_msgs.msg import Imu, LaserScan
        from tf2_ros import Buffer, TransformListener
        rclpy.init()
        cls.node = rclpy.create_node('mapper_test')
        cls.got = {}
        n = cls.node
        n.create_subscription(LaserScan, '/rccar/lidar/scan',
                              lambda m: cls.got.setdefault('scan', m),
                              qos_profile_sensor_data)
        n.create_subscription(Imu, '/rccar/lidar/imu',
                              lambda m: cls.got.setdefault('imu', m),
                              qos_profile_sensor_data)
        n.create_subscription(
            OccupancyGrid, '/rccar/mapper/map',
            lambda m: cls.got.setdefault('map', m),
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        n.create_subscription(DiagnosticArray, '/diagnostics',
                              lambda m: cls.got.setdefault('diag', []).append(m), 10)
        cls.buf = Buffer()
        cls.listener = TransformListener(cls.buf, n)

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def _wait(self, pred, timeout=25.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end and not pred():
            rclpy.spin_once(self.node, timeout_sec=0.05)
        return pred()

    def test_scan(self):
        self.assertTrue(self._wait(lambda: 'scan' in self.got), 'no LaserScan')
        scan = self.got['scan']
        self.assertEqual(len(scan.ranges), 1080)
        self.assertEqual(scan.header.frame_id, 'lidar_link')
        self.assertTrue(any(r < float('inf') for r in scan.ranges))

    def test_imu(self):
        self.assertTrue(self._wait(lambda: 'imu' in self.got), 'no Imu')
        self.assertEqual(self.got['imu'].header.frame_id, 'lidar_imu_link')
        self.assertAlmostEqual(self.got['imu'].angular_velocity.z, 0.3)
        # fake sends no bitmap: legacy (all provided) except acc, gated by imu_trust_acc=False
        self.assertEqual(self.got['imu'].orientation_covariance[0], 0.0)
        self.assertEqual(self.got['imu'].angular_velocity_covariance[0], 0.0)
        self.assertEqual(self.got['imu'].linear_acceleration_covariance[0], -1.0)

    def test_map(self):
        self.assertTrue(self._wait(lambda: 'map' in self.got), 'no OccupancyGrid')
        grid = self.got['map']
        self.assertEqual((grid.info.width, grid.info.height), (4, 3))
        self.assertEqual(len(grid.data), 12)

    def test_tf_odom_base(self):
        from rclpy.time import Time
        self.assertTrue(self._wait(
            lambda: self.buf.can_transform('odom', 'base_link', Time())),
            'odom->base_link not resolvable')
        self.assertTrue(self.buf.can_transform('map', 'odom', Time()))
        # fake pose (1, 2, 0.5) is the lidar; base is 0.2 m behind it along yaw
        t = self.buf.lookup_transform('map', 'base_link', Time())
        self.assertAlmostEqual(t.transform.translation.x, 1.0 - 0.2 * 0.8775825, places=2)

    def test_diagnostics_link_ok(self):
        def ok():
            for arr in self.got.get('diag', []):
                for st in arr.status:
                    if st.name == 'mapper_driver: link' and st.level == b'\x00' \
                            and any(kv.key == 'sdp_version' and kv.value == 'fake-1.0'
                                    for kv in st.values):
                        return True
            return False
        self.assertTrue(self._wait(ok), 'no OK link diagnostics')
