# Plan: mechanical/ subproject, build123d frame for the TT-02 (rev1)

Status: active (2026-11-28; A in main (#26); B (#27) and C (#29) in mech-dev; D open for the owner review (#30); integration PR #28)

## Context
`mechanical/` is a scaffold (ADR 0001 reserves it for 3D-printed mounts). We need a printed frame that carries the rev3 power board and the Pi 5 on the TT-02 chassis, with rail blocks for the camera and the lidar. The workflow copies `pcb/`: a design skill, TDD and checks, a read-only review agent, CI. Claude designs and checks on the Linux VM with build123d. The owner imports the STEP file in SolidWorks (Win11) for the final human review. Infrastructure comes first, then the frame. This is an iterative design: placeholder values now, measured values later.

## Decisions (owner, 2026-11-27)
- PCB interface: the cut rev3 board, four M3 holes (not the blank dowels).
- Environment: a pinned Docker image (like the KiCad image).
- Plugins and MCP: none. Own skill and agent. Take the useful ideas of pzfreo/build123d-mcp (validate gate before export, hole/feature inventory, STEP diff between revisions, printability checks, previews). No third-party code in the agent loop.
- Battery swap: a quick-release frame. Pull the clips, lift the frame, swap the battery. Cables need slack.
- Chassis interface: the four body posts plus the stock body clips. Keep it a swappable module: a later change to screw pads on the damper stays must not need a refactor.
- Printing: not decided. Assume that the lab has all common printers and filaments. Values are `assumed` until confirmed.
- STEP handoff: CI artifacts on every PR. A committed copy only for an approved release (`docs/mechanical/releases/<rev>/`).
- `plugin-dev:skill-reviewer`: one run after phase B.
- `/setup-shop`: not needed. The image needs only docker, which `make check-host` already requires. No new host package.

## Facts and sources (to owner files, not copied into code)
| Item | Value | Status, source |
|---|---|---|
| rev3 board | 66 x 140 mm outline; M3 holes (footprint 3.2 mm, drill 3.4 mm in the board file), 3.5 mm in from each edge (59 x 133 mm pattern) | confirmed: `pcb/src/rc_power_board.kicad_pcb`. Code reads the board file, no copy |
| rev3 underside | bare B.Cu with `VBAT_RAW`, faces the chassis: standoff >= 5 mm + insulation (proposed, not approved) | `docs/pcb/fab_handoff.md` |
| Pi 5 | 85 x 56 mm; 4 x ø2.7 (M2.5), 58 x 49 mm pattern, 3.5 mm from edges; ø6 keep-out pads; ports +3 mm | official, "approximate": `docs/datasheets/RP-008348-DS-10-raspberry-pi-5-product-brief.pdf` p.3 (owner added, not committed yet) |
| Pi 5 heights | USB/RJ45 about 17 mm; Active Cooler 13.7 mm | estimate; cooler official drawing |
| TT-02 (kit 58716 = GR Yaris Rally1 on TT-02) | wheelbase 257 mm; body posts L-R about 65-67 mm (3P), F-R about 240 mm (EST); 6 mm body clips; M3 tapping screws | official manual `tamiya.com/english/rc/rcmanual/tt02.pdf` + third-party. Measure |
| Battery | top-load, left side of the tub, holder bar D1 + 2 snap pins; bay about 139 x 47 x 25 mm; bar top about 37 mm above ground (EST) | manual step 36 + 3P. Measure |
| Mapper M2M1 | `docs/datasheets/slamtec_mapper_M2M1_datasheet.md` (2 x M3, 24 mm apart, under; arrow +X) | official digest in repo |
| Camera | not chosen (no model in `docs/hardware.md`) | rail block only |

## Layout
- `mechanical/`: `README.md` (sign), `CLAUDE.md` (verify commands), `pyproject.toml` + `uv.lock` (build123d 0.13.0, bd_warehouse 0.4.0, trimesh 5.2.2, pytest, ruff; Python 3.13), `config/` (TOML read by code), `src/rccar_mech/` (library + parts), `tests/`, `.claude/skills/mech-design/`. Outputs to `build/mech/` (git ignores it).
- `config/hardware.toml`: tables `pi5`, `tt02`, `battery`, `mapper`, `camera_block`, each with `status` and `source`, like `milling.toml`. The loader rejects a table without them. `pcb_rev3` has only a path to the `.kicad_pcb` file. The loader parses the outline and the `MountingHole` footprints.
- `config/print.toml`: process, nozzle, min wall, hole compensation, layer height, heat limit. All `assumed` (start: FDM, 0.4 mm nozzle, PETG-class).
- `config/frame.toml`: design parameters (deck thickness, clearances, standoff height, rail-block sizes, chassis-interface type `body_posts` or `screw_pads`).
- `docker/cad.Dockerfile`: `python:3.13-slim@sha256:...`, `libgl1`, uv copied from `ghcr.io/astral-sh/uv:<ver>@sha256`, `uv sync --frozen` of `mechanical/uv.lock` into `/opt/venv`. Runs as the host uid with the repo mounted (pattern: `KICAD_RUN`).
- `docs/mechanical/`: `conventions.md` (units mm, frame X forward / Y left / Z up = REP-103 and `base_link`, origin = body-post center at ground level; SolidWorks import notes: Y-up default, STEP keeps no feature history), `handoff.md` (Linux, GitHub, SolidWorks loop + the measure list), `releases/rev1/review/README.md` (status record, pcb pattern).
- Claude files: `.claude/rules/mechanical.md` (paths `mechanical/**`, `docs/mechanical/**`), `.claude/agents/mech-reviewer.md`, `mechanical/.claude/skills/mech-design/` (`SKILL.md`, `references/check-matrix.md`, `references/build123d-notes.md` (API notes, pointer to `llms.txt` and the source at the pinned tag), `references/lessons.md`).

## Library design (modular, parameterized)
- `params.py`: load and check the TOML files (status, source, units).
- `refs.py`: reference envelopes (not printed): Pi 5 with port and cooler keep-outs, rev3 board with tallest-part height, battery and its lift-out path, body posts, holder bar.
- `parts/`: `deck.py` (plate, halves, splice), `chassis_if.py` (one function per interface type, same return contract; select through `frame.toml`), `mounts.py` (standoffs, blind holes, rail blocks). The assembly is `models/frame.py`.
- `export.py`: STEP (labels, colors; read the file back), binary STL (set tolerance), SVG views (ExportSVG + `project_to_viewport`), `report.json` (bbox, volume, mass estimate, center-of-gravity height, holes inventory, check results).
- `checks.py`: solid valid, solid count, bbox, volume, min wall, hole diameters and centers vs the source, interference = 0 between parts and refs, clearances (battery lift path, frame bottom above holder bar, Pi ports), max component height, print bed fit, STL watertight and winding (trimesh), STEP round-trip (volume and bbox within tolerance).
- `diff.py`: compare two STEP files (bbox, volume, hole inventory). Used for a release and a PR summary.

## Make targets (prefix `mech-`)
`cad-image`, `mech-test` (pytest + ruff), `mech-build MODEL=frame` (STEP, STL, SVG, report to `build/mech/`), `mech-check` (checks; exit 1 on failure), `mech-diff A= B=`, `mech-release REV=rev1` (copy the approved outputs to `docs/mechanical/releases/<rev>/`). Add to `MAKE_TARGETS` in `deploy/tests/test_claude_agents.py`.

## CI
`.github/workflows/mechanical.yml`: on pull_request with paths `mechanical/**`, `docker/cad.Dockerfile`, `docs/mechanical/**`. Build the image (buildx, GHA cache), `make mech-test mech-build mech-check`, upload `build/mech/` (STEP, STL, SVG, report) as artifact `mech-<model>` (30 days).

## Rollout phases (one PR per phase, TDD: red test first)

The phases have letters (A to D), so that they are not confused with PR numbers. Owner 2026-11-28: phase A merged in `main` (#26). Phases B and C go into the integration branch `mech-dev` when their CI passes. Phase D targets `mech-dev` and stays open for the owner review. `mech-dev` goes into `main` only when the owner merges it.
- **Plan PR (#25):** branch `mechanical-frame` off `main`. Commit `docs/plans/2026-11-27-mechanical-frame.md` (this plan, `Status: active`). Open the PR (body: 1 Intro, 2 Owner steps to start, 3 Rollout phases).
- **A. Pipeline (#26):** image, uv project, make targets, CI, `params.py`, `export.py`, `checks.py`, `diff.py`, all on a test part (a bracket with 2 holes). Tests: validity, dims, holes, STEP round trip, STL watertight, a parameter-change regression. Owner: import the test STEP in SolidWorks once (units, names, colors).
- **B. Claude tooling:** rule, skill `mech-design`, agent `mech-reviewer`, test updates (`mech-*` names), docs (`docs/claude-tooling.md`, `docs/dependencies.md` image pins, root `README.md` row, `docs/README.md`, `mechanical/README.md`). Then `plugin-dev:skill-reviewer` (local enable, removed by `make close`).
- **C. Hardware facts and references:** commit the Pi 5 PDF + `docs/datasheets/compute_raspberry_pi5.md` digest, `hardware.toml` with placeholders, the KiCad board reader (test: 4 holes at the expected spacing, outline 66 x 140), `refs.py` envelopes.
- **D. Frame rev1:** deck, body-post interface with clips, PCB and Pi mounts, rail blocks. Checks green. `mech-reviewer`, then `code-review`. Owner SolidWorks review.
- **E. Iterate (owner):** owner measures the car (list in `handoff.md`). Placeholders become `confirmed`. Print, fit, drill the rail blocks. After approval: `make mech-release REV=rev1`.

## Verification
- `make mech-test`, `make mech-build MODEL=frame`, `make mech-check` (exit 0), `make checks`, `make context` (no new warning).
- CI `mechanical.yml` green, with the artifacts present.
- Not verified by the agent: SolidWorks import, print fit, real car dimensions (owner).
