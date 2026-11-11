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
- .claude/settings.json: marketplaces + enabledPlugins. No project MCP servers (context7 removed: free tier too restrictive).
- superpowers@claude-plugins-official: workflow skills (brainstorming, writing-plans, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, verification-before-completion). Official marketplace pins upstream obra/superpowers by sha.
- location: pyrightconfig.json (and .mcp.json, if a project MCP server is ever re-added) must stay at repo root (claude code reads project mcp only from root .mcp.json; pyright discovers config only at workspace root); never move into .claude/
- pyright-lsp@claude-plugins-official: needs `pyright-langserver` on PATH. Config: pyrightconfig.json (include rccar_* + deploy, py3.12, basic; `reportMissingImports` = warning because rclpy/rccar_msgs only exist inside the ROS image).
- clangd-lsp@claude-plugins-official: needs `clangd` on PATH + firmware/esp32/compile_commands.json (`make compiledb`). firmware/esp32/.clangd strips xtensa-only gcc flags. Known gap: no --query-driver, so xtensa libstdc++ system headers may show false errors; trust `make build` over clangd for std headers.
- embedded-skills@embedded-skills, ros2-engineering@ros2-engineering-skills: domain skills (see dependencies.md).
- asd-ste100@asd-ste100-skill: ASD-STE100 Simplified Technical English rewrite skill + `scripts/ste-lint.py` (stdlib, advisory). Project convention: .claude/rules/writing.md.
- `make check-dev` reports missing LSP binaries.

## Workflow (applies repo-wide; summarized in CLAUDE.md)
- Library/framework API => upstream docs/source for the pinned version first (official docs or the tagged source on GitHub). Match stack pins: arduino-esp32 2.0.17 (core 2.x, NOT 3.x), ESP-IDF 4.4.7, PlatformIO espressif32 6.9.0, ROS 2 Jazzy, micro-ROS jazzy. Docs for a different major version => say so, don't guess.
- Non-trivial change (new feature, multi-file, protocol/tuning/safety touch) => superpowers: brainstorming -> writing-plans -> test-driven-development -> requesting-code-review -> verification-before-completion. Plans: docs/plans/YYYY-MM-DD-<topic>.md. Trivial fixes skip brainstorming/plans.
- Bug => systematic-debugging before any fix.
- TDD scope: no host python. deploy/ python => pytest in deploy/tests (`make unit`: ROS test image, CI ros.yml). ROS packages (incl. the FIRMWARE_KEYS drift test that reads main.cpp) => `make ros-test` (colcon test in docker, CI ros.yml). Firmware => compile check `make build` (CI firmware.yml); behavior needs bench (`make test`) = hardware, user runs it; never claim hardware verification without user-provided output. Agents never run hardware fault-injection (docs/setup.md bench checklist is user-run).
- Review: project subagent `.claude/agents/ros2-reviewer.md` (diff vs rules + ros2-engineering refs + stop-path checklist) before requesting-code-review.
- Domain skills: firmware/esp32/** => embedded-skills (respect .claude/rules/firmware.md invariants over skill defaults: gnu++11, LEDC via driver/ledc.h, critical-section rules). ros2/micro-ROS/rccar_* => ros2-engineering.
- Project text (docs, .claude/*, PR/commit/review text, user-facing strings) => asd-ste100 skill, mode and project rules in .claude/rules/writing.md.
- After editing .py/.cpp/.h: read LSP diagnostics, fix new ones; pyright runs on the host and does not see rclpy/rccar_msgs (warnings), so judge those by `make ros-test`.
- Every PR body uses `.github/pull_request_template.md` and carries the user-run bench checklist: deploy block (`make setup`, `make config`, `make car-down`, flash, `make car-up && make car-ps`, incl. dependency/rebuild steps) plus feature checks. Agents never tick hardware boxes.
- Each newly arriving sensor gets `.claude/rules/<sensor>.md` (software name, e.g. rangefinder) that explicitly links all its docs and datasheets, plus `docs/datasheets/<sensor>_<model>.md` (summary + tuning key map). Model names appear only in datasheet docs, README inventory/wiring.
- Plugin bumps: change ref/sha deliberately, note in PR; never enable a plugin with hooks without reading its hooks.
