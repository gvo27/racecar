# firmware/: agent notes

Rules: `.claude/rules/firmware.md` (loads for `firmware/esp32/**`). Facts: `docs/firmware/README.md`. Message copy: `firmware/esp32/extra_packages/rccar_msgs` is a copy of `ros2_ws/src/rccar_msgs` (`.claude/rules/msgs.md`).

## Verify
- `make build`: compile the env `esp32s3` in the docker image `rccar-fw` (`make fw-image` first). CI does the same.
- `make compiledb`, then read the clangd diagnostics of the changed files.
- A boundary change (comms header, `handleLine`, `setKey`): `make unit` (`deploy/tests/test_contract.py`) and `make ros-test` (`test_tuning.py`).
- `make flash`, `make monitor` and the bench `make test` are user-run. Never claim hardware behavior without user output.
