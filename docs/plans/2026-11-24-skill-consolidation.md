# Plan: skill consolidation (branch `consolidate`, stacked PR on `restructure`)

Status: active

## Context
Follow-up of PR #23 (monorepo layout). Source plan: `docs/plans/2026-11-24-skill-consolidation.md`, issue #20 items 2, 5, 6. Problems:
- Procedures live in 18 path rules. ROS 2, firmware and deploy have no task skills.
- `pcb-lab-config` and `pcb-milling-check` overlap: 9 shared facts or steps, and each points to the other.
- Skills hold repo facts: kicad-happy `2.3.2` in 4 pcb reference lines, mill values in `pcb-lab-config`.
- Scripts parse `.claude/CLAUDE.md`: `pcb/libraries/lab.py`, Makefile:32.
- `schematics.md` is 41 lines (budget 40).
- Gaps: no `docker compose config` target, no msgs copy target, no test for the pins.h/README pinout sync.

Goal: a small set of task skills. Each skill does one task, reads its facts from the owner files, and has a Verify section. The rules keep only constraints. The always-on context cost goes down.

User decisions: `car-deploy` in `deploy/.claude/skills/`. `interface-change` at the root `.claude/skills/`. No pressure tests. One `plugin-dev:skill-reviewer` run for each new or changed skill.

## Branch and PR
- `git switch -c consolidate origin/restructure`. PR base = `restructure`. GitHub retargets it to `main` when #23 merges and its branch is deleted.
- PR #22 guard: do not edit its files (`docs/techctcarvera/milling.toml`, `tools/fab_export.py`, `tools/test_fab.py`, `tools/test_milling_check.py`, `docs/pcb/releases/rev3/review/README.md`, `docs/pcb/fab_handoff.md`). Their stale comments go on the merge-guard list in the PR body.
- Invoke `asd-ste100` (strict for `.claude/**`) before writing. Do not use superpowers skills (step 0 removes the plugin).

## Step 0: remove superpowers from the project (user request: too many tokens for small gains)
- Cost now: the SessionStart hook injects `using-superpowers` (3,192 chars, about 800 tokens) in each session, plus about 14 skill descriptions in the listing. Measure before and after in a headless session (`/context` or the listing), and put the numbers in the PR.
- `.claude/settings.json`: delete the `superpowers@claude-plugins-official` entry. The `claude-plugins-official` marketplace stays, because other plugins use it.
- Remove the mentions: `docs/claude-tooling.md:10` (plugin table), `docs/setup.md:35`, `docs/dependencies.md:27`, `.claude/CLAUDE.md:17,19`, and the superpowers skill names in `.claude/rules/claude-tooling.md` (writing-plans, requesting-code-review, verification-before-completion). Leave the old plans (`docs/plans/2026-11-01-slamtec-mapper.md:141` is a record).
- Keep its useful lessons, each at the place where it applies. Do not copy the user-scope skill `engineering-workflow`, which already owns plan, TDD, CI, review and report:
  - `.claude/CLAUDE.md` workflow (always-on, terse):
    - `non-trivial change => skill engineering-workflow (plan in docs/plans/, failing test first, independent review agent: ros2-reviewer, pcb-reviewer or code-review)`
    - `bug or flaky test => root cause before a fix: reproduce, read the full error, one hypothesis and one change at a time, no rerun until green; 3 failed fixes => stop and ask` (systematic-debugging)
    - `design choice => one question at a time, 2-3 options with a recommendation` (brainstorming)
  - The Verify section of each project skill ends with: "Claim a result only with the command output from this session. A check you did not run is 'not run'." (verification-before-completion)
  - `.claude/rules/ros2.md`: "A flaky launch test: find the cause first. Match the QoS of the publisher (durability, reliability) before you add a wait." This is the PR #23 lesson (`test_supervisor_launch.py`).
  - Skill writing (writing-skills): `test_claude_agents.py` already enforces "Use when" descriptions and the size limit. Step 1 adds the Verify-section test. No other copy.

## Steps (TDD: red test first; one commit per step)
1. **Red tests** (`deploy/tests/`):
   - `test_claude_agents.py`: each `SKILL.md` has a `## Verify` section. Skill and reference files hold no `x.y.z` version (same regex as `context_check.py`).
   - New `test_pinout.py`: the GPIO numbers of the active pins in `firmware/esp32/include/pins.h` equal the root README pin table (owner rule: `firmware.md:32`).
   - `pcb/libraries/test_lab.py`: `read_pointer()` reads `pcb/config/lab.toml` (key `dir`). A missing key raises. `.claude/CLAUDE.md` is not read.
2. **`lab:` to TOML** (issue #20 item 2):
   - New `pcb/config/lab.toml` (`dir = "docs/techctcarvera"`).
   - `lab.py` reads it with `tomllib`. `LAB_DIR` env still overrides.
   - Makefile:32 reads the TOML (`sed`). Also `LAB_DIR ?=`, and `KICAD_RUN` passes `-e LAB_DIR`. This fixes the found gap: a shell `LAB_DIR` had no effect in the container.
   - `.claude/CLAUDE.md` `lab:` line becomes a pointer to `pcb/config/lab.toml`. Update `docs/techctcarvera/README.md`, `docs/pcb/README.md:22`, `pcb/libraries/paths.py:7`, `tools/milling_check.py:4` (not a PR #22 file).
   - Verify: `make pcb-test`, `make pcb-mill-check BOARD=src`.
3. **`pcb-mill`** = merge of `pcb-lab-config` + `pcb-milling-check` in `pcb/.claude/skills/pcb-mill/`:
   - `SKILL.md`: lab file (fill or change), run, loop, report, rules, Verify. One description, under 776 chars (the two old ones use 776).
   - `references/mill-rules.md`: the 16 MILL-* ids.
   - `references/gap-defaults.md`: the generic start values, labeled "not this lab". Every value of this lab points to its `milling.toml` or `design_rules.toml` key.
   - Rename every reference: `pcb-reviewer.md:17`, `pcb-design` (SKILL :28,:29,:41, board-loop :27, check-matrix :11,:29, intake :12, lessons :50), `pcb-parts` :15,:53, `docs/pcb/conventions.md:65`, `docs/techctcarvera/README.md`, `tools/milling_check.py:3`.
   - Remove kicad-happy `2.3.2` from `kicad-happy.md:3` and `fab-gate.md:18,23,28`. Point to `.claude/settings.json` (plugin ref) and `docs/dependencies.md`.
4. **`interface-change`** (rename of `sim-parity`, moved to the root `.claude/skills/`):
   - Steps: message change, then the copy, then the fan-out (from `msgs.md:12-13`), then the contract "Sources" table, then the sim. Flash together with the new Pi image (`msgs.md:17`). Verify: `make checks`, `make unit`, `make build`, `make ros-test`.
   - New make target `msgs-sync` (copy to `firmware/esp32/extra_packages/`). `msgs.md` points to it.
   - Update the 8 references: `test_contract.py:125`, `sensor_contract.md:7,42`, `ros2-reviewer.md:38`, `docs/sim/README.md:9`, `.claude/CLAUDE.md:10`, PR template :15, `ros2.md:11`, `firmware.md:36`.
5. **`firmware-change`** in `firmware/.claude/skills/firmware-change/`:
   - Procedures:
     - key change across 3 files (`tuning.md:16`, `rangefinder.md:28`)
     - `CFG_MAGIC` bump
     - clean build after a `rccar.meta` or `extra_packages` change
     - pins.h and README pinout sync (test from step 1)
     - new sensor (points to `docs/firmware/README.md` "New sensor")
     - toolchain volume reset (`dependencies.md:22`)
   - Verify: `make build`, `make compiledb` + clangd, `make ros-test` (`test_tuning.py`), `make checks`.
   - User-run only: `flash`, `monitor`, `make test`, the PR bench checklist.
6. **`car-deploy`** in `deploy/.claude/skills/car-deploy/`:
   - Procedures:
     - a render_env or `[platform.*]` key change (`tuning.md:15`)
     - image digest bump (`dependencies.md:20`)
     - `drivers-stop` before a rebuild
     - the deploy, replug and shutdown sequences (points to `docs/deploy.md` "Operations")
     - `make dev-setup` on the Pi
     - the PR "Deploy" checklist
   - New make target `config-check` (`make config` + `docker compose ... config -q`).
   - Verify: `make checks`, `make unit`, `make config-check`.
   - User-run: the `.claude/settings.json` ask list.
7. **Rules shrink to constraints and pointers:**
   - `firmware.md`, `tuning.md`, `msgs.md`, `rangefinder.md`, `deploy.md`, `dependencies.md`, `hw-testing.md`: remove the moved procedures and duplicates (deploy.md:26-29 = docs/deploy.md:42-45; hw-testing.md:15 = :20). Add a pointer to the skill's `SKILL.md`, so path work outside the skill folder finds it.
   - `schematics.md`: drop L33 (in 3 other places) and merge L40-41, to 40 lines or fewer.
   - `.claude/CLAUDE.md` `skills:` line: list the nested folders (`pcb/`, `firmware/`, `deploy/`).
8. **Docs:**
   - Update `docs/plans/2026-11-24-skill-consolidation.md` to this plan (Status: active), then to done and archived at the end.
   - Update `docs/claude-tooling.md` (skill locations).
   - ADR? No. This is not an invariant, layout or interface change.
9. **Review:** enable `plugin-dev@claude-plugins-official` for this session with local scope (`.claude/rules/plugins.md`). Run the `plugin-dev:skill-reviewer` agent on `pcb-mill`, `interface-change`, `firmware-change` and `car-deploy`. Fix the findings. Then run `project-context-reviewer` (context cost) and `code-review` on the diff. Then `make close` removes the local enable.
10. **PR:** "refactor(skills): consolidate the project skills". Body from the template, with:
    - the always-on cost before and after (root skill descriptions + `.claude/CLAUDE.md`)
    - the merge-guard list for PR #22
    - "Refs #20" (closes items 2, 5, 6)
    - wait for CI.

## Verification
- `make checks`, `make unit`, `make ros-test`, `make build`, `make pcb-test`, `make pcb-mill-check BOARD=src`, `make config-check` (needs `.env` and `ros-image`; if missing on the dev host, "not run").
- `make msgs-sync` then `git diff --exit-code firmware/esp32/extra_packages` (no change).
- `make context`: no new warning.
- Headless Claude Code sessions:
  1. At the root, the listing shows `hw-research` and `interface-change` only.
  2. After a read of `firmware/README.md`: `firmware-change` appears.
  3. After a read of `deploy/car/compose.yaml`: `car-deploy` appears.
  4. After a read of `pcb/README.md`: `pcb-mill` appears, and neither old pcb skill name appears.
- `make open` / `make close`: exit 0.
- CI green on the stacked PR.
- Not verified: hardware. No car behavior changes, so the bench checklist is only "no change".
