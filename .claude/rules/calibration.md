---
paths:
  - "rccar_calibration/**"
  - "rccar_teleop/**"
---

# rccar_calibration + rccar_teleop (run with `make calibrate|tune|test|teleop`, stack up)

- `bench_test` NEVER arms and never commands throttle (the motor stays off). It does a steering sweep and a failsafe check only. There is no ROS throttle test.
- `calibrate` prompts for physical steps and jogs with raw_pwm/cal_point. On `save` it writes the ESP32 flash (mcu_bridge save) and `tuning.toml` through `update_tuning_file` (in place, bind mount rw). It writes only `[steering.calibration]` / `[throttle.calibration]` keys that exist. It adds no new keys.
- `rangefinder_monitor` (`make rangefinder`) is a read-only subscriber on `/rccar/rangefinder/range` (best effort). It prints MCU stamp, Pi time, range and rate. It prints a hint every 2 s while no data arrives. Pure formatting is in `rangefinder_format.py`.
- `tune` calls `/mcu_bridge/push_tuning` (+ save).
- All ESP32 access goes through mcu_bridge services. Nothing here opens a serial port.
- Teleop keys: up/down = throttle, left/right = heading (+ = left), `c` = center, space = BRAKE, `d` = disarm, `a` = arm (Reset). `a` is refused unless throttle is 0. `q` = disarm + quit, `x` = disarm + quit + shutdown hint. Terminal mode is restored on every exit path. Teleop publishes `DriveCmd(source='admin')` on /rccar/cmd/admin. Default max throttle is 0.3.
- Pure helpers (teleop_state.py, helpers.py) hold the logic and have pytest tests. Keep keyboard I/O in the node file.
- If you change a key or service name, change README + docs/setup.md key table + this file.
