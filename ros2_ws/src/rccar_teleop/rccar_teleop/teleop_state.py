"""Pure key decoding and teleop state (no rclpy, no termios)."""

ARROWS = {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}
ESC = '\x1b'


class KeyDecoder:
    """Turn raw terminal bytes into key names; keeps partial escape sequences."""

    def __init__(self):
        self._buf = ''

    def feed(self, text: str) -> list:
        self._buf += text
        keys = []
        while self._buf:
            ch = self._buf[0]
            if ch != ESC:
                keys.append(ch)
                self._buf = self._buf[1:]
                continue
            if len(self._buf) < 2:
                break                                  # wait for the rest
            nxt = self._buf[1]
            if nxt == 'O':                             # SS3: ESC O A
                if len(self._buf) < 3:
                    break
                name = ARROWS.get(self._buf[2])
                if name:
                    keys.append(name)
                self._buf = self._buf[3:]
            elif nxt == '[':                           # CSI: ESC [ params final
                end = 2
                while end < len(self._buf) and not '@' <= self._buf[end] <= '~':
                    end += 1
                if end >= len(self._buf):
                    break
                name = ARROWS.get(self._buf[end]) if end == 2 else None
                if name:
                    keys.append(name)
                self._buf = self._buf[end + 1:]
            else:                                      # ESC followed by a normal key
                keys.append('esc')
                self._buf = self._buf[1:]
        return keys

    def flush(self) -> list:
        """Emit a pending lone ESC (call when no further bytes arrive)."""
        pending, self._buf = self._buf, ''
        return ['esc'] if pending.startswith(ESC) else []


class TeleopState:
    """Throttle/heading set-points driven by key presses."""

    def __init__(self, max_throttle=0.3, throttle_step=0.05, heading_step=0.0873,
                 max_heading=0.5236):
        self.max_throttle = abs(max_throttle)
        self.throttle_step = throttle_step
        self.heading_step = heading_step
        self.max_heading = abs(max_heading)
        self.throttle = 0.0
        self.heading = 0.0

    def _step_throttle(self, delta: float) -> None:
        value = round(self.throttle + delta, 4)
        self.throttle = max(-self.max_throttle, min(self.max_throttle, value))

    def _step_heading(self, delta: float) -> None:
        value = round(self.heading + delta, 4)
        self.heading = max(-self.max_heading, min(self.max_heading, value))

    def handle(self, key: str):
        """
        Apply a key; return an action name for the node or None.

        Actions: brake, disarm, arm, arm_refused, quit, shutdown.
        """
        if key == 'up':
            self._step_throttle(self.throttle_step)
        elif key == 'down':
            self._step_throttle(-self.throttle_step)
        elif key == 'left':
            self._step_heading(self.heading_step)          # REP-103: + = left
        elif key == 'right':
            self._step_heading(-self.heading_step)
        elif key == 'c':
            self.heading = 0.0
        elif key == ' ':
            self.throttle = 0.0
            return 'brake'
        elif key == 'd':
            self.throttle = 0.0
            return 'disarm'
        elif key == 'a':
            return 'arm' if self.throttle == 0.0 else 'arm_refused'
        elif key in ('q', 'Q', 'esc'):
            self.throttle = 0.0
            return 'quit'
        elif key in ('x', 'X'):
            self.throttle = 0.0
            return 'shutdown'
        return None
