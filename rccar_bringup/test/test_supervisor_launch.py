"""
launch_testing: supervisor wiring against a fake MCU (runs under colcon test).

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
import launch_testing  # noqa: E402,I100,I201,I202
import launch_testing.actions  # noqa: E402,I100,I201,I202
import rclpy  # noqa: E402,I100,I201,I202
from launch.actions import ExecuteProcess  # noqa: E402,I100,I201,I202
from launch_ros.actions import Node as LaunchNode  # noqa: E402,I100,I201,I202
from rccar_msgs.msg import DriveCmd, SupervisorState  # noqa: E402,I100,I201,I202
from rccar_msgs.srv import Reset  # noqa: E402,I100,I201,I202
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy  # noqa: E402,I100,I201,I202
from std_msgs.msg import String  # noqa: E402,I100,I201,I202
from std_srvs.srv import Trigger  # noqa: E402,I100,I201,I202

FAKE_MCU = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_mcu.py')
SEND_HZ = 20.0


@pytest.mark.launch_test
def generate_test_description():
    return launch.LaunchDescription([
        ExecuteProcess(cmd=[sys.executable, FAKE_MCU], output='screen'),
        LaunchNode(package='rccar_supervisor', executable='supervisor_node',
                   name='supervisor', output='screen',
                   parameters=[{'send_hz': SEND_HZ, 'admin_timeout_s': 0.3}]),
        launch_testing.actions.ReadyToTest(),
    ])


class TestSupervisorWiring(unittest.TestCase):
    """Sequential scenario: arm -> forward -> silence -> brake."""

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('supervisor_test')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def setUp(self):
        n = self.node
        self.drive, self.log, self.state = [], [], None
        self.admin = n.create_publisher(
            DriveCmd, '/rccar/cmd/admin',
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        n.create_subscription(
            DriveCmd, '/rccar/mcu/drive', self.drive.append,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        n.create_subscription(String, '/fake_mcu/log', lambda m: self.log.append(m.data), 50)
        n.create_subscription(
            SupervisorState, '/rccar/supervisor/state', self._on_state,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.arm_cli = n.create_client(Reset, '/supervisor/arm')
        self.brake_cli = n.create_client(Trigger, '/supervisor/brake')

    def _on_state(self, msg):
        self.state = msg

    def spin(self, seconds, throttle=None):
        """Spin for ``seconds``, publishing admin commands at SEND_HZ if throttle given."""
        end = time.monotonic() + seconds
        next_pub = 0.0
        while time.monotonic() < end:
            if throttle is not None and time.monotonic() >= next_pub:
                msg = DriveCmd()
                msg.throttle, msg.source = float(throttle), 'admin'
                self.admin.publish(msg)
                next_pub = time.monotonic() + 1.0 / SEND_HZ
            rclpy.spin_once(self.node, timeout_sec=0.01)

    def wait_for(self, cond, timeout=10.0, throttle=None):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if cond():
                return True
            self.spin(0.05, throttle)
        return cond()

    def call(self, client, request):
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=5.0)
        self.assertTrue(future.done(), 'service call timed out')
        return future.result()

    def test_arm_forward_silence_brake(self):
        self.assertTrue(self.arm_cli.wait_for_service(10.0), 'supervisor arm service')
        self.assertTrue(self.brake_cli.wait_for_service(10.0))
        self.assertTrue(self.wait_for(lambda: self.state is not None), 'no state')
        self.assertTrue(self.wait_for(lambda: self.admin.get_subscription_count() >= 1))

        # boot: disarmed, nothing on the drive topic even with admin commands flowing
        self.spin(0.5, throttle=0.0)
        self.assertEqual(self.drive, [], 'drive published while disarmed')
        self.assertFalse(self.state.armed)

        # a non-neutral admin command blocks arming
        self.spin(0.3, throttle=0.2)
        req = Reset.Request()
        req.incident = self.state.incident
        res = self.call(self.arm_cli, req)
        self.assertFalse(res.ok, res.message)

        # neutral admin -> arm succeeds (MCU got ARM), armed but stationary
        self.spin(0.5, throttle=0.0)
        res = self.call(self.arm_cli, req)
        self.assertTrue(res.ok, res.message)
        self.assertIn('ARM', self.log)
        self.assertTrue(self.wait_for(lambda: self.state.armed))

        # deadman: motion only after the admin input re-asserts neutral post-reset
        self.drive.clear()
        self.spin(0.3, throttle=0.2)
        self.assertTrue(self.drive and all(m.throttle == 0.0 for m in self.drive),
                        'non-neutral first command after reset must be held at 0')

        # drive is forwarded
        self.spin(0.2, throttle=0.0)
        self.drive.clear()
        self.spin(0.8, throttle=0.2)
        fwd = [m for m in self.drive if m.source == 'admin' and abs(m.throttle - 0.2) < 1e-3]
        self.assertGreaterEqual(len(fwd), 5, f'forwarded {len(fwd)} of {len(self.drive)}')

        # admin silence -> neutral keeps streaming
        self.spin(0.6)
        self.drive.clear()
        self.spin(0.6)
        self.assertGreaterEqual(len(self.drive), 5, 'stream must continue (armed, idle)')
        self.assertTrue(all(m.throttle == 0.0 for m in self.drive))

        # brake -> DISARM sent, stream stops, state latched
        self.log.clear()
        res = self.call(self.brake_cli, Trigger.Request())
        self.assertTrue(res.success, res.message)
        self.spin(0.3)
        self.assertIn('DISARM', self.log)
        self.drive.clear()
        self.spin(0.8)
        self.assertEqual(self.drive, [], 'drive must stop after brake')
        self.assertTrue(self.wait_for(lambda: self.state.estop_latched))
        self.assertFalse(self.state.armed)
        self.assertGreaterEqual(self.state.incident, 1)
