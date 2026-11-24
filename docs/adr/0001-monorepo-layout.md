# 0001: Monorepo layout

- Status: Accepted
- Date: 2026-11-24
- Plan: `docs/plans/2026-11-24-monorepo-layout.md`

## Context
- The 8 ROS packages (`rccar_*`) were at the repo root, next to `pcb/`, `firmware/`, `docs/`, `deploy/` and `docker/`. Every folder that was not a ROS package needed a `COLCON_IGNORE` file, and the root README had to explain the mix.
- The project will grow: the sim (now in the repo `gvo27/racecar-sim`) will move into this repo, and a mechanical subproject (3D-printed mounts for the Pi, the power board and the sensors) will start.
- The car stack mounts the repo root in the containers at `/ws/src/racecar`. `RCCAR_TUNING`, the `logs/` mount, `deploy/render_env.py` and `rccar.service` use paths below that mount.

## Decision
Each subproject has one root folder: `ros2_ws/` (ROS 2 workspace: `src/` and `repos/`), `firmware/`, `pcb/`, `models/`, `simulation/` and `mechanical/`. Each subproject folder has a `README.md`. A subproject folder can also have a `CLAUDE.md` with its verify commands.

The shared infrastructure stays at the root: `deploy/`, `docker/`, `scripts/`, `Makefile`, `tuning.toml` and `logs/`. The container layout does not change. Compose still mounts the repo root at `/ws/src/racecar`, and colcon finds the packages in `/ws/src/racecar/ros2_ws/src/` because it searches recursively.

The recommended clone path on the Pi changes from `~/ros2_ws/src/racecar` to `~/racecar`, because the repo now contains its own `ros2_ws/`.

## Consequences
- The make targets, the container paths and the runtime behavior do not change.
- A skill for one subproject goes in `<subproject>/.claude/skills/` (now `pcb/` and `ros2_ws/`). Claude Code loads it only after it reads a file in that folder, so other sessions do not carry its description. A rule with `paths:` points to the `SKILL.md` from folders outside the subproject (for example `docs/pcb/`).
- Path globs in `.claude/rules/*.md`, the hook `.claude/hooks/hw_guard.py`, the CI path filters and `docker/ros.Dockerfile` name `ros2_ws/src/`. Tests check them: `deploy/tests/test_rules_paths.py`, `test_hw_guard.py`, `test_layout.py`, `test_claude_agents.py`.
- The existing Pi clone must move once to `~/racecar`. Then `make install-host` writes the new `WorkingDirectory` into `rccar.service` (procedure: `docs/setup.md`).
- The `COLCON_IGNORE` files stay. The compose mount and a sim workspace that imports this repo still see the whole tree, and `firmware/` holds a copy of `rccar_msgs`.
- racecar-sim pins an old commit of this repo. When it moves the pin, its colcon build finds the packages in `ros2_ws/src/`. But racecar-sim names the old paths in other files: `tests/test_pin.py` (`docs/sensor_contract.md`, `rccar_*/` package paths), `.claude/` files and docs (`docs/sensor_contract.md`, `.claude/skills/sim-parity/SKILL.md`). The pin move must change these paths to `docs/interfaces/sensor_contract.md`, `ros2_ws/src/rccar_*/` and `ros2_ws/.claude/skills/sim-parity/SKILL.md`.
