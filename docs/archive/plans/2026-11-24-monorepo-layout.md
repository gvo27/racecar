# Plan: monorepo layout (branch `restructure`, new PR)

Status: done (2026-11-24; the Pi bench checklist of the PR is user-run)

## Context
The 8 ROS packages `rccar_*` sit at the repo root next to `pcb/`, `firmware/`, `docs/`, `deploy/`, `docker/`. The user wants a monorepo layout with dedicated root folders: `ros2_ws/`, `firmware/`, `pcb/`, `models/`, plus scaffolds for `simulation/gazebo/` (racecar-sim moves in later) and `mechanical/` (3D-printed case later). Each subproject gets a short README and, where useful, a nested CLAUDE.md. The workflow gets an invariants file and `docs/adr/`. The root README gets shorter. The car (Pi 5 + ESP32-S3) must build, deploy and behave exactly as it does now.

Key design choice: **the container layout stays the same.** Compose still mounts the repo root at `/ws/src/racecar`. `tuning.toml`, `logs/`, `deploy/`, `docker/`, `scripts/`, `Makefile` stay at the root. So `RCCAR_TUNING`, `/ws/src/racecar/logs`, `rccar.service`, `render_env.py` and every make target name stay unchanged. colcon finds packages recursively, so `/ws/src/racecar/ros2_ws/src/rccar_*` builds with no colcon change. Only source paths move.

Branch: `git switch -c restructure origin/main`. PR #22 (`rev3-milling-findings`) edits `docs/pcb`, `docs/techctcarvera` and the pcb skills. This plan does not touch those files.

Out of scope (follow-up PRs): skill consolidation (plan file written in this PR, step 6). Move the `lab:` value that `lab.py` and the Makefile parse out of `.claude/CLAUDE.md` into TOML (project-context row 2). That move conflicts with PR #22. Mechanical CAD content. Sim repo merge.

## Issue #20 (project-context review, 2026-11-19): what this PR takes
I checked each item against the current repo and this plan.
| # | Finding | Decision |
|---|---|---|
| 1 | CLAUDE.md `workflow:` copies `.claude/rules/claude-tooling.md` Workflow | **Fix, but invert the issue's direction.** The rule loads only on `.claude/**`, CI and `deploy/tests` paths, so deleting the CLAUDE.md copy would remove the workflow from most sessions. CLAUDE.md stays the always-on owner (compressed). The rule's Workflow block keeps only items that CLAUDE.md does not have (ros2-reviewer, domain-skill mapping, new-sensor rule). |
| 2 | `lab:` parsed from CLAUDE.md | Defer to follow-up (conflicts with PR #22) |
| 3 | Stack pins copied in claude-tooling.md:16, CLAUDE.md:20, drivers.md | **Fix.** Owner: `firmware/esp32/platformio.ini` and `docs/dependencies.md`. The copies become pointers. |
| 4 | drivers.md:17 wrong path `rccar_drivers/slamtec/*` | **Fix**: `ros2_ws/src/rccar_drivers/rccar_drivers/slamtec/`; delete the copied Workflow block |
| 5 | Versions in skills | **Fix hw-research**: description becomes one "Use when..." sentence; versions point to the owner. The pcb-design and pcb-fab references go to the consolidation plan (PR #22 edits those skills). |
| 6 | pcb-lab-config copies milling.toml values | Consolidation plan (PR #22 conflict) |
| 7 | firmware.md 50 lines (budget 40) | **Fix**: move detail to `docs/firmware/README.md` (the rule is edited anyway for the pinout pointer) |
| 8 | README 188 lines | **Fix** (step 6). The pin map stays in the root README because the user asked for it. The daily command table stays short; `make help` owns the full list. |
| 9 | `docs/README.md` index | **Fix** (step 5) |
| 10 | `plan:` points outside `docs/plans/`; slamtec plan maybe done | **Fix**: rename the key to `roadmap: docs/docker_ros_plan.md`; mark its "Target layout" section as replaced by ADR-0001. Read `docs/lidar/README.md`: if the slamtec plan is done, `git mv` it to `docs/archive/plans/`, else add `Status: active`. |
| 11 | `.claude/procedures/errors` path does not exist | **Fix** wording: "strict for `.claude/**`, procedures and error strings" |
| 12 | `make context` target | **Fix**: add target `context` that runs `~/.claude/skills/project-context/scripts/context_check.py .`. It prints a WARN and exits 0 if the script is missing. Use it in Verification. |
Also: do not grow `.claude/rules/writing.md`. Do not edit `.claude/rules/schematics.md` (PR #22 edits it); its invariant pointer goes to the follow-up. The PR body says "Refs #20" and lists the done and deferred items. The issue stays open for items 2, 5 (pcb), 6.

## Target layout
```
README.md          rewritten (4 sections)
.claude/           CLAUDE.md slimmed (@docs/invariants.md import); rules globs re-prefixed
docs/              README.md (new index), invariants.md (new), adr/ (new), interfaces/ (sensor_contract.md, ros2.md moved), hardware.md (new)
ros2_ws/           README.md, CLAUDE.md, .gitignore (build/ install/ log/), repos/ (was repos/), src/rccar_* (8 packages)
firmware/          README.md, CLAUDE.md (new); esp32/ unchanged
pcb/               CLAUDE.md (new); README.md: only the stale `mill/` line is fixed
models/            unchanged (README exists)
simulation/gazebo/ README.md placeholder; simulation/COLCON_IGNORE
mechanical/        README.md placeholder; COLCON_IGNORE
deploy/ docker/ scripts/ logs/ tuning.toml Makefile   stay at root
```

## Steps (TDD: red first; one commit per step; Conventional Commits; author Claude via `git -c`)

1. **Red: guard tests** (`deploy/tests/`, `make unit`):
   - New `test_layout.py`: each `package.xml` outside `firmware/` is under `ros2_ws/src/`; no `rccar_*` dir at the root; each root subproject (`ros2_ws`, `firmware`, `pcb`, `models`, `simulation`, `mechanical`, `docs`) has `README.md`; `simulation/`, `mechanical/` have `COLCON_IGNORE`, `ros2_ws/` has none; `docs/invariants.md` exists and `.claude/CLAUDE.md` imports it; `docs/adr/0000-template.md` exists.
   - Make silent repo-root lookups fail loudly: `rccar_mcu_bridge/test/test_tuning.py` (skip), `rccar_bringup/test/test_tuning_params.py` (return), `test_bringup_launch.py`, `test_sim_launch.py` (skipTest). Today they skip when `tuning.toml` is missing. After the move `parents[2]` would point at `ros2_ws/src`, and CI would stay green with the checks off. Stricter check: stated in the PR.
   - `test_claude_agents.py` `PATH_RE`: also check backticked `ros2_ws|firmware|pcb|models|simulation|mechanical/` paths (stricter check).
   - `test_contract.py`: each row of the new "Source" column in the contract table names an existing path (red until step 3).
   - `test_render_env.py` literals `/home/pi/ros2_ws/src/racecar` → `/home/pi/racecar`.
   - `test_layout.py` also checks that each relative image or link target in `README.md` files outside `docs/archive/` exists.
   - Run `make unit`. The new tests must fail (red).
2. **Move packages**: `git mv rccar_* ros2_ws/src/`, `git mv repos ros2_ws/repos`. Fix paths:
   - Package tests: replace `parents[2]` / `'..','..'` with a walk-up to the dir that holds `tuning.toml` (a few lines per test file, no new package).
   - `docker/ros.Dockerfile` COPY lines (:24-36, :47-57, :81-88): `ros2_ws/src/<pkg>` → `src/racecar/ros2_ws/src/<pkg>`, `ros2_ws/repos/`. `tuning.toml`, `main.cpp` stay at `src/racecar/`. Dockerignore: add `simulation`, `mechanical`.
   - `.claude/hooks/hw_guard.py:33` `DRIVER_PATHS` and `deploy/tests/test_hw_guard.py` literals → `ros2_ws/src/rccar_drivers/`, `ros2_ws/src/rccar_description/`.
   - `deploy/tests/test_contract.py` paths; `pyrightconfig.json` include; `.gitignore`.
   - `.github/workflows/ros.yml` (filters :7,:23; loops :139-145; `interfaces-sync` diff :161) and `firmware.yml` (`rccar_msgs/**` filter); `.claude/agents/ros2-reviewer.md:27`; `.claude/rules/msgs.md:12` sync command.
   - `.claude/rules/*.md` `paths:` globs: prefix `ros2_ws/src/` in calibration, drivers, hw-testing, mcu_bridge, msgs, plugins, rangefinder, ros2, supervisor, tuning; `repos.md` → `ros2_ws/repos/**`. `test_rules_paths.py` proves that each glob matches.
   - Keep all existing COLCON_IGNORE files. The compose mount and the future sim workspace see the whole repo, and `firmware/` holds a duplicate `rccar_msgs`.
   - Run `make unit`, `make ros-test`, `make build`. All pass (green).
3. **Docs and pointers**:
   - `git mv docs/sensor_contract.md docs/ros2.md docs/interfaces/`. Update every pointer: rules, skills, agents, PR template, `test_contract.py`, `docs/sim/README.md`, other docs.
   - Contract table: add a "Source" column (code path for each row). `sim-parity` SKILL table drops its own path list and reads the Source column (one owner, tested).
   - `hw-research` description: pinned versions → pointer to `docs/dependencies.md` (the owner; add any version it lacks).
   - Path prose: `docs/{setup,deploy,claude-tooling,docker_ros_plan,lidar/*}.md`, `models/README.md`. Clone path `~/ros2_ws/src/racecar` → `~/racecar` in `docs/setup.md`, with a migration note for the existing Pi.
4. **Invariants and ADR workflow**:
   - `docs/invariants.md` owns the 6 invariants (moved from `.claude/CLAUDE.md:12-18`, STE strict). `.claude/CLAUDE.md` loads it with `@docs/invariants.md`: always in context, one owner. `.claude/rules/supervisor.md:10` points to it (`schematics.md:21`: follow-up, PR #22 conflict).
   - `docs/adr/README.md` (index), `0000-template.md` (status, context, decision, consequences), `0001-monorepo-layout.md` (this change, incl. the kept container layout and the `~/racecar` clone path).
   - `.claude/CLAUDE.md` workflow line: "change to an invariant, the repo layout or an interface => ADR in docs/adr/ first". PR template: one checkbox "ADR / invariants impact".
   - Existing bug: `scripts/close.py:12` reads `docs/plan`; the real dir is `docs/plans`, so the done-plan check never runs. Write the test first in `deploy/tests`, then fix.
5. **Subproject READMEs and nested CLAUDE.md** (README about 30 lines: purpose, pointers. CLAUDE.md 20 lines or fewer: pointers and local verify commands, no copy of a rule):
   - `ros2_ws/README.md`; `ros2_ws/CLAUDE.md` (verify: `make ros-test`, `make unit`, pyright; msgs sync pointer).
   - `firmware/README.md` (points to `docs/firmware/README.md`); `firmware/CLAUDE.md` (verify: `make build`, `make compiledb` + clangd; bench `make test` is user-run).
   - `pcb/CLAUDE.md` (verify: `make pcb-test`, `make pcb-check BOARD=src`); `pcb/README.md:7` stale `mill/` → `src/`.
   - `simulation/README.md`, `simulation/gazebo/README.md`, `mechanical/README.md`: placeholders with purpose and planned content.
   - The `tests:` line in the root `.claude/CLAUDE.md` shrinks to a pointer. The commands for each subtree go into the nested files.
   - New `docs/README.md`: one line per entry.
   - **One key visual in each human README where a true one exists.** A diagram has 10 lines or fewer and its facts come from code or the owner doc, not from memory. GitHub renders Mermaid, and the terminal shows it as text.
     - root: Mermaid system diagram in the compute stack section (Pi 5 ROS stack, micro-ROS agent over UART, ESP32, servo and ESC, sensors), plus the existing ASCII pinout
     - `pcb/README.md`: `docs/pcb/power_architecture.png`
     - `ros2_ws/README.md`: Mermaid node/topic graph (teleop and other sources, supervisor, `/rccar/mcu/drive`, micro-ROS agent, ESP32; mapper_driver). Topic names come from `docs/interfaces/`.
     - `firmware/README.md`: Mermaid task/data flow from `docs/firmware/README.md`
     - `simulation/README.md`: Mermaid of the sim boundary (gz, then virtual MCU and Mapper, then the same car nodes) from `docs/sim/README.md`
     - `mechanical/README.md` and `models/README.md`: no visual yet (no content to draw)
6. **Root README rewrite** (about 80 lines):
   - (a) Layout table: folder | 1 sentence | key link. Links: `ros2_ws/src/`, `firmware/esp32/`, `pcb/src/` (active mill board), `simulation/`, `docs/README.md`.
   - (b) Daily command table: `make open`, `make close`, `car-up`, `car-ps`, `teleop`, `car-logs`, `car-shutdown`, `rangefinder`, `viz`, `help`.
   - (c) Compute stack table.
   - (d) Pinout: keep the diagram and table identical to `firmware/esp32/include/pins.h`.
   - Moved sections: inventory, rangefinder wiring, power rules and power-up sequence → new `docs/hardware.md`. Once-per-Pi, sensor and "when needed" tables → `docs/setup.md`; add the missing "after `git pull`" row. Session and plugin notes → `docs/claude-tooling.md`. Fix links: `docs/setup.md:53,131`, `docs/rangefinder/README.md:14`, `.claude/rules/rangefinder.md:15,17`, `.claude/rules/firmware.md:36`, `docs/firmware/README.md:3`.
   - Write `docs/plans/<date>-skill-consolidation.md` (Status: active, follow-up after PR #22). Contents: merge pcb-lab-config + pcb-milling-check; sim-parity → interface-change (sim in-repo); new car-deploy and firmware-change skills that take procedures out of rules; plugin-dev:skill-reviewer runs in that PR.
7. **Simplify and review**: run `simplify` on the test and helper code. Then independent reviews: `ros2-reviewer`, `project-context-reviewer`, `code-review`. Fix each finding, then rerun the checks.
8. **PR** "refactor: move to monorepo layout" from `restructure`. Body: `.github/pull_request_template.md` with the user-run Pi checklist below. Add a "Follow-up" section that links `docs/plans/<date>-skill-consolidation.md` (and the `lab:` TOML move) as the next task. Wait for CI (`gh pr checks --watch`).

## Verification
Local (amd64 dev host). Each check must pass, with output:
- `make unit`: new layout, rules-glob, contract (Source column), hw_guard, agent-path and close.py tests
- `make ros-test`: colcon build + test in docker; tuning/firmware checks now fail instead of skipping
- `make build` (firmware; `extra_packages` unchanged), `make pcb-test`
- `diff -r ros2_ws/src/rccar_msgs firmware/esp32/extra_packages/rccar_msgs`: empty
- `make config` then `docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated config`: mounts unchanged
- `make context` (project-context check script): no dead pointers or orphans; sizes within budget for the files this PR touches
- `git grep -nE '(^|[^/])rccar_[a-z_]+/' -- ':!ros2_ws' ':!docs/archive'`: review each hit (a package name, not a stale path)
- CI green on the PR (ros, firmware, pcb workflows)

Dev workflow (dev host, after the move; output shown for each):
- `make close`, then `make open`: both exit 0 with no new WARN line. `close.py` now finds `docs/plans/`.
- `make check-host`, `make dev-setup` (`uv sync --frozen`, `direnv allow`), `make help` (target list unchanged except new targets)
- LSP: pyright diagnostics clean on `ros2_ws/src` and `deploy/` (`uv run pyright`); `make compiledb`, then clangd resolves `firmware/esp32/src/main.cpp`
- Claude Code context: open a file in `ros2_ws/src/rccar_supervisor/` and check that `.claude/rules/supervisor.md` and `ros2_ws/CLAUDE.md` load. Edit a file in `ros2_ws/src/rccar_drivers/` while the drivers container runs (simulated by `test_hw_guard.py`), and check that `hw_guard` still denies.
- `make pcb-test`: `lab.py` still finds `lab:` in `.claude/CLAUDE.md`

User-run on the Pi (PR checklist; agents never start hardware), in this order:
1. `cd ~/ros2_ws/src/racecar && make car-down`
2. `mv ~/ros2_ws/src/racecar ~/racecar && cd ~/racecar` (keeps the untracked `.env` and `logs/`)
3. `git fetch && git switch restructure && make dev-setup` (the `.venv` has absolute paths, so uv rebuilds it)
4. `make install-host` (rewrites the `rccar.service` WorkingDirectory)
5. `make ros-image && make car-up && make car-ps` (all healthy)
6. `make teleop` (arm, steer, brake, disarm), `make rangefinder`, `make lidar-snapshot`, `make mcu CMD="GET"`
7. Reboot once and check `make car-ps` (the boot service starts from the new path)

No `make flash` is needed: the firmware sources do not change.

Not verified by agents: the arm64 image on the Pi, live hardware behavior, and a racecar-sim build at a new pin. The sim vcs-imports the whole repo, and colcon crawls `ros2_ws/src` recursively, so the sim build should work. It is checked when the sim bumps its pin or merges into this repo.
