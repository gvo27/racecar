"""Push tuning.toml to the MCU and persist it (``ros2 run rccar_calibration tune``)."""
import argparse
import sys

from rccar_calibration.bridge_client import BridgeClient, BridgeError, DEFAULT_BRIDGE
import rclpy


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bridge', default=DEFAULT_BRIDGE)
    ns, ros_args = ap.parse_known_args(args)
    rclpy.init(args=ros_args)
    bridge = BridgeClient(ns.bridge)
    try:
        ok, msg = bridge.trigger('push_tuning', 30.0)
        print(msg)
        if not ok:
            return 1
        print(bridge.trigger('get')[1])
        ok, msg = bridge.trigger('save', 5.0)
        print(msg)
        return 0 if ok else 1
    except BridgeError as exc:
        print(f'error: {exc}')
        return 1
    finally:
        bridge.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
