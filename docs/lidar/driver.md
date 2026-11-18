# Lidar driver: reference

Facts about the lidar driver (`rccar_drivers`, `rccar_description`). The rules are in [.claude/rules/drivers.md](../../.claude/rules/drivers.md). Status: [README.md](README.md). Device facts: [docs/datasheets/slamtec_mapper_M2M1_datasheet.md](../datasheets/slamtec_mapper_M2M1_datasheet.md).

## Protocol facts
- The protocol is JSON over TCP 1445 on the Mapper's Wi-Fi (192.168.11.1, bench-confirmed) or on Ethernet. `mapper_host` may move to tuning.toml [platform.pi5] in a later change. Messages end with `\n\r\n\r\n` and are matched by request_id. There is no USB or serial data.
- On the bench firmware (2.6.0_dev), result `code == 1` means success. The datasheet envelope does not say this (`protocol.RESULT_OK`). The `getrobothealth` flags are camelCase (`hasError`...). `Health.from_result` parses them (it also accepts snake_case). The device failure code is unobserved.
- No ROS 2 driver exists (opensw_ros and slamware_ros_sdk are ROS 1). The project has its own driver that uses only the standard library. The logic is in `rccar_drivers/slamtec/*` (no rclpy). The node (`mapper_driver`) only wires the lifecycle.
- All socket IO runs on one thread. Callbacks and timers do not share the socket. The driver reconnects with backoff and stamps each message on receive.

## Viz bridge + TF
- The viz bridge is read-only. Never enable clientPublish, services or parameters. They would bypass the supervisor: a viewer could publish /rccar/mcu/drive or call /supervisor/arm. `viz.launch.py` sets `capabilities: [connectionGraph, assets]` and `^$` for the client_topic, service and param whitelists (the foxglove_bridge defaults are all `.*`). `test_viz_launch.py` asserts this.
- REP-105 deviation: odom->base_link comes from the SLAM pose. It may jump on relocalization or loop closure until a continuous odom source (wheel encoder or IMU) exists. After that, the driver should publish map->odom instead.
- LaserScan.scan_time is the polling period and stamp is the receive time. The driver does not use the device per-scan pose or timestamp yet.
- The driver skips the map fetch (with a throttled warning) when the known area is larger than `map_max_cells` (default 4e6). `map_period_s` is 2.0 by default. A device command error (a code other than `RESULT_OK`) keeps the link up. Only a socket or protocol error causes a reconnect. The first good scan resets the backoff.

## Bench values and open parameters (defaults in code, not in tuning.toml)
- `scan_angle_sign`, `map_transpose`: flip them as the bench check shows. An obstacle in front of the cap arrow must appear on +X, an obstacle on the left must appear on +Y, and the map must not be mirrored.
- `map_free_is_high`: CONFIRMED False (bench 2026-11-02: Bitmap8Bit 0 is unknown, 1..127 is free, 128..255 is occupied). The parameter stays for other firmware versions.
- IMU (fw 2.6.0_dev): orientation only. Bench values: `availibilityBitMap` 131, acc ~0.003 at rest (no gravity, units unverified), gyro/raw_*/compass exactly 0.
  - The bit layout is INFERRED (`protocol.ImuBit`, datasheet section 11). The SDK lists names without values. The layout agrees with the bench: 131 = QUATERNION + CALIBRATED_ACC + FUSION_6DOF.
  - `/rccar/lidar/imu` shows what the device provides with covariance[0] = -1 (`slamtec/imu.py`). Rates are not provided unless the CALIBRATED_GYRO bit is set. Acceleration is not provided unless the CALIBRATED_ACC bit is set AND param `imu_trust_acc` is true (default false). The values are still copied raw.
  - The driver publishes the bitmap as the `imu_avail_bitmap` value of the `mapper_driver: link` diagnostics status. The hw test reads it from there.
- Heading and yaw rate come from the SLAM pose, not from the IMU. The SLAM pose has a 10 Hz rate and ~100 ms latency, and it jumps on relocalization or loop closure. `make lidar-imu` derives heading and yaw rate and gates the jumps. For true yaw rate and body acceleration, a dedicated IMU is needed (tuning.toml `[imu]`, reserved, add nothing).
- `rccar_description` mount offsets are UNMEASURED until the user measures them on the car. Do not use guessed numbers.
- Put no unconfirmed parameters in tuning.toml (`[platform.pi5] mapper_host` only after the bench confirms the IP).

## Power path
- `+5V_SENS` XH header (J11 to J14), XHP-2 housing, USB-A male 2-wire pigtail (red +, black GND), the Mapper USB-A "5V DC" socket (power input only, no data).

## Hardware test (`make lidar-hw-test`)
- A launch_testing run: `rccar_drivers/test_hw/test_mapper_hw.py`. Criteria and thresholds: `rccar_drivers/hw_criteria.py` (pytest: `test/test_hw_criteria.py`). Report: `logs/hw_test_lidar_<UTC>.json`, with `status` for each criterion.
- Each criterion is PASS, FAIL or NA ("not provided"). NA never fails. OVERALL is PASS only if no criterion is FAIL.
- IMU gyro-at-rest is NA when its bit is absent from `imu_avail_bitmap` (read from /diagnostics). acc-units is NA when its bit is absent or the driver marks acceleration as not provided (`imu_trust_acc` false, the default).
- `rccar_drivers/test_hw/` is not under `test/`. `conftest.py` ignores it unless `RCCAR_HW_TEST=1`, so `colcon test` and CI never collect it. `setup.py` installs it to `share/rccar_drivers/test_hw/` for the runtime image.
- The test runs its own driver, so `drivers` must be stopped. It leaves `drivers` stopped and says so.
- Work loop: `make drivers-stop`, edit, `make ros-test` (fake Mapper), `make ros-image`, `make lidar-hw-test`.
