# PCB projects (power distribution board)

| Path | Content |
| --- | --- |
| `releases/rev_A/` | The rev A board: KiCad project (`rc_power_board.kicad_sch`, `.kicad_pcb`, `.kicad_pro`, `.kicad_dru`), lib tables, `bom.csv` (from `make bom`), schematic plot |
| `lib/` | Symbol and footprint libraries, shared by all boards (`rc_power.kicad_sym`, `rc_power.pretty/`) |
| `libraries/` | Board tools, their Python libraries and tests. They run in the KiCad image through `make`. `paths.py` holds this layout |
| `COLCON_IGNORE` | Keeps this directory out of the ROS 2 build |

- Fab outputs are not committed. `make pcb-fab` writes them to `build/fab/<BOARD>/`.
- Context of the board and the schematic (plan, overview, BOM notes, review record): [`docs/pcb/`](../docs/pcb/README.md). Stale docs: `docs/archive/pcb/`.
- Lab facts, mill tools and waivers: the lab directory (`lab:` line in [`.claude/CLAUDE.md`](../.claude/CLAUDE.md)).
- Rules: [`.claude/rules/schematics.md`](../.claude/rules/schematics.md).
- Make targets: `make help`. A target works on one board: `make pcb-check BOARD=<path below pcb/>`. The default is `BOARD` in the Makefile (`releases/rev_A`).
