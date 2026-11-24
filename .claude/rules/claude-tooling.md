---
paths:
  - ".claude/**"
  - "pyrightconfig.json"
  - "**/.clangd"
  - "deploy/tests/**"
  - ".github/workflows/**"
  - ".github/pull_request_template.md"
---

# Claude tooling and repo workflow

Reference (plugins, LSP, session targets, hook, test scopes): `docs/claude-tooling.md`.

## Workflow
The always-on workflow is in `.claude/CLAUDE.md` (`workflow:`). This list adds only what that file does not have.
- If the docs of a library are for a different major version than the pin, say so. Do not guess.
- A non-trivial change is a new feature, a change to many files, the protocol, tuning or safety. Trivial fixes skip the plan. Plan file: `docs/plans/YYYY-MM-DD-<topic>.md`.
- Tests that need ROS or the runtime run in docker (scopes in `docs/claude-tooling.md`).
- Never claim hardware verification without output from the user or a `make lidar-hw-test` report from the Pi.
- Review of ROS, micro-ROS or deploy changes: the `ros2-reviewer` agent before `code-review`.
- Domain skills: `firmware/esp32/**` embedded-skills, `ros2_ws/src/**` ros2-engineering, `pcb/**` kicad-happy (`.claude/rules/plugins.md`). The project rules win over the skill defaults (for example gnu++11, LEDC through `driver/ledc.h`, the critical-section rules).
- Judge pyright warnings about rclpy and rccar_msgs with `make ros-test`.
- Agents never tick hardware boxes in a PR body.
- A new sensor gets `.claude/rules/<sensor>.md` (software name) and `docs/datasheets/<kind>_<model>.md` (form: skill `pcb-parts`). Model names appear only in the datasheet docs, in `docs/hardware.md` (inventory and wiring) and in the root README pinout.

## Plugins and tools
- `enabledPlugins` in `.claude/settings.json` is the only owner of the default plugin set. Enable a plugin for one session with local scope (`.claude/rules/plugins.md`).
- Change a plugin ref or sha on purpose and note it in the PR. Never enable a plugin with hooks before you read its hooks.
- `code-simplifier`: apply the project rules (Python 3.12 and ruff, C++ gnu++11, `.claude/rules/firmware.md`), not its JS/React standards. Do not use it on the safety paths (stop path, failsafe, supervisor latch) without tests that cover the change. Run the tests after each change.
- `caveman` applies only to chat. Text that persists stays in STE. Do not use `caveman-commit` or `caveman-compress` on project text.
- Keep `pyrightconfig.json` (and any `.mcp.json`) at the repo root.
- The hook launcher runs only with `.venv/bin/python`. Never change it to the system python3.
