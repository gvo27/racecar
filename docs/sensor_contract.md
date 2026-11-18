# Sensor and actuator contract (hardware boundary)

This file is the single list of the topics at the hardware boundary. The car drivers and the ESP32 firmware publish them. The sim repo ([racecar-sim](https://github.com/gvo27/racecar-sim)) must publish the same topics with the same type, frame and QoS. Then the code above the supervisor runs without changes in sim and on the car.

- `deploy/tests/test_contract.py` compares the "active" rows with the source code (`make unit`). If a row and the code are different, the test fails.
- "planned" rows are not tested. They show the names that new drivers must use.
- A change to a row needs a "Sim impact" section in the PR (`.claude/skills/sim-parity/SKILL.md`).
- QoS: `sensor_data` = best effort, keep last 5 (`qos_profile_sensor_data`). `reliable+tl` = reliable + transient local, depth 1.

## Topics

| topic | type | frame | publisher | qos | rate | status | sim source |
|---|---|---|---|---|---|---|---|
| /rccar/lidar/scan | sensor_msgs/LaserScan | lidar_link | mapper_driver | sensor_data | 10 Hz | active | real mapper_driver, fed by the virtual Mapper (TCP 1445) |
| /rccar/lidar/imu | sensor_msgs/Imu | lidar_imu_link | mapper_driver | sensor_data | 50 Hz | active | real mapper_driver, fed by the virtual Mapper |
| /rccar/mapper/pose | geometry_msgs/PoseStamped | map | mapper_driver | sensor_data | 10 Hz | active | real mapper_driver, fed by the virtual Mapper |
| /rccar/mapper/map | nav_msgs/OccupancyGrid | map | mapper_driver | reliable+tl | 0.5 Hz | active | real mapper_driver, fed by the virtual Mapper |
| /rccar/rangefinder/range | sensor_msgs/Range | rangefinder_link | esp32 | best_effort | 50 Hz | active | virtual ESP32 |
| /rccar/mcu/telemetry | rccar_msgs/Telemetry | - | esp32 | best_effort | 10 Hz | active | virtual ESP32 |
| /rccar/mcu/event | rccar_msgs/McuEvent | - | esp32 | reliable | event | active | virtual ESP32 |
| /rccar/mcu/drive | rccar_msgs/DriveCmd | - | supervisor | best_effort | 50 Hz | active | real supervisor (the virtual ESP32 only subscribes) |
| /rccar/mcu/command | rccar_msgs/McuCommand | - | esp32 (service) | service | on call | active | virtual ESP32 (same grammar as `handleLine`) |
| /rccar/cmd/captain | rccar_msgs/DriveCmd | - | captain | reliable | 20 Hz | active | sim policies and planners (never `/rccar/mcu/drive`) |
| /rccar/cmd/admin | rccar_msgs/DriveCmd | - | teleop | reliable | 20 Hz | active | real teleop |
| /rccar/odom/wheel | nav_msgs/Odometry | odom | encoder driver | sensor_data | TBD | planned | virtual ESP32 encoder stub (off by default) |
| /rccar/imu/data | sensor_msgs/Imu | imu_link | imu driver | sensor_data | TBD (100 Hz or more) | planned | gz IMU (full mode) |
| /rccar/camera/image_raw | sensor_msgs/Image | camera_optical_frame | camera driver | sensor_data | TBD | planned | later PR (camera sim) |

## TF

| parent -> child | publisher | status | note |
|---|---|---|---|
| map -> odom | mapper_driver | active | identity (REP-105 shortcut until the EKF exists) |
| odom -> base_link | mapper_driver | active | from the Mapper pose and the base_link -> lidar_link mount |
| base_link -> lidar_link -> lidar_imu_link | robot_state_publisher (rccar_description) | active | mount offsets UNMEASURED (0) |
| base_link -> rangefinder_link | - | gap | the frame is in the Range header, but not in the URDF yet |

The sim never publishes `odom -> base_link` or any `/rccar/*` topic from Gazebo directly. The Gazebo ground-truth pose goes on an internal topic outside `/rccar/`.

## Device facts that the sim must copy

| fact | value | source |
|---|---|---|
| Mapper result code for success | 1 (not 0) | PR gvo27/racecar#6, `slamtec/protocol.py` `RESULT_OK` |
| Mapper health flags | camelCase (`hasError`, `hasLidarDisconnected`, ...) | PR #6, `slamtec/protocol.py` |
| Raw points per scan | about 920 over 360 degrees; the driver bins them to `n_bins` 1080 | datasheet section 11, `mapper_node.py` |
| Scan range | `range_min` 0.15 m, `range_max` 40 m | `mapper_node.py` PARAMS |
| Mapper IMU (fw 2.6.0_dev) | orientation only, availability bitmap 131, rate and acceleration covariance[0] = -1 | PR #6 bench |
| Mapper pose | 10 Hz, about 100 ms late, can jump on relocalization | PR #6 roadmap note (not verified as a model) |
| Track | 2D lidar needs walls of 30 cm or more | PR #6 roadmap note |
