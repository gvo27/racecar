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
make fw-image ros-image config          # build both images, then render deploy/car/.env.generated (config runs in the firmware image)
```

- The repo is at `~/ros2_ws/src/racecar` on the Pi. The containers mount it at `/ws/src/racecar` (read-only, plus `tuning.toml` and `logs/` read-write), so calibration writes your working copy. Use one clone for each user. Nobody edits the clone of another user.
- `make install-host` prints each step. It installs `deploy/car/99-rccar.rules` (CH343 `1a86:55d3` -> `/dev/rccar-esp32`, group `dialout`). It renders `deploy/car/rccar.service` with the path of this clone and your user. Afterwards, unplug the USB cable and plug it in again one time. The unit starts the stack at boot with the images that are already built. Deploys stay explicit (`make car-pull && make car-up`).
- `make setup` checks the host prerequisites and builds both images (`fw-image`, `ros-image`).
- `make config` runs `deploy/render_env.py` inside the ROS image, so it needs `make ros-image` first. It reads `.env` and `tuning.toml [platform.$PLATFORM]` (today: `esp32_device`, `arch`). It writes the gitignored `deploy/car/.env.generated`. If `.env` is missing, it fails with a hint.
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
