"""Regression: McuBridge must not shadow rclpy.Node internals (lifecycle services were lost)."""
import pytest

rclpy = pytest.importorskip('rclpy')


def test_lifecycle_services_survive_construction_and_activation():
    from rccar_mcu_bridge.bridge_node import McuBridge
    rclpy.init()
    try:
        node = McuBridge()
        names = [s.srv_name for s in node.services]
        assert any(n.endswith('/change_state') for n in names), names
        assert any(n.endswith('/get_state') for n in names), names
        node.destroy_node()
    finally:
        rclpy.shutdown()
