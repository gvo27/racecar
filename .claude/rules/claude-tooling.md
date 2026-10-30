---
paths:
  - ".claude/**"
  - ".mcp.json"
  - "pyrightconfig.json"
  - "**/.clangd"
  - "tools/tests/**"
  - ".github/workflows/**"
---

# Claude tooling (plugins, MCP, LSP, tests)

## Inventory
- .claude/settings.json: marketplaces + enabledPlugins + enabledMcpjsonServers. .mcp.json: project MCP servers.
- superpowers@claude-plugins-official: workflow skills (brainstorming, writing-plans, executing-plans, test-driven-development, systematic-debugging, requesting-code-review, verification-before-completion). Official marketplace pins upstream obra/superpowers by sha.
- context7 (.mcp.json, http https://mcp.context7.com/mcp, no key; optional CONTEXT7_API_KEY in user scope for rate limits): tools resolve-library-id -> get-library-docs.
- location: .mcp.json + pyrightconfig.json must stay at repo root (claude code reads project mcp only from root .mcp.json; pyright discovers config only at workspace root); never move into .claude/
- pyright-lsp@claude-plugins-official: needs `pyright-langserver` on PATH. Config: pyrightconfig.json (include tools/, venv .venv, py3.12, basic).
- clangd-lsp@claude-plugins-official: needs `clangd` on PATH + firmware/esp32/compile_commands.json (`make compiledb`). firmware/esp32/.clangd strips xtensa-only gcc flags. Known gap: no --query-driver, so xtensa libstdc++ system headers may show false errors; trust `make build` over clangd for std headers.
- embedded-skills@embedded-skills, ros2-engineering@ros2-engineering-skills, kicad-happy@kicad-happy: domain skills (see dependencies.md).
- kicad-happy: skills kicad, spice, emc, datasheets, bom + distributor/fab skills. Python stdlib scripts; SPICE needs `ngspice` on PATH (optional host dev tool, like the LSP binaries). Distributor skills need API keys in user scope; never commit keys.
- `make check-dev` reports missing LSP binaries.

## Workflow (applies repo-wide; summarized in CLAUDE.md)
- Library/framework API => Context7 docs first. Match stack pins: arduino-esp32 2.0.17 (core 2.x, NOT 3.x), ESP-IDF 4.4.7, PlatformIO espressif32 6.9.0, ROS 2 Jazzy, micro-ROS jazzy. Docs for a different major version => say so, don't guess.
- Non-trivial change (new feature, multi-file, protocol/tuning/safety touch) => superpowers: brainstorming -> writing-plans -> test-driven-development -> requesting-code-review -> verification-before-completion. Plans: docs/plans/YYYY-MM-DD-<topic>.md. Trivial fixes skip brainstorming/plans.
- Bug => systematic-debugging before any fix.
- TDD scope: host python => pytest in tools/tests (`make unit`, CI python.yml). Firmware => compile check `make build` (CI firmware.yml); behavior needs bench (`make test`) = hardware, user runs it; never claim hardware verification without user-provided output. Phase 2 ROS packages => colcon test.
- Domain skills: firmware/esp32/** => embedded-skills (respect .claude/rules/firmware.md invariants over skill defaults: gnu++11, LEDC via driver/ledc.h, critical-section rules). ros2/micro-ROS/rccar_* => ros2-engineering. docs/schematics/** => kicad-happy (kicad + spice skills; rules in .claude/rules/schematics.md).
- After editing .py/.cpp/.h: read LSP diagnostics, fix new ones; pre-existing pyright errors in tools/rccar.py (parse_kv float|str union) are known, don't widen scope.
- Plugin bumps: change ref/sha deliberately, note in PR; never enable a plugin with hooks without reading its hooks.
