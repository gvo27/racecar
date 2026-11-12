"""Regression: MapperDriver must not shadow rclpy.Node internals."""
import pytest

rclpy = pytest.importorskip('rclpy')


def test_lifecycle_services_survive_construction():
    from rccar_drivers.mapper_node import MapperDriver
    rclpy.init()
    try:
        node = MapperDriver(namespace='regtest')
        names = [s.srv_name for s in node.services]
        assert any(n.endswith('/change_state') for n in names), names
        assert any(n.endswith('/get_state') for n in names), names
        node.destroy_node()
    finally:
        rclpy.shutdown()
