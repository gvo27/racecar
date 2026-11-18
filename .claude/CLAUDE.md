project: autonomous_rc_car_platform
scope: infrastructure + comms layer (actuation, safety, host link, logging); ML models/sims live in separate repos deployed to the rpi5
chassis: tamiya_tt02_1:10
goals: [sensor_fusion, object_detection, semantic_slam, racing_trajectory_optimization]
compute: {high_level: raspberry_pi_5 (ros2 jazzy in docker, deploy/car), real_time: esp32-s3-n16r8 (micro-ros client)}
plan: docs/docker_ros_plan.md
status: docs/{rangefinder,lidar,sim}/README.md, docs/pcb/review/README.md  # each file owns its status; do not copy status here
sim: {repo: gvo27/racecar-sim (pins this repo), contract: docs/sensor_contract.md, findings: docs/sim/README.md}
lab: docs/techctcarvera/  # the lab directory; pcb/libraries/lab.py and the Makefile read this line. Another lab => change this line only
convention: .claude/ = general rules, skills, agents (no site values); docs/ = facts that change; this file = pointers, no values. Path-specific rules load by their paths: frontmatter
cmd: make help  # session: make open (start), make close (end); car host setup: make setup
invariants:
  - esp32 role: actuator pwm + host comms only; powers nothing
  - sensors on separate power rail, common ground, <=3.3v signals
  - supervisor = sole publisher of /rccar/mcu/drive
  - software stop is not safety-rated; esc power switch = hardware stop
  - no unconfirmed parameters in tuning.toml
  - agents never run hardware fault-injection tests or (re)start hardware without explicit human approval; bench checklists are user-run (.claude/rules/hw-testing.md)
workflow:  # details: .claude/rules/claude-tooling.md
  - library/framework API => check upstream docs/source at the pinned version before writing code; match stack versions (arduino-esp32 2.x, esp-idf 4.4, ros2 jazzy)
  - non-trivial change => superpowers brainstorming -> writing-plans (docs/plans/) -> test-driven-development -> requesting-code-review
  - bug => superpowers systematic-debugging first
  - tests: no system python (host dev tools via uv only); deploy/ python => make unit (ros test image); ros => make ros-test (colcon test in docker); firmware => make build (compile, CI) + bench make test (hardware, user-run; never claim without output)
  - every PR body = .github/pull_request_template.md with user-run bench checklist (deploy + deps + feature checks)
  - all project text (docs, .claude/*, PR/commit/review text, user-facing strings) => asd-ste100 STE: strict for .claude/procedures/errors, ste-flavored for prose; keep facts+hedges; .claude/rules/writing.md
  - after code edits => check lsp diagnostics (pyright, clangd; make compiledb for firmware)
