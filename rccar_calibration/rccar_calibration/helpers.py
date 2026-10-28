"""Pure helpers for the calibration CLIs (no rclpy)."""
from dataclasses import dataclass

RAW_MIN_US, RAW_MAX_US = 500, 2500

CAL_TO_TOML = {'center': 'center_us', 'left': 'left_us', 'right': 'right_us',
               'maxdeg': 'max_steer_deg', 'gain': 'heading_gain'}
CAL_POINT_IDS = {'left': 0, 'center': 1, 'right': 2}     # CalPoint.LEFT/CENTER/RIGHT

HELP = """commands:
  +N / -N        nudge pulse by N us (e.g. +10, -2)
  =N             jump to N us
  center|left|right   store current pulse as that end point
  maxdeg D       road-wheel angle (deg) at full lock, measured
  gain G         heading -> steering gain
  show           print firmware config
  save           write values to tuning.toml AND the ESP32 flash
  q              quit (unsaved values are discarded on next connect)"""


def clamp_us(us) -> int:
    return int(max(RAW_MIN_US, min(RAW_MAX_US, us)))


@dataclass(frozen=True)
class Action:
    kind: str            # move store set show save quit help
    us: int = 1500
    name: str = ''
    value: float = 0.0


def parse_command(text: str, us: int) -> Action:
    """Parse one calibrate prompt line against the current pulse ``us``."""
    cmd = text.strip().lower()
    if not cmd:
        return Action('help', us)
    try:
        if cmd[0] in '+-' and cmd[1:].isdigit():
            return Action('move', clamp_us(us + int(cmd)), '', 0.0)
        if cmd[0] == '=' and cmd[1:].isdigit():
            return Action('move', clamp_us(int(cmd[1:])))
        if cmd in ('center', 'left', 'right'):
            return Action('store', us, cmd)
        if cmd in ('show', 'save'):
            return Action(cmd, us)
        if cmd in ('q', 'quit', 'exit'):
            return Action('quit', us)
        parts = cmd.split()
        if len(parts) == 2 and parts[0] in ('maxdeg', 'gain'):
            return Action('set', us, parts[0], float(parts[1]))
    except ValueError:
        pass
    return Action('help', us)


def missing_points(stored) -> list:
    """Calibration end points not yet stored, in guided order."""
    return [p for p in ('center', 'left', 'right') if p not in stored]


def sweep_plan(center_us: int, left_us: int, right_us: int) -> list:
    """Steering sweep as (label, raw pulse) steps, like the legacy bench test."""
    return [('center', center_us), ('left lock', left_us), ('center', center_us),
            ('right lock', right_us), ('center', center_us)]


def sweep_from_tuning(tuning: dict) -> list:
    cal = tuning['steering']['calibration']
    return sweep_plan(clamp_us(cal['center_us']), clamp_us(cal['left_us']),
                      clamp_us(cal['right_us']))


def timeout_margin_ok(timeout_ms: float, send_hz: float, factor: float = 3.0) -> bool:
    """tuning.toml rule: firmware timeout >= factor x command period."""
    return timeout_ms >= factor * 1000.0 / send_hz
