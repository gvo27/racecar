---
name: sim-parity
description: Use when a change touches the hardware boundary of the car - firmware/esp32 controlTask, handleLine or setKey, rccar_msgs, a topic, type, frame or QoS in rccar_drivers or main.cpp, rccar_description URDF, or a tuning.toml key. Lists the docs/sensor_contract.md rows and the racecar-sim artifacts to update, and adds the "Sim impact" PR section. Do not use for changes above the supervisor.
---

# Sim parity checklist

The sim repo (racecar-sim) replaces the ESP32 and the Mapper with virtual devices. The real car nodes run unchanged in sim. If the boundary changes and the sim does not follow, the sim gives wrong results and no test fails in the sim repo. This checklist prevents that.

## Steps
1. Run `git diff --name-only <base>...HEAD`. Find each changed path in the table below.
2. For each match, do the action in the table. Do not skip a row.
3. Update `docs/sensor_contract.md`. Keep one row for each topic. Copy the type, frame, QoS and rate from the code. Do not write a value from memory.
4. Run `make unit`. `deploy/tests/test_contract.py` must pass.
5. Fill in the "Sim impact" section of the PR body (`.github/pull_request_template.md`). List each racecar-sim artifact to change. Write "racecar-sim `.repos` pin bump: needed".
6. Do not edit the racecar-sim repo from this repo. Give the list to the user.

## Table
| Changed path | Contract action | racecar-sim artifact |
|---|---|---|
| `firmware/esp32/src/main.cpp` controlTask, slew, clamps, failsafe | none | `rccar_sim_mcu` model + golden vectors |
| `main.cpp` handleLine, setKey; a `tuning.toml` key | none (`test_tuning.py` checks FIRMWARE_KEYS) | `rccar_sim_mcu` grammar and key limits |
| `main.cpp` comms header (pub/sub/srv lines) | update the ESP32 rows | `rccar_sim_mcu` node entities |
| `rccar_msgs/**` | update the type column | `rccar_sim_mcu` node; bridge config |
| `rccar_drivers/**` topic, type, frame, QoS, PARAMS defaults | update the mapper_driver rows | `rccar_sim_mapper`; gz bridge config |
| `rccar_drivers/rccar_drivers/slamtec/protocol.py` | update "Device facts" | `rccar_sim_mapper` protocol server |
| `rccar_description/urdf/**` | update the TF table | sim wrapper xacro; gz sensor xacros |
| `rccar_supervisor/**` arbitration, Reset, inputs | update the `/rccar/cmd/*` rows | sim-safety-check in racecar-sim |
| `rccar_bringup/launch/car.launch.py`, `drivers.launch.py` arguments | none | `rccar_sim_bringup` launch files |

## Rules
- `docs/sensor_contract.md` is the source of truth for the boundary. The `ros2.md` topic table must agree with it.
- Never add an unconfirmed value to `tuning.toml` for the sim. Sim-only values stay in racecar-sim.
- Do not rename a `/rccar/...` topic without user approval.
- Only the supervisor publishes `/rccar/mcu/drive`.

## Verify
- `make unit` output shows that `test_contract.py` passed.
- The PR body has the "Sim impact" section.
- Report as "not verified": the racecar-sim build and the pin bump. They happen in racecar-sim.
