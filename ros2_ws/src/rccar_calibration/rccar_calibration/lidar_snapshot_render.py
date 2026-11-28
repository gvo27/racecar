"""Pure PNG rendering of an OccupancyGrid + scan + pose for the lidar snapshot (no rclpy)."""
import math
import struct
import zlib

__all__ = ['encode_png', 'grid_to_rgb', 'render', 'scan_endpoints', 'upscale_factor',
           'world_to_pixel']

UNKNOWN = (128, 128, 128)
FREE = (255, 255, 255)
OCCUPIED = (0, 0, 0)
SCAN_COLOR = (220, 30, 30)
POSE_COLOR = (30, 90, 220)
POSE_RADIUS_PX = 6
HEADING_TICK_PX = 25
SCAN_ONLY_RESOLUTION = 0.05
SCAN_ONLY_MARGIN_M = 1.0


def _cell_color(value):
    if value < 0:
        return UNKNOWN
    return FREE if value < 50 else OCCUPIED


def grid_to_rgb(width, height, data):
    """
    Convert OccupancyGrid cells to RGB rows, top row first (+Y up).

    Grid row 0 is at the origin y (bottom), so rows are flipped. Each row is
    ``bytes`` of length 3 * width. Unknown (-1) grey, 0..49 white, >= 50 black.
    """
    rows = []
    for r in range(height - 1, -1, -1):
        row = bytearray()
        for value in data[r * width:(r + 1) * width]:
            row.extend(_cell_color(value))
        rows.append(bytes(row))
    return rows


def upscale_factor(width, height, target=800, cap=4096):
    """Integer scale >= 1 so the long side is about ``target`` px, never above ``cap``."""
    long_side = max(width, height, 1)
    scale = max(1, target // long_side)
    while scale > 1 and scale * long_side > cap:
        scale -= 1
    return scale


def scan_endpoints(scan, pose):
    """
    Map-frame (x, y) of every valid beam end.

    ``scan``: angle_min, angle_increment, ranges, range_min, range_max.
    ``pose``: x, y, yaw of lidar_link in the map frame. Angles are used as published.
    """
    pts = []
    for i, r in enumerate(scan['ranges']):
        if r is None or not math.isfinite(r):
            continue
        if r < scan['range_min'] or r > scan['range_max']:
            continue
        a = pose['yaw'] + scan['angle_min'] + i * scan['angle_increment']
        pts.append((pose['x'] + r * math.cos(a), pose['y'] + r * math.sin(a)))
    return pts


def world_to_pixel(x, y, map_meta, scale):
    """(col, row) in the flipped, upscaled image for a map-frame point; None if outside."""
    dx = x - map_meta['origin_x']
    dy = y - map_meta['origin_y']
    yaw = map_meta.get('origin_yaw', 0.0)
    gx = dx * math.cos(yaw) + dy * math.sin(yaw)
    gy = -dx * math.sin(yaw) + dy * math.cos(yaw)
    cx = gx / map_meta['resolution']
    cy = gy / map_meta['resolution']
    if not (0.0 <= cx < map_meta['width'] and 0.0 <= cy < map_meta['height']):
        return None
    col = int(cx * scale)
    # image row 0 = top = max y; cell row int(cy) maps exactly (no off-by-one at cell edges)
    row = map_meta['height'] * scale - 1 - int(cy * scale)
    return col, row


def _upscale(rows, scale):
    out = bytearray()
    for row in rows:
        wide = bytearray()
        for i in range(0, len(row), 3):
            wide.extend(row[i:i + 3] * scale)
        out.extend(bytes(wide) * scale)
    return out


def _put(canvas, w, h, x, y, color):
    if 0 <= x < w and 0 <= y < h:
        o = (y * w + x) * 3
        canvas[o:o + 3] = bytes(color)


def _square(canvas, w, h, cx, cy, side, color):
    lo = side // 2
    for yy in range(cy - lo, cy - lo + side):
        for xx in range(cx - lo, cx - lo + side):
            _put(canvas, w, h, xx, yy, color)


def _disc(canvas, w, h, cx, cy, radius, color):
    for yy in range(cy - radius, cy + radius + 1):
        for xx in range(cx - radius, cx + radius + 1):
            if (xx - cx) ** 2 + (yy - cy) ** 2 <= radius * radius:
                _put(canvas, w, h, xx, yy, color)


def _scan_only_meta(endpoints, pose):
    xs = [p[0] for p in endpoints] + [pose['x']]
    ys = [p[1] for p in endpoints] + [pose['y']]
    res = SCAN_ONLY_RESOLUTION
    x0 = min(xs) - SCAN_ONLY_MARGIN_M
    y0 = min(ys) - SCAN_ONLY_MARGIN_M
    width = int(math.ceil((max(xs) + SCAN_ONLY_MARGIN_M - x0) / res))
    height = int(math.ceil((max(ys) + SCAN_ONLY_MARGIN_M - y0) / res))
    return {'width': max(width, 1), 'height': max(height, 1), 'resolution': res,
            'origin_x': x0, 'origin_y': y0, 'origin_yaw': 0.0}


def render(map_meta, data, scan=None, pose=None):
    """
    Render the map with scan endpoints (red) and pose (blue dot + heading tick).

    Returns (width_px, height_px, rgb_bytes). Without a map but with scan and pose,
    the scan is drawn alone on a grey canvas (0.05 m/cell) around the pose.
    Raises ValueError when there is nothing to draw.
    """
    endpoints = scan_endpoints(scan, pose) if scan and pose else []
    if map_meta is None:
        if not (scan and pose):
            raise ValueError('need a map, or a scan and a pose')
        map_meta = _scan_only_meta(endpoints, pose)
        data = [-1] * (map_meta['width'] * map_meta['height'])
    scale = upscale_factor(map_meta['width'], map_meta['height'])
    rows = grid_to_rgb(map_meta['width'], map_meta['height'], data)
    w = map_meta['width'] * scale
    h = map_meta['height'] * scale
    canvas = _upscale(rows, scale)
    side = max(2, scale // 2)
    for x, y in endpoints:
        px = world_to_pixel(x, y, map_meta, scale)
        if px is not None:
            _square(canvas, w, h, px[0], px[1], side, SCAN_COLOR)
    if pose:
        px = world_to_pixel(pose['x'], pose['y'], map_meta, scale)
        if px is not None:
            _disc(canvas, w, h, px[0], px[1], POSE_RADIUS_PX, POSE_COLOR)
            yaw = pose['yaw'] - map_meta.get('origin_yaw', 0.0)
            for k in range(HEADING_TICK_PX + 1):
                _put(canvas, w, h, px[0] + int(round(k * math.cos(yaw))),
                     px[1] - int(round(k * math.sin(yaw))), POSE_COLOR)
    return w, h, bytes(canvas)


def _chunk(kind, payload):
    body = kind + payload
    return (struct.pack('>I', len(payload)) + body
            + struct.pack('>I', zlib.crc32(body) & 0xffffffff))


def encode_png(width, height, rgb_bytes):
    """Encode 8-bit RGB (3 * width * height bytes) as PNG, filter 0, zlib level 6."""
    stride = width * 3
    raw = bytearray()
    for r in range(height):
        raw.append(0)
        raw.extend(rgb_bytes[r * stride:(r + 1) * stride])
    return (b'\x89PNG\r\n\x1a\n'
            + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + _chunk(b'IDAT', zlib.compress(bytes(raw), 6))
            + _chunk(b'IEND', b''))
