---
paths:
  - "tuning.toml"
  - "ros2_ws/src/rccar_bringup/**"
  - "deploy/render_env.py"
---

# tuning.toml

Reference (platform keys, rendered env, launch arguments, PARAM_MAP): `docs/deploy.md`, `docs/interfaces/ros2.md`.

- `tuning.toml` is the single source of truth for runtime tuning and platform settings. Secrets and private names stay in the gitignored `.env`.
- Add a key only with a confirmed value (datasheet or measurement), invariant 5. Reserved sections stay empty.
- Keep each key name unique in the whole file. The tools edit lines by key name.
- A new `[platform.*]` key that compose uses changes `deploy/render_env.py`, `deploy/tests` and `docs/deploy.md` together.
- A firmware-bound key changes in `tuning.toml`, `FIRMWARE_KEYS` and `setKey` in one commit (procedure: `firmware/.claude/skills/firmware-change/SKILL.md`, "Tuning key").
