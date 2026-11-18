"""
launch_testing: lifecycle cycling and reconnect of mapper_driver (in-process FakeMapper).

Tests are numbered: they share one driver and leave it active.
"""
import os
import sys
import time
import unittest

import pytest

pytest.importorskip('launch_testing')
pytest.importorskip('rclpy')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from fake_mapper import FakeMapper  # noqa: E402,I100,I201,I202
import launch  # noqa: E402,I100,I201,I202
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
from launch_ros.actions import LifecycleNode, Node  # noqa: E402,I100,I201,I202
from lifecycle_msgs.msg import Transition  # noqa: E402,I100,I201,I202
from lifecycle_msgs.srv import ChangeState as ChangeStateSrv  # noqa: E402,I100,I201,I202
import rclpy  # noqa: E402,I100,I201,I202
from rclpy.qos import qos_profile_sensor_data  # noqa: E402,I100,I201,I202

PORT = 18446
SERVER = FakeMapper(port=PORT)


@pytest.mark.launch_test
def generate_test_description():
    driver = LifecycleNode(
        package='rccar_drivers', executable='mapper_driver', name='mapper_driver',
        namespace='', output='screen',
        parameters=[{'host': '127.0.0.1', 'port': PORT, 'scan_rate_hz': 20.0,
                     'map_period_s': 0.5, 'health_period_s': 0.5,
                     'reconnect_max_s': 1.0, 'range_max': 40}])  # int for a double param
    return launch.LaunchDescription([
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--x', '0.2', '--frame-id', 'base_link',
                        '--child-frame-id', 'lidar_link']),
        driver,
        launch_testing.actions.ReadyToTest(),
    ])


class TestLifecycleCycling(unittest.TestCase):
    """Cycle the lifecycle and drop the link; scans must resume, one /tf publisher."""

    @classmethod
    def setUpClass(cls):
        from sensor_msgs.msg import LaserScan
        rclpy.init()
        cls.node = rclpy.create_node('mapper_cycle_test')
        cls.scans = 0
        cls.node.create_subscription(LaserScan, '/rccar/lidar/scan', cls._on_scan,
                                     qos_profile_sensor_data)
        cls.cli = cls.node.create_client(ChangeStateSrv, '/mapper_driver/change_state')

    @classmethod
    def _on_scan(cls, _msg):
        cls.scans += 1

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()
        SERVER.stop()

    def _wait(self, pred, timeout=15.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end and not pred():
            rclpy.spin_once(self.node, timeout_sec=0.05)
        return pred()

    def _transition(self, transition_id):
        self.assertTrue(self.cli.wait_for_service(timeout_sec=15.0))
        req = ChangeStateSrv.Request()
        req.transition.id = transition_id
        fut = self.cli.call_async(req)
        self.assertTrue(self._wait(fut.done, 15.0), 'change_state timed out')
        self.assertTrue(fut.result().success, f'transition {transition_id} failed')

    def _scans_flow(self, timeout=15.0):
        start = type(self).scans
        self.assertTrue(self._wait(lambda: type(self).scans >= start + 5, timeout),
                        'scans did not resume')

    def _tf_publishers(self):
        infos = self.node.get_publishers_info_by_topic('/tf')
        return [i for i in infos if i.node_name == 'mapper_driver']

    def _assert_one_tf_publisher(self):
        self.assertTrue(self._wait(lambda: len(self._tf_publishers()) == 1, 10.0),
                        f'/tf publishers from mapper_driver: {len(self._tf_publishers())}')

    def test_1_configure_activate(self):
        # no launch-side auto-transition: it would re-activate after our deactivate
        self._transition(Transition.TRANSITION_CONFIGURE)
        self._transition(Transition.TRANSITION_ACTIVATE)
        self._scans_flow(30.0)
        self._assert_one_tf_publisher()

    def test_2_deactivate_activate(self):
        self._transition(Transition.TRANSITION_DEACTIVATE)
        self._transition(Transition.TRANSITION_ACTIVATE)
        self._scans_flow()
        self._assert_one_tf_publisher()

    def test_3_cleanup_configure_activate(self):
        self._transition(Transition.TRANSITION_DEACTIVATE)
        self._transition(Transition.TRANSITION_CLEANUP)
        self.assertTrue(self._wait(lambda: not self._tf_publishers(), 10.0),
                        'TF publisher not destroyed by cleanup')
        self._transition(Transition.TRANSITION_CONFIGURE)
        self._transition(Transition.TRANSITION_ACTIVATE)
        self._scans_flow()
        self._assert_one_tf_publisher()

    def test_4_reconnect_after_link_drop(self):
        SERVER.drop_connections()
        start = type(self).scans
        self.assertTrue(self._wait(lambda: type(self).scans >= start + 10, 10.0),
                        'scans did not resume after the link dropped')
