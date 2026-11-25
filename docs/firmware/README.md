# ESP32 firmware: reference

Facts about the ESP32-S3-N16R8 firmware in `firmware/esp32/`. The rules for changes are in [.claude/rules/firmware.md](../../.claude/rules/firmware.md). The pin map is `firmware/esp32/include/pins.h` (the table in the root [README.md](../../README.md#microcontroller-pinout) is a copy).

## Build
- One PlatformIO env, `esp32s3` (default for `FW_ENV=`). `platform = espressif32@6.9.0`: Arduino-ESP32 2.0.17, ESP-IDF 4.4.7, `board = esp32-s3-devkitc-1`.
- micro-ROS is the only comms layer. `micro_ros_platformio` is pinned by commit, `board_microros_distro = jazzy`. The serial transport is on UART0 (framed XRCE).
- Entity limits are in `rccar.meta`: 1 node, 3 publishers, 1 subscription, 1 service. `rccar_msgs` comes from `extra_packages/` (a synced copy).
- The first `pio run` builds the micro-ROS library with colcon into `.pio/libdeps` (about 10 min; needs git, cmake and network).
- `loop()` runs `spin_some` and a reconnect state machine with sparse pings. Time sync uses `rmw_uros_sync_session`.
- Memory: `board_build.arduino.memory_type = qio_opi` (quad flash, octal PSRAM). A wrong type causes a boot loop.
- `ARDUINO_USB_CDC_ON_BOOT=0`: `Serial` = UART0 = CH343 = the right-hand USB-C port "COM". The left port "USB" (native, GPIO19/20) is reserved as a regulated power input.
- `make build`, `make flash` and `make monitor` run in the docker image `rccar-fw` (`docker/firmware.Dockerfile`, `make fw-image`). The toolchain cache is the named volume `rccar-platformio-v2` on `/opt/platformio`. Serial access: `--device $(PORT)` and `--group-add <dialout gid>`.
- `build` and `flash` delete only `.pio/build` and keep `.pio/libdeps`. `make clean` deletes all of `.pio`. To our knowledge, the library is not built again when `rccar.meta` changes (not verified). A stale library shows as a publisher that fails at runtime.
- `flash` and `monitor` refuse to run while the car stack (mcu-agent) holds the serial port.
- CI: `.github/workflows/firmware.yml` runs `make build FW_ENV=esp32s3`. It caches `.pio/libdeps` (key: `platformio.ini`, `rccar.meta`, `extra_packages`) and uploads `firmware.bin`. CI only compiles.

## Tasks and peripherals
- `controlTask()`: 100 Hz default, core 1, high priority. It is registered with the task watchdog.
- `loop()`: the Arduino loop task, core 1 (Arduino default), priority 1. It owns UART0 (micro-ROS) and the NVS writes.
- `rangefinderTask()`: core 0, priority 1. It owns the I2C bus and `g_rangefinder` (see [docs/rangefinder/README.md](../rangefinder/README.md)).
- PWM: ESP-IDF LEDC driver. Servo = LEDC timer 0 / channel 0. ESC = timer 1 / channel 1. Both 14-bit, low-speed mode.
- Shared state under `g_mux`: `g_cfg`, `g_cmd`, `g_out`, `g_armed`, `g_rawSteerUs`, `g_rangefinder`.
- Pins: active steer 4, throttle 5, I2C SDA/SCL 8/9. Reserved (declared, not configured): BATT_LOW 6, IMU_INT 7, ENC_A/B 15/16. Spare: 10 to 14, 17, 18. Never used: GPIO3/46 and 0/45 (strapping), 35 to 37 (PSRAM), 19/20 (native USB), 43/44 (COM UART).

## Limits
- Steering: calibrated `left`/`right` in drive mode. RAW mode: 500 to 2500 us absolute (DS3225 datasheet).
- ESC: 900 to 2100 us absolute. `esc_min < esc_neutral < esc_max` on every SET.
- Frame rates: servo 50 to 330 Hz (datasheet), ESC 50 to 400 Hz.

## Command grammar (McuCommand over micro-ROS)
- Commands: `D h s`, `ARM`, `DISARM`/`STOP`, `PING [seq]`, `TIME ms`, `TEL hz`, `RAW us|OFF`, `CAL LEFT|CENTER|RIGHT us`, `SET key val`, `GET`, `SAVE`, `DEFAULTS`, `SENS name`, `INFO`.
- Reply prefixes: `OK`, `ERR`, `CFG`, `PONG`, `INFO`, `SENS`. `mcu_bridge` matches on them.
- `SENS rangefinder` returns one read-only line: `present driver addr period_ms scale_m no_return min_m max_m fov_rad radiation raw range_m status age_ms seq`. If `present=0`, then `raw=0` and `range_m=nan`. Other names return `ERR`.
- Reply cap: 384 characters (`REPLY_CAP`). `CFG` has no `rf_*` keys. `SET rf_*` replies with `CFG`, so read the rf values back with `SENS rangefinder`.
- `rf_period_ms` is clamped to 20 ms or more: UART0 at 115200 baud carries about 11.5 KB/s, and a Range frame is about 80 B. `rf_min_m` and `rf_max_m` are clamped independently. A SET that leaves `rf_min_m >= rf_max_m` gives `ERR rf_min_m must be < rf_max_m`.
- Drive is the `DriveCmd` subscription on `/rccar/mcu/drive` (heading_rad becomes degrees inside, throttle in [-1, 1]). The ESP32 sends no acknowledgement. All other commands go through the service `/rccar/mcu/command`. The service runs `handleLine(char*, Print&)` (`StrPrint` captures the reply). `D` over the service gives `ERR`. `TIME` gives `ERR`. Manual check: `make mcu CMD="GET"` (stack up).

## Config persistence
- `Config` is one NVS blob (`Preferences`, namespace `rccar`, key `cfg`). The firmware ignores a blob with a different `CFG_MAGIC` and loads the defaults.
- `tuning.toml` layout for each device: `[<dev>]` hand-tuned knobs, `[<dev>.calibration]` measured values (written by `make calibrate`), `[warmup.<dev>]` routine settings.

## New sensor
- Use the rangefinder as the template (`.claude/rules/rangefinder.md`).
- Add its pins to `pins.h`. Fill its `tuning.toml` section only with values confirmed against `docs/datasheets/`.
- Read it in its own task. Read it in `controlTask()` only when safety needs it.
- Emergency braking lives in the firmware, so that it works without the host.
