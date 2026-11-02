"""
Lifecycle node `mapper_driver`: Slamtec Mapper M2M1 -> ROS 2 topics and TF.

Threading: all device IO runs on ONE worker thread (slamtec.worker.MapperWorker)
because the protocol is synchronous request/response over a single socket. The
worker's sink converts each decoded result and publishes it directly from that
thread (rclpy publish is thread-safe), so no queue is needed and executor
callbacks (timers for diagnostics + heartbeat) never touch the socket.

Stamps are the node clock at receive time, and LaserScan.scan_time is the
polling period (1 / scan_rate_hz): the device's per-scan pose/timestamp is not
used yet. IMU values are published raw:
the acc unit (m/s^2 vs g) is bench-TBD (see slamtec.protocol docstring).

TF: map->odom identity (static, once on activate); odom->base_link = Mapper pose
of the lidar composed with the inverse of base_link->lidar_link (looked up from
TF, published by robot_state_publisher). Skipped while that lookup fails.
Planar only: z, roll and pitch of the extrinsic are ignored.
REP-105 deviation: odom->base_link comes from the SLAM pose, so it can jump on
relocalization or loop closure until a continuous odom source (wheel encoder,
IMU) exists; then this driver should publish map->odom instead.
"""
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid
from rccar_drivers.heartbeat import touch
from rccar_drivers.slamtec import convert
from rccar_drivers.slamtec.diagnostics import link_level, SCAN_FRESH_S
from rccar_drivers.slamtec.frames import odom_to_base
from rccar_drivers.slamtec.params import check_params
from rccar_drivers.slamtec.protocol import MapperClient
from rccar_drivers.slamtec.vehicle_state import quat_to_yaw
from rccar_drivers.slamtec.worker import MapperWorker
from rcl_interfaces.msg import ParameterDescriptor
import rclpy
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.lifecycle import Node, TransitionCallbackReturn
from rclpy.qos import (
    DurabilityPolicy, qos_profile_sensor_data, QoSProfile, ReliabilityPolicy)
from rclpy.time import Time
from sensor_msgs.msg import Imu, LaserScan
from tf2_ros import Buffer, StaticTransformBroadcaster, TransformBroadcaster
from tf2_ros import TransformException, TransformListener

MAP_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
HB_PERIOD_S = 0.5

# name -> default; every one is a ROS parameter (not in tuning.toml: unconfirmed)
PARAMS = {
    'host': '192.168.11.1', 'port': 1445, 'timeout_s': 1.0,
    'scan_rate_hz': 10.0, 'imu_rate_hz': 50.0, 'pose_rate_hz': 10.0,
    'map_period_s': 2.0, 'health_period_s': 1.0, 'reconnect_max_s': 5.0,
    'map_max_cells': 4_000_000,
    'n_bins': 1080, 'range_min': 0.15, 'range_max': 40.0,
    'scan_angle_sign': 1.0, 'map_transpose': False, 'map_free_is_high': False,
    'map_frame': 'map', 'odom_frame': 'odom', 'base_frame': 'base_link',
    'lidar_frame': 'lidar_link', 'imu_frame': 'lidar_imu_link',
    'publish_tf': True, 'heartbeat_file': '',
}


class _RosSink:
    """Worker sink: convert decoded Mapper data and publish (worker thread)."""

    def __init__(self, node):
        self._n = node

    def on_scan(self, points):
        n = self._n
        c = n.cfg
        sign = c['scan_angle_sign']
        pts = [(a * sign, d, v) for a, d, v in points]
        s = convert.scan_to_ranges(pts, int(c['n_bins']), c['range_min'], c['range_max'])
        msg = LaserScan()
        msg.header.stamp = n.get_clock().now().to_msg()
        msg.header.frame_id = c['lidar_frame']
        msg.angle_min = s.angle_min
        msg.angle_max = s.angle_max
        msg.angle_increment = s.angle_increment
        msg.time_increment = 0.0
        msg.scan_time = 1.0 / c['scan_rate_hz']
        msg.range_min = c['range_min']
        msg.range_max = c['range_max']
        msg.ranges = s.ranges
        n.pub_scan.publish(msg)

    def on_imu(self, sample):
        n = self._n
        msg = Imu()
        msg.header.stamp = n.get_clock().now().to_msg()
        msg.header.frame_id = n.cfg['imu_frame']
        w, x, y, z = sample.quat
        msg.orientation.w, msg.orientation.x = w, x
        msg.orientation.y, msg.orientation.z = y, z
        msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = sample.gyro
        (msg.linear_acceleration.x, msg.linear_acceleration.y,
         msg.linear_acceleration.z) = sample.acc
        n.pub_imu.publish(msg)

    def on_pose(self, pose):
        n = self._n
        stamp = n.get_clock().now().to_msg()
        msg = PoseStamped()
        msg.header.stamp = stamp
        msg.header.frame_id = n.cfg['map_frame']
        msg.pose.position.x, msg.pose.position.y = pose.x, pose.y
        q = convert.yaw_to_quat(pose.yaw)
        (msg.pose.orientation.x, msg.pose.orientation.y,
         msg.pose.orientation.z, msg.pose.orientation.w) = q
        n.pub_pose.publish(msg)
        if n.cfg['publish_tf']:
            n.publish_odom_tf(stamp, pose)

    def on_map(self, m):
        n = self._n
        c = n.cfg
        g = convert.map_to_grid(m, c['map_transpose'], c['map_free_is_high'])
        msg = OccupancyGrid()
        msg.header.stamp = n.get_clock().now().to_msg()
        msg.header.frame_id = c['map_frame']
        msg.info.map_load_time = msg.header.stamp
        msg.info.resolution = g.resolution
        msg.info.width, msg.info.height = g.width, g.height
        msg.info.origin.position.x = g.origin_x
        msg.info.origin.position.y = g.origin_y
        msg.info.origin.orientation.w = 1.0
        msg.data = g.data  # array('b'): rclpy fast path
        n.pub_map.publish(msg)


class MapperDriver(Node):
    """Owner of the Mapper TCP link (configure/activate/deactivate)."""

    def __init__(self, **kwargs):
        super().__init__('mapper_driver', **kwargs)
        # dynamic typing: launch may pass ints for double params (range_max:=40);
        # check_params casts by the default's type
        desc = ParameterDescriptor(dynamic_typing=True)
        for key, default in PARAMS.items():
            self.declare_parameter(key, default, desc)
        # NB: no attribute names that shadow rclpy.Node internals (see ros2.md)
        self.cfg = dict(PARAMS)
        self.pub_scan = self.pub_imu = self.pub_pose = None
        self.pub_map = self.pub_diag = None
        self._worker = None
        self._diag_timer = self._hb_timer = None
        self._tf_buf = self._tf_listener = None
        self._tf_dyn = self._tf_static = None

    # -- lifecycle ----------------------------------------------------------
    def on_configure(self, state):
        raw = {k: self.get_parameter(k).value for k in PARAMS}
        cfg, errors = check_params(raw, PARAMS)
        if errors:
            for err in errors:
                self.get_logger().error(f'invalid parameter: {err}')
            return TransitionCallbackReturn.FAILURE
        self.cfg = cfg
        c = self.cfg
        self.pub_scan = self.create_lifecycle_publisher(
            LaserScan, '/rccar/lidar/scan', qos_profile_sensor_data)
        self.pub_imu = self.create_lifecycle_publisher(
            Imu, '/rccar/lidar/imu', qos_profile_sensor_data)
        self.pub_pose = self.create_lifecycle_publisher(
            PoseStamped, '/rccar/mapper/pose', qos_profile_sensor_data)
        self.pub_map = self.create_lifecycle_publisher(
            OccupancyGrid, '/rccar/mapper/map', MAP_QOS)
        self.pub_diag = self.create_lifecycle_publisher(
            DiagnosticArray, '/diagnostics', 10)
        if c['publish_tf']:
            self._tf_buf = Buffer()
            self._tf_listener = TransformListener(self._tf_buf, self)
            self._tf_dyn = TransformBroadcaster(self)
        client = MapperClient(c['host'], int(c['port']), float(c['timeout_s']))
        self._worker = MapperWorker(
            client, _RosSink(self),
            {'scan': 1.0 / c['scan_rate_hz'], 'imu': 1.0 / c['imu_rate_hz'],
             'pose': 1.0 / c['pose_rate_hz'], 'map': c['map_period_s'],
             'health': c['health_period_s']},
            reconnect_max_s=float(c['reconnect_max_s']), log=self._log,
            map_max_cells=int(c['map_max_cells']))
        # Not fatal: the Mapper needs ~40 s to boot; the worker keeps retrying.
        if not self._worker.connect_once():
            self.get_logger().warning(
                f'Mapper {c["host"]}:{c["port"]} not reachable yet; will keep retrying')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        if self.cfg['publish_tf'] and self._tf_static is None:
            self._tf_static = StaticTransformBroadcaster(self)
            self._tf_static.sendTransform(self._identity_tf())
        if not self._worker.start():
            self.get_logger().error('previous IO thread still running; cannot activate')
            return TransitionCallbackReturn.FAILURE
        self._diag_timer = self.create_timer(
            float(self.cfg['health_period_s']), self._publish_diagnostics)
        self._hb_timer = self.create_timer(HB_PERIOD_S, self._beat)
        return super().on_activate(state)

    def on_deactivate(self, state):
        self._stop_io()
        return super().on_deactivate(state)

    def on_cleanup(self, state):
        self._stop_io()
        self._teardown()
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state):
        self._stop_io()
        self._teardown()
        return TransitionCallbackReturn.SUCCESS

    def _stop_io(self):
        for name in ('_diag_timer', '_hb_timer'):
            timer = getattr(self, name)
            if timer is not None:
                self.destroy_timer(timer)
                setattr(self, name, None)
        if self._worker is not None:
            self._worker.stop()

    def _teardown(self):
        self._worker = None
        for name in ('pub_scan', 'pub_imu', 'pub_pose', 'pub_map', 'pub_diag'):
            pub = getattr(self, name)
            if pub is not None:
                self.destroy_lifecycle_publisher(pub)
                setattr(self, name, None)
        if self._tf_listener is not None:
            self._tf_listener.unregister()
        self._tf_listener = self._tf_buf = None
        for name in ('_tf_dyn', '_tf_static'):
            bc = getattr(self, name)
            if bc is not None:
                self.destroy_publisher(bc.pub_tf)
                setattr(self, name, None)

    def stop_io(self):
        """Stop the IO thread (process exit path)."""
        self._stop_io()

    def _log(self, level, text):
        # one call site per severity: rclpy forbids changing severity at a call site
        log = self.get_logger()
        if level == 'error':
            log.error(text)
        elif level == 'warn':
            log.warning(text)
        elif level == 'debug':
            log.debug(text)
        else:
            log.info(text)

    # -- TF -------------------------------------------------------------------
    def _identity_tf(self):
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id = self.cfg['map_frame']
        tf.child_frame_id = self.cfg['odom_frame']
        tf.transform.rotation.w = 1.0
        return tf

    def publish_odom_tf(self, stamp, pose):
        """Broadcast odom->base_link, skipping while base->lidar is unknown."""
        c = self.cfg
        try:
            t = self._tf_buf.lookup_transform(
                c['base_frame'], c['lidar_frame'], Time(), Duration(seconds=0.0))
        except TransformException as exc:
            self.get_logger().warning(
                f'no {c["base_frame"]}->{c["lidar_frame"]} yet, skipping TF: {exc}',
                throttle_duration_sec=5.0)
            return
        r = t.transform.rotation
        base_to_lidar = (t.transform.translation.x, t.transform.translation.y,
                         quat_to_yaw(r.w, r.x, r.y, r.z))
        x, y, yaw = odom_to_base((pose.x, pose.y, pose.yaw), base_to_lidar)
        out = TransformStamped()
        out.header.stamp = stamp
        out.header.frame_id = c['odom_frame']
        out.child_frame_id = c['base_frame']
        out.transform.translation.x, out.transform.translation.y = x, y
        q = convert.yaw_to_quat(yaw)
        (out.transform.rotation.x, out.transform.rotation.y,
         out.transform.rotation.z, out.transform.rotation.w) = q
        self._tf_dyn.sendTransform(out)

    # -- timers (executor thread; read worker state only) ----------------------
    def _publish_diagnostics(self):
        if self._worker is None or self.pub_diag is None:
            return
        up, version, health, temp, age = self._worker.snapshot()
        level, message = link_level(up, health, age)
        st = DiagnosticStatus()
        st.level = bytes([level])
        st.name = 'mapper_driver: link'
        st.message = message
        st.hardware_id = str(self.cfg['host'])
        st.values = [
            KeyValue(key='host', value=str(self.cfg['host'])),
            KeyValue(key='sdp_version', value=version),
            KeyValue(key='last_scan_age_s',
                     value='' if age is None else f'{age:.2f}'),
            KeyValue(key='board_temperature_c',
                     value='' if temp is None else f'{temp:.1f}'),
        ]
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.status = [st]
        self.pub_diag.publish(msg)

    def _beat(self):
        if self._worker is None:
            return
        up, _, _, _, age = self._worker.snapshot()
        if up and age is not None and age < SCAN_FRESH_S:
            touch(self.cfg['heartbeat_file'])


def main(args=None):
    rclpy.init(args=args)
    node = MapperDriver()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.stop_io()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
