import math
import struct
import zlib

from rccar_calibration.lidar_snapshot_render import (
    encode_png, grid_to_rgb, render, scan_endpoints, upscale_factor, world_to_pixel)

META = {'width': 3, 'height': 2, 'resolution': 1.0, 'origin_x': 0.0, 'origin_y': 0.0,
        'origin_yaw': 0.0}


def decode(png):
    assert png[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, ihdr = 8, b'', None
    while pos < len(png):
        n = struct.unpack('>I', png[pos:pos + 4])[0]
        kind = png[pos + 4:pos + 8]
        body = png[pos + 8:pos + 8 + n]
        crc = struct.unpack('>I', png[pos + 8 + n:pos + 12 + n])[0]
        assert crc == zlib.crc32(kind + body) & 0xffffffff
        if kind == b'IHDR':
            ihdr = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    w, h = ihdr[0], ihdr[1]
    assert ihdr[2:] == (8, 2, 0, 0, 0)
    raw = zlib.decompress(idat)
    rows = []
    for r in range(h):
        line = raw[r * (w * 3 + 1):(r + 1) * (w * 3 + 1)]
        assert line[0] == 0
        rows.append([tuple(line[1 + 3 * c:4 + 3 * c]) for c in range(w)])
    return w, h, rows


def test_grid_colors_and_flip():
    # row 0 (bottom): unknown, free, occupied; row 1 (top): occupied, free(49), unknown
    rows = grid_to_rgb(3, 2, [-1, 0, 100, 100, 49, -1])
    assert rows[1][0:3] == bytes((128, 128, 128))
    assert rows[1][3:6] == bytes((255, 255, 255))
    assert rows[1][6:9] == bytes((0, 0, 0))
    assert rows[0][0:3] == bytes((0, 0, 0))
    assert rows[0][3:6] == bytes((255, 255, 255))
    assert rows[0][6:9] == bytes((128, 128, 128))


def test_png_header_and_pixels():
    w, h, rgb = render(META, [-1, 0, 100, 100, 49, -1])
    png = encode_png(w, h, rgb)
    pw, ph, px = decode(png)
    assert (pw, ph) == (w, h) == (3 * 266, 2 * 266)
    assert px[0][0] == (0, 0, 0)  # top-left = grid row 1, col 0
    assert px[0][-1] == (128, 128, 128)
    assert px[-1][0] == (128, 128, 128)
    assert px[-1][-1] == (0, 0, 0)


def test_encode_png_tiny():
    pw, ph, px = decode(encode_png(2, 1, bytes((1, 2, 3, 4, 5, 6))))
    assert (pw, ph) == (2, 1)
    assert px == [[(1, 2, 3), (4, 5, 6)]]


def test_endpoints_forward_and_yaw_rotation():
    scan = {'angle_min': 0.0, 'angle_increment': 0.1, 'ranges': [2.0],
            'range_min': 0.1, 'range_max': 10.0}
    x, y = scan_endpoints(scan, {'x': 1.0, 'y': 1.0, 'yaw': 0.0})[0]
    assert abs(x - 3.0) < 1e-9 and abs(y - 1.0) < 1e-9
    x, y = scan_endpoints(scan, {'x': 1.0, 'y': 1.0, 'yaw': math.pi / 2})[0]
    assert abs(x - 1.0) < 1e-9 and abs(y - 3.0) < 1e-9


def test_endpoints_filter_invalid():
    scan = {'angle_min': 0.0, 'angle_increment': 0.1,
            'ranges': [math.inf, math.nan, 0.01, 50.0, 1.0, None],
            'range_min': 0.1, 'range_max': 10.0}
    assert len(scan_endpoints(scan, {'x': 0.0, 'y': 0.0, 'yaw': 0.0})) == 1


def test_world_to_pixel():
    assert world_to_pixel(0.5, 0.5, META, 1) == (0, 1)  # bottom-left cell
    assert world_to_pixel(2.5, 1.5, META, 1) == (2, 0)  # top-right cell
    assert world_to_pixel(3.5, 0.5, META, 1) is None
    assert world_to_pixel(-0.1, 0.5, META, 1) is None
    assert world_to_pixel(0.5, 2.0, META, 1) is None
    assert world_to_pixel(0.5, 0.0, META, 2) == (1, 3)


def test_world_to_pixel_origin_yaw():
    meta = dict(META, origin_yaw=math.pi / 2)
    # grid +x axis points to world +y
    assert world_to_pixel(0.0, 0.5, meta, 1) == (0, 1)
    assert world_to_pixel(0.0, 2.5, meta, 1) == (2, 1)


def test_upscale_cap():
    assert upscale_factor(10, 10) == 80
    assert upscale_factor(4000, 100) == 1
    assert upscale_factor(1, 1, target=800, cap=100) == 100
    assert upscale_factor(5, 5, target=10000, cap=4096) * 5 <= 4096


def test_render_marks_scan_and_pose():
    meta = {'width': 20, 'height': 20, 'resolution': 1.0, 'origin_x': 0.0,
            'origin_y': 0.0, 'origin_yaw': 0.0}
    scan = {'angle_min': 0.0, 'angle_increment': 0.1, 'ranges': [5.0],
            'range_min': 0.1, 'range_max': 10.0}
    w, h, rgb = render(meta, [0] * 400, scan, {'x': 5.0, 'y': 10.0, 'yaw': 0.0})
    _, _, px = decode(encode_png(w, h, rgb))
    colors = {c for row in px for c in row}
    assert (220, 30, 30) in colors and (30, 90, 220) in colors


def test_render_scan_only():
    scan = {'angle_min': 0.0, 'angle_increment': 0.1, 'ranges': [2.0, 3.0],
            'range_min': 0.1, 'range_max': 10.0}
    w, h, rgb = render(None, None, scan, {'x': 0.0, 'y': 0.0, 'yaw': 0.0})
    assert len(rgb) == w * h * 3
    assert (30, 90, 220) in {c for r in decode(encode_png(w, h, rgb))[2] for c in r}
