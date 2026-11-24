# Claude Code tooling: reference

Facts about the Claude Code setup of this repo. The rules for work with it are in [.claude/rules/claude-tooling.md](../.claude/rules/claude-tooling.md). Plugin sources and pins: [.claude/rules/dependencies.md](../.claude/rules/dependencies.md) and `docs/dependencies.md`.

## Plugins
`enabledPlugins` in `.claude/settings.json` is the only owner of the default set. A plugin with the value `false` loads no skills, hooks or agents. The folder-to-plugin map for on-demand plugins is `.claude/rules/plugins.md`.

| Plugin | Gives | Needs |
| --- | --- | --- |
| superpowers (claude-plugins-official) | workflow skills: brainstorming, writing-plans, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, verification-before-completion | the official marketplace pins obra/superpowers by sha |
| pyright-lsp | Python LSP | `pyright-langserver` on PATH (uv dev group). Config `pyrightconfig.json`: `ros2_ws/src` and `deploy`, py3.12, basic. `reportMissingImports` = warning (rclpy and rccar_msgs exist only in the ROS image) |
| clangd-lsp | C++ LSP | `clangd` on PATH (apt) and `firmware/esp32/compile_commands.json` (`make compiledb`). `firmware/esp32/.clangd` removes xtensa-only flags. No `--query-driver`, so xtensa libstdc++ headers can show false errors |
| embedded-skills, ros2-engineering, kicad-happy | domain skills | kicad-happy: stdlib scripts; SPICE needs `ngspice`; distributor skills need API keys in user scope |
| asd-ste100 | STE rewrite skill and `scripts/ste-lint.py` (stdlib, advisory) | |
| code-simplifier | the `code-simplifier` agent | its prompt lists JS/React standards that do not apply here |
| claude-md-management | CLAUDE.md commands and the claude-md-improver skill | off by default |
| caveman | terse chat replies | hooks need node. Without node, start the mode with `/caveman` |

There are no project MCP servers (context7 was removed: the free tier was too restrictive). `pyrightconfig.json` and a future `.mcp.json` stay at the repo root: Claude Code reads project MCP only from the root, and pyright finds its config only at the workspace root.

## Session and dev tools
- `make open` at the start of a session: git fast-forward, `uv sync --frozen`, `direnv allow`, install of the enabled plugins that are missing. `make close` before exit: removes the session-only plugin enables (`make plugins-reset`, `scripts/plugins_reset.py`), cache cleanup, a report of work that is not committed or not pushed. Scripts: `scripts/open.py`, `scripts/close.py` (template: user skill setup-shop).
- `make setup` is different: it prepares a car host and builds the images.
- `make open` needs `direnv` and `docker` on the host (`make check-host`). Install a missing host tool with the package manager, for example `sudo apt install direnv`.
- To enable a plugin for one session: `claude plugin enable <plugin> --scope local`, then `/reload-plugins`. `make open` installs the enabled plugins that are missing. To install one by hand, accept the trust prompt or run:
  ```bash
  claude plugin marketplace add JuliusBrussee/caveman@v4.1.0
  claude plugin install <plugin>@<marketplace> --scope project
  ```
- `make context` runs the check script of the user skill `project-context` (dead pointers, orphan docs, size budgets). It prints WARN and exits 0 when the skill is not installed.
- `make check-dev` reports missing dev tools (uv, direnv, LSP binaries). `make dev-setup` installs ruff, pyright and pytest into `.venv` from `uv.lock`.

## Hook
- `.claude/hooks/hw_guard.py` is a PreToolUse hook for Bash and Edit|Write|MultiEdit|NotebookEdit. `settings.json` registers the launcher `sh .claude/hooks/hw_guard.sh`.
- The launcher runs `hw_guard.py` (stdlib only) with `.venv/bin/python`, never the system python3. If `.venv` is missing, it answers "ask" with the reason `make dev-setup` (fail closed).
- Output: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask|deny", "permissionDecisionReason": ...}}`, exit 0.
- Tests: `deploy/tests/test_hw_guard.py` (`make unit`). The rules it enforces: `.claude/rules/hw-testing.md`. The `permissions.ask` list in `settings.json` repeats the restart targets as a second layer.

## Test scopes
- deploy/ Python: pytest in `deploy/tests` (`make unit`, ROS test image, CI `ros.yml`).
- ROS packages, with the `FIRMWARE_KEYS` drift test that reads `main.cpp`: `make ros-test` (colcon test in docker, CI `ros.yml`).
- Firmware: compile check `make build` (CI `firmware.yml`). Behavior needs the bench (`make test`), which the user runs.
- Hardware evidence comes from the user, or from a `make lidar-hw-test` report made on the Pi (`ros2_ws/src/rccar_drivers/rccar_drivers/hw_criteria.py`, `logs/hw_test_lidar_*.json`).
