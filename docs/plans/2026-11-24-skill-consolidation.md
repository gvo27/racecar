# Plan: consolidate the project skills

Status: active (follow-up of the monorepo layout PR, ADR 0001)

## Context
The monorepo layout PR took the hard-coded paths out of `sim-parity` (the "Sources" table of `docs/interfaces/sensor_contract.md` is now the owner, and `test_contract.py` checks it) and the stack pins out of `hw-research` (owner: `docs/dependencies.md`, "Stack pins"). A review with the user skill `project-context` and issue #20 found these open items:

- 7 project skills: 5 for the PCB (now in `pcb/.claude/skills/`), `hw-research` (root) and `sim-parity` (now in `ros2_ws/.claude/skills/`). Nested skills load only when Claude reads a file in their folder. ROS 2, firmware and deploy have no task skills. Their procedures are in 18 rules that load by path.
- `pcb-lab-config` and `pcb-milling-check` overlap: both read the lab limits of the mill.
- `pcb-lab-config` copies mill values that `docs/techctcarvera/milling.toml` owns (issue #20, item 6).
- `pcb-design/references/kicad-happy.md:3` and `pcb-fab/references/fab-gate.md:18` contain versions (issue #20, item 5).
- `pcb/libraries/lab.py` and the Makefile read the `lab:` line of `.claude/CLAUDE.md`. A script must not read CLAUDE.md (issue #20, item 2).
- `.claude/rules/schematics.md` has 41 lines (budget 40).

## Principles (user scope)
- Each project skill does one domain task, holds its scripts and references, and tells how to verify its result.
- A skill holds no repo facts. It reads them from their owner (a doc, a config file, a table that a test checks).
- Literal paths stay only where the harness needs them (rule `paths:`, the hook). A test checks each of them.

## Proposed steps
1. Merge `pcb-lab-config` and `pcb-milling-check` into one skill `pcb-mill` (lab limits, inventory, milling check). The skill points to `milling.toml` for the values.
2. Move the versions in the pcb skill references to `docs/dependencies.md` and point to it.
3. Rename `sim-parity` to `interface-change`. It covers a message change (copy to the firmware), the contract, and the sim. When the sim moves into `simulation/`, the steps edit the sim in the same PR.
4. Add `firmware-change` in `firmware/.claude/skills/`: pins, `setKey`, tuning keys, message copy, `make build`, `make compiledb`, the bench checklist for the PR. Move the procedures out of `.claude/rules/firmware.md`, `tuning.md` and `msgs.md`. The rules keep the constraints.
5. Add `car-deploy` (root `.claude/skills/`, because deploy is shared infrastructure): image, compose, render_env and udev changes, `make unit`, `docker compose config`, the Pi bench checklist. Move the procedures out of `.claude/rules/deploy.md` and `hw-testing.md`.
6. Move the `lab:` value to a TOML file (for example `pcb/config/lab.toml`). `lab.py` and the Makefile read the TOML file. `.claude/CLAUDE.md` points to it.
7. Run the agent `plugin-dev:skill-reviewer` on each new or changed skill (the user chose to run it in this follow-up, not in the layout PR).

## Verify
- `make unit` (`test_claude_agents.py` checks the skill frontmatter and the paths that the skills name), `make pcb-test`, `make context`.
- The always-on token cost of the skill descriptions goes down or stays the same.
