# ros2_ws/: agent notes

Interfaces: `docs/interfaces/sensor_contract.md` (boundary), `docs/interfaces/ros2.md` (other topics and services).

## Verify
- `make ros-test`: colcon build and colcon test in the ROS test image (pytest, launch_testing with the fake ESP32 and the fake Mapper, ament lint).
- pyright diagnostics of the changed files (`pyrightconfig.json` includes `ros2_ws/src`).
- A `rccar_msgs` change: `.claude/rules/msgs.md`.
