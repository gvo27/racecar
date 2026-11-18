"""Pure converters from decoded Slamtec data to plain values (no rclpy)."""
from array import array
from collections import namedtuple
import math

NO_RETURN = 100000.0

ScanArrays = namedtuple(
    'ScanArrays', 'angle_min angle_max angle_increment ranges')
GridArrays = namedtuple(
    'GridArrays', 'width height resolution origin_x origin_y data')


def scan_to_ranges(points, n_bins=1080, range_min=0.0, range_max=40.0):
    """
    Bin (angle, dist, valid) points into a uniform LaserScan layout.

    Bins cover [-pi, pi); the nearest return wins on collision; empty bins
    are inf.
    """
    inc = 2.0 * math.pi / n_bins
    angle_min = -math.pi
    ranges = [float('inf')] * n_bins
    for angle, dist, valid in points:
        if not valid or dist == NO_RETURN or not range_min <= dist <= range_max:
            continue
        k = round((angle - angle_min) / inc) % n_bins
        if dist < ranges[k]:
            ranges[k] = dist
    return ScanArrays(angle_min, angle_min + inc * (n_bins - 1), inc, ranges)


def cell_to_occupancy(u8, free_is_high=False):
    """
    Map a Slamtec Bitmap8Bit cell to OccupancyGrid (-1 unknown, 0 free, 100 occ).

    Bench-confirmed (2026-11-02, real Mapper M2M1, open room): 0 -> unknown,
    1..127 -> free, 128..255 -> occupied. free_is_high=True swaps free and
    occupied, kept for other firmware versions.
    """
    if u8 == 0:
        return -1
    return 0 if (u8 >= 128) == free_is_high else 100


def _lut(free_is_high):
    """256-byte table: raw cell -> OccupancyGrid value as an unsigned byte (-1 -> 255)."""
    return bytes(cell_to_occupancy(v, free_is_high) & 0xFF for v in range(256))


_LUTS = {True: _lut(True), False: _lut(False)}


def map_to_grid(m, transpose=False, free_is_high=False):
    """
    Convert MapData to OccupancyGrid arrays (data is array('b'), int8).

    Default assumes row-major with x fastest (index = y * width + x). With
    transpose=True the buffer is read as x-major (index = x * height + y),
    for the case where the bench shows the orientation is flipped.
    Uses bytes.translate with a LUT: C speed, no per-cell Python loop.
    """
    w, h = m.width, m.height
    cells = bytes(m.cells)
    if transpose:
        # row y = cells[y], cells[y + h], ... (x = 0..w-1)
        raw = b''.join(cells[y:w * h:h] for y in range(h))
    else:
        raw = cells[:w * h]
    data = array('b', raw.translate(_LUTS[bool(free_is_high)]))
    return GridArrays(w, h, m.resolution, m.origin_x, m.origin_y, data)


def yaw_to_quat(yaw):
    """Return the (x, y, z, w) quaternion for a rotation about +Z."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))
