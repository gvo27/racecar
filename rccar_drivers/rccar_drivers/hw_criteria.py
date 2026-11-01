"""
Pass/fail criteria for the physical lidar acceptance test (no rclpy).

Used by rccar_drivers/test_hw/test_mapper_hw.py (make lidar-hw-test). Thresholds are
module constants so they are versioned in git. Changing one needs a stated reason and
user approval (.claude/rules/hw-testing.md). Every eval_* takes collected samples and
returns (passed: bool, detail: str).
"""
import math

# --- thresholds -------------------------------------------------------------------------
CONNECT_TIMEOUT_S = 60.0       # Mapper boots in ~40 s
WINDOW_S = 10.0                # measurement window (car stationary)
MAP_TIMEOUT_S = 30.0
SCAN_MIN_HZ = 8.0
SCAN_MIN_FINITE_FRACTION = 0.30   # indoor room
MAX_SCAN_GAP_S = 1.0
IMU_MIN_RATE_FRACTION = 0.8       # of the imu_rate_hz parameter
ACC_MS2_RANGE = (9.0, 10.6)
ACC_G_RANGE = (0.9, 1.1)
GYRO_Z_REST_MAX = 0.05            # rad/s, mean |z|
QUAT_NORM_TOL = 0.02
POSE_MIN_HZ = 5.0
POSE_MAX_DRIFT_M = 0.05
POSE_MAX_DRIFT_DEG = 2.0
MAP_RESOLUTION = 0.05
MAP_RESOLUTION_TOL = 0.01
MAP_MIN_KNOWN_FRACTION = 0.01


def _level_int(level):
    """DiagnosticStatus.level is a single byte in rclpy jazzy, an int elsewhere."""
    return level[0] if isinstance(level, (bytes, bytearray)) else int(level)


def eval_single_publisher(count):
    """Exactly one publisher on /rccar/lidar/scan (the test's own driver)."""
    if count == 1:
        return True, '1 publisher'
    if count > 1:
        return False, ('%d publishers on /rccar/lidar/scan: the compose `drivers` service '
                       'is still running; run `make drivers-stop`' % count)
    return False, 'no publisher on /rccar/lidar/scan (driver did not configure/activate)'


def eval_link(events, timeout_s=CONNECT_TIMEOUT_S):
    """Events are (seconds since start, level) of 'mapper_driver: link'; OK within timeout."""
    names = {0: 'OK', 1: 'WARN', 2: 'ERROR', 3: 'STALE'}
    for t, level in events:
        if _level_int(level) == 0 and t <= timeout_s:
            return True, 'link OK after %.1f s (limit %.0f s)' % (t, timeout_s)
    if not events:
        return False, 'no link diagnostics within %.0f s' % timeout_s
    seen = sorted({names.get(_level_int(lv), '?') for _, lv in events})
    return False, 'link never OK within %.0f s (levels seen: %s)' % (timeout_s, ','.join(seen))


def eval_rate(times, window_s, min_hz):
    """Message rate over the window from receive times."""
    hz = len(times) / window_s if window_s > 0 else 0.0
    return hz >= min_hz, '%.2f Hz over %.1f s (min %.2f)' % (hz, window_s, min_hz)


def eval_gap(times, max_gap_s=MAX_SCAN_GAP_S):
    """Largest gap between consecutive receive times."""
    if len(times) < 2:
        return False, 'fewer than 2 messages'
    gap = max(b - a for a, b in zip(times, times[1:]))
    return gap <= max_gap_s, 'max gap %.2f s (limit %.2f)' % (gap, max_gap_s)


def eval_scan_length(lengths, n_bins):
    """Every scan has n_bins ranges."""
    bad = sorted({n for n in lengths if n != n_bins})
    if not lengths:
        return False, 'no scans'
    return not bad, ('all %d scans have %d ranges' % (len(lengths), n_bins) if not bad
                     else 'lengths %s != n_bins %d' % (bad, n_bins))


def eval_finite_fraction(scans, min_fraction=SCAN_MIN_FINITE_FRACTION):
    """Mean fraction of finite ranges over all scans."""
    fracs = [sum(1 for r in s if math.isfinite(r)) / len(s) for s in scans if len(s)]
    if not fracs:
        return False, 'no scans'
    mean = sum(fracs) / len(fracs)
    return mean >= min_fraction, 'mean finite fraction %.2f (min %.2f)' % (mean, min_fraction)


def eval_range_bounds(scans, range_min, range_max):
    """Every finite range within [range_min, range_max]; NaN is a failure, inf is no-return."""
    nan = out = 0
    for s in scans:
        for r in s:
            if math.isnan(r):
                nan += 1
            elif math.isfinite(r) and not range_min <= r <= range_max:
                out += 1
    if not scans:
        return False, 'no scans'
    return nan == 0 and out == 0, '%d NaN, %d outside [%.2f, %.2f]' % (
        nan, out, range_min, range_max)


def eval_frame(frames, expected):
    """Every header.frame_id equals expected."""
    bad = sorted({f for f in frames if f != expected})
    if not frames:
        return False, 'no messages'
    return not bad, 'frame_id %s' % (expected if not bad else 'unexpected %s' % bad)


def eval_stamps_monotonic(stamps):
    """Header stamps never decrease."""
    if len(stamps) < 2:
        return False, 'fewer than 2 messages'
    back = sum(1 for a, b in zip(stamps, stamps[1:]) if b < a)
    return back == 0, '%d backwards steps in %d stamps' % (back, len(stamps))


def classify_acc_units(mean_norm):
    """'m/s^2', 'g' or 'unknown' from the mean |acc| at rest."""
    if ACC_MS2_RANGE[0] <= mean_norm <= ACC_MS2_RANGE[1]:
        return 'm/s^2'
    if ACC_G_RANGE[0] <= mean_norm <= ACC_G_RANGE[1]:
        return 'g'
    return 'unknown'


def eval_acc_units(accs):
    """Classify IMU acceleration units at rest; unknown fails."""
    if not accs:
        return False, 'no imu samples'
    mean = sum(math.sqrt(x * x + y * y + z * z) for x, y, z in accs) / len(accs)
    units = classify_acc_units(mean)
    if units == 'unknown':
        return False, 'mean |acc| %.3f at rest: units unknown (expect %s m/s^2 or %s g)' % (
            mean, ACC_MS2_RANGE, ACC_G_RANGE)
    return True, 'mean |acc| %.3f -> %s' % (mean, units)


def eval_gyro_rest(gyro_z, max_abs=GYRO_Z_REST_MAX):
    """Mean |gyro z| at rest below max_abs rad/s."""
    if not gyro_z:
        return False, 'no imu samples'
    mean = sum(abs(z) for z in gyro_z) / len(gyro_z)
    return mean < max_abs, 'mean |gyro z| %.4f rad/s (max %.3f)' % (mean, max_abs)


def eval_quat_norm(quats, tol=QUAT_NORM_TOL):
    """Quaternion (x, y, z, w) norms within tol of 1."""
    if not quats:
        return False, 'no imu samples'
    worst = max(abs(math.sqrt(sum(c * c for c in q)) - 1.0) for q in quats)
    return worst <= tol, 'worst |norm-1| %.4f (tol %.2f)' % (worst, tol)


def eval_pose_finite(poses):
    """Every pose (x, y, yaw) is finite."""
    if not poses:
        return False, 'no poses'
    bad = sum(1 for p in poses if not all(math.isfinite(v) for v in p))
    return bad == 0, '%d non-finite of %d poses' % (bad, len(poses))


def eval_pose_drift(poses, max_m=POSE_MAX_DRIFT_M, max_deg=POSE_MAX_DRIFT_DEG):
    """Stationary drift of the SLAM pose relative to the first sample (yaw wrapped)."""
    if not poses:
        return False, 'no poses'
    x0, y0, a0 = poses[0]
    dist = max(math.hypot(x - x0, y - y0) for x, y, _ in poses)
    ang = max(abs(math.degrees(math.atan2(math.sin(a - a0), math.cos(a - a0))))
              for _, _, a in poses)
    ok = dist < max_m and ang < max_deg
    return ok, 'drift %.3f m (max %.2f), %.2f deg (max %.1f)' % (dist, max_m, ang, max_deg)


def eval_map_received(grid, timeout_s=MAP_TIMEOUT_S):
    """Map arrived in time and non-empty; grid = dict(t, width, height, ...) or None."""
    if grid is None:
        return False, 'no OccupancyGrid within %.0f s' % timeout_s
    ok = grid['t'] <= timeout_s and grid['width'] > 0 and grid['height'] > 0
    return ok, 'map %dx%d after %.1f s (limit %.0f s)' % (
        grid['width'], grid['height'], grid['t'], timeout_s)


def eval_map_resolution(grid):
    """Map resolution about MAP_RESOLUTION."""
    if grid is None:
        return False, 'no map'
    res = grid['resolution']
    return abs(res - MAP_RESOLUTION) <= MAP_RESOLUTION_TOL + 1e-9, (
        'resolution %.3f m (expect %.2f +- %.2f)' % (res, MAP_RESOLUTION, MAP_RESOLUTION_TOL))


def eval_map_known(grid, min_fraction=MAP_MIN_KNOWN_FRACTION):
    """Fraction of cells that are not -1 (unknown)."""
    if grid is None or not grid['data']:
        return False, 'no map'
    frac = sum(1 for v in grid['data'] if v != -1) / len(grid['data'])
    return frac >= min_fraction, 'known cells %.1f %% (min %.1f %%)' % (
        100 * frac, 100 * min_fraction)


def eval_tf(resolved):
    """map->base_link resolvable."""
    return bool(resolved), 'map->base_link %s' % ('resolvable' if resolved else 'NOT resolvable')
