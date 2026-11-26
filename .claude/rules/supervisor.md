---
paths:
  - "ros2_ws/src/rccar_supervisor/**"
---

# Supervisor (safety authority)

Reference (input priorities and timeouts, state limits, stop-path checklist): `docs/interfaces/ros2.md`. ros2-engineering reference: safety-estop sections 3, 5 and 6.

- The supervisor is the only publisher of `/rccar/mcu/drive` (invariant 3, `docs/invariants.md`). Never add a second publisher (the fake MCU in tests only subscribes).
- The highest-priority fresh input wins. Never forward a stale input.
- Boot state: disarmed, not latched, incident 0. Arming needs an explicit Reset.
- `brake`, `disarm` and an MCU FAILSAFE event latch a new incident and stop forwarding at once. Services bypass arbitration and send MCU DISARM until confirmed.
- `arm` is `Reset(incident)`: only for the current incident, only while the top-priority input is neutral or stale. The result is armed but stationary. Discard commands from before the reset. Forward throttle 0 from each input until that input has sent a neutral command since the reset.
- Fail-safe by silence: while disarmed, publish nothing. Keep `cmd_timeout_ms >= 3 x 1000/send_hz` (the ESP32 disarm is the backstop).
- Logic stays in `arbiter.py` (pure, table tests). A behavior change needs an arbiter test first.
- The software stop is not safety-rated. The ESC power switch is the hardware stop. Say so in the user docs.
- Hardware runs of the stop-path checklist are user bench only.
