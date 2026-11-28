---
paths:
  - "firmware/esp32/include/rangefinder.h"
  - "firmware/esp32/src/rangefinder*.cpp"
  - "firmware/esp32/src/main.cpp"
  - "ros2_ws/src/rccar_calibration/**/rangefinder*"
  - "docs/datasheets/*rangefinder*"
  - "docs/datasheets/LIDAR-Lite*"
  - "docs/rangefinder/**"
  - "tuning.toml"
---

# Rangefinder (ESP32 I2C)

The software name is always "rangefinder". The model name appears only in the datasheet docs and in `docs/hardware.md` (inventory and wiring) and in the root README pinout.

Docs: status, findings and the swap procedure `docs/rangefinder/README.md`. Datasheet summary, pinout, registers and tuning key map `docs/datasheets/rangefinder_lidar_lite_v4.md`. Wiring: `docs/hardware.md`. Pin map: root `README.md`. Firmware rules: `.claude/rules/firmware.md`.

## Rules
- The firmware tolerates absence: with no sensor or `driver = 0`, control, failsafe and telemetry do not change. A failed init retries slowly and never blocks.
- I2C runs only in `rangefinderTask` (core 0), with bounded timeouts. The task makes no Serial prints and does not touch PWM or LEDC.
- Device protocol (addresses, registers, byte order) is only in the driver file. The task, `main.cpp` and the ROS side are device-agnostic.
- Device characteristics are `[rangefinder]` tuning keys, not constants. Only confirmed values.
- Publish only a raw value equal to `no_return_raw` as +inf. Publish all other values unchanged (consumers check min_range and max_range, REP-117).
- `SENS rangefinder` is read-only. It does not enable or disable publishing (`SET rf_driver 0` does).
- Keep pins 5 to 10 of the sensor unconnected (GPIOB low at power-up starts the BLE bootloader).
- Sensor power comes from the sensor rail, never from the ESP32.
- E-brake thresholds wait for bench data. They live in the firmware first, then become tuning keys (`firmware-change`, "Tuning key").
- An interface or protocol change follows `.claude/rules/msgs.md`.
- Deploy order: flash the firmware before `make car-up` with a new Pi image.

## Verify
CI: `make build`, `make ros-test` (FIRMWARE_KEYS drift test, monitor unit tests). Hardware: the user-run bench checklist in the PR body. Never claim hardware verification without output from the user.
