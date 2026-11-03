"""
Pure formatting + planar helpers for the lidar IMU monitor (no rclpy).

quat_to_yaw / wrap_angle / planar_speed duplicate the math of
rccar_drivers.slamtec.vehicle_state on purpose: this package stays decoupled
from the driver package. Pose-derived yaw rate / accelerations: lidar_imu_pose.
"""
from datetime import datetime, timezone
import math

from rccar_calibration.rangefinder_format import RateEstimator

__all__ = ['HEADER', 'RateEstimator', 'SOURCE', 'Throttle', 'format_line', 'log_filename',
           'make_record', 'planar_speed', 'quat_to_yaw', 'wrap_angle']

HEADER = ('columns: pi <Pi time s>  heading <deg, SLAM pose yaw>  '
          'imu_heading <deg, IMU quaternion yaw, cross-check>  '
          'yaw_rate <deg/s, from pose yaw>  speed <m/s, from SLAM poses>  '
          'acc_long <m/s2, d(speed)/dt from poses>  '
          'acc_lat <m/s2, speed*yaw_rate from poses>  <IMU rate Hz>  '
          'imu_gyro <deg/s> / imu_acc <raw units> (n/a: not provided by the Mapper)  '
          'JUMP = pose jump (relocalization), estimator reset')

SOURCE = {
    'heading_deg': 'pose', 'imu_heading_deg': 'imu', 'yaw_rate_dps': 'pose',
    'speed_mps': 'pose', 'acc_long': 'pose', 'acc_lat': 'pose',
    'imu_gyro_z_dps': 'imu', 'imu_acc_x': 'imu', 'imu_acc_y': 'imu',
}


def quat_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Yaw (rad, about +z) of a quaternion; roll and pitch are ignored."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def wrap_angle(a: float) -> float:
    """Wrap an angle in rad to [-pi, pi)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def planar_speed(prev, cur):
    """Speed in m/s from two (x, y, t_s) poses; None if dt <= 0."""
    dt = cur[2] - prev[2]
    if dt <= 0.0:
        return None
    return math.hypot(cur[0] - prev[0], cur[1] - prev[1]) / dt


class Throttle:
    """Allow at most one event per ``period_s``."""

    def __init__(self, period_s: float):
        self.period_s = period_s
        self._last = None

    def ready(self, now: float) -> bool:
        if self._last is None or now - self._last >= self.period_s:
            self._last = now
            return True
        return False


def _num(v, fmt):
    return 'n/a' if v is None else format(v, fmt)


def format_line(pi_time_s, heading_deg, imu_heading_deg, yaw_rate_dps, speed_mps,
                acc_long, acc_lat, rate_hz, imu_gyro_dps=None, imu_acc=None,
                jump=False) -> str:
    """
    One monitor line; any value may be None (printed n/a).

    imu_gyro_dps / imu_acc (x, y) are the raw IMU values, None when the Mapper marks
    them not provided.
    """
    acc = 'n/a' if imu_acc is None else f'{imu_acc[0]:.2f},{imu_acc[1]:.2f}'
    parts = [
        f'pi {pi_time_s:.3f}',
        f'heading {_num(heading_deg, ".1f")} deg',
        f'imu_heading {_num(imu_heading_deg, ".1f")} deg',
        f'yaw_rate {_num(yaw_rate_dps, ".1f")} dps',
        f'speed {_num(speed_mps, ".2f")} m/s',
        f'acc_long {_num(acc_long, ".2f")}',
        f'acc_lat {_num(acc_lat, ".2f")}',
        f'{rate_hz:.1f} Hz',
        f'imu_gyro {_num(imu_gyro_dps, ".1f")} dps',
        f'imu_acc {acc}',
    ]
    if jump:
        parts.append('JUMP')
    return '  '.join(parts)


def _clean(v):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v


def make_record(pi_time_s, heading_deg, imu_heading_deg, yaw_rate_dps, speed_mps,
                acc_long, acc_lat, rate_hz, imu_gyro_dps=None, imu_acc=None,
                jump=False) -> dict:
    """JSON-serialisable record for one printed line (non-finite -> None)."""
    acc_x, acc_y = (None, None) if imu_acc is None else imu_acc
    return {
        'pi_time_s': _clean(pi_time_s),
        'heading_deg': _clean(heading_deg),
        'imu_heading_deg': _clean(imu_heading_deg),
        'yaw_rate_dps': _clean(yaw_rate_dps),
        'speed_mps': _clean(speed_mps),
        'acc_long': _clean(acc_long),
        'acc_lat': _clean(acc_lat),
        'imu_rate_hz': _clean(rate_hz),
        'imu_gyro_z_dps': _clean(imu_gyro_dps),
        'imu_acc_x': _clean(acc_x),
        'imu_acc_y': _clean(acc_y),
        'source': dict(SOURCE),
        'jump': bool(jump),
    }


def log_filename(epoch_s: float) -> str:
    """lidar_imu_<UTC YYYYmmddTHHMMSSZ>.jsonl for a wall-clock time."""
    stamp = datetime.fromtimestamp(epoch_s, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'lidar_imu_{stamp}.jsonl'
