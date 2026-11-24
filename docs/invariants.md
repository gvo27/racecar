# Invariants

These rules are true for every change in this repo. To change an invariant, write an ADR in `docs/adr/` first and get the owner's approval.

1. The ESP32 sends only actuator PWM and host communication. It supplies power to nothing.
2. The sensors use a separate power rail with a common ground. All signals stay at 3.3 V or less.
3. The supervisor is the only publisher of `/rccar/mcu/drive` (rule: `.claude/rules/supervisor.md`).
4. The software stop is not safety-rated. The ESC power switch is the hardware stop.
5. `tuning.toml` contains no unconfirmed parameter (rule: `.claude/rules/tuning.md`).
6. Agents never run hardware fault-injection tests. Agents never start or restart hardware without explicit human approval. The user runs the bench checklists (rule: `.claude/rules/hw-testing.md`).
