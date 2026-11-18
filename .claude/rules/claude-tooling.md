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
- Library or framework API: read the upstream docs or the tagged source for the pinned version first. Match the stack pins: arduino-esp32 2.0.17 (core 2.x, not 3.x), ESP-IDF 4.4.7, PlatformIO espressif32 6.9.0, ROS 2 Jazzy, micro-ROS jazzy. If the docs are for a different major version, say so. Do not guess.
- Non-trivial change (new feature, many files, protocol, tuning or safety): superpowers brainstorming, writing-plans (`docs/plans/YYYY-MM-DD-<topic>.md`), test-driven-development, requesting-code-review, verification-before-completion. Trivial fixes skip the plan.
- Bug: systematic-debugging before any fix.
- No system python. Host dev tools come from uv. Tests that need ROS or the runtime run in docker (scopes in `docs/claude-tooling.md`).
- Never claim hardware verification without output from the user or a `make lidar-hw-test` report from the Pi. Agents never run hardware fault injection.
- Review of ROS, micro-ROS or deploy changes: the `ros2-reviewer` agent before requesting-code-review.
- Domain skills: `firmware/esp32/**` embedded-skills, `rccar_*` ros2-engineering, `pcb/**` kicad-happy (`.claude/rules/plugins.md`). The project rules win over the skill defaults (for example gnu++11, LEDC through `driver/ledc.h`, the critical-section rules).
- Project text follows `.claude/rules/writing.md`.
- After you edit `.py`, `.cpp` or `.h`: read the LSP diagnostics and fix the new ones. Judge pyright warnings about rclpy and rccar_msgs with `make ros-test`.
- Every PR body uses `.github/pull_request_template.md` with the user-run bench checklist. Agents never tick hardware boxes.
- A new sensor gets `.claude/rules/<sensor>.md` (software name) and `docs/datasheets/<sensor>_<model>.md`. Model names appear only in the datasheet docs and in the README inventory and wiring.

## Plugins and tools
- `enabledPlugins` in `.claude/settings.json` is the only owner of the default plugin set. Enable a plugin for one session with local scope (`.claude/rules/plugins.md`).
- Change a plugin ref or sha on purpose and note it in the PR. Never enable a plugin with hooks before you read its hooks.
- `code-simplifier`: apply the project rules (Python 3.12 and ruff, C++ gnu++11, `.claude/rules/firmware.md`), not its JS/React standards. Do not use it on the safety paths (stop path, failsafe, supervisor latch) without tests that cover the change. Run the tests after each change.
- `caveman` applies only to chat. Text that persists stays in STE. Do not use `caveman-commit` or `caveman-compress` on project text.
- Keep `pyrightconfig.json` (and any `.mcp.json`) at the repo root.
- The hook launcher runs only with `.venv/bin/python`. Never change it to the system python3.
