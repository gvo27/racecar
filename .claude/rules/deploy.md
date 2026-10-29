---
paths:
  - "deploy/**"
  - "docker/**"
  - ".env.example"
---

# Deploy (phase 2, bench-verified: deploy/car/, docker/ros.Dockerfile, .env.example)

## Config split
- `tuning.toml` = ssot for tuning + platform settings. Confirmed today: `[platform.pi5] esp32_device, arch`. Planned (add only once confirmed): mem limits, cpuset, inference backend, `[models].base_url`, `[supervisor]`.
- `.env` (gitignored) = secrets + private names only: TZ, ROS_DOMAIN_ID (default 0), PLATFORM, TS_DOMAIN, ADMIN_TS_HOST, BACKUP_DEST (+ optional RCCAR_ROS_IMAGE override). `.env.example` documents each key; keep in sync.
- `make config` runs `deploy/render_env.py` inside the ROS image `$(ROS_IMAGE)` (`--user <host uid:gid>`, repo mounted at /work; make passes `--repo-dir $(CURDIR)` and `--dialout-gid` because the container's group db differs; needs `make ros-image` first; runs at boot via rccar.service ExecStartPre, so it must not depend on the firmware image). Stdlib; tests in `deploy/tests`, run by `make unit` (ROS test image): `.env` required (hint if missing) + `tuning.toml [platform.$PLATFORM]` -> gitignored `deploy/car/.env.generated` (ESP32_DEVICE PLATFORM ROS_DOMAIN_ID TZ RCCAR_ROS_IMAGE REPO_DIR HOST_UID HOST_GID DIALOUT_GID). Compose reads it via `--env-file` with `${VAR:?msg}` for required vars. New platform = new `[platform.<name>]` table, no per-platform compose files.

## Compose conventions (`deploy/car/compose.yaml`; services mcu-agent, core, tools[profile])
Every service:
- `network_mode: host`, `ipc: host`; `ROS_DOMAIN_ID` from env, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`
- `restart: unless-stopped` (tools: on demand)
- `x-logging` anchor: json-file, max-size 10m, max-file 3 (also in /etc/docker/daemon.json); `ROS_LOG_DIR=/tmp/roslog` on tmpfs
- `mem_limit` (`CORE_MEM_LIMIT` default 512m; not yet in `[platform.*]` because unconfirmed)
- pinned images: third-party by digest (micro-ros-agent), our own `rccar-ros:local` or `${RCCAR_ROS_IMAGE}` by git SHA from GHCR; never `:latest`
- `${VAR:?msg}` for required vars
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, size-capped `tmpfs: /tmp`, `read_only: true`; `SYS_NICE` only on core. Never `privileged`.
- containers run as the host uid/gid (`HOST_UID`/`HOST_GID`) so calibration can write the bind-mounted `tuning.toml` (rw); the repo is mounted read-only at /ws/src/racecar, `logs/` rw
- heartbeat-file healthcheck on core: both /run/hb files (supervisor, mcu_bridge) touched within 6 s. mcu-agent image has no heartbeat: healthcheck = `pgrep -x micro_ros_agent`; core `depends_on` it with `service_started`
- header comment `# <svc> — <role>` + `# Notes: .claude/rules/deploy.md`
- serial: `devices: [${ESP32_DEVICE}]` (udev symlink /dev/rccar-esp32) + `group_add: [dialout gid]`

## Host files (installed by `make install-host`, prints each step)
- `deploy/car/99-rccar.rules` -> /etc/udev/rules.d (CH343 1a86:55d3 -> /dev/rccar-esp32, group dialout, 0660)
- `deploy/car/rccar.service` -> /etc/systemd/system with @REPO_DIR@ and @USER@ substituted; oneshot `compose up -d` at boot, `down` at stop. Does not pull or build.

## Operations
- Explicit deploys: `make car-pull && make car-up`. No auto-updaters, no autoheal.
- `flash`/`monitor` require the stack down (the agent holds the port) and a present `$(PORT)` (default /dev/rccar-esp32).
- USB unplug/replug: the device node passed into `mcu-agent` goes stale => `make car-down && make car-up`.
- Containers stay unprivileged; shutdown via `make car-shutdown` (supervisor disarm, compose down, confirm, sudo poweroff) in the ssh shell.
- `docker/ros.Dockerfile` stages: builder -> test (`make ros-test`) / runtime (default). Entry `docker/entrypoint.sh` sources /opt/ros/jazzy and /ws/install.
