# models/

- `manifest.yaml` (committed): name, version, file, sha256, inputs/outputs per model.
- Weights are not in git. `models/cache/` is gitignored.
- Download base URL: `tuning.toml [models].base_url`, with `${TS_DOMAIN}` taken from `.env`. The `[models]` section is not in `tuning.toml` yet (no confirmed value).
- The host must be on the Tailscale tailnet with MagicDNS accepted, otherwise `*.${TS_DOMAIN}` does not resolve.
- `make models` downloads into `models/cache/` and verifies sha256: not implemented yet (currently validates and prints the manifest).
