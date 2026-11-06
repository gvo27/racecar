---
paths:
  - "rccar_calibration/**"
  - "rccar_teleop/**"
---

# rccar_calibration + rccar_teleop (run via `make calibrate|tune|test|teleop`, stack up)

- `bench_test` NEVER arms and never commands throttle (motor stays off): steering sweep + failsafe check only. There is no ROS throttle test.
- `calibrate`: prompts for physical steps, jogs with raw_pwm/cal_point, on `save` writes the ESP32 flash (mcu_bridge save) and `tuning.toml` via `update_tuning_file` (in place, bind mount rw). Only `[steering.calibration]` / `[throttle.calibration]` keys that exist; no new keys.
- `rangefinder_monitor` (`make rangefinder`): read-only subscriber on `/rccar/rangefinder/range` (best effort), prints MCU stamp, Pi time, range, rate; prints a hint every 2 s while no data. Pure formatting in `rangefinder_format.py`.
- `lidar_imu_monitor` (`make lidar-imu`): read-only; subscribes `/rccar/lidar/imu` + `/rccar/mapper/pose` (sensor_data QoS); prints <=10 lines/s (pi time, heading from pose yaw, imu_heading from the quaternion (cross-check), yaw_rate/speed/acc_long/acc_lat all derived from the SLAM pose (`lidar_imu_pose.py`: ~0.3 s finite difference + EMA, acc_lat = speed*yaw_rate, yaw step > 0.5 rad = relocalization: estimator reset, `JUMP`), IMU rate, `imu_gyro`/`imu_acc` shown n/a when the Imu message has covariance[0] = -1), appends JSON lines to `logs/lidar_imu_<UTC>.jsonl` (`log_dir` param / `RCCAR_LOG_DIR`, default /ws/src/racecar/logs; unwritable => warn once). JSONL has the same keys plus `source` (pose/imu per key) and `jump`. Pure code in `lidar_imu_format.py` + `lidar_imu_pose.py` (quat->yaw/wrap/speed duplicated from rccar_drivers on purpose; no import). Rules: drivers.md.
- `lidar_snapshot` (`make lidar-snapshot`): read-only one-shot; subscribes scan/pose/imu (sensor_data), map (reliable + transient_local), /diagnostics for `window_s` (3) up to `timeout_s` (8); writes `logs/lidar_snapshot_<UTC>/` (map.png, scan/pose/imu/map_meta/diagnostics/summary .json, summary.txt incl. scan-map agreement); exit 0 iff scan+pose+map seen. Pure code: `lidar_snapshot_render.py` (stdlib PNG), `lidar_snapshot_summary.py`.
- `lidar_record` (`make lidar-record SECS=30`): `ros2 bag record -s mcap` of the lidar topics (`lidar_record.TOPICS`) into `logs/lidar_bag_<UTC>/`, SIGINT after `--secs` (1..600), then `ros2 bag info`. Needs rosbag2 + rosbag2_storage_mcap (package.xml).
- `logs/` is fully gitignored (public repo; maps/bags are floor plans of private spaces). Never commit or upload captured data unasked.
- `tune`: calls `/mcu_bridge/push_tuning` (+ save).
- all MCU access through mcu_bridge services; nothing here opens a serial port.
- teleop keys: up/down throttle, left/right heading (+ = left), `c` center, space BRAKE, `d` disarm, `a` arm (Reset; refused unless throttle 0), `q` disarm+quit, `x` disarm+quit+shutdown hint. Terminal mode restored on every exit path; publish `DriveCmd(source='admin')` on /rccar/cmd/admin; max throttle default 0.3.
- pure helpers (teleop_state.py, helpers.py) carry the logic and are pytest-tested; keep keyboard I/O in the node file.
- changing a key or service name => README + docs/setup.md key table + this file.
