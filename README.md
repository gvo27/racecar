# racecar

This project turns a 1:10 Tamiya TT-02 into a self-driving research platform. It has a two-layer compute stack. A Raspberry Pi 5 does perception, sensor fusion, semantic SLAM and racing-line optimization. An ESP32-S3 does hard-real-time control. This repo holds everything that runs on the car: PWM actuation, failsafes, the host-to-ESP32 protocol, runtime tuning, logging and the Docker/ROS 2 deployment. Setup: [docs/setup.md](docs/setup.md).

## Compute stack

| Layer | Hardware | Role | Status |
| --- | --- | --- | --- |
| High level | Raspberry Pi 5 | autonomy stack: ROS 2 Jazzy in Docker (`deploy/car/`), supervisor + micro-ROS agent, sends `DriveCmd` (heading, throttle) | phase 2 complete (bench-verified); phase 4 rangefinder + lidar (Slamtec Mapper, `make viz`): compile-only, not bench-verified |
| Real time | ESP32-S3-N16R8 | hardware PWM to servo/ESC, failsafe, telemetry; micro-ROS client over UART0 | this repo, `firmware/esp32/` (env `esp32s3`, micro-ROS) |

## Current inventory

| Component | Item | Documentation |
| --- | --- | --- |
| chassis | Tamiya TT-02 | — |
| battery | 2S 7.4V 80C 5200mAh LiPo Battery Pack | — |
| microcontroller | ESP32 S3 N16R8 | [user guide](https://github.com/microrobotics/ESP32-S3-N16R8/blob/main/ESP32-S3-N16R8_User_Guide.pdf) |
| edge compute | Raspberry Pi 5 | 5V 5A |
| voltage regulator for compute rail | Pololu D36V50F5 (5V 5.5A, 6-50V in) | [pololu.com/product/4091](https://www.pololu.com/product/4091), [archived](docs/datasheets/Pololu%20-%205V%2C%205.5A%20Step-Down%20Voltage%20Regulator%20D36V50F5.htm) |
| rangefinder | Garmin LIDAR-Lite v4 LED, part number 010-02022-00 | [archived PDF](docs/datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](docs/datasheets/rangefinder_lidar_lite_v4.md), [instructions](https://static.garmin.com/pumac/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf) (software name: rangefinder) |
| lidar | Slamtec Mapper M2M1 | [datasheet digest](docs/datasheets/slamtec_mapper_M2M1_datasheet.md) |
| motor controller | THW-1060-BRUSHED | [thw-1060-brushed-esc.md](docs/datasheets/thw-1060-brushed-esc.md) |
| steering servo | DS3225MG | [ds3225_servo.md](docs/datasheets/ds3225_servo.md) |

## Microcontroller Pin map (left header P1 only)

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

Wire colours: signal = yellow/white, power = red, ground = black. Rangefinder I2C: SDA = white, SCL = green. Put a tape flag on the two active signal wires.

## Make commands

This section lists day-to-day commands only, in the order you use them. `make help` lists everything (dev, CI and firmware tools too). [docs/setup.md](docs/setup.md) has the details.

**Once per Pi.** First, run `cp .env.example .env` and add yourself to the `docker` and `dialout` groups (docs/setup.md §1).

| # | Command | What it does |
| --- | --- | --- |
| 1 | `make setup` | Checks git, make and docker. Builds both Docker images (it runs `fw-image` and `ros-image`) |
| 2 | `make install-host` | Needs sudo. Names the ESP32 `/dev/rccar-esp32` and starts the car stack at every boot. Afterwards, unplug the USB cable and plug it in again one time |
| 3 | `make flash` | Switch the ESC off first. Uploads the firmware to the ESP32. Run it again only when `firmware/` changes |

You do not need to run `make config` by hand. `car-up` and the boot service run it.

**Every session**

| # | Command | What it does |
| --- | --- | --- |
| 1 | `make car-up` | Starts the stack (micro-ROS agent, supervisor, lidar driver). After a boot it already runs if you did `install-host`. Running it again is harmless |
| 2 | `make car-ps` | Wait until every service shows `healthy`. Then switch the ESC on |
| 3 | `make teleop` | Drives the car over SSH (arrows, space = brake, `x` = disarm + quit) |
| 4 | `make car-shutdown` | Disarms, stops the stack and offers to power off the Pi. Then switch the ESC off |

**Sensors** (stack running)

| Command | Sensor | What it does |
| --- | --- | --- |
| `make rangefinder` | rangefinder (Garmin LIDAR-Lite v4) | Shows a live distance feed in the terminal |
| `make viz` | lidar (Slamtec Mapper) | Shows scan, map and pose on `localhost:8765` for Foxglove. Forward the port with VS Code SSH |
| `make lidar-imu` | lidar (Slamtec Mapper) | Shows live heading, yaw rate, speed and acceleration. Also saves them to `logs/` |
| `make lidar-snapshot` | lidar (Slamtec Mapper) | Makes one capture to `logs/`: `map.png` (map + scan + pose) and a text summary. Claude Code can read both |
| `make lidar-record SECS=30` | lidar (Slamtec Mapper) | Records the lidar topics to a rosbag (`.mcap`, opens in Foxglove) in `logs/` |
| `make lidar-hw-test` | lidar (Slamtec Mapper) | Automated PASS/FAIL check of the real unit with the car still. Run `make drivers-stop` first and `make car-up` afterwards |

**When needed**

| Situation | Commands |
| --- | --- |
| something looks wrong | `make car-logs` |
| USB cable replugged | `make car-down`, then `make car-up` |
| first drive, or the servo/linkage changed | `make calibrate`, then `make test` (steering sweep; the motor never runs) |
| edited `tuning.toml` | `make tune` |
| after `git pull` | `make car-down`, `make ros-image`, `make flash` (only if `firmware/` changed, ESC off), `make car-up` |

## Wiring: Rangefinder (Garmin LIDAR-Lite v4 LED)

The software name is *rangefinder*. Datasheet: [archived PDF](docs/datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](docs/datasheets/rangefinder_lidar_lite_v4.md). Power off while wiring.

| Garmin pin | Name | Wire | Connect to |
| --- | --- | --- | --- |
| 1 | VIN (5 V, 4.75-5.25 V) | red | regulated 5 V **sensor rail** (never ESP32 5V/3V3) |
| 2 | GND | black | common ground (P1-22) |
| 3 | I2C SDA | **white** | GPIO8 (P1-12) |
| 4 | I2C SCL | **green** | GPIO9 (P1-15) |
| 5-10 | GPIOA, GPIOB, nRF debug | n/a | leave unconnected |

## Power rules

1. **The ESP32 powers nothing.** It outputs only actuator signals and communications. A separate regulated power rail powers the sensors. This rail shares ground with the ESP32. All signals stay at ≤ 3.3 V.
2. Servo power comes from the built-in 6 V / 3 A BEC of the ESC (red wire of the throttle lead). Connect it with a Y-harness.
3. Connect the grounds of the ESP32, ESC and servo (P1-22).

## Power-up sequence

1. ESC **off**. Wheels off the ground.
2. Connect the USB cable to **COM**. The ESP32 boots and sends neutral (1500 µs) on both channels. Then run `make car-up`.
3. ESC **on**. It beeps and learns neutral.
4. To power down, do the steps in reverse order. Switch the ESC off first. **Always switch the ESC off before `make flash`.**

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

Bench checklist (the procedure that verified phase 2): [docs/setup.md](docs/setup.md#phase-2-bench-checklist-user-run). Roadmap: [docs/docker_ros_plan.md](docs/docker_ros_plan.md). Firmware design: [docs/esp32-firmware-proposal.md](docs/esp32-firmware-proposal.md).
