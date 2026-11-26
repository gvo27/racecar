# Dependencies: reference

Facts about the host prerequisites, the toolchain images and the Claude plugin sources. The rules are in [.claude/rules/dependencies.md](../.claude/rules/dependencies.md).

## Host prerequisites
- git, make, docker engine + compose plugin + buildx, uv. The user must be in groups `docker` and `dialout`.
- No system Python, no `pip install`, no `requirements.txt`. Host Python comes only through uv. `pyproject.toml` (dev group, exact `==` pins, `package = false`) + `uv.lock` + `.python-version` (3.13, the system interpreter) are committed. `make dev-setup` runs `uv sync --frozen` + `direnv allow` (both are safe to run again, and `make setup` runs it). It fills the gitignored `.venv`. `.envrc` puts `.venv/bin` on PATH. If direnv is missing or `direnv allow` fails, dev-setup prints a warning and continues. Dev tools today: ruff, pyright (gives `pyright-langserver`), pytest. Runtime, ROS tests, firmware and KiCad tools stay in docker. To add a dev tool, run `uv add --dev <tool>==<ver>` and commit `pyproject.toml` + `uv.lock`. In the Claude Code sandbox, `~/.cache/uv` is read-only: set `UV_CACHE_DIR=$PWD/.cache/uv` (gitignored).
- `make config` runs `deploy/render_env.py` in the ROS image (python 3.12, noble). `make unit` runs `deploy/tests` in the ROS test image (`rccar-ros-test:local`). `make setup` checks git/make/docker/uv (+ compose/buildx warnings), runs `make dev-setup` and builds both images.

## Stack pins
Read the docs or the tagged source of these versions before you write code against an API.
- Firmware: PlatformIO platform `espressif32@6.9.0` (`firmware/esp32/platformio.ini`, the owner). It gives arduino-esp32 2.0.17 (core 2.x, not 3.x) and ESP-IDF 4.4.7.
- micro-ROS: jazzy, through micro_ros_platformio pinned by commit (`firmware/esp32/platformio.ini`).
- ROS 2: Jazzy (`docker/ros.Dockerfile` base image, pinned by digest).

## Toolchain images
- `docker/firmware.Dockerfile` -> image `rccar-fw`: python:3.12-slim-bookworm, platformio==6.1.16, esptool==4.8.1, pyserial==3.5. The project packages (espressif32@6.9.0, board toolchain, framework, scons) are preinstalled with a project-context `pio pkg install` into `/opt/platformio` (`PLATFORMIO_CORE_DIR`, a+rwX for `--user <host uid>`). `docker/firmware.Dockerfile.dockerignore` filters the context.
- Named volume `rccar-platformio-v2` on `/opt/platformio` is seeded from the image on first use. A bind mount through `FW_VOL=<abs dir>` is NOT seeded: packages download on the first build. If the image toolchain changes, run `docker volume rm rccar-platformio-v2`. CI uses the named volume.
- `docker/ros.Dockerfile` -> image `rccar-ros:local` (`make ros-image`): `ros:jazzy-ros-base@sha256:<digest>`. Refresh the digest deliberately: `docker pull` + `docker inspect --format '{{index .RepoDigests 0}}'`. The builder stage does `vcs import` (only if ros2_ws/repos/rccar.repos is not empty) + `rosdep install --from-paths src --ignore-src -y --rosdistro jazzy` (apt lists cleaned) + `colcon build --merge-install`. The `test` stage = builder + `colcon test`. The `runtime` stage = ros-base + exec deps + /ws/install, user `ubuntu` (uid 1000). `docker/ros.Dockerfile.dockerignore` filters the context. The build-arg `ROSDEP_INSTALL=0` skips rosdep (offline sandbox only; then every dep must be in the base image).
- `docker/kicad.Dockerfile` -> image `rccar-kicad:local` (`make kicad-image`): `kicad/kicad:10.0.8@sha256:3f4a0178...ddc34` (kicad-cli, pcbnew Python, ghostscript). Used by `make erc` and `make pcb-*` for `pcb/`. The Makefile copies the stock lib tables from `/usr/share/kicad/template` into `build/kicad-cfg` (XDG_CONFIG_HOME). Without them, ERC gives about 111 false library warnings.
- Freerouting: `ghcr.io/freerouting/freerouting:2.5.0@sha256:6c195891...cf8e` (variable `FREEROUTING_IMAGE` in the Makefile). Used only by `make pcb-route`.
- `microros/micro-ros-agent:jazzy` is pinned by digest in deploy/car/compose.yaml. To bump it: pull, copy the digest, note it in the PR.
- package.xml: never use `<buildtool_depend>ament_python</buildtool_depend>` (it is not a rosdep key, and rosdep install fails). ament_python packages declare only `<export><build_type>ament_python</build_type>`.
- Keep the `rccar-fw` pins (platformio, esptool, pyserial) consistent with the `platformio.ini` platform pin.

## Claude plugin sources (.claude/settings.json)
- claude-plugins-official (anthropics/claude-plugins-official): superpowers, pyright-lsp, clangd-lsp, claude-md-management (commands + claude-md-improver skill, no hooks), code-simplifier (agent only, no hooks). The LSP binaries are optional host dev tools (not runtime deps). `pyright-langserver` comes from the uv dev group (`make dev-setup`). `clangd` comes from apt. See `make check-dev`.
- embedded-skills@embedded-skills: github rovinax/embedded-skills, ref master (no tags upstream). Topics: firmware arch, driver layering, rtos, isr.
- ros2-engineering@ros2-engineering-skills: github dbwls99706/ros2-engineering-skills, ref v1.7.2. Topics: micro-ros, ros2_control, nav2, perception.
- asd-ste100@asd-ste100-skill: github danyuchn/asd-ste100-skill, ref master (the default branch; upstream has no `main` branch and no tags; marketplace sources take ref only, no sha; reviewed at a4905d922500dd7530ca8a0eb9e4940494255709). Skill + lint script only, no hooks.
- ros2-engineering ships advisory hooks (PreToolUse edit/bash validator, Stop advisory, never blocks). To opt out, set ROS2_SKILL_DISABLE_HOOKS=all.
- caveman@caveman: github JuliusBrussee/caveman, ref v4.1.0 (tag 1e91f1306d602d4ca23618701b1185575ae1869b; Apache-2.0 + MIT). Skills: caveman (terse chat replies), caveman-commit, caveman-review, caveman-compress, cavecrew agents. Hooks: SessionStart, SubagentStart, UserPromptSubmit and SessionEnd. They run `node` and do nothing when node is not on PATH. They write mode and stats files under `~/.claude` only. They do not use the network (read 2026-11-11). The default mode is `caveman`. To change it, set `CAVEMAN_DEFAULT_MODE=off`.
- kicad-happy@kicad-happy: github aklofas/kicad-happy, ref v2.3.2 (commit 2fd9aa0). Reviewed: no hooks, no MCP, Python scripts use the stdlib only. The network is used only for the distributor APIs. Topics: KiCad schematic review, SPICE, EMC, datasheets, BOM. Optional host dev tools: ngspice (SPICE), kicad-cli (ERC/netlist).
