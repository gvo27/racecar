"""
Interactive steering calibration (``ros2 run rccar_calibration calibrate``).

Jogs the servo with RAW pulses via /mcu_bridge/raw_pwm, stores end points with
cal_point/set_param, and on ``save`` persists to the ESP32 flash and writes the
[steering.calibration] keys back into tuning.toml. The motor is never armed.
"""
import argparse
import sys

from rccar_calibration.bridge_client import BridgeClient, BridgeError, DEFAULT_BRIDGE
from rccar_calibration.helpers import (
    CAL_POINT_IDS, CAL_TO_TOML, HELP, missing_points, parse_command)
from rccar_mcu_bridge.tuning import resolve_tuning_path, update_tuning_file
import rclpy

GUIDE = """Steering calibration (motor stays disarmed).
 1. Mount the servo horn so the wheels are roughly straight at 1500 us.
 2. Jog (+N / -N) until the wheels point straight, type `center`.
 3. Jog to full left lock, stop BEFORE the linkage binds (buzzing = stall), `left`.
 4. Jog to full right lock the same way, `right`.
 5. Measure the road-wheel angle at lock and enter it with `maxdeg D`.
 6. `save` writes the ESP32 flash and tuning.toml."""


def run(bridge: BridgeClient, tuning_path) -> int:
    us = 1500
    changed = {}
    stored = set()
    print(GUIDE)
    print(HELP)
    ok, msg = bridge.raw_pwm(us)
    if not ok:
        print(f'cannot jog: {msg}')
        return 1
    try:
        while True:
            todo = missing_points(stored)
            hint = f' (todo: {", ".join(todo)})' if todo else ''
            try:
                text = input(f'[{us} us]{hint} > ')
            except EOFError:
                break
            act = parse_command(text, us)
            if act.kind == 'quit':
                break
            if act.kind == 'help':
                print(HELP)
            elif act.kind == 'move':
                ok, msg = bridge.raw_pwm(act.us)
                if ok:
                    us = act.us
                else:
                    print(f'  ? {msg}')
            elif act.kind == 'store':
                ok, msg = bridge.cal_point(CAL_POINT_IDS[act.name], us)
                print(f'  {msg}')
                if ok:
                    changed[CAL_TO_TOML[act.name]] = us
                    stored.add(act.name)
            elif act.kind == 'set':
                ok, msg = bridge.set_param(act.name, act.value)
                print(f'  {msg}')
                if ok:
                    changed[CAL_TO_TOML[act.name]] = act.value
            elif act.kind == 'show':
                print(bridge.trigger('get')[1])
            elif act.kind == 'save':
                ok, msg = bridge.trigger('save', 5.0)
                print(f'  {msg}')
                if ok and changed:
                    update_tuning_file(changed, tuning_path)
                    print(f'  {tuning_path} updated: {changed}')
                    changed = {}
    finally:
        try:
            bridge.raw_pwm(-1)           # RAW OFF: release the servo
        except BridgeError:
            pass
    if changed:
        print(f'unsaved values discarded: {changed}')
    return 0


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bridge', default=DEFAULT_BRIDGE, help='mcu_bridge node name')
    ap.add_argument('--tuning', default='', help='tuning.toml to update (default: $RCCAR_TUNING)')
    ns, ros_args = ap.parse_known_args(args)
    rclpy.init(args=ros_args)
    bridge = BridgeClient(ns.bridge)
    try:
        return run(bridge, resolve_tuning_path(ns.tuning))
    except (BridgeError, KeyboardInterrupt) as exc:
        print(f'\n{exc}' if str(exc) else '\naborted')
        return 1
    finally:
        bridge.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
