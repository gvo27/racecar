"""Pure formatting + rate helpers for the rangefinder monitor (no rclpy)."""
from collections import deque
import math

HEADER = ('columns: mcu <MCU stamp s>  pi <Pi receive time s>  range <m> (<cm>)'
          '  [latency pi-mcu ms]  [flags]  rate <Hz>')


class RateEstimator:
    """Message rate in Hz over the last ``window_s`` seconds."""

    def __init__(self, window_s: float = 2.0):
        self.window_s = window_s
        self._times = deque()

    def add(self, t: float) -> None:
        self._times.append(t)
        self._trim(t)

    def _trim(self, now: float) -> None:
        while self._times and now - self._times[0] > self.window_s:
            self._times.popleft()

    def rate(self, now=None) -> float:
        """Hz over the window; 0.0 with fewer than two samples."""
        if now is not None:
            self._trim(now)
        if len(self._times) < 2:
            return 0.0
        span = self._times[-1] - self._times[0]
        return (len(self._times) - 1) / span if span > 0 else 0.0


def describe_range(range_m: float, min_range: float, max_range: float) -> str:
    """Human text for a Range value following REP-117 (+inf no return, -inf too close)."""
    if math.isnan(range_m):
        return 'invalid (nan)'
    if math.isinf(range_m):
        return 'no return' if range_m > 0 else 'too close (-inf)'
    text = f'range {range_m:.3f} m ({range_m * 100.0:.1f} cm)'
    if range_m < min_range or range_m > max_range:
        text += ' out of range'
    return text


def format_line(stamp_sec: int, stamp_nanosec: int, recv_time_s: float,
                range_m: float, min_range: float, max_range: float,
                rate_hz=None) -> str:
    """One monitor line: MCU stamp, Pi receive time, range, latency, rate."""
    synced = stamp_sec != 0 or stamp_nanosec != 0
    if synced:
        mcu_s = stamp_sec + stamp_nanosec * 1e-9
        mcu = f'mcu {stamp_sec}.{stamp_nanosec:09d}'
    else:
        mcu = 'mcu unsynced'
    parts = [mcu, f'pi {recv_time_s:.3f}',
             describe_range(range_m, min_range, max_range)]
    if synced:
        parts.append(f'latency {(recv_time_s - mcu_s) * 1000.0:.1f} ms')
    if rate_hz is not None:
        parts.append(f'{rate_hz:.1f} Hz')
    return '  '.join(parts)
