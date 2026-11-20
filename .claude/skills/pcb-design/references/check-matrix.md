# Check matrix

A clean ERC and a clean DRC show that the files agree with their own rules. They do not show that the board does its job. This file lists all the checks and what each one cannot find. All commands run in the pinned KiCad 10 image (`make kicad-image` first). A result counts only with its output from the current session.

| Scope | Command | Pass condition | Manual review (the command cannot find this) |
| --- | --- | --- | --- |
| Schematic | `make erc` | 0 errors. Each warning has a written reason | Pin-to-net against each datasheet note. PWR_FLAG on nets behind a fuse or a ferrite. Wires between parts in one region (labels only between regions) |
| Schematic | kicad-happy `kicad`: `analyze_schematic.py` | Each finding has a verdict | Known false positives: `docs/pcb/releases/rev1/review/README.md` and `.claude/skills/pcb-fab/references/fab-gate.md` |
| Parts | `make bom`, then `git diff --stat pcb/<BOARD>/bom.csv` | No diff. No part without `Status` | Skill `pcb-parts`: budget, ratings, mating connectors, lifecycle |
| Board | `make pcb-check` | DRC 0 errors, 0 unconnected items, parity clean. `check_board` 0 problems | Each DRC warning type has a written reason. Copper width along each current path is in `PATH_ROWS` |
| Board | `make pcb-mill-check` (method "mill") | 0 errors that are not waived | Skill `pcb-milling-check`. Solder access and rivet access |
| Board | `make pcb-gate` (kicad-happy analyzers: schematic, PCB, EMC, thermal, and Gerbers for a fab house) | Each finding has a verdict. Gate result read with `fab-gate.md` of skill `pcb-fab` | Return path of each signal that changes layer. Parts under module bodies |
| Tools | `make pcb-test` | All tests pass | A new check has a test that fails on a bad board |
| Fab outputs (only when the owner asks for them) | `make pcb-fab` (writes `build/fab/<BOARD>/`, not committed) | `test_fab` passes. Same files after a second run on the same board | Frame, units, mirror state, hole count for each tool against the board |
| Documents | `grep` each number of the review record in the check output | Each number agrees | Statements with no check behind them |
| Subcircuits | kicad-happy `spice` (needs `ngspice`) | Only if `ngspice` is installed | Without `ngspice`: write "SPICE not run" in the report |

## Triage
1. Give each finding one verdict: **true** (fix it), **false positive** (write the reason and the evidence), **owner decision** (put it in the report).
2. Check a finding in the raw file before you act. An analyzer reads patterns. It does not know this board's decisions.
3. Add a new false positive, so the next review does not spend time on it: an analyzer finding of the board goes to the table in `docs/pcb/releases/rev1/review/README.md`, a fab release gate line goes to `.claude/skills/pcb-fab/references/fab-gate.md`.
4. A true finding that a check could find again becomes a check with a test (`pcb/libraries/`, or `tools/` in the lab directory for a mill check).

## Design principles (review each one, write a line for each in the report)
- **Power:** budget for each rail from datasheet maximum values. Regulator output at the minimum input voltage, with dropout. Fuse at 75 % or less of its rating for the continuous load. Copper sized for the fuse rating.
- **Parts:** one part family where possible, a part in hand before a new part, an active part from a known manufacturer (skill `pcb-parts`).
- **Connectors:** one family for the board. One written pin-order rule. Keyed or locking types on a vehicle.
- **Physical use:** vibration (heavy parts held, locking connectors, strain relief), heat (derating graph at the real input voltage, air space), battery (cutoff voltage, start current of each load), service (fuse access, test points, labels).
- **Manufacture:** the method limits come from the lab file (skill `pcb-lab-config`) or from the fab house. A footprint shows the real body of the part.
- **Schematic style:** wired connections between parts in a region, one label for each bus, no crossings, GND as symbols.

