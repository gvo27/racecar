# PCB projects (power distribution board)

| Path | Content |
| --- | --- |
| `releases/rev1/` | The rev1 board, the base board: KiCad project (`rc_power_board.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.kicad_dru`), lib tables, `bom.csv` (from `make bom`), schematic plot, `placement.py`, `design_rules.toml` |
| `releases/rev2/` | Rev2 release: a frozen copy of the mill prototype with the JST XH headers, with its own `design_rules.toml` (2026-11-17). Do not tune it |
| `mill/` | The mill prototype (now with temporary wire solder pads for the first print round, `[parts.wire]` of the mill tuning file): the rev1 circuit without the LEDs and their resistors, with through-hole capacitors for C2 to C8, and with wider tracks and gaps for the lab mill. Made by `make pcb-all BOARD=src` from `mill/placement.py` and the mill tuning file (`design_rules.toml` in the lab directory). Its next release is `releases/rev3/` |
| `lib/` | Symbol and footprint libraries, shared by all boards (`rc_power.kicad_sym`, `rc_power.pretty/`) |
| `libraries/` | Board tools, their Python libraries and tests. They run in the KiCad image through `make`. `paths.py` holds this layout |
| `COLCON_IGNORE` | Keeps this directory out of the ROS 2 build |

- The only deliverable of each board is its `.kicad_pcb` file (scope: `docs/pcb/conventions.md`). Fab outputs are optional and not committed. `make pcb-fab` writes them to `build/fab/<BOARD>/`.
- Context of the board and the schematic (plan, overview, BOM notes, review record): [`docs/pcb/`](../docs/pcb/README.md). Stale docs: `docs/archive/pcb/`.
- Releases are numbered `rev1`, `rev2`, `rev3` and so on (rev1 and rev2 were `rev_A` and `rev_B` until 2026-11-18). A release is frozen: copy the working board to `releases/rev<N>/` with its own `design_rules.toml`.
- Risks of the mill board, most important first: [review record](../docs/pcb/releases/rev3/review/README.md#risks-most-important-first).
- Lab facts, mill tools and waivers: the lab directory (`lab:` line in [`.claude/CLAUDE.md`](../.claude/CLAUDE.md)).
- Rules: [`.claude/rules/schematics.md`](../.claude/rules/schematics.md).
- Design rules: `design_rules.toml` in the board directory, or in the lab directory for a board without its own file (`mill/`). `make pcb-rules BOARD=<board>` checks the KiCad project files against them.
- Make targets: `make help`. A target works on one board: `make pcb-check BOARD=<path below pcb/>`. The default is the base board (`BASE_BOARD` in the Makefile, `DEFAULT_BOARD` in `libraries/paths.py`).
