# Rev A power board: review package

Scope (owner, 2026-11-11): a valid, DRC-clean, routed KiCad PCB **for review only**. Task 9 (2026-11-13) adds the board fit to the lab's Fusion 360 template and the fab files in `../fab/` (DXF, Excellon; `make pcb-fab`). The CAM stays in the lab template. The milling rules still apply to the board.

Rebuild: `make kicad-image pcb-review`. All tools run in the pinned KiCad 10.0.8 image. Freerouting 2.5.0 runs in its own pinned image (`make pcb-route`).

## Files

| File | Content |
| --- | --- |
| `drc.json` | `kicad-cli pcb drc --schematic-parity --severity-all`: 0 errors, 16 warnings, 0 unconnected items, parity clean. |
| `milling_check.json` | Milling check (`make pcb-mill-check`). Groups: errors, waived, questions, bits, warnings. |
| `rc_power_board_layers.pdf` | One page per layer: F.Cu, B.Cu, F.Fab, B.Fab (each with Edge.Cuts). |
| `rc_power_board_1to1.pdf` | Scale 1: pads, holes and fab outlines. Print at "actual size" on A4 landscape. The board is at the top-left of the page. Use it for the paper check with real parts. |

## Board

- Outline 66 x 140 mm (limit 70 x 146 mm). Drill/place origin at the lower-left corner. 2 layers, 0.070 mm copper, 1.57 mm total.
- **Rivet vias: 3.** Two make one F.Cu jumper for `U1_PG` (U1.1 to J5.1, about 38 mm on F.Cu, along the north side of the two modules; rivets at (40.4, 49.8) and (3.4, 52.1)). The jumper is planned in `placement.py` (`JUMPERS`, with a B.Cu stub that keeps 0.4 mm from U1.2). One rivet ties the F.Cu GND pour to B.Cu GND. All are 1.1 mm drill / 2.1 mm pad (assumed). No via is inside a part courtyard. The router does not place vias (the check `check_board.py` counts them).
- Placement (Task 7c, 2026-11-12): U1 and U2 are the Pololu D36V50F5 with the real 25.4 mm body. Both stand side by side with the pin row on the north edge (rot 90): U2 body x 8.0 to 33.4, U1 body x 36.0 to 61.4, both y 22.3 to 47.7 (mm from the lower-left corner). Body gap 2.6 mm; `check_board.py` fails below a 1.5 mm courtyard gap (`MODULE_GAP_MM`). U1 is 4.6 mm from the right edge. Input chain at the bottom: J1 (BAT+ left, GND right) at (23.7, 3.5), F1 above BAT+. `VBAT` is an E-shaped zone: F1.2, an arm along y 22.4 to 28.8, and one prong under each module up to a pad-width neck at the VIN pads (U2.5/6, U1.5/6). The GND pads of each module touch the pour on the north side and on the south side of the pin row. J6 and J7 moved up the right edge to y 56.6 and 68.4, above the U1 body; `+5V_CPU` runs from the U1 VOUT pads north to them. Left edge from the bottom: J4, J3, J5, J8, J11, J9 (unchanged). Order and turns come from a planarity check of the edge pins. C2 and C4 (B-side, `VBAT` input caps) stay under the module bodies on the other face of the board; they are clear of the pins.
- `VBAT_RAW`, `VBAT`, `+5V_CPU` and `+5V_SENS` are planned B.Cu zones in `placement.py` (`BUS_ZONES`). GND is the B.Cu pour. `GND_KEEPOUTS` keep router tracks out of the pocket between the two `VBAT` prongs. No power zone joins two board edges, but the `VBAT_RAW` to `VBAT` tree, the U2 `+5V_SENS` trunk and U2 itself fence the left connector region: its GND (J3, J4, J5, J8, J9, J11, C9) joins J1.2 through the U2 GND pads (the 4.5 mm pad block) and not through a wide pour. The 6 mm GND path J1.2, U2 input GND, U1 runs on the east side of the tree.
- **Copper width along the current paths** (opening test on B.Cu, `check_board.py`; `make pcb-check` fails below the need; pads narrower than the opening are measured at their own width, with the copper within 2.5 mm of the pad counted):

| Path | Need | Baseline (e0ba889) | This board |
| --- | --- | --- | --- |
| GND: J1.2, U2 input GND, U1.7 to U1.10 | 6.0 mm | 0.59 mm | 7.41 mm |
| GND: J6.2, J7.2, U1.7 to U1.10 | 1.6 mm | 0.59 mm | 4.07 mm |
| GND: U2 output GND, J8.2, J9.2, J11.2, C9.2 | 1.6 mm | 1.38 mm | 1.76 mm |
| `VBAT_RAW`: J1.1, F1 | 6.0 mm | 6.48 mm | 6.18 mm |
| `VBAT`: F1, U2.5, U2.6, U1.5, U1.6 | 6.0 mm | 2.35 mm | 6.39 mm |
| `+5V_CPU`: all pads | 1.6 mm | 1.00 mm | 1.99 mm |
| `+5V_SENS`: all pads | 1.6 mm | 1.58 mm | 1.79 mm |

- The earlier statement that the GND trunks are at least 6 mm wide was not true for the baseline board. The opening test now checks it.
- The narrowest GND path is 1.76 mm: the strip west of the J11 and J9 pins. J11.2 sits between `+5V_SENS` pads J11.1 and J9.1, so its only GND path is this strip. J11 and J9 are 0.25 mm further from the edge than J4, J5, J8 and J3 to make the strip 1.6 mm or more.
- Both modules are the D36V50F5 with 12 numbered pads. U2 EN, VRP and PG have no net (no-connect flags), and the router adds no track to them.

## Checks run (this build)

| Check | Result |
| --- | --- |
| `make erc` | 0 errors, 3 warnings (`lib_symbol_mismatch`, D2 to D4: owner GUI step "Update Symbols") |
| DRC with schematic parity | 0 errors, 0 unconnected items, parity clean; 13 `lib_footprint_mismatch` warnings (see below) |
| `make pcb-check` (`check_board.py`) | 0 problems: no F.Cu copper on a THT pad, every hole in the drill set or a bored hole of at least 3.3 mm in `MILLED_HOLES`, all vias 1.1/2.1 mm, no narrow HighCurrent track |
| `make pcb-mill-check` | 0 unwaived errors, 0 waived, 0 MILL-GAP-BIT areas, 2 MILL-SLIVER warnings, 0 MILL-ISLAND warnings, 0 owner/lab-tech questions |
| `make pcb-fab` | 5 files in `../fab/`; `test_fab.py` 21 tests pass (copper area, holes vs `kicad-cli pcb export drill`, dowels) |
| `make pcb-test` | 119 tests pass |

**MILL-DEPTH (resolved, Task 9).** The lab CAM cuts 0.08 mm deep in one pass (lab .f3z) and the owner says the blank is even (depth error 0). The minimum depth 0.08 mm is above the copper thickness of 0.070 mm, so the check passes. The margin is only 0.01 mm: a real depth error above 0.01 mm leaves copper in the isolation cut. The lab tech confirms the margin on a test piece.

**Holes (Task 9).** The lab tools make drills from 0.1 to 2.0 mm and bores of 3.3 mm or more (the only end mill is 3.175 mm). Changes: H1 to H4 3.2 to 3.4 mm; J1 wire pads 3.0 to 3.4 mm (pad 4.4 mm, ring 0.5 mm); F1 locating peg 2.4 to 3.4 mm (peg size not confirmed: the Littelfuse drawing was not reachable); vias 1.2 to 1.1 mm (pad 2.1 mm, ring 0.5 mm); Phoenix MKDS 1.5 to 1.3 mm; F1 pins 1.5 to 1.4 mm.

**DRC warnings.** 16 x `lib_footprint_mismatch` (C9, F1, H1 to H4, J1, J3 to J9, J11 to J14): the board copies of these footprints have snapped drills and grown pads (annular ring 0.45 mm). The stock libraries are not changed.

**Milling warnings.** 2 x MILL-SLIVER, both on the B.Cu GND pour at U3 (SOT-23-5, pitch 0.95 mm). Cause: the 0.4 mm pad clearance leaves GND necks between the U3 pads (pad 1/3 on one side, pad 4/5 on the other) toward the GND pad U3.2. The necks are 0.44 to 0.50 mm wide (they survive an opening of 0.22 mm radius, not 0.25 mm), 0.5 and 0.4 mm2 removed by the test. Harmless for function (GND of a 3.3 V LDO, low current; the pour reaches U3.2 through two necks, one on each side). For milling the copper stays, but a neck this narrow may lift: the lab tech decides. Not waived: the copper is narrower than the minimum track width. Not removable without moving U3 or changing its footprint (rule `U3_fine`).

Earlier warnings, now removed: 3 F.Cu GND "slivers" and 4 MILL-ISLAND were false positives of the check (zero-width slits of the filler outline; same-net bus zones that overlap and were tested one by one). The check is fixed (`milling_check.py`, with tests). 3 real slivers were removed by changing bus-zone outlines in `placement.py` (`BUS_ZONES`) and refilling the zones on the existing board with `build_pcb.py --sync-zones` (parts and tracks unchanged, no re-route): a 0.2 mm step between two `+5V_SENS` rectangles at U2.3, a 0.5 mm notch beside the J8.1/J11.1 bar, and a 0.45 mm step where the `VBAT` trunk meets the U1 VIN neck. Pour pieces smaller than 200 mm2 are dropped.

## Assumptions (all "assumed": lab tech to confirm)

- Confirmed from the lab file and the owner (Task 9): drill set 0.1 to 2.0 mm in 0.1 mm steps; end mill 3.175 mm; cut depth 0.08 mm; depth error 0; stock 152.4 x 101.6 mm; dowels 4.191 mm.
- Assumed: bored holes of 3.3 mm or more (tool + 0.125 mm). Rivet via 1.1 mm drill / 2.1 mm pad; the 0.8 mm EasyContac rivet (1.0 mm OD) sits about 0.05 mm loose before soldering.
- Isolation bit: 0.2 mm tip, Fusion taper 30. Cut width at 0.08 mm depth: 0.243 mm (30 deg included) or 0.292 mm (60 deg included). The smallest copper gap on the board is 0.35 mm (U3 pads), which passes both readings.
- U1 and U2 are the Pololu D36V50F5 (owner 2026-11-12). The footprint comes from Pololu's drawing (tolerance of drill location +-0.1 mm). The 3 mounting holes are on F.Fab only. The standoff of the module over the F.Cu pour (parts 1.8 mm under the module) is not known: check on the real header.
- No reverse-polarity protection (owner decision). U3 keeps the stock SOT-23-5 footprint and rule `U3_fine`.
- XH and terminal-block orientation: pin 1 at the bottom on the left edge, except J4 and J8 (rotated 270 degrees: pin 1 at the top). J6 and J7 on the right edge also have pin 1 at the top. Deviation from the rule "pin 1 at the same end": it is needed for B.Cu routing without rivets. J8 turned means the Garmin pin order runs top to bottom. Wire entry direction of the vertical XH headers is not checked: check it with the 1:1 print.

## Owner GUI checks (user-run)

1. Open the schematic in KiCad 10: Update Symbols from Library (D2 to D4), run ERC, re-plot the PDF.
2. Open the board: 3D view (pin 1 marks, fuse access, no collisions, J4 body next to the edge), run DRC.
3. Print `rc_power_board_1to1.pdf` at actual size. Put the real parts on the print: both Pololu modules (25.4 mm body, pins in the 12 holes), F1 holder, XH headers, J6/J7 terminal blocks, C1, C9.
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

1. Accept the `U1_PG` F.Cu jumper (2 rivets, about 38 mm, north of the module bodies), or move J5 next to U1?
2. Accept J4, J8, J6 and J7 with pin 1 at the top, J1 turned 180 degrees (GND left), and J11 and J9 0.25 mm further from the edge?
3. Add a GND rivet beside each jumper via, or more test points?
4. Lab tech: bit list, rivet hole, minimum cut depth (MILL-DEPTH), dowel size.
5. J1 wire-pad size is TBD; the stock footprint pads (4.4 mm, 3.0 mm drill) are a placeholder.
