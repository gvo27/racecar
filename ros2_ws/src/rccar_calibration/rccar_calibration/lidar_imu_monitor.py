"""Live Mapper IMU feed (planar vehicle state) + jsonl log. Read-only."""
import json
import math
import os
import sys
import time

from geometry_msgs.msg import PoseStamped
from rccar_calibration.lidar_imu_format import (
    format_line, HEADER, log_filename, make_record, quat_to_yaw, RateEstimator,
    Throttle)
from rccar_calibration.lidar_imu_pose import PlanarEstimator
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

WAIT_PERIOD_S = 2.0
PRINT_PERIOD_S = 0.1
DEFAULT_LOG_DIR = '/ws/src/racecar/logs'


class LidarImuMonitor(Node):
    """Print/log at most ~10 lines/s from /rccar/lidar/imu + /rccar/mapper/pose."""

    def __init__(self):
        super().__init__('lidar_imu_monitor')
        self.imu_topic = self.declare_parameter(
            'imu_topic', '/rccar/lidar/imu').value
        self.pose_topic = self.declare_parameter(
            'pose_topic', '/rccar/mapper/pose').value
        log_dir = self.declare_parameter(
            'log_dir', os.environ.get('RCCAR_LOG_DIR', DEFAULT_LOG_DIR)).value
        self._rate = RateEstimator(2.0)
        self._throttle = Throttle(PRINT_PERIOD_S)
        self._last_rx = None
        self._est = PlanarEstimator()
        self._planar = None
        self._jump_latched = False
        self._log = self._open_log(log_dir)
        self.create_subscription(Imu, self.imu_topic, self._on_imu,
                                 qos_profile_sensor_data)
        self.create_subscription(PoseStamped, self.pose_topic, self._on_pose,
                                 qos_profile_sensor_data)
        self.create_timer(WAIT_PERIOD_S, self._on_timer)
        print(HEADER, flush=True)

    def _open_log(self, log_dir):
        path = os.path.join(log_dir, log_filename(time.time()))
        try:
            fh = open(path, 'a', encoding='utf-8')
        except OSError as exc:
            self.get_logger().warn(f'not logging, cannot write {path}: {exc}')
            return None
        print(f'logging to {path}', flush=True)
        return fh

    def _now_s(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_pose(self, msg: PoseStamped):
        q = msg.pose.orientation
        yaw = quat_to_yaw(q.x, q.y, q.z, q.w)
        self._planar = self._est.update(
            self._now_s(), msg.pose.position.x, msg.pose.position.y, yaw)
        self._jump_latched = self._jump_latched or self._planar.jump

    def _on_imu(self, msg: Imu):
        now = self._now_s()
        self._last_rx = now
        self._rate.add(now)
        if not self._throttle.ready(now):
            return
        q = msg.orientation
        imu_heading = (None if msg.orientation_covariance[0] == -1.0 else
                       math.degrees(quat_to_yaw(q.x, q.y, q.z, q.w)))
        gyro = (None if msg.angular_velocity_covariance[0] == -1.0 else
                math.degrees(msg.angular_velocity.z))
        acc = (None if msg.linear_acceleration_covariance[0] == -1.0 else
               (msg.linear_acceleration.x, msg.linear_acceleration.y))
        p = self._planar
        heading = None if p is None else math.degrees(p.heading)
        yaw_rate = None if p is None or p.yaw_rate is None else math.degrees(p.yaw_rate)
        values = (
            now, heading, imu_heading, yaw_rate,
            None if p is None else p.speed,
            None if p is None else p.acc_long,
            None if p is None else p.acc_lat,
            self._rate.rate(now), gyro, acc, self._jump_latched)
        self._jump_latched = False
        print(format_line(*values), flush=True)
        if self._log is not None:
            self._log.write(json.dumps(make_record(*values)) + '\n')
            self._log.flush()

    def _on_timer(self):
        stale = (self._last_rx is None
                 or self._now_s() - self._last_rx > WAIT_PERIOD_S)
        if stale:
            print(f'waiting for {self.imu_topic} (Mapper powered + on Wi-Fi? '
                  'check: make car-logs, drivers service)', flush=True)
        # a stale pose must not report a frozen speed/rate
        if stale:
            self._est.reset()
            self._planar = None

    def close(self):
        if self._log is not None:
            self._log.close()


def main(args=None):
    rclpy.init(args=args)
    node = LidarImuMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
