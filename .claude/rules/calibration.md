---
paths:
  - "rccar_calibration/**"
  - "rccar_teleop/**"
---

# rccar_calibration + rccar_teleop (run with `make calibrate|tune|test|teleop`, stack up)

- `bench_test` NEVER arms and never commands throttle (the motor stays off). It does a steering sweep and a failsafe check only. There is no ROS throttle test.
- `calibrate` prompts for physical steps and jogs with raw_pwm/cal_point. On `save` it writes the ESP32 flash (mcu_bridge save) and `tuning.toml` through `update_tuning_file` (in place, bind mount rw). It writes only `[steering.calibration]` / `[throttle.calibration]` keys that exist. It adds no new keys.
- `rangefinder_monitor` (`make rangefinder`) is a read-only subscriber on `/rccar/rangefinder/range` (best effort). It prints MCU stamp, Pi time, range and rate. It prints a hint every 2 s while no data arrives. Pure formatting is in `rangefinder_format.py`.
- `lidar_imu_monitor` (`make lidar-imu`) is read-only. It subscribes to `/rccar/lidar/imu` and `/rccar/mapper/pose` (sensor_data QoS). It prints at most 10 lines/s with these columns:
  - Pi time.
  - `heading` (from the pose yaw).
  - `imu_heading` (from the IMU quaternion, as a cross-check).
  - `yaw_rate`, `speed`, `acc_long` and `acc_lat`. All four come from the SLAM pose. `lidar_imu_pose.py` computes them with a finite difference over ~0.3 s plus EMA, and `acc_lat` = speed * yaw_rate. A yaw step above 0.5 rad means relocalization: the estimator resets and the line shows `JUMP`.
  - IMU rate.
  - `imu_gyro` and `imu_acc`. The line shows n/a for them when the Imu message has covariance[0] = -1.
- `lidar_imu_monitor` also appends JSON lines to `logs/lidar_imu_<UTC>.jsonl` (`log_dir` param / `RCCAR_LOG_DIR`, default /ws/src/racecar/logs). If the directory is not writable, it warns one time. The JSONL has the same keys plus `source` (pose or imu for each key) and `jump`. The pure code is in `lidar_imu_format.py` and `lidar_imu_pose.py`. The quaternion-to-yaw, wrap and speed code is a copy of the rccar_drivers code on purpose (no import). Rules: drivers.md.
- `lidar_snapshot` (`make lidar-snapshot`) is a read-only one-shot. It subscribes to scan, pose and imu (sensor_data), map (reliable + transient_local) and /diagnostics for `window_s` (3) up to `timeout_s` (8). It writes `logs/lidar_snapshot_<UTC>/` with map.png, the .json files (scan, pose, imu, map_meta, diagnostics, summary) and summary.txt (includes the scan-map agreement). It exits with 0 only if it saw scan, pose and map. The pure code is `lidar_snapshot_render.py` (stdlib PNG) and `lidar_snapshot_summary.py`.
- `lidar_record` (`make lidar-record SECS=30`) runs `ros2 bag record -s mcap` for the lidar topics (`lidar_record.TOPICS`) into `logs/lidar_bag_<UTC>/`. It sends SIGINT after `--secs` (1..600), then runs `ros2 bag info`. It needs rosbag2 and rosbag2_storage_mcap (package.xml).
- `logs/` is fully gitignored. The repo is public, and maps and bags are floor plans of private spaces. Never commit or upload captured data unasked.
- `tune` calls `/mcu_bridge/push_tuning` (+ save).
- All ESP32 access goes through mcu_bridge services. Nothing here opens a serial port.
- Teleop keys: up/down = throttle, left/right = heading (+ = left), `c` = center, space = BRAKE, `d` = disarm, `a` = arm (Reset). `a` is refused unless throttle is 0. `q` = disarm + quit, `x` = disarm + quit + shutdown hint. Terminal mode is restored on every exit path. Teleop publishes `DriveCmd(source='admin')` on /rccar/cmd/admin. Default max throttle is 0.3.
- Pure helpers (teleop_state.py, helpers.py) hold the logic and have pytest tests. Keep keyboard I/O in the node file.
- If you change a key or service name, change README + docs/setup.md key table + this file.
