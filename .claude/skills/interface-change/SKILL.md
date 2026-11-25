---
name: interface-change
description: Use when a change touches the hardware boundary of the car - a rccar_msgs message or service, the firmware comms header, handleLine, setKey or controlTask, a topic, type, frame or QoS of a driver, the URDF, or a tuning.toml key. Keeps the message copy, the contract and the sim in step. Not for changes above the supervisor.
---

# Interface change (messages, contract, sim)

The boundary has three parts that must agree: the code, `docs/interfaces/sensor_contract.md` (the contract) and the sim (racecar-sim). The sim replaces the ESP32 and the Mapper with virtual devices, and the car nodes run unchanged in sim. If the boundary changes and the sim does not follow, the sim gives wrong results and no sim test fails. Car-side sim findings: `docs/sim/README.md`.

## Steps
1. Run `git diff --name-only <base>...HEAD`. Find each changed path in the "Sources" table of the contract. For each match, do the contract action and note the sim artifact of that row. Do not skip a row.
2. A message or service change in `ros2_ws/src/rccar_msgs/`:
   1. Run `make msgs-sync`. It copies the package to `firmware/esp32/extra_packages/rccar_msgs/`. Never edit the copy.
   2. Change the users: `firmware/esp32/src/main.cpp`, `rccar_mcu_bridge` and its users (supervisor, teleop, calibration).
   3. If the count of entities changes, change the counts in `firmware/esp32/rccar.meta`.
   4. Build the firmware again from zero: `make clean && make build`.
3. A tuning key change: follow `firmware/.claude/skills/firmware-change/SKILL.md` ("Tuning key").
4. Change the contract rows. Keep one row for each topic. Copy the type, frame, QoS and rate from the code, not from memory.
5. Fill in the "Sim impact" section of the PR body: each racecar-sim artifact to change, and "racecar-sim `.repos` pin bump: needed".
6. A field order or type change breaks the firmware that is on the ESP32. Add to the bench checklist: flash the firmware together with the new Pi image.
7. Do not edit the racecar-sim repo from this repo. Give the artifact list to the user.

## Rules
- The contract is the source of truth for the boundary. `docs/interfaces/ros2.md` lists only the topics above the boundary. It does not repeat a boundary type or QoS.
- Do not rename a `/rccar/...` topic without user approval.
- Sim-only values stay in racecar-sim, not in `tuning.toml`.

## Verify
- `make msgs-sync`, then `git status --short firmware/esp32/extra_packages` shows the copy in the same commit as the message change.
- `make checks` (`test_contract.py`: contract rows and "Sources" paths), `make ros-test`, `make build`.
- Claim a result only with the command output from this session. A check that you did not run is "not run". The racecar-sim build and the pin bump are "not verified": they happen in racecar-sim.
