---
paths:
  - "Makefile"
  - "docker/**"
  - "deploy/**"
  - "ros2_ws/repos/**"
  - "**/package.xml"
  - "firmware/esp32/platformio.ini"
  - ".claude/settings.json"
---

# Dependencies

Reference (host prerequisites, toolchain images, digests, plugin sources): `docs/dependencies.md`.

- Put new runtime deps in `package.xml` (rosdep) or a Dockerfile. Never install on the host.
- Host Python comes only through uv. No system Python, no `pip install`, no `requirements.txt`. A host dev tool goes in the uv dev group: `uv add --dev <tool>==<ver>`, then commit `pyproject.toml` and `uv.lock`.
- Runtime, ROS tests, firmware and KiCad tools stay in docker.
- Pin versions everywhere: exact pip pins, base images by tag (by digest for ros, micro-ros-agent, KiCad and Freerouting), GitHub Actions by major tag. Never use `:latest`.
- Change a digest on purpose: `docker pull`, `docker inspect --format '{{index .RepoDigests 0}}'`, and note it in the PR.
- Keep the `rccar-fw` pins (platformio, esptool, pyserial) consistent with the platform pin in `platformio.ini`.
- After a change to the firmware image toolchain, run `docker volume rm rccar-platformio-v2`.
- `package.xml`: never use `<buildtool_depend>ament_python</buildtool_depend>` (it is not a rosdep key). ament_python packages declare only `<export><build_type>ament_python</build_type>`.
- Third-party ROS sources without an apt binary go in `ros2_ws/repos/rccar.repos` (`.claude/rules/repos.md`).
- Claude plugins: bump the ref to a tag. Never track a moving branch when a tag exists. Read the hooks of a plugin before you enable it.
- In the Claude Code sandbox `~/.cache/uv` is read-only: set `UV_CACHE_DIR=$PWD/.cache/uv`.
