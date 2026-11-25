---
name: car-deploy
description: Use when you change the car stack deployment - deploy/ (compose, render_env, udev, systemd), docker/ images or digests, a [platform.*] key of tuning.toml, .env.example - or when you prepare the Pi deploy steps of a PR. Gives the steps, the checks that an agent can run, and the steps that only the user runs.
---

# Car deploy (Pi, docker compose)

The constraints are in `.claude/rules/deploy.md`, `dependencies.md` and `hw-testing.md`. Facts (config split, compose settings, host files, image stages, operations): `docs/deploy.md`. Commands: `docs/commands.md`.

## Platform key or render_env change
1. Follow the constraints of `.claude/rules/tuning.md` (platform key) and `.claude/rules/deploy.md` ("Config").
2. Write the test first in `deploy/tests/test_render_env.py`, then change `deploy/render_env.py`, then `docs/deploy.md`.

## Compose change
1. Keep the hardening of each service (`.claude/rules/deploy.md`, "Compose").
2. Run `make config-check`. It renders the env file and validates the compose file.

## Image change
1. Before a build on the Pi: `make drivers-stop` (the hook denies `make ros-image` and `make setup` while the drivers container runs).
2. A base image digest change: `docker pull <image>:<tag>`, then `docker inspect --format '{{index .RepoDigests 0}}' <image>:<tag>`. Put the digest in the Dockerfile or the compose file. Write the old and the new digest in the PR.
3. `make ros-test` (image `test` stage) and `make ros-image` (runtime stage).

## Pi deploy steps (user-run)
The agent does not start, restart or flash hardware. The owner of the deploy checklist is the "Deploy" part of `.github/pull_request_template.md`. Copy its steps into the PR. Add only the steps that the change needs:
- `make dev-setup`, if `uv.lock` or `.envrc` changed.
- `make fw-image`, if the firmware toolchain changed.
- `make install-host`, if `deploy/car/99-rccar.rules` or `deploy/car/rccar.service` changed.
- `make clean && make flash` instead of `make flash`, if `rccar.meta`, `extra_packages` or `platformio.ini` changed.
Operations (replug, shutdown, pull): `docs/deploy.md` ("Operations").

## Verify
- `make checks` (`deploy/tests`, fast, no docker). `make unit` runs the same tests in the ROS image: run it when the image changed.
- `make config-check` for a compose, env or platform change. It needs `.env` and the image `rccar-ros:local`. Without them the check is "not run".
- `make ros-test` for an image change.
- Claim a result only with the command output from this session. A check that you did not run is "not run". Hardware steps are "user-run".
