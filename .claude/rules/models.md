---
paths:
  - "models/**"
---

# Models

Reference (manifest schema, download source, status): `models/README.md`.

- Never put model weights in git. `models/cache/` stays gitignored.
- Do not add `[models]` keys to `tuning.toml` without a confirmed value.
- A change to the manifest schema also changes `models/README.md`.
