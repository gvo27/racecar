---
paths:
  - "deploy/**"
  - "docker/**"
  - ".env.example"
---

# Deploy (phase 2, bench-verified: deploy/car/, docker/ros.Dockerfile, .env.example)

## Config split
- `tuning.toml` is the single source of truth (SSOT) for tuning and platform settings. Confirmed today: `[platform.pi5] esp32_device, arch`. Planned (add only when confirmed): mem limits, cpuset, inference backend, `[models].base_url`, `[supervisor]`.
- `.env` (gitignored) holds secrets and private names only: TZ, ROS_DOMAIN_ID (default 0), PLATFORM, TS_DOMAIN, ADMIN_TS_HOST, BACKUP_DEST (+ optional RCCAR_ROS_IMAGE override). `.env.example` documents each key. Keep them in sync.
- `make config` runs `deploy/render_env.py` inside the ROS image `$(ROS_IMAGE)`. Details:
  - It uses `--user <host uid:gid>` and mounts the repo at /work. Make passes `--repo-dir $(CURDIR)` and `--dialout-gid` because the container group db is different.
  - It needs `make ros-image` first.
  - It runs at boot through rccar.service ExecStartPre, so it must not depend on the firmware image.
  - It uses the standard library only. The tests are in `deploy/tests`. `make unit` (ROS test image) runs them.
  - It requires `.env` (it gives a hint if `.env` is missing). It reads `tuning.toml [platform.$PLATFORM]` and writes the gitignored `deploy/car/.env.generated` (ESP32_DEVICE PLATFORM ROS_DOMAIN_ID TZ RCCAR_ROS_IMAGE REPO_DIR HOST_UID HOST_GID DIALOUT_GID).
  - Compose reads that file with `--env-file` and uses `${VAR:?msg}` for required variables.
  - A new platform is a new `[platform.<name>]` table. Do not add per-platform compose files.

## Compose conventions (`deploy/car/compose.yaml`; services mcu-agent, core, tools[profile])
Every service has these settings:
- `network_mode: host`, `ipc: host`. `ROS_DOMAIN_ID` comes from the environment. `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`.
- `restart: unless-stopped` (tools: on demand).
- `x-logging` anchor: json-file, max-size 10m, max-file 3 (also in /etc/docker/daemon.json). `ROS_LOG_DIR=/tmp/roslog` on tmpfs.
- `mem_limit` (`CORE_MEM_LIMIT` default 512m). It is not yet in `[platform.*]` because it is unconfirmed.
- Pinned images: third-party images by digest (micro-ros-agent). Our own images are `rccar-ros:local` or `${RCCAR_ROS_IMAGE}` by git SHA from GHCR. Never use `:latest`.
- `${VAR:?msg}` for required variables.
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, size-capped `tmpfs: /tmp`, `read_only: true`. Only core has `SYS_NICE`. Never use `privileged`.
- Containers run as the host uid/gid (`HOST_UID`/`HOST_GID`), so calibration can write the bind-mounted `tuning.toml` (rw). The repo is mounted read-only at /ws/src/racecar. `logs/` is rw.
- Core has a heartbeat-file healthcheck: both /run/hb files (supervisor, mcu_bridge) must be touched within 6 s. The mcu-agent image has no heartbeat, so its healthcheck is `pgrep -x micro_ros_agent`. Core has `depends_on` it with `service_started`.
- Header comment: `# <svc> — <role>` + `# Notes: .claude/rules/deploy.md`
- Serial: `devices: [${ESP32_DEVICE}]` (udev symlink /dev/rccar-esp32) + `group_add: [dialout gid]`

## drivers service (phase 4, lidar)
- `drivers` runs `rccar_bringup drivers.launch.py` (mapper_driver + robot_state_publisher). It has no `devices` and no `cap_add`. It uses the same hardening and logging anchors as core. It mounts only the repo, read-only (`${REPO_DIR}:/ws/src/racecar:ro`). It does NOT use `*ros-mounts`, so it has no rw tuning.toml and no logs/. It talks to the Mapper over wlan0 (host network).
- The healthcheck is a heartbeat file. The driver touches it only while scans flow. It is expected that `drivers` is unhealthy when the Mapper is off. This does not affect core or mcu-agent.
- `MAPPER_HOST` env override (default 192.168.11.1) is for the Ethernet fallback. It is not in `.env`. The address is bench-confirmed. `mapper_host` may move to tuning.toml [platform.pi5] in a later change.
- For `make drivers-stop` / `drivers-start` / `lidar-hw-test`, see `.claude/rules/hw-testing.md`. `make ros-image` refuses while `drivers` runs.

## Host files (installed by `make install-host`, which prints each step)
- `deploy/car/99-rccar.rules` -> /etc/udev/rules.d (CH343 1a86:55d3 -> /dev/rccar-esp32, group dialout, 0660)
- `deploy/car/rccar.service` -> /etc/systemd/system, with @REPO_DIR@ and @USER@ substituted. It is a oneshot: `compose up -d` at boot, `down` at stop. It does not pull or build.

## Operations
- Deploy explicitly: `make car-pull && make car-up`. Use no auto-updaters and no autoheal.
- `flash` and `monitor` need the stack down (the agent holds the port) and a present `$(PORT)` (default /dev/rccar-esp32).
- After a USB unplug or replug, the device node that passes into `mcu-agent` is stale. Run `make car-down && make car-up`.
- Containers stay unprivileged. Shut down with `make car-shutdown` (supervisor disarm, compose down, confirm, sudo poweroff) in the ssh shell.
- `docker/ros.Dockerfile` stages: builder -> test (`make ros-test`) / runtime (default). Entry `docker/entrypoint.sh` sources /opt/ros/jazzy and /ws/install.
