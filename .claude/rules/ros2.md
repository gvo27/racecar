---
paths:
  - "ros2_ws/src/rccar_*/**"
---

# ROS 2 conventions (Jazzy)

Boundary topics, frames, QoS and TF: `docs/interfaces/sensor_contract.md` (tested by `deploy/tests/test_contract.py`). Other topics, subscribers and services: `docs/interfaces/ros2.md`. ros2-engineering references: communication, lifecycle-components, testing, launch-system.

## Interfaces
- A topic, type, frame or QoS change at the boundary changes the code, `docs/interfaces/sensor_contract.md` and the sim (skill `sim-parity`) together. A message change follows `.claude/rules/msgs.md`.
- The supervisor is the only publisher of `/rccar/mcu/drive`.
- Names are `/rccar/<area>/<stream>`, snake_case. Do not hardcode absolute names inside libraries. Use standard messages before custom ones. Units are SI and REP-103 (rad, + = left).
- Commands: freshness before delivery (best effort, timeout at the consumer). Events and state must not be lost (reliable).

## Structure
- Thin node, fat library: logic in plain Python modules with pytest and no rclpy. The node only does the wiring.
- Test the wiring with launch_testing and the fake ESP32 (`ros2_ws/src/rccar_bringup/test/fake_mcu.py`).
- Resource owners use lifecycle. Every parameter uses `declare_parameter`.
- Never give instance attributes the names of rclpy.Node internals (`_services`, `_clients`, `_publishers`, `_subscriptions`, `_timers`, `_executor`, `_context`, `_clock`). They silently break the lifecycle services.
- No blocking `spin_until_future_complete` inside callbacks. Use coroutine callbacks and a ReentrantCallbackGroup.
- Every launch file accepts `use_sim_time` and passes it to every node. The `sim:=` argument is reserved in `rccar_bringup`.
- Nothing above the boundary (`/rccar/mcu/drive` and the sensor topics) imports ESP32, serial or Gazebo specifics. A sim-only branch in autonomy code is a boundary leak.
- ament lint must pass (flake8, pep257, xmllint).

## Verify
`make ros-test`. Hardware behavior: the user bench only.
