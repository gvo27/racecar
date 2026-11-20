# Rev3 milling findings

This log records the findings of the rev3 milling, one entry for each finding. The board is `pcb/src/rc_power_board.kicad_pcb`. A finding that changes a lab value also changes `milling.toml` in the lab directory (`lab:` in `.claude/CLAUDE.md`). That file holds the current value. This log holds the history.

Status of an entry: `verified` (measured or seen on the real board or the machine), `reported` (a statement that nobody checked yet).

## F-001: dowel holes need more clearance (2026-11-19, verified)

- Found: during the rev3 milling. The dowel pins measure 4.0 mm with a caliper.
- Old value: dowel hole 4.191 mm (0.165 in), from the lab CAM template (Bore1).
- Change (owner): add 0.003 in (0.0762 mm) to the hole. New hole: 4.2672 mm (0.168 in). The clearance on the 4.0 mm pin changes from 0.191 mm to 0.267 mm (diameter).
- Changed: `[dowel]` in `milling.toml`. The fab export reads the value from there (`DOWEL_4.267` in the drill map and the Excellon file).
- Effect: more clearance permits more shift between the two faces after the flip, up to about 0.27 mm (was about 0.19 mm).
- Open: the lab CAM template (Bore1, `example/` in the lab directory) still bores 4.191 mm. The lab tech must change Bore1 to 4.2672 mm.
