# Make commands: reference

This file lists day-to-day commands only, in the order you use them. `make help` lists everything (dev, CI and firmware tools too). [setup.md](setup.md) has the details.

**Once per Pi.** First, run `cp .env.example .env` and add yourself to the `docker` and `dialout` groups ([setup.md](setup.md) §1).

| # | Command | What it does |
| --- | --- | --- |
| 1 | `make setup` | Checks git, make and docker. Builds both Docker images (it runs `fw-image` and `ros-image`) |
| 2 | `make install-host` | Needs sudo. Names the ESP32 `/dev/rccar-esp32` and starts the car stack at every boot. Afterwards, unplug the USB cable and plug it in again one time |
| 3 | `make flash` | Switch the ESC off first. Uploads the firmware to the ESP32. Run it again only when `firmware/` changes |

You do not need to run `make config` by hand. `car-up` and the boot service run it.

**Every session**: see the root [README.md](../README.md#daily-commands).

**Sensors** (stack running)

| Command | Sensor | What it does |
| --- | --- | --- |
| `make rangefinder` | rangefinder | Shows a live distance feed in the terminal |
| `make viz` | lidar | Shows scan, map and pose on `localhost:8765` for Foxglove. Forward the port with VS Code SSH |
| `make lidar-imu` | lidar | Shows live heading, yaw rate, speed and acceleration. Also saves them to `logs/` |
| `make lidar-snapshot` | lidar | Makes one capture to `logs/`: `map.png` (map + scan + pose) and a text summary. Claude Code can read both |
| `make lidar-record SECS=30` | lidar | Records the lidar topics to a rosbag (`.mcap`, opens in Foxglove) in `logs/` |
| `make lidar-hw-test` | lidar | Automated PASS/FAIL check of the real unit with the car still. Run `make drivers-stop` first and `make car-up` afterwards |

**When needed**

| Situation | Commands |
| --- | --- |
| something looks wrong | `make car-logs` |
| USB cable replugged | `make car-down`, then `make car-up` |
| first drive, or the servo/linkage changed | `make calibrate`, then `make test` (steering sweep; the motor never runs) |
| edited `tuning.toml` | `make tune` |
| after `git pull` | `make car-down`, `make ros-image`, `make flash` (only if `firmware/` changed, ESC off), `make car-up` |

