---
paths:
  - "tuning.toml"
  - "rccar_bringup/**"
  - "deploy/render_env.py"
---

# tuning.toml

Reference (platform keys, rendered env, launch arguments, PARAM_MAP): `docs/deploy.md`, `docs/ros2.md`.

- `tuning.toml` is the single source of truth for runtime tuning and platform settings. Secrets and private names stay in the gitignored `.env`.
- Add a key only with a confirmed value (datasheet or measurement). Reserved sections stay empty. This rule owns "no unconfirmed parameters".
- Keep each key name unique in the whole file. The tools edit lines by key name.
- A new `[platform.*]` key that compose uses changes `deploy/render_env.py`, `deploy/tests` and `docs/deploy.md` together.
- A firmware-bound key change changes `tuning.toml`, `rccar_mcu_bridge.tuning.FIRMWARE_KEYS` and `main.cpp` `setKey` together. `rccar_mcu_bridge/test/test_tuning.py` checks this. This rule owns the key-change rule.
