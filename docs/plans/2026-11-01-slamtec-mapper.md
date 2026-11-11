# Plan: Slamtec Mapper M2M1 → ROS 2 (phase 4 starts with the lidar)

## Context
The car needs a lidar for semantic SLAM (geometric SLAM + camera detections fused onto the map) on the Pi 5 (Ubuntu 24.04, ROS 2 Jazzy in Docker). The Mapper M2M1 is a lidar with its own SLAM computer. It sends JSON over TCP port 1445 on Wi‑Fi or Ethernet. It never uses USB or serial.

**Driver finding:** there is no usable ROS 2 driver.
- `hatchbed/opensw_ros` is ROS 1 only (catkin/roscpp package.xml + CMakeLists). The datasheet's "ROS 1/2" note is wrong.
- Slamtec's `slamware_ros_sdk` is ROS 1 and wraps a closed binary SDK.

Decision: we write our own small Python driver. The protocol is already reverse‑engineered and validated in `docs/datasheets/slamtec_mapper_M2M1_datasheet.md` §11.

**User decisions:**
- v1 publishes scan + IMU + onboard SLAM pose/TF + onboard occupancy map.
- The lidar comes before the phase 3 recorder.

## Answers to the user's questions (go in docs/setup.md "Lidar" section)

**Bandwidth over Wi‑Fi:** the link has enough capacity.
- One scan is ≈930 pts × 12 B ≈ 11 KB raw, ≈15 KB as base64.
- At 10–20 Hz that is ≈1.2–2.4 Mbit/s. With pose, IMU at 50 Hz, and the map polled at about 1 Hz, the total stays under 5 Mbit/s.
- 802.11n/ac links give tens of Mbit/s, so throughput is enough.

The real Wi‑Fi costs are latency jitter (5–50 ms spikes) and dropouts. These actions reduce the effect:
- stamp each message on receive
- treat any gap longer than the timeout as stale and publish diagnostics
- the lidar is **not** in the stop path

**Network layout:**
- Bench and live: Ethernet stays on the lab LAN. The onboard Wi‑Fi of the Pi (wlan0) joins the `SLAMWARE-xxxx` AP of the Mapper. On that AP, the Mapper is 192.168.11.1.
- At the lab, wlan0 must not get the default route, so internet traffic keeps going over eth0. Corrected: use netplan route metrics (eth0 100, wlan0 600, dhcp4 and dhcp6 overrides). Do not use `use-routes: false`. It broke home Wi‑Fi because overrides are per interface. At home, wlan0 is the only default route. Details: docs/setup.md. The AP IP 192.168.11.1 is bench-confirmed.
- Result for live tests: the only radio is busy, so admin SSH from the laptop must use the AP of the Mapper. The laptop joins `SLAMWARE-xxxx` and connects with SSH to the 192.168.11.x address of the Pi.
- Fallback: connect the Mapper to the Pi Ethernet port (direct cable, Pi as DHCP server or static IP). Use the same driver with `host` changed.

**Power and wiring:**
- The Mapper accepts 4.8–12 V. It draws up to 1.6 A at start and about 0.75 A typical when it runs. Ripple must stay at 50 mV or less.
- The only wire it needs is power to its "5V DC" input. This input is a standard USB‑A socket beside the RJ45 port (corrected: earlier drafts said a 2‑pin receptacle). Data goes over Wi‑Fi. Nothing connects to the ESP32 or the GPIO header.
- **Do not power it from the Pi 5 USB ports.** Without a USB‑PD 5 A supply (the Pololu is not PD), the Pi limits USB to 600 mA total. Even with `usb_max_current_enable=1`, the limit is 1.6 A shared. The 5 A of the Pi already uses most of the Pololu D36V50F5 (5.5 A).
- The invariant "sensors on separate rail, common ground" applies. Add a **second regulator** from the 2S LiPo as the sensor rail. For example, use a second Pololu D36V50F5 or a smaller 5 V ≥3 A buck. Connect `+5V_SENS` to the Mapper through the USB‑A male pigtail (below), and tie the grounds together.
- A direct 2S battery (6–8.4 V) is inside the voltage range. But ESC and motor noise exceeds the 50 mV ripple limit. Use a regulator.
- **The 1 ft 22AWG 3 A pigtail is electrically sufficient.**
  - The round‑trip resistance is about 0.6 m × 53 mΩ/m ≈ 32 mΩ, so the voltage drop is ≈50 mV at 1.6 A. The voltage stays above 4.8 V from a 5.0 V source.
  - Its rating of 3 A is more than the 1.6 A peak.
  - **Corrected:** the USB‑A male plug of the pigtail goes straight into the "5V DC" USB‑A socket of the Mapper. Crimp an XHP‑2 onto its bare ends (red to pin 1 `+5V_SENS`, black to pin 2 GND). You do not need to splice the kit cable.
  - Before the first connection, use a multimeter to check the pigtail colors (USB pin 1 red, pin 4 black) and to check that the Mapper port does not source voltage. For the first power-up, use a bench supply at 5.0 V with a limit of about 2 A, if possible.
- Mount: the M2.5 bottom screws must be ≤6 mm long. Keep tilt within ±3°. Keep the speed at 2 m/s or less while mapping.

**Semantic SLAM path:**
- The Mapper supplies geometric SLAM (pose + occupancy grid) on its own CPU. This leaves the Pi free for detection models.
- The semantic layer still needs a **camera**, which is not in the inventory, plus camera↔lidar extrinsics. This work is in phase 5 (rccar_perception/inference).
- The Garmin LIDAR‑Lite v4 is a 1‑D rangefinder, not a scanner.

## Implementation (Sonnet subagents do it task by task, and Opus reviews each task)

1. **`rccar_drivers/`**: new ament_python package, "thin node, fat library" per `.claude/rules/ros2.md`.
   - `rccar_drivers/slamtec/protocol.py` (no rclpy):
     - `MapperClient` with a socket, the `\n\r\n\r\n` delimiter, request_id matching and timeouts
     - `rle_inflate`, `parse_scan` and `decode_map`, ported from datasheet §11
     - helpers that convert results to plain dataclasses
   - `rccar_drivers/slamtec/convert.py`: converts the dataclasses to LaserScan, Imu, PoseStamped and OccupancyGrid fields.
     - Scan: angle bins with uniform increment. Fill `inf` for `dist==100000` or invalid points.
     - Map: handle the row/col orientation and verify it with a bench capture.
   - `rccar_drivers/mapper_node.py`: a **lifecycle** node `/mapper_driver`.
     - configure: connect and read `getsdpversion`
     - activate: start the timers
     - deactivate and cleanup close the socket
     - The node reconnects with backoff.
   - Parameters, all set through `declare_parameter`. The defaults stay in code until the bench confirms them:
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

   - TF: `map→odom` is identity. The node computes `odom→base_link` from the Mapper pose, composed with the inverse of the `base_link→lidar_link` extrinsic, which it looks up from TF. This is REP‑105 compatible, so wheel odometry can replace the identity later.
   - Heartbeat file in `/run/hb` matching the core pattern.
   - Deps in package.xml: rclpy, rclpy lifecycle, sensor_msgs, geometry_msgs, nav_msgs, diagnostic_msgs, tf2_ros. The driver uses the standard library socket, json and base64 modules. There are no new pip deps.
2. **`rccar_description/`**: minimal URDF/xacro (`base_link`, `lidar_link`, `lidar_imu_link`) plus robot_state_publisher, as package.xml deps `xacro` and `robot_state_publisher`.
   - Mount offsets are user‑measured on the car and entered before merge. No guessed numbers.
3. **`rccar_bringup/launch/drivers.launch.py`**: rsp + the lifecycle mapper driver, auto configure/activate, `use_sim_time` passthrough.
4. **`deploy/car/compose.yaml`**: new `drivers` service.
   - It uses the same hardening anchors as `core`: host network (required to reach wlan0), read_only, cap_drop ALL, mem_limit, logging, and the heartbeat healthcheck.
   - It needs no device access. A driver crash cannot affect core or the supervisor.
5. **Tests** (`make ros-test`):
   - pytest on the protocol: RLE swap/sentinel cases and the backward scan parser on synthetic encodings
   - a request/response delimiter‑split test
   - conversion tests
   - launch_testing with a **fake Mapper TCP server** (`rccar_drivers/test/fake_mapper.py`, a sibling of fake_mcu) that asserts the topics, TF and reconnect behavior
6. **Docs and context:**
   - Add a Lidar section to `docs/setup.md` with the answers above: netplan wlan0 snippet, power wiring, and a bench checklist that the user runs.
   - `docs/docker_ros_plan.md`: phase 4 is now first. Update the phase status.
   - `.claude/rules/drivers.md` (paths `rccar_drivers/**`, `rccar_description/**`).
   - Add the new rows to the `.claude/rules/ros2.md` topic table.
   - `.claude/layout.yaml`, CLAUDE.md (`phase`/`next`/`pkgs`/`make`).
   - `tuning.toml [platform.pi5] mapper_host`: add it **only after** the bench confirms the IP.

7. **Live websocket feed (`make viz`)**: **foxglove_bridge** (`ros-jazzy-foxglove-bridge`, an apt binary).
   - Why not rosbridge_suite: rosbridge sends JSON and is slow for LaserScan/OccupancyGrid. foxglove_bridge sends binary CDR. The Foxglove app and the open-source Lichtblick viewer show scan, map and TF with no extra code.
   - Add it to package.xml of `rccar_bringup` as an exec_depend, plus `viz.launch.py` with `address:=127.0.0.1 port:=8765` and a topic whitelist (`/rccar/.*`, `/tf.*`, `/diagnostics`).
   - `make viz` runs `docker compose --profile tools run --rm tools ros2 launch rccar_bringup viz.launch.py`.
   - The bridge binds to localhost, so only SSH can reach it. VS Code Remote‑SSH forwards localhost:8765 automatically. The laptop opens Foxglove or Lichtblick at `ws://localhost:8765`.
   - Launch test: the bridge starts and the port opens.

8. **IMU vehicle feed + quick log (`make lidar-imu`)**.
   - The Mapper does publish IMU data: `getimuinrobotcoordinate` returns acc, gyro, compass and quaternion. `getpose` returns yaw.
   - Keep only planar‑vehicle quantities:
     - heading: yaw from the SLAM pose, and from the IMU quaternion as a cross‑check
     - yaw rate: gyro z
     - horizontal acceleration: acc x (longitudinal) and acc y (lateral)
     - planar speed, derived from successive SLAM poses
   - Drop pitch, roll, vertical acc, gyro x/y and raw compass.
   - Note: the request word "yaw" is read as roll. Heading *is* yaw, so it stays.
   - Pure library `rccar_drivers/slamtec/vehicle_state.py` (pytest‑tested): quaternion→yaw, wrap, speed from poses.
   - No new topic. The monitor node subscribes to `/rccar/lidar/imu` and `/rccar/mapper/pose` and derives the fields itself.
   - `rccar_calibration/lidar_imu_monitor.py` + `lidar_imu_format.py`, mirroring `rangefinder_monitor` / `rangefinder_format` on the rangefinder branch:
     - prints one line per sample: time, heading_deg, yaw_rate_dps, acc_long, acc_lat, speed_mps and rate, plus a "waiting for…" hint while nothing arrives
     - appends JSON lines to `logs/lidar_imu_<UTC date-time>.jsonl` (logs/ is already mounted read‑write and gitignored), one file per run
     - no rotation and no other logging framework
   - Make target: `lidar-imu: _need-stack ## live Mapper IMU feed (heading, yaw rate, horizontal accel) + logs/lidar_imu_*.jsonl`

## Power-rail notes → posted as a comment on the `schematic` PR (branch not edited)
- Find the PR for head `schematic` and post **one** comment with the attribution footer. If no PR exists, tell the user. Do not create a PR.
- Comment content:
  - The Mapper M2M1 load is 4.8–12 V, 0.75 A typical / 1.3 A max running / 1.6 A startup, with ripple ≤50 mV. It is not in the `+5V_SENS` budget, which is 3.3 A TBD against a 4 A buck. With the Mapper, the running current is about 4.0–4.6 A worst case. Review the buck rating again, maybe 5–6 A.
  - Suggested connection: a spare 2‑pin XH header (J11–J14), pin 1 +5V_SENS red, pin 2 GND black.
  - The 22AWG lead and the XH rating of 3 A per pin are enough for 1.6 A.
  - Corrected: crimp XHP‑2 onto the bare ends of a USB‑A male 22AWG pigtail (red to +, black to GND). Its USB‑A plug goes into the "5V DC" USB‑A socket of the Mapper.
- Put the same wiring summary in the draft PR body.

## Process
- Branch **`lidar`**, created from **`origin/rangefinder`** (it merges to main soon). Reuse its `rangefinder_monitor` pattern, its make‑target style and `.github/pull_request_template.md`.
- Open a **draft PR** against `rangefinder`, or against `main` if rangefinder has already merged. The PR body follows the template and includes the bench checklist and the wiring notes.
- Before you start, write `docs/plans/<date>-slamtec-mapper.md` (superpowers writing‑plans). Use TDD for each task.
- Delegation:
  - **Sonnet** subagents (`model: "sonnet"`) do steps 1+5 (protocol/convert/tests), 1 (node), 2–3, 4 and 6 in sequence.
  - **Opus** reviews with the `ros2-reviewer` agent, plus my own review of each diff before the next task.
- Check the upstream rclpy lifecycle, LaserScan and tf2 Jazzy docs before you write the node code.
- Commit and push to `lidar`, then open the draft PR.

## Verification

**Agent side (CI, no hardware):**
- `make ros-test` passes: unit tests, launch_testing with the fake Mapper (topics, TF, reconnect, foxglove_bridge port open) and ament lint.
- `make unit` passes. Check the pyright diagnostics on the new package.

**Bench checklist (user-run, goes in the PR body).**
The visual checks use `make viz`. The websocket feeds a viewer on your laptop. RViz is not needed on the Pi.

1. **Power + link**
   - Power the Mapper from `+5V_SENS`. Wait about 40 s until it spins steadily.
   - On the Pi, check that `networkctl status wlan0` shows `SLAMWARE-…`.
   - Check that `ip route | grep default` still shows `eth0`.
   - Check that `nc -vz 192.168.11.1 1445` says `succeeded`.
2. **Stack:** `make car-up && make car-ps`, and `drivers` shows healthy.
3. **Rates:** in `make tools`, run `ros2 topic hz /rccar/lidar/scan` and expect about 10 Hz, then `ros2 topic hz /rccar/lidar/imu` and expect the IMU rate.
4. **Live view via `make viz`:**
   - In VS Code Remote‑SSH, open the **Ports** tab. Port 8765 is forwarded automatically. If it is not, add it.
   - On the laptop, open Foxglove (app.foxglove.dev or the desktop app) or Lichtblick. Choose "Foxglove WebSocket" and enter `ws://localhost:8765`.
   - Add a **3D panel** with fixed frame `map`. Turn on `/rccar/lidar/scan`, `/rccar/mapper/map` and `/tf`.
   - **Scan check:** the points trace the walls of the room. Put your hand or a box about 0.5 m directly in front of the ▷ arrow on the lidar cap. Points must appear on **+X** (the red axis of `lidar_link`) at about 0.5 m. Move it to the left of the arrow. The points must then appear on **+Y** (green). If the points are mirrored or rotated, the angle convention is wrong. Stop and report it.
   - **Map + pose check:** carry the car by hand around a short loop (one room, or a corridor and back). Keep it level within ±3° and move at a walking pace.
     - Walls appear in grey and black on the map.
     - The `base_link` axes move with you. Forward motion goes along red +X.
     - When you return to the start, the scan lines up with the map walls again. This means loop closure worked.
     - The map shape must match the real room and must not be mirrored. A mirrored layout means the grid row/col orientation is flipped (datasheet §11 ambiguity).
     - This check replaces the RoboStudio comparison, because RoboStudio runs only on Windows. If you have Windows, you can also compare the same map in RoboStudio at 192.168.11.1 (optional).
5. **IMU feed:** run `make lidar-imu` with the car flat on the bench.
   - Expect heading steady, yaw_rate ≈ 0, acc_long/acc_lat ≈ 0 (±0.2 m/s²) and speed 0.
   - Rotate the car by hand about 90° to the left. Heading goes up by about 90, and yaw_rate is positive while the car moves.
   - Push the car forward. acc_long goes positive for a short time.
   - Check that `logs/lidar_imu_*.jsonl` exists and grows.
6. **Link loss (user‑run fault test; the car's ESC switch is OFF):**
   - Unplug Mapper power.
   - Within about 2 s, the Foxglove scan freezes. `make lidar-imu` prints `waiting for…`. In `ros2 topic echo /diagnostics --once`, the mapper status shows ERROR/stale. The driver logs reconnect attempts (`make car-logs` or `docker compose logs drivers`).
   - **Supervisor unaffected:** `make car-ps` still shows `core` and `mcu-agent` healthy, and `ros2 topic echo /rccar/supervisor/state --once` shows the same state as before the unplug.
   - Connect the Mapper power again. After boot (about 40 s), the scan resumes with **no** container restart, and `drivers` becomes healthy again.
7. **Regression:** run `make test`, then `make teleop`. Drive, brake and disarm must work as before.
