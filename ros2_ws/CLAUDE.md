# ros2_ws/: agent notes

Rules load by path (`.claude/rules/ros2.md` and the package rules). Interfaces: `docs/interfaces/sensor_contract.md` (boundary), `docs/interfaces/ros2.md` (other topics and services). A boundary change uses skill `sim-parity`.

## Verify
- `make ros-test`: colcon build and colcon test in the ROS test image (pytest, launch_testing with the fake ESP32 and the fake Mapper, ament lint).
- `make unit`: `deploy/tests` (contract, layout, rule globs, hook) in the same image.
- pyright diagnostics of the changed files (`pyrightconfig.json` includes `ros2_ws/src`).
- A change to `rccar_msgs`: copy it to `firmware/esp32/extra_packages/rccar_msgs` and run `make build` (`.claude/rules/msgs.md`).
- Before you edit `rccar_drivers` or `rccar_description` on the Pi: `make drivers-stop` (`.claude/rules/hw-testing.md`).
