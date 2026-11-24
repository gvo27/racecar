# Lidar: status and findings

This file owns the bench status of the lidar (Slamtec Mapper M2M1, JSON over TCP 1445 on Wi-Fi). Other docs point here for the status. They do not copy it. The source is PR #6: its bench checklist, the owner comments and the agent bench comment of 2026-11-02.

Other facts have their own owners:

| Topic | Owner |
| --- | --- |
| Driver parameters, protocol facts, bench-confirmed values | [.claude/rules/drivers.md](../../.claude/rules/drivers.md) |
| Device facts, protocol notes, power specs | [docs/datasheets/slamtec_mapper_M2M1_datasheet.md](../datasheets/slamtec_mapper_M2M1_datasheet.md) |
| Power harness, networking, viewing, debug tools | [docs/setup.md](../setup.md) "Lidar" |
| Topics, frames, QoS, device facts for the sim | [docs/interfaces/sensor_contract.md](../interfaces/sensor_contract.md) |
| Hardware test criteria | `ros2_ws/src/rccar_drivers/rccar_drivers/hw_criteria.py` |
| Agent rules on the Pi | [.claude/rules/hw-testing.md](../../.claude/rules/hw-testing.md) |
| Design plan | [docs/plans/2026-11-01-slamtec-mapper.md](../plans/2026-11-01-slamtec-mapper.md) |
| Roadmap: track, 3D lidar, odometry, sim | [roadmap.md](roadmap.md) |

## Status (2026-11-18)

The driver code is in `main`. The driver runs on the real Mapper (owner comment on PR #6). **The owner reports that lidar mapping still needs troubleshooting.** Mapping is not accepted.

| Check (PR #6 bench checklist) | Result |
| --- | --- |
| Deploy: `make setup`, `make config`, `make car-down`, `make car-up && make car-ps` | pass |
| Netplan file with SSID `SLAMWARE-D22981`, metrics eth0 100 / wlan0 600 | pass |
| `nc -vz 192.168.11.1 1445` | pass |
| Route metric checks (`grep RouteMetric`, lab and home `ip route`) | not done |
| Power: pigtail continuity, first boot, move to `+5V_SENS` | not done |
| Step 1: `make lidar-hw-test` | box ticked by the owner. No `OVERALL: PASS` report is recorded. The 5 recorded runs (below) did not pass |
| Step 1: `make drivers-start` after the test | pass |
| `make viz` and the Foxglove connection to `ws://localhost:8765` | pass |
| Scan direction (+X forward, +Y left) | not done |
| Map and pose loop, map not mirrored | not done |
| Mount offsets measured | not done. The URDF offsets are 0 and UNMEASURED |
| `make lidar-imu` checks | not done |
| `make lidar-snapshot`, `make lidar-record SECS=10` | not done on the bench |
| Link loss (unplug Mapper power) | not done |
| Regression: `make test`, `make teleop` | not done |

### Hardware test runs (2026-11-02, after fix `93cf2c0`)

| Run | Report (`logs/`, on the Pi, not in git) | Result | IMU acc units | Pose drift |
| --- | --- | --- | --- | --- |
| 1 | `hw_test_lidar_20261102T214447Z.json` | 18/20 | FAIL, mean abs acc 0.004 | FAIL, 0.072 m, 1.45 deg |
| 2 | `hw_test_lidar_20261102T215056Z.json` (the agent did not start this run. It read only the JSON summary) | 19/20 | FAIL, 0.005 | PASS, 0.020 m, 0.00 deg |
| 3 | `hw_test_lidar_20261102T215517Z.json` | 19/20 | FAIL, 0.003 | PASS, 0.000 m, 0.00 deg |
| 4 | `hw_test_lidar_20261102T215534Z.json` | 18/20 | FAIL, 0.005 | FAIL, 0.220 m, 4.60 deg |
| 5 | `hw_test_lidar_20261102T215551Z.json` | 18/20 | FAIL, 0.005 | FAIL, 0.152 m, 2.20 deg |

The other 18 criteria passed in every run. Values: scan 10.00 Hz, gap 0.11 s, 1080 ranges, finite fraction 0.45 to 0.47, IMU 49.8 to 50 Hz, quaternion norm exact, pose 10 Hz, map 143 x 159 at 0.05 m, 39 % known, TF resolvable. `sdp_version` was `2.6.0_dev (Dec 12 2019)`. The "imu gyro z at rest" pass is not evidence of a working gyro: the value is exactly 0.

## Findings

These are the lessons from the lidar work. Each one has a reason that is not clear from the code alone.

1. **The fake Mapper hid two protocol errors.** The bench firmware returns `"code":1` for success, and the health flags are camelCase. The fake Mapper used `0` and snake_case, so CI passed and the real device failed. The log showed `mapper connect failed: getsdpversion failed: code 1`. The `drivers` container stayed unhealthy for 39 h, and 19 of 20 hw tests failed. Fix: `93cf2c0`. Lesson: get one real device reply before you write the fake server, and copy its shape. The failure code of the device is not observed.
2. **The IMU gives orientation only on firmware 2.6.0_dev.** `availibilityBitMap` is 131. `raw_acc`, `gyro`, `raw_gyro` and `compass` are exactly 0. `acc` is about 0.003 at rest, with no gravity, units unknown. So `make lidar-imu` derives yaw rate, acceleration and speed from the SLAM pose (10 Hz, about 100 ms latency). A true yaw rate and acceleration need a separate IMU.
3. **Pose drift at rest is not stable.** Drift failed in 3 of 5 runs (0.07 to 0.22 m, up to 4.6 deg) and passed in 2. A possible cause is SLAM pose corrections while the unit is stationary. This is not proven, and the test room was not controlled. The 0.05 m / 2 deg limit is the owner's decision.
4. **The map cell encoding is the reverse of the first guess.** Bitmap8Bit 0 is unknown, 1 to 127 is free, 128 to 255 is occupied. `map_free_is_high` is now `False` by default (bench 2026-11-02).
5. **The viz bridge needs the new websocket subprotocol.** foxglove_bridge 3.6.0 accepts `foxglove.sdk.v1` and rejects `foxglove.websocket.v1`. It logs `Dropping client ...: handshake failed` for a plain HTTP request, for example `localhost:8765` in a browser ("connection was reset" in Firefox). `app.foxglove.dev` through the VS Code port forward connected with 0 handshake failures. The network layout was not the cause.
6. **The viz bridge is read-only by design.** The default bridge settings let a viewer publish `/rccar/mcu/drive` or call `/supervisor/arm`. The bridge binds to 127.0.0.1:8765, with the capabilities `connectionGraph` and `assets` only. A test checks this.
7. **Route metrics, not route removal.** An earlier netplan file set `use-routes: false, use-dns: false` on wlan0. That applied to every SSID and broke home internet. Metrics (eth0 100, wlan0 600, dhcp4 and dhcp6 equal) keep the lab LAN first and home Wi-Fi working.
8. **The Mapper power input is a USB-A socket.** It is a power input, not a USB data port. An earlier PR text described a 2-pin receptacle. The Pi USB ports cannot supply the 1.6 A start-up current.
9. **Logs are private.** A map or a bag is a floor plan of the place where the car was, and the repo is public. `logs/` is fully gitignored.
10. **Wi-Fi bandwidth is enough. Jitter is the cost.** A scan is about 15 KB (base64), so 10 Hz is about 1.2 Mbit/s, under 5 Mbit/s with pose, IMU and map. Jitter is 5 to 50 ms with dropouts. The driver stamps on receive, reports stale data in diagnostics and reconnects by itself.

## Open items

- Troubleshoot the mapping (owner report). Then do the scan direction, map mirror and loop checks (`scan_angle_sign`, `map_transpose`).
- Measure the mount offsets (`lidar_x`, `lidar_y`, `lidar_z`, `lidar_yaw`) and put them in `ros2_ws/src/rccar_description/urdf/rccar.urdf.xacro`. The PR says: measure them before the merge.
- Get one `make lidar-hw-test` run with `OVERALL: PASS`, or change the criteria for the IMU units and the pose drift (owner decision). Record the report name here.
- Find the cause of exit code 137 of `rccar-drivers-1` on `make drivers-stop` (not investigated).
- Do the power checks and move the Mapper to the `+5V_SENS` header. The Mapper is not in the 3.3 A rail budget of the power board. With the Mapper, the 4 A buck goes to about 4.6 A (notes on gvo27/racecar#3).
- Do the link-loss test and the route metric checks.
- Move `mapper_host` (192.168.11.1) to `[platform.pi5]` in `tuning.toml` (follow-up).
