---
paths:
  - "deploy/**"
  - "docker/**"
  - ".env.example"
---

# Deploy

Reference (config split, compose settings, drivers service, host files, image stages, operations): `docs/deploy.md`. Procedures and checks: `deploy/.claude/skills/car-deploy/SKILL.md`.

## Config
- Add a platform value only when it is confirmed (`.claude/rules/tuning.md`). A new platform is a new `[platform.<name>]` table, not a new compose file.
- `.env` (gitignored) holds only secrets and private names. Keep `.env.example` in sync with it.
- `deploy/render_env.py` uses the standard library only, runs in the ROS image, and must not depend on the firmware image (it runs at boot).

## Compose
- Every service keeps the hardening: `cap_drop: [ALL]`, `no-new-privileges`, `read_only: true`, size-capped tmpfs, the `x-logging` anchor, a `mem_limit`. Only core has `SYS_NICE`. Never use `privileged`.
- Third-party images by digest. Own images `rccar-ros:local` or `${RCCAR_ROS_IMAGE}` by git SHA. Never `:latest`.
- Required variables use `${VAR:?msg}`.
- Containers run as the host uid/gid. The repo mount is read-only. Only `tuning.toml` and `logs/` are writable, and only where a service needs them.
- Each service has a healthcheck. Each service file has the header `# <svc> — <role>` and `# Notes: docs/deploy.md`.
- `drivers` has no `devices`, no `cap_add`, and no rw mounts. An unhealthy `drivers` must not affect core or mcu-agent.

## Operations
- Deploy explicitly. No auto-updaters, no autoheal.
- Hardware starts and restarts need human approval (`.claude/rules/hw-testing.md`).
