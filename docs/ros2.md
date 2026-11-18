# ROS 2 interfaces: reference

The hardware-boundary topics (type, frame, QoS, rate, TF) are owned by [docs/sensor_contract.md](sensor_contract.md). This file lists the rest: topics above the boundary, the subscribers and the services. The rules are in [.claude/rules/ros2.md](../.claude/rules/ros2.md).

## Topics above the boundary
| topic | type | publisher | QoS | subscriber |
|---|---|---|---|---|
| /rccar/cmd/admin, /rccar/cmd/captain | DriveCmd | teleop, captain (one topic for each source) | reliable depth 1 | supervisor (best_effort depth 1, matches either) |
| /rccar/supervisor/state | SupervisorState | supervisor | reliable + transient_local depth 1 | teleop, UIs |
| /diagnostics | diagnostic_msgs/DiagnosticArray (status `mapper_driver: link`) | mapper_driver | default | any |

## Subscribers of the boundary topics
| topic | subscriber |
|---|---|
| /rccar/mcu/drive | ESP32 (micro-ROS best effort). The supervisor is the only publisher |
| /rccar/mcu/telemetry | any |
| /rccar/mcu/event | supervisor, mcu_bridge |
| /rccar/rangefinder/range | rangefinder_monitor, any |
| /rccar/lidar/scan, /rccar/mapper/map | viz, lidar_snapshot, lidar_record, any |
| /rccar/lidar/imu, /rccar/mapper/pose | lidar_imu_monitor, lidar_snapshot, lidar_record, any |

## Services
- `/supervisor/{arm,disarm,brake}`
- `/mcu_bridge/{set_param,cal_point,raw_pwm,save,get,info,push_tuning}`
- `/rccar/mcu/command` (McuCommand, ESP32)

## Not used
VDA 5050, Nav2 BT plugin scaffolding, gz-sim ECS and plugin tooling, a 4-layer clean-architecture split for each package, ros2_control (the ESP32 owns PWM; revisit with ackermann_steering_controller for captain or Nav2).

## CI
`.github/workflows/ros.yml` also runs the advisory ros2-engineering validators (qos_audit, launch_validator, skill_validate_hook).
