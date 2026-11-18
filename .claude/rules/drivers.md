---
paths:
  - "rccar_drivers/**"
  - "rccar_description/**"
  - "rccar_bringup/launch/drivers.launch.py"
  - "rccar_bringup/launch/viz.launch.py"
  - "rccar_calibration/**/lidar_imu*"
  - "docs/datasheets/slamtec*"
  - "docs/lidar/**"
---

# Lidar driver (rccar_drivers, rccar_description)

The software name is "lidar" or "mapper". The model name appears only in the datasheet docs. Reference (protocol, viz, bench values, power path): `docs/lidar/driver.md`. Status and open items: `docs/lidar/README.md`. Topics and QoS: `.claude/rules/ros2.md`. Hardware test rules: `.claude/rules/hw-testing.md`.

## Rules
- The driver uses only the standard library. Keep the logic in `rccar_drivers/slamtec/*` (no rclpy). The node only wires the lifecycle.
- All socket IO runs on one thread. Callbacks and timers do not share the socket.
- A device command error keeps the link up. Only a socket or protocol error causes a reconnect, with backoff.
- Copy the shape of a real device reply into the fake Mapper and its tests. Do not invent a reply format.
- The viz bridge is read-only. Never enable clientPublish, services or parameters: a viewer could publish `/rccar/mcu/drive` or call `/supervisor/arm`. `test_viz_launch.py` checks this.
- Do not hide an open parameter (`scan_angle_sign`, `map_transpose`, the IMU units, the mount offsets) behind a guessed value. Defaults stay in code. `tuning.toml` gets a value only after the bench confirms it.
- Mark IMU values that the device does not provide as not provided (covariance[0] = -1).
- `rccar_calibration` (`lidar_imu_monitor`) must not import `rccar_drivers`.

## Invariants
- The lidar is never in the stop path. On link loss, diagnostics show ERROR or stale and the driver reconnects. The supervisor and core are not affected.
- The `drivers` container is separate from core. It has no devices and no cap_add.
- The lidar takes power from the sensor rail (`+5V_SENS`), never from Pi USB. It needs no ESP32 pin.

## Verify
`make ros-test` (protocol, convert, fake-Mapper launch test, viz launch test). Hardware: `make lidar-hw-test` on the Pi, then the user bench. Never claim hardware success without output.
