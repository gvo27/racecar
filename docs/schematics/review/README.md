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
- **Rivet vias: 3.** Two make one F.Cu jumper for `U1_PG` (U1.1 to J5.1, about 75 mm on F.Cu; rivets at (52.0, 23.9) and (3.4, 52.1)). The jumper is planned in `placement.py` (`JUMPERS`). Without it the `U1_PG` track would cut the GND trunk between U2 and U1. One rivet ties the F.Cu GND pour to B.Cu GND. All are 1.2 mm drill / 2.1 mm pad (assumed). No via is inside a part courtyard. The router does not place vias (the baseline board had 5 rivets, with two I2C jumpers).
- Placement: input chain at the bottom end. J1 is turned 180 degrees: GND is on the left, BAT+ on the right, and F1 is above BAT+. U2 is at the left, U1 at the right. J6 and J7 are now on the right edge next to U1, so `+5V_CPU` is a short peninsula and does not cross the board. Left edge, from the bottom: J4, J3, J5, J8 (turned 180 degrees), J11, J9. Order and turns come from a planarity check of the edge pins: with this order the PWM, BEC and I2C nets run in B.Cu without a crossing. Right edge: J6, J7, J12 to J14. The 3.3 V chain (U3, FB1, C6 to C8) is at the top right.
- `VBAT_RAW`, `VBAT`, `+5V_CPU` and `+5V_SENS` are planned B.Cu zones in `placement.py` (`BUS_ZONES`). GND is the B.Cu pour. `GND_KEEPOUTS` keep router tracks out of the GND trunks (left trunk J1 to U2, corridor U2 to U1). No power zone joins two board edges.
- **Copper width along the current paths** (opening test on B.Cu, `check_board.py`; `make pcb-check` fails below the need; pads narrower than the opening are measured at their own width, with the copper within 2.5 mm of the pad counted):

| Path | Need | Baseline (e0ba889) | This board |
| --- | --- | --- | --- |
| GND: J1.2, U2 input GND, U1.7 to U1.10 | 6.0 mm | 0.59 mm | 8.00 mm or more (test limit) |
| GND: J6.2, J7.2, U1.7 to U1.10 | 1.6 mm | 0.59 mm | 4.07 mm |
| GND: U2 output GND, J8.2, J9.2, J11.2, C9.2 | 1.6 mm | 1.38 mm | 1.76 mm |
| `VBAT_RAW`: J1.1, F1 | 6.0 mm | 6.48 mm | 6.18 mm |
| `VBAT`: F1, U2.1, U1.5, U1.6 | 6.0 mm | 2.35 mm | 6.30 mm |
| `+5V_CPU`: all pads | 1.6 mm | 1.00 mm | 1.67 mm |
| `+5V_SENS`: all pads | 1.6 mm | 1.58 mm | 1.79 mm |

- The earlier statement that the GND trunks are at least 6 mm wide was not true for the baseline board. The opening test now checks it.
- The narrowest GND path is 1.76 mm: the strip west of the J11 and J9 pins. J11.2 sits between `+5V_SENS` pads J11.1 and J9.1, so its only GND path is this strip. J11 and J9 are 0.25 mm further from the edge than J4, J5, J8 and J3 to make the strip 1.6 mm or more.
- The U2 signal-row VOUT pad has no number now (as the PG and FB pads). It has no net, and the router adds no track to it.

## Checks run (this build)

| Check | Result |
| --- | --- |
| `make erc` | 0 errors, 3 warnings (`lib_symbol_mismatch`, D2 to D4: owner GUI step "Update Symbols") |
| DRC with schematic parity | 0 errors, 0 unconnected items, parity clean; 14 `lib_footprint_mismatch` warnings (see below) |
| `make pcb-check` (`check_board.py`) | 0 problems: no F.Cu copper on a THT pad, every hole in the bit set or in `MILLED_HOLES`, all vias 1.2/2.1 mm, no narrow HighCurrent track |
| `make pcb-mill-check` | 0 unwaived errors, 0 waived, 0 MILL-GAP-BIT areas, 8 MILL-SLIVER and 4 MILL-ISLAND warnings, 1 owner/lab-tech question (MILL-DEPTH) |
| `make pcb-test` | 73 tests pass |

**MILL-DEPTH (question for the owner and the lab tech).** With the assumed depth range 0.10 to 0.15 mm and a depth error of +-0.05 mm, the minimum depth is 0.05 mm. This is below the copper thickness of 0.070 mm, so a shallow cut may not go through the copper. The minimum depth must be at least 0.12 mm. The check keeps this as an error. It is a finding about the limits, not about the board. Exit code of `make pcb-mill-check` is 1 because of this finding.

**DRC warnings.** 14 x `lib_footprint_mismatch` (C9, F1, J3 to J9, J11 to J14, U1; J6 and J7): the board copies of these footprints have snapped drills and grown pads (annular ring 0.45 mm). The stock libraries are not changed.

**Milling warnings.** 8 x MILL-SLIVER (3 on the F.Cu pour beside THT pads, 2 on the B.Cu pour at U3, 2 on `+5V_SENS` and 1 on `VBAT` where a zone edge meets a pad). 4 x MILL-ISLAND: parts of the overlapping bus zones of `+5V_CPU` (1), `+5V_SENS` (2) and `VBAT` (1) that touch no pad or track. The check does not join overlapping zones, so these are not real islands. Pour pieces smaller than 200 mm2 are dropped.

## Assumptions (all "assumed": lab tech to confirm)

- Drill set 0.8, 1.0, 1.2, 1.5 mm. Holes larger than 1.5 mm are milled (smallest end mill 1.0 mm).
- Rivet via 1.2 mm drill / 2.1 mm pad. The 0.8 mm EasyContac rivet (1.0 mm OD) sits about 0.1 mm loose before soldering.
- Cut depth 0.10 to 0.15 mm, depth error +-0.05 mm (see MILL-DEPTH). Isolation bits 30 deg / 0.2 mm tip and 60 deg / 0.1 mm tip. Cut width at the worst-case depth (0.20 mm): 0.307 mm and 0.331 mm. The smallest copper gap on the board is 0.35 mm (U3 pads).
- U2 is the Pololu D24V90F5 (assumed). The footprint comes from Pololu's drawing (tolerance of drill location +-0.1 mm). Terminal-block holes and M2 holes are not in the footprint (terminal-hole diameter TBD).
- No reverse-polarity protection (owner decision). U3 keeps the stock SOT-23-5 footprint and rule `U3_fine`.
- XH and terminal-block orientation: pin 1 at the bottom on the left edge, except J4 and J8 (rotated 270 degrees: pin 1 at the top). J6 and J7 on the right edge also have pin 1 at the top. Deviation from the rule "pin 1 at the same end": it is needed for B.Cu routing without rivets. J8 turned means the Garmin pin order runs top to bottom. Wire entry direction of the vertical XH headers is not checked: check it with the 1:1 print.

## Owner GUI checks (user-run)

1. Open the schematic in KiCad 10: Update Symbols from Library (D2 to D4), run ERC, re-plot the PDF.
2. Open the board: 3D view (pin 1 marks, fuse access, no collisions, J4 body next to the edge), run DRC.
3. Print `rc_power_board_1to1.pdf` at actual size. Put the real parts on the print: U2 footprint against the real Pololu module, F1 holder, XH headers, J6/J7 terminal blocks, C1, C9.
4. Check the F.Cu jumper and the three rivets: each rivet needs both sides soldered.
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
| CC-DET `+5V_CPU` 1.03 mm minimum trace | Fixed: `+5V_CPU` is a planned zone, at least 1.67 mm wide | None. |
| EMC GP-001 and RP-001: layer change without a GND via | Applies to the `U1_PG` jumper only (a slow status signal). The I2C and PWM nets stay on B.Cu. | Not changed: a GND rivet beside each jumper via adds rivets. Owner to decide. |
| EMC VS-001 via stitching insufficient | True: one GND via on the F.Cu pour | Not changed. The F.Cu pour is a shield and copper balance only. |
| EMC SW-001 U1 harmonics in 30 to 88 MHz | Module property (Pololu D36V50F5 switching) | Lab pre-compliance test. |
| EMC score | 82 of 100 | None. |

## Open questions for the owner

1. Accept the `U1_PG` F.Cu jumper (2 rivets, about 75 mm, partly under the U2 body), or move J5 next to U1?
2. Accept J4, J8, J6 and J7 with pin 1 at the top, J1 turned 180 degrees (GND left), and J11 and J9 0.25 mm further from the edge?
3. Add a GND rivet beside each jumper via, or more test points?
4. Lab tech: bit list, rivet hole, minimum cut depth (MILL-DEPTH), dowel size.
5. J1 wire-pad size is TBD; the stock footprint pads (4.4 mm, 3.0 mm drill) are a placeholder.
