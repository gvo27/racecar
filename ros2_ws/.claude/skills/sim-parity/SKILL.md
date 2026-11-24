---
name: sim-parity
description: Use when a change touches the hardware boundary of the car - firmware/esp32 controlTask, handleLine or setKey, rccar_msgs, a topic, type, frame or QoS in rccar_drivers or main.cpp, rccar_description URDF, or a tuning.toml key. Lists the docs/interfaces/sensor_contract.md rows and the racecar-sim artifacts to update, and adds the "Sim impact" PR section. Do not use for changes above the supervisor.
---

# Sim parity checklist

The sim repo (racecar-sim) replaces the ESP32 and the Mapper with virtual devices. The real car nodes run unchanged in sim. Car-side findings and open items: `docs/sim/README.md`. If the boundary changes and the sim does not follow, the sim gives wrong results and no test fails in the sim repo. This checklist prevents that.

## Steps
1. Run `git diff --name-only <base>...HEAD`. Find each changed path in the "Sources" table of `docs/interfaces/sensor_contract.md`.
2. For each match, do the contract action and list the sim artifact of that row. Do not skip a row.
3. Update `docs/interfaces/sensor_contract.md`. Keep one row for each topic. Copy the type, frame, QoS and rate from the code. Do not write a value from memory.
4. Run `make unit`. `deploy/tests/test_contract.py` must pass.
5. Fill in the "Sim impact" section of the PR body (`.github/pull_request_template.md`). List each racecar-sim artifact to change. Write "racecar-sim `.repos` pin bump: needed".
6. Do not edit the racecar-sim repo from this repo. Give the list to the user.

## Rules
- `docs/interfaces/sensor_contract.md` is the source of truth for the boundary. `docs/interfaces/ros2.md` lists only the topics above the boundary and the subscribers. It does not repeat a boundary type or QoS.
- Never add an unconfirmed value to `tuning.toml` for the sim. Sim-only values stay in racecar-sim.
- Do not rename a `/rccar/...` topic without user approval.
- Only the supervisor publishes `/rccar/mcu/drive`.

## Verify
- `make unit` output shows that `test_contract.py` passed.
- The PR body has the "Sim impact" section.
- Report as "not verified": the racecar-sim build and the pin bump. They happen in racecar-sim.
