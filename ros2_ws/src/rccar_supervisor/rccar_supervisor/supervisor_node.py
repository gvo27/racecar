"""
Supervisor node: thin rclpy adapter around :class:`Arbiter`.

Safety authority and the ONLY publisher of ``/rccar/mcu/drive``. Fail-safe by
silence: drive is streamed only while armed; when latched nothing is published
and the firmware command timeout keeps the car disarmed.

Threading: a SingleThreadedExecutor with one ReentrantCallbackGroup, so the
coroutine service callbacks can await the MCU without blocking and the arbiter
is never touched concurrently.
"""
from rccar_msgs.msg import DriveCmd, McuEvent, SupervisorState
from rccar_msgs.srv import McuCommand, Reset
from rccar_supervisor.arbiter import (
    ADMIN_TOPIC, Arbiter, CAPTAIN_TOPIC, NEUTRAL_THROTTLE)
from rccar_supervisor.heartbeat import touch
from rccar_supervisor.mcu_call import call_service
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_srvs.srv import Trigger

MCU_COMMAND = '/rccar/mcu/command'
MCU_DRIVE = '/rccar/mcu/drive'
MCU_EVENT = '/rccar/mcu/event'
STATE_TOPIC = '/rccar/supervisor/state'

# Commands are only valid while fresh (per-input timeout), so a late retransmit
# is worthless: best effort depth 1 on the subscriber. A best-effort subscription
# also matches reliable publishers, so teleop/captain QoS choices cannot silently
# break the link.
CMD_IN_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
# MCU drive: freshness over delivery (micro-ROS best effort subscriber).
DRIVE_OUT_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
# Late joiners (teleop, UIs) must see a latched stop.
STATE_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)
# Firmware publishes events reliably; do not miss FAILSAFE.
EVENT_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


class SupervisorNode(Node):
    """Arbitrates admin/captain commands and owns arm/disarm/brake."""

    def __init__(self):
        super().__init__('supervisor')
        self.declare_parameter('send_hz', 50.0)
        self.declare_parameter('admin_priority', 100)
        self.declare_parameter('admin_timeout_s', 0.3)
        self.declare_parameter('captain_priority', 10)
        self.declare_parameter('captain_timeout_s', 0.5)
        self.declare_parameter('neutral_threshold', NEUTRAL_THROTTLE)
        self.declare_parameter('mcu_command_timeout_s', 2.0)
        self.declare_parameter('heartbeat_file', '')

        def p(name):
            return self.get_parameter(name).value

        inputs = {
            ADMIN_TOPIC: (int(p('admin_priority')), float(p('admin_timeout_s'))),
            CAPTAIN_TOPIC: (int(p('captain_priority')), float(p('captain_timeout_s'))),
        }
        self._arb = Arbiter(inputs, float(p('neutral_threshold')))
        self._mcu_timeout = float(p('mcu_command_timeout_s'))
        self._hb_file = str(p('heartbeat_file'))
        send_hz = float(p('send_hz'))
        if send_hz <= 0.0:
            raise ValueError('send_hz must be > 0')

        self._group = ReentrantCallbackGroup()
        self._disarm_acked = -1       # incident for which MCU DISARM succeeded
        self._disarm_busy_until = 0.0
        self._last_state = None
        self._last_state_pub = 0.0

        for topic in inputs:
            self.create_subscription(
                DriveCmd, topic, lambda msg, t=topic: self._on_cmd(t, msg),
                CMD_IN_QOS, callback_group=self._group)
        self.create_subscription(McuEvent, MCU_EVENT, self._on_event, EVENT_QOS,
                                 callback_group=self._group)
        self._drive_pub = self.create_publisher(DriveCmd, MCU_DRIVE, DRIVE_OUT_QOS)
        self._state_pub = self.create_publisher(SupervisorState, STATE_TOPIC, STATE_QOS)
        self._mcu = self.create_client(McuCommand, MCU_COMMAND, callback_group=self._group)

        self.create_service(Reset, '~/arm', self._on_arm, callback_group=self._group)
        self.create_service(Trigger, '~/disarm', self._on_disarm, callback_group=self._group)
        self.create_service(Trigger, '~/brake', self._on_brake, callback_group=self._group)

        self.create_timer(1.0 / send_hz, self._tick, callback_group=self._group)
        self.create_timer(1.0, lambda: self._publish_state(force=True),
                          callback_group=self._group)
        self._publish_state(force=True)
        self.get_logger().info(
            f'supervisor up: disarmed, incident 0, inputs {inputs}, send_hz {send_hz}')

    # -- helpers ----------------------------------------------------------
    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _publish_drive(self, heading: float, throttle: float, source: str) -> None:
        msg = DriveCmd()
        msg.stamp = self.get_clock().now().to_msg()
        msg.heading_rad = float(heading)
        msg.throttle = float(throttle)
        msg.source = source[:16] or 'supervisor'
        self._drive_pub.publish(msg)

    def _publish_state(self, force: bool = False) -> None:
        now = self._now()
        st = self._arb.state(now)
        if not force and st == self._last_state:
            return
        self._last_state = st
        msg = SupervisorState()
        msg.stamp = self.get_clock().now().to_msg()
        msg.armed = st.armed
        msg.estop_latched = st.estop_latched
        msg.incident = st.incident
        msg.active_source = st.active_source[:32]
        msg.reason = st.reason[:64]
        self._state_pub.publish(msg)

    def _mcu_cmd(self, text: str) -> McuCommand.Request:
        req = McuCommand.Request()
        req.command = text
        return req

    async def _send_mcu(self, text: str):
        resp = await call_service(self, self._mcu, self._mcu_cmd(text),
                                  self._mcu_timeout, self._group)
        return resp is not None and resp.ok, resp

    async def _disarm_mcu(self) -> None:
        """Send MCU DISARM once per latch (retried from the tick until it succeeds)."""
        incident = self._arb.incident
        if self._disarm_acked == incident:
            return
        self._disarm_busy_until = self._now() + self._mcu_timeout   # tick retry backs off
        ok, resp = await self._send_mcu('DISARM')
        self._disarm_busy_until = 0.0
        if ok:
            self._disarm_acked = incident
        else:
            self.get_logger().warning(
                'MCU DISARM not confirmed (will retry; silence still stops the car): '
                f'{resp.reply if resp else "no reply"}')

    def _latch(self, how: str, reason: str) -> bool:
        new = getattr(self._arb, how)(reason)
        if new:
            self.get_logger().warning(f'LATCHED incident {self._arb.incident}: {reason}')
        self._publish_state(force=True)
        return new

    # -- callbacks ----------------------------------------------------------
    def _on_cmd(self, topic: str, msg: DriveCmd) -> None:
        self._arb.receive(topic, msg.heading_rad, msg.throttle, self._now())

    def _on_event(self, msg: McuEvent) -> None:
        if msg.code == McuEvent.FAILSAFE:
            if self._latch('failsafe', f'mcu failsafe: {msg.text}'[:64]):
                self._disarm_acked = self._arb.incident     # MCU already disarmed
        elif msg.code in (McuEvent.READY, McuEvent.DISARMED) and self._arb.armed:
            what = 'rebooted' if msg.code == McuEvent.READY else 'disarmed itself'
            if self._latch('failsafe', f'mcu {what}'):
                self._disarm_acked = self._arb.incident

    def _tick(self) -> None:
        touch(self._hb_file)
        now = self._now()
        out = self._arb.output(now)
        if out is not None:
            self._publish_drive(out.heading, out.throttle, out.source)
        elif self._arb.latched and self._disarm_acked != self._arb.incident:
            self._retry_disarm()
        self._publish_state()

    def _retry_disarm(self) -> None:
        """Non-blocking MCU DISARM retry driven by the tick (callback style)."""
        now = self._now()
        if now < self._disarm_busy_until or not self._mcu.service_is_ready():
            return
        self._disarm_busy_until = now + self._mcu_timeout
        incident = self._arb.incident
        future = self._mcu.call_async(self._mcu_cmd('DISARM'))

        def done(fut):
            if not fut.cancelled() and fut.exception() is None and fut.result().ok:
                self._disarm_acked = incident
            self._disarm_busy_until = 0.0

        future.add_done_callback(done)

    async def _on_arm(self, request, response):
        ok, msg = self._arb.check_reset(request.incident, self._now())
        if not ok:
            response.ok, response.message = False, msg
            return response
        mcu_ok, resp = await self._send_mcu('ARM')
        if not mcu_ok:
            response.ok = False
            response.message = f'MCU ARM failed: {resp.reply if resp else "no reply"}'
            return response
        ok, msg = self._arb.reset(request.incident, self._now())
        if not ok:
            # A brake/disarm raced the MCU ARM: the latch wins, make sure MCU is disarmed.
            self._disarm_acked = -1
            await self._disarm_mcu()
        else:
            self.get_logger().info(f'ARMED (incident {self._arb.incident})')
        self._publish_state(force=True)
        response.ok, response.message = ok, msg
        return response

    async def _on_disarm(self, request, response):
        self._latch('disarm', 'operator disarm')
        await self._disarm_mcu()
        response.success = self._disarm_acked == self._arb.incident
        response.message = f'disarmed, incident {self._arb.incident}'
        if not response.success:
            response.message += ' (MCU DISARM unconfirmed, retrying; drive stream stopped)'
        return response

    async def _on_brake(self, request, response):
        # Throttle-neutral first, then latch + DISARM.
        self._publish_drive(0.0, 0.0, 'supervisor')
        self._latch('brake', 'operator brake')
        await self._disarm_mcu()
        response.success = self._disarm_acked == self._arb.incident
        response.message = f'braked, incident {self._arb.incident}'
        if not response.success:
            response.message += ' (MCU DISARM unconfirmed, retrying; drive stream stopped)'
        return response


def main(args=None):
    rclpy.init(args=args)
    node = SupervisorNode()
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
