"""
Map tuning.toml to ROS parameter dicts (pure, no rclpy).

Only keys present in the file are emitted; nodes keep their code defaults for
everything else. tuning.toml stays the single source of truth.
"""

# node -> {(table, key): parameter name}
PARAM_MAP = {
    'supervisor': {
        ('link', 'send_hz'): 'send_hz',
        ('supervisor', 'admin_priority'): 'admin_priority',
        ('supervisor', 'admin_timeout_s'): 'admin_timeout_s',
        ('supervisor', 'captain_priority'): 'captain_priority',
        ('supervisor', 'captain_timeout_s'): 'captain_timeout_s',
        ('supervisor', 'neutral_threshold'): 'neutral_threshold',
    },
    'mcu_bridge': {
        ('mcu_bridge', 'save_after_push'): 'save_after_push',
    },
}

FLOAT_PARAMS = {'send_hz', 'admin_timeout_s', 'captain_timeout_s', 'neutral_threshold'}


def node_params(tuning: dict) -> dict:
    """Return {node_name: {param: value}} from a parsed tuning.toml."""
    out = {}
    for node, mapping in PARAM_MAP.items():
        params = {}
        for (table, key), name in mapping.items():
            section = tuning.get(table)
            if isinstance(section, dict) and key in section:
                val = section[key]
                params[name] = float(val) if name in FLOAT_PARAMS else val
        out[node] = params
    return out
