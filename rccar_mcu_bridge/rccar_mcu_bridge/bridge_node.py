"""
Lifecycle node: typed wrappers + tuning push over ``/rccar/mcu/command``.

Never sends ARM (the supervisor owns arming). On activation (as soon as the
MCU service is reachable: its READY event may predate this node) and on every
MCU READY it pushes every FIRMWARE_KEYS command from tuning.toml,
sequentially, stopping at the first error; SAVE only when ``save_after_push``
is set.

One ReentrantCallbackGroup + SingleThreadedExecutor: coroutine callbacks await
the MCU without blocking the executor.
"""
from rccar_mcu_bridge.commands import cal_point_cmd, raw_pwm_cmd, set_param_cmd
from rccar_mcu_bridge.heartbeat import touch
from rccar_mcu_bridge.mcu_call import call_service
from rccar_mcu_bridge.tuning import firmware_commands, load_tuning, resolve_tuning_path
from rccar_msgs.msg import McuEvent
from rccar_msgs.srv import CalPoint, McuCommand, RawPwm, SetParam
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.lifecycle import Node, TransitionCallbackReturn
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_srvs.srv import Trigger

MCU_COMMAND = '/rccar/mcu/command'
MCU_EVENT = '/rccar/mcu/event'
EVENT_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


class McuBridge(Node):
    """Owner of the MCU command channel for calibration and tuning."""

    def __init__(self):
        super().__init__('mcu_bridge')
        self.declare_parameter('tuning_file', '')
        self.declare_parameter('save_after_push', False)
        self.declare_parameter('command_timeout_s', 2.0)
        self.declare_parameter('heartbeat_file', '')
        self._group = ReentrantCallbackGroup()
        self._tuning = {}
        self._tuning_path = None
        self._client = None
        self._srvs, self._sub, self._hb = [], None, None
        self._pushing = False
        self._startup_timer = None
        self._startup_pending = False

    # -- lifecycle ----------------------------------------------------------
    def on_configure(self, state):
        self._tuning_path = resolve_tuning_path(self.get_parameter('tuning_file').value)
        try:
            self._tuning = load_tuning(self._tuning_path)
        except (OSError, ValueError) as exc:
            self.get_logger().error(f'cannot load tuning {self._tuning_path}: {exc}')
            return TransitionCallbackReturn.FAILURE
        n = len(firmware_commands(self._tuning))
        self.get_logger().info(f'tuning {self._tuning_path}: {n} firmware commands')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state):
        g = self._group
        self._client = self.create_client(McuCommand, MCU_COMMAND, callback_group=g)
        sub = self.create_subscription(McuEvent, MCU_EVENT, self._on_event, EVENT_QOS,
                                       callback_group=g)
        srvs = [
            self.create_service(SetParam, '~/set_param', self._set_param, callback_group=g),
            self.create_service(CalPoint, '~/cal_point', self._cal_point, callback_group=g),
            self.create_service(RawPwm, '~/raw_pwm', self._raw_pwm, callback_group=g),
            self.create_service(Trigger, '~/save', self._trigger('SAVE'), callback_group=g),
            self.create_service(Trigger, '~/get', self._trigger('GET'), callback_group=g),
            self.create_service(Trigger, '~/info', self._trigger('INFO'), callback_group=g),
            self.create_service(Trigger, '~/push_tuning', self._push_tuning,
                                callback_group=g),
        ]
        hb = self.create_timer(0.5, self._beat, callback_group=g)
        self._sub, self._hb, self._srvs = sub, hb, srvs
        self._startup_pending = True
        self._startup_timer = self.create_timer(0.5, self._startup_push, callback_group=g)
        return super().on_activate(state)

    def on_deactivate(self, state):
        self._destroy_entities()
        return super().on_deactivate(state)

    def on_cleanup(self, state):
        self._destroy_entities()
        self._tuning = {}
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state):
        self._destroy_entities()
        return TransitionCallbackReturn.SUCCESS

    def _destroy_entities(self):
        if self._client is None:
            return
        for srv in self._srvs:
            self.destroy_service(srv)
        self.destroy_subscription(self._sub)
        self.destroy_timer(self._hb)
        if self._startup_timer is not None:
            self.destroy_timer(self._startup_timer)
        self._startup_timer, self._startup_pending = None, False
        self.destroy_client(self._client)
        self._srvs, self._sub, self._hb, self._client = [], None, None, None

    def _beat(self):
        touch(self.get_parameter('heartbeat_file').value)

    # -- MCU access -----------------------------------------------------------
    async def _mcu(self, text):
        """Send one ASCII command. Returns (ok, reply)."""
        req = McuCommand.Request()
        req.command = text
        timeout = float(self.get_parameter('command_timeout_s').value)
        resp = await call_service(self, self._client, req, timeout, self._group)
        if resp is None:
            return False, 'no reply from /rccar/mcu/command (agent down or timeout)'
        return bool(resp.ok), resp.reply

    async def _typed(self, build, response):
        try:
            cmd = build()
        except ValueError as exc:
            response.ok, response.message = False, str(exc)
            return response
        response.ok, response.message = await self._mcu(cmd)
        return response

    async def _set_param(self, request, response):
        return await self._typed(lambda: set_param_cmd(request.key, request.value), response)

    async def _cal_point(self, request, response):
        return await self._typed(lambda: cal_point_cmd(request.point, request.us), response)

    async def _raw_pwm(self, request, response):
        return await self._typed(lambda: raw_pwm_cmd(request.us), response)

    def _trigger(self, command):
        async def handler(request, response):
            response.success, response.message = await self._mcu(command)
            return response
        return handler

    # -- tuning push ------------------------------------------------------------
    async def _push(self):
        """Push all firmware commands sequentially. Returns (ok, message)."""
        if self._pushing:
            return False, 'push already in progress'
        self._pushing = True
        try:
            try:        # re-read so a fresh `calibrate` write is picked up
                self._tuning = load_tuning(self._tuning_path)
            except (OSError, ValueError) as exc:
                return False, f'cannot load tuning {self._tuning_path}: {exc}'
            cmds = firmware_commands(self._tuning)
            for cmd in cmds:
                ok, reply = await self._mcu(cmd)
                if not ok:
                    msg = f'push stopped at "{cmd}": {reply}'
                    self.get_logger().error(msg)
                    return False, msg
            msg = f'pushed {len(cmds)} commands'
            if self.get_parameter('save_after_push').value:
                ok, reply = await self._mcu('SAVE')
                if not ok:
                    return False, f'{msg}, SAVE failed: {reply}'
                msg += ', saved to flash'
            self.get_logger().info(msg)
            return True, msg
        finally:
            self._pushing = False

    async def _push_tuning(self, request, response):
        response.success, response.message = await self._push()
        return response

    async def _startup_push(self):
        """One push after activation, once the MCU service is reachable."""
        if not self._startup_pending or self._client is None \
                or not self._client.service_is_ready():
            return
        self._startup_pending = False
        self._startup_timer.cancel()
        self.get_logger().info('MCU reachable after activation: pushing tuning')
        await self._push()

    async def _on_event(self, msg):
        if msg.code == McuEvent.READY:
            self.get_logger().info('MCU READY: pushing tuning')
            await self._push()


def main(args=None):
    rclpy.init(args=args)
    node = McuBridge()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
