project: autonomous_rc_car_platform
scope: infrastructure + comms layer (actuation, safety, host link, logging); ML model weights stay outside git (models/); sim: gvo27/racecar-sim today, simulation/ later
chassis: tamiya_tt02_1:10
goals: [sensor_fusion, object_detection, semantic_slam, racing_trajectory_optimization]
compute: {high_level: raspberry_pi_5 (ros2 jazzy in docker, deploy/car), real_time: esp32-s3-n16r8 (micro-ros client)}
layout: README.md (subproject table); decisions: docs/adr/ (0001 = layout)
roadmap: docs/docker_ros_plan.md
status: docs/{rangefinder,lidar,sim}/README.md, docs/pcb/releases/rev1/review/README.md (rev1), docs/pcb/releases/rev3/review/README.md (mill board)  # each file owns its status; do not copy status here
sim: {repo: gvo27/racecar-sim (pins this repo), contract: docs/interfaces/sensor_contract.md, findings: docs/sim/README.md}
lab: docs/techctcarvera/  # the lab directory; pcb/libraries/lab.py and the Makefile read this line. Another lab => change this line only
convention: .claude/ = general rules, skills, agents (no site values); docs/ = facts that change; this file = pointers, no values. Path-specific rules load by their paths: frontmatter; ros2_ws/, firmware/, pcb/ CLAUDE.md = verify commands of the subtree
cmd: make help  # session: make open (start), make close (end); car host setup: make setup
invariants: docs/invariants.md  # loaded below; change one => ADR first
@../docs/invariants.md
workflow:  # always-on owner; extra items: .claude/rules/claude-tooling.md
  - library/framework API => check upstream docs/source at the pinned version before writing code; pins: docs/dependencies.md (stack pins)
  - non-trivial change => superpowers brainstorming -> writing-plans (docs/plans/) -> test-driven-development -> requesting-code-review
  - change to an invariant, the repo layout or an interface => ADR in docs/adr/ first (docs/adr/0000-template.md)
  - bug => superpowers systematic-debugging first
  - tests: no system python (host dev tools via uv only); .claude/, docs/, deploy/, scripts/ => make unit; subtree verify commands => the CLAUDE.md of ros2_ws/, firmware/, pcb/; hardware checks are user-run (never claim without output)
  - every PR body = .github/pull_request_template.md with user-run bench checklist (deploy + deps + feature checks)
  - all project text (docs, .claude/*, PR/commit/review text, user-facing strings) => asd-ste100 STE: strict for .claude/**, procedures and error strings; ste-flavored for prose; keep facts+hedges; .claude/rules/writing.md
  - after code edits => check lsp diagnostics (pyright, clangd; make compiledb for firmware)
