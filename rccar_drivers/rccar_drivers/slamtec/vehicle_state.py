"""Planar vehicle-state helpers derived from SLAM pose and IMU (no rclpy)."""
from collections import deque
import math


def quat_to_yaw(w, x, y, z):
    """Return yaw (rad) of a quaternion."""
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def wrap_pi(a):
    """Wrap an angle to [-pi, pi)."""
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class SpeedEstimator:
    """Planar speed from successive (t, x, y) samples over a short window."""

    def __init__(self, window_s=0.3):
        self._window_s = window_s
        self._samples = deque()

    def update(self, t, x, y):
        """Add a sample; return speed in m/s or None until 2 usable samples."""
        if self._samples and t <= self._samples[-1][0]:
            return self.speed()
        self._samples.append((t, x, y))
        while (len(self._samples) > 2
               and t - self._samples[1][0] >= self._window_s):
            self._samples.popleft()
        return self.speed()

    def speed(self):
        """Return the current estimate or None."""
        if len(self._samples) < 2:
            return None
        t0, x0, y0 = self._samples[0]
        t1, x1, y1 = self._samples[-1]
        return math.hypot(x1 - x0, y1 - y0) / (t1 - t0)

    def reset(self):
        """Forget all samples."""
        self._samples.clear()


def planar_from_imu(acc, gyro):
    """Return (acc_long, acc_lat, yaw_rate) from ImuSample-like tuples."""
    return acc[0], acc[1], gyro[2]
