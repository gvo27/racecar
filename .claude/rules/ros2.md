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
| /rccar/rangefinder/range | sensor_msgs/Range | esp32 (fake_mcu in tests) | best_effort | rangefinder_monitor, any |
| /rccar/lidar/scan | sensor_msgs/LaserScan (frame lidar_link, ~10 Hz) | rccar_drivers mapper_driver | best_effort (sensor_data) | viz, lidar_snapshot, lidar_record, any |
| /rccar/lidar/imu | sensor_msgs/Imu (frame lidar_imu_link, ~50 Hz; orientation only on fw 2.6.0_dev; rate/accel covariance[0]=-1 (not provided), values raw) | mapper_driver | best_effort | lidar_imu_monitor, lidar_snapshot, lidar_record, any |
| /rccar/mapper/pose | geometry_msgs/PoseStamped (pose of lidar_link in map, ~10 Hz) | mapper_driver | best_effort | lidar_imu_monitor, lidar_snapshot, lidar_record, any |
| /rccar/mapper/map | nav_msgs/OccupancyGrid (~0.5 Hz, map_period_s 2.0) | mapper_driver | reliable + transient_local depth 1 | viz, lidar_snapshot, lidar_record, any |
| /diagnostics | diagnostic_msgs/DiagnosticArray (status 'mapper_driver: link') | mapper_driver | default | any |
| /rccar/supervisor/state | SupervisorState | supervisor | reliable + transient_local depth 1 | teleop, UIs |
- TF: map->odom identity (static); odom->base_link from the Mapper SLAM pose (REP-105 deviation: it can jump on relocalization/loop closure until a continuous odom source (wheel encoder/IMU) exists; then the driver should publish map->odom instead); robot_state_publisher publishes base_link->lidar_link->lidar_imu_link (rccar_description).
- services: /supervisor/{arm,disarm,brake}; /mcu_bridge/{set_param,cal_point,raw_pwm,save,get,info,push_tuning}; /rccar/mcu/command (McuCommand, esp32).
- names: `/rccar/<area>/<stream>`, snake_case, no hardcoded absolute names inside libraries. Standard msgs before custom ones; units SI/REP-103 (rad, + = left).
- freshness beats delivery for commands (best effort, timeout at consumer); events/state must not be lost (reliable).

## Structure
- thin node, fat library: put logic in plain python modules (arbiter, teleop_state, tuning, commands, helpers) and test them with pytest without rclpy. The node only does wiring.
- launch_testing with the fake ESP32 (rccar_bringup/test/fake_mcu.py) tests the wiring. It is the seed of the sim adapter.
- Resource owners use lifecycle (mcu_bridge is managed, and car.launch.py configures + activates it). Every parameter uses `declare_parameter`.
- Never give instance attributes the names of rclpy.Node internals (`_services`, `_clients`, `_publishers`, `_subscriptions`, `_timers`, `_executor`, `_context`, `_clock`). Such names silently break the lifecycle services (regression test in rccar_mcu_bridge/test).
- Do not use a blocking `spin_until_future_complete` inside callbacks. Use coroutine callbacks + ReentrantCallbackGroup.
- Every launch file accepts `use_sim_time` and passes it to every node. The `sim:=` arg is reserved in rccar_bringup.
- The hardware boundary is the supervisor output `/rccar/mcu/drive` + the telemetry/sensor topics. Nothing above it imports ESP32/serial/Gazebo specifics. A sim-only branch in autonomy code = boundary leak.
- ament lint must pass (flake8, pep257, xmllint, copyright off). `<buildtool_depend>ament_python</buildtool_depend>` is NOT a rosdep key. Never add it (it breaks rosdep install).

## Skip
VDA 5050, Nav2 BT plugin scaffolding, gz-sim ECS/plugin tooling, mandatory 4-layer clean-architecture split per package, ros2_control (esp32 owns pwm, revisit with ackermann_steering_controller for captain/nav2).

## Verify
`make ros-test` (colcon test in docker). CI .github/workflows/ros.yml also runs the advisory ros2-engineering validators (qos_audit, launch_validator, skill_validate_hook). Hardware behavior = user bench only.
