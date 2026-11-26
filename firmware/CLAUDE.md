# firmware/: agent notes

Facts: `docs/firmware/README.md`.

## Verify
- `make build`: compile the env `esp32s3` in the docker image `rccar-fw` (`make fw-image` first). CI does the same.
- `make compiledb`, then read the clangd diagnostics of the changed files.
- A boundary change (comms header, `handleLine`, `setKey`): `make unit` (`deploy/tests/test_contract.py`) and `make ros-test` (`test_tuning.py`).
- User-run only: `make flash`, `make monitor`, the bench `make test`.
