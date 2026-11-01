"""Pure link-health decision for the Mapper diagnostics status (no rclpy)."""

OK, WARN, ERROR = 0, 1, 2
SCAN_FRESH_S = 2.0  # a scan older than this is stale (also the heartbeat limit)


def link_level(link_up, health=None, last_scan_age=None):
    """
    Return (level, message) from link state, a protocol.Health (or None) and scan age.

    Link down -> ERROR. has_fatal/has_error -> ERROR. Link up but the last
    scan older than 3 x SCAN_FRESH_S -> ERROR, older than SCAN_FRESH_S -> WARN
    ('no scans'; None = no scan yet, still starting). has_warning or a
    disconnected lidar -> WARN. Otherwise OK.
    """
    if not link_up:
        return ERROR, 'disconnected, retrying'
    if health is not None and (health.has_fatal or health.has_error):
        return ERROR, 'device reports %s' % ('fatal' if health.has_fatal else 'error')
    if last_scan_age is not None:
        if last_scan_age > 3.0 * SCAN_FRESH_S:
            return ERROR, 'no scans'
        if last_scan_age > SCAN_FRESH_S:
            return WARN, 'no scans'
    if health is None:
        return OK, 'connected'
    if health.has_lidar_disconnected:
        return WARN, 'lidar disconnected'
    if health.has_warning:
        return WARN, 'device reports warning'
    return OK, 'ok'
