# mechanical/: agent notes

Facts and conventions: `docs/mechanical/README.md`. The tools run only in the CAD image (`make cad-image`). Do not run them with the host python.

Verify: `make mech-test`, then `make mech-check MODEL=<model>` for each changed model. Exit 1 = check errors.
