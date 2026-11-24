---
paths:
  - "ros2_ws/src/rccar_mcu_bridge/**"
---

# mcu_bridge

Reference (services, push sequence, heartbeat): `docs/interfaces/ros2.md`. Key-change rule: `.claude/rules/tuning.md`.

- No clamps in the bridge. The firmware owns the clamps and the safety checks.
- Never send ARM. The supervisor owns arming. DISARM goes through the supervisor, not the bridge.
- `tuning.py` stays pure (no rclpy).
- Write `tuning.toml` in place, never rename or replace it: it is a read-write bind mount.
- Touch the heartbeat file only while the node is ACTIVE.
- `test_lifecycle_services.py` guards the rclpy.Node attribute rule of `.claude/rules/ros2.md`.
