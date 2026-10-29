---
paths:
  - "rccar_calibration/**"
  - "rccar_teleop/**"
---

# rccar_calibration + rccar_teleop (run via `make calibrate|tune|test|teleop`, stack up)

- `bench_test` NEVER arms and never commands throttle (motor stays off): steering sweep + failsafe check only. There is no ROS throttle test.
- `calibrate`: prompts for physical steps, jogs with raw_pwm/cal_point, on `save` writes the ESP32 flash (mcu_bridge save) and `tuning.toml` via `update_tuning_file` (in place, bind mount rw). Only `[steering.calibration]` / `[throttle.calibration]` keys that exist; no new keys.
- `tune`: calls `/mcu_bridge/push_tuning` (+ save).
- all MCU access through mcu_bridge services; nothing here opens a serial port.
- teleop keys: up/down throttle, left/right heading (+ = left), `c` center, space BRAKE, `d` disarm, `a` arm (Reset; refused unless throttle 0), `q` disarm+quit, `x` disarm+quit+shutdown hint. Terminal mode restored on every exit path; publish `DriveCmd(source='admin')` on /rccar/cmd/admin; max throttle default 0.3.
- pure helpers (teleop_state.py, helpers.py) carry the logic and are pytest-tested; keep keyboard I/O in the node file.
- changing a key or service name => README + docs/setup.md key table + this file.
