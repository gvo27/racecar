"""Pure statistics + text summary for the lidar snapshot (no rclpy)."""
from datetime import datetime, timezone
import math

from rccar_calibration.lidar_imu_format import quat_to_yaw
from rccar_calibration.lidar_snapshot_render import scan_endpoints, world_to_pixel

LEVEL_NAMES = {0: 'OK', 1: 'WARN', 2: 'ERROR', 3: 'STALE'}
LEGEND = ('map.png: white free, black occupied, grey unknown, red = current scan endpoints, '
          'blue dot + tick = Mapper pose/heading; +X right, +Y up (map frame)')
AGREEMENT_HINT = ('scan/map agreement = fraction of scan endpoints within 1 cell of an '
                  'occupied cell; low => mirrored scan (scan_angle_sign), wrong pose, '
                  'or the unit was moving')


def snapshot_dirname(t_unix):
    """lidar_snapshot_<UTC YYYYmmddTHHMMSSZ> for a wall-clock time."""
    stamp = datetime.fromtimestamp(t_unix, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'lidar_snapshot_{stamp}'


def json_safe(obj):
    """Copy of obj with non-finite floats replaced by None (valid JSON)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if hasattr(obj, 'item') and not isinstance(obj, (str, bytes)):
        return json_safe(obj.item())  # numpy scalar (rclpy array fields) -> plain python
    return obj


def _valid(scan):
    return [r for r in scan['ranges']
            if r is not None and math.isfinite(r)
            and scan['range_min'] <= r <= scan['range_max']]


def scan_stats(scan):
    """Beam count, valid fraction, min/median/max valid range (None if none), angle span."""
    beams = len(scan['ranges'])
    valid = sorted(_valid(scan))
    n = len(valid)
    if n == 0:
        median = None
    elif n % 2:
        median = valid[n // 2]
    else:
        median = 0.5 * (valid[n // 2 - 1] + valid[n // 2])
    span = math.degrees(abs(scan['angle_increment']) * max(beams - 1, 0))
    return {
        'beams': beams,
        'finite_fraction': (n / beams) if beams else 0.0,
        'min_range': valid[0] if n else None,
        'median_range': median,
        'max_range': valid[-1] if n else None,
        'angle_span_deg': span,
    }


def map_stats(map_meta, data):
    """Size, resolution, origin, unknown/free/occupied cell counts and known area."""
    unknown = sum(1 for v in data if v < 0)
    occupied = sum(1 for v in data if v >= 50)
    free = len(data) - unknown - occupied
    res = map_meta['resolution']
    return {
        'width': map_meta['width'], 'height': map_meta['height'], 'resolution': res,
        'origin': [map_meta['origin_x'], map_meta['origin_y'],
                   map_meta.get('origin_yaw', 0.0)],
        'unknown': unknown, 'free': free, 'occupied': occupied,
        'known_area_m2': (free + occupied) * res * res,
    }


def scan_map_agreement(endpoints, map_meta, data):
    """
    Fraction of endpoints within 1 cell (8-neighbourhood) of an occupied cell.

    Endpoints outside the map count as disagreeing. None if there are no
    endpoints or no map. Low => mirrored scan (scan_angle_sign), wrong pose,
    or the unit moving.
    """
    if not endpoints or map_meta is None or data is None:
        return None
    w, h = map_meta['width'], map_meta['height']
    hits = 0
    for x, y in endpoints:
        px = world_to_pixel(x, y, map_meta, 1)
        if px is None:
            continue
        col, row = px[0], h - 1 - px[1]
        found = False
        for rr in range(max(row - 1, 0), min(row + 1, h - 1) + 1):
            for cc in range(max(col - 1, 0), min(col + 1, w - 1) + 1):
                if data[rr * w + cc] >= 50:
                    found = True
        hits += found
    return hits / len(endpoints)


def imu_summary(imu):
    """Yaw (deg) from the quaternion and which fields the Mapper provides (cov[0] != -1)."""
    if imu is None:
        return None
    x, y, z, w = imu['orientation']
    return {
        'yaw_deg': math.degrees(quat_to_yaw(x, y, z, w)),
        'provided': {
            'orientation': imu['orientation_covariance0'] != -1,
            'angular_velocity': imu['angular_velocity_covariance0'] != -1,
            'linear_acceleration': imu['linear_acceleration_covariance0'] != -1,
        },
    }


def diag_summary(statuses):
    """Return the mapper_driver status as level name, message and key/values; None if absent."""
    for st in statuses or []:
        if 'mapper_driver' in st['name']:
            return {'name': st['name'],
                    'level': LEVEL_NAMES.get(st['level'], str(st['level'])),
                    'message': st['message'],
                    'values': dict(st['values'])}
    return None


def topic_stats(counts, first_last_times, now):
    """Per topic: count, rate_hz ((n-1)/(last-first), needs >= 2) and age_s since last."""
    out = {}
    for topic, count in counts.items():
        first, last = first_last_times.get(topic, (None, None))
        rate = None
        if count >= 2 and last is not None and last > first:
            rate = (count - 1) / (last - first)
        out[topic] = {'count': count, 'rate_hz': rate,
                      'age_s': None if last is None else now - last}
    return out


def build_summary(scan, pose, imu, map_meta, data, diag, counts, times, now, t_unix=None):
    """Assemble the full summary dict from the captured plain-dict messages."""
    endpoints = scan_endpoints(scan, pose) if scan and pose else []
    return {
        'time_utc': None if t_unix is None else snapshot_dirname(t_unix)[len('lidar_snapshot_'):],
        'scan': scan_stats(scan) if scan else None,
        'pose': None if not pose else {
            'x': pose['x'], 'y': pose['y'], 'yaw_deg': math.degrees(pose['yaw'])},
        'map': map_stats(map_meta, data) if map_meta else None,
        'agreement': scan_map_agreement(endpoints, map_meta, data),
        'imu': imu_summary(imu),
        'diagnostics': diag_summary(diag),
        'topics': topic_stats(counts, times, now),
    }


def _n(v, fmt='.3f'):
    return 'n/a' if v is None else format(v, fmt)


def format_summary(s):
    """Human-readable text for a build_summary dict, with the image legend."""
    lines = ['lidar snapshot ' + (s.get('time_utc') or 'n/a')]
    sc = s.get('scan')
    if sc is None:
        lines.append('scan: n/a')
    else:
        lines.append(
            f"scan: {sc['beams']} beams, valid {_n(sc['finite_fraction'], '.2f')}, "
            f"range min/median/max {_n(sc['min_range'], '.2f')}/"
            f"{_n(sc['median_range'], '.2f')}/{_n(sc['max_range'], '.2f')} m, "
            f"span {_n(sc['angle_span_deg'], '.1f')} deg")
    p = s.get('pose')
    if p is None:
        lines.append('pose: n/a')
    else:
        lines.append(f"pose: x {p['x']:.3f} y {p['y']:.3f} yaw {p['yaw_deg']:.1f} deg")
    m = s.get('map')
    if m is None:
        lines.append('map: n/a')
    else:
        lines.append(
            f"map: {m['width']}x{m['height']} cells @ {m['resolution']:.3f} m, origin "
            f"({m['origin'][0]:.2f}, {m['origin'][1]:.2f}), unknown {m['unknown']} "
            f"free {m['free']} occupied {m['occupied']}, known {m['known_area_m2']:.1f} m2")
    lines.append(f"scan/map agreement: {_n(s.get('agreement'), '.2f')}")
    imu = s.get('imu')
    if imu is None:
        lines.append('imu: n/a')
    else:
        prov = ', '.join(k for k, v in imu['provided'].items() if v) or 'none'
        lines.append(f"imu: yaw {imu['yaw_deg']:.1f} deg, provided: {prov}")
    d = s.get('diagnostics')
    if d is None:
        lines.append('diagnostics mapper_driver: n/a')
    else:
        kv = ', '.join(f'{k}={v}' for k, v in d['values'].items())
        lines.append(f"diagnostics {d['name']}: {d['level']} {d['message']}"
                     + (f' [{kv}]' if kv else ''))
    for topic, t in s.get('topics', {}).items():
        lines.append(f"topic {topic}: {t['count']} msgs, rate {_n(t['rate_hz'], '.1f')} Hz, "
                     f"age {_n(t['age_s'], '.1f')} s")
    lines.append(LEGEND)
    lines.append(AGREEMENT_HINT)
    return '\n'.join(lines) + '\n'
