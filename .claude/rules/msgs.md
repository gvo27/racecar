---
paths:
  - "rccar_msgs/**"
  - "firmware/esp32/extra_packages/**"
---

# rccar_msgs (interface contract, shared with the esp32)

- bounded strings only (`string<=N`): micro-ROS static memory. No unbounded `string`/sequences in anything the firmware sees.
- sync rule: `firmware/esp32/extra_packages/rccar_msgs` is a copy of `rccar_msgs/` (`cp -r rccar_msgs/. firmware/esp32/extra_packages/rccar_msgs/`). Never edit the copy. CI `interfaces-sync` runs `diff -r`.
- any msg/srv change => both copies + firmware/esp32/src/main.cpp + rccar_mcu_bridge (+ supervisor/teleop/calibration users) + docs + `make build`; entity counts in firmware/esp32/rccar.meta if entities change.
- REP-103 SI units: angles rad (+ = left/CCW), `throttle` dimensionless [-1, 1] (not m/s), time as builtin_interfaces/Time. Document units in the .msg comments.
- priority never in a message: arbitration priority/timeout comes from supervisor config keyed on the input topic. `DriveCmd.source` is logging only.
- McuCommand reuses the firmware command grammar (ARM DISARM RAW CAL SET GET SAVE DEFAULTS TEL INFO PING; no TIME over micro-ROS). Only supervisor + mcu_bridge call it.
- rosidl: new field order/type changes are breaking for the firmware; flash firmware together with the Pi image.
