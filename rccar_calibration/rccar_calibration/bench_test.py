"""Bench test: steering sweep + failsafe-config check. NEVER arms the motor."""
import argparse
import sys
import time

from rccar_calibration.bridge_client import BridgeClient, BridgeError, DEFAULT_BRIDGE
from rccar_calibration.helpers import sweep_from_tuning, timeout_margin_ok
from rccar_mcu_bridge.tuning import load_tuning, parse_kv, resolve_tuning_path
import rclpy


def run(bridge: BridgeClient, tuning: dict, dwell_s: float) -> int:
    print(bridge.trigger('info')[1])
    ok, cfg = bridge.trigger('get')
    print(cfg)
    if not ok:
        return 1

    print('\n[1/2] steering sweep via RAW pulses (motor disarmed)')
    try:
        for label, us in sweep_from_tuning(tuning):
            ok, msg = bridge.raw_pwm(us)
            print(f'  {label:<10} {us} us  {"ok" if ok else msg}')
            if not ok:
                return 1
            time.sleep(dwell_s)
    finally:
        bridge.raw_pwm(-1)

    print('\n[2/2] failsafe configuration (no ARM: the motor stays off)')
    timeout_ms = parse_kv(cfg).get('timeout', tuning['safety']['cmd_timeout_ms'])
    send_hz = tuning['link']['send_hz']
    good = timeout_margin_ok(float(timeout_ms), float(send_hz))
    print(f'  firmware timeout {timeout_ms} ms vs command period {1000 / send_hz:.0f} ms: '
          f'{"OK" if good else "TOO TIGHT (need >= 3 periods)"}')
    print('  live failsafe (kill mcu-agent / stop teleop while armed) is a manual bench check;'
          ' this tool never arms.')
    return 0 if good else 1


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bridge', default=DEFAULT_BRIDGE)
    ap.add_argument('--tuning', default='')
    ap.add_argument('--dwell', type=float, default=1.0, help='seconds per sweep step')
    ns, ros_args = ap.parse_known_args(args)
    rclpy.init(args=ros_args)
    bridge = BridgeClient(ns.bridge)
    try:
        tuning = load_tuning(resolve_tuning_path(ns.tuning))
        return run(bridge, tuning, ns.dwell)
    except (BridgeError, OSError, KeyError) as exc:
        print(f'error: {exc}')
        return 1
    finally:
        bridge.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
