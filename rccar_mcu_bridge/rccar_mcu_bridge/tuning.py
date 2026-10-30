"""
tuning.toml -> firmware ASCII commands (pure, no rclpy).

FIRMWARE_KEYS is the single source of truth for (table, key) -> firmware command.
Invariant: tuning key change => tuning.toml + FIRMWARE_KEYS + firmware setKey
(test_tuning.py checks both the tuning.toml keys and the main.cpp setKey names).
"""
import os
from pathlib import Path
import re

import tomllib

DEFAULT_TUNING = '/ws/src/racecar/tuning.toml'

# tuning.toml (table, key) -> firmware command prefix. Order matters for ESC
# endpoints: the firmware rejects any SET that breaks esc_min < neutral < max.
FIRMWARE_KEYS = [
    (('steering.calibration', 'center_us'), 'CAL CENTER'),
    (('steering.calibration', 'left_us'), 'CAL LEFT'),
    (('steering.calibration', 'right_us'), 'CAL RIGHT'),
    (('steering.calibration', 'max_steer_deg'), 'SET maxdeg'),
    (('steering', 'heading_gain'), 'SET gain'),
    (('steering', 'servo_hz'), 'SET servo_hz'),
    (('throttle.calibration', 'esc_min_us'), 'SET esc_min'),
    (('throttle.calibration', 'esc_max_us'), 'SET esc_max'),
    (('throttle.calibration', 'esc_neutral_us'), 'SET esc_neutral'),
    (('throttle.calibration', 'deadband_us'), 'SET deadband'),
    (('throttle', 'esc_hz'), 'SET esc_hz'),
    (('throttle', 'speed_limit'), 'SET limit'),
    (('throttle', 'accel_per_s'), 'SET accel'),
    (('throttle', 'reverse_double_tap'), 'SET revmode'),
    (('throttle', 'brake_ms'), 'SET brake_ms'),
    (('throttle', 'gap_ms'), 'SET gap_ms'),
    (('throttle', 'brake_level'), 'SET brake_level'),
    (('safety', 'cmd_timeout_ms'), 'SET timeout'),
    (('control', 'control_hz'), 'SET control_hz'),
    (('rangefinder', 'driver'), 'SET rf_driver'),
    (('rangefinder', 'i2c_addr'), 'SET rf_addr'),
    (('rangefinder', 'period_ms'), 'SET rf_period_ms'),
    (('rangefinder', 'reading_scale_m'), 'SET rf_scale_m'),
    (('rangefinder', 'no_return_raw'), 'SET rf_no_return'),
    # firmware clamps min < max: push max first so a wider range never rejects
    (('rangefinder', 'max_range_m'), 'SET rf_max_m'),
    (('rangefinder', 'min_range_m'), 'SET rf_min_m'),
    (('rangefinder', 'fov_rad'), 'SET rf_fov_rad'),
    (('rangefinder', 'radiation_type'), 'SET rf_radiation'),
]


def resolve_tuning_path(param: str = '') -> Path:
    """Node parameter, else $RCCAR_TUNING, else the in-container default."""
    return Path(param or os.environ.get('RCCAR_TUNING') or DEFAULT_TUNING)


def load_tuning(path) -> dict:
    with open(path, 'rb') as f:
        return tomllib.load(f)


def tuning_value(tuning: dict, table: str, key: str):
    """Look up ``table`` (dotted) / ``key``; raises KeyError if absent."""
    node = tuning
    for part in table.split('.'):
        node = node[part]
    return node[key]


def firmware_commands(tuning: dict) -> list:
    """Commands in FIRMWARE_KEYS order, skipping keys missing from ``tuning``."""
    cmds = []
    for (table, key), prefix in FIRMWARE_KEYS:
        try:
            val = tuning_value(tuning, table, key)
        except (KeyError, TypeError):
            continue
        val = int(val) if isinstance(val, bool) else val
        cmds.append(f'{prefix} {val}')
    return cmds


def update_tuning_file(values: dict, path) -> None:
    """
    Rewrite ``key = value`` lines in place, keeping comments and layout.

    Keys in tuning.toml are unique across sections, so a per-key regex is safe.
    """
    path = Path(path)
    text = path.read_text()
    for key, val in values.items():
        text, n = re.subn(rf'(?m)^(\s*{key}\s*=\s*)[^#\n]*?(\s*(#.*)?)$',
                          rf'\g<1>{val}\g<2>', text, count=1)
        if n != 1:
            raise KeyError(f'{key} not found in {path.name}')
    path.write_text(text)


def parse_kv(line: str) -> dict:
    """'TEL t=1 hdg=2.0 ...' -> {'t': 1.0, 'hdg': 2.0, ...}."""
    out = {}
    for tok in line.split()[1:]:
        if '=' in tok:
            k, v = tok.split('=', 1)
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out
