---
paths:
  - "firmware/esp32/**"
---

# Firmware rules (ESP32-S3)

Reference facts (build, tasks, pins, limits, command grammar): `docs/firmware/README.md`.

## Build
- Build, flash and monitor only with `make build`, `make flash` and `make monitor`. No host `pio`.
- Keep one env (`esp32s3`) and one comms layer (micro-ROS). No comms macros, no `#ifdef` variants.
- Compiler is `-std=gnu++11`. Do not use `std::clamp`, C++14 aggregate init with default member initializers, or `if constexpr`.
- After a change to `rccar.meta` or `extra_packages`, run `make clean && make build`.
- Never use the native USB port (GPIO19/20) for comms. COM (UART0) is the only host link.

## Architecture
- `controlTask()` is the only writer of PWM outputs.
- `loop()` is for comms only. Never block it. Never write PWM from it.
- After `setup()`, nothing prints to `Serial`. UART0 carries the XRCE stream. Keep `esp_log_level_set("*", ESP_LOG_NONE)` in `setup()`.
- Read and write shared state only inside `portENTER_CRITICAL(&g_mux)`. Copy the data out, then work on the copy. No Serial calls inside a critical section.
- Use the ESP-IDF LEDC driver (`driver/ledc.h`), not the Arduino `ledc*` API.
- `setup()` sets both PWM outputs to 50 Hz / 1500 us before anything else. The ESC learns neutral at power-on.
- A sensor task never blocks `controlTask` or `loop()`, never touches `Serial` or PWM, and tolerates a missing sensor. Device protocol stays in its driver file (`src/<sensor>_*.cpp`).
- Keep the control task on the task watchdog.
- A new optional publisher is created last and is non-fatal.

## Safety (do not weaken without an explicit request)
- Throttle requires `ARM`. The boot state is disarmed.
- No drive command for `timeoutMs`: disarm, neutral, `FAILSAFE` event.
- Keep the steering and ESC clamps (limits in `docs/firmware/README.md`). Use an ESC frame rate above 50 Hz only after you confirm that the ESC accepts it.
- `SAVE` refuses unless center lies between left and right.
- Emergency braking lives in the firmware, so that it works without the host.

## Pins
- `firmware/esp32/include/pins.h` is the source. Keep the README table identical.
- Use left header P1 only. Never use the strapping, PSRAM, native USB or COM UART pins (list in `docs/firmware/README.md`).
- The ESP32 supplies no power to peripherals.

## Protocol and config
- A new or renamed command, `SET` key or interface changes all of these together: `rccar_msgs`, `firmware/esp32/extra_packages` (diff -r clean), `rccar_mcu_bridge` (`FIRMWARE_KEYS`, commands), `tuning.toml` and `docs/`. `test_tuning.py` checks `FIRMWARE_KEYS` against `tuning.toml` and `main.cpp`.
- Keep every reply within `REPLY_CAP` (384). `test_tuning.py` checks the worst case.
- `D` (drive) goes only through the `/rccar/mcu/drive` subscription, never through the service.
- A change to the `Config` layout must bump `CFG_MAGIC`.
- Never add unconfirmed parameters to `tuning.toml`.

## New sensor
- Use the rangefinder as the template (`.claude/rules/rangefinder.md`). Each sensor gets its own `.claude/rules/<sensor>.md`.
- Add its pins to `pins.h`. Fill its `tuning.toml` section only with values confirmed against `docs/datasheets/`.
- Read it in its own task. Read it in `controlTask()` only when safety needs it.
