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

## Supervisor
- Input priority and timeout come from the supervisor config, keyed on the input topic: admin 100 / 0.3 s, captain 10 / 0.5 s.
- `/rccar/supervisor/state` reason strings are 64 characters or fewer.
- Stop-path checklist (hardware runs are user bench only): kill teleop, kill core, unplug USB, agent loss, stale reset, reset with throttle not 0, double brake, brake during reset.

## mcu_bridge
- Lifecycle node `/mcu_bridge`. Typed services wrap `/rccar/mcu/command` (McuCommand). `commands.py` builds the command strings.
- On activation (when `/rccar/mcu/command` is reachable) and on each `McuEvent.READY`, it pushes `firmware_commands(tuning)` in sequence and stops at the first error. `SAVE` only if `save_after_push`.
- `FIRMWARE_KEYS` in `tuning.py` maps (table, key) to the firmware command. `update_tuning_file` rewrites `key = value` lines in place.
- The heartbeat file is touched every 0.5 s while the node is ACTIVE. The docker healthcheck reads it.

## Launch and tuning parameters
- Launch arguments: `use_sim_time`, `sim`, `tuning_file` (default `$RCCAR_TUNING`, else `/ws/src/racecar/tuning.toml`), `heartbeat_dir`.
- `rccar_bringup/tuning_params.py` `PARAM_MAP` maps `tuning.toml` tables to node parameters. Only keys that are in the file are passed. Otherwise the nodes keep their code defaults.
