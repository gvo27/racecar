---
paths:
  - "rccar_mcu_bridge/**"
---

# rccar_mcu_bridge

- lifecycle node `/mcu_bridge`: typed services (set_param, cal_point, raw_pwm, save, get, info, push_tuning) wrap `/rccar/mcu/command` (McuCommand). Builds the ASCII commands in `commands.py`; no clamps here, the firmware owns clamps and safety checks.
- never sends ARM (supervisor owns arming). May send DISARM only via the supervisor, not here.
- on activation (once `/rccar/mcu/command` is reachable; the MCU READY may predate the bridge) and on every `McuEvent.READY` pushes `firmware_commands(tuning)` sequentially, stops at first error; SAVE only if `save_after_push`.
- `tuning.py`: pure (no rclpy). `FIRMWARE_KEYS` is the ssot of (table,key)->firmware command. It must equal `tools/rccar.py` while that exists (test_firmware_keys_identical_to_tools_rccar). `update_tuning_file` rewrites `key = value` lines in place (keys unique in tuning.toml); the file is a read-write bind mount, so write in place, never rename/replace.
- tuning key change => tuning.toml + FIRMWARE_KEYS (+ tools/rccar.py while legacy) + main.cpp setKey + test.
- heartbeat file touched every 0.5 s only while ACTIVE (docker healthcheck depends on it).
- instance attributes must not shadow rclpy.Node internals (see ros2.md); `test_lifecycle_services.py` guards it.
