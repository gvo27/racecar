# Sim: car-side findings

The sim lives in the separate repo [racecar-sim](https://github.com/gvo27/racecar-sim). It replaces the ESP32 and the Mapper with virtual devices. The real car nodes run unchanged in sim. This file records the car-side findings from PR #9 (sim contract). It does not own the sim plan or the sim status.

| Topic | Owner |
| --- | --- |
| Sim plan and status | racecar-sim `docs/plans/2026-11-10-sim-scaffold.md` (PR gvo27/racecar-sim#1) |
| Hardware boundary: topics, types, frames, QoS, TF, device facts | [docs/interfaces/sensor_contract.md](../interfaces/sensor_contract.md) |
| What to update when the boundary changes | [.claude/skills/interface-change/SKILL.md](../../.claude/skills/interface-change/SKILL.md) |
| Sim/real parity design | [docs/docker_ros_plan.md](../docker_ros_plan.md) "Sim/real parity + ROS 2 conventions" |
| Car pin in the sim repo | racecar-sim `repos/racecar.repos` (procedure: racecar-sim `repos/README.md`) |
| Lidar facts that the sim must copy | [docs/lidar/README.md](../lidar/README.md), [docs/lidar/roadmap.md](../lidar/roadmap.md) "Simulation" |

## Status (2026-11-18)

- The PR #9 code is in `main` (through the stacked branches). No bench check of PR #9 is done.
- racecar-sim pins this repo at `3623d3b` (an old commit of the `sim-contract` branch). The pin must move to a `main` commit (open item below).
- racecar-sim PR #2 (virtual ESP32, `rccar_sim_mcu`) is open.

## Findings

1. **One contract file, tested against the code.** `docs/interfaces/sensor_contract.md` lists every topic at the hardware boundary. `deploy/tests/test_contract.py` (`make unit`) compares the "active" rows with `mapper_node.py`, the `main.cpp` comms header, the supervisor and the URDF. A row that does not agree with the code fails the test. "planned" rows are not tested.
2. **The sim must get the car tuning.** Before PR #9, `sim:=true` skipped `mcu_bridge`. The virtual ESP32 then ran with the firmware defaults, not with `tuning.toml`. Example: the firmware default `maxSteerDeg` is 25, but `max_steer_deg` in `tuning.toml` is 30. Now `mcu_bridge` runs in sim too and pushes `tuning.toml` to `/rccar/mcu/command` (`ros2_ws/src/rccar_bringup/launch/car.launch.py`). `sim:=false` does not change. Test: `ros2_ws/src/rccar_bringup/test/test_sim_launch.py`.
3. **One `robot_state_publisher` only.** `drivers.launch.py` has the argument `urdf_file:=` (default: `rccar.urdf.xacro`). The sim gives its wrapper xacro, so the sim does not start a second `robot_state_publisher`. Tests: `test_urdf_file_launch.py`, `test_urdf_default_launch.py`.
4. **A fake device hides real device behavior.** The lidar driver passed CI against a fake Mapper and failed on the real one (success code 1, camelCase health flags, see [docs/lidar/README.md](../lidar/README.md) finding 1). The sim Mapper must copy the device facts of the contract, not the old fake server.
5. **Rule globs can go stale.** `deploy/tests/test_rules_paths.py` checks that each `.claude/rules/*.md` file has `paths:` and that each glob matches a file. `ros2-reviewer` selects rules by `paths:`, not by a fixed list.
6. **CI can fail on runner DNS.** On `c483e39`, the apt step failed with `Could not resolve 'archive.ubuntu.com'`. A re-run of the failed jobs passed. Re-run once before you look for a code cause.
7. **The `asd-ste100` marketplace has no `main` branch.** The ref in `.claude/settings.json` is `master`.

## Open items

- Move the racecar-sim pin from `3623d3b` to the `main` merge commit (racecar-sim skill `sim-bump-pin`, or `make bump-racecar SHA=<sha>` there).
- At the pin move, racecar-sim must change the car paths that ADR 0001 lists. The car skill `sim-parity` is now `interface-change` (`.claude/skills/interface-change/SKILL.md`).
- Run the PR #9 bench checks: `make car-up` shows `mcu_bridge` active and the tuning push. In `make ros-shell`, `ros2 param get /robot_state_publisher robot_description` contains `lidar_link`. Then `make test` and `make teleop`.
- Car PR `dev-lsp` (planned in the handoff note, not opened): the `rccar-dev` image, LSP shims for pyright and clangd, `make lsp` / `check-dev` / `doctor`, the `.clangd` query-driver, updates to `dependencies.md` and `hw-testing.md`.
