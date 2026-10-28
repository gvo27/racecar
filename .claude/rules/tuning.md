---
paths:
  - "tuning.toml"
  - "rccar_bringup/**"
  - "deploy/render_env.py"
---

# tuning.toml ssot + bringup

- single source of truth for runtime tuning and platform settings. Secrets/private names stay in gitignored `.env`.
- no unconfirmed parameters: add a key only with a confirmed value (datasheet or measurement). Reserved sections stay empty.
- keys unique across the whole file (tools edit lines by key name).
- `[platform.<name>]` today: `[platform.pi5] esp32_device = "/dev/rccar-esp32"` (udev rule in deploy/car) and `arch = "arm64"`. Nothing else (mem limits, cpuset, backend are unconfirmed). Selected by `PLATFORM` in `.env`.
- `make config` -> `deploy/render_env.py` (stdlib, tomllib) -> gitignored `deploy/car/.env.generated`: ESP32_DEVICE PLATFORM ROS_DOMAIN_ID TZ RCCAR_ROS_IMAGE REPO_DIR HOST_UID HOST_GID DIALOUT_GID. New `[platform.*]` key used by compose => render_env.py + deploy/tests + deploy.md.
- `rccar_bringup/tuning_params.py` PARAM_MAP maps tuning tables to node params; only keys present in the file are emitted, nodes keep code defaults otherwise.
- firmware-bound key change => tuning.toml + rccar_mcu_bridge.tuning.FIRMWARE_KEYS (+ tools/rccar.py while legacy) + main.cpp setKey.
- launch args: use_sim_time, sim, tuning_file (default $RCCAR_TUNING else /ws/src/racecar/tuning.toml), heartbeat_dir.
