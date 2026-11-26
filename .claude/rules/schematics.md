---
paths:
  - "pcb/**"
  - "docs/pcb/**"
  - "docs/techctcarvera/**"
---

# PCB (power distribution board)

Workflow: skill `pcb-design`. Fab outputs and releases: skill `pcb-fab`. Review: agent `pcb-reviewer`. The pcb skills are in `pcb/.claude/skills/` and load when you read a file in `pcb/`. Outside `pcb/`, read their `SKILL.md` first. Facts and conventions (layout, design rules, sources of truth, rails, connectors, pin order, board tools): `docs/pcb/conventions.md`. Mill tuning loop: `docs/techctcarvera/README.md`.

## Sources and generated files
- The schematic is the source for the board. Change parts and nets in the schematic first.
- The only deliverable of a board is its `.kicad_pcb` file. Do not make export files (`make pcb-fab`, Gerbers) as a deliverable. Make them only when the owner asks. Scope: `docs/pcb/conventions.md`.
- Never invent a part value. Unknown is `TBD`.
- Do not edit generated files by hand: variant schematics (`make pcb-sch`), `.kicad_pro` net classes and `.kicad_dru` (`make pcb-rules`), `bom.csv` (`make bom`), fab outputs (`make pcb-fab`, not committed).
- Limits come from `design_rules.toml` and the lab file. Do not add a limit as a constant to a tool. Never change a limit, a waiver or a check to make a board pass.
- Never tune or rebuild a release in `pcb/releases/`. The working mill board is `pcb/src` (rebuilt with `--force` by `make pcb-all`: put changes into `placement.py` or the design rules).
- A spec change that contradicts `docs/pcb/power_board_plan.md` updates the plan in the same change, or ask.
- Save the projects only with KiCad 10. Do not downgrade the file format.

## Design invariants
- Rails: `VBAT`, `+5V_CPU` (Pi 5 and ESP32 only), `+5V_SENS`, `+3V3_SENS`, `+6V_BEC` (servo only, never joined to a 5 V rail). One common `GND`. Rails are project power symbols from `rc_power.kicad_sym`.
- The ESP32 powers nothing. Sensors never take power from ESP32 pins. Signals are 3.3 V or less (invariants 1 and 2, `docs/invariants.md`).
- Every net that feeds a power_in pin through a fuse or a ferrite has a PWR_FLAG.
- U1 EN never connects directly to an ESP32 GPIO. Future control goes through a transistor.
- One replaceable main fuse F1. Size VBAT_RAW, VBAT and GND copper for the fuse rating, not the load.
- Keep the connector families and the XH pin-order rules A, B and C (`docs/pcb/conventions.md`). Keep the crimp table in `docs/pcb/fab_handoff.md` in step with the schematic.
- Never claim that a current "fits" or is "within rating" without a check. J3 and J4 run at 100 % of the XH pin rating.
- Pi 5 and ESP32 power leaves through USB-C pigtails (J6, J7), so their input protection stays in the path.

## Board
- After every board change, run `make pcb-check pcb-mill-check`. DRC clean does not mean millable.
- Never put F.Cu copper on a THT pad. Never put a via inside a part courtyard. No courtyard overlaps another one or crosses the board edge. Module footprints carry the real body.
- Never make a hole between the largest drill and `milled_hole_min`.
- Do not route a reviewed board again from zero. Do not change a J3, J4, J5 or J8 orientation without a new `make pcb-route`.
- Never use the KiCad native DXF for the mill. `make pcb-fab` writes the lab frame.

## Analyzers
- kicad-happy findings are claims. Check each one against the raw files and the datasheets. Known false positives: `docs/pcb/releases/rev1/review/README.md` and `pcb/.claude/skills/pcb-fab/references/fab-gate.md`.
- ERC and DRC results count only with their KiCad 10 output from this session.
