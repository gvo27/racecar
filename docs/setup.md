# Setup: zero to driving

Assumptions are marked **Assume:**. If one is false, fix it before continuing.

## 1. Host

**Assume:** Raspberry Pi 5 with Ubuntu 24.04 (a laptop works for firmware work), with `git`, `make` and **Docker Engine + compose plugin + buildx**. Nothing else is installed on the host: Python, PlatformIO and ROS all run in Docker. Internet access to Docker Hub, `packages.ros.org`, `raw.githubusercontent.com` (rosdep), pypi.org and registry.platformio.org.

```sh
sudo usermod -aG docker,dialout $USER   # then log out and back in
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/gvo27/racecar && cd racecar    # one clone per user; collaborators work via GitHub PRs
make install-host                       # sudo: udev rule -> /dev/rccar-esp32, systemd unit rccar.service (enabled)
cp .env.example .env                    # set TZ, ROS_DOMAIN_ID (default 0), PLATFORM=pi5
make fw-image ros-image config          # build both images, then render deploy/car/.env.generated (config runs in the firmware image)
```

- The repo lives at `~/ros2_ws/src/racecar` on the Pi. The containers mount it at `/ws/src/racecar` (read-only, plus `tuning.toml` and `logs/` read-write), so calibration writes your working copy. One clone per user: nobody edits another user's clone.
- `make install-host` prints each step. It installs `deploy/car/99-rccar.rules` (CH343 `1a86:55d3` -> `/dev/rccar-esp32`, group `dialout`) and renders `deploy/car/rccar.service` with this clone's path and your user. Unplug and replug the USB cable once afterwards. The unit starts the stack at boot with whatever images are already built; deploys stay explicit (`make car-pull && make car-up`).
- `make setup` checks the host prerequisites and builds both images (`fw-image`, `ros-image`).
- `make config` (runs `deploy/render_env.py` inside the ROS image, so it needs `make ros-image` first) reads `.env` and `tuning.toml [platform.$PLATFORM]` (today: `esp32_device`, `arch`) and writes the gitignored `deploy/car/.env.generated`. It fails with a hint if `.env` is missing.
- `make ros-image` runs `rosdep` against `package.xml`, so it needs `packages.ros.org` and `raw.githubusercontent.com`.

**Claude Code (optional):** open the repo in Claude Code and trust the folder. It then asks you to install the plugins in `.claude/settings.json` and to approve the Context7 MCP server in `.mcp.json`.

| Plugin / server | Use |
| --- | --- |
| `superpowers` | brainstorm → plan → TDD → review workflow |
| Context7 (MCP) | current library docs (ROS 2, ESP-IDF, arduino-esp32, PlatformIO) |
| `pyright-lsp` | Python diagnostics, needs `pyright-langserver` on PATH |
| `clangd-lsp` | firmware C/C++ diagnostics, needs `clangd` on PATH + `make compiledb` |
| `embedded-skills` | firmware architecture, RTOS, ISR design |
| `ros2-engineering` | micro-ROS, ros2_control, Nav2, perception; advisory hooks (`ROS2_SKILL_DISABLE_HOOKS=all` turns them off) |

```sh
sudo apt install clangd         # firmware LSP
pipx install pyright            # Python LSP (or: npm install -g pyright)
make check-dev                  # both must say OK
make compiledb                  # firmware/esp32/compile_commands.json for clangd
make unit                       # deploy/tests in the ROS test image, no hardware
```

## 2. Wiring (power off)

**Assume:** ESC switch **off**, battery connected to the ESC, car on a stand with the wheels off the ground.

1. Servo signal → P1-4 (GPIO4). ESC throttle-lead signal → P1-5 (GPIO5).
2. ESC black and servo black → P1-22 (G), the common ground.
3. ESC red (6 V) → servo red only, through a Y-harness. **Nothing red touches the ESP32.**

See the pin map in the [README](../README.md#pin-map-left-header-p1-only).

## 3. Connect

**Assume:** a USB-C cable that carries **data**, plugged into the board's **right** USB-C port, labelled **COM**. The left port, **USB**, is reserved for future regulated power. Never flash through it.

```sh
ls -l /dev/rccar-esp32     # the udev symlink exists once the board is plugged in (make install-host)
```

## 4. Flash (micro-ROS firmware)

**Assume:** the ESC is **off** and the car stack is **down** (`make car-down`; flash and monitor refuse while it holds the serial port).

```sh
make flash      # FW_ENV=esp32s3 (micro-ROS). Builds in Docker and uploads over COM.
```

- The first `make build` / `make flash` also builds the micro-ROS library into `firmware/esp32/.pio/libdeps` (git clone of ROS repos + colcon, about 10 minutes, needs network). `make build` and `make flash` only clean `.pio/build`, so later builds are fast. `make clean` deletes everything including `libdeps`.
- If the upload can't connect: hold **BOOT**, tap **RST**, release **BOOT**, then re-run.
- Time sync is `rmw_uros_sync_session`; the `TIME` command is not available over micro-ROS.

## 5. Start the car stack

```sh
make car-up     # config + docker compose up -d: mcu-agent + core (supervisor + mcu_bridge)
make car-ps     # both services must become "healthy"
make car-logs   # Ctrl+C to exit
```

Then switch the ESC **on** while the ESP32 is running. It beeps and learns 1500 µs as neutral. The car boots disarmed and nothing moves until you arm it.

## 6. Drive over SSH

```sh
ssh pi              # from the laptop
cd ~/ros2_ws/src/racecar && make teleop
```

Teleop runs in the SSH terminal and talks to the supervisor locally (`/rccar/cmd/admin`); ROS traffic never leaves the Pi.

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

After a brake or disarm the supervisor refuses motion until you press `a` (with throttle at neutral). After arming, the supervisor forwards throttle only once teleop has sent a neutral command (teleop does that automatically). The ESP32 failsafe disarms on its own if drive commands stop. **The software stop is not safety-rated: the ESC power switch is the independent hardware stop.**

## 7. Test, calibrate, tune (ROS)

The stack must be running (`make car-up`). The tools run in the `tools` container and call the `mcu_bridge` services.

```sh
make test            # steering sweep + failsafe check, motor stays off, never arms
make calibrate       # find center / left / right, measure maxdeg, `save`, `q`
git diff tuning.toml # calibrate wrote the [steering.calibration] values into your clone
make tune            # push tuning.toml to the ESP32 and save it to flash
```

`mcu_bridge` also pushes `tuning.toml` to the ESP32 RAM when it starts (once the ESP32 is reachable) and every time the firmware reports READY. There is no ROS throttle test.

Single commands to the ESP32 (stack up): `make mcu CMD="GET"`, `make mcu CMD="INFO"`, `make mcu CMD="SET gain 1.5"` (calls `/rccar/mcu/command`; `D` and `ARM` are refused: drive and arming go through the supervisor). `SET` changes RAM only and is overwritten by the next tuning push (on MCU READY); edit `tuning.toml` and `make tune` to persist.

### Tuning loop

1. Edit `tuning.toml`.
2. `make tune` (or `ros2 service call /mcu_bridge/push_tuning std_srvs/srv/Trigger` from `make ros-shell`).
3. `make teleop` to drive.
4. Commit `tuning.toml` when it feels right.

### Rangefinder

Wiring (power off): see [README "Rangefinder wiring"](../README.md#rangefinder-wiring-garmin-lidar-lite-v4-led); datasheet summary: [rangefinder_lidar_lite_v4.md](datasheets/rangefinder_lidar_lite_v4.md). Sensor 5 V comes from the sensor rail, never from the ESP32.

```sh
make mcu CMD="SENS rangefinder"   # read-only status + config line (stack up); publishing is on while driver = 1
make rangefinder                  # live feed: MCU timestamp, Pi receive time, range (m/cm), rate; Ctrl+C to exit
```

The first flash after this feature needs the micro-ROS library rebuilt (`rccar.meta` has 3 publishers): `make clean && make flash` once. `+inf` means the sensor reported its no-return value (`rf_no_return`); every other reading is published unchanged, so consumers must check `min_range`/`max_range` (REP-117). Disable the sensor with `make mcu CMD="SET rf_driver 0"` or `[rangefinder] driver = 0` + `make tune`. Bench checklists now live in each PR body ([`.github/pull_request_template.md`](../.github/pull_request_template.md)), not here.

**How I2C clocking works (for newcomers).** I2C uses two wires: SCL (clock) and SDA (data). The ESP32 is the bus master and is the only one that drives SCL. The sensor changes SDA only while SCL is low, and the receiver samples SDA while SCL is high, so data and clock stay in step in hardware; there is no software synchronisation to do. The timestamp on a range sample marks when the ESP32 finished reading it (converted to ROS time via `rmw_uros_sync_session`), not when the light left the sensor.

## 8. USB disconnect

After the USB cable is unplugged and replugged (or the ESP32 resets its USB serial device), the device node passed into the `mcu-agent` container goes stale. Run:

```sh
make car-down && make car-up
```

## 9. Shutdown

In the teleop terminal press `x` (disarm, quit, hint), then in the SSH shell:

```sh
make car-shutdown   # disarm via /supervisor/disarm, compose down, asks, then sudo poweroff
```

Then switch the ESC off and unplug USB. Containers stay unprivileged; `poweroff` runs on the host in your shell.

## Phase 2 bench checklist (user-run)

The procedure used to verify phase 2 (bench-verified 2026-10-29); rerun it after firmware or supervisor changes. Hardware fault injection. **Never run by an agent.** Wheels off the ground, ESC power switch within reach. Paste outputs into the PR.

1. `make fw-image ros-image config`, `make flash`, `make car-up`; `make car-ps` shows `mcu-agent` and `core` healthy.
2. `ros2 topic echo /rccar/mcu/telemetry` (from `make ros-shell`) shows telemetry with `armed: false`.
3. `make test` passes (steering sweep + failsafe, motor off).
4. `make teleop`: arrow keys drive; space brakes; `d` disarms; after either, motion is refused until `a`; `a` with throttle not at 0 is refused. `make car-logs` shows `mcu_bridge` pushing tuning at startup (`MCU reachable after activation`).
5. Kill `core` (`docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated kill core`) while driving slowly: the ESP32 failsafe stops the car within `cmd_timeout_ms`.
6. Unplug the USB cable while driving slowly: the ESP32 failsafe stops the car; after replugging, `mcu-agent` reconnects and `core` stays healthy, and the supervisor shows a latched incident (`mcu rebooted`/failsafe) that needs `a`. The device node passed to the container goes stale on replug: `make car-down && make car-up` recovers (expected behaviour, see section 8).
7. Kill teleop (close the terminal) while driving slowly: the supervisor stops the car.
8. `make car-shutdown` disarms, stops the stack and powers off after confirmation.
9. `docker compose logs`: logs stay capped at 3 x 10 MB per container.

## Optional

```sh
make monitor    # raw serial monitor in Docker (stack must be down; Ctrl+C to exit)
make models     # validates models/manifest.yaml; download not implemented yet
make ros-test   # build the test image + colcon test (no hardware)
```

Roadmap: [docker_ros_plan.md](docker_ros_plan.md).
