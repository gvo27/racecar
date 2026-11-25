# firmware/: agent notes

Facts: `docs/firmware/README.md`. Procedures and checks: skill `firmware-change` (`firmware/.claude/skills/firmware-change/SKILL.md`).

## Verify
- `make build` (CI does the same), `make compiledb` and the clangd diagnostics of the changed files.
- User-run only: `make flash`, `make monitor`, the bench `make test`.
