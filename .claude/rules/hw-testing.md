---
paths:
  - "ros2_ws/src/rccar_drivers/**"
  - "ros2_ws/src/rccar_description/**"
  - "deploy/**"
  - "Makefile"
  - ".claude/hooks/**"
---

# Hardware testing by an agent on the Pi

`.claude/hooks/hw_guard.py` enforces these rules (hook facts: `docs/claude-tooling.md`). Hardware test facts: `docs/lidar/driver.md`. Run `make dev-setup` on the Pi before you start Claude Code. Do not run the Pi agent with `--dangerously-skip-permissions`.

1. Run `make drivers-stop` before you edit or rebuild driver code (`ros2_ws/src/rccar_drivers/`, `ros2_ws/src/rccar_description/`, `docker/ros.Dockerfile`, `make ros-image` or `make setup`). While `drivers` runs, the hook denies edits and builds.
2. Never start or restart hardware, or a container that touches hardware, without explicit human approval in the current conversation. This applies in auto mode also. The commands: `make drivers-start|car-up|flash|install-host|car-shutdown`, `docker compose up|start|restart`, `docker start|restart`, `systemctl start|restart|enable ...rccar`, `reboot|poweroff|shutdown`. Stop commands (`drivers-stop`, `car-down`, `compose stop`) are free.
3. Sensor acceptance is `make lidar-hw-test`. Paste the PASS/FAIL/NA table as evidence. A threshold change needs the reason and user approval.
4. Hardware tests are read-only. The driver sends getters only. Do not add device reboot or configuration commands. The car is stationary with ESC power off.
5. The agent may run `make lidar-snapshot` and `make lidar-record SECS=<=60` at any time without approval (read-only subscribers). Do not commit or upload anything from `logs/`.
6. Fault injection (unplug power or USB, kill core, motor runs) is user-run only.
