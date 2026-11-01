---
paths:
  - "rccar_drivers/**"
  - "rccar_description/**"
  - "deploy/**"
  - "Makefile"
  - ".claude/hooks/**"
---

# Hardware testing by an agent on the Pi (lidar attached)

Enforced by `.claude/hooks/hw_guard.py` (PreToolUse, needs python3 on the dev host: Ubuntu ships it; the one host-side script). Hook "ask"/"deny" is evaluated before the permission mode takes effect in auto mode; whether "ask" prompts under `--dangerously-skip-permissions` is not documented: do not run the Pi agent with that flag.

## Rules
1. `make drivers-stop` BEFORE editing or rebuilding driver code (`rccar_drivers/`, `rccar_description/`, `docker/ros.Dockerfile`, `make ros-image`/`setup`). Hook denies Edit/Write and builds while the `drivers` container runs; `make ros-image` also refuses (`_need-drivers-down`).
2. Never start/restart hardware or containers touching hardware without explicit human approval in the current conversation, regardless of auto mode: `make drivers-start|car-up|flash|install-host|car-shutdown`, `docker compose up|start|restart`, `docker start|restart`, `systemctl start|restart|enable ...rccar`, `reboot|poweroff|shutdown`. Hook answers "ask" (a human approves). Stops (`drivers-stop`, `car-down`, `compose stop`) are free.
3. Sensor acceptance = `make lidar-hw-test`: launch_testing (`rccar_drivers/test_hw/test_mapper_hw.py`), criteria + thresholds in `rccar_drivers/hw_criteria.py` (pytest: `test/test_hw_criteria.py`), JSON report `logs/hw_test_lidar_<UTC>.json`. Paste the PASS/FAIL table as evidence. Changing a threshold needs a stated reason and user approval.
4. HW tests are read-only (the driver sends getters only; no device reboot/config commands may be added). Car stationary, ESC power OFF. The test runs its own driver, so `drivers` must be stopped (pre-check fails otherwise).
5. Fault injection (unplug power/USB, kill core, motor runs) stays user-run (docs/setup.md bench checklist).
6. Loop: `make drivers-stop` -> edit -> `make ros-test` (fake Mapper, CI-safe) -> `make ros-image` (allowed while stopped) -> `make lidar-hw-test` (no restart needed). Leaving `drivers` running again (`make drivers-start`) = hardware restart: ask the user.

## Layout
- `rccar_drivers/test_hw/` is NOT under `test/`; `conftest.py` ignores it unless `RCCAR_HW_TEST=1`, so `colcon test`/CI never collect it. Installed to `share/rccar_drivers/test_hw/` (setup.py) for the runtime image.
- `make lidar-hw-test` leaves `drivers` stopped and says so.
