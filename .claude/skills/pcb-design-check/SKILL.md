---
name: pcb-design-check
description: Use when a KiCad schematic or board in docs/schematics/ is created, changed or reviewed, before a claim that the schematic or the board is correct, complete or ready for review, and before a report to the owner. Gives the check matrix for schematic, board, part compatibility, fab outputs and design principles, and points to the lessons list. Keywords - ERC, DRC, design review, verification, check my board, kicad-happy, power budget.
---

# PCB design check (schematic, board, compatibility, principles)

A clean ERC and a clean DRC show that the files agree with their own rules. They do not show that the board does its job. This skill lists all the checks and what each one cannot find.

Read `lessons.md` in this directory before a design step or a review. Each lesson comes from an error on this project.

## Check matrix
All commands run in the pinned KiCad 10 image (`make kicad-image` first). A result counts only with its output from the current session.

| Scope | Command | Pass condition | Manual review (the command cannot find this) |
| --- | --- | --- | --- |
| Schematic | `make erc` | 0 errors. Each warning has a written reason | Pin-to-net against each datasheet note. PWR_FLAG on nets behind a fuse or a ferrite. Wires between parts in one region (labels only between regions) |
| Schematic | kicad-happy `kicad`: `analyze_schematic.py` | Each finding has a verdict | Known false positives: `.claude/rules/schematics.md` and `docs/schematics/review/README.md` |
| Parts | `make bom`, then `git diff --stat docs/schematics/bom.csv` | No diff. No part without `Status` | Skill `pcb-parts`: budget, ratings, mating connectors, lifecycle |
| Board | `make pcb-check` | DRC 0 errors, 0 unconnected items, parity clean. `check_board` 0 problems | Each DRC warning type has a written reason. Copper width along each current path is in `PATH_ROWS` |
| Board | `make pcb-mill-check` (method "mill") | 0 errors that are not waived | Skill `pcb-milling-check`. Solder access and rivet access |
| Board | kicad-happy `kicad`: `analyze_pcb.py`. kicad-happy `emc`: `analyze_emc.py` | Each finding has a verdict | Return path of each signal that changes layer. Parts under module bodies |
| Tools | `make pcb-test` | All tests pass | A new check has a test that fails on a bad board |
| Fab outputs | `make pcb-fab`, then `git status --short docs/schematics/fab` | No diff after a second run on the same board | Frame, units, mirror state, hole count for each tool against the board |
| Documents | `grep` each number of the review record in the check output | Each number agrees | Statements with no check behind them |
| Subcircuits | kicad-happy `spice` (needs `ngspice`) | Only if `ngspice` is installed | Without `ngspice`: write "SPICE not run" in the report |

## Run the kicad-happy analyzers
The scripts use the Python standard library. Use the plugin directory of the installed version (`installPath` of `kicad-happy@kicad-happy` in `~/.claude/plugins/installed_plugins.json`). Run them with `python3` in the KiCad image, with the plugin directory mounted read-only. Write the output below `build/` or `docs/schematics/analysis/` (run directories are in `.gitignore`).

```
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD":"$PWD" -v "$KH":"$KH":ro -w "$PWD/docs/schematics" rccar-kicad:local \
  python3 "$KH/skills/kicad/scripts/analyze_pcb.py" rc_power_board.kicad_pcb --output "$PWD/build/analysis/pcb.json"
```

Read each script's `--help` first: the options change between plugin versions. Load the kicad-happy skill (`kicad`, `emc`) for the meaning of the rule ids.

## Triage
1. Give each finding one verdict: **true** (fix it), **false positive** (write the reason and the evidence), **owner decision** (put it in the report).
2. Check a finding in the raw file before you act. An analyzer reads patterns. It does not know this board's decisions.
3. Add a new false positive to the table in `docs/schematics/review/README.md`, so the next review does not spend time on it.
4. A true finding that a check could find again becomes a check with a test (`docs/schematics/tools/`).

## Design principles (review each one, write a line for each in the report)
- **Power:** budget for each rail from datasheet maximum values. Regulator output at the minimum input voltage, with dropout. Fuse at 75 % or less of its rating for the continuous load. Copper sized for the fuse rating.
- **Parts:** one part family where possible, a part in hand before a new part, an active part from a known manufacturer (skill `pcb-parts`).
- **Connectors:** one family for the board. One written pin-order rule. Keyed or locking types on a vehicle.
- **Physical use:** vibration (heavy parts held, locking connectors, strain relief), heat (derating graph at the real input voltage, air space), battery (cutoff voltage, start current of each load), service (fuse access, test points, labels).
- **Manufacture:** the method limits come from the lab file (skill `pcb-lab-config`) or from the fab house. A footprint shows the real body of the part.
- **Schematic style:** wired connections between parts in a region, one label for each bus, no crossings, GND as symbols.

## Report
Use the report order of `.claude/agents/pcb-designer.md` (phase 4). Never write "ready" or "verified" for a row that you did not run in this session.
