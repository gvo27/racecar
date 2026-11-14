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
- git, make, docker engine + compose plugin + buildx, uv. The user must be in groups `docker` and `dialout`.
- No system Python, no `pip install`, no `requirements.txt`. Host Python comes only through uv. `pyproject.toml` (dev group, exact `==` pins, `package = false`) + `uv.lock` + `.python-version` (3.13, the system interpreter) are committed. `make dev-setup` runs `uv sync --frozen` + `direnv allow` (both are safe to run again, and `make setup` runs it). It fills the gitignored `.venv`. `.envrc` puts `.venv/bin` on PATH. If direnv is missing or `direnv allow` fails, dev-setup prints a warning and continues. Dev tools today: ruff, pyright (gives `pyright-langserver`), pytest. Runtime, ROS tests, firmware and KiCad tools stay in docker. To add a dev tool, run `uv add --dev <tool>==<ver>` and commit `pyproject.toml` + `uv.lock`. In the Claude Code sandbox, `~/.cache/uv` is read-only: set `UV_CACHE_DIR=$PWD/.cache/uv` (gitignored).
- `make config` runs `deploy/render_env.py` in the ROS image (python 3.12, noble). `make unit` runs `deploy/tests` in the ROS test image (`rccar-ros-test:local`). `make setup` checks git/make/docker/uv (+ compose/buildx warnings), runs `make dev-setup` and builds both images.

## Toolchain images
- `docker/firmware.Dockerfile` -> image `rccar-fw`: python:3.12-slim-bookworm, platformio==6.1.16, esptool==4.8.1, pyserial==3.5. The project packages (espressif32@6.9.0, board toolchain, framework, scons) are preinstalled with a project-context `pio pkg install` into `/opt/platformio` (`PLATFORMIO_CORE_DIR`, a+rwX for `--user <host uid>`). `docker/firmware.Dockerfile.dockerignore` filters the context.
- Named volume `rccar-platformio-v2` on `/opt/platformio` is seeded from the image on first use. A bind mount through `FW_VOL=<abs dir>` is NOT seeded: packages download on the first build. If the image toolchain changes, run `docker volume rm rccar-platformio-v2`. CI uses the named volume.
- `docker/ros.Dockerfile` -> image `rccar-ros:local` (`make ros-image`): `ros:jazzy-ros-base@sha256:<digest>`. Refresh the digest deliberately: `docker pull` + `docker inspect --format '{{index .RepoDigests 0}}'`. The builder stage does `vcs import` (only if repos/rccar.repos is not empty) + `rosdep install --from-paths src --ignore-src -y --rosdistro jazzy` (apt lists cleaned) + `colcon build --merge-install`. The `test` stage = builder + `colcon test`. The `runtime` stage = ros-base + exec deps + /ws/install, user `ubuntu` (uid 1000). `docker/ros.Dockerfile.dockerignore` filters the context. The build-arg `ROSDEP_INSTALL=0` skips rosdep (offline sandbox only; then every dep must be in the base image).
- `microros/micro-ros-agent:jazzy` is pinned by digest in deploy/car/compose.yaml. To bump it: pull, copy the digest, note it in the PR.
- package.xml: never use `<buildtool_depend>ament_python</buildtool_depend>` (it is not a rosdep key, and rosdep install fails). ament_python packages declare only `<export><build_type>ament_python</build_type>`.
- Keep the `rccar-fw` pins (platformio, esptool, pyserial) consistent with the `platformio.ini` platform pin.

## Rules
- Put new runtime deps in `package.xml` (rosdep) or a Dockerfile. Never install on the host. Host dev tools go only in the uv dev group.
- Pin versions everywhere: exact pip pins, base images by tag (by digest for ros and micro-ros-agent), GitHub Actions by major tag (`@v4`...). Never use `:latest`.
- Third-party ROS sources without an apt binary go in `repos/rccar.repos` (see `.claude/rules/repos.md`).

## Claude plugins (.claude/settings.json, usage: .claude/rules/claude-tooling.md)
- claude-plugins-official (anthropics/claude-plugins-official): superpowers, pyright-lsp, clangd-lsp. The LSP binaries are optional host dev tools (not runtime deps). `pyright-langserver` comes from the uv dev group (`make dev-setup`). `clangd` comes from apt. See `make check-dev`.
- embedded-skills@embedded-skills: github rovinax/embedded-skills, ref master (no tags upstream). Topics: firmware arch, driver layering, rtos, isr.
- ros2-engineering@ros2-engineering-skills: github dbwls99706/ros2-engineering-skills, ref v1.7.2. Topics: micro-ros, ros2_control, nav2, perception.
- asd-ste100@asd-ste100-skill: github danyuchn/asd-ste100-skill, ref main (no tags upstream, marketplace sources take ref only, no sha, reviewed at a4905d922500dd7530ca8a0eb9e4940494255709). Skill + lint script only, no hooks.
- ros2-engineering ships advisory hooks (PreToolUse edit/bash validator, Stop advisory, never blocks). To opt out, set ROS2_SKILL_DISABLE_HOOKS=all.
- To bump a plugin, change the ref to a tag. Never track a moving branch when a tag exists.
