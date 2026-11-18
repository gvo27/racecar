---
paths:
  - "rccar_calibration/**"
  - "rccar_teleop/**"
---

# Car tools (rccar_calibration, rccar_teleop)

Reference (each tool, its columns, files and teleop keys): `docs/tools/README.md`.

- `bench_test` never arms and never commands throttle. It does a steering sweep and a failsafe check only.
- `calibrate` writes only `[steering.calibration]` and `[throttle.calibration]` keys that exist in `tuning.toml`. It adds no keys. It writes in place (`update_tuning_file`): the file is a rw bind mount.
- Monitors and captures (`rangefinder_monitor`, `lidar_imu_monitor`, `lidar_snapshot`, `lidar_record`) only subscribe. No publishers, no service calls.
- All ESP32 access goes through the `mcu_bridge` services. Nothing here opens a serial port.
- Teleop: `a` (arm) is refused unless throttle is 0. Restore the terminal mode on every exit path. Teleop publishes only `DriveCmd(source='admin')` on `/rccar/cmd/admin`.
- Logic goes in pure helpers with pytest tests. Keyboard I/O stays in the node file.
- `lidar_imu_monitor` must not import `rccar_drivers` (the math is a copy on purpose).
- `logs/` is fully gitignored: maps and bags are floor plans of private spaces, and the repo is public. Never commit or upload captured data unasked.
- A key or service name change also changes the README, the `docs/setup.md` key table and `docs/tools/README.md`.
