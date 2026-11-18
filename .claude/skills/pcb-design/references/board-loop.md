# Schematic and board loops

## Work rules (each edit)
- Tools run in the KiCad image through `make` targets. Do not use the host Python. Do not install software.
- A tool or check change starts with a failing test in `pcb/libraries/test_*.py` or in `tools/test_*.py` of the lab directory. Then make it pass.
- Change parts and nets in the schematic first. Then update the board. Never add a part only on the board.
- Do not route a reviewed board again from zero (`make pcb-route`) without a reason. Use `build_pcb.py --sync-fields`, `--sync-zones`, `--sync-drills` or a local edit.
- Never change a value in the lab file, a design rule or a waiver to make a check pass. Never use `--force` on `pcb-build` on an owner board.
- An unknown part value stays `TBD`. Write the source of each new fact: datasheet page, owner statement with the date, or measurement.
- A statement in a document about a dimension or a width comes from a check that can fail. If no check exists, add one, with its test first.
- Commit each step with its check output in the body.

## Checks after each edit
- Schematic change: `make erc bom`.
- Board, footprint or placement change: `make pcb-check pcb-mill-check pcb-test`, and `make pcb-fab` when copper or holes changed.
- Tool change: `make pcb-test`.
- Before a review: `make pcb-gate` (and `METHOD=mill` for the mill board).

## Schematic loop (owner gate 2)
1. Do one task from the plan: one region or one concern.
2. Run the schematic rows of `check-matrix.md`. Read the diff.
3. When all rows pass, dispatch `pcb-reviewer` (fresh context). Fix each finding and run the checks again. Repeat until the reviewer gives no blocker and no major finding.
4. Give the owner the schematic PDF, the ERC output, the BOM, the power budget and the open questions. Do not start the board before the owner approves the schematic.

## Board loop
1. Order of work: outline and mounting, connectors on the edge, power-path placement, power copper as planned zones, signal routing, checks, fab outputs.
2. After each change, run the board rows of `check-matrix.md`. Method "mill" adds skill `pcb-milling-check`.
3. Make the fab outputs again when the copper or the holes change.
4. When all rows pass, dispatch `pcb-reviewer`. Fix and repeat as in the schematic loop.

## Mill board
The tuning loop of the mill board (`pcb/mill`, the mill tuning file, `make pcb-all BOARD=mill`) is in `docs/techctcarvera/README.md` "Tune a prototype". `pcb-all` rebuilds the board with `--force`: put each change into `placement.py` or the design rules, never into the GUI.
