"""Live rangefinder feed: MCU stamp, Pi time, range and rate. Read-only."""
import sys

from rccar_calibration.rangefinder_format import format_line, HEADER, RateEstimator
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range

WAIT_PERIOD_S = 2.0


class RangefinderMonitor(Node):
    """Print one line per Range message; hint while nothing arrives."""

    def __init__(self):
        super().__init__('rangefinder_monitor')
        self.topic = self.declare_parameter(
            'topic', '/rccar/rangefinder/range').value
        self._rate = RateEstimator(2.0)
        self._last_rx = None
        self.create_subscription(Range, self.topic, self._on_range,
                                 qos_profile_sensor_data)
        self.create_timer(WAIT_PERIOD_S, self._on_timer)
        print(HEADER, flush=True)

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_range(self, msg: Range):
        now = self._now_s()
        self._last_rx = now
        self._rate.add(now)
        print(format_line(msg.header.stamp.sec, msg.header.stamp.nanosec, now,
                          msg.range, msg.min_range, msg.max_range,
                          self._rate.rate(now)), flush=True)

    def _on_timer(self):
        stale = (self._last_rx is None
                 or self._now_s() - self._last_rx > WAIT_PERIOD_S)
        if stale:
            print(f'waiting for {self.topic} (sensor wired + powered? '
                  'check: make mcu CMD="SENS rangefinder")', flush=True)


def main(args=None):
    rclpy.init(args=args)
    node = RangefinderMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
