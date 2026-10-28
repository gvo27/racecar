"""
Admin keyboard teleop for an SSH terminal (``ros2 run rccar_teleop keyboard``).

Publishes DriveCmd(source='admin') on /rccar/cmd/admin at ``rate_hz`` and calls
the supervisor's arm/disarm/brake services. Terminal modes are always restored.
"""
import os
import select
import signal
import sys
import termios
import time
import tty

from rccar_msgs.msg import DriveCmd, SupervisorState
from rccar_msgs.srv import Reset
from rccar_teleop.teleop_state import KeyDecoder, TeleopState
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_srvs.srv import Trigger

HELP = ('up/down throttle  left/right heading  c center  space BRAKE  d disarm  '
        'a arm (throttle 0)  q disarm+quit  x disarm+quit (power-off hint)')
SHUTDOWN_HINT = 'run `make car-shutdown` in this shell to power off'

# Reliable, depth 1: the supervisor subscribes best effort, which matches either.
CMD_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
STATE_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.TRANSIENT_LOCAL)


class TeleopNode(Node):
    """Publishes admin commands and wraps the supervisor services."""

    def __init__(self):
        super().__init__('teleop_keyboard')
        self.declare_parameter('max_throttle', 0.3)
        self.declare_parameter('throttle_step', 0.05)
        self.declare_parameter('heading_step_rad', 0.0873)
        self.declare_parameter('max_heading_rad', 0.5236)
        self.declare_parameter('rate_hz', 20.0)
        self.declare_parameter('supervisor', '/supervisor')

        def p(name):
            return self.get_parameter(name).value

        self.state = TeleopState(p('max_throttle'), p('throttle_step'),
                                 p('heading_step_rad'), p('max_heading_rad'))
        self.rate_hz = float(p('rate_hz'))
        sup = str(p('supervisor')).rstrip('/')
        self.pub = self.create_publisher(DriveCmd, '/rccar/cmd/admin', CMD_QOS)
        self.sup_state = None
        self.create_subscription(SupervisorState, '/rccar/supervisor/state',
                                 self._on_state, STATE_QOS)
        self.arm_cli = self.create_client(Reset, f'{sup}/arm')
        self.disarm_cli = self.create_client(Trigger, f'{sup}/disarm')
        self.brake_cli = self.create_client(Trigger, f'{sup}/brake')
        self.messages = []
        self.pending = []
        self.disarm_sent = False

    def _on_state(self, msg):
        self.sup_state = msg

    def publish(self) -> None:
        msg = DriveCmd()
        msg.stamp = self.get_clock().now().to_msg()
        msg.heading_rad = float(self.state.heading)
        msg.throttle = float(self.state.throttle)
        msg.source = 'admin'
        self.pub.publish(msg)

    def _call(self, client, request, label):
        if not client.service_is_ready():
            self.messages.append(f'{label}: supervisor service not available')
            return None
        future = client.call_async(request)

        def done(fut):
            try:
                res = fut.result()
                ok = res.ok if hasattr(res, 'ok') else res.success
                self.messages.append(f'{label}: {"ok" if ok else "REFUSED"} - {res.message}')
            except Exception as exc:  # noqa: BLE001
                self.messages.append(f'{label}: failed ({exc})')

        future.add_done_callback(done)
        self.pending.append(future)
        return future

    def act(self, action):
        if action == 'brake':
            self.publish()                       # neutral first
            return self._call(self.brake_cli, Trigger.Request(), 'brake')
        if action in ('disarm', 'quit', 'shutdown'):
            self.disarm_sent = True
            if action != 'disarm':
                self.publish()
            return self._call(self.disarm_cli, Trigger.Request(), 'disarm')
        if action == 'arm_refused':
            self.messages.append('arm: set throttle to 0 first')
        elif action == 'arm':
            if self.sup_state is None:
                self.messages.append('arm: no supervisor state yet')
                return None
            req = Reset.Request()
            req.incident = int(self.sup_state.incident)
            return self._call(self.arm_cli, req, 'arm')
        return None

    def status(self) -> str:
        s = self.sup_state
        if s is None:
            sup = 'supervisor: ?'
        else:
            mode = 'ARMED' if s.armed else ('LATCHED' if s.estop_latched else 'disarmed')
            sup = f'{mode} inc {s.incident} src "{s.active_source}" {s.reason}'
        return (f'thr {self.state.throttle:+.2f}  hdg {self.state.heading:+.2f} rad  {sup}')


def _say(text: str) -> None:
    sys.stdout.write(f'\r\x1b[K{text}\r\n')
    sys.stdout.flush()


def run(node: TeleopNode, fd: int) -> str:
    """Run the teleop loop and return the final action (quit or shutdown)."""
    decoder = KeyDecoder()
    period = 1.0 / node.rate_hz
    next_pub = time.monotonic()
    final = 'quit'
    _say(HELP)
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.0)
        ready, _, _ = select.select([fd], [], [], 0.01)
        if ready:
            keys = decoder.feed(os.read(fd, 64).decode(errors='ignore'))
        else:
            keys = decoder.flush()
        stop = None
        for key in keys:
            action = node.state.handle(key)
            node.act(action)
            if action in ('quit', 'shutdown'):
                stop = action
                break
        while node.messages:
            _say(node.messages.pop(0))
        now = time.monotonic()
        if now >= next_pub:
            node.publish()
            next_pub = now + period
            sys.stdout.write(f'\r\x1b[K{node.status()}')
            sys.stdout.flush()
        if stop:
            final = stop
            break
    # give the disarm call a moment to complete
    deadline = time.monotonic() + 1.5
    while time.monotonic() < deadline and any(not f.done() for f in node.pending):
        rclpy.spin_once(node, timeout_sec=0.05)
    while node.messages:
        _say(node.messages.pop(0))
    return final


def main(args=None):
    if not sys.stdin.isatty():
        sys.stderr.write('keyboard teleop needs an interactive terminal (ssh -t / docker -it)\n')
        return 2
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)

    def on_signal(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGHUP, on_signal)
    rclpy.init(args=args)
    node = TeleopNode()
    final = 'quit'
    try:
        tty.setcbreak(fd)
        final = run(node, fd)
    except KeyboardInterrupt:
        final = 'quit'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        try:
            # best effort: make sure the supervisor is told even on Ctrl-C / SIGTERM
            if not node.disarm_sent:
                node.act('disarm')
                end = time.monotonic() + 0.5
                while time.monotonic() < end and any(not f.done() for f in node.pending):
                    rclpy.spin_once(node, timeout_sec=0.05)
        except Exception:  # noqa: BLE001
            pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.stdout.write('\n')
    if final == 'shutdown':
        print(SHUTDOWN_HINT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
