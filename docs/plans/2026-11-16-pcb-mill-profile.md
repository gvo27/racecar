# Plan: mill tuning file and mill prototype board

Date: 2026-11-16. Owner request, approved in the session. Status: done on branch `pcb-mill` (first prototype layout). Follow-up items are at the end.

## Goal
The lab mill is not accurate in X and Y. The owner wants one config file that describes the limits of a board for this mill, so that small changes propagate quickly across several prototypes. The rev A board stays as it is for a fab house.

## Decisions of the owner
- Same parts and footprints on the mill board. U3 stays SOT-23-5. The 0805 parts stay.
- No surface mount LEDs on the mill board: D2, D3, D4 and their resistors R1, R2, R3 are removed.
- The 2 mm target applies between different components and to nearby tracks. Gaps that a footprint fixes are listed exceptions.
- Two board directories with shared tools. Mill tools and mill config are in the lab directory.

## Design
- `design_rules.toml` for each board (`pcb/tools/rules.py`). `pcb/fabhouse/design_rules.toml` holds the rev A values. The mill tuning file is `design_rules.toml` in the lab directory. A board without its own file uses it.
- The tools read all limits from the rules: `build_pcb.py`, `route_pcb.py`, `check_board.py`, `milling_check.py`. `gen_rules.py` (`make pcb-rules`) writes them into `.kicad_pro` and `.kicad_dru`.
- `variant.py` (`make pcb-sch`) makes the mill schematic from the rev A schematic and the exclude list.
- `pcb/<board>/placement.py` holds the board data. The mill file loads the rev A file and changes it.
- New milling rules: `MILL-GAP` with the horizontal error, `MILL-GAP-FIXED`, `MILL-CUT-SPACING`, `MILL-COMP-GAP`.
- `make pcb-all BOARD=mill` runs all steps after a rule change.

## Limits of the approach
- The design rules do not move parts. A rule change that the placement cannot keep makes a check fail. Then a person or an agent changes `pcb/mill/placement.py`.
- The component gap is measured between pads on different nets, not between courtyards. A 2 mm courtyard gap between all parts does not fit the 66 mm wide outline (modules, connectors).

## Follow-up
- Lab tech: confirm the values of the tuning file (questions in `review/README.md` of the lab directory).
- Review of the mill board by `pcb-reviewer` and by the owner.
- `MILL-ISLAND` warning on `+5V_SENS`: examine.
- Lessons for `.claude/skills/pcb-design-check/lessons.md` after the review.
