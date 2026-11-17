# Mill prototype board (`pcb/mill`): review record

Date: 2026-11-16. Board: `pcb/mill/rc_power_board.kicad_pcb`, made by `make pcb-all BOARD=mill` from `pcb/mill/placement.py` and the mill tuning file (`design_rules.toml` in this lab directory). The rev A board (`pcb/fabhouse`) is not changed.

Status: first prototype layout. The checks pass. The agent `pcb-reviewer` reviewed the board on 2026-11-16 (no blocker, 2 major and 7 minor findings: all fixed, see "Review findings"). No person reviewed the board. The values of the tuning file are start values (`assumed`).

## What is different from rev A

| Item | Rev A (`pcb/fabhouse`) | Mill board (`pcb/mill`) |
| --- | --- | --- |
| Parts | 40 | 34: no D2, D3, D4 (LEDs), no R1, R2, R3 (their resistors). Same footprints for all other parts |
| Clearance | 0.4 mm | 0.5 mm (cut width 0.292 mm + 2 x 0.10 mm horizontal error) |
| Default track | 0.5 mm | 1.5 mm target (2.0 mm cut spacing - 0.5 mm clearance) |
| `+6V_BEC` track | 1.0 mm | 1.5 mm |
| Pour: smallest width | 0.5 mm | 1.0 mm |
| Pads of different parts, different nets | 1.10 mm smallest (C6 to C7) | 2.0 mm minimum, U3 included (U3 to C7 and C8: 2.0 mm, U3 to C6: 2.3 mm) |
| U3 (SOT-23-5) | pour necks of 0.44 to 0.50 mm between the pads | planned zones: `/LDO_IN` bar with two prongs (0.6 mm wide, 1.0 mm long), GND strip under the body (0.6 mm wide) with a 2.0 mm wide end in the pour, `+3V3_SENS` bar. No pour neck between the pads, no sliver. Zone fill is 0.34 to 0.35 mm from the U3 pads |
| 3.3 V nets | tracks, 0.5 mm | zones: `/LDO_IN` bar 2.0 mm, `+3V3_SENS` bar 2.0 mm with 1.9 mm teeth to J12, J13, J14 |
| Test points | on stubs | on the rail trunks (TP1, TP2) and on the `+3V3_SENS` bar (TP3) |
| J9, J11 | x = 3.65 mm | x = 3.75 mm (the GND path to J11.2 measures 1.64 mm against a need of 1.6 mm: 0.04 mm margin) |
| `U1_PG` jumper stub and rivet at U1 | x = 40.4 mm, 0.5 mm track | x = 39.9 mm, 1.5 mm track |

Not changed: outline 66 x 140 mm, mounting holes, connector positions (but J9 and J11), modules, fuse, power zones, the F.Cu path of the `U1_PG` jumper on two rivets, the stitching via, the Power5A width (1.6 mm: the Pololu pin pitch limits the necks at the module pads to 1.9 mm) and the edge clearance (0.5 mm).

## Check results

| Check | Result |
| --- | --- |
| `make erc BOARD=mill` | 0 errors, 3 warnings (`lib_symbol_mismatch`, as rev A) |
| `make pcb-rules BOARD=mill` | The project files agree with the design rules. 15 values assumed |
| `make pcb-check BOARD=mill` | DRC: 0 errors, 16 warnings (`lib_footprint_mismatch`, as rev A), 0 unconnected, parity clean. `check_board`: 0 problems |
| `make pcb-mill-check BOARD=mill` | 0 errors, 0 waived, 62 warnings: 48 `MILL-CUT-SPACING`, 14 `MILL-GAP-FIXED`. No `MILL-SLIVER`, no `MILL-ISLAND` |
| `make pcb-fab BOARD=mill` | Outputs in `pcb/mill/fab/`. The target then runs `test_fab.py` on the mill board: 21 tests, OK |
| `make pcb-test` | 93 + 62 = 155 tests, OK (rev A board and tools, `test_rules.py` also loads the mill board) |

Copper width along the current paths (opening test, B.Cu):

| Path | Need | Measured |
| --- | --- | --- |
| GND trunk J1 to the pour at U1 | 6.0 mm | 8.00 mm or more |
| GND entrance U1, entrance U2 | 1.6 mm | 4.60 mm |
| GND J6/J7 to U1 | 1.6 mm | 3.96 mm |
| GND U2 output to J8/J9/J11/C9 | 1.6 mm | 1.64 mm |
| `VBAT_RAW`, `VBAT` trunk | 6.0 mm | 6.18 mm, 6.39 mm |
| `VBAT` necks at U1 and U2 | 1.6 mm | 1.88 mm |
| `+5V_CPU` load path, `+5V_SENS` load path | 1.6 mm | 1.99 mm, 1.67 mm |
| `+5V_CPU` all pads, `+5V_SENS` all pads | 1.5 mm | 1.99 mm, 1.58 mm |
| `+6V_BEC` J3 to J4 | 1.5 mm | 1.50 mm |
| `+3V3_SENS` bar to J12/J13/J14 | 1.2 mm | 1.29 mm |
| `/LDO_IN` bar FB1 to C6/C7 | 1.5 mm | 1.99 mm |

## Warnings to read

The milling check prints positions as (x, -y) in mm from the lower-left corner of the outline. This file gives (x, y).

- **`MILL-GAP-FIXED` (14).** All at U3: gaps of 0.34 to 0.35 mm between two U3 pads, or between a U3 pad and the planned zone fill. They are above the cut width (0.292 mm) and below the cut width plus the horizontal error (0.492 mm). The footprint fixes them. A cut that is 0.1 mm off takes up to about 0.07 mm from a pad, a prong or the strip (0.6 mm wide copper). U3 is the risk item of this board for this mill.
- **`MILL-CUT-SPACING` (48).** Copper narrower than the 1.5 mm target. No track is in the list (no track is narrower than 1.5 mm).
  - Zones at U3: the two `/LDO_IN` prongs (0.6 mm), the GND strip (0.6 mm) and the `+3V3_SENS` bar at U3.5 (1.3 mm).
  - Zone stubs to C3 and C5, the `+5V_SENS` branch to J9, and the teeth to J12, J13, J14: the opening test removes the corners and the pad ends of 1.6 to 1.9 mm wide copper.
  - GND pour (38 of the 48, without the U3 strip): the ring between the pins of the XH connectors and the board edge, the corners at the mounting holes, the pour between the module pins, and one piece at the `U1_PG` rivet. The pin pitch and the edge distance fix these widths.

## Review findings (`pcb-reviewer`, 2026-11-16) and fixes

| Finding | Fix |
| --- | --- |
| Major: `MILL-COMP-GAP` left out U3. U3 to C6 was 1.6 mm, U3 to C7 1.5 mm | The check includes parts with an exception. U3 and C8 moved 0.5 mm north: 2.0 mm or more |
| Major: a track or a pad of another part near a U3 pad became a `MILL-GAP-FIXED` warning | Fixed gaps are only two pads of one part, or zone fill at a pad of an exception part with `zones = true`. All other gaps below the minimum are `MILL-GAP` errors. The `.kicad_dru` rule does not cover tracks and vias |
| Zone fill was 0.30 mm from the U3 pads, less than the 0.35 mm pad gap | Exception clearance 0.34 mm. All U3 gaps are 0.34 to 0.35 mm |
| `MILL-ISLAND` on `+5V_SENS` | Cause: the rev A trunk zone overlaps the end of the FB1 bar zone, and the fill leaves fragments of 0.003 mm2. The mill trunk ends at y 99.2 mm. The finding is gone. The rev A placement has the same overlap (not changed; the rev A milling check prints no island) |
| `/U1_PG` stub 0.9 mm wide | Stub and rivet moved 0.5 mm west: 1.5 mm wide |
| `/THROTTLE_PWM` 1.12 mm wide for 2.0 mm at J5 | No design change. The router made 1.5 mm tracks in the next run. A new routing run can make such a narrow piece again: `MILL-CUT-SPACING` lists it |
| Two `MILL-SLIVER` pieces at the end of the U3 GND strip | The strip ends in a 2.0 mm wide GND zone. No sliver |
| Tuning file text said "courtyards" for `component_gap` | Text corrected: pads of two parts on different nets |
| Wrong statements in this file (2.0 mm minimum, "bridge", "0.5 mm copper", test counts) | Corrected |

The reviewer also compared all pad nets of the 34 parts with rev A (0 differences) and found no F.Cu zone copper on a THT pad.

## Margins without spare

- `clearance` 0.5 mm against the minimum 0.492 mm (cut width + 2 x 0.10 mm): 0.008 mm. A larger `horizontal_error` makes `MILL-GAP` errors on the whole board. Then raise `clearance` and `zone_clearance` too.
- `horizontal_error` is used for copper gaps only. The edge clearance (0.5 mm), the annular ring and the holes have no allowance for it.
- GND path to J11.2: 1.64 mm against 1.6 mm. `+5V_SENS` load path: 1.67 mm against 1.6 mm. `+5V_SENS` all pads: 1.58 mm against 1.5 mm. `+6V_BEC`: 1.50 mm against 1.5 mm. A cut that is 0.1 mm off takes these paths below the need.

## Not verified

- No KiCad GUI check of the mill project. No kicad-happy analysis of the mill board.
- No owner review. The reviewer did not compute the narrowest GND neck at J12.2, J13.2, J14.2 and C8.2 (DRC shows them connected).
- Rivet and solder access, 3D collisions, wire entry.
- The routing is made again in each `make pcb-all` run. Two runs with different inputs gave different track shapes.
- The mill did not cut this board.
- The schematic PDF of the mill variant is not plotted.

## Questions for the lab tech

1. "Minimum 2 mm spacing between cuts": is this the distance between the centers of two isolation gaps? The tuning file uses this reading (`cut_spacing_min`).
2. What is the real horizontal error of the mill? The tuning file uses 0.10 mm for each side (`horizontal_error`).
3. Are the fixed gaps at U3 (0.34 to 0.35 mm, cut width 0.292 mm) acceptable on this mill? A cut that is 0.1 mm off takes about 0.07 mm from 0.6 mm wide copper. If not, U3 needs a different package or a module.
4. Is 0.6 mm wide copper acceptable at the U3 prongs (1.0 mm long) and the U3 GND strip (about 3 mm long)?
