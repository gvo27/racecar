"""Pure formatting + planar helpers for the lidar IMU monitor (no rclpy).

quat_to_yaw / wrap_angle / planar_speed duplicate the math of
rccar_drivers.slamtec.vehicle_state on purpose: this package stays decoupled
from the driver package.
"""
from datetime import datetime, timezone
import math

from rccar_calibration.rangefinder_format import RateEstimator

__all__ = ['HEADER', 'RateEstimator', 'Throttle', 'format_line', 'log_filename',
           'make_record', 'planar_speed', 'quat_to_yaw', 'wrap_angle']

HEADER = ('columns: pi <Pi time s>  heading <deg, SLAM pose yaw>  '
          'imu_heading <deg, IMU quaternion yaw>  yaw_rate <deg/s, gyro z>  '
          'acc_long <m/s2, raw units TBD>  acc_lat <m/s2, raw units TBD>  '
          'speed <m/s, from SLAM poses>  <IMU rate Hz>')


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


def format_line(pi_time_s, heading_deg, imu_heading_deg, yaw_rate_dps,
                acc_long, acc_lat, speed_mps, rate_hz) -> str:
    """One monitor line; heading/speed are None until two poses arrived."""
    return '  '.join([
        f'pi {pi_time_s:.3f}',
        f'heading {_num(heading_deg, ".1f")} deg',
        f'imu_heading {imu_heading_deg:.1f} deg',
        f'yaw_rate {yaw_rate_dps:.1f} dps',
        f'acc_long {acc_long:.2f}',
        f'acc_lat {acc_lat:.2f}',
        f'speed {_num(speed_mps, ".2f")} m/s',
        f'{rate_hz:.1f} Hz',
    ])


def _clean(v):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v


def make_record(pi_time_s, heading_deg, imu_heading_deg, yaw_rate_dps,
                acc_long, acc_lat, speed_mps, rate_hz) -> dict:
    """JSON-serialisable record for one printed line (non-finite -> None)."""
    return {
        'pi_time_s': _clean(pi_time_s),
        'heading_deg': _clean(heading_deg),
        'imu_heading_deg': _clean(imu_heading_deg),
        'yaw_rate_dps': _clean(yaw_rate_dps),
        'acc_long': _clean(acc_long),
        'acc_lat': _clean(acc_lat),
        'speed_mps': _clean(speed_mps),
        'imu_rate_hz': _clean(rate_hz),
    }


def log_filename(epoch_s: float) -> str:
    """lidar_imu_<UTC YYYYmmddTHHMMSSZ>.jsonl for a wall-clock time."""
    stamp = datetime.fromtimestamp(epoch_s, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'lidar_imu_{stamp}.jsonl'
