# Rev A power board: review package

Scope (owner, 2026-11-11): a valid, DRC-clean, routed KiCad PCB **for review only**. There are no Gerber, drill or CAM files. The lab tech gives those steps later. The milling rules still apply to the board.

Rebuild: `make kicad-image pcb-review`. All tools run in the pinned KiCad 10.0.8 image. Freerouting 2.5.0 runs in its own pinned image (`make pcb-route`).

## Files

| File | Content |
| --- | --- |
| `drc.json` | `kicad-cli pcb drc --schematic-parity --severity-all`: 0 errors, 14 warnings, 0 unconnected items, parity clean. |
| `milling_check.json` | Milling check (`make pcb-mill-check`). Groups: errors, waived, questions, bits, warnings. |
| `rc_power_board_layers.pdf` | One page per layer: F.Cu, B.Cu, F.Fab, B.Fab (each with Edge.Cuts). |
| `rc_power_board_1to1.pdf` | Scale 1: pads, holes and fab outlines. Print at "actual size" on A4 landscape. The board is at the top-left of the page. Use it for the paper check with real parts. |

## Board

- Outline 66 x 140 mm (limit 70 x 146 mm). Drill/place origin at the lower-left corner. 2 layers, 0.070 mm copper, 1.57 mm total.
- **Rivet vias: 5.** Four make two F.Cu jumpers (`I2C_SDA`, `I2C_SCL`). One ties the F.Cu GND pour to B.Cu GND. All are 1.2 mm drill / 2.1 mm pad (assumed). No via is inside a part courtyard.
- Placement: input chain (J1, F1, C1, D1) at the bottom end; the VBAT trunk goes up between U2 (left) and U1 (right). Left edge: J6, J7, J5, J4, J3, J8, J11, J9 (compute and sensor wiring). Right edge: J12 to J14 (3.3 V). The 3.3 V chain (U3, FB1, C6 to C8) is at the top right.
- `VBAT_RAW`, `VBAT` and GND are B.Cu zones. The trunks are at least 6 mm wide. At the U1 header the VBAT neck is 2.35 mm wide for about 4.5 mm (pin pitch). This is below the HighCurrent track width of 6.0 mm and carries the U1 input current (about 4.4 to 4.7 A). IPC-2221 for 2 oz copper gives about 1.4 mm at 5 A. Owner to accept or change.
- Net-class widths: `+5V_CPU` has one 1.03 mm neck (class width 1.6 mm) near J6/J7, where the router could not keep 1.6 mm. Other power tracks keep their class width. Signal tracks are 0.5 mm.

## Checks run (this build)

| Check | Result |
| --- | --- |
| `make erc` | 0 errors, 3 warnings (`lib_symbol_mismatch`, D2 to D4: owner GUI step "Update Symbols") |
| DRC with schematic parity | 0 errors, 0 unconnected items, parity clean; 14 `lib_footprint_mismatch` warnings (see below) |
| `make pcb-check` (`check_board.py`) | 0 problems: no F.Cu copper on a THT pad, every hole in the bit set or in `MILLED_HOLES`, all vias 1.2/2.1 mm, no narrow HighCurrent track |
| `make pcb-mill-check` | 0 unwaived errors, 0 waived, 0 MILL-GAP-BIT areas, 7 MILL-SLIVER warnings, 1 owner/lab-tech question (MILL-DEPTH) |
| `make pcb-test` | 64 tests pass |

**MILL-DEPTH (question for the owner and the lab tech).** With the assumed depth range 0.10 to 0.15 mm and a depth error of +-0.05 mm, the minimum depth is 0.05 mm. This is below the copper thickness of 0.070 mm, so a shallow cut may not go through the copper. The minimum depth must be at least 0.12 mm. The check keeps this as an error. It is a finding about the limits, not about the board. Exit code of `make pcb-mill-check` is 1 because of this finding.

**DRC warnings.** 14 x `lib_footprint_mismatch` (C9, F1, J3 to J9, J11 to J14, U1; J6 and J7): the board copies of these footprints have snapped drills and grown pads (annular ring 0.45 mm). The stock libraries are not changed.

**Milling warnings.** 5 x MILL-SLIVER on the F.Cu pour (0.06 to 0.43 mm2 slivers beside THT pads) and 2 x MILL-SLIVER on the B.Cu pour at U3 (0.37 and 0.50 mm2). No island remains: the F.Cu pour is one piece with one stitching via. Pour pieces smaller than 200 mm2 are dropped.

## Assumptions (all "assumed": lab tech to confirm)

- Drill set 0.8, 1.0, 1.2, 1.5 mm. Holes larger than 1.5 mm are milled (smallest end mill 1.0 mm).
- Rivet via 1.2 mm drill / 2.1 mm pad. The 0.8 mm EasyContac rivet (1.0 mm OD) sits about 0.1 mm loose before soldering.
- Cut depth 0.10 to 0.15 mm, depth error +-0.05 mm (see MILL-DEPTH). Isolation bits 30 deg / 0.2 mm tip and 60 deg / 0.1 mm tip. Cut width at the worst-case depth (0.20 mm): 0.307 mm and 0.331 mm. The smallest copper gap on the board is 0.35 mm (U3 pads).
- U2 is the Pololu D24V90F5 (assumed). The footprint comes from Pololu's drawing (tolerance of drill location +-0.1 mm). Terminal-block holes and M2 holes are not in the footprint (terminal-hole diameter TBD).
- No reverse-polarity protection (owner decision). U3 keeps the stock SOT-23-5 footprint and rule `U3_fine`.
- XH and terminal-block orientation: pin 1 at the bottom on the left edge (J4 is rotated 270 degrees: pin 1 at the top, body toward the edge). This order makes the PWM, BEC and I2C nets routable with only two jumpers. Wire entry direction of the vertical XH headers is not checked: check it with the 1:1 print.

## Owner GUI checks (user-run)

1. Open the schematic in KiCad 10: Update Symbols from Library (D2 to D4), run ERC, re-plot the PDF.
2. Open the board: 3D view (pin 1 marks, fuse access, no collisions, J4 body next to the edge), run DRC.
3. Print `rc_power_board_1to1.pdf` at actual size. Put the real parts on the print: U2 footprint against the real Pololu module, F1 holder, XH headers, J6/J7 terminal blocks, C1, C9.
4. Check the F.Cu jumpers and the five rivets: each rivet needs both sides soldered.
5. Do not run `make pcb-build --force` or `make pcb-route` over a board with manual edits.

## Review tools (kicad-happy plugin 2.3.2): findings and what was done

The plugin analyzers ran on the board (`analyze_schematic.py`, `analyze_pcb.py --full`, `cross_analysis.py`, `analyze_emc.py`). SPICE, thermal, lifecycle and gerber analysis were not run (no simulator or Gerber files, no MPNs, review-only scope). Treated as claims; each was checked against the board.

| Finding | Check | Action |
| --- | --- | --- |
| SS-001 sourcing blocker: 0 of 27 parts have an MPN | True: part values are `TBD` by project rule | None. MPNs wait for part choices. |
| PU-001 U1 PG and U3 EN "missing pull-up" | False positive: the ESP32 input pull-up serves PG (see `power_board_plan.md`); U3 EN is tied to its input | None. |
| TE-001 test point coverage 0 of 16 nets | Partly true: TP1 to TP3 exist on `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`; no other net has a test point | Listed. Add test points only if the owner wants them. |
| PM-002 J1 is 0.8 mm from the edge | By design: wire pads at the edge; copper edge clearance is 0.5 mm and checked | None. |
| PS-002 `VBAT` plane split in 6 islands | False positive: the bus is several overlapping zones. The union of their fills is one piece (checked with pcbnew); DRC has 0 unconnected items | None. |
| CC-DET `+5V_CPU` 1.03 mm minimum trace | True: one neck near J6/J7 (class width 1.6 mm) | Listed above. About 3 A on `+5V_CPU` is within 1.03 mm at 2 oz copper by IPC-2221 (about 1.0 mm at 3 A); owner to accept. |
| EMC GP-001 and RP-001: `I2C_SCL`, `I2C_SDA` (also `STEER_PWM`, `THROTTLE_PWM` partial): reference plane gap and layer change without a GND via | True for the two F.Cu jumpers (about 30 mm each, over a B.Cu GND zone that tracks cut). I2C runs at 100 to 400 kHz, so the risk is low. | Not changed: a GND rivet beside each jumper via adds rivets. Owner to decide. |
| EMC VS-001 via stitching insufficient | True: one GND via on the F.Cu pour | Not changed. The F.Cu pour is a shield and copper balance only. |
| EMC SW-001 U1 harmonics in 30 to 88 MHz | Module property (Pololu D36V50F5 switching) | Lab pre-compliance test. |
| EMC score | 82 of 100 | None. |

## Open questions for the owner

1. Accept the 2.35 mm VBAT neck at the U1 header and the 1.03 mm `+5V_CPU` neck?
2. Accept the two F.Cu jumpers (4 rivets) for I2C, or change the connector order (needs a new route)?
3. Add GND rivets beside the jumper vias, or more test points?
4. Lab tech: bit list, rivet hole, minimum cut depth (MILL-DEPTH), dowel size.
5. J1 wire-pad size is TBD; the stock footprint pads (4.4 mm, 3.0 mm drill) are a placeholder.
