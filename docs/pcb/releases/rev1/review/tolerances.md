# Rev1 power board: tolerances, margins, minimum spacing, trace widths

Date: 2026-11-16. Board: `rc_power_board.kicad_pcb` on branch `schematic` at `91c04d0`.

Sources:

- The lab limits come from `milling.toml` in the lab directory (`dir` in `pcb/config/lab.toml`).
- The check results come from the committed `milling_check.json` in this directory. The checks did not run again for this report.
- The copper width of the power paths comes from the table in `README.md` in this directory.
- The capacitor gaps and the track widths are measured on the board file with `pcbnew` (one-time script, not a repo check).

## Process limits (lab mill)

- The isolation cut is 0.292 mm wide: 0.2 mm tip, 60 deg included angle, 0.08 mm depth.
- The cut depth is 0.08 mm. The copper is 0.070 mm thick (2 oz). The depth margin is 0.01 mm.
- The lab file sets the depth error of the blank to 0 (owner statement). A real depth error above 0.01 mm leaves copper in the cut.
- The lab tech accepts this margin (2026-11-13). If necessary, the lab adds a second, deeper pass.
- The drill location tolerance of the Pololu module is +-0.1 mm. The edge tolerance of the module is +-0.3 mm.

## Design rules and margins against the 0.292 mm cut

| Item | Rule | Margin |
| --- | --- | --- |
| Copper clearance (board) | 0.40 mm | 0.108 mm |
| U3 pads (rule `U3_fine`) | 0.30 mm rule, 0.35 mm real (smallest gap on the board) | 0.058 mm |
| Zone fill to pads | 0.40 mm (zone setting 0.5 mm) | 0.108 mm |
| Track width | 0.5 mm minimum | assumed, the lab did not confirm it |
| Copper to board edge | 0.5 mm | assumed |
| Annular ring | 0.45 mm minimum (rivet via: 1.1 mm drill, 2.1 mm pad) | assumed |
| Hole to hole, hole to copper | 0.25 mm | not in the lab file |
| Module courtyard gap (U1 to U2) | 1.5 mm minimum, 2.6 mm real body gap | 1.1 mm |

## Trace widths

Net classes (`rc_power_board.kicad_pro`). All classes have a clearance of 0.4 mm and a via of 2.1 mm with a 1.1 mm drill.

| Net class | Track width | Nets |
| --- | --- | --- |
| Default | 0.5 mm | all other nets |
| Power3A | 1.0 mm | `+6V_BEC` |
| Power5A | 1.6 mm | `+5V_CPU`, `+5V_SENS` |
| HighCurrent | 6.0 mm | `*VBAT*`, `GND` |

Tracks on the board (measured):

| Net | Width | Layer | Segments | Length |
| --- | --- | --- | --- | --- |
| `+3V3_SENS` | 0.5 mm | B.Cu | 14 | 57.2 mm |
| `+6V_BEC` | 1.0 mm | B.Cu | 5 | 15.8 mm |
| `/I2C_SCL` | 0.5 mm | B.Cu | 4 | 10.0 mm |
| `/I2C_SDA` | 0.5 mm | B.Cu | 3 | 15.8 mm |
| `/LDO_IN` | 0.5 mm | B.Cu | 12 | 17.4 mm |
| `/STEER_PWM` | 0.5 mm | B.Cu | 5 | 35.7 mm |
| `/THROTTLE_PWM` | 0.5 mm | B.Cu | 9 | 17.1 mm |
| `/U1_PG` | 0.5 mm | B.Cu | 3 | 12.5 mm |
| `/U1_PG` | 0.5 mm | F.Cu | 3 | 39.3 mm |
| `Net-(D2-A)`, `Net-(D3-A)`, `Net-(D4-A)` | 0.5 mm | B.Cu | 1 each | 3.2, 2.0, 2.0 mm |

- The board has only two track widths: 0.5 mm and 1.0 mm. Each track is at its class width, which is also the minimum. The margin is 0.
- The nets `VBAT`, `VBAT_RAW`, `GND`, `+5V_CPU` and `+5V_SENS` have no tracks. Their copper is zone fill.

Copper width of the power paths (opening test of `check_board.py`, values from `README.md` in this directory):

| Path | Need | Measured | Margin |
| --- | --- | --- | --- |
| GND trunk (J1.2 to the pour under U1) | 6.0 mm | 8.00 mm or more | 2.0 mm or more |
| GND entrance U1, GND entrance U2 | 1.6 mm | 4.81 mm | 3.21 mm |
| GND: J6.2, J7.2, U1.7 to U1.10 | 1.6 mm | 4.07 mm | 2.47 mm |
| GND: U2 output GND, J8.2, J9.2, J11.2, C9.2 | 1.6 mm | 1.64 mm | 0.04 mm |
| `VBAT_RAW`: J1.1, F1 | 6.0 mm | 6.18 mm | 0.18 mm |
| `VBAT` trunk | 6.0 mm | 6.39 mm | 0.39 mm |
| `VBAT` neck at U1 VIN, at U2 VIN | 1.6 mm | 1.88 mm | 0.28 mm |
| `+5V_CPU` load path | 1.6 mm | 1.99 mm | 0.39 mm |
| `+5V_SENS` load path | 1.6 mm | 1.67 mm | 0.07 mm |
| `+5V_CPU` all pads (small-part branches) | 0.5 mm | 1.17 mm | 0.67 mm |
| `+5V_SENS` all pads (small-part branches) | 0.5 mm | 1.00 mm | 0.50 mm |
| `+6V_BEC`: J3.2 to J4.2 | 1.0 mm | 1.00 mm | 0 |

- The `+6V_BEC` row passes only because of the 0.01 mm numeric tolerance of the test (`OPEN_TOL_MM`).
- The smallest margins that are not 0 are 0.04 mm (GND at J11.2) and 0.07 mm (`+5V_SENS` load path).
- The isolation cut follows the copper outline of the board file. A cut that is wider or offset decreases these widths.

## Capacitors

| Pair | Pad gap (different nets) | Courtyard gap | Side |
| --- | --- | --- | --- |
| The two pads of each 0805 part (C2 to C8) | 0.90 mm | not applicable | B |
| C6 to C7 | 1.10 mm | 0.61 mm | B |
| TP2 to C5 | 1.30 mm | 0.56 mm | B |
| TP1 to C3 | 1.34 mm | 0.58 mm | B |
| C1 to F1 | more than 1.94 mm | 0.82 mm | F |
| C1 to J1 | more than 1.94 mm | 0.98 mm | F |
| C9 to J11 | more than 1.94 mm | 1.21 mm | F |

- C2 to C8 are 0805 parts on the bottom side. C1 (radial, 10 mm) and C9 (radial, 8 mm) are on the top side.
- No courtyards overlap.
- All copper gaps at the capacitors are 0.90 mm or more. This is approximately 3 times the cut width. The capacitors are not the limit for milling.
- The courtyard gaps of 0.56 to 0.61 mm are small for hand soldering. They cause no electrical problem and no milling problem.

## Weak points

1. The depth margin is 0.01 mm. This is the smallest margin on the board.
2. U3 (SOT-23-5) has a pad gap of 0.35 mm and a margin of 0.058 mm. Bit wear or runout above approximately 0.03 mm for each side removes this margin.
3. There are two `MILL-SLIVER` warnings: GND necks of 0.44 to 0.50 mm at U3. These necks can lift. They are not waived. The lab tech decides.
4. Three copper widths have almost no margin: `+6V_BEC` (0), GND at J11.2 (0.04 mm) and the `+5V_SENS` load path (0.07 mm).
5. `track_min`, `edge_clearance`, `annular_min`, `via_pad` and `milled_hole_min` have the status "assumed". The lab tech did not confirm them.
6. The values of C1 to C6 and C9 are TBD. The voltage ratings of C7 and C8 are TBD. A larger case changes the capacitor gaps.

Committed check status: 0 milling errors, 0 waivers, 2 warnings.
