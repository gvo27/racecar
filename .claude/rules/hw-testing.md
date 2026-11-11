---
paths:
  - "rccar_drivers/**"
  - "rccar_description/**"
  - "deploy/**"
  - "Makefile"
  - ".claude/hooks/**"
---

# Hardware testing by an agent on the Pi (lidar attached)

`.claude/hooks/hw_guard.py` enforces these rules. It is a PreToolUse hook and needs python3 on the dev host (Ubuntu includes it). It is the only host-side script. In auto mode, the hook "ask" or "deny" result is evaluated before the permission mode takes effect. The documentation does not say if "ask" prompts under `--dangerously-skip-permissions`. Do not run the Pi agent with that flag.

## Rules
1. Run `make drivers-stop` BEFORE you edit or rebuild driver code (`rccar_drivers/`, `rccar_description/`, `docker/ros.Dockerfile`, `make ros-image`/`setup`). While the `drivers` container runs, the hook denies Edit/Write and builds. `make ros-image` also refuses (`_need-drivers-down`).
2. Never start or restart hardware, or containers that touch hardware, without explicit human approval in the current conversation. This applies in auto mode also. The commands are: `make drivers-start|car-up|flash|install-host|car-shutdown`, `docker compose up|start|restart`, `docker start|restart`, `systemctl start|restart|enable ...rccar`, `reboot|poweroff|shutdown`. The hook answers "ask" (a human approves). Stop commands (`drivers-stop`, `car-down`, `compose stop`) are free.
3. Sensor acceptance is `make lidar-hw-test`. It is a launch_testing run (`rccar_drivers/test_hw/test_mapper_hw.py`). The criteria and thresholds are in `rccar_drivers/hw_criteria.py` (pytest: `test/test_hw_criteria.py`). The JSON report is `logs/hw_test_lidar_<UTC>.json`. Paste the PASS/FAIL/NA table as evidence. To change a threshold, state the reason and get user approval.
   Each criterion has the status PASS, FAIL or NA ("not provided"). A criterion is NA in these cases:
   - IMU gyro-at-rest: its bit is absent from the `imu_avail_bitmap` that the test read from /diagnostics.
   - acc-units: its bit is absent, or the driver marks acceleration as not provided (`imu_trust_acc` is false, the default).

   NA never fails. OVERALL is PASS if and only if no criterion is FAIL. The JSON report has `status` for each criterion.
4. HW tests are read-only. The driver sends getters only. Do not add device reboot or configuration commands. The car must be stationary with ESC power OFF. The test runs its own driver, so `drivers` must be stopped (the pre-check fails if it is not).
5. To debug with live data, the agent MAY run `make lidar-snapshot` and `make lidar-record SECS=<=60` on the Pi at any time. These commands are read-only subscribers. `drivers` stays up and no approval is needed. Read `summary.txt` and open `map.png` with the Read tool (image). Do not commit or upload anything from `logs/`.
6. Fault injection (unplug power/USB, kill core, motor runs) stays user-run (docs/setup.md bench checklist).
7. Use this loop: `make drivers-stop` -> edit -> `make ros-test` (fake Mapper, CI-safe) -> `make ros-image` (allowed while stopped) -> `make lidar-hw-test` (no restart needed). To leave `drivers` running again (`make drivers-start`) is a hardware restart: ask the user.

## Layout
- `rccar_drivers/test_hw/` is NOT under `test/`. `conftest.py` ignores it unless `RCCAR_HW_TEST=1`, so `colcon test` and CI never collect it. `setup.py` installs it to `share/rccar_drivers/test_hw/` for the runtime image.
- `make lidar-hw-test` leaves `drivers` stopped and says so.
