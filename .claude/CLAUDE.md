project: autonomous_rc_car_platform
scope: infrastructure + comms layer (actuation, safety, host link, logging); ML models/sims live in separate repos deployed to the rpi5
chassis: tamiya_tt02_1:10
goals: [sensor_fusion, object_detection, semantic_slam, racing_trajectory_optimization]
compute: {high_level: raspberry_pi_5 (ros2 jazzy in docker, deploy/car), real_time: esp32-s3-n16r8 (micro-ros client)}
phase: 2 complete (ros2 actuator path, bench-verified); phase 4 started: rangefinder driver (compile-only, awaiting bench)  # pi: mcu-agent+core(supervisor,mcu_bridge) -usb/micro-ros-> esp32 -pwm-> servo+esc; legacy ascii path removed
next: phase 3 recorder/backup, phase 4 sensors (rangefinder first; imu/encoder/battery next)
plan: docs/docker_ros_plan.md
stack:
  mcu: {build: platformio in docker (docker/firmware.Dockerfile, image rccar-fw, make build/flash/monitor, FW_ENV=esp32s3), platform: espressif32@6.9.0, framework: arduino-esp32-2.0.17, comms: micro_ros_platformio jazzy serial uart0 (libdeps cached in .pio/libdeps), lang: c++gnu11}
  ros: {distro: jazzy, image: docker/ros.Dockerfile (ros:jazzy-ros-base by digest, rosdep+colcon, target test/runtime), stack: deploy/car/compose.yaml (mcu-agent, core, tools), pkgs: [rccar_msgs, rccar_supervisor, rccar_mcu_bridge, rccar_teleop, rccar_calibration, rccar_bringup], make: [config, ros-image, car-up, car-down, ros-test, unit, teleop, calibrate, tune, test, mcu, rangefinder]}
  host: {prereqs: [git, make, docker+compose+buildx], groups: [docker, dialout], python: none (make config runs in ros image, make unit in ros test image)}
hw: {steer: ds3225mg@gpio4, throttle: thw1060_esc@gpio5, battery: 2s_lipo, rangefinder: garmin_lidar_lite_v4_led@esp32 i2c gpio8(sda,garmin pin3,white)/gpio9(scl,garmin pin4,green) 0x62, vin(pin1,red) 5v sensor rail, gnd(pin2,black)}
usb_ports: {left_USB: native, planned regulated power input; right_COM: ch343 uart0, flashing + host link}
layout: .claude/layout.yaml
cmd: make help
plugins: .claude/settings.json  # superpowers, pyright-lsp, clangd-lsp, embedded-skills, ros2-engineering; mcp: .mcp.json (context7)
rules: .claude/rules/{firmware,dependencies,deploy,models,repos,claude-tooling,ros2,msgs,mcu_bridge,supervisor,calibration,tuning,rangefinder}.md  # path-scoped, see paths: frontmatter
agents: .claude/agents/ros2-reviewer.md  # review diffs vs rules + ros2-engineering refs + stop-path checklist
invariants:
  - esp32 role: actuator pwm + host comms only; powers nothing
  - sensors on separate power rail, common ground, <=3.3v signals
  - pins: left header P1 only; pins.h == README table
  - protocol/interface change => rccar_msgs + firmware/esp32/extra_packages (diff -r clean) + main.cpp + rccar_mcu_bridge + docs
  - tuning key change => tuning.toml + rccar_mcu_bridge.tuning.FIRMWARE_KEYS + main.cpp setKey (test-enforced: rccar_mcu_bridge/test/test_tuning.py)
  - supervisor = sole publisher of /rccar/mcu/drive; brake/disarm latch, arm = Reset(incident) -> armed but stationary
  - agents never run hardware fault-injection tests (kill core, unplug usb, motor runs); bench checklist is user-run (docs/setup.md)
  - usb replug => make car-down && make car-up (device node in mcu-agent container goes stale)
  - software stop is not safety-rated; esc power switch = hardware stop
  - no unconfirmed parameters in tuning.toml
  - new sensor => .claude/rules/<sensor>.md linking all docs/datasheets + docs/datasheets/<sensor>_<model>.md; sensor characteristics are tuning params, device protocol in a driver file
  - new deps => package.xml (rosdep) or a Dockerfile, never host; pin versions, no :latest
  - firmware paths: firmware/esp32/**
workflow:  # details: .claude/rules/claude-tooling.md
  - library/framework API => fetch current docs with context7 before writing code; match stack versions (arduino-esp32 2.x, esp-idf 4.4, ros2 jazzy)
  - non-trivial change => superpowers brainstorming -> writing-plans (docs/plans/) -> test-driven-development -> requesting-code-review
  - bug => superpowers systematic-debugging first
  - tests: no host python; deploy/ python => make unit (ros test image); ros => make ros-test (colcon test in docker); firmware => make build (compile, CI) + bench make test (hardware, user-run; never claim without output)
  - every PR body = .github/pull_request_template.md with user-run bench checklist (deploy + deps + feature checks)
  - after code edits => check lsp diagnostics (pyright, clangd; make compiledb for firmware)
