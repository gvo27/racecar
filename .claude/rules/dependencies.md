---
paths:
  - "Makefile"
  - "docker/**"
  - "deploy/**"
  - "repos/**"
  - "**/package.xml"
  - "firmware/esp32/platformio.ini"
  - ".claude/settings.json"
---

# Dependencies

## Host prerequisites
- git, make, docker engine + compose plugin + buildx. User in groups `docker` and `dialout`.
- No host Python, no `.venv`, no `requirements.txt`. `make config` runs `deploy/render_env.py` in the `rccar-fw` image (python 3.12); `make unit` runs `deploy/tests` in the ROS test image (`rccar-ros-test:local`); `make setup` checks git/make/docker (+ compose/buildx warnings) and builds both images.

## Toolchain images
- `docker/firmware.Dockerfile` -> image `rccar-fw`: python:3.12-slim-bookworm, platformio==6.1.16, esptool==4.8.1, pyserial==3.5, project packages (espressif32@6.9.0, board toolchain, framework, scons) preinstalled via project-context `pio pkg install` into `/opt/platformio` (`PLATFORMIO_CORE_DIR`, a+rwX for `--user <host uid>`). Context filtered by `docker/firmware.Dockerfile.dockerignore`.
- Named volume `rccar-platformio-v2` on `/opt/platformio` is seeded from the image on first use (a bind mount via `FW_VOL=<abs dir>` is NOT seeded; packages download on first build). Image toolchain change => `docker volume rm rccar-platformio-v2`. CI uses the named volume.
- `docker/ros.Dockerfile` -> image `rccar-ros:local` (`make ros-image`): `ros:jazzy-ros-base@sha256:<digest>` (refresh digest deliberately: `docker pull` + `docker inspect --format '{{index .RepoDigests 0}}'`); builder stage = `vcs import` (only if repos/rccar.repos non-empty) + `rosdep install --from-paths src --ignore-src -y --rosdistro jazzy` (apt lists cleaned) + `colcon build --merge-install`; `test` stage = builder + `colcon test`; `runtime` stage = ros-base + exec deps + /ws/install, user `ubuntu` (uid 1000). Context filtered by `docker/ros.Dockerfile.dockerignore`. `ROSDEP_INSTALL=0` build-arg skips rosdep (offline sandbox only; every dep must then be in the base image).
- `microros/micro-ros-agent:jazzy` pinned by digest in deploy/car/compose.yaml; bump = pull, copy digest, note in PR.
- package.xml: never `<buildtool_depend>ament_python</buildtool_depend>` (not a rosdep key; rosdep install fails). ament_python packages declare only `<export><build_type>ament_python</build_type>`.
- Keep the `rccar-fw` pins (platformio, esptool, pyserial) consistent with the `platformio.ini` platform pin.

## Rules
- New deps go in `package.xml` (rosdep) or a Dockerfile. Never install on the host.
- Pin versions everywhere: exact pip pins, base images by tag (by digest for ros and micro-ros-agent), GitHub Actions by major tag (`@v4`...), no `:latest`.
- Third-party ROS sources without apt binary: `repos/rccar.repos` (see `.claude/rules/repos.md`).

## Claude plugins (.claude/settings.json; usage: .claude/rules/claude-tooling.md)
- claude-plugins-official (anthropics/claude-plugins-official): superpowers, pyright-lsp, clangd-lsp. LSP binaries (pyright-langserver, clangd) = optional host dev tools, the one allowed host install (not runtime deps); `make check-dev`.
- context7 = .mcp.json http server, no install.
- embedded-skills@embedded-skills: github rovinax/embedded-skills, ref master (no tags upstream); firmware arch, driver layering, rtos, isr.
- ros2-engineering@ros2-engineering-skills: github dbwls99706/ros2-engineering-skills, ref v1.7.2; micro-ros, ros2_control, nav2, perception.
- ros2-engineering ships advisory hooks (PreToolUse edit/bash validator, Stop advisory; never blocks). opt out: ROS2_SKILL_DISABLE_HOOKS=all.
- bump plugin = change ref to a tag; never track a moving branch when a tag exists.
