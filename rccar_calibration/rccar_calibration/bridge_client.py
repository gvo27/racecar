"""Synchronous client for the rccar_mcu_bridge services (CLI use only)."""
import os

from rccar_msgs.srv import CalPoint, RawPwm, SetParam
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger

DEFAULT_BRIDGE = '/mcu_bridge'


class BridgeError(RuntimeError):
    """Bridge service missing or call failed to complete."""


class BridgeClient(Node):
    """Calls /mcu_bridge/* and returns (ok, message) tuples."""

    def __init__(self, bridge: str = DEFAULT_BRIDGE, timeout_s: float = 5.0):
        super().__init__(f'rccar_cli_{os.getpid()}')
        self._timeout = timeout_s
        b = bridge.rstrip('/')
        self._set = self.create_client(SetParam, f'{b}/set_param')
        self._cal = self.create_client(CalPoint, f'{b}/cal_point')
        self._raw = self.create_client(RawPwm, f'{b}/raw_pwm')
        self._trig = {name: self.create_client(Trigger, f'{b}/{name}')
                      for name in ('save', 'get', 'info', 'push_tuning')}

    def _call(self, client, request, timeout_s=None):
        if not client.wait_for_service(timeout_sec=self._timeout):
            raise BridgeError(f'{client.srv_name} not available: is mcu_bridge '
                              'active? (ros2 lifecycle get /mcu_bridge)')
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_s or self._timeout)
        if not future.done():
            raise BridgeError(f'{client.srv_name} timed out')
        res = future.result()
        return (res.ok if hasattr(res, 'ok') else res.success), res.message

    def set_param(self, key: str, value: float):
        req = SetParam.Request()
        req.key, req.value = key, float(value)
        return self._call(self._set, req)

    def cal_point(self, point: int, us: int):
        req = CalPoint.Request()
        req.point, req.us = int(point), int(us)
        return self._call(self._cal, req)

    def raw_pwm(self, us: int):
        req = RawPwm.Request()
        req.us = int(us)
        return self._call(self._raw, req)

    def trigger(self, name: str, timeout_s=None):
        return self._call(self._trig[name], Trigger.Request(), timeout_s)
