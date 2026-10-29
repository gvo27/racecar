---
paths:
  - "models/**"
---

# Models

- Weights never in git. `models/manifest.yaml` (committed): per model name, version, file, sha256, inputs/outputs. `models/cache/` gitignored.
- Source: ML training repo publishes versioned artifacts. Base URL = `tuning.toml [models].base_url` with `${TS_DOMAIN}` from `.env`. `[models]` NOT yet in tuning.toml (no confirmed value; do not add unconfirmed).
- Host must be on the tailnet with MagicDNS accepted. Tailscale setup is out of scope.
- `make models`: phase 1 = validate/print manifest only. Planned = download to `models/cache/` + verify sha256. Inference container mounts cache read-only.
- Manifest change => update `models/README.md` if schema changes.
