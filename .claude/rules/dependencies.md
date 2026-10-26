---
paths:
  - "Makefile"
  - "docker/**"
  - "deploy/**"
  - "repos/**"
  - "**/package.xml"
  - "firmware/esp32/platformio.ini"
  - "requirements.txt"
  - ".claude/settings.json"
---

# Dependencies

## Host prerequisites
- git, make, docker engine + compose plugin + buildx. User in groups `docker` and `dialout`.
- Python >=3.11 + `.venv` only for host tools (`tools/`) until phase 2 parity.

## Toolchain images
- `docker/firmware.Dockerfile` -> image `rccar-fw`: python:3.12-slim-bookworm, platformio==6.1.16, esptool==4.8.1, pyserial==3.5, project packages (espressif32@6.9.0, board toolchain, framework, scons) preinstalled via project-context `pio pkg install` into `/opt/platformio` (`PLATFORMIO_CORE_DIR`, a+rwX for `--user <host uid>`). Context filtered by `docker/firmware.Dockerfile.dockerignore`.
- Named volume `rccar-platformio` on `/opt/platformio` is seeded from the image on first use (a bind mount via `FW_VOL=<abs dir>` is NOT seeded; packages download on first build). Image toolchain change => `docker volume rm rccar-platformio`. CI uses the named volume.
- `docker/ros.Dockerfile` (planned, phase 2): ros:jazzy-ros-base digest-pinned; apt deps via rosdep from `package.xml`; `vcs import`.
- Keep image pins consistent with `requirements.txt` ranges and `platformio.ini` platform pin.

## Python host env (transitional)
- `.venv` + `requirements.txt` (repo root) retained until phase 2 bench parity, then removed together with `tools/`.
- `make setup` = check prereqs, create `.venv`, pip install, `make fw-image`.

## Rules
- New deps go in `package.xml` (rosdep) or a Dockerfile. Never install on the host.
- Pin versions everywhere: exact pip pins, base images by tag (by digest for ros), no `:latest`.
- Third-party ROS sources without apt binary: `repos/rccar.repos` (see `.claude/rules/repos.md`).

## Claude plugins (.claude/settings.json)
- embedded-skills@embedded-skills: github rovinax/embedded-skills, ref master (no tags upstream); firmware arch, driver layering, rtos, isr.
- ros2-engineering@ros2-engineering-skills: github dbwls99706/ros2-engineering-skills, ref v1.7.2; micro-ros, ros2_control, nav2, perception.
- ros2-engineering ships advisory hooks (PreToolUse edit/bash validator, Stop advisory; never blocks). opt out: ROS2_SKILL_DISABLE_HOOKS=all.
- bump plugin = change ref to a tag; never track a moving branch when a tag exists.
