---
name: pcb-fab
description: Use when someone asks "Is this board ready to order?" or "ready to mill?", before fab outputs (Gerbers, drill files, DXF, Excellon) go to a fab house or the lab mill, when a BOM or order files for JLCPCB, PCBWay, LCSC, DigiKey or Mouser are needed, or when a board in pcb/ becomes a release. Runs the kicad-happy fab release gate and gives the deliverables for each manufacturing method. Keywords - fab release gate, BOM export, CPL, order files, Gerber, DFM, release.
---

# PCB fab deliverables

A board is ready only when the gate, the project checks and an independent review agree. This skill makes the deliverables and the evidence. The owner places the order.

## References
| File | Use |
| --- | --- |
| `references/fab-gate.md` | The 8 gate categories, how to read them here, known false positives, the last results |
| `references/workflow.md` | The 7-step upstream workflow of kicad-happy and how this project runs each step |

## Step 0
1. Check that the kicad-happy skills (`kicad`, `bom`, `jlcpcb`, `pcbway`) are in your skill list. If not, follow `.claude/rules/plugins.md`.
2. Know the method: `fab` (fab house) or `mill` (the lab mill). Ask the owner if the plan does not say it.

## Gate
1. Run the project checks first, with output: `make erc bom pcb-check pcb-test BOARD=<board>`. Method mill also: `make pcb-mill-check BOARD=<board>`.
2. Run `make pcb-gate BOARD=<board>` (`METHOD=fab|mill`). Read the verdict line `Gate: PASS|WARN|FAIL`. The exit code is 0 also for FAIL.
3. Give each WARN and FAIL line a verdict: true, false positive (add it to `references/fab-gate.md` with the evidence), or owner decision.
4. Dispatch `pcb-reviewer` with the scope "fab" and `build/gate/<BOARD>/`.

## Deliverables
**Method fab (fab house):**
- Gerbers and the drill file: `make pcb-gate METHOD=fab` writes them to `build/gate/<BOARD>/gerbers/`. Load the skill `jlcpcb` or `pcbway` for its layer names and limits.
- BOM and order files (kicad-happy `bom`, run in the KiCad image, output below `build/order/<BOARD>/`):
  - `bom_manager.py export <schematic> -o build/order/<BOARD>/bom.csv`
  - `bom_manager.py order build/order/<BOARD>/bom.csv -o build/order/<BOARD>/ --boards <N> --spares <S>`: DigiKey, Mouser and LCSC files with the quantities for N boards plus spares.
  - JLCPCB assembly: `translate_bom_pnp.py bom` and `translate_bom_pnp.py pnp` (BOM and CPL). Check basic and extended parts with the skill `lcsc`.
- The committed BOM stays `pcb/<BOARD>/bom.csv` (`make bom`). Do not commit the order files: they depend on the board count.

**Method mill (lab mill):**
- `make pcb-fab BOARD=<board>`: DXF (F.Cu, B.Cu, Edge.Cuts), Excellon and the drill-map DXF in the frame of the lab CAM template (`build/fab/<BOARD>/`). `test_fab` must pass.
- The parts list is `pcb/<BOARD>/bom.csv`. The loop for the next print round: `docs/techctcarvera/README.md` "Tune a prototype".

## Release
A release freezes a board in `pcb/releases/rev<N>/` with its own `design_rules.toml`. The next number follows the last release (`pcb/README.md`). Set the title-block revision: `<N>` for a release, `<N> (draft)` for a board in work. Never tune a release.

## Report
1. The gate verdict and each line with its verdict.
2. The project checks with their result lines from this run.
3. The deliverables with their paths.
4. Owner decisions (TBD parts, silkscreen, method limits that are `assumed`).
5. What was not checked (for example, no SPICE without `ngspice`, no supplier stock without API keys).
