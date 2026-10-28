project: autonomous_rc_car_platform
scope: infrastructure + comms layer (actuation, safety, host link, logging); ML models/sims live in separate repos deployed to the rpi5
chassis: tamiya_tt02_1:10
goals: [sensor_fusion, object_detection, semantic_slam, racing_trajectory_optimization]
compute: {high_level: raspberry_pi_5 (ros2, future), real_time: esp32-s3-n16r8}
phase: docker_foundation  # host -usb-> esp32 -pwm-> servo+esc; firmware toolchain in docker
next: phase 2 = ros2 (docker) + micro_ros_on_esp32 on rpi5
plan: docs/docker_ros_plan.md
stack:
  mcu: {build: platformio in docker (docker/firmware.Dockerfile, image rccar-fw, make build/flash/monitor), platform: espressif32@6.9.0, framework: arduino-esp32-2.0.17, lang: c++gnu11}
  host: {prereqs: [git, make, docker+compose+buildx], groups: [docker, dialout], lang: python>=3.12 (tools/ only, until phase 2), deps: requirements.txt, venv: .venv}
hw: {steer: ds3225mg@gpio4, throttle: thw1060_esc@gpio5, battery: 2s_lipo}
usb_ports: {left_USB: native, planned regulated power input; right_COM: ch343 uart0, flashing + host link}
layout: .claude/layout.yaml
cmd: make help
plugins: .claude/settings.json  # superpowers, pyright-lsp, clangd-lsp, embedded-skills, ros2-engineering; mcp: .mcp.json (context7)
rules: .claude/rules/{firmware,dependencies,deploy,models,repos,claude-tooling}.md  # path-scoped, see paths: frontmatter
invariants:
  - esp32 role: actuator pwm + host comms only; powers nothing
  - sensors on separate power rail, common ground, <=3.3v signals
  - pins: left header P1 only; pins.h == README table
  - protocol change => main.cpp + rccar.py + docs
  - tuning key change => tuning.toml + rccar.FIRMWARE_KEYS + main.cpp setKey
  - no unconfirmed parameters in tuning.toml
  - new deps => package.xml (rosdep) or a Dockerfile, never host; pin versions, no :latest
  - firmware paths: firmware/esp32/**
workflow:  # details: .claude/rules/claude-tooling.md
  - library/framework API => fetch current docs with context7 before writing code; match stack versions (arduino-esp32 2.x, esp-idf 4.4, ros2 jazzy)
  - non-trivial change => superpowers brainstorming -> writing-plans (docs/plans/) -> test-driven-development -> requesting-code-review
  - bug => superpowers systematic-debugging first
  - tests: host python => make unit; firmware => make build (compile) + bench make test (hardware, user-run; never claim without output)
  - after code edits => check lsp diagnostics (pyright, clangd; make compiledb for firmware)
