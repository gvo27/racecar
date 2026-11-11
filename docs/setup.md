# Setup: zero to driving

Assumptions have the label **Assume:**. If an assumption is false, fix it before you continue.

## 1. Host

**Assume:** you have a Raspberry Pi 5 with Ubuntu 24.04 (a laptop works for firmware work). The host has `git`, `make` and **Docker Engine + compose plugin + buildx**. Nothing else is installed on the host. Python, PlatformIO and ROS all run in Docker. The host has internet access to Docker Hub, `packages.ros.org`, `raw.githubusercontent.com` (rosdep), pypi.org and registry.platformio.org.

```sh
sudo usermod -aG docker,dialout $USER   # then log out and back in
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/gvo27/racecar && cd racecar    # one clone per user; collaborators work via GitHub PRs
make install-host                       # sudo: udev rule -> /dev/rccar-esp32, systemd unit rccar.service (enabled)
cp .env.example .env                    # set TZ, ROS_DOMAIN_ID (default 0), PLATFORM=pi5
make setup                              # check prerequisites, build both images (fw-image + ros-image)
```

- The repo is at `~/ros2_ws/src/racecar` on the Pi. The containers mount it at `/ws/src/racecar` (read-only, plus `tuning.toml` and `logs/` read-write), so calibration writes your working copy. Use one clone for each user. Nobody edits the clone of another user.
- `make install-host` prints each step. It installs `deploy/car/99-rccar.rules` (CH343 `1a86:55d3` -> `/dev/rccar-esp32`, group `dialout`). It renders `deploy/car/rccar.service` with the path of this clone and your user. Afterwards, unplug the USB cable and plug it in again one time. The unit starts the stack at boot with the images that are already built. Deploys stay explicit (`make car-pull && make car-up`).
- `make setup` checks the host prerequisites and builds both images (`fw-image`, `ros-image`).
- `make config` runs automatically in `make car-up` and in the boot service; run it by hand only to check the rendered file. It runs `deploy/render_env.py` inside the ROS image (so it needs `make ros-image` first), reads `.env` and `tuning.toml [platform.$PLATFORM]` (today: `esp32_device`, `arch`) and writes the gitignored `deploy/car/.env.generated`. It fails with a hint if `.env` is missing.
- `make ros-image` runs `rosdep` against `package.xml`, so it needs `packages.ros.org` and `raw.githubusercontent.com`.

**Claude Code (optional):** open the repo in Claude Code and trust the folder. Claude Code then asks you to install the plugins in `.claude/settings.json`.

| Plugin / server | Use |
| --- | --- |
| `superpowers` | brainstorm → plan → TDD → review workflow |
| `pyright-lsp` | Python diagnostics, needs `pyright-langserver` on PATH |
| `clangd-lsp` | firmware C/C++ diagnostics, needs `clangd` on PATH + `make compiledb` |
| `embedded-skills` | firmware architecture, RTOS, ISR design |
| `asd-ste100` | Simplified Technical English rewrites for docs and PR text (`.claude/rules/writing.md`) |
| `ros2-engineering` | micro-ROS, ros2_control, Nav2, perception, advisory hooks (`ROS2_SKILL_DISABLE_HOOKS=all` turns them off) |

```sh
sudo apt install clangd         # firmware LSP
pipx install pyright            # Python LSP (or: npm install -g pyright)
make check-dev                  # both must say OK
make compiledb                  # firmware/esp32/compile_commands.json for clangd
make unit                       # deploy/tests in the ROS test image, no hardware
```

## 2. Wiring (power off)

**Assume:** the ESC switch is **off**, the battery is connected to the ESC, and the car is on a stand with the wheels off the ground.

1. Connect the servo signal to P1-4 (GPIO4). Connect the ESC throttle-lead signal to P1-5 (GPIO5).
2. Connect the ESC black wire and the servo black wire to P1-22 (G), the common ground.
3. Connect the ESC red wire (6 V) to the servo red wire only, through a Y-harness. **No red wire touches the ESP32.**

See the pin map in the [README](../README.md#pin-map-left-header-p1-only).

## 3. Connect

**Assume:** you use a USB-C cable that carries **data**, and it is in the **right** USB-C port of the board, labelled **COM**. The left port, **USB**, is reserved for future regulated power. Never flash through it.

```sh
ls -l /dev/rccar-esp32     # the udev symlink exists once the board is plugged in (make install-host)
```

## 4. Flash (micro-ROS firmware)

**Assume:** the ESC is **off** and the car stack is **down** (`make car-down`). Flash and monitor refuse to run while the stack holds the serial port.

```sh
make flash      # FW_ENV=esp32s3 (micro-ROS). Builds in Docker and uploads over COM.
```

- The first `make build` / `make flash` also builds the micro-ROS library into `firmware/esp32/.pio/libdeps` (git clone of ROS repos + colcon, about 10 minutes, needs network). `make build` and `make flash` clean only `.pio/build`, so later builds are fast. `make clean` deletes everything, including `libdeps`.
- If the upload cannot connect: hold **BOOT**, tap **RST**, release **BOOT**, then run the command again.
- Time sync uses `rmw_uros_sync_session`. The `TIME` command is not available over micro-ROS.

## 5. Start the car stack

```sh
make car-up     # config + docker compose up -d: mcu-agent + core (supervisor + mcu_bridge)
make car-ps     # both services must become "healthy"
make car-logs   # Ctrl+C to exit
```

Then switch the ESC **on** while the ESP32 is running. The ESC beeps and learns 1500 µs as neutral. The car boots disarmed. Nothing moves until you arm it.

## 6. Drive over SSH

```sh
ssh pi              # from the laptop
cd ~/ros2_ws/src/racecar && make teleop
```

Teleop runs in the SSH terminal and talks to the supervisor locally (`/rccar/cmd/admin`). ROS traffic never leaves the Pi.

| Key | Action |
| --- | --- |
| up / down | throttle +/- one step (limited to `max_throttle`) |
| left / right | heading left / right (REP-103: left is positive) |
| `c` | center heading |
| space | **brake** (latches an incident, throttle to 0) |
| `d` | **disarm** (latches an incident) |
| `a` | **arm** = reset the latched incident; only with throttle at 0; the car is armed but stationary |
| `q` | disarm and quit |
| `x` | disarm, quit and print the shutdown hint |

After a brake or disarm, the supervisor refuses motion until you press `a` (with throttle at neutral). After arming, the supervisor forwards throttle only after teleop sends a neutral command (teleop does that automatically). The ESP32 failsafe disarms on its own if drive commands stop. **The software stop is not safety-rated. The ESC power switch is the independent hardware stop.**

## 7. Test, calibrate, tune (ROS)

The stack must be running (`make car-up`). The tools run in the `tools` container and call the `mcu_bridge` services.

```sh
make test            # steering sweep + failsafe check, motor stays off, never arms
make calibrate       # find center / left / right, measure maxdeg, `save`, `q`
git diff tuning.toml # calibrate wrote the [steering.calibration] values into your clone
make tune            # push tuning.toml to the ESP32 and save it to flash
```

`mcu_bridge` also pushes `tuning.toml` to the ESP32 RAM when it starts (after the ESP32 is reachable) and every time the firmware reports READY. There is no ROS throttle test.

Single commands to the ESP32 (stack up): `make mcu CMD="GET"`, `make mcu CMD="INFO"`, `make mcu CMD="SET gain 1.5"`. These call `/rccar/mcu/command`. The ESP32 refuses `D` and `ARM`, because drive and arming go through the supervisor. `SET` changes RAM only. The next tuning push (on ESP32 READY) overwrites it. To keep a value, edit `tuning.toml` and run `make tune`.

### Tuning loop

1. Edit `tuning.toml`.
2. `make tune` (or `ros2 service call /mcu_bridge/push_tuning std_srvs/srv/Trigger` from `make ros-shell`).
3. Run `make teleop` to drive.
4. Commit `tuning.toml` when the car behaves as you want.

### Rangefinder

Wiring (power off): see [README "Rangefinder wiring"](../README.md#rangefinder-wiring-garmin-lidar-lite-v4-led). Datasheet summary: [rangefinder_lidar_lite_v4.md](datasheets/rangefinder_lidar_lite_v4.md). The sensor 5 V comes from the sensor rail, never from the ESP32.

```sh
make mcu CMD="SENS rangefinder"   # read-only status + config line (stack up); publishing is on while driver = 1
make rangefinder                  # live feed: MCU timestamp, Pi receive time, range (m/cm), rate; Ctrl+C to exit
```

The first flash after this feature needs a rebuild of the micro-ROS library (`rccar.meta` has 3 publishers). Run `make clean && make flash` one time. `+inf` means that the sensor reported its no-return value (`rf_no_return`). The firmware publishes every other reading unchanged, so consumers must check `min_range`/`max_range` (REP-117). To disable the sensor, run `make mcu CMD="SET rf_driver 0"`, or set `[rangefinder] driver = 0` and run `make tune`. Bench checklists are now in each PR body ([`.github/pull_request_template.md`](../.github/pull_request_template.md)), not here.

**How I2C clocking works (for newcomers).** I2C uses two wires: SCL (clock) and SDA (data). The ESP32 is the bus master and is the only device that drives SCL. The sensor changes SDA only while SCL is low. The receiver samples SDA while SCL is high. So the hardware keeps data and clock in step, and there is no software synchronisation to do. The timestamp on a range sample marks when the ESP32 finished the read (converted to ROS time through `rmw_uros_sync_session`). It does not mark when the light left the sensor.

### Lidar (Slamtec Mapper M2M1)

Software name: *lidar* (topics `/rccar/lidar/*`, `/rccar/mapper/*`). Datasheet digest: [slamtec_mapper_M2M1_datasheet.md](datasheets/slamtec_mapper_M2M1_datasheet.md). Rules: `.claude/rules/drivers.md`. Status: compile/CI only, not bench-verified.

**What it is.** A 2-D lidar with its own onboard SLAM computer. It publishes scans, IMU, a SLAM pose and an occupancy map over JSON on TCP port 1445, via its own Wi-Fi or its Ethernet port. There is no USB or serial data connection; the only wire is power. Nothing connects to the ESP32 or the GPIO header.

**Why our own driver.** The ROS drivers that exist do not fit: `hatchbed/opensw_ros` is ROS 1 (catkin/roscpp; the datasheet's "ROS 1/2" is wrong) and Slamtec's `slamware_ros_sdk` is ROS 1 around a closed binary SDK. `rccar_drivers` (node `mapper_driver`, container `drivers`) speaks the protocol directly with the Python stdlib; no new pip deps.

**Power and wiring (power off; nothing here is bench-verified).**
- Load: 4.8-12 V, ~0.75 A typical, 1.3 A max running, 1.6 A at start-up, ripple <= 50 mV.
- Source: the `+5V_SENS` rail of the power board (branch `schematic`) through a spare 2-pin JST-XH header (J11-J14): pin 1 `+5V_SENS`, pin 2 GND. Rail ground is common with the car ground.
- Harness: the Mapper's "5V DC" input is a standard USB-A socket right beside the Ethernet (RJ45) port. Take a 1 ft 22 AWG 3 A USB-A male 2-wire pigtail (a second-hand unit may lack the kit cable) and crimp an XHP-2 housing onto its bare ends: XH pin 1 `+5V_SENS` to red, pin 2 GND to black. Then plug the USB-A end into the Mapper's "5V DC" socket. Only USB pins 1 (VBUS) and 4 (GND) are used; no data lines.
- Not from the Pi USB ports: without a USB-PD 5 A supply the Pi limits USB to 600 mA total (1.6 A shared with `usb_max_current_enable=1`), and the Pi's own regulator is already fully used by the Pi. The raw 2S battery (6-8.4 V) is in the voltage range but ESC/motor noise breaks the ripple limit; regulate.
- The pigtail is electrically sufficient (3 A rating vs 1.6 A start-up; ~0.6 m round trip x 53 mohm/m = ~32 mohm, ~50 mV drop at 1.6 A, so ~4.95 V at the Mapper, above the 4.8 V minimum).
- Before first connection (power off), with a multimeter: (1) check the pigtail colors against the plug, since cheap pigtails sometimes swap them: continuity from USB pin 1 (VBUS) to red and pin 4 (GND) to black; (2) with the Mapper unpowered and the pigtail unplugged, measure across the Mapper socket's pins 1 and 4 to confirm the port is not sourcing voltage.
- First power-up: if you have a bench supply, set 5.0 V with about a 2 A current limit. Expect about 1.5 A at start-up falling to about 0.75 A, and the head spinning within about 40 s. Then move the connection to `+5V_SENS`.
- Feed 5 V only. The datasheet allows up to 12 V, but we stay at the USB/`+5V_SENS` level. Never power it from a Pi USB port, and never straight from the 2S pack (ripple must be <= 50 mV).
- This socket is a power input only, not a USB data port.
- Mounting: M2.5 bottom screws no longer than 6 mm, tilt within +-3 deg, <= 2 m/s while mapping, the arrow on the cap is +X (forward).
- Allow ~40 s after power-up until it spins steadily.

**Networking (novice notes).** A Wi-Fi radio is either a *station* (joins someone else's network) or an *access point* (AP, offers one). The Mapper is an AP named `SLAMWARE-xxxxxx` at 192.168.11.1 (bench-confirmed: `nc -vz 192.168.11.1 1445` succeeded on this unit; the `opensw` default of 192.168.11.11 does not apply). The Pi's `wlan0` joins it as a station; at the lab `eth0` stays on the LAN. The *default route* is where the Pi sends traffic for any address it has no specific route to (the internet). The Mapper network has no internet, so it must not win the default route at the lab, or `apt`, `docker pull` and SSH-by-name break.

The tool is a *route metric*: a priority number on a default route, lowest wins. We give `eth0` 100 and `wlan0` 600 (whichever SSID it is on). Lab: both exist, `eth0` (100) wins, and the Mapper's 192.168.11.0/24 subnet is still reached over `wlan0`. Home: no cable, so `wlan0` is the only default route and home internet works. (Without `eth0` at the lab the only default is via the Mapper, which has no internet; harmless while driving.)

Netplan merges every `/etc/netplan/*.yaml` file *per interface*, so settings in one file apply to that interface for all SSIDs. This is why dropping routes/DNS on `wlan0` (an earlier version of this doc) also killed internet on the home Wi-Fi. Use a separate file `/etc/netplan/60-mapper.yaml` (`sudo chmod 600` it). It only adds metrics and the Mapper SSID; DHCP and the home SSID stay in `50-cloud-init.yaml` (cloud-init may regenerate that file, ours is untouched):

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4-overrides: {route-metric: 100}   # lab LAN wins when cabled
      dhcp6-overrides: {route-metric: 100}   # must equal dhcp4 (eth0 has dhcp6: true in 50-cloud-init)
  wifis:
    wlan0:
      dhcp4-overrides: {route-metric: 600}   # any Wi-Fi (home or Mapper) loses to eth0
      dhcp6-overrides: {route-metric: 600}
      access-points:
        "SLAMWARE-D22981": {}                # this unit's SSID; yours: label or laptop Wi-Fi list (open; add password: if set)
```

```sh
sudo chmod 600 /etc/netplan/60-mapper.yaml
sudo netplan try
```

`netplan try` applies the config and reverts by itself after 120 s unless you press Enter, so a mistake cannot lock you out for good. Over Wi-Fi SSH (home) prefer applying at the lab over Ethernet. If it errors `networkd requires that route-metric has the same value in both dhcp4_overrides and dhcp6_overrides`, the merged config has DHCPv6 on that interface (cloud-init sets `dhcp6: true` on `eth0`) without a matching `dhcp6-overrides`; that is why both are set. A `netplan-ovs-cleanup.service changed on disk` warning is harmless; `sudo systemctl daemon-reload` clears it.

Checks (all read-only). Merged config, works before applying (`netplan get` needs a key path; a bare name prints `null`). Expect eth0: dhcp4, dhcp6, optional, both overrides 100; wlan0: both SSIDs, regulatory-domain, 600:

```sh
sudo netplan get ethernets.eth0
sudo netplan get wifis.wlan0
```

What networkd actually uses (100 for eth0, 600 for wlan0):

```sh
grep -H RouteMetric /run/systemd/network/10-netplan-*.network
```

Lab (cable in, Mapper on):

```sh
ip route show default
networkctl status wlan0
nc -vz 192.168.11.1 1445
ping -c1 ubuntu.com
```

Expect: default via eth0 metric 100 listed first (wlan0 600 may follow), wlan0 on `SLAMWARE-...` with a 192.168.11.x address, `succeeded`, ping works. Slow DNS at the lab: `resolvectl status` shows whether the Mapper's DHCP offered a DNS server.

Home (no Mapper):

```sh
ip route show default
ping -c1 ubuntu.com
```

Expect: default via wlan0 only, ping works.

**One radio, one network.** With the home SSID in range, wpa_supplicant has no priority between saved SSIDs and stays on the current one; at the lab only the Mapper is in range, so it joins automatically. To switch by hand: `sudo wpa_cli -i wlan0 list_networks`, then `sudo wpa_cli -i wlan0 select_network <id>` (SSH over Wi-Fi drops). Switch back with `select_network <home id>` and `sudo wpa_cli -i wlan0 enable_network all`.

**Pi doesn't join the Mapper Wi-Fi.** In order:

1. Placeholder still present? A leftover `SLAMWARE-XXXXXX` makes wpa_supplicant chase a network that does not exist (wlan0 no-carrier, "Network is unreachable"):
   ```sh
   sudo netplan get wifis.wlan0.access-points
   sudo sed -i 's/SLAMWARE-XXXXXX/<real SSID>/' /etc/netplan/60-mapper.yaml
   sudo netplan apply
   ```
   (use `netplan try` instead of `apply` when on Wi-Fi SSH).
2. Which network is it on? `networkctl status wlan0` (see "one radio, one network" above).
3. Is the AP visible? Check frequency and signal; for 5 GHz also `iw reg get` should show US:
   ```sh
   sudo wpa_cli -i wlan0 scan
   sudo wpa_cli -i wlan0 scan_results | grep -i slamware
   ```
4. Client log, look for `CTRL-EVENT-CONNECTED` and association attempts:
   ```sh
   journalctl -u netplan-wpa-wlan0 -b
   ```
5. Force it: `sudo wpa_cli -i wlan0 select_network <id>` (ids from `list_networks`); revert as above.
6. Joined but no IP (DHCP):
   ```sh
   journalctl -u systemd-networkd -b | grep wlan0
   ```

- Live tests: the only radio is busy, so admin SSH from the laptop also goes over the Mapper AP: join the laptop to the same `SLAMWARE-xxxxxx` network and SSH to the Pi's address on it (`ip -4 addr show wlan0`).
- Fallback: cable the Mapper to the Pi's Ethernet (static IP on the Pi in the Mapper's subnet) and set `MAPPER_HOST=<mapper ip>` in the environment of the `drivers` service (compose default 192.168.11.1; not in `.env`, it is not a secret).

**Bandwidth.** One scan is ~930 points x 12 B = ~11 KB raw, ~15 KB base64. At 10-20 Hz that is 1.2-2.4 Mbit/s; with pose, IMU at 50 Hz and the map at ~0.5 Hz the total stays under 5 Mbit/s, far below what 802.11n/ac gives. The real cost is jitter (5-50 ms spikes) and dropouts, so messages are stamped on receive, gaps beyond the timeout are stale (diagnostics `mapper_driver: link`) and the lidar is **not** in the stop path (supervisor/ESP32 failsafe are unaffected).

**Step 1: agent-run acceptance (`make lidar-hw-test`).** Before the manual steps below, Claude Code on the Pi (or you) runs `make drivers-stop && make lidar-hw-test` with the car stationary and ESC power off. It launches its own `mapper_driver` against the physical Mapper (read-only, getters only) and checks link, scan, IMU (quaternion provided; acc units / gyro at rest are NA when the device does not provide them), pose drift and pose yaw rate at rest, map and TF against `rccar_drivers/hw_criteria.py`; PASS/FAIL/NA table on stdout (NA does not fail the run), JSON in `logs/hw_test_lidar_<UTC>.json`. It leaves `drivers` stopped; `make drivers-start` is a hardware restart and needs your approval (the guard hook asks). Rules: `.claude/rules/hw-testing.md`.

**Viewing: `make viz`.** Runs foxglove_bridge (binary, handles LaserScan/OccupancyGrid well; rosbridge is JSON and slow). It binds to `127.0.0.1` only: a websocket has no login, so binding to the Pi's LAN address would let anyone on the network read the feed. On localhost only something already on the Pi can connect, and SSH carries the rest. In VS Code Remote-SSH the **Ports** tab forwards 8765 automatically (add it if not). On the laptop open Foxglove (app.foxglove.dev or desktop) or Lichtblick, choose "Foxglove WebSocket", `ws://localhost:8765`, add a 3D panel with fixed frame `map` and enable `/rccar/lidar/scan`, `/rccar/mapper/map`, `/tf`. Served: `/rccar/*`, `/tf`, `/tf_static`, `/diagnostics`, `/robot_description`. Override: `ros2 launch rccar_bringup viz.launch.py port:=9000`. Troubleshooting: the bridge (foxglove_bridge 3.6.0, SDK based) accepts the websocket subprotocol `foxglove.sdk.v1` and rejects the legacy `foxglove.websocket.v1`; it logs `Dropping client 127.0.0.1:<port>: handshake failed` for a plain HTTP request (opening http://localhost:8765 in a browser, a port probe) and for a viewer that offers only `foxglove.websocket.v1` or no subprotocol (HTTP 400 `Missing expected sec-websocket-protocol header`). Port probes from VS Code are harmless; if the viewer never connects, update it to a version that offers `foxglove.sdk.v1`.

The Foxglove "Infinity invalid values" warning on `/rccar/lidar/scan` is expected (+inf = no return per REP-117); set the scan's Color mode to Flat and Point size to about 4.

**Topics.** See `.claude/rules/ros2.md`. Scan/IMU/pose are best effort (~10/50/10 Hz); the map is reliable + transient_local (~0.5 Hz). Bench-TBD parameters of `mapper_driver`: `scan_angle_sign`, `map_transpose` (`map_free_is_high` is bench-confirmed `false`: cells 0 unknown, 1..127 free, 128..255 occupied, 2026-11-02); IMU `linear_acceleration` is raw and flagged not provided (covariance[0] = -1) unless `imu_trust_acc:=true`; the URDF mount offsets in `rccar_description` are unmeasured until you measure them on the car.

**IMU feed: `make lidar-imu`.** Read-only, stack up. The Mapper (fw 2.6.0_dev) exports only an orientation, no rates, so most columns come from the SLAM pose. One line per sample (at most ~10/s): Pi time, `heading` (SLAM pose yaw), `imu_heading` (IMU quaternion yaw, cross-check), `yaw_rate` (pose, deg/s), `speed` (successive poses), `acc_long` (d(speed)/dt, pose), `acc_lat` (speed x yaw rate, pose), IMU rate, then `imu_gyro` / `imu_acc` (raw IMU values, `n/a` while the Mapper does not provide them). `JUMP` marks a pose jump above 0.5 rad (relocalization or loop closure): the estimator restarts. Limits: pose-derived values are 10 Hz with ~100 ms latency, smoothed (~0.3 s window + EMA) and can jump on loop closure; for logging and estimation only, not control. True yaw rate and body acceleration need a dedicated IMU. Each run appends JSON lines (same keys, plus `source` = pose/imu per key and `jump`) to `logs/lidar_imu_<UTC>.jsonl` (override dir: parameter `log_dir` / env `RCCAR_LOG_DIR`; unwritable => warning, printing continues). Prints `waiting for /rccar/lidar/imu (Mapper powered + on Wi-Fi? ...)` when nothing arrives for 2 s. Check the Mapper link with `make car-logs`.

**Debug data (for you and for Claude Code on the Pi): `make lidar-snapshot`, `make lidar-record`.** Both only subscribe (no publishing, no service calls), run with the stack up and leave the `drivers` service running.
- `make lidar-snapshot` listens for ~3 s and writes `logs/lidar_snapshot_<UTC>/`: `map.png` (white free, black occupied, grey unknown, red = current scan endpoints, blue dot + tick = Mapper pose/heading; +X right, +Y up), `scan.json`, `pose.json`, `imu.json`, `map_meta.json`, `diagnostics.json`, `summary.json` and `summary.txt` (topic rates, scan statistics, map size, link health, **scan-map agreement**: the fraction of scan endpoints that land on a wall of the map; low when the scan is mirrored (`scan_angle_sign`), the pose is wrong or the unit is moving). Exit 1 + `missing: ...` when scan, pose or map did not arrive. Claude Code opens `map.png` as an image.
- `make lidar-record SECS=30` (1..600 s) records `/rccar/lidar/scan`, `/rccar/lidar/imu`, `/rccar/mapper/pose`, `/rccar/mapper/map`, `/tf`, `/tf_static`, `/diagnostics`, `/robot_description` to `logs/lidar_bag_<UTC>/` (rosbag2, mcap), then prints `ros2 bag info`. Open the `.mcap` in Foxglove ("Open local file") or read it with `rosbag2_py` for offline sensor-fusion work. About 50 KB/s.
- `logs/` is gitignored on purpose: a map or bag is a floor plan of wherever the car was (this repo is public). Share a dataset deliberately (e.g. a release asset), never by committing it.

## 8. USB disconnect

If you unplug the USB cable and plug it in again (or the ESP32 resets its USB serial device), the device node passed into the `mcu-agent` container goes stale. Run:

```sh
make car-down && make car-up
```

## 9. Shutdown

In the teleop terminal, press `x` (disarm, quit, hint). Then, in the SSH shell, run:

```sh
make car-shutdown   # disarm via /supervisor/disarm, compose down, asks, then sudo poweroff
```

Then switch the ESC off and unplug the USB cable. Containers stay unprivileged. `poweroff` runs on the host in your shell.

## Phase 2 bench checklist (user-run)

This procedure verified phase 2 (bench-verified 2026-10-29). Run it again after firmware or supervisor changes. It does hardware fault injection. **An agent must never run it.** Keep the wheels off the ground. Keep the ESC power switch within reach. Paste the outputs into the PR.

1. Run `make fw-image ros-image config`, `make flash` and `make car-up`. Make sure that `make car-ps` shows `mcu-agent` and `core` healthy.
2. Run `ros2 topic echo /rccar/mcu/telemetry` (from `make ros-shell`). Make sure that it shows telemetry with `armed: false`.
3. Run `make test`. Make sure that it passes (steering sweep + failsafe, motor off).
4. Run `make teleop`. Make sure of these results: the arrow keys drive, space brakes, and `d` disarms. After a brake or a disarm, the supervisor refuses motion until you press `a`. The supervisor refuses `a` if throttle is not 0. Make sure that `make car-logs` shows `mcu_bridge` pushing tuning at startup (`MCU reachable after activation`).
5. Drive slowly and kill `core` (`docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated kill core`). Make sure that the ESP32 failsafe stops the car within `cmd_timeout_ms`.
6. Drive slowly and unplug the USB cable. Make sure of these results: the ESP32 failsafe stops the car. After you plug the cable in again, `mcu-agent` reconnects and `core` stays healthy. The supervisor shows a latched incident (`mcu rebooted`/failsafe) that needs `a`. The device node passed to the container goes stale when you plug the cable in again. Run `make car-down && make car-up` to recover (expected behaviour, see section 8).
7. Drive slowly and kill teleop (close the terminal). Make sure that the supervisor stops the car.
8. Run `make car-shutdown`. Make sure that it disarms, stops the stack and powers off after you confirm.
9. Run `docker compose logs`. Make sure that the logs stay at the limit of 3 x 10 MB for each container.

## Optional

```sh
make monitor    # raw serial monitor in Docker (stack must be down; Ctrl+C to exit)
make models     # validates models/manifest.yaml; download not implemented yet
make ros-test   # build the test image + colcon test (no hardware)
```

Roadmap: [docker_ros_plan.md](docker_ros_plan.md).
