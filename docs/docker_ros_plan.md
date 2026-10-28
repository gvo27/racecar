# Docker + ROS 2 plan

## Context

**Current state (verified on `main`):** on bench power, the Raspberry Pi 5 (Ubuntu 24.04 LTS) drives the ESP32-S3 over USB serial using `tools/rccar.py`, and the ESP32 outputs PWM to the steering servo and the ESC. There is no battery and there are no sensors yet.

**Goal:** a repo layout and service split that grows into the full autonomy stack on ROS 2 Jazzy. Nothing should be tied to the Pi 5, which is a prototype stand-in for future ROS 2 compute.

**Fixed decisions:**
- **Two repos.**
  - **This repo:** everything that runs on the car.
  - **ML training repo:** separate. It publishes versioned model artifacts that this repo downloads at runtime.
- **Multi-package layout**, the `Universal_Robots_ROS2_Driver` pattern: sibling ROS 2 packages at the repo root, non-ROS folders marked `COLCON_IGNORE`, and a `.repos` manifest for third-party sources.
- **Docker for every toolchain and runtime.** The host only needs `git`, `make` and Docker. Images are built for `arm64` and `amd64`.
- **`tuning.toml` is the single source of truth (SSOT)** for runtime tuning and platform settings. Secrets and private hostnames stay in the gitignored `.env`.
- **Out of scope for now:** server-side services (ingest, storage, Grafana, Coolify).

**Rules for every phase (one PR each):**
- The root `README.md` gets brief quick setup → deploy commands. Long guides go in `docs/`.
- `.claude/CLAUDE.md` and `.claude/layout.yaml` are updated in the same concise, machine-readable style.
- Every new feature folder gets a `.claude/rules/<feature>.md` with a `paths:` block.

---

## Target layout

```
rccar/                            ← repo root; colcon finds packages directly
├── rccar_msgs/                   msgs/srvs/actions: DriveCmd, Health, calibration srvs (contract)
├── rccar_description/            URDF + TF frames
├── rccar_bringup/                launch; loads tuning.toml → ROS params
├── rccar_mcu_bridge/             micro-ROS agent launch, FIRMWARE_KEYS, tuning push to ESP32
├── rccar_calibration/            interactive calibration/tuning CLIs (actuators now, sensors later)
├── rccar_supervisor/             safety authority: arbitration, arm/disarm, e-stop, heartbeats
├── rccar_teleop/                 admin keyboard teleop (runs in the SSH session)
├── rccar_captain/                central orchestrator (later; see "Captain")
├── rccar_recorder/ rccar_backup/ (phase 3)
├── rccar_drivers/ rccar_perception/ rccar_inference/   (later)
├── firmware/esp32/               PlatformIO project                                   [COLCON_IGNORE]
├── models/                       manifest.yaml, README.md (committed); cache/ (gitignored) [COLCON_IGNORE]
├── repos/                        rccar.repos + README.md                              [COLCON_IGNORE]
├── docker/                       ros + firmware toolchain Dockerfiles                  [COLCON_IGNORE]
├── deploy/car/                   compose.yaml, systemd unit, udev rules                [COLCON_IGNORE]
├── tuning.toml                   SSOT: [link] [steering(.calibration)] [throttle(.calibration)] [warmup] … + [platform.*] [models] [supervisor]
├── .env.example                  committed template; .env gitignored
├── .claude/                      CLAUDE.md, layout.yaml, rules/<feature>.md
├── docs/  logs/  Makefile  README.md
└── .github/workflows/            firmware build, colcon test, multi-arch images → GHCR
```

- Packages are only created in the phase that needs them.
- Workspace build (inside the ROS image): `vcs import src < src/rccar/repos/rccar.repos && colcon build`.
- `repos/README.md` briefly explains:
  - **Entry format:** `type`, `url`, `version`. Pin a tag or commit, never a moving branch.
  - **Commands:** `vcs import` / `vcs pull`.
  - **When to add an entry:** a third-party source with no apt binary. Never our own code.

---

## Dependencies

| Layer | Where it lives | Replaces |
|---|---|---|
| Host prerequisites | `git`, `make`, Docker Engine + compose + buildx; user in the `docker` and `dialout` groups | — |
| Firmware toolchain | `docker/firmware.Dockerfile`: PlatformIO pinned to `espressif32@6.9.0`, esptool. Named volume for `~/.platformio` caches the toolchain | `.venv` + `pio` |
| ROS runtime + Python deps | `docker/ros.Dockerfile`: `ros:jazzy-ros-base` (digest-pinned), apt `rosdep` deps from `package.xml`, `vcs import` | `.venv` + `requirements.txt` |

- **`make` stays on the host** as the entry point. The README setup lists it.
- **Retire `.venv` once the containers reach parity.** Flash from the container on the Pi (`--device /dev/rccar-esp32`). Non-Linux laptops flash via `ssh pi make flash`.
- **`make setup`** becomes: check the host prerequisites, then `docker compose pull` or build the images.
- **Machine-readable note:** `.claude/rules/dependencies.md` with paths `Makefile`, `docker/**`, `deploy/**`, `repos/**`, `**/package.xml`, `firmware/esp32/platformio.ini`. It records: host prerequisites, toolchain pins, the image-per-toolchain map, the rule that new deps go in `package.xml` (rosdep) or a Dockerfile and never on the host, and the rule to pin versions.

---

## Configuration: tuning.toml SSOT + .env

- **New sections**, added only once their values are confirmed (per the "no unconfirmed parameters" invariant):
  - `[platform.pi5]`: device path, per-container memory limits, CPU set, inference backend.
  - `[models]`: `base_url = "https://<host>.${TS_DOMAIN}/…"`.
  - `[supervisor]`: the admin link settings below.
- **`.env` holds only secrets and private names:** `TS_DOMAIN`, `PLATFORM`, `TZ`, `ADMIN_TS_HOST`, the backup destination. `.env.example` documents each key.
- **`make config`** renders the gitignored `deploy/car/.env.generated` from `tuning.toml [platform.$PLATFORM]` + `.env`. Compose reads it through `${VAR:?msg}`. A new platform is just a new `[platform.<name>]` table, with no per-platform compose files.
- **`rccar_bringup`** loads the same file into ROS params. Under the invariant "tuning key change => tuning.toml + FIRMWARE_KEYS + firmware", `FIRMWARE_KEYS` now lives in `rccar_mcu_bridge`.

---

## Actuator access, calibration and admin control under ROS 2

- **Today `tools/rccar.py` is the official interface.** After phase 2, every actuator interaction goes through ROS 2 via micro-ROS. The ASCII path (`esp32s3_ascii` firmware env, `tools/`, `.venv`) stays as a `legacy-*` fallback until the user's bench parity test, and is then deleted in a follow-up.
- **Firmware micro-ROS interfaces** (contract: `rccar_msgs`; bounded strings only):
  - subscription `/rccar/mcu/drive` (`DriveCmd`: `heading_rad`, dimensionless `throttle` [-1, 1], `source`; REP-103 SI units). The supervisor is the only publisher.
  - publishers `/rccar/mcu/telemetry` (best effort) and `/rccar/mcu/event` (reliable).
  - one service `/rccar/mcu/command` (`McuCommand`) that reuses the firmware's ASCII parser, so every clamp and safety check stays in one place and the entity count fits micro-ROS defaults. Typed services (`set_param`, `cal_point`, `raw_pwm`, `save`, `get`, `info`) wrap it on the Pi in `rccar_mcu_bridge`.
  - `rmw_uros_sync_session` replaces `TIME`; a reconnect state machine handles agent loss.
  - The failsafe timeout and the emergency brake stay in firmware.
- **`rccar_calibration`** provides interactive tools (`ros2 run`) that call those services.
  - Physical adjustments stay manual. The tool prompts for the step (servo horn, ESC neutral trim, sensor mount), jogs or measures the value, and writes it to the bind-mounted `tuning.toml [steering.calibration]` / `[throttle.calibration]`.
  - Later it also covers camera intrinsics, camera↔lidar extrinsics and IMU bias.
- **Make targets keep their names** (`calibrate`, `teleop`, `test`, `tune`, `session`, `flash`) and wrap `docker compose run --rm …`.

### Admin teleop over SSH (supervisor layer)
- **Flow:** laptop → `ssh pi` → `make teleop` runs `rccar_teleop` on the Pi, inside the SSH terminal. ROS traffic stays local; it never runs on the laptop.
- **Admin commands:** `DriveCmd` on `/rccar/cmd/admin`, the highest-priority input in the supervisor config.
- **Emergency services** live on the supervisor, bypass arbitration, and forward disarm to the ESP32 immediately: brake and disarm (`std_srvs/Trigger`); reverse is a normal drive command. Brake/disarm **latch** an incident; `arm` is `Reset(incident)` and leads to *armed but stationary*, and teleop must return to neutral before motion. Fail-safe by silence: the supervisor streams drive commands only while a permit is valid, and the ESP32 timeout disarms when they stop.
- **Software stop is not safety-rated.** The ESC power switch is the independent hardware stop.
- **Admin input goes straight to the supervisor**, never through the captain.
- **Full shutdown:** the teleop key disarms through the supervisor and exits, then `make car-shutdown` runs in the SSH shell (`compose down` + `sudo poweroff`). Containers stay unprivileged.

### Optional admin-link failsafe (note only, not implemented)
- `tuning.toml [supervisor]`:
  - `admin_link_failsafe = false` (default: the car may run on its own)
  - `admin_link_timeout_s`
  - the peer is `ADMIN_TS_HOST` from `.env`
- **Runtime toggle:** `ros2 param set /supervisor admin_link_failsafe true` (wrapped as `make admin-failsafe-on/off`). The config file sets the boot default.
- **Presence indicator:** the admin laptop's Tailscale peer status (`Online`, last seen), read through the host's tailscaled LocalAPI socket mounted read-only into the supervisor.
- **When enabled and the peer is offline past the timeout:** brake → neutral → disarm, plus `EVT ADMIN_LOST`.

---

## Captain (note only, not implemented in these phases)

`rccar_captain` orchestrates central compute: it sequences drivers, perception, localization and planning, and it outputs heading/speed `DriveCmd` (`source=captain`).

**Authority chain:** `[future: cloud nav API, natural-language agent] → captain → supervisor ← admin teleop`, then `supervisor → micro-ROS → ESP32 failsafe`.

- Higher layers send **goals**, not motor commands, as ROS 2 actions on `rccar_msgs/action/Mission`.
- Each source publishes `DriveCmd` on its own input topic (`/rccar/cmd/<source>`). Priority and timeout per input come from supervisor config, never from the message (a sender could fake it); `DriveCmd.source` is for logging. The supervisor arbitrates (twist_mux pattern), is the only publisher on `/rccar/mcu/drive`, and keeps final veto.
- Adding a layer means a new action client or a new `DriveCmd` source, with no changes to the supervisor or firmware.

---

## Car containers (`deploy/car/compose.yaml`)

| Container | Contents | Notes |
|---|---|---|
| `mcu-agent` | `micro-ros-agent` + tuning push node | `/dev/rccar-esp32` (udev symlink), `group_add: [dialout]` |
| `supervisor` | rccar_supervisor | `depends_on: mcu-agent (service_healthy)` |
| `tools` (on demand) | rccar_calibration, rccar_teleop, firmware flash | `docker compose run --rm tools …` |
| `recorder`, `backup` | phase 3 | data on bind-mounted `/data` (SSD, not microSD) |
| `drivers`, `perception`, `captain` | later | perception + inference as composable nodes in one process |

**Every service gets:**
- `network_mode: host` + `ipc: host` (ROS 2 discovery)
- `restart: unless-stopped`
- the `x-logging` anchor: `json-file`, `max-size: 10m`, `max-file: 3`. The same limits are set in `/etc/docker/daemon.json`, and `ROS_LOG_DIR` points to tmpfs or `/data`.
- `mem_limit` from `[platform.*]`
- pinned images: base images by digest, our own by git SHA from GHCR. Never `:latest`.
- `${VAR:?msg}` for required variables
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, a size-capped `tmpfs: /tmp`, and `read_only: true` where possible. `SYS_NICE` is added back only for real-time nodes.
- a heartbeat-file healthcheck (`find /run/hb -mmin -0.1`)
- a header comment: `# <svc> — <role>` + `# Notes: .claude/rules/deploy.md`

A systemd unit runs `compose up -d` at boot. Deploys are explicit: `make car-pull && make car-up` at known SHAs. No auto-updaters and no autoheal.

---

## Models

- `models/manifest.yaml` (committed) lists name, version, file, sha256 and I/O spec.
- `make models` resolves `tuning.toml [models].base_url` with `${TS_DOMAIN}` from `.env`, downloads into the gitignored `models/cache/`, and verifies the hashes. The inference container mounts that folder read-only.
- `models/README.md` notes that the host must be on the tailnet with MagicDNS accepted. Do not implement Tailscale setup.

---

## `.claude/` context files

- **`.claude/layout.yaml`**: machine-readable map of path → role, owner package, rules file and invariants. `CLAUDE.md` replaces its `layout:` block with `layout: .claude/layout.yaml`.
- **Rules files**, each created with its feature:

| Rules file | `paths:` |
|---|---|
| `firmware.md` (exists; update) | `firmware/esp32/**` |
| `dependencies.md` | `Makefile`, `docker/**`, `deploy/**`, `repos/**`, `**/package.xml`, `firmware/esp32/platformio.ini` |
| `deploy.md` | `deploy/**`, `docker/**`, `.env.example` |
| `tuning.md` | `tuning.toml`, `rccar_bringup/**` |
| `models.md` | `models/**` |
| `repos.md` | `repos/**` |
| `msgs.md` | `rccar_msgs/**` |
| `mcu_bridge.md` | `rccar_mcu_bridge/**` |
| `calibration.md` | `rccar_calibration/**` |
| `supervisor.md` | `rccar_supervisor/**`, `rccar_teleop/**` |
| `ros2.md` | `rccar_*/**` (phase 2; see "Sim/real parity + ROS 2 conventions") |
| `captain.md` | `rccar_captain/**` (later) |

---

## Sim/real parity + ROS 2 conventions

**Sim is a swap, not a separate codebase.** Sim and car share `rccar_description` (URDF), `rccar_msgs`, the supervisor and everything above it. Only the layer below the supervisor changes:

```
captain / perception / planning / supervisor      ← identical in sim and on the car
                     │ arbitrated DriveCmd, telemetry, sensor topics
        ┌────────────┴────────────┐
   sim:=true                  sim:=false (default)
 Gazebo + ros_gz_bridge      mcu-agent → micro-ROS → ESP32
```

- **Hardware boundary = the supervisor's output topic + telemetry/sensor topics.** Nothing above it may import or assume ESP32, serial or Gazebo specifics.
- **Every launch file accepts `use_sim_time`**, and `rccar_bringup` passes it through, so no node needs edits to run in sim.
- **The sim repo** (worlds, gz bridge config, the sim adapter) stays separate per CLAUDE.md. It pulls this repo through its own `.repos`, and adds nothing to this repo except the `sim:=` launch arg.
- If autonomy code needs a sim-only branch, treat that as a boundary leak and fix the interface.

**`.claude/rules/ros2.md`** (paths: `rccar_*/**`, in the same compact style as `firmware.md`). Content to borrow from [ros2-claude-code-template](https://github.com/harunkurtdev/ros2-claude-code-template) `.claude/rules/` + skills, trimmed to what we use:
- **Communication** (`ros2_communication.md`): topic/service naming, a QoS profile per stream (sensor data = best-effort, commands/e-stop = reliable), standard msgs before custom ones.
- **Testing** (`testing.md`): algorithms in plain Python/C++ libraries tested with pytest/gtest without ROS ("thin node, fat library"), plus `launch_testing` for node wiring.
- **Lifecycle nodes** for resource owners (mcu_bridge, drivers, recorder). Declare every parameter with `declare_parameter`.
- **Launch:** composable launch files, params loaded from `tuning.toml` through `rccar_bringup`, and no hardcoded values.
- **Skip:** VDA 5050, Nav2 BT plugin scaffolding, gz-sim ECS/plugin tooling, and the mandatory 4-layer clean-architecture split per package.

---

## Phases

1. **Foundation: Docker toolchain + restructure + CI** (one PR)
   - **Toolchains:** `docker/firmware.Dockerfile`, with `make build/flash/monitor` running through it.
   - **CI:** a GitHub Actions firmware build.
   - **Restructure:** move `firmware/` to `firmware/esp32/` and add the `COLCON_IGNORE` markers. Add `repos/` (empty manifest + README), `.env.example`, `models/` (manifest + README), and `make config` / `make models` skeletons.
   - **Context files:** add `.claude/layout.yaml`, `dependencies.md`, `deploy.md`, `models.md` and `repos.md`, and update `firmware.md`, CLAUDE.md, the README setup (git, make, docker) and the Makefile.
   - **Scope limit:** `tools/` and `.venv` stay, so bench host control is unchanged.
2. **ROS 2 + micro-ROS actuator path** (one phase; it may land as an ASCII-bridge commit followed by a micro-ROS commit if that makes the cutover easier to debug)
   - **Images and packages:** `docker/ros.Dockerfile` (multi-stage), then `rccar_msgs` (`DriveCmd` heading_rad/throttle/source, `McuCommand`, `Reset`, calibration srvs), `rccar_mcu_bridge`, `rccar_bringup`, `rccar_supervisor` (arbitration + latched e-stop), `rccar_teleop` and `rccar_calibration`.
   - **Firmware:** the comms layer becomes micro-ROS via `micro_ros_platformio` (jazzy, serial on UART0, pinned by commit), with `rccar_msgs` copied into `firmware/esp32/extra_packages/`. Env `esp32s3` = micro-ROS (default), `esp32s3_ascii` = legacy protocol. `make build` keeps `.pio/libdeps` (the micro-ROS lib build is slow) and cleans only `.pio/build`.
   - **CI:** ROS image build + `colcon build/test` (pytest, launch_testing, ament_lint), ros2-engineering static validators, an `extra_packages` sync check, and a firmware matrix over both envs.
   - **Not in phase 2:** ros2_control (the ESP32 owns PWM and there is no odometry); revisit with `ackermann_steering_controller` for the captain/Nav2 phase.
   - **Deployment:** `deploy/car/` (compose, systemd, udev) and `[platform.pi5]`.
   - **Cleanup (follow-up PR):** delete `tools/`, `.venv` and the `esp32s3_ascii` env after the user's bench parity test.
   - **New invariant:** "msg/srv change => rccar_msgs + firmware/esp32/extra_packages + docs".
   - **Conventions:** add `.claude/rules/ros2.md`. Make the supervisor output the hardware boundary, and have every launch file accept `use_sim_time` (see "Sim/real parity").
3. **Recorder + backup.** MCAP bags to `/data`; upload only when disarmed and idle, to the destination set in `.env`.
4. **Sensors.** `rccar_drivers`, `rccar_description` TF, sensor calibration, time sync (chrony). `rccar_description` is the single URDF for car and sim; sensor topics/frames are defined once so the sim adapter can publish the same ones.
5. **Captain, perception, inference, admin-link failsafe.** Per the notes above.
6. **Sim adapter (sim repo).** Gazebo world + `ros_gz_bridge` below the supervisor, and a `sim:=true` arg in `rccar_bringup`. Verify the captain/perception stack runs unchanged in sim and on the car.

---

## Verification

- **Every phase:** bench check on the Pi + ESP32: steering sweep + failsafe (`make test`), calibrate round-trip into `tuning.toml`, and teleop over SSH from the laptop. The root README quick-start must work verbatim from a fresh clone on a host with only git, make and Docker.
- **Phase 1:**
  - The CI firmware job is green.
  - The container build of `firmware.bin` matches a local `make build`.
  - `make flash` from the container works on the Pi.
  - `colcon list` finds nothing (no packages yet) and doesn't descend into `firmware/`.
- **Phase 2:**
  - `make config && make car-up`, and `docker compose ps` shows every service healthy.
  - `ros2 topic echo` shows telemetry.
  - Admin teleop over SSH: drive, brake, reverse, disarm.
  - Unplug the USB cable or kill `mcu-agent` → the ESP32 failsafe stops the car.
  - Kill teleop → the supervisor stops the car.
  - `make car-shutdown` disarms and then powers off.
  - Logs stay capped at 3×10 MB per container.
