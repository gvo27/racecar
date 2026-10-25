---
paths:
  - "deploy/**"
  - "docker/**"
  - ".env.example"
---

# Deploy (phase 1: docker/ + .env.example exist; deploy/car/ is planned, phase 2)

## Config split
- `tuning.toml` = ssot for tuning + platform settings. Planned sections (add only once values are confirmed): `[platform.<name>]` (device path, per-container mem limit, cpuset, inference backend), `[models].base_url`, `[supervisor]`.
- `.env` (gitignored) = secrets + private names only: TZ, PLATFORM, TS_DOMAIN, ADMIN_TS_HOST, BACKUP_DEST. `.env.example` documents each key; keep in sync.
- `make config`: phase 1 = check `.env` exists. Phase 2 (planned) = render gitignored `deploy/car/.env.generated` from `tuning.toml [platform.$PLATFORM]` + `.env`. Compose reads via `${VAR:?msg}`. New platform = new `[platform.<name>]` table, no per-platform compose files.

## Compose conventions (planned, phase 2, `deploy/car/compose.yaml`)
Every service:
- `network_mode: host`, `ipc: host`
- `restart: unless-stopped`
- `x-logging` anchor: json-file, max-size 10m, max-file 3 (also in /etc/docker/daemon.json); `ROS_LOG_DIR` on tmpfs or /data
- `mem_limit` from `[platform.*]`
- pinned images: base by digest, own by git SHA from GHCR, never `:latest`
- `${VAR:?msg}` for required vars
- `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`, size-capped `tmpfs: /tmp`, `read_only: true` where possible; `SYS_NICE` only for real-time nodes
- heartbeat-file healthcheck `find /run/hb -mmin -0.1`
- header comment `# <svc> — <role>` + `# Notes: .claude/rules/deploy.md`
- serial: `/dev/rccar-esp32` (udev symlink) + `group_add: [dialout]`

## Operations (planned)
- systemd unit runs `compose up -d` at boot. Explicit deploys: `make car-pull && make car-up`. No auto-updaters, no autoheal.
- Containers stay unprivileged; shutdown via `make car-shutdown` (compose down + poweroff) in the ssh shell.
