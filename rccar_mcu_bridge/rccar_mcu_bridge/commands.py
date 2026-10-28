"""Typed-service arguments -> firmware ASCII command strings (pure)."""
import math
import re

CAL_NAMES = {0: 'LEFT', 1: 'CENTER', 2: 'RIGHT'}
RAW_MIN_US, RAW_MAX_US = 500, 2500
MAX_COMMAND_LEN = 64            # McuCommand.command is string<=64
_KEY = re.compile(r'^[A-Za-z0-9_]{1,24}$')


def _check_len(cmd: str) -> str:
    if len(cmd) > MAX_COMMAND_LEN:
        raise ValueError(f'command too long: {cmd!r}')
    return cmd


def set_param_cmd(key: str, value: float) -> str:
    if not _KEY.match(key):
        raise ValueError(f'bad key {key!r}')
    if not math.isfinite(value):
        raise ValueError('value must be finite')
    return _check_len(f'SET {key} {value:.6g}')


def cal_point_cmd(point: int, us: int) -> str:
    if point not in CAL_NAMES:
        raise ValueError(f'bad calibration point {point}')
    return _check_len(f'CAL {CAL_NAMES[point]} {int(us)}')


def raw_pwm_cmd(us: int) -> str:
    if us == -1:
        return 'RAW OFF'
    if not RAW_MIN_US <= us <= RAW_MAX_US:
        raise ValueError(f'raw pulse {us} us outside {RAW_MIN_US}..{RAW_MAX_US}')
    return f'RAW {int(us)}'
