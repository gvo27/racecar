"""Pure converters from decoded Slamtec data to plain values (no rclpy)."""
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


def cell_to_occupancy(u8, free_is_high=True):
    """
    Map a Slamtec Bitmap8Bit cell to OccupancyGrid (-1 unknown, 0 free, 100 occ).

    Convention from slamware_ros_sdk: the cell is a signed char; 0 -> unknown,
    negative (128..255 as uint8) -> free, positive -> occupied. Must be
    bench-verified against RoboStudio; free_is_high=False swaps free/occupied.
    """
    if u8 == 0:
        return -1
    return 0 if (u8 >= 128) == free_is_high else 100


_LUTS = {True: [cell_to_occupancy(v, True) for v in range(256)],
         False: [cell_to_occupancy(v, False) for v in range(256)]}


def map_to_grid(m, transpose=False, free_is_high=True):
    """
    Convert MapData to OccupancyGrid arrays.

    Default assumes row-major with x fastest (index = y * width + x). With
    transpose=True the buffer is read as x-major (index = x * height + y),
    for the case where the bench shows the orientation is flipped.
    """
    w, h = m.width, m.height
    cells = m.cells
    lut = _LUTS[bool(free_is_high)]
    if transpose:
        data = [lut[cells[x * h + y]] for y in range(h) for x in range(w)]
    else:
        data = [lut[c] for c in cells[:w * h]]
    return GridArrays(w, h, m.resolution, m.origin_x, m.origin_y, data)


def yaw_to_quat(yaw):
    """Return the (x, y, z, w) quaternion for a rotation about +Z."""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))
