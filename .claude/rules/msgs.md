---
paths:
  - "ros2_ws/src/rccar_msgs/**"
  - "firmware/esp32/extra_packages/**"
---

# rccar_msgs (interface contract with the ESP32)

Command grammar: `docs/firmware/README.md`.

- Bounded strings only (`string<=N`): micro-ROS uses static memory. No unbounded string or sequence in a message that the firmware sees.
- `firmware/esp32/extra_packages/rccar_msgs` is a copy of `ros2_ws/src/rccar_msgs/` (`cp -r ros2_ws/src/rccar_msgs/. firmware/esp32/extra_packages/rccar_msgs/`). Never edit the copy. CI `interfaces-sync` runs `diff -r`.
- A msg or srv change also changes: both copies, `firmware/esp32/src/main.cpp`, `rccar_mcu_bridge` and its users (supervisor, teleop, calibration), the docs, `make build`, and the entity counts in `firmware/esp32/rccar.meta` if entities change.
- REP-103 SI units: angles in rad (+ = left), `throttle` dimensionless in [-1, 1], time as `builtin_interfaces/Time`. Write the units in the .msg comments.
- Never put a priority in a message. Arbitration comes from the supervisor config. `DriveCmd.source` is for logging only.
- Only the supervisor and `mcu_bridge` call McuCommand.
- A field order or type change breaks the firmware. Flash the firmware together with the new Pi image.
