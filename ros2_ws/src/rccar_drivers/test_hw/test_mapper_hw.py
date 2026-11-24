"""
Hardware acceptance test of the PHYSICAL lidar (make lidar-hw-test). Not run by colcon test.

Launches its own mapper_driver (lifecycle, auto configure/activate) and a zero
base_link->lidar_link static transform, then checks the real topics against the criteria in
rccar_drivers/hw_criteria.py and writes logs/hw_test_lidar_<UTC>.json.

Preconditions: car stationary, ESC power OFF, compose `drivers` service stopped
(make drivers-stop). Read-only: the driver only sends getters; nothing here sends commands.
Env: RCCAR_HW_TEST=1 (required), MAPPER_HOST (default 192.168.11.1), RCCAR_LOG_DIR,
RCCAR_GIT_SHA.
"""
import datetime
import json
import math
import os
import time
import unittest

import launch
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.events import matches_action
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
import launch_testing.actions
from lifecycle_msgs.msg import Transition
from rccar_drivers import hw_criteria as hc
from rccar_drivers.mapper_node import PARAMS
import rclpy
from rclpy.qos import (
    DurabilityPolicy, qos_profile_sensor_data, QoSProfile, ReliabilityPolicy)
from rclpy.time import Time

ENABLED = os.environ.get('RCCAR_HW_TEST') == '1'
HOST = os.environ.get('MAPPER_HOST', '192.168.11.1')
LOG_DIR = os.environ.get('RCCAR_LOG_DIR', '/ws/src/racecar/logs')
GIT_SHA = os.environ.get('RCCAR_GIT_SHA', 'unknown')

PRECONDITIONS = ('PRECONDITIONS: car stationary, ESC power OFF, `drivers` service stopped '
                 '(make drivers-stop). Read-only test (getters only).')


def generate_test_description():
    if not ENABLED:
        return launch.LaunchDescription([launch_testing.actions.ReadyToTest()])
    driver = LifecycleNode(
        package='rccar_drivers', executable='mapper_driver', name='mapper_driver',
        namespace='', output='screen', parameters=[{'host': HOST}])
    return launch.LaunchDescription([
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--x', '0', '--y', '0', '--z', '0', '--frame-id', 'base_link',
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


@unittest.skipUnless(ENABLED, 'set RCCAR_HW_TEST=1 (make lidar-hw-test)')
class TestMapperHardware(unittest.TestCase):
    """Collect once in setUpClass, evaluate one criterion per test, write the report."""

    results = []
    extra = {}
    abort = None

    @classmethod
    def setUpClass(cls):
        from diagnostic_msgs.msg import DiagnosticArray
        from nav_msgs.msg import OccupancyGrid
        from geometry_msgs.msg import PoseStamped
        from sensor_msgs.msg import Imu, LaserScan
        from tf2_ros import Buffer, TransformListener
        print('\n' + PRECONDITIONS)
        rclpy.init()
        cls.node = n = rclpy.create_node('mapper_hw_test')
        cls.t0 = time.monotonic()
        cls.diag, cls.scan, cls.imu, cls.pose, cls.grid = [], [], [], [], None

        def now():
            return time.monotonic()

        def on_diag(msg):
            for st in msg.status:
                if st.name == 'mapper_driver: link':
                    cls.diag.append((now() - cls.t0, st.level))
                    for kv in st.values:
                        if kv.key == 'sdp_version' and kv.value:
                            cls.extra['sdp_version'] = kv.value
                        if kv.key == 'imu_avail_bitmap' and kv.value:
                            cls.extra['imu_avail_bitmap'] = kv.value

        def on_scan(m):
            cls.scan.append((now(), m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                             m.header.frame_id, list(m.ranges)))

        def on_imu(m):
            q = m.orientation
            cls.imu.append((now(), m.linear_acceleration, m.angular_velocity,
                            (q.x, q.y, q.z, q.w), m.linear_acceleration_covariance[0]))

        def on_pose(m):
            q = m.pose.orientation
            yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
            cls.pose.append((now(), m.pose.position.x, m.pose.position.y, yaw))

        def on_map(m):
            if cls.grid is None:
                cls.grid = {'t': now() - cls.t0, 'width': m.info.width,
                            'height': m.info.height, 'resolution': m.info.resolution,
                            'data': list(m.data)}

        n.create_subscription(DiagnosticArray, '/diagnostics', on_diag, 10)
        n.create_subscription(LaserScan, '/rccar/lidar/scan', on_scan, qos_profile_sensor_data)
        n.create_subscription(Imu, '/rccar/lidar/imu', on_imu, qos_profile_sensor_data)
        n.create_subscription(PoseStamped, '/rccar/mapper/pose', on_pose,
                              qos_profile_sensor_data)
        n.create_subscription(
            OccupancyGrid, '/rccar/mapper/map', on_map,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL))
        cls.buf = Buffer()
        cls.listener = TransformListener(cls.buf, n)

        # publisher pre-check (own driver must be the only one)
        cls._spin_until(lambda: n.count_publishers('/rccar/lidar/scan') >= 1, 20.0)
        # allow discovery of a foreign publisher
        cls._spin_until(lambda: False, 2.0)
        cls.pub_count = n.count_publishers('/rccar/lidar/scan')
        if not hc.eval_single_publisher(cls.pub_count)[0]:
            cls.abort = hc.eval_single_publisher(cls.pub_count)[1]
            return
        print('waiting for Mapper link (up to %.0f s) ...' % hc.CONNECT_TIMEOUT_S)
        cls._spin_until(lambda: any(hc._level_int(lv) == 0 for _, lv in cls.diag),
                        hc.CONNECT_TIMEOUT_S)
        print('waiting for first map (up to %.0f s) ...' % hc.MAP_TIMEOUT_S)
        cls._spin_until(lambda: cls.grid is not None, hc.MAP_TIMEOUT_S)
        cls._spin_until(lambda: cls.buf.can_transform('map', 'base_link', Time()), 10.0)
        print('measuring %.0f s (car must stay stationary) ...' % hc.WINDOW_S)
        cls.w0 = now()
        cls._spin_until(lambda: False, hc.WINDOW_S)
        cls.w1 = now()
        cls.tf_ok = cls.buf.can_transform('map', 'base_link', Time())

    @classmethod
    def _spin_until(cls, pred, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end and not pred():
            rclpy.spin_once(cls.node, timeout_sec=0.05)

    @classmethod
    def tearDownClass(cls):
        try:
            cls._report()
        finally:
            cls.node.destroy_node()
            rclpy.shutdown()

    # -- helpers ------------------------------------------------------------------------
    @classmethod
    def _window(cls, samples):
        return [s for s in samples if cls.w0 <= s[0] <= cls.w1]

    @classmethod
    def _avail(cls):
        """IMU availability bitmap seen in /diagnostics (None: not observed => legacy)."""
        return hc.parse_avail(cls.extra.get('imu_avail_bitmap'))

    def _check(self, name, threshold, result):
        passed, detail = result
        status = hc.to_status(passed)
        type(self).results.append({'criterion': name, 'status': status,
                                   'passed': status != hc.FAIL,
                                   'threshold': threshold, 'measured': detail})
        self.assertNotEqual(status, hc.FAIL, '%s: %s' % (name, detail))

    def _need(self):
        if self.abort:
            self.fail(self.abort)

    # -- criteria (alphabetical = run order) -----------------------------------------
    def test_00_single_publisher(self):
        self._check('precheck: single scan publisher', '== 1',
                    hc.eval_single_publisher(self.pub_count))

    def test_01_link(self):
        self._need()
        self._check('link OK', '<= %.0f s' % hc.CONNECT_TIMEOUT_S, hc.eval_link(self.diag))

    def test_10_scan_rate(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan rate', '>= %.1f Hz' % hc.SCAN_MIN_HZ,
                    hc.eval_rate([s[0] for s in w], hc.WINDOW_S, hc.SCAN_MIN_HZ))

    def test_11_scan_gap(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan gap', '<= %.1f s' % hc.MAX_SCAN_GAP_S,
                    hc.eval_gap([s[0] for s in w]))

    def test_12_scan_length(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan ranges == n_bins', '== %d' % PARAMS['n_bins'],
                    hc.eval_scan_length([len(s[3]) for s in w], PARAMS['n_bins']))

    def test_13_scan_finite(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan finite fraction', '>= %.2f' % hc.SCAN_MIN_FINITE_FRACTION,
                    hc.eval_finite_fraction([s[3] for s in w]))

    def test_14_scan_bounds(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan range bounds',
                    '[%.2f, %.2f]' % (PARAMS['range_min'], PARAMS['range_max']),
                    hc.eval_range_bounds([s[3] for s in w], PARAMS['range_min'],
                                         PARAMS['range_max']))

    def test_15_scan_frame(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan frame_id', PARAMS['lidar_frame'],
                    hc.eval_frame([s[2] for s in w], PARAMS['lidar_frame']))

    def test_16_scan_stamps(self):
        self._need()
        w = self._window(self.scan)
        self._check('scan stamps monotonic', '0 backwards',
                    hc.eval_stamps_monotonic([s[1] for s in w]))

    def test_20_imu_rate(self):
        self._need()
        w = self._window(self.imu)
        want = hc.IMU_MIN_RATE_FRACTION * PARAMS['imu_rate_hz']
        self._check('imu rate', '>= %.1f Hz' % want,
                    hc.eval_rate([s[0] for s in w], hc.WINDOW_S, want))

    def test_21_imu_units(self):
        self._need()
        w = self._window(self.imu)
        accs = [(s[1].x, s[1].y, s[1].z) for s in w]
        acc_provided = any(s[4] != -1.0 for s in w)
        res = hc.eval_imu_acc_units(accs, self._avail(), acc_provided)
        if res[0] == hc.PASS:
            type(self).extra['imu_units'] = hc.classify_acc_units(
                sum(math.sqrt(x * x + y * y + z * z) for x, y, z in accs) / len(w))
        else:
            type(self).extra.setdefault('imu_units', 'unknown')
        self._check('imu acc units (rest)', 'm/s^2 [%.1f,%.1f] or g [%.1f,%.1f]' % (
            hc.ACC_MS2_RANGE + hc.ACC_G_RANGE), res)

    def test_22_imu_gyro(self):
        self._need()
        w = self._window(self.imu)
        self._check('imu gyro z at rest', '< %.2f rad/s' % hc.GYRO_Z_REST_MAX,
                    hc.eval_imu_gyro_rest([s[2].z for s in w], self._avail()))

    def test_23_imu_quat(self):
        self._need()
        w = self._window(self.imu)
        self._check('imu quaternion norm', '1 +- %.2f' % hc.QUAT_NORM_TOL,
                    hc.eval_quat_norm([s[3] for s in w]))

    def test_24_imu_quat_provided(self):
        self._need()
        self._check('imu quaternion provided', 'QUATERNION bit set',
                    hc.eval_imu_quat_provided(self._avail()))

    def test_30_pose_rate(self):
        self._need()
        w = self._window(self.pose)
        self._check('pose rate', '>= %.1f Hz' % hc.POSE_MIN_HZ,
                    hc.eval_rate([s[0] for s in w], hc.WINDOW_S, hc.POSE_MIN_HZ))

    def test_31_pose_finite(self):
        self._need()
        w = self._window(self.pose)
        self._check('pose finite', 'all finite', hc.eval_pose_finite([s[1:] for s in w]))

    def test_32_pose_drift(self):
        self._need()
        w = self._window(self.pose)
        self._check('pose drift (stationary)', '< %.2f m, < %.0f deg' % (
            hc.POSE_MAX_DRIFT_M, hc.POSE_MAX_DRIFT_DEG),
            hc.eval_pose_drift([s[1:] for s in w]))

    def test_33_pose_yaw_rate_rest(self):
        self._need()
        w = self._window(self.pose)
        self._check('pose yaw rate (stationary)',
                    '|mean| < %.2f rad/s' % hc.POSE_YAW_RATE_REST_MAX,
                    hc.eval_pose_yaw_rate_rest([(s[0], s[3]) for s in w]))

    def test_40_map_received(self):
        self._need()
        self._check('map received', '<= %.0f s' % hc.MAP_TIMEOUT_S,
                    hc.eval_map_received(self.grid))

    def test_41_map_resolution(self):
        self._need()
        self._check('map resolution', '%.2f +- %.2f' % (
            hc.MAP_RESOLUTION, hc.MAP_RESOLUTION_TOL), hc.eval_map_resolution(self.grid))

    def test_42_map_known(self):
        self._need()
        self._check('map known cells', '>= %.0f %%' % (100 * hc.MAP_MIN_KNOWN_FRACTION),
                    hc.eval_map_known(self.grid))

    def test_50_tf(self):
        self._need()
        self._check('tf map->base_link', 'resolvable', hc.eval_tf(self.tf_ok))

    # -- report -------------------------------------------------------------------------
    @classmethod
    def _report(cls):
        res = cls.results
        width = max([len(r['criterion']) for r in res] + [9])
        print('\n%-*s  %-6s  %s' % (width, 'criterion', 'RESULT', 'measured'))
        for r in res:
            print('%-*s  %-6s  %s' % (width, r['criterion'], r['status'], r['measured']))
        overall = hc.overall([r['status'] for r in res])
        ok = overall == hc.PASS
        counts = {k: sum(1 for r in res if r['status'] == k) for k in (hc.PASS, hc.FAIL, hc.NA)}
        print('OVERALL: %s (%d PASS, %d FAIL, %d NA of %d)' % (
            overall, counts[hc.PASS], counts[hc.FAIL], counts[hc.NA], len(res)))
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        report = {'utc': stamp, 'git_sha': GIT_SHA, 'mapper_host': HOST,
                  'sdp_version': cls.extra.get('sdp_version', ''),
                  'imu_units': cls.extra.get('imu_units', ''),
                  'imu_avail_bitmap': cls.extra.get('imu_avail_bitmap', ''),
                  'overall_pass': ok, 'criteria': res}
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            path = os.path.join(LOG_DIR, 'hw_test_lidar_%s.json' % stamp)
            with open(path, 'w') as f:
                json.dump(report, f, indent=2)
            print('report: %s' % path)
        except OSError as e:
            print('WARN: report not written (%s)' % e)
