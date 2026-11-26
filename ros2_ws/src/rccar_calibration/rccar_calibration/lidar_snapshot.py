"""One-shot, read-only capture of the lidar topics -> PNG + JSON + text summary."""
import json
import os
import sys
import time

from diagnostic_msgs.msg import DiagnosticArray
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from rccar_calibration.lidar_imu_format import quat_to_yaw
from rccar_calibration.lidar_snapshot_render import encode_png, render
from rccar_calibration.lidar_snapshot_summary import (
    build_summary, format_summary, json_safe, snapshot_dirname)
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    qos_profile_sensor_data, QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy)
from sensor_msgs.msg import Imu, LaserScan

DEFAULT_LOG_DIR = '/ws/src/racecar/logs'
HINT = 'Mapper powered and on Wi-Fi? drivers running? check: make car-logs'


def _level(v):
    return int.from_bytes(v, 'little') if isinstance(v, (bytes, bytearray)) else int(v)


class LidarSnapshot(Node):
    """Subscribe only; keep the latest message of each topic as a plain dict."""

    def __init__(self):
        super().__init__('lidar_snapshot')
        p = self.declare_parameter
        self.window_s = float(p('window_s', 3.0).value)
        self.timeout_s = float(p('timeout_s', 8.0).value)
        self.log_dir = p('log_dir', os.environ.get('RCCAR_LOG_DIR', DEFAULT_LOG_DIR)).value
        self.topics = {
            'scan': p('scan_topic', '/rccar/lidar/scan').value,
            'pose': p('pose_topic', '/rccar/mapper/pose').value,
            'imu': p('imu_topic', '/rccar/lidar/imu').value,
            'map': p('map_topic', '/rccar/mapper/map').value,
            'diag': p('diagnostics_topic', '/diagnostics').value,
        }
        self.latest = {}
        self.counts = {}
        self.times = {}
        map_qos = QoSProfile(depth=1, reliability=QoSReliabilityPolicy.RELIABLE,
                             durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        t = self.topics
        self.create_subscription(LaserScan, t['scan'], self._on_scan, qos_profile_sensor_data)
        self.create_subscription(PoseStamped, t['pose'], self._on_pose,
                                 qos_profile_sensor_data)
        self.create_subscription(Imu, t['imu'], self._on_imu, qos_profile_sensor_data)
        self.create_subscription(OccupancyGrid, t['map'], self._on_map, map_qos)
        self.create_subscription(DiagnosticArray, t['diag'], self._on_diag, 10)

    def now_s(self) -> float:
        """Node clock in seconds."""
        return self.get_clock().now().nanoseconds * 1e-9

    def _store(self, key, value):
        now = self.now_s()
        self.latest[key] = value
        name = self.topics[key]
        self.counts[name] = self.counts.get(name, 0) + 1
        first = self.times.get(name, (now, now))[0]
        self.times[name] = (first, now)

    def _on_scan(self, msg):
        self._store('scan', {
            'frame_id': msg.header.frame_id, 'angle_min': msg.angle_min,
            'angle_max': msg.angle_max, 'angle_increment': msg.angle_increment,
            'range_min': msg.range_min, 'range_max': msg.range_max,
            'ranges': [float(r) for r in msg.ranges]})

    def _on_pose(self, msg):
        q = msg.pose.orientation
        self._store('pose', {
            'frame_id': msg.header.frame_id, 'x': msg.pose.position.x,
            'y': msg.pose.position.y, 'yaw': quat_to_yaw(q.x, q.y, q.z, q.w)})

    def _on_imu(self, msg):
        q = msg.orientation
        self._store('imu', {
            'frame_id': msg.header.frame_id,
            'orientation': [float(q.x), float(q.y), float(q.z), float(q.w)],
            'angular_velocity': [msg.angular_velocity.x, msg.angular_velocity.y,
                                 msg.angular_velocity.z],
            'linear_acceleration': [msg.linear_acceleration.x, msg.linear_acceleration.y,
                                    msg.linear_acceleration.z],
            'orientation_covariance0': float(msg.orientation_covariance[0]),
            'angular_velocity_covariance0': float(msg.angular_velocity_covariance[0]),
            'linear_acceleration_covariance0': float(msg.linear_acceleration_covariance[0])})

    def _on_map(self, msg):
        info = msg.info
        o = info.origin.orientation
        self._store('map', {
            'frame_id': msg.header.frame_id, 'width': info.width, 'height': info.height,
            'resolution': info.resolution, 'origin_x': info.origin.position.x,
            'origin_y': info.origin.position.y,
            'origin_yaw': quat_to_yaw(o.x, o.y, o.z, o.w), 'data': [int(v) for v in msg.data]})

    def _on_diag(self, msg):
        self._store('diag', [{
            'name': s.name, 'level': _level(s.level), 'message': s.message,
            'values': {kv.key: kv.value for kv in s.values}} for s in msg.status])

    def missing(self):
        """Topic names of scan, pose and map not yet received."""
        return [self.topics[k] for k in ('scan', 'pose', 'map') if k not in self.latest]

    def capture(self):
        """Spin until window_s elapsed and scan+pose+map seen, or timeout_s."""
        start = time.monotonic()
        while rclpy.ok():
            elapsed = time.monotonic() - start
            if elapsed >= self.timeout_s:
                break
            if elapsed >= self.window_s and not self.missing():
                break
            rclpy.spin_once(self, timeout_sec=0.1)


def write_snapshot(node, out_dir, t_unix):
    """Write all files into out_dir; returns the summary text."""
    lat = node.latest
    scan, pose, imu = lat.get('scan'), lat.get('pose'), lat.get('imu')
    m = lat.get('map')
    meta = None if m is None else {k: v for k, v in m.items() if k != 'data'}
    data = None if m is None else m['data']
    summary = build_summary(scan, pose, imu, meta, data, lat.get('diag'), node.counts,
                            node.times, node.now_s(), t_unix)
    text = format_summary(summary)

    def dump(name, obj):
        with open(os.path.join(out_dir, name), 'w', encoding='utf-8') as fh:
            json.dump(json_safe(obj), fh, indent=2)

    os.makedirs(out_dir, exist_ok=True)
    if meta is not None or (scan and pose):
        w, h, rgb = render(meta, data, scan, pose)
        with open(os.path.join(out_dir, 'map.png'), 'wb') as fh:
            fh.write(encode_png(w, h, rgb))
    if scan is not None:
        dump('scan.json', scan)
    if pose is not None:
        dump('pose.json', {'x': pose['x'], 'y': pose['y'],
                           'yaw_deg': summary['pose']['yaw_deg'],
                           'frame': pose['frame_id']})
    if imu is not None:
        dump('imu.json', imu)
    if meta is not None:
        dump('map_meta.json', meta)
    dump('diagnostics.json', lat.get('diag'))
    dump('summary.json', summary)
    with open(os.path.join(out_dir, 'summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write(text)
    return text


def main(args=None):
    rclpy.init(args=args)
    node = LidarSnapshot()
    code = 0
    try:
        node.capture()
        t_unix = time.time()
        out_dir = os.path.join(node.log_dir, snapshot_dirname(t_unix))
        try:
            text = write_snapshot(node, out_dir, t_unix)
        except OSError as exc:
            print(f'cannot write {out_dir}: {exc}', file=sys.stderr, flush=True)
            return 2
        print(text, flush=True)
        print(f'snapshot: {out_dir}', flush=True)
        missing = node.missing()
        if missing:
            print('missing: ' + ' '.join(missing), flush=True)
            print(HINT, flush=True)
            code = 1
    except KeyboardInterrupt:
        code = 130
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return code


if __name__ == '__main__':
    sys.exit(main())
