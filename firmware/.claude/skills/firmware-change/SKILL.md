---
name: firmware-change
description: Use when you change the ESP32 firmware in firmware/esp32 - a pin, a SET key or tuning key, the Config layout, rccar.meta, the toolchain image, or a new sensor. Gives the steps that keep the firmware, tuning.toml, the ROS bridge and the README pinout in step, and the checks to run.
---

# Firmware change (ESP32-S3)

The constraints are in `.claude/rules/firmware.md` (it loads for `firmware/esp32/**`). Facts (build, tasks, pins, limits, command grammar): `docs/firmware/README.md`. A change to a message or to the comms header also follows `.claude/skills/interface-change/SKILL.md`.

## Tuning key
A key that the firmware reads (`SET <key>`) lives in three places. Change them in one commit:
1. `tuning.toml`: only a confirmed value (datasheet or measurement).
2. `FIRMWARE_KEYS` in `ros2_ws/src/rccar_mcu_bridge/rccar_mcu_bridge/tuning.py`.
3. `setKey` in `firmware/esp32/src/main.cpp`.
`ros2_ws/src/rccar_mcu_bridge/test/test_tuning.py` checks that the three agree and that each reply stays within `REPLY_CAP`.

## Config layout
A change to the `Config` struct (fields, order, types) must change `CFG_MAGIC`. Otherwise the ESP32 loads an old NVS blob into the new layout.

## Pins
`firmware/esp32/include/pins.h` is the source. Change the diagram and the table of the root `README.md` ("Microcontroller pinout") in the same commit. `deploy/tests/test_pinout.py` checks the diagram. Check the table by hand.

## Build configuration
- After a change to `rccar.meta`, `extra_packages` or `platformio.ini`: `make clean && make build`. A plain `make build` can keep the old micro-ROS library (`docs/firmware/README.md`, "Build").
- After a change to the toolchain image (`docker/firmware.Dockerfile`): `make fw-image`, then remove the PlatformIO volume (`FW_VOL` in the Makefile) with `docker volume rm`, so the next build seeds it again.

## New sensor
Follow `docs/firmware/README.md` ("New sensor"). The sensor also gets `.claude/rules/<sensor>.md` (software name) and a datasheet note `docs/datasheets/<kind>_<model>.md` (form: skill `pcb-parts`).

## Verify
- `make build` (env `esp32s3`), or `make clean && make build` ("Build configuration").
- `make compiledb`, then the clangd diagnostics of the changed files.
- `make ros-test` for a key or a reply change (`test_tuning.py`). `make checks` for a pin or a comms header change (`test_pinout.py`, `test_contract.py`).
- User-run only: `make flash`, `make monitor`, the bench `make test` and the bench checklist of the PR. Add the flash step to the PR checklist.
- Claim a result only with the command output from this session. A check that you did not run is "not run".
