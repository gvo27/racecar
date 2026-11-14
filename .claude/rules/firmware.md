---
paths:
  - "firmware/esp32/**"
---

# Firmware implementation rules (ESP32-S3-N16R8)

## Build
- There is one PlatformIO env, `esp32s3` (default). It uses `platform = espressif32@6.9.0`: Arduino-ESP32 2.0.17, ESP-IDF 4.4.7, `board = esp32-s3-devkitc-1`. micro-ROS is the only comms layer: no comms macros, no `#ifdef` variants. `FW_ENV=` on make defaults to this env.
- micro-ROS comms layer: `micro_ros_platformio` is pinned by commit. `board_microros_distro = jazzy`. The serial transport is on UART0 (framed XRCE). Entity limits are in `rccar.meta` (1 node, 3 pubs, 1 sub, 1 service). `rccar_msgs` comes from `extra_packages/` (synced copy, bounded strings only). The first `pio run` builds the library with colcon into `.pio/libdeps` (~10 min, needs git, cmake, network). `loop()` runs `spin_some` + a reconnect state machine (sparse pings). Time uses `rmw_uros_sync_session`.
- Memory: `board_build.arduino.memory_type = qio_opi` (quad flash, octal PSRAM). A wrong type causes a boot loop.
- The compiler is `-std=gnu++11`. Do not use `std::clamp`, C++14 aggregate init with default member initializers, or `if constexpr`.
- `ARDUINO_USB_CDC_ON_BOOT=0`: `Serial` = UART0 = CH343 = right-hand USB-C port "COM". Use COM for flashing and for the host link (laptop now, Pi later). The left port "USB" (native, GPIO19/20) is reserved as a regulated power input. Never use it for comms.
- Build and flash only with `make build` / `make flash` / `make monitor`. They run in docker image `rccar-fw` (`docker/firmware.Dockerfile`, build it with `make fw-image`). `build` and `flash` delete only `firmware/esp32/.pio/build` (they keep `.pio/libdeps`, the micro-ROS library cache). `make clean` deletes all of `.pio`. After you change `rccar.meta` (or `extra_packages`), run `make clean && make build`. The micro-ROS library is built one time into `.pio/libdeps`. To our knowledge, it is not rebuilt when the meta changes (unverified). CI keys its cache on `rccar.meta`, so CI always rebuilds. A stale library shows up as a publisher creation that fails at runtime. `flash` and `monitor` refuse to run while the car stack (mcu-agent) holds the serial port.
- A host `pio` is not necessary. The toolchain cache is the named volume `rccar-platformio-v2` on `/opt/platformio`. Serial: `--device $(PORT)` + `--group-add <dialout gid>`.
- CI: `.github/workflows/firmware.yml` runs `make build FW_ENV=esp32s3`, caches `.pio/libdeps` (key: platformio.ini, rccar.meta, extra_packages) and uploads `firmware.bin`. CI only compiles. Behavior is a user bench test.

## Architecture invariants
- `controlTask()` (100 Hz default, core 1, high prio) is the ONLY writer of PWM outputs.
- `loop()` is for comms only (micro-ROS spin, publishers, reconnect). Never block it. Never write PWM from it. After `setup()`, nothing else may print to `Serial` (UART0 carries the XRCE stream).
- Shared state (`g_cfg`, `g_cmd`, `g_out`, `g_armed`, `g_rawSteerUs`, `g_rangefinder`) is read and written only inside `portENTER_CRITICAL(&g_mux)`. Copy the data out, then work on the copy. Make no Serial calls inside critical sections.
- PWM uses the ESP-IDF LEDC driver (`driver/ledc.h`), not Arduino `ledc*` (its API differs between core 2.x and 3.x). Servo = LEDC timer 0 / channel 0. ESC = timer 1 / channel 1. Both use 14-bit, low-speed mode.
- `setup()` must initialise both PWM outputs at 50 Hz / 1500 us BEFORE anything else (the ESC learns neutral at power-on).
- `rangefinderTask()` (core 0, priority 1, own task) owns the I2C bus and `g_rangefinder`. It tolerates absence: with no sensor it sets `present=false` and probes again every 1 s. It never blocks `controlTask`/`loop()`. It never touches `Serial` or PWM. Device protocol is only in `src/rangefinder_*.cpp` behind `include/rangefinder.h`. Every output characteristic (scale, no-return value, min/max, FOV, radiation type, period, address, driver) is a `Config`/tuning key `rf_*`. See `.claude/rules/rangefinder.md`.
- `setup()` calls `esp_log_level_set("*", ESP_LOG_NONE)`. No IDF log line may reach UART0 and corrupt the XRCE stream.
- `Wire.begin` runs lazily in `rangefinderTask`, only after a non-null driver is selected (driver 0 leaves GPIO8/9 untouched).
- The Range publisher is created last (after the executor) and is non-fatal (`g_rangePubOk`). A stale micro-ROS lib with 2 publishers still gives a working drive/command session. `publishRange` does nothing without the publisher. `destroyEntities` finalises the publisher only if the flag is set.
- The control task is registered with the task watchdog. A hang must reset the chip (pins go idle, ESC cuts after 0.1 s).

## Safety invariants (do not weaken without an explicit request)
- Throttle requires `ARM`. The boot state is disarmed.
- If no drive command (`/rccar/mcu/drive`) arrives for `timeoutMs`, the ESP32 disarms, sets neutral and sends a `FAILSAFE` event.
- Steering clamp: calibrated `left`/`right` in drive mode. In RAW mode, 500-2500 us absolute (DS3225 datasheet).
- ESC clamp: 900-2100 us absolute. `esc_min < esc_neutral < esc_max` is enforced on every SET.
- Frame rates: servo 50-330 Hz (datasheet), ESC 50-400 Hz (use more than 50 Hz only after you confirm the ESC accepts it).
- `SAVE` refuses unless center lies between left and right.

## Pins
- Single source of truth: `firmware/esp32/include/pins.h`. Keep the README table identical.
- Use left header P1 only. Never use GPIO3/46 (strapping), 35-37 (PSRAM), 19/20 (native USB), 43/44 (COM UART), 0/45 (strapping).
- Active: steer 4, throttle 5, I2C SDA/SCL 8/9 (rangefinder now, IMU shares the bus later). Reserved (declared, not configured): BATT_LOW 6, IMU_INT 7, ENC_A/B 15/16. Spare: 10, 11, 12, 13, 14, 17, 18.
- The ESP32 supplies no power to peripherals. Sensors use a separate rail with common ground and <=3.3 V signals.

## Protocol (McuCommand grammar over micro-ROS, no serial ASCII host link)
- Commands: `D h s`, `ARM`, `DISARM`/`STOP`, `PING [seq]`, `TIME ms`, `TEL hz`, `RAW us|OFF`, `CAL LEFT|CENTER|RIGHT us`, `SET key val`, `GET`, `SAVE`, `DEFAULTS`, `SENS name`, `INFO`. `SENS rangefinder` is implemented. It returns one read-only line with status + all `rf_*` config: `present driver addr period_ms scale_m no_return min_m max_m fov_rad radiation raw range_m status age_ms seq`. If present=0, then raw=0 and range_m=nan. Other names return `ERR`.
- The reply length limit is 384 chars (`REPLY_CAP`). `CFG` carries no `rf_*` keys (test_tuning.py checks that the worst-case widths of `CFG` and `SENS rangefinder` are <= 384). `SET rf_*` still replies with `CFG`, so rf values are not echoed. Read them back with `SENS rangefinder`. `rf_period_ms` is clamped to >= 20 ms (UART0 115200 baud ~ 11.5 KB/s, a Range frame is ~80 B, 50 Hz ~ 4 KB/s). `rf_min_m` and `rf_max_m` are clamped independently. A SET that leaves `rf_min_m >= rf_max_m` is rejected with `ERR rf_min_m must be < rf_max_m`.
- Reply prefixes: `OK`, `ERR`, `CFG`, `PONG`, `INFO`, `SENS`. `mcu_bridge` matches on these prefixes.
- Drive is the `DriveCmd` subscription on `/rccar/mcu/drive` (heading_rad -> deg internally, throttle [-1,1]). The ESP32 never acknowledges it. Every other command goes through the `McuCommand` service `/rccar/mcu/command`. The service runs `handleLine(char*, Print&)` (`StrPrint` captures the reply into a bounded string), so the clamps and safety checks stay in one place. `D` over the service is refused (`ERR`): the drive subscription is the only drive path. `TIME` returns `ERR` (time sync = `rmw_uros_sync_session`). Telemetry and events are `Telemetry`/`McuEvent` topics. Manual check: `make mcu CMD="GET"` (stack up).
- If you add or rename a command, `SET` key or interface, you must make matching changes in `rccar_msgs` + `firmware/esp32/extra_packages` (diff -r clean), `rccar_mcu_bridge` (`FIRMWARE_KEYS`, commands), `tuning.toml`, and `docs/`. `test_tuning.py` checks `FIRMWARE_KEYS` against `tuning.toml` and the `setKey`/`CAL` names in `main.cpp`.
- `tuning.toml` layout per device: `[<dev>]` has hand-tuned knobs. `[<dev>.calibration]` has measured values (for example `[steering.calibration]`, `[throttle.calibration]`, written by `make calibrate`, later by an auto-calibration warm-up). `[warmup.<dev>]` has routine settings. Never add unconfirmed parameters.

## Config persistence
- The `Config` struct is stored as one NVS blob (`Preferences`, namespace `rccar`, key `cfg`).
- Any change to the `Config` layout MUST bump `CFG_MAGIC` (the firmware then ignores old blobs and loads defaults).

## Adding a sensor
- The rangefinder is the template: see `.claude/rules/rangefinder.md` (driver table, `rf_*` keys, `Range` topic). Each new sensor gets its own `.claude/rules/<sensor>.md`.
- Add its pins to `pins.h` (already reserved). Fill its empty section in `tuning.toml` after you confirm the parameters against `docs/datasheets/`.
- Read sensors in their own task. If safety needs it (for example emergency brake from distance), read them in `controlTask()`. Report with `SENS <name> k=v ...` and telemetry fields.
- Emergency braking must live in firmware, so that it works without the host.
