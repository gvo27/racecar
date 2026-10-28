"""
Fake MCU for launch tests: /rccar/mcu/command replies OK, drive is counted.

Every received command is also published on /fake_mcu/log (std_msgs/String) so
tests can assert on ARM / DISARM without a real firmware.
"""
from rccar_msgs.msg import DriveCmd
from rccar_msgs.srv import McuCommand
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class FakeMcu(Node):
    """Stand-in for the micro-ROS firmware entities used by the supervisor."""

    def __init__(self):
        super().__init__('fake_mcu')
        self.drive_count = 0
        self.create_service(McuCommand, '/rccar/mcu/command', self._on_command)
        self.create_subscription(
            DriveCmd, '/rccar/mcu/drive', self._on_drive,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        # transient_local: a test that subscribes late still sees every command
        self._log = self.create_publisher(
            String, '/fake_mcu/log',
            QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def _on_drive(self, msg):
        self.drive_count += 1

    def _on_command(self, request, response):
        self._log.publish(String(data=request.command))
        response.ok = True
        response.reply = f'OK {request.command}'
        return response


def main():
    rclpy.init()
    node = FakeMcu()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
