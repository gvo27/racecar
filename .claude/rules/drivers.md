---
paths:
  - "rccar_drivers/**"
  - "rccar_description/**"
  - "rccar_bringup/launch/drivers.launch.py"
  - "rccar_bringup/launch/viz.launch.py"
  - "rccar_calibration/**/lidar_imu*"
  - "docs/datasheets/slamtec*"
---

# Drivers: lidar (Slamtec Mapper M2M1) -> rccar_drivers, rccar_description

Software name "lidar"/"mapper"; model name only in datasheet docs. Docs: `docs/datasheets/slamtec_mapper_M2M1_datasheet.md` (protocol section 11), `docs/setup.md` "Lidar" (power, networking, viewing). Topics/QoS table: `.claude/rules/ros2.md`. Service: `.claude/rules/deploy.md`.

## Protocol facts
- JSON over TCP 1445 on the Mapper's Wi-Fi (192.168.11.1) or Ethernet; messages end with `\n\r\n\r\n`, matched by request_id. No USB/serial data.
- no ROS 2 driver exists (opensw_ros and slamware_ros_sdk are ROS 1): own stdlib-only driver; logic in `rccar_drivers/slamtec/*` (no rclpy), node = lifecycle wiring (`mapper_driver`).
- all socket IO on one thread (no sharing the socket between callbacks/timers); reconnect with backoff; stamp on receive.

## Viz bridge + TF
- viz bridge is read-only; never enable clientPublish/services/parameters (would bypass the supervisor: a viewer could publish /rccar/mcu/drive or call /supervisor/arm). viz.launch.py sets `capabilities: [connectionGraph, assets]` and `^$` for client_topic/service/param whitelists (foxglove_bridge defaults are all `.*`); test_viz_launch.py asserts it.
- REP-105 deviation: odom->base_link comes from the SLAM pose and may jump on relocalization/loop closure until a continuous odom source (wheel encoder/IMU) exists; then the driver should publish map->odom instead.
- LaserScan.scan_time = polling period, stamp = receive time (device per-scan pose/timestamp not used yet).
- map fetch is skipped (throttled warning) when the known area exceeds `map_max_cells` (default 4e6); `map_period_s` default 2.0. Device command errors (nonzero code) keep the link up; only socket/protocol errors reconnect (backoff reset by the first good scan).

## Bench-TBD (do not hide behind guessed values; defaults in code, not in tuning.toml)
- `scan_angle_sign`, `map_transpose`, `map_free_is_high`: flip per the bench check (obstacle in front of the cap arrow must appear on +X, left on +Y; map not mirrored).
- IMU `linear_acceleration` units (raw), gyro rad/s assumed.
- `rccar_description` mount offsets: UNMEASURED until the user measures them on the car. No guessed numbers.
- no unconfirmed parameters in tuning.toml (`[platform.pi5] mapper_host` only after the bench confirms the IP).

## Invariants
- lidar is never in the stop path; link loss => diagnostics ERROR/stale + reconnect, supervisor/core unaffected.
- `drivers` container separate from core (crash isolation); no devices, no cap_add.
- sensors on separate power rail (`+5V_SENS`), common ground; the lidar needs no ESP32 pin.
- lidar power: `+5V_SENS` XH header (J11-J14) -> XHP-2 -> USB-A male 2-wire pigtail (red=+, black=GND) -> the Mapper's USB-A "5V DC" socket (power input only, no data); 5 V only, never from Pi USB.
- `calibration` (lidar_imu_monitor) must not import rccar_drivers; the quaternion/speed math is duplicated on purpose.

## Verify
`make ros-test` (protocol, convert, fake-Mapper launch test, viz launch test). Hardware: `make lidar-hw-test` (agent-run on the Pi, `.claude/rules/hw-testing.md`) then user bench (PR body checklist); never claim it without output.
