---
paths:
  - "firmware/esp32/**"
---

# Firmware implementation rules (ESP32-S3-N16R8)

## Build
- One PlatformIO env, `esp32s3` (default; `platform = espressif32@6.9.0`: Arduino-ESP32 2.0.17, ESP-IDF 4.4.7, `board = esp32-s3-devkitc-1`). micro-ROS is the only comms layer: no comms macros, no `#ifdef` variants. `FW_ENV=` on make defaults to it.
- micro-ROS comms layer: `micro_ros_platformio` pinned by commit, `board_microros_distro = jazzy`, serial transport on UART0 (framed XRCE), entity limits in `rccar.meta` (1 node, 3 pubs, 1 sub, 1 service), `rccar_msgs` from `extra_packages/` (synced copy, bounded strings only). The library is colcon-built into `.pio/libdeps` on the first `pio run` (~10 min, needs git, cmake, network). `loop()` runs `spin_some` + a reconnect state machine (sparse pings); time via `rmw_uros_sync_session`.
- Memory: `board_build.arduino.memory_type = qio_opi` (quad flash, octal PSRAM). Wrong type = boot loop.
- Compiler is `-std=gnu++11`: no `std::clamp`, no C++14 aggregate init with default member initializers, no `if constexpr`.
- `ARDUINO_USB_CDC_ON_BOOT=0`: `Serial` = UART0 = CH343 = right-hand USB-C port "COM". Flashing and the host link (laptop now, Pi later) use COM. The left port "USB" (native, GPIO19/20) is reserved as a regulated power input; never use it for comms.
- Build/flash only via `make build` / `make flash` / `make monitor`: they run in docker image `rccar-fw` (`docker/firmware.Dockerfile`, build with `make fw-image`); `build` and `flash` delete only `firmware/esp32/.pio/build` (keep `.pio/libdeps`, the micro-ROS library cache); `make clean` deletes all of `.pio`. After changing `rccar.meta` (or `extra_packages`) run `make clean && make build`: the micro-ROS library is built once into `.pio/libdeps` and, to our knowledge, is not rebuilt when the meta changes (unverified; CI keys its cache on `rccar.meta`, so CI always rebuilds). A stale library shows up as publisher creation failing at runtime. `flash`/`monitor` refuse while the car stack (mcu-agent) holds the serial port.
- No host `pio` needed. Toolchain cache = named volume `rccar-platformio-v2` on `/opt/platformio`. Serial: `--device $(PORT)` + `--group-add <dialout gid>`.
- CI: `.github/workflows/firmware.yml` runs `make build FW_ENV=esp32s3`, caches `.pio/libdeps` (key: platformio.ini, rccar.meta, extra_packages), uploads `firmware.bin`. CI only compiles; behavior is user bench.

## Architecture invariants
- `controlTask()` (100 Hz default, core 1, high prio) is the ONLY writer of PWM outputs.
- `loop()` is comms only (micro-ROS spin, publishers, reconnect). Never block it, never write PWM from it. Nothing else may print to `Serial` after `setup()` (UART0 carries the XRCE stream).
- Shared state (`g_cfg`, `g_cmd`, `g_out`, `g_armed`, `g_rawSteerUs`, `g_rangefinder`) is read/written only inside `portENTER_CRITICAL(&g_mux)`. Copy out, then work on the copy. No Serial calls inside critical sections.
- PWM uses the ESP-IDF LEDC driver (`driver/ledc.h`), not Arduino `ledc*` (its API differs between core 2.x and 3.x). Servo = LEDC timer 0 / channel 0, ESC = timer 1 / channel 1, 14-bit, low-speed mode.
- `setup()` must initialise both PWM outputs at 50 Hz / 1500 us BEFORE anything else (the ESC learns neutral at power-on).
- `rangefinderTask()` (core 0, priority 1, own task) owns the I2C bus and `g_rangefinder`. Absence-tolerant (no sensor -> `present=false`, re-probe every 1 s), never blocks `controlTask`/`loop()`, never touches `Serial` or PWM. Device protocol only in `src/rangefinder_*.cpp` behind `include/rangefinder.h`; every output characteristic (scale, no-return value, min/max, FOV, radiation type, period, address, driver) is a `Config`/tuning key `rf_*`. See `.claude/rules/rangefinder.md`.
- `setup()` calls `esp_log_level_set("*", ESP_LOG_NONE)`: no IDF log line may reach UART0 and corrupt the XRCE stream.
- `Wire.begin` runs lazily in `rangefinderTask`, only once a non-null driver is selected (driver 0 leaves GPIO8/9 untouched).
- The Range publisher is created last (after the executor) and is non-fatal (`g_rangePubOk`): a stale micro-ROS lib with 2 publishers still gives a working drive/command session. `publishRange` is a no-op without it; `destroyEntities` finalises it only if the flag is set.
- The control task is registered with the task watchdog; a hang must reset the chip (pins go idle, ESC cuts after 0.1 s).

## Safety invariants (do not weaken without an explicit request)
- Throttle requires `ARM`; boot state is disarmed.
- No drive command (`/rccar/mcu/drive`) for `timeoutMs` -> disarm + neutral + `FAILSAFE` event.
- Steering clamp: calibrated `left`/`right` in drive mode; 500-2500 us absolute (DS3225 datasheet) in RAW mode.
- ESC clamp: 900-2100 us absolute; `esc_min < esc_neutral < esc_max` enforced on every SET.
- Frame rates: servo 50-330 Hz (datasheet), ESC 50-400 Hz (above 50 Hz only after confirming the ESC accepts it).
- `SAVE` refuses unless center lies between left and right.

## Pins
- Single source of truth: `firmware/esp32/include/pins.h`; keep the README table identical.
- Left header P1 only. Never use GPIO3/46 (strapping), 35-37 (PSRAM), 19/20 (native USB), 43/44 (COM UART), 0/45 (strapping).
- Active: steer 4, throttle 5, I2C SDA/SCL 8/9 (rangefinder now, IMU shares the bus later). Reserved (declared, not configured): BATT_LOW 6, IMU_INT 7, ENC_A/B 15/16. Spare: 10, 11, 12, 13, 14, 17, 18.
- ESP32 supplies no power to peripherals; sensors use a separate rail with common ground and <=3.3 V signals.

## Protocol (McuCommand grammar over micro-ROS; no serial ASCII host link)
- Commands: `D h s`, `ARM`, `DISARM`/`STOP`, `PING [seq]`, `TIME ms`, `TEL hz`, `RAW us|OFF`, `CAL LEFT|CENTER|RIGHT us`, `SET key val`, `GET`, `SAVE`, `DEFAULTS`, `SENS name` (implemented: `SENS rangefinder` -> one read-only line with status + all `rf_*` config: `present driver addr period_ms scale_m no_return min_m max_m fov_rad radiation raw range_m status age_ms seq`; present=0 -> raw=0 range_m=nan; other names `ERR`), `INFO`.
- Reply length is capped at 384 chars (`REPLY_CAP`); `CFG` carries no `rf_*` keys (test_tuning.py checks worst-case widths of `CFG` and `SENS rangefinder` <= 384). `SET rf_*` still replies with `CFG`, so rf values are not echoed: read them back with `SENS rangefinder`. `rf_period_ms` is clamped to >= 20 ms (UART0 115200 baud ~ 11.5 KB/s; a Range frame is ~80 B, 50 Hz ~ 4 KB/s). `rf_min_m` / `rf_max_m` are clamped independently; a SET leaving `rf_min_m >= rf_max_m` is rejected with `ERR rf_min_m must be < rf_max_m`.
- Reply prefixes: `OK`, `ERR`, `CFG`, `PONG`, `INFO`, `SENS`. `mcu_bridge` matches on these prefixes.
- Drive is the `DriveCmd` subscription on `/rccar/mcu/drive` (heading_rad -> deg internally, throttle [-1,1]); it is never acknowledged. Every other command goes through the `McuCommand` service `/rccar/mcu/command`, which runs `handleLine(char*, Print&)` (`StrPrint` captures the reply into a bounded string), so clamps and safety checks stay in one place. `D` over the service is refused (`ERR`): the drive subscription is the only drive path. `TIME` returns `ERR` (time sync = `rmw_uros_sync_session`). Telemetry/events are `Telemetry`/`McuEvent` topics. Manual check: `make mcu CMD="GET"` (stack up).
- Adding or renaming a command, `SET` key or interface requires matching changes in `rccar_msgs` + `firmware/esp32/extra_packages` (diff -r clean), `rccar_mcu_bridge` (`FIRMWARE_KEYS`, commands), `tuning.toml`, and `docs/`. `test_tuning.py` checks `FIRMWARE_KEYS` against `tuning.toml` and the `setKey`/`CAL` names in `main.cpp`.
- `tuning.toml` layout per device: `[<dev>]` hand-tuned knobs, `[<dev>.calibration]` measured values (e.g. `[steering.calibration]`, `[throttle.calibration]`; written by `make calibrate`, later auto-calibration warm-up), `[warmup.<dev>]` routine settings. Never add unconfirmed parameters.

## Config persistence
- `Config` struct is stored as one NVS blob (`Preferences`, namespace `rccar`, key `cfg`).
- Any change to the `Config` layout MUST bump `CFG_MAGIC` (old blobs are then ignored and defaults load).

## Adding a sensor
- The rangefinder is the template: see `.claude/rules/rangefinder.md` (driver table, `rf_*` keys, `Range` topic). Each new sensor gets its own `.claude/rules/<sensor>.md`.
- Add its pins to `pins.h` (already reserved) and fill its empty section in `tuning.toml` once parameters are confirmed against `docs/datasheets/`.
- Read sensors in their own task or in `controlTask()` if needed for safety (e.g. emergency brake from distance); report via `SENS <name> k=v ...` and telemetry fields.
- Emergency braking must live in firmware so it works without the host.
