"""Pure parameter coercion + validation for the mapper node (no rclpy)."""

POSITIVE = ('timeout_s', 'scan_rate_hz', 'imu_rate_hz', 'pose_rate_hz', 'map_period_s',
            'health_period_s', 'reconnect_max_s', 'map_max_cells', 'port')
MIN_BINS = 90


def check_params(raw, defaults):
    """
    Return (cfg, errors): values cast to the default's type, plus problems.

    Launch files may pass ints for double parameters (range_max:=40), so
    numbers are cast by the default's type. errors is a list of strings; the
    node fails the configure transition if it is not empty.
    """
    cfg, errors = {}, []
    for key, default in defaults.items():
        value = raw.get(key, default)
        try:
            if isinstance(default, bool):
                if not isinstance(value, bool):
                    raise TypeError('expected bool')
            elif isinstance(default, int):
                if isinstance(value, bool) or int(value) != value:
                    raise TypeError('expected integer')
                value = int(value)
            elif isinstance(default, float):
                if isinstance(value, bool):
                    raise TypeError('expected number')
                value = float(value)
            elif not isinstance(value, str):
                raise TypeError('expected string')
        except (TypeError, ValueError) as exc:
            errors.append('%s=%r: %s' % (key, value, exc))
            value = default
        cfg[key] = value
    if errors:
        return cfg, errors
    for key in POSITIVE:
        if not cfg[key] > 0:
            errors.append('%s must be > 0 (got %r)' % (key, cfg[key]))
    if cfg['n_bins'] < MIN_BINS:
        errors.append('n_bins must be >= %d (got %r)' % (MIN_BINS, cfg['n_bins']))
    if not 0.0 <= cfg['range_min'] < cfg['range_max']:
        errors.append('need 0 <= range_min < range_max (got %r, %r)'
                      % (cfg['range_min'], cfg['range_max']))
    return cfg, errors
