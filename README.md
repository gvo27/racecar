# racecar

A 1:10 Tamiya TT-02 built into a self-driving research platform on a two-layer compute stack: a Raspberry Pi 5 for perception, sensor fusion, semantic SLAM and racing-line optimization, and an ESP32-S3 for hard-real-time control. This repo holds everything that runs on the car: PWM actuation, failsafes, the host-to-MCU protocol, runtime tuning, logging and the Docker/ROS 2 deployment. Setup: [docs/setup.md](docs/setup.md).

## Compute stack

| Layer | Hardware | Role | Status |
| --- | --- | --- | --- |
| High level | Raspberry Pi 5 | autonomy stack: ROS 2 Jazzy in Docker (`deploy/car/`), supervisor + micro-ROS agent, sends `DriveCmd` (heading, throttle) | phase 2 complete (bench-verified); phase 4 rangefinder: compile-only, not bench-verified |
| Real time | ESP32-S3-N16R8 | hardware PWM to servo/ESC, failsafe, telemetry; micro-ROS client over UART0 | this repo, `firmware/esp32/` (env `esp32s3`, micro-ROS) |

## Current inventory

Source: [`docs/datasheets/components_list.xlsx`](docs/datasheets/components_list.xlsx)

| Component | Item | Documentation |
| --- | --- | --- |
| microcontroller | ESP32 S3 N16R8 | [user guide](https://github.com/microrobotics/ESP32-S3-N16R8/blob/main/ESP32-S3-N16R8_User_Guide.pdf) |
| chassis | Tamiya TT-02 | — |
| battery | 2S 7.4V 80C 5200mAh LiPo Battery Pack | — |
| computer | Raspberry Pi 5 | needs 5V, 5A |
| voltage regulator for rpi | Pololu D36V50F5 (5V 5.5A, 6-50V in) | [pololu.com/product/4091](https://www.pololu.com/product/4091), [archived](docs/datasheets/Pololu%20-%205V%2C%205.5A%20Step-Down%20Voltage%20Regulator%20D36V50F5.htm) |
| lidar | Garmin LIDAR-Lite v4 LED, part number 010-02022-00 | [archived PDF](docs/datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](docs/datasheets/rangefinder_lidar_lite_v4.md), [instructions](https://static.garmin.com/pumac/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf) (software name: rangefinder) |
| motor controller | THW-1060-BRUSHED | [thw-1060-brushed-esc.md](docs/datasheets/thw-1060-brushed-esc.md) |
| steering servo | DS3225MG | [ds3225_servo.md](docs/datasheets/ds3225_servo.md) |

## USB-C ports (ESP32-S3-N16R8)

| Port | Position | Connects to | Use |
| --- | --- | --- | --- |
| **COM** | right | CH343 USB-UART → UART0 (GPIO43/44) | **flashing** + host link (laptop now, Raspberry Pi later) |
| **USB** | left | native USB (GPIO19/20) | planned regulated power input. Not used for data |

Flash and talk to the board **only through COM**.

## Pin map (left header P1 only)

Source of truth: [`firmware/esp32/include/pins.h`](firmware/esp32/include/pins.h). Keep this table identical to it.

```
                ESP32-S3-N16R8   (top view, antenna up)
          P1 (LEFT header)
        ┌─────┬──────────────────────────────┐
  3V3   │  1  │ unused (sensors: own rail)   │
  3V3   │  2  │ unused                       │
  RST   │  3  │ ✗ do not use                 │
  GPIO4 │  4  │ ● STEER_PWM   → servo signal │
  GPIO5 │  5  │ ● THROTTLE_PWM→ ESC signal   │
  GPIO6 │  6  │ ○ BATT_LOW                   │
  GPIO7 │  7  │ ○ IMU_INT                    │
  GPIO15│  8  │ ○ ENC_A                      │
  GPIO16│  9  │ ○ ENC_B                      │
  GPIO17│ 10  │ · spare (UART1 TX)           │
  GPIO18│ 11  │ · spare (UART1 RX)           │
  GPIO8 │ 12  │ ● I2C SDA → rangefinder 3    │
  GPIO3 │ 13  │ ✗ strapping                  │
  GPIO46│ 14  │ ✗ strapping                  │
  GPIO9 │ 15  │ ● I2C SCL → rangefinder 4    │
  GPIO10│ 16  │ · spare                      │
  GPIO11│ 17  │ · spare                      │
  GPIO12│ 18  │ · spare                      │
  GPIO13│ 19  │ · spare                      │
  GPIO14│ 20  │ · spare                      │
  5V    │ 21  │ input only - leave unwired   │
  G     │ 22  │ ■ COMMON GROUND (ESC/servo)  │
        └─────┴──────────────────────────────┘
          [USB] left        [COM] right ← flash / host
   ● active   ○ reserved (no code yet)   · spare   ✗ do not use   ■ ground
```

| P1 # | GPIO | Function | Status |
| --- | --- | --- | --- |
| 4 | 4 | **STEER_PWM** → DS3225 signal | **active** |
| 5 | 5 | **THROTTLE_PWM** → ESC signal | **active** |
| 6 | 6 | *BATT_LOW* (hi/low input) | *reserved* |
| 7 | 7 | *IMU_INT* | *reserved* |
| 8 / 9 | 15 / 16 | *ENC_A / ENC_B* (shaft encoder) | *reserved* |
| 12 / 15 | 8 / 9 | **I2C SDA / SCL** → rangefinder (Garmin pin 3 / 4) | **active** |
| 10, 11, 16-20 | 17, 18, 10, 11, 12-14 | spare | spare |
| 3, 13, 14 | RST, 3, 46 | ~~reset / strapping pins~~ | ~~do not use~~ |
| 22 | G | common ground | power |

Wire colours: signal = yellow/white, power = red, ground = black. Put a tape flag on the two active signal wires.

## Rangefinder wiring (Garmin LIDAR-Lite v4 LED)

Software name: *rangefinder*. Datasheet: [archived PDF](docs/datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](docs/datasheets/rangefinder_lidar_lite_v4.md). Power off while wiring.

| Garmin pin | Name | Wire | Connect to |
| --- | --- | --- | --- |
| 1 | VIN (5 V, 4.75-5.25 V) | red | regulated 5 V **sensor rail** (never ESP32 5V/3V3) |
| 2 | GND | black | common ground (P1-22) |
| 3 | I2C SDA | white or green (TBD) | GPIO8 (P1-12) |
| 4 | I2C SCL | white or green (TBD) | GPIO9 (P1-15) |
| 5-10 | GPIOA, GPIOB, nRF debug | n/a | leave unconnected |

- The sensor has internal 13 kOhm pull-ups to 3.3 V: no level shifter, no external pull-ups. Signals are 3.3 V max.
- Leave GPIOB (pin 6) unconnected: low at power-up starts the BLE bootloader.
- Status: driver compiled in CI, not yet bench-verified. Enable with `make mcu CMD="SENS rangefinder"`, watch with `make rangefinder`.

## Make commands

Run `make help` for the live list. Setup: [docs/setup.md](docs/setup.md). ROS tools (`teleop`, `calibrate`, `tune`, `test`, `mcu`, `rangefinder`) need the stack running (`make car-up`).

**Car stack (ROS 2 + micro-ROS in Docker)**

| Target | What it does |
| --- | --- |
| `config` | render `deploy/car/.env.generated` from `.env` + `tuning.toml [platform.$PLATFORM]` (runs in the firmware image; needs `make fw-image` first) |
| `install-host` | sudo: install the udev rule (`/dev/rccar-esp32`) and the `rccar.service` systemd unit |
| `ros-image` | build the ROS 2 image (`docker/ros.Dockerfile` → `rccar-ros:local`) |
| `ros-test` | build the test image, `colcon test` + `test-result` (no hardware); `ros-test-image` / `ros-test-run` are its two halves (`unit-run` runs `deploy/tests` in the same image) |
| `car-up` / `car-down` | start / stop `mcu-agent` + `core` (docker compose) |
| `car-ps` / `car-logs` | health / follow logs |
| `car-pull` | pull the pinned third-party images |
| `car-shutdown` | disarm via the supervisor, stop the stack, then `sudo poweroff` (asks first) |
| `ros-shell` | shell in the tools container (ROS sourced) |

**ROS tools (stack running)**

| Target | What it does |
| --- | --- |
| `teleop` | SSH keyboard driving through the supervisor |
| `calibrate` | interactive servo center/left/right calibration, writes `tuning.toml` |
| `tune` | push `tuning.toml` to the ESP32 and save it to flash |
| `test` | steering sweep + failsafe check (motor stays off, never arms) |
| `rangefinder` | live terminal feed of `/rccar/rangefinder/range` (MCU timestamp, Pi receive time, range m/cm, rate); enable with `make mcu CMD="SENS rangefinder"` |
| `mcu CMD="GET"` | send one `McuCommand` to the ESP32 (`GET`, `INFO`, `PING`, `SET key val`, ...) and print the reply |

**Firmware (Docker; `FW_ENV=esp32s3`)**

| Target | What it does |
| --- | --- |
| `fw-image` | build the firmware toolchain image |
| `build` | clean `.pio/build` (keeps the slow micro-ROS `libdeps` cache) + compile |
| `flash` | compile + upload over COM (stack must be down, ESC off) |
| `monitor` | raw serial monitor (stack must be down) |
| `clean` | delete all of `firmware/esp32/.pio` (incl. `libdeps`) |
| `compiledb` | `compile_commands.json` for clangd |

**Host / dev**

| Target | What it does |
| --- | --- |
| `setup` | check host prerequisites (git, make, docker), build the firmware and ROS images |
| `unit` | `deploy/tests` (pytest) in the ROS test image, no hardware |
| `check-dev` | check optional LSP binaries for Claude Code |
| `models` | print `models/manifest.yaml` (download not implemented yet) |

## Power rules

1. **The ESP32 powers nothing.** It only outputs actuator signals and talks to the host. Sensors run from a separate regulated rail that shares ground with the ESP32 and keeps all signals at ≤ 3.3 V.
2. Servo power comes from the ESC's built-in 6 V / 3 A BEC (red wire of the throttle lead), connected by Y-harness. **Never connect it to the ESP32**, and don't run servo current through the breadboard.
3. The ESP32, ESC and servo grounds must all be connected (P1-22).

## Power-up sequence

1. ESC **off**. Wheels off the ground.
2. USB cable into **COM**. The ESP32 boots and sends neutral (1500 µs) on both channels. Then `make car-up`.
3. ESC **on**. It beeps and learns neutral.
4. Power down in reverse: ESC off first. **Always switch the ESC off before `make flash`.**

## Repo layout

```
rccar_msgs/        interface contract: DriveCmd, Telemetry, McuEvent, SupervisorState, McuCommand, Reset, ...
rccar_supervisor/  safety authority: arbitration, latched stop, sole publisher of /rccar/mcu/drive
rccar_mcu_bridge/  lifecycle node: typed services over McuCommand, tuning push, FIRMWARE_KEYS
rccar_teleop/      admin keyboard teleop (SSH)
rccar_calibration/ calibrate, bench_test, tune
rccar_bringup/     launch (car.launch.py), tuning.toml -> ROS parameters
firmware/esp32/    ESP32 firmware (PlatformIO): src/main.cpp, include/pins.h, extra_packages/rccar_msgs (synced copy), rccar.meta
deploy/car/        compose.yaml, 99-rccar.rules (udev), rccar.service (systemd); deploy/render_env.py (make config)
docker/            firmware.Dockerfile, ros.Dockerfile (+ entrypoint.sh, ros-test.sh)
models/            manifest.yaml (weights are not in git), cache/ gitignored
repos/             rccar.repos (third-party ROS sources, vcstool)
tuning.toml        all runtime tuning + [platform.*]; pushed to the ESP32 by mcu_bridge
.env.example       template for the gitignored .env
logs/              session history (*.jsonl, gitignored)
docs/              setup.md, docker_ros_plan.md, proposal, datasheets/
.claude/           CLAUDE.md, layout.yaml, rules/, agents/
.github/           workflows/{firmware,ros}.yml
Makefile           every command (make help)
```

Bench checklist (the procedure used to verify phase 2): [docs/setup.md](docs/setup.md#phase-2-bench-checklist-user-run). Roadmap: [docs/docker_ros_plan.md](docs/docker_ros_plan.md). Firmware design: [docs/esp32-firmware-proposal.md](docs/esp32-firmware-proposal.md).
