---
paths:
  - "firmware/esp32/**"
---

# Firmware rules (ESP32-S3)
Reference facts (build, tasks, pins, limits, command grammar): `docs/firmware/README.md`. Procedures (tuning key, Config layout, pins, build configuration, new sensor) and checks: `firmware/.claude/skills/firmware-change/SKILL.md`. Tasks, shared state, watchdog and ISRs: `firmware/.claude/skills/firmware-rtos/SKILL.md`.

## Build
- Build, flash and monitor only with `make build`, `make flash` and `make monitor`. No host `pio`.
- Keep one env (`esp32s3`) and one comms layer (micro-ROS). No comms macros, no `#ifdef` variants.
- Compiler is `-std=gnu++11`. Do not use `std::clamp`, C++14 aggregate init with default member initializers, or `if constexpr`.

## Architecture
- `controlTask()` is the only writer of PWM outputs. Keep it on the task watchdog.
- `loop()` is for comms only. Never block it. Never write PWM from it.
- After `setup()`, nothing prints to `Serial`. UART0 carries the XRCE stream. Keep `esp_log_level_set("*", ESP_LOG_NONE)` in `setup()`.
- Read and write shared state only inside `portENTER_CRITICAL(&g_mux)`. Copy the data out, then work on the copy. No Serial calls inside a critical section.
- Use the ESP-IDF LEDC driver (`driver/ledc.h`), not the Arduino `ledc*` API.
- `setup()` sets both PWM outputs to 50 Hz / 1500 us before anything else. The ESC learns neutral at power-on.
- A sensor task never blocks `controlTask` or `loop()`, never touches `Serial` or PWM, and tolerates a missing sensor. Device protocol stays in its driver file (`src/<sensor>_*.cpp`).
- A new optional publisher is created last and is non-fatal.

## Safety (do not weaken without an explicit request)
- Throttle requires `ARM`. The boot state is disarmed.
- No drive command for `timeoutMs`: disarm, neutral, `FAILSAFE` event. Keep emergency braking in the firmware.
- Keep the steering and ESC clamps (limits in `docs/firmware/README.md`). Use an ESC frame rate above 50 Hz only after you confirm that the ESC accepts it.
- `SAVE` refuses while armed (an NVS write stalls `controlTask`) and unless center lies between left and right.

## Pins
- `firmware/esp32/include/pins.h` is the source. Keep the pinout of the root `README.md` identical (the diagram: `test_pinout.py`; the table: by hand).
- Use left header P1 only. Never use the strapping, PSRAM, native USB or COM UART pins (list in `docs/firmware/README.md`). COM (UART0) is the only host link.

## Protocol and config
- A new or renamed command, a message or a boundary change follows `.claude/skills/interface-change/SKILL.md`. A `SET` key change follows `firmware-change` ("Tuning key").
- Keep every reply within `REPLY_CAP`. `test_tuning.py` checks the worst case.
- `D` (drive) goes only through the `/rccar/mcu/drive` subscription, never through the service.
- A change to the `Config` layout must bump `CFG_MAGIC`.
