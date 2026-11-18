# Rangefinder: status and findings

This file owns the bench status of the rangefinder (Garmin LIDAR-Lite v4 LED on the ESP32 I2C bus). Other docs point here for the status. They do not copy it.

Other facts have their own owners:

| Topic | Owner |
| --- | --- |
| Wiring, names, invariants, sensor swap | [.claude/rules/rangefinder.md](../../.claude/rules/rangefinder.md) |
| Datasheet summary, registers, tuning key map | [docs/datasheets/rangefinder_lidar_lite_v4.md](../datasheets/rangefinder_lidar_lite_v4.md) |
| Tuning values | `tuning.toml` `[rangefinder]` |
| Topic, frame, QoS, rate | [docs/sensor_contract.md](../sensor_contract.md) |
| Bring-up commands | [docs/setup.md](../setup.md) "Rangefinder" |
| Pin map and wire colours | [README.md](../../README.md) "Pin map", "Wiring: Rangefinder" |

## Status (2026-11-18)

The software is in `main` (PR #5, FW 0.3.0). The owner ran most of the sensor bench checks on the Pi. The owner reports: "sensor stack is functional, have not tested full vehicle".

| Check (PR #5 bench checklist) | Result |
| --- | --- |
| Deploy: `make setup`, `make config`, `make car-down`, `make clean && make flash`, `make car-up && make car-ps` | pass |
| `make mcu CMD="GET"` shows the tuned values | pass |
| `make mcu CMD="SENS rangefinder"` shows `present=1 driver=1 addr=0x62 period_ms=20` and a plausible `range_m` | pass |
| `make rangefinder`: live lines at about 50 Hz, flat target at 0.5 m, 1 m and 2 m | pass. The readings are not recorded |
| Aimed at open space: `no return` (+inf) | not done |
| Ctrl+C exits cleanly | pass |
| Sensor rail off with the stack up: `present=0`, teleop and failsafe still work. Rail on: readings resume in about 1 s | pass |
| `SET rf_driver 0` stops publishing, `make tune` restores it | pass |
| SDA/SCL wire colours confirmed | pass (SDA white, SCL green) |
| Regression: `make test` | not done |
| Regression: `make teleop` (drive, brake, disarm) | not done |

## Findings

These are the decisions and lessons from the rangefinder work. Each one has a reason that is not clear from the code alone.

1. **Flash before `car-up`.** Old firmware answers `ERR unknown key rf_driver` to the tuning push. The push then stops before `SAVE`. Flash the new firmware first, then start the stack with the new Pi image.
2. **One clean build after a publisher change.** `rccar.meta` allows 3 publishers. A change to `rccar.meta` needs `make clean && make flash` one time, because the micro-ROS library must build again (about 10 min).
3. **The Range publisher is optional.** The firmware creates it last. If a stale micro-ROS library has only 2 publishers, drive and command still work. Only the range topic is missing.
4. **The config resets after a `CFG_MAGIC` change.** The bump to `0xC0FFEE03` resets the ESP32 config to defaults. The automatic tuning push on READY restores it. Run `make tune` to save it to flash.
5. **The UART0 link sets the minimum period.** UART0 at 115200 baud carries about 11.5 KB/s. A Range frame is about 80 B, so 50 Hz uses about 4 KB/s. The firmware clamps `rf_period_ms` to 20 ms or more. The sensor can do more than 200 Hz over I2C, so the link is the limit, not the sensor.
6. **IDF logging is off on UART0.** UART0 carries the micro-ROS (XRCE) stream. Any IDF log line corrupts it (`firmware/esp32/src/main.cpp`, `esp_log_level_set("*", ESP_LOG_NONE)`).
7. **No sensor is a normal state.** With no sensor or `driver = 0`, the control, failsafe and telemetry do not change. The task probes again every 1 s. It calls `Wire.begin` only after it selects a driver, so `driver = 0` leaves GPIO8/9 untouched. The bench test with the sensor rail off shows this.
8. **Only the no-return value becomes +inf.** The sensor reports 1 cm when it gets no valid return. The firmware publishes only a raw value equal to `no_return_raw` as +inf. It publishes all other values unchanged. Consumers must check `min_range` and `max_range` (REP-117).
9. **Keep GPIOB (pin 6) unconnected.** If GPIOB is low at power-up, the sensor starts its Bluetooth LE bootloader. Pins 5 to 10 stay unconnected.
10. **The timestamp marks the end of the I2C read.** It does not mark the time when the light left the sensor. The Pi converts it to ROS time through `rmw_uros_sync_session`.
11. **The reply cap fits the worst case.** The worst-case `CFG` and `SENS rangefinder` replies fit the 384-character reply cap. A test checks this. Do not add `rf_*` keys to `CFG`: `SENS rangefinder` reports them.

## Open items

- Aim the sensor at open space and check for `no return` (+inf).
- Record the readings at 0.5 m, 1 m and 2 m against a tape measure. Put them in this file.
- Run the regression checks `make test` and `make teleop` with the rangefinder firmware.
- Test on the full vehicle (wheels on the ground). The owner did not test this yet.
- The frame `rangefinder_link` is not in the URDF yet (`docs/sensor_contract.md`, TF row `gap`).
- The forward e-brake is not in the firmware. Its thresholds need confirmed bench readings first. They go in the firmware, then in `tuning.toml`, `FIRMWARE_KEYS` and `setKey`.
