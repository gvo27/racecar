"""
Command arbitration and latched-stop state machine (pure, no rclpy).

Semantics follow safety-estop.md section 5:

* boot: disarmed, not latched, incident 0, an explicit reset is required;
* ``brake``/``disarm``/``failsafe`` latch a new incident (idempotent while
  already latched) and stop all forwarding;
* ``reset(incident, now)`` is accepted only for the current incident while the
  top-priority (admin) input is neutral or stale, and yields *armed but stationary*: commands
  received before the reset are discarded (generation fence), so neutral is
  streamed until a command arrives after the reset;
* silence is the stop: when disarmed ``output`` returns None.

All times are seconds on whatever clock the caller uses (node clock).
"""
from dataclasses import dataclass
import math

ADMIN_TOPIC = '/rccar/cmd/admin'
CAPTAIN_TOPIC = '/rccar/cmd/captain'

# topic -> (priority, timeout_s). Higher priority wins.
DEFAULT_INPUTS = {
    ADMIN_TOPIC: (100, 0.3),
    CAPTAIN_TOPIC: (10, 0.5),
}

NEUTRAL_THROTTLE = 0.05
REASON_MAX = 64


def source_name(topic: str) -> str:
    """``/rccar/cmd/admin`` -> ``admin``."""
    return topic.rsplit('/', 1)[-1]


def _clean(value: float, limit: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(-limit, min(limit, value))


@dataclass(frozen=True)
class Cmd:
    heading: float
    throttle: float
    rx_time: float


@dataclass(frozen=True)
class Output:
    heading: float
    throttle: float
    source: str


@dataclass(frozen=True)
class State:
    armed: bool
    estop_latched: bool
    incident: int
    active_source: str
    reason: str


class Arbiter:
    """Priority/timeout arbitration plus the arm/latch state machine."""

    def __init__(self, inputs=None, neutral_threshold: float = NEUTRAL_THROTTLE):
        self.inputs = dict(DEFAULT_INPUTS if inputs is None else inputs)
        self.neutral_threshold = neutral_threshold
        self.armed = False
        self.latched = False
        self.incident = 0
        self.reason = 'boot: reset required'
        self._last = {}

    # -- inputs ---------------------------------------------------------
    def receive(self, topic: str, heading: float, throttle: float, now: float) -> None:
        """Record a command. Stored even when disarmed (reset checks neutral)."""
        if topic not in self.inputs:
            return
        self._last[topic] = Cmd(_clean(heading, math.pi), _clean(throttle, 1.0), now)

    def _selected(self, now: float):
        best = None
        for topic, (prio, timeout) in self.inputs.items():
            cmd = self._last.get(topic)
            if cmd is None or now - cmd.rx_time > timeout:
                continue
            if best is None or prio > self.inputs[best[0]][0]:
                best = (topic, cmd)
        return best

    def select(self, now: float):
        """Return (topic, Cmd) of the highest-priority fresh input, or None."""
        return self._selected(now)

    # -- latch ----------------------------------------------------------
    def _latch(self, reason: str) -> bool:
        if self.latched:
            return False
        self.armed = False
        self.latched = True
        self.incident += 1
        self.reason = reason[:REASON_MAX]
        self._last.clear()
        return True

    def brake(self, reason: str = 'brake') -> bool:
        return self._latch(reason)

    def disarm(self, reason: str = 'disarm') -> bool:
        return self._latch(reason)

    def failsafe(self, reason: str = 'mcu failsafe') -> bool:
        return self._latch(reason)

    def check_reset(self, incident: int, now: float):
        """Would ``reset`` succeed now? Returns (ok, message) without changing state."""
        if incident != self.incident:
            return False, f'stale incident {incident}, current is {self.incident}'
        # Deadman: the top-priority input (admin) must be neutral or absent. Stale
        # lower-priority goals need no check; the generation fence discards them.
        top = max(self.inputs, key=lambda t: self.inputs[t][0])
        cmd = self._last.get(top)
        if (cmd is not None and now - cmd.rx_time <= self.inputs[top][1]
                and abs(cmd.throttle) >= self.neutral_threshold):
            return False, f'{source_name(top)} throttle not neutral'
        return True, ''

    def reset(self, incident: int, now: float):
        """Clear the latch and arm (stationary). Returns (ok, message)."""
        ok, msg = self.check_reset(incident, now)
        if not ok:
            return False, msg
        self.armed = True
        self.latched = False
        self.reason = ''
        self._last.clear()           # fence: nothing received before reset survives
        return True, 'armed'

    # -- outputs --------------------------------------------------------
    def output(self, now: float):
        """Return the values to forward as a DriveCmd, or None (stop streaming)."""
        if not self.armed:
            return None
        sel = self._selected(now)
        if sel is None:
            return Output(0.0, 0.0, '')
        topic, cmd = sel
        return Output(cmd.heading, cmd.throttle, source_name(topic))

    def state(self, now: float) -> State:
        out = self.output(now)
        active = out.source if out is not None else ''
        return State(self.armed, self.latched, self.incident, active, self.reason)
