---
paths:
  - "firmware/esp32/include/rangefinder.h"
  - "firmware/esp32/src/rangefinder*.cpp"
  - "firmware/esp32/src/main.cpp"
  - "rccar_calibration/**/rangefinder*"
  - "docs/datasheets/*rangefinder*"
  - "docs/datasheets/LIDAR-Lite*"
  - "tuning.toml"
---

# Rangefinder (Garmin LIDAR-Lite v4 LED on ESP32 I2C)

Software name is always "rangefinder"; the model name appears only in docs/datasheets and the README inventory/wiring.

## Docs (read these, keep them in sync)
- datasheet PDF: `docs/datasheets/LIDAR-Lite LED v4 Instructions_EN-US.pdf` (source https://static.garmin.com/pumac/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf; Garmin code https://github.com/garmin/)
- summary + datasheet->tuning key map: `docs/datasheets/rangefinder_lidar_lite_v4.md`
- wiring + pin map (== pins.h): README.md "Pin map", "Rangefinder wiring"
- bring-up + I2C note: docs/setup.md "Rangefinder"
- firmware rules (pins, tasks, rccar.meta, FW version): .claude/rules/firmware.md
- QoS (sensor data = best effort): .claude/rules/ros2.md
- `make rangefinder` tool: .claude/rules/calibration.md
- tuning ssot: .claude/rules/tuning.md; FIRMWARE_KEYS: .claude/rules/mcu_bridge.md
- plan: docs/docker_ros_plan.md phase 4
- PR bench checklist: .github/pull_request_template.md

## Wiring (P1 only; Garmin pin -> target)
- 1 VIN 5 V (4.75-5.25 V; 85 mA acquiring, 2 mA idle), red -> regulated 5 V sensor rail. never ESP32 5V/3V3
- 2 GND, black -> common ground (P1-22)
- 3 SDA, white/green (TBD) -> GPIO8 (P1-12)
- 4 SCL, white/green (TBD) -> GPIO9 (P1-15)
- 5-10 GPIOA, GPIOB, nRF debug: unconnected (GPIOB low at power-up = BLE bootloader)
- internal 13 kOhm pull-ups to 3.3 V: no level shifter, no external pull-ups; all signals <= 3.3 V
- GPIO10/11 (P1-16/17) are spare (no longer reserved DIST_TRIG/ECHO)

## Names
- topic `/rccar/rangefinder/range` sensor_msgs/Range, best effort; frame `rangefinder_link` (no TF yet: `rccar_description` is phase 4); only raw == `no_return_raw` -> +inf, all other values published unchanged (consumers check min_range/max_range, REP-117)
- McuCommand `SENS rangefinder` = read-only status + config line (does not enable/disable publishing); disable with `SET rf_driver 0` or `[rangefinder] driver = 0` + `make tune`
- link budget: UART0 115200 baud = ~11.5 KB/s; a Range frame is ~80 B, so 50 Hz (default) = ~4 KB/s; firmware clamps `rf_period_ms` >= 20 ms
- the Range publisher is created last and is non-fatal (a stale micro-ROS lib with 2 publishers still gives a working drive/command session, no range topic)
- firmware: `rangefinderTask` (core 0, device-agnostic), `include/rangefinder.h` (driver interface), `src/rangefinder_lidar_lite_v4.cpp` (Garmin protocol only here); FW 0.3.0; rccar.meta publishers = 3
- pi tool: `make rangefinder` -> rccar_calibration `rangefinder_monitor` (MCU stamp via rmw_uros_sync_session, Pi receive time, range m/cm, rate)
- keys: tuning.toml `[rangefinder]` driver i2c_addr period_ms reading_scale_m no_return_raw min_range_m max_range_m fov_rad radiation_type -> `SET rf_*` (rccar_mcu_bridge.tuning.FIRMWARE_KEYS + main.cpp setKey, test-enforced)
- timestamp = when the ESP32 completed the read; SDA/SCL clocking is inherent to I2C hardware (master drives SCL)

## Invariants
- absence-tolerant: no sensor / driver=0 => firmware behaves identically (control, failsafe, telemetry unchanged); init failure retries slowly, never blocks
- never blocks control task or loop(); I2C only in rangefinderTask (core 0), bounded timeouts
- no Serial prints, no PWM/LEDC touch from the task
- device protocol (addresses, registers, byte order) only in the driver file; task/main/ROS side are device-agnostic
- device characteristics are tuning params, not constants; no unconfirmed params in tuning.toml
- e-brake thresholds deferred until bench data; when added, they live in firmware (not the Pi), then tuning.toml + FIRMWARE_KEYS + setKey
- sensor power from the sensor rail, never from the ESP32
- interface/protocol change => rccar_msgs + extra_packages + main.cpp + rccar_mcu_bridge + docs (see msgs.md)

## Swap to another rangefinder
1. new `firmware/esp32/src/rangefinder_<model>.cpp` implementing `include/rangefinder.h`
2. register in the driver table entry (`driver` id)
3. new `[rangefinder]` values from its datasheet (confirmed only)
4. new `docs/datasheets/rangefinder_<model>.md` summary + archived PDF; update this file's Docs and Wiring, README wiring, mapping table
5. update paths above, layout.yaml; wiring change => pins.h == README

## Deploy
- flash firmware BEFORE `make car-up` with the new Pi image: old firmware answers `ERR unknown key rf_driver` and the tuning push stops before SAVE
- `CFG_MAGIC` bump resets NVS config to defaults until the automatic tuning push / `make tune`
- `make clean && make flash` once (`rccar.meta` changed: 3 publishers)

## Verification
- CI: `make build` (firmware.yml), `make ros-test` (FIRMWARE_KEYS drift test, monitor unit tests)
- hardware: user-run bench checklist in the PR body (.github/pull_request_template.md); never claim hardware verification without user output
