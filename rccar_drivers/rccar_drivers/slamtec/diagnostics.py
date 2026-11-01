"""Pure link-health decision for the Mapper diagnostics status (no rclpy)."""

OK, WARN, ERROR = 0, 1, 2


def link_level(link_up, health=None):
    """
    Return (level, message) from link state and a protocol.Health (or None).

    Link down -> ERROR. has_fatal/has_error -> ERROR. has_warning or a
    disconnected lidar -> WARN. Otherwise OK.
    """
    if not link_up:
        return ERROR, 'disconnected, retrying'
    if health is None:
        return OK, 'connected'
    if health.has_fatal or health.has_error:
        return ERROR, 'device reports %s' % ('fatal' if health.has_fatal else 'error')
    if health.has_lidar_disconnected:
        return WARN, 'lidar disconnected'
    if health.has_warning:
        return WARN, 'device reports warning'
    return OK, 'ok'
