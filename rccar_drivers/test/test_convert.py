"""Scan binning, occupancy mapping, quaternion helper."""
import math
import time

import pytest

from rccar_drivers.slamtec import convert as c
from rccar_drivers.slamtec.protocol import MapData


def test_scan_layout():
    s = c.scan_to_ranges([], n_bins=360)
    assert s.angle_min == -math.pi
    assert s.angle_increment == pytest.approx(2 * math.pi / 360)
    assert s.angle_max == pytest.approx(-math.pi + s.angle_increment * 359)
    assert len(s.ranges) == 360 and all(math.isinf(r) for r in s.ranges)


def test_scan_default_bins():
    assert len(c.scan_to_ranges([]).ranges) == 1080


def test_scan_binning_and_filters():
    inc = 2 * math.pi / 360
    pts = [(0.0, 2.0, True),
           (0.0, 1.5, True),            # nearer wins
           (inc * 10, 100000.0, True),  # no return
           (inc * 20, 3.0, False),      # invalid
           (inc * 30, 50.0, True),      # beyond range_max
           (inc * 40, 0.02, True)]      # below range_min
    s = c.scan_to_ranges(pts, n_bins=360, range_min=0.05)
    k0 = 180
    assert s.ranges[k0] == 1.5
    assert sum(1 for r in s.ranges if math.isfinite(r)) == 1


def test_scan_wraps_at_pi():
    s = c.scan_to_ranges([(math.pi, 2.0, True)], n_bins=360)
    assert s.ranges[0] == 2.0


def test_cell_to_occupancy():
    assert c.cell_to_occupancy(0) == -1
    assert c.cell_to_occupancy(1) == 100
    assert c.cell_to_occupancy(127) == 100
    assert c.cell_to_occupancy(128) == 0
    assert c.cell_to_occupancy(255) == 0


def test_map_to_grid_row_major():
    m = MapData(3, 2, 0.05, -1.0, -2.0, bytes([0, 1, 255, 255, 0, 1]))
    g = c.map_to_grid(m)
    assert (g.width, g.height, g.resolution) == (3, 2, 0.05)
    assert (g.origin_x, g.origin_y) == (-1.0, -2.0)
    assert list(g.data) == [-1, 100, 0, 0, -1, 100]


def test_map_to_grid_transpose():
    # x-major buffer: index = x * height + y
    m = MapData(3, 2, 0.05, 0.0, 0.0, bytes([0, 1, 255, 255, 0, 1]))
    g = c.map_to_grid(m, transpose=True)
    assert list(g.data) == [-1, 0, -1, 100, 0, 100]


def test_yaw_to_quat():
    assert c.yaw_to_quat(0.0) == (0.0, 0.0, 0.0, 1.0)
    x, y, z, w = c.yaw_to_quat(math.pi)
    assert z == pytest.approx(1.0) and w == pytest.approx(0.0, abs=1e-12)


def test_free_is_high_false_swaps_meaning():
    assert c.cell_to_occupancy(0, free_is_high=False) == -1
    assert c.cell_to_occupancy(1, free_is_high=False) == 0
    assert c.cell_to_occupancy(255, free_is_high=False) == 100
    m = MapData(3, 2, 0.05, 0.0, 0.0, bytes([0, 1, 255, 255, 0, 1]))
    g = c.map_to_grid(m, free_is_high=False)
    assert list(g.data) == [-1, 0, 100, 100, -1, 0]


def test_map_to_grid_is_int8_array():
    m = MapData(3, 2, 0.05, 0.0, 0.0, bytes([0, 1, 255, 255, 0, 1]))
    assert c.map_to_grid(m).data.typecode == 'b'


def test_map_to_grid_large_is_fast():
    n = 2000
    cells = bytes(range(256)) * (n * n // 256 + 1)
    m = MapData(n, n, 0.05, 0.0, 0.0, cells[:n * n])
    for transpose in (False, True):
        t0 = time.perf_counter()
        g = c.map_to_grid(m, transpose=transpose)
        assert time.perf_counter() - t0 < 0.5
        assert len(g.data) == n * n


def test_map_to_grid_transpose_matches_naive():
    w, h = 5, 3
    cells = bytes([(i * 37) % 256 for i in range(w * h)])
    m = MapData(w, h, 0.05, 0.0, 0.0, cells)
    g = c.map_to_grid(m, transpose=True)
    naive = [c.cell_to_occupancy(cells[x * h + y]) for y in range(h) for x in range(w)]
    assert list(g.data) == naive
