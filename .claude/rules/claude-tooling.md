---
paths:
  - ".claude/**"
  - ".mcp.json"
  - "pyrightconfig.json"
  - "**/.clangd"
  - "deploy/tests/**"
  - ".github/workflows/**"
  - ".github/pull_request_template.md"
---

# Claude tooling (plugins, MCP, LSP, tests)

## Inventory
- .claude/settings.json holds marketplaces + enabledPlugins. There are no project MCP servers (context7 removed: free tier too restrictive).
- superpowers@claude-plugins-official gives workflow skills (brainstorming, writing-plans, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, verification-before-completion). The official marketplace pins upstream obra/superpowers by sha.
- location: pyrightconfig.json (and .mcp.json, if a project MCP server is ever added again) must stay at the repo root. Claude Code reads project MCP only from the root .mcp.json. Pyright finds its config only at the workspace root. Never move them into .claude/.
- pyright-lsp@claude-plugins-official needs `pyright-langserver` on PATH. Config: pyrightconfig.json (include rccar_* + deploy, py3.12, basic). `reportMissingImports` = warning, because rclpy/rccar_msgs exist only inside the ROS image.
- clangd-lsp@claude-plugins-official needs `clangd` on PATH + firmware/esp32/compile_commands.json (`make compiledb`). firmware/esp32/.clangd removes xtensa-only gcc flags. Known gap: there is no --query-driver, so xtensa libstdc++ system headers may show false errors. For std headers, trust `make build` more than clangd.
- embedded-skills@embedded-skills, ros2-engineering@ros2-engineering-skills: domain skills (see dependencies.md).
- asd-ste100@asd-ste100-skill: ASD-STE100 Simplified Technical English rewrite skill + `scripts/ste-lint.py` (stdlib, advisory). Project convention: .claude/rules/writing.md.
- `make check-dev` reports missing LSP binaries.

## Workflow (applies repo-wide, summarized in CLAUDE.md)
- Library/framework API => read the upstream docs/source for the pinned version first (official docs or the tagged source on GitHub). Match stack pins: arduino-esp32 2.0.17 (core 2.x, NOT 3.x), ESP-IDF 4.4.7, PlatformIO espressif32 6.9.0, ROS 2 Jazzy, micro-ROS jazzy. If the docs are for a different major version, say so. Do not guess.
- Non-trivial change (new feature, multi-file, protocol/tuning/safety touch) => superpowers: brainstorming -> writing-plans -> test-driven-development -> requesting-code-review -> verification-before-completion. Plans: docs/plans/YYYY-MM-DD-<topic>.md. Trivial fixes skip brainstorming/plans.
- Bug => systematic-debugging before any fix.
- TDD scope: no host python. deploy/ python => pytest in deploy/tests (`make unit`: ROS test image, CI ros.yml). ROS packages (incl. the FIRMWARE_KEYS drift test that reads main.cpp) => `make ros-test` (colcon test in docker, CI ros.yml). Firmware => compile check `make build` (CI firmware.yml). Firmware behavior needs the bench (`make test`). The bench is hardware, and the user runs it. Never claim hardware verification without output from the user. Agents never run hardware fault-injection (the docs/setup.md bench checklist is user-run).
- Review: use the project subagent `.claude/agents/ros2-reviewer.md` (diff vs rules + ros2-engineering refs + stop-path checklist) before requesting-code-review.
- Domain skills: firmware/esp32/** => embedded-skills (obey the .claude/rules/firmware.md invariants, not the skill defaults: gnu++11, LEDC via driver/ledc.h, critical-section rules). ros2/micro-ROS/rccar_* => ros2-engineering.
- Project text (docs, .claude/*, PR/commit/review text, user-facing strings) => asd-ste100 skill. Mode and project rules: .claude/rules/writing.md.
- After you edit .py/.cpp/.h: read the LSP diagnostics and fix the new ones. Pyright runs on the host and does not see rclpy/rccar_msgs (warnings), so judge those with `make ros-test`.
- Every PR body uses `.github/pull_request_template.md` and has the user-run bench checklist. The checklist has a deploy block (`make setup`, `make config`, `make car-down`, flash, `make car-up && make car-ps`, incl. dependency/rebuild steps) plus feature checks. Agents never tick hardware boxes.
- Each new sensor gets `.claude/rules/<sensor>.md` (software name, for example rangefinder). That file links all docs and datasheets of the sensor. Each new sensor also gets `docs/datasheets/<sensor>_<model>.md` (summary + tuning key map). Model names appear only in datasheet docs and in the README inventory/wiring.
- Plugin bumps: change the ref/sha deliberately and note it in the PR. Never enable a plugin with hooks before you read its hooks.
