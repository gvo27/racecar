"""
Planar kinematics from the Mapper SLAM pose (no rclpy).

The Mapper IMU exports only an orientation on fw 2.6.0_dev (no rates), so yaw
rate and accelerations are derived from the 10 Hz pose stream:

- yaw_rate: finite difference of the unwrapped pose yaw over a ~0.3 s window, EMA-smoothed
- speed: distance between consecutive poses / dt (as before)
- acc_long: finite difference of speed over the same window, EMA-smoothed
- acc_lat: speed * yaw_rate (centripetal, a = v * omega)

A yaw step above JUMP_RAD between consecutive poses is treated as a relocalization or
loop closure: the estimator resets and the sample is flagged `jump`. For logging and
estimation only (10 Hz, ~100 ms latency), never for control.

wrap_angle is duplicated from rccar_calibration.lidar_imu_format / rccar_drivers on
purpose: this package stays decoupled from the driver package.
"""
from collections import deque
import math
from typing import NamedTuple, Optional

WINDOW_S = 0.3
EMA_ALPHA = 0.5
JUMP_RAD = 0.5
MAX_GAP_S = 1.0  # a longer pose gap is a dropout: restart instead of differentiating over it


def wrap_angle(a: float) -> float:
    """Wrap an angle in rad to [-pi, pi)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class Planar(NamedTuple):
    """One estimator output; derived values are None until enough poses arrived."""

    heading: float                # rad, wrapped pose yaw
    yaw_rate: Optional[float]     # rad/s
    speed: Optional[float]        # m/s
    acc_long: Optional[float]     # m/s^2
    acc_lat: Optional[float]      # m/s^2
    jump: bool


class _Ema:
    def __init__(self, alpha):
        self._alpha = alpha
        self.value = None

    def update(self, v):
        self.value = v if self.value is None else (
            self.value + self._alpha * (v - self.value))
        return self.value


class PlanarEstimator:
    """Feed (t_s, x, y, yaw) poses in order; get heading/yaw rate/speed/accelerations."""

    def __init__(self, window_s=WINDOW_S, alpha=EMA_ALPHA, jump_rad=JUMP_RAD,
                 max_gap_s=MAX_GAP_S):
        self._window_s = window_s
        self._alpha = alpha
        self._jump_rad = jump_rad
        self._max_gap_s = max_gap_s
        self.reset()

    def reset(self):
        """Forget all history (relocalization, stale input)."""
        self._yaw_hist = deque()    # (t, unwrapped yaw)
        self._speed_hist = deque()  # (t, speed)
        self._last = None           # (t, x, y, wrapped yaw)
        self._yaw_u = 0.0
        self._rate_f = _Ema(self._alpha)
        self._acc_f = _Ema(self._alpha)

    @staticmethod
    def _slope(hist, t, v, window_s):
        """(v - v_old) / (t - t_old) against the oldest sample inside the window."""
        while len(hist) > 1 and t - hist[1][0] >= window_s:
            hist.popleft()
        t0, v0 = hist[0]
        return None if t <= t0 else (v - v0) / (t - t0)

    def update(self, t, x, y, yaw) -> Planar:
        """Add one pose; returns the current estimate."""
        heading = wrap_angle(yaw)
        last = self._last
        if last is not None:
            dt = t - last[0]
            step = wrap_angle(heading - last[3])
            if dt <= 0.0:
                return Planar(heading, None, None, None, None, False)
            if abs(step) > self._jump_rad:
                self.reset()
                self._start(t, x, y, heading)
                return Planar(heading, None, None, None, None, True)
            if dt > self._max_gap_s:
                self.reset()
                self._start(t, x, y, heading)
                return Planar(heading, None, None, None, None, False)
            self._yaw_u += step
            speed = math.hypot(x - last[1], y - last[2]) / dt
        else:
            self._yaw_u = heading
            speed = None
        self._last = (t, x, y, heading)
        self._yaw_hist.append((t, self._yaw_u))
        if speed is None:
            return Planar(heading, None, None, None, None, False)
        self._speed_hist.append((t, speed))
        rate = self._slope(self._yaw_hist, t, self._yaw_u, self._window_s)
        if rate is not None:
            rate = self._rate_f.update(rate)
        acc = self._slope(self._speed_hist, t, speed, self._window_s)
        if acc is not None:
            acc = self._acc_f.update(acc)
        acc_lat = None if rate is None else speed * rate
        return Planar(heading, rate, speed, acc, acc_lat, False)

    def _start(self, t, x, y, heading):
        self._yaw_u = heading
        self._last = (t, x, y, heading)
        self._yaw_hist.append((t, heading))
