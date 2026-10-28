---
paths:
  - "rccar_supervisor/**"
---

# rccar_supervisor (safety authority; refs: safety-estop §3 §5 §6)

- sole publisher of `/rccar/mcu/drive`. Inputs `/rccar/cmd/<source>` with (priority, timeout) from config keyed on topic (admin 100/0.3 s, captain 10/0.5 s). Highest-priority fresh input wins; stale input never forwarded.
- boot: disarmed, not latched, incident 0, explicit Reset required.
- `brake` / `disarm` / MCU FAILSAFE event latch a new incident (idempotent while latched) and stop forwarding immediately (services bypass arbitration, send MCU DISARM, retried until confirmed).
- `arm` = `Reset(incident)`: only for the current incident (stale refused), only while top-priority input is neutral/stale; result = armed but stationary. Generation fence: commands received before the reset are discarded; neutral is streamed until a fresh command arrives.
- fail-safe by silence: while disarmed publish nothing; esp32 `cmd_timeout_ms` disarm is the backstop. Keep `cmd_timeout_ms >= 3 x 1000/send_hz`.
- state: `/rccar/supervisor/state` reliable + transient_local; reason strings <= 64 chars.
- logic in `arbiter.py` (pure, table tests: priority, timeout, latch, reset needs neutral, single output). Node = wiring. Any behavior change needs an arbiter test first.
- software stop is not safety-rated; ESC power switch is the independent hardware stop (state it in user docs).
- QoS rows: see ros2.md. Never add a second publisher on /rccar/mcu/drive (fake MCU in tests only subscribes).
- stop-path checklist: kill teleop, kill core, unplug usb, agent loss, stale reset, reset with throttle != 0, double brake, brake during reset. Hardware runs of these are user bench only.
