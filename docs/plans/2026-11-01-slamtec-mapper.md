# Plan: Slamtec Mapper M2M1 → ROS 2 (phase 4 starts with the lidar)

## Context
The car needs a lidar for semantic SLAM (geometric SLAM + camera detections fused onto the map) on the Pi 5 (Ubuntu 24.04, ROS 2 Jazzy in Docker). The Mapper M2M1 is a lidar with its own SLAM computer. It talks JSON over TCP port 1445 over Wi‑Fi or Ethernet, never over USB or serial.

**Driver finding:** there is no usable ROS 2 driver.
- `hatchbed/opensw_ros` is ROS 1 only (catkin/roscpp package.xml + CMakeLists). The datasheet's "ROS 1/2" note is wrong.
- Slamtec's `slamware_ros_sdk` is ROS 1 and wraps a closed binary SDK.

→ We write our own small Python driver. The protocol is already reverse‑engineered and validated in `docs/datasheets/slamtec_mapper_M2M1_datasheet.md` §11.

**User decisions:**
- v1 publishes scan + IMU + onboard SLAM pose/TF + onboard occupancy map.
- The lidar comes before the phase 3 recorder.

## Answers to the user's questions (go in docs/setup.md "Lidar" section)

**Bandwidth over Wi‑Fi:** the link has plenty of headroom.
- One scan is ≈930 pts × 12 B ≈ 11 KB raw, ≈15 KB as base64.
- At 10–20 Hz that is ≈1.2–2.4 Mbit/s. Add pose, IMU at 50 Hz, and the map polled at about 1 Hz, and the total stays under 5 Mbit/s.
- 802.11n/ac links give tens of Mbit/s, so throughput is fine.

The real Wi‑Fi costs are latency jitter (5–50 ms spikes) and dropouts. Mitigations:
- stamp each message on receive
- treat any gap longer than the timeout as stale and publish diagnostics
- the lidar is **not** in the stop path

**Network layout:**
- Bench and live: Ethernet stays on the lab LAN, and the Pi's onboard Wi‑Fi (wlan0) joins the Mapper's own `SLAMWARE-xxxx` AP, where the Mapper is 192.168.11.1.
- wlan0 must **not** take the default route, so internet keeps going over eth0. In netplan this is `dhcp4-overrides: {use-routes: false}` or a high route-metric.
- Consequence for live tests: the only radio is busy, so admin SSH from the laptop has to happen on the Mapper's AP. The laptop joins `SLAMWARE-xxxx` and SSHes to the Pi's 192.168.11.x address.
- Fallback: Mapper on Pi Ethernet (direct cable, Pi as DHCP server or static IP), the same driver with `host` changed.

**Power and wiring:**
- The Mapper takes 4.8–12 V, starts at up to 1.6 A, and runs at about 0.75 A typical. Ripple must stay at 50 mV or less.
- The only wire it needs is power to its 2‑pin "5V DC" receptacle. Data goes over Wi‑Fi. Nothing connects to the ESP32 or the GPIO header.
- **Do not power it from the Pi 5 USB ports.** Without a USB‑PD 5 A supply (the Pololu isn't PD), the Pi caps USB at 600 mA total. Even with `usb_max_current_enable=1` the cap is 1.6 A shared, and the Pololu D36V50F5 (5.5 A) is already fully used by the Pi's 5 A.
- Per the "sensors on separate rail, common ground" invariant: add a **second regulator** from the 2S LiPo as the sensor rail. For example, a second Pololu D36V50F5 or a smaller 5 V ≥3 A buck. Add a USB‑A female breakout or wire it straight to the 2‑pin plug, and tie the grounds together.
- Direct 2S battery (6–8.4 V) is inside the voltage range, but ESC/motor noise breaks the 50 mV ripple limit. Regulate.
- **The 1 ft 22AWG 3 A pigtail is electrically sufficient.**
  - Round‑trip resistance is about 0.6 m × 53 mΩ/m ≈ 32 mΩ, so the drop is ≈50 mV at 1.6 A. That stays above 4.8 V from a 5.0 V source.
  - Its rated 3 A is more than the 1.6 A peak.
  - But it only solves the conductor: it needs a USB‑A female source that can supply 2 A, and its bare end needs the Mapper's 2‑pin housing.
  - Simplest route: reuse or cut the kit cable's 2‑pin end and splice it to the pigtail, with red to + and black to GND. Check polarity with a multimeter before connecting.
- Mount: keep the M2.5 bottom screws ≤6 mm long, keep tilt within ±3°, and keep the speed at 2 m/s or less while mapping.

**Semantic SLAM path:**
- The Mapper supplies geometric SLAM (pose + occupancy grid) on its own CPU, which leaves the Pi free for detection models.
- The semantic layer still needs a **camera**, which isn't in the inventory, plus camera↔lidar extrinsics. That happens in phase 5 (rccar_perception/inference).
- The Garmin LIDAR‑Lite v4 is a 1‑D rangefinder, not a scanner.

## Implementation (executed by Sonnet subagents, task by task; Opus reviews each)

1. **`rccar_drivers/`**: new ament_python package, "thin node, fat library" per `.claude/rules/ros2.md`.
   - `rccar_drivers/slamtec/protocol.py` (no rclpy):
     - `MapperClient` with a socket, the `\n\r\n\r\n` delimiter, request_id matching and timeouts
     - `rle_inflate`, `parse_scan` and `decode_map`, ported from datasheet §11
     - helpers that convert results to plain dataclasses
   - `rccar_drivers/slamtec/convert.py`: conversion from the dataclasses to LaserScan, Imu, PoseStamped and OccupancyGrid fields.
     - Scan: angle bins with uniform increment. Fill `inf` for `dist==100000` or invalid points.
     - Map: handle the row/col orientation and verify it against a bench capture.
   - `rccar_drivers/mapper_node.py`: a **lifecycle** node `/mapper_driver`.
     - configure: connect and read `getsdpversion`
     - activate: start the timers
     - deactivate and cleanup close the socket
     - The node reconnects with backoff.
   - Parameters, all set through `declare_parameter`; defaults live in code until the bench confirms them:
     - `host` (192.168.11.1), `port` (1445)
     - `scan_rate` (10), `imu_rate` (50), `map_period_s` (1.0)
     - `frame_ids`, `publish_tf`, `timeout_s`
   - Publishes:

     | topic | type | QoS |
     |---|---|---|
     | `/rccar/lidar/scan` | LaserScan, frame `lidar_link` | sensor_data / best_effort |
     | `/rccar/lidar/imu` | Imu, frame `lidar_imu_link` | best_effort |
     | `/rccar/mapper/pose` | PoseStamped, frame `map` | best_effort |
     | `/rccar/mapper/map` | OccupancyGrid | reliable + transient_local, depth 1 |
     | `/diagnostics` | DiagnosticArray from `getrobothealth`, `getsystemresource`, link age | — |

   - TF: `map→odom` identity, and `odom→base_link` computed from the Mapper pose composed with the inverse of the `base_link→lidar_link` extrinsic, looked up from TF. REP‑105 compatible, so wheel odometry can replace the identity later.
   - Heartbeat file in `/run/hb` matching the core pattern.
   - Deps in package.xml: rclpy, rclpy lifecycle, sensor_msgs, geometry_msgs, nav_msgs, diagnostic_msgs, tf2_ros. Stdlib socket/json/base64; no new pip deps.
2. **`rccar_description/`**: minimal URDF/xacro (`base_link`, `lidar_link`, `lidar_imu_link`) plus robot_state_publisher, as package.xml deps `xacro` and `robot_state_publisher`.
   - Mount offsets are user‑measured on the car and entered before merge. No guessed numbers.
3. **`rccar_bringup/launch/drivers.launch.py`**: rsp + the lifecycle mapper driver, auto configure/activate, `use_sim_time` passthrough.
4. **`deploy/car/compose.yaml`**: new `drivers` service.
   - Same hardening anchors as `core`: host network, which is required to reach wlan0, read_only, cap_drop ALL, mem_limit, logging, and the heartbeat healthcheck.
   - No device access is needed. A driver crash can't touch core or the supervisor.
5. **Tests** (`make ros-test`):
   - pytest on the protocol: RLE swap/sentinel cases and the backward scan parser on synthetic encodings
   - a request/response delimiter‑split test
   - conversion tests
   - launch_testing with a **fake Mapper TCP server** (`rccar_drivers/test/fake_mapper.py`, a sibling of fake_mcu) that asserts the topics, TF and reconnect behavior
6. **Docs and context:**
   - `docs/setup.md` gets a Lidar section with the answers above: netplan wlan0 snippet, power wiring, and a bench checklist that the user runs.
   - `docs/docker_ros_plan.md`: phase 4 now first, and the phase status.
   - `.claude/rules/drivers.md` (paths `rccar_drivers/**`, `rccar_description/**`).
   - The `.claude/rules/ros2.md` topic table gains the new rows.
   - `.claude/layout.yaml`, CLAUDE.md (`phase`/`next`/`pkgs`/`make`).
   - `tuning.toml [platform.pi5] mapper_host`: add it **only after** the bench confirms the IP.

7. **Live websocket feed (`make viz`)**: **foxglove_bridge** (`ros-jazzy-foxglove-bridge`, an apt binary).
   - Why not rosbridge_suite: rosbridge sends JSON and is slow for LaserScan/OccupancyGrid. foxglove_bridge sends binary CDR, and the Foxglove app and the open-source Lichtblick viewer render scan, map and TF with no extra code.
   - Add it to package.xml of `rccar_bringup` as an exec_depend, plus `viz.launch.py` with `address:=127.0.0.1 port:=8765` and a topic whitelist (`/rccar/.*`, `/tf.*`, `/diagnostics`).
   - `make viz` runs `docker compose --profile tools run --rm tools ros2 launch rccar_bringup viz.launch.py`.
   - Binding to localhost means only SSH can reach it. VS Code Remote‑SSH auto‑forwards localhost:8765. The laptop opens Foxglove or Lichtblick at `ws://localhost:8765`.
   - Launch test: the bridge starts and the port opens.

8. **IMU vehicle feed + quick log (`make lidar-imu`)**.
   - The Mapper does publish IMU data: `getimuinrobotcoordinate` returns acc, gyro, compass and quaternion, and `getpose` returns yaw.
   - Keep only planar‑vehicle quantities:
     - heading: yaw from the SLAM pose, and from the IMU quaternion as a cross‑check
     - yaw rate: gyro z
     - horizontal acceleration: acc x (longitudinal) and acc y (lateral)
     - planar speed, derived from successive SLAM poses
   - Drop pitch, roll, vertical acc, gyro x/y and raw compass.
   - Note: "yaw" in the request is read as roll. Heading *is* yaw, so it stays.
   - Pure library `rccar_drivers/slamtec/vehicle_state.py` (pytest‑tested): quaternion→yaw, wrap, speed from poses.
   - No new topic: the monitor node subscribes to `/rccar/lidar/imu` and `/rccar/mapper/pose` and derives the fields itself.
   - `rccar_calibration/lidar_imu_monitor.py` + `lidar_imu_format.py`, mirroring `rangefinder_monitor` / `rangefinder_format` on the rangefinder branch:
     - prints one line per sample: time, heading_deg, yaw_rate_dps, acc_long, acc_lat, speed_mps and rate, plus a "waiting for…" hint while nothing arrives
     - appends JSON lines to `logs/lidar_imu_<UTC date-time>.jsonl` (logs/ is already mounted read‑write and gitignored), one file per run
     - no rotation and no other logging framework
   - Make target: `lidar-imu: _need-stack ## live Mapper IMU feed (heading, yaw rate, horizontal accel) + logs/lidar_imu_*.jsonl`

## Power-rail notes → posted as a comment on the `schematic` PR (branch not edited)
- Find the PR for head `schematic` and post **one** comment with the attribution footer. If no PR exists, tell the user and don't create one.
- Comment content:
  - The Mapper M2M1 load is 4.8–12 V, 0.75 A typical / 1.3 A max running / 1.6 A startup, with ripple ≤50 mV. It isn't in the `+5V_SENS` budget, which is 3.3 A TBD against a 4 A buck. Adding it takes running current to about 4.0–4.6 A worst case, so the buck rating should be revisited, maybe 5–6 A.
  - Suggested connection: a spare 2‑pin XH header (J11–J14), pin 1 +5V_SENS red, pin 2 GND black.
  - The 22AWG lead and the XH 3 A/pin rating are fine for 1.6 A.
  - The kit cable's 2‑pin housing is re‑terminated onto XHP‑2.
- The draft PR body also gets the same wiring summary.

## Process
- Branch **`lidar`**, created from **`origin/rangefinder`** (it merges to main soon). Reuse its `rangefinder_monitor` pattern, its make‑target style and `.github/pull_request_template.md`.
- Open a **draft PR** against `rangefinder`, or against `main` if rangefinder has already merged. The PR body follows the template, with the bench checklist and the wiring notes in it.
- Before starting, write `docs/plans/<date>-slamtec-mapper.md` (superpowers writing‑plans). Work TDD per task.
- Delegation:
  - **Sonnet** subagents (`model: "sonnet"`) do steps 1+5 (protocol/convert/tests), 1 (node), 2–3, 4 and 6 in sequence.
  - **Opus** reviews: the `ros2-reviewer` agent plus my own review of each diff before the next task.
- Fetch rclpy lifecycle, LaserScan and tf2 Jazzy docs with context7 before the node code is written.
- Commit and push to `lidar`, then open the draft PR.

## Verification

**Agent side (CI, no hardware):**
- `make ros-test` passes: unit tests, launch_testing with the fake Mapper (topics, TF, reconnect, foxglove_bridge port open) and ament lint.
- `make unit` passes. Check pyright diagnostics on the new package.

**Bench checklist (user-run, goes in the PR body).**
Yes, the visual checks use `make viz`: the websocket feeds a viewer on your laptop. RViz isn't needed on the Pi.

1. **Power + link**
   - Power the Mapper from `+5V_SENS` and wait about 40 s until it spins steadily.
   - On the Pi, check that `nmcli -t -f ACTIVE,SSID dev wifi | grep '^yes'` shows `SLAMWARE-…`.
   - Check that `ip route | grep default` still shows `eth0`.
   - Check that `nc -vz 192.168.11.1 1445` says `succeeded`.
2. **Stack:** `make car-up && make car-ps`, and `drivers` shows healthy.
3. **Rates:** in `make tools`, run `ros2 topic hz /rccar/lidar/scan` and expect about 10 Hz, then `ros2 topic hz /rccar/lidar/imu` and expect the IMU rate.
4. **Live view via `make viz`:**
   - In VS Code Remote‑SSH, open the **Ports** tab. Port 8765 is forwarded automatically; if it isn't, add it.
   - On the laptop, open Foxglove (app.foxglove.dev or the desktop app) or Lichtblick, choose "Foxglove WebSocket", and enter `ws://localhost:8765`.
   - Add a **3D panel** with fixed frame `map`. Turn on `/rccar/lidar/scan`, `/rccar/mapper/map` and `/tf`.
   - **Scan check:** the points trace the room's walls. Put your hand or a box about 0.5 m directly in front of the ▷ arrow on the lidar cap. Points must appear on **+X** (the red axis of `lidar_link`) at about 0.5 m. Move it to the left of the arrow, and the points must appear on **+Y** (green). If they show up mirrored or rotated, the angle convention is wrong, so stop and report it.
   - **Map + pose check:** hand‑carry the car, kept level within ±3° and at a walking pace, around a short loop (one room or a corridor and back).
     - Walls fill in grey and black on the map.
     - The `base_link` axes move with you, and forward motion goes along red +X.
     - Coming back to the start, the scan lines up with the map walls again, which means loop closure worked.
     - The map shape must match the real room and not be mirrored. A mirrored layout means the grid row/col orientation is flipped (datasheet §11 ambiguity).
     - This replaces the RoboStudio comparison, because RoboStudio is Windows‑only. If you have Windows, the same map in RoboStudio at 192.168.11.1 is an optional extra check.
5. **IMU feed:** run `make lidar-imu` with the car flat on the bench.
   - Expect heading steady, yaw_rate ≈ 0, acc_long/acc_lat ≈ 0 (±0.2 m/s²) and speed 0.
   - Rotate the car by hand about 90° to the left: heading goes up by about 90 and yaw_rate is positive while it moves.
   - Push it forward: acc_long goes positive briefly.
   - Check that `logs/lidar_imu_*.jsonl` exists and grows.
6. **Link loss (user‑run fault test; the car's ESC switch is OFF):**
   - Unplug Mapper power.
   - Within about 2 s, the Foxglove scan freezes. `make lidar-imu` prints `waiting for…`. In `ros2 topic echo /diagnostics --once`, the mapper status shows ERROR/stale, and the driver logs reconnect attempts (`make car-logs` or `docker compose logs drivers`).
   - **Supervisor unaffected:** `make car-ps` still shows `core` and `mcu-agent` healthy, and `ros2 topic echo /rccar/supervisor/state --once` shows the same state as before the unplug.
   - Plug the Mapper back in. After boot (about 40 s), the scan resumes with **no** container restart, and `drivers` goes back to healthy.
7. **Regression:** `make test`, then `make teleop` (drive, brake and disarm behave as before).
