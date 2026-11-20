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

## F-002: B.Cu isolation with a 0.6 mm corn bit, about 40 min (2026-11-20, reported)

- Found: during the rev3 milling (owner). The B.Cu isolation uses a 0.6 mm corn bit, not the T2 V-bit of the lab CAM template. The B.Cu run takes about 40 min.
- Expected bit: T2 of the lab CAM template, chamfer mill "0.1mm Tip Engraving Metal", 0.2 mm tip, 30 deg per side (60 deg included), cut width 0.292 mm at 0.08 mm depth (`[inventory.cam_tools]` in `milling.toml`).
- Stock on hand (owner 2026-11-20): no corn bit below 0.6 mm. One V-bit, 1/8 in shank, 30 deg, 0.2 mm tip (`[inventory.bits_on_hand]`). Its angle reading (included or per side) is not confirmed.
- The isolation limits are not changed. `[[isolation_bit]]` in `milling.toml` is still the 60deg/0.2 V-bit (cut width 0.292 mm at 0.08 mm depth). The milling check and the mill tuning file (`clearance` 0.8 mm = 0.292 mm + 2 x 0.25 mm) use that bit.
- Risk (agent analysis from the review record, not measured): a 0.6 mm flat bit cuts a groove of about 0.6 mm. It cannot cut a gap narrower than 0.6 mm. On B.Cu, these gaps are smaller than 0.6 mm or almost equal to it:
  - U3 (SOT-23-5): 0.34 to 0.35 mm, pad to pad and zone to pad. The CAM can leave copper there (a bridge), or the cut can remove pad copper.
  - Wire pads J3, J4, J5, J8, J9, J11 to J14: 0.6 mm, pad to pad. The cut fits only with no X/Y error.
  - U1 and U2 VOUT to GND: 0.64 mm. Margin 0.02 mm for each side. The tuning file assumes 0.25 mm.
- Check after the B.Cu run: examine these gaps for bridges and for damaged pads. Measure the real groove width.
- Open (owner): record the corn bit in `milling.toml` (name, tip, flutes) if it stays the B.Cu tool. A 0.6 mm cut width then needs a clearance of about 1.1 mm (0.6 mm + 2 x 0.25 mm) in the mill tuning file for the next board.
