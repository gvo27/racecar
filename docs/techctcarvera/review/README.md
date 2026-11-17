# Mill prototype board (`pcb/mill`): review record

Date: 2026-11-16. Board: `pcb/mill/rc_power_board.kicad_pcb`, made by `make pcb-all BOARD=mill` from `pcb/mill/placement.py` and the mill tuning file (`design_rules.toml` in this lab directory). The rev A board (`pcb/fabhouse`) is not changed.

Status: first prototype layout. The checks pass. No person and no review agent reviewed the board. The values of the tuning file are start values (`assumed`).

## What is different from rev A

| Item | Rev A (`pcb/fabhouse`) | Mill board (`pcb/mill`) |
| --- | --- | --- |
| Parts | 40 | 34: no D2, D3, D4 (LEDs), no R1, R2, R3 (their resistors). Same footprints for all other parts |
| Clearance | 0.4 mm | 0.5 mm (cut width 0.292 mm + 2 x 0.10 mm horizontal error) |
| Default track | 0.5 mm | 1.5 mm target (2.0 mm cut spacing - 0.5 mm clearance) |
| `+6V_BEC` track | 1.0 mm | 1.5 mm |
| Pour: smallest width | 0.5 mm | 1.0 mm |
| Pads of different parts, different nets | 1.10 mm smallest (C6 to C7) | 2.0 mm minimum |
| U3 (SOT-23-5) | pour necks of 0.44 to 0.50 mm between the pads | planned zones: `/LDO_IN` bar with two prongs, GND strip under the body, `+3V3_SENS` bar. No pour neck |
| 3.3 V nets | tracks, 0.5 mm | zones: `/LDO_IN` bar 2.0 mm, `+3V3_SENS` bar 2.0 mm with 1.9 mm teeth to J12, J13, J14 |
| Test points | on stubs | on the rail trunks (TP1, TP2) and on the `+3V3_SENS` bar (TP3) |
| J9, J11 | x = 3.65 mm | x = 3.75 mm (the GND strip west of the pads keeps 1.6 mm) |

Not changed: outline 66 x 140 mm, mounting holes, connector positions (but J9 and J11), modules, fuse, power zones, the `U1_PG` jumper on two rivets, the stitching via, the Power5A width (1.6 mm: the Pololu pin pitch limits the necks at the module pads to 1.9 mm) and the edge clearance (0.5 mm).

## Check results

| Check | Result |
| --- | --- |
| `make erc BOARD=mill` | 0 errors, 3 warnings (`lib_symbol_mismatch`, as rev A) |
| `make pcb-rules BOARD=mill` | The project files agree with the design rules. 15 values assumed |
| `make pcb-check BOARD=mill` | DRC: 0 errors, 16 warnings (`lib_footprint_mismatch`, as rev A), 0 unconnected, parity clean. `check_board`: 0 problems |
| `make pcb-mill-check BOARD=mill` | 0 errors, 0 waived, 67 warnings: 52 `MILL-CUT-SPACING`, 12 `MILL-GAP-FIXED`, 2 `MILL-SLIVER`, 1 `MILL-ISLAND` |
| `make pcb-fab BOARD=mill` | Outputs in `pcb/mill/fab/`. 21 tests, OK |

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

- **`MILL-GAP-FIXED` (12).** All at U3. The gaps are 0.30 to 0.35 mm: above the cut width (0.292 mm), below the cut width plus the horizontal error (0.492 mm). The footprint fixes them. A cut that is 0.1 mm off at U3 can cut into a pad or leave a bridge. U3 is the risk item of this board for this mill.
- **`MILL-SLIVER` (2).** GND copper of about 0.05 and 0.08 mm2 at the end of the U3 GND strip, narrower than 0.5 mm.
- **`MILL-CUT-SPACING` (52).** Copper narrower than the 1.5 mm target:
  - Tracks: `/U1_PG` stub at U1.1, 0.9 mm wide, 5.9 mm long (it passes U1.2). `/THROTTLE_PWM`, 1.12 mm wide for 2.0 mm and 1.40 mm for 0.4 mm, at J5.
  - Zones at U3: the two `/LDO_IN` prongs (0.6 mm), the GND strip (0.6 mm) and the `+3V3_SENS` bar at U3.5 (1.3 mm).
  - Zone stubs to C3 and C5 and the teeth to J12, J13, J14: the test removes the corners of 1.6 to 1.9 mm wide copper.
  - GND pour: the ring between the pins of the XH connectors and the board edge, the corners at the mounting holes, and the pour between the module pins. The pin pitch and the edge distance fix these widths.
- **`MILL-ISLAND` (1).** `+5V_SENS` zone piece at (26.10, 100.40) mm that touches no pad. Not examined. Rev A has no such finding.

## Not verified

- No KiCad GUI check of the mill project. No kicad-happy analysis of the mill board.
- No review by `pcb-reviewer` and no owner review.
- The mill did not cut this board.
- The schematic PDF of the mill variant is not plotted.

## Questions for the lab tech

1. "Minimum 2 mm spacing between cuts": is this the distance between the centers of two isolation gaps? The tuning file uses this reading (`cut_spacing_min`).
2. What is the real horizontal error of the mill? The tuning file uses 0.10 mm for each side (`horizontal_error`).
3. Are the fixed gaps at U3 (0.30 to 0.35 mm) acceptable on this mill? If not, U3 needs a different package or a module.
4. Is 0.5 mm copper acceptable at the U3 strips and prongs (0.6 mm wide, 1 to 4 mm long)?
