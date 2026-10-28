# Setup: zero to driving

Assumptions are marked **Assume:**. If one is false, fix it before continuing.

## 1. Host

**Assume:** Raspberry Pi 5 with Ubuntu 24.04 (a laptop works for firmware work), with `git`, `make`, **Docker Engine + compose plugin + buildx**, and **Python ≥ 3.12** as `python3` (host-side only for `make config` and `make unit`; everything else runs in Docker). Internet access to Docker Hub, `packages.ros.org`, `raw.githubusercontent.com` (rosdep), pypi.org and registry.platformio.org.

```sh
sudo usermod -aG docker,dialout $USER   # then log out and back in
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/gvo27/racecar && cd racecar    # one clone per user; collaborators work via GitHub PRs
make install-host                       # sudo: udev rule -> /dev/rccar-esp32, systemd unit rccar.service (enabled)
cp .env.example .env                    # set TZ, ROS_DOMAIN_ID (default 0), PLATFORM=pi5
make config ros-image fw-image          # render deploy/car/.env.generated, build the ROS image, build the firmware toolchain image
```

- The repo lives at `~/ros2_ws/src/racecar` on the Pi. The containers mount it at `/ws/src/racecar` (read-only, plus `tuning.toml` and `logs/` read-write), so calibration writes your working copy. One clone per user: nobody edits another user's clone.
- `make install-host` prints each step. It installs `deploy/car/99-rccar.rules` (CH343 `1a86:55d3` -> `/dev/rccar-esp32`, group `dialout`) and renders `deploy/car/rccar.service` with this clone's path and your user. Unplug and replug the USB cable once afterwards. The unit starts the stack at boot with whatever images are already built; deploys stay explicit (`make car-pull && make car-up`).
- `make config` reads `.env` and `tuning.toml [platform.$PLATFORM]` (today: `esp32_device`, `arch`) and writes the gitignored `deploy/car/.env.generated`. It fails with a hint if `.env` is missing.
- `make ros-image` runs `rosdep` against `package.xml`, so it needs `packages.ros.org` and `raw.githubusercontent.com`.
- Optional, laptop or dev machine: `make setup` creates `.venv` for `make unit` and the legacy tools.

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
make unit                       # host Python unit tests, no hardware (after make setup)
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
- Time sync is `rmw_uros_sync_session`; the legacy `TIME` command is not available in micro-ROS mode.

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

After a brake or disarm the supervisor refuses motion until you press `a` (with throttle at neutral). The ESP32 failsafe disarms on its own if drive commands stop. **The software stop is not safety-rated: the ESC power switch is the independent hardware stop.**

## 7. Test, calibrate, tune (ROS)

The stack must be running (`make car-up`). The tools run in the `tools` container and call the `mcu_bridge` services.

```sh
make test            # steering sweep + failsafe check, motor stays off, never arms
make calibrate       # find center / left / right, measure maxdeg, `save`, `q`
git diff tuning.toml # calibrate wrote the [steering.calibration] values into your clone
make tune            # push tuning.toml to the ESP32 and save it to flash
```

`mcu_bridge` also pushes `tuning.toml` to the ESP32 RAM every time the firmware reports READY. There is no ROS equivalent of the legacy throttle test (`legacy-test-throttle`).

### Tuning loop

1. Edit `tuning.toml`.
2. `make tune` (or `ros2 service call /mcu_bridge/push_tuning std_srvs/srv/Trigger` from `make ros-shell`).
3. `make teleop` to drive.
4. Commit `tuning.toml` when it feels right.

## 8. Legacy fallback (ASCII protocol)

Kept until the bench parity test passes, then removed in a follow-up PR.

```sh
make setup                              # .venv + deps (needs pypi.org)
make car-down
make flash FW_ENV=esp32s3_ascii         # ASCII firmware, same actuator core
make legacy-detect                      # expect: CH343 1a86:55d3 marked "use this one"
make legacy-ping legacy-sync-time
make legacy-test legacy-calibrate legacy-tune legacy-teleop legacy-session
```

Back to ROS: `make flash` (default env), then `make car-up`.

## 9. Shutdown

In the teleop terminal press `x` (disarm, quit, hint), then in the SSH shell:

```sh
make car-shutdown   # disarm via /supervisor/disarm, compose down, asks, then sudo poweroff
```

Then switch the ESC off and unplug USB. Containers stay unprivileged; `poweroff` runs on the host in your shell.

## Phase 2 bench checklist (user-run)

Hardware fault injection. **Never run by an agent.** Wheels off the ground, ESC power switch within reach. Paste outputs into the PR.

1. `make config ros-image fw-image`, `make flash`, `make car-up`; `make car-ps` shows `mcu-agent` and `core` healthy.
2. `ros2 topic echo /rccar/mcu/telemetry` (from `make ros-shell`) shows telemetry with `armed: false`.
3. `make test` passes (steering sweep + failsafe, motor off).
4. `make teleop`: arrow keys drive; space brakes; `d` disarms; after either, motion is refused until `a`; `a` with throttle not at 0 is refused.
5. Kill `core` (`docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated kill core`) while driving slowly: the ESP32 failsafe stops the car within `cmd_timeout_ms`.
6. Unplug the USB cable while driving slowly: the ESP32 failsafe stops the car; after replugging, `mcu-agent` reconnects and `core` stays healthy.
7. Kill teleop (close the terminal) while driving slowly: the supervisor stops the car.
8. `make car-shutdown` disarms, stops the stack and powers off after confirmation.
9. Fallback: `make flash FW_ENV=esp32s3_ascii`, then `make legacy-detect legacy-test` work; reflash the default env afterwards.
10. `docker compose logs`: logs stay capped at 3 x 10 MB per container.

## Optional

```sh
make monitor    # raw serial monitor in Docker (stack must be down; Ctrl+C to exit)
make models     # validates models/manifest.yaml; download not implemented yet
make ros-test   # build the test image + colcon test (no hardware)
```

Roadmap: [docker_ros_plan.md](docker_ros_plan.md).
