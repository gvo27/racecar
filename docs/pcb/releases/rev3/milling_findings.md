# Rev3 milling findings

This log records the findings of the rev3 milling, one entry for each finding. The CAM brief for the lab tech: `docs/plans/2026-11-20-rev3-milling-brief.md`. The board is `pcb/src/rc_power_board.kicad_pcb`. A finding that changes a lab value also changes `milling.toml` in the lab directory (`lab:` in `.claude/CLAUDE.md`). That file holds the current value. This log holds the history.

Status of an entry: `verified` (measured or seen on the real board or the machine), `reported` (a statement that nobody checked yet).

## F-001: dowel holes need more clearance (2026-11-19, verified)

- Found: during the rev3 milling. The dowel pins measure 4.0 mm with a caliper.
- Old value: dowel hole 4.191 mm (0.165 in), from the lab CAM template (Bore1).
- Change (owner): add 0.003 in (0.0762 mm) to the hole. New hole: 4.2672 mm (0.168 in). The clearance on the 4.0 mm pin changes from 0.191 mm to 0.267 mm (diameter).
- Changed: `[dowel]` in `milling.toml`. The fab export reads the value from there (`DOWEL_4.267` in the drill map and the Excellon file).
- Effect: more clearance permits more shift between the two faces after the flip, up to about 0.27 mm (was about 0.19 mm).
- Closed (owner 2026-11-25): the lab bores the widened 4.2672 mm hole. The first hole was too narrow and was widened.

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

## F-003: the V-bit on hand can mill B.Cu (2026-11-20, reported)

- Bit: Makera "Single Flute Engraving Bit for Metal", QR code `C1-BIT-ENGRAVE-M-30-0.2`, 1/8 in shank, 30 deg, 0.2 mm tip (`[inventory.bits_on_hand]` in `milling.toml`).
- Owner: the bit measures the same as T2. The lab tech: T2 in the lab CAM template comes from Makera and is correct.
- Owner observation: the cone is not symmetric (one side is higher). Both slant lengths are longer than the shank diameter (more than 3 mm).
- Agent analysis (not measured): a single-flute engraving bit has one flat ground face, so a cone that is not symmetric is the usual shape. For a cone from a 0.2 mm tip to a 3.175 mm shank, the slant length is about 3.0 mm at 30 deg per side (T2) and about 5.7 mm at 30 deg included. A slant length a little more than 3 mm agrees with T2. A slant length near 5.7 mm means 30 deg included.
- Viable for B.Cu with either reading: the cut width at 0.08 mm depth is 0.292 mm (per side) or 0.243 mm (included). Both are less than the smallest B.Cu gap (U3, 0.34 mm). The 0.6 mm corn bit is not (F-002).
- Open: the slant length in mm on the cutting side, or the width of a test groove at 0.08 mm depth (0.29 mm or 0.24 mm).

## F-004: Fusion 360 limits the engraving bit on B.Cu (2026-11-20, open)

- Found (lab): Fusion 360 does not let the engraving bit (T2, a chamfer mill in the tool library) do all B.Cu milling. It seems to allow the bit only for some operations.
- Leads (not confirmed, Autodesk forum and help, read 2026-11-20): users report "invalid tool" errors for a chamfer mill in some milling operations (for example adaptive clearing). The 2D Adaptive help says rest machining needs the geometry of the previous tool (diameter, corner radius, taper angle, shoulder length). The lab template already uses T2 in 2D Contour.
- Possible workaround (not tested): T2 in 2D Contour (or Trace) for the isolation. A flat end mill (0.6 mm corn bit, or the 0.2 mm micro end mill, `[inventory.bits_on_hand]`) for pocket or rest operations.
- Open: the Fusion version, the operation and the exact error text.

## F-005: the lab CAM file of the failed rev3 run (2026-11-25, reported)

- Source: the Fusion file of the lab tech, read by the agent. File (user paths removed) and facts with status: [`cam/`](cam/README.md). The run failed (owner). The next run waits for the 0.2 mm end mills.
- Dowels (lab standard): the two setup origins are 145.8468 mm apart, equal to `[dowel] centers` in `milling.toml`. The dowel hole is 4.2672 mm (F-001).
- Model: the board is not flipped. F.Cu is on the top face and B.Cu on the bottom face, both at the true board position. Setup3 flips the frame (`flipZ`) and starts at the second dowel point.
- Z0 (cause of the failure, agent analysis): the operator probes Z0 on the board surface (owner). The CAM expects Z0 at the sketch points: 0.065 mm above the F.Cu surface (Setup5) and 0.075 mm below the B.Cu surface (Setup3). With a probed Z0, F.Cu is cut 0.14 mm deep and B.Cu is not cut. Fix in the CAM: set the WCS Z origin of each setup to the stock top.
- Isolation is a pocket with the 0.6 mm corn bit (F-002). The 0.2 mm rest pass is only on B.Cu. No V-bit pass.
- T6 (0.2 mm end mill in the CAM) has a 4 mm shank and does not fit the 1/8 in collet. Its feed is 0.1 mm/tooth. The lab uses the generally recommended cutting data of the real bit (owner).
- Holes: the 1.3 mm J6/J7 holes are drilled at 1.1 mm. The rivet via at KiCad (68.1, 42.1) is not drilled. Tools are staged by exact spec between rounds (owner): `make pcb-mill-check` lists them (F-006).
- Flood coolant on 3 tools, the machine has air only. No outline cut. No NC code in the file.

## F-006: the milling check uses the lab CAM isolation tools (2026-11-25)

- `[[isolation_bit]]` in `milling.toml` is now the 0.6 mm corn bit and the 0.2 mm end mill (flat, cut width = diameter). The V-bit (T2) is not in the lab CAM (F-004).
- `MILL-GAP-BIT` now uses the horizontal error: the corn bit fits a gap of 1.1 mm or more, the 0.2 mm end mill a gap of 0.7 mm or more. The rev3 board has 127 areas where only the 0.2 mm end mill fits: the lab CAM needs the rest pass on both faces there.
- `make pcb-mill-check` lists the tools to stage, with exact specs: drills 0.8, 1.0, 1.1, 1.3 and 1.4 mm, the 3.175 mm end mill, the corn bit and the 0.2 mm end mill. 8 tools for 6 slots: more than one round.
- Board: no change. The rev3 board passes with the lab CAM tools: 0 errors.
