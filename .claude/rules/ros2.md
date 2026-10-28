---
paths:
  - "rccar_*/**"
---

# ROS 2 conventions (jazzy; ros2-engineering refs: communication, lifecycle-components, testing, launch-system)

## Names + QoS (actual table; change a row => change code + this table + msgs.md)
| topic | type | publisher | QoS | subscriber |
|---|---|---|---|---|
| /rccar/cmd/admin, /rccar/cmd/captain | DriveCmd | teleop / captain (own topic per source) | reliable depth 1 | supervisor, best_effort depth 1 (matches either) |
| /rccar/mcu/drive | DriveCmd | supervisor ONLY | best_effort depth 1 | esp32 (micro-ros best effort) |
| /rccar/mcu/telemetry | Telemetry | esp32 | best_effort | any |
| /rccar/mcu/event | McuEvent | esp32 | reliable depth 10 | supervisor, mcu_bridge |
| /rccar/supervisor/state | SupervisorState | supervisor | reliable + transient_local depth 1 | teleop, UIs |
- services: /supervisor/{arm,disarm,brake}; /mcu_bridge/{set_param,cal_point,raw_pwm,save,get,info,push_tuning}; /rccar/mcu/command (McuCommand, esp32).
- names: `/rccar/<area>/<stream>`, snake_case, no hardcoded absolute names inside libraries. Standard msgs before custom ones; units SI/REP-103 (rad, + = left).
- freshness beats delivery for commands (best effort, timeout at consumer); events/state must not be lost (reliable).

## Structure
- thin node, fat library: logic in plain python modules (arbiter, teleop_state, tuning, commands, helpers) tested with pytest without rclpy; node = wiring only.
- launch_testing with the fake MCU (rccar_bringup/test/fake_mcu.py) for wiring; it is the seed of the sim adapter.
- lifecycle for resource owners (mcu_bridge is managed; car.launch.py configures + activates it). Every parameter via `declare_parameter`.
- never name instance attributes like rclpy.Node internals (`_services`, `_clients`, `_publishers`, `_subscriptions`, `_timers`, `_executor`, `_context`, `_clock`): it silently kills lifecycle services (regression test in rccar_mcu_bridge/test).
- no blocking `spin_until_future_complete` inside callbacks; coroutine callbacks + ReentrantCallbackGroup.
- `use_sim_time` accepted by every launch file and passed to every node; `sim:=` arg reserved in rccar_bringup.
- hardware boundary = supervisor output `/rccar/mcu/drive` + telemetry/sensor topics; nothing above imports ESP32/serial/Gazebo specifics. sim-only branch in autonomy code = boundary leak.
- ament lint must pass (flake8, pep257, xmllint; copyright off). `<buildtool_depend>ament_python</buildtool_depend>` is NOT a rosdep key: never add it (breaks rosdep install).

## Skip
VDA 5050, Nav2 BT plugin scaffolding, gz-sim ECS/plugin tooling, mandatory 4-layer clean-architecture split per package, ros2_control (esp32 owns pwm; revisit with ackermann_steering_controller for captain/nav2).

## Verify
`make ros-test` (colcon test in docker). CI .github/workflows/ros.yml also runs advisory ros2-engineering validators (qos_audit, launch_validator, skill_validate_hook). Hardware behavior = user bench only.
