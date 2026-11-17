# Mill prototype board (`pcb/mill`): review record

Date: 2026-11-17. Board: `pcb/mill/rc_power_board.kicad_pcb`, made by `make pcb-all BOARD=mill` from `pcb/mill/placement.py` and the mill tuning file (`design_rules.toml` in this lab directory). The rev A board (`pcb/fabhouse`) is not changed.

Status: second layout, after the lab tech notes (owner, 2026-11-17). The checks pass. The agent `pcb-reviewer` reviewed the first layout on 2026-11-16 (all findings fixed). No person and no review agent reviewed this second layout. The values of the tuning file are `assumed`.

## Lab tech notes and what the board does

| Note | Board |
| --- | --- |
| The mill is not dialed in: error margin, bit size, step tolerance | `horizontal_error` 0.25 mm for each side (was 0.10). `clearance` 0.8 mm = cut width 0.292 mm + 2 x 0.25 mm, rounded up |
| 2 mm spacing between cuts, 2 mm spacing for components | Pours and planned zones keep a 2.0 mm copper gap from other copper (`zone_clearance`). Pads of two different parts on different nets are 2.0 mm or more apart (smallest: 2.03 mm, C6 to FB1). Where a 2 mm gap is not possible (see "Areas without the 2 mm copper gap"), the rule is 2 mm between cuts: 1.3 mm track + 0.8 mm gap = 2.1 mm |
| The surface mount ceramic capacitors are too close | C2 to C8 are through-hole ceramic capacitors with 5.0 mm lead pitch (`C_Disc_D5.0mm_W2.5mm_P5.00mm`, top side). The pads of one capacitor are 2.6 mm apart (0805: 0.9 mm). Same values as in the schematic |
| Check the through-hole capacitors | C1: 2.4 mm between its pads, 2.55 mm to D1. C9: 1.8 mm between its pads (3.5 mm lead pitch, not changed), 7.07 mm to J11 |
| Thicken the small traces, add general thickness | Every track is 1.3 mm (rev A: 0.5 mm). 1.3 mm is the largest width that leaves an XH pin with 0.8 mm to the next pin. Pour copper is 1.2 mm or wider. The 3.3 V nets are zones of 1.9 to 2.0 mm |
| Do not worry about the pin headers | The XH headers keep their footprint. Their pads are 0.6 mm apart (listed as `MILL-GAP-FIXED`) |
| Drop the surface mount LEDs | No D2, D3, D4 and no R1, R2, R3 |
| Apply the 2 mm rule to the USB pigtail ports | J6 and J7 have no exception. Their pads are 2.18 mm apart and 2.8 mm or more from pads of other parts (J6.2 to TP1). The `+5V_CPU` bar between them moved 2 mm west, in line with the trunk: it is 2.35 mm from the GND pads J6.2 and J7.2 |
| U1 and U2: add space at VOUT | The GND pour and the GND areas at the modules keep 2.0 mm from the 5 V trunks, which cover the VOUT pads. The VOUT pads are 0.64 mm from the GND pads of the module (pin pitch 2.54 mm): this gap cannot change |
| Through-hole soldering is difficult | Annular ring 0.8 mm on the THT pads of C1, C2 to C8, J1, J6, J7 (`annular_target`). Not on parts where the pitch gives no room: XH headers, modules, C9 and F1 keep 0.45 mm |

## Areas without the 2 mm copper gap

In these areas a zone has the board clearance (0.8 mm) or the footprint fixes a smaller gap. They are in `pcb/mill/placement.py` (`_NEAR`, `_NEAR_GND`, `_FINE`) and in the `[[exception]]` entries of the tuning file.

| Area | Gap | Cause |
| --- | --- | --- |
| U3 (SOT-23-5): pads, two `/LDO_IN` prongs, GND strip, `+3V3_SENS` bar at U3.5 | 0.34 to 0.35 mm | Pad gap of the footprint. Owner decision: U3 stays |
| XH headers J3, J4, J5, J8, J9, J11 to J14: pad to pad | 0.6 mm | 2.5 mm pin pitch. Tracks and zones keep 0.8 mm from the pads |
| Modules U1, U2: pad to pad, VIN neck to GND pads | 0.64 mm | 2.54 mm pin pitch. The necks are as wide as the pads |
| Left edge, x 0.6 to 12.5 mm, y 27 to 105.5 mm: GND between header pins, tracks and the edge. `+5V_SENS` bar at J8.1/J11.1 and its branch to J9.1 | 0.8 mm | The 2 mm pour leaves no GND copper between the pins and the edge |
| Right edge, x 58.6 to 65.4 mm, y 103.5 to 132 mm: GND at J12 to J14 and the three `+3V3_SENS` teeth | 0.8 mm | Same |
| Bottom edge, y 0.6 to 7.4 mm, x 28 to 65.4 mm: GND trunk from J1.2, and the VBAT stub to C1 | 0.8 mm | The trunk needs 6.0 mm. With 2 mm to the C1.1 pad it has 5.4 mm |
| GND at the module GND pads (x 20.4 to 25.5 and 48.4 to 53.5 mm, y 41 to 51 mm) to the VIN neck | 0.8 mm | With 2 mm on both sides the GND copper there is 1.6 mm wide. It is 1.9 mm now |
| All tracks (signals, `+6V_BEC`): track to track, track to pad | 0.8 mm | The tracks start at header pins |

All other copper has a 2.0 mm gap: the pour to the VBAT, 5 V, `/LDO_IN` and `+3V3_SENS` zones, and to the pads of C1 to C9, D1, FB1, F1, J1, J6, J7 and the test points.

## Other differences from rev A

- 34 parts (rev A: 40).
- C2 and C4 (input capacitors of U1 and U2) are north of the pin rows, about 6 mm from the VIN pads, on a VBAT stub. On rev A they are under the modules on the bottom side. A through-hole part has no room under a module.
- C3 is on the `+5V_CPU` bar north of J7. C5 is on the `+5V_SENS` trunk. C6 and C7 are south of the `/LDO_IN` bar, C8 is on the `+3V3_SENS` bar.
- Test points TP1, TP2, TP3 are on the rail trunks.
- J9 and J11 are at x = 4.3 mm (rev A: 3.65 mm).
- The `U1_PG` stub and its rivet are at x = 39.6 mm (rev A: 40.4 mm).
- Not changed: outline 66 x 140 mm, mounting holes, modules, fuse, D1 (SMB), FB1 (0805), the other connector positions, Power5A width (1.6 mm), edge clearance (0.5 mm).

## Check results

| Check | Result |
| --- | --- |
| `make erc BOARD=mill` | 0 errors, 3 warnings (`lib_symbol_mismatch`, as rev A) |
| `make pcb-rules BOARD=mill` | The project files agree with the design rules. 16 values assumed |
| `make pcb-check BOARD=mill` | DRC: 0 errors, 0 unconnected, parity clean. 117 warnings: 26 `lib_footprint_mismatch` (pads changed by the build), 91 `silk_over_copper` (silkscreen of the library footprints; the milled board has no silkscreen). `check_board`: 0 problems |
| `make pcb-mill-check BOARD=mill` | 0 errors, 0 waived, 122 warnings: 112 `MILL-GAP-FIXED`, 8 `MILL-CUT-SPACING`, 2 `MILL-CONN-EDGE`. No `MILL-SLIVER`, no `MILL-ISLAND` |
| `make pcb-fab BOARD=mill` | Outputs in `pcb/mill/fab/`. The target then runs `test_fab.py` on the mill board: 21 tests, OK |
| `make bom BOARD=mill` | `pcb/mill/bom.csv` |
| `make pcb-test` | 95 + 62 = 157 tests, OK |

Copper width along the current paths (opening test, B.Cu):

| Path | Need | Measured |
| --- | --- | --- |
| GND trunk J1 to the pour at U1 | 6.0 mm | 6.80 mm |
| GND entrance U1, entrance U2 | 1.6 mm | 1.94 mm, 1.88 mm |
| GND J6/J7 to U1 | 1.6 mm | 1.94 mm |
| GND U2 output to J8/J9/J11/C9 | 1.6 mm | 1.91 mm |
| `VBAT_RAW`, `VBAT` trunk | 6.0 mm | 6.18 mm, 6.39 mm |
| `VBAT` necks at U1 and U2 | 1.6 mm | 1.88 mm |
| `+5V_CPU` load path, `+5V_SENS` load path | 1.6 mm | 1.99 mm, 1.67 mm |
| `+5V_CPU` all pads, `+5V_SENS` all pads | 1.3 mm | 1.99 mm, 1.67 mm |
| `+6V_BEC` J3 to J4 | 1.3 mm | 1.29 mm (passes with the 0.01 mm test tolerance) |
| `+3V3_SENS` bar to J12/J13/J14 | 1.2 mm | 1.88 mm |
| `/LDO_IN` bar FB1 to C6/C7 | 1.3 mm | 1.99 mm |

The GND entrances were 4.6 mm on the first layout. The 2 mm gap to the 5 V trunks makes them narrower.

## Warnings to read

The milling check prints positions as (x, -y) in mm from the lower-left corner of the outline.

- **`MILL-GAP-FIXED` (112).** Gaps below 0.792 mm (cut width + 2 x 0.25 mm) that the footprints fix. A THT pad pair counts on both copper layers. Modules U1 and U2: pad to pad and VIN neck to pad, 0.64 mm. XH headers: pad to pad, 0.6 mm. U3: pad to pad and zone to pad, 0.34 to 0.35 mm. With an error of 0.25 mm for each side, a cut at U3 can remove most of a 0.6 mm wide pad, prong or strip. U3 is the risk item of this board.
- **`MILL-CUT-SPACING` (8).** Copper below 1.2 mm (2.0 mm cut spacing - 0.8 mm clearance): the two `/LDO_IN` prongs (0.6 mm), the U3 GND strip (0.6 mm), the places where the three `+3V3_SENS` teeth meet the bar, and the corners where the two VBAT capacitor stubs meet the necks.
- **`MILL-CONN-EDGE` (2).** J9 and J11: the courtyard is more than 1.0 mm from the board edge (1.55 mm). The connectors moved in for the GND strip west of their pads.

## Margins without spare

- `clearance` 0.8 mm against the minimum 0.792 mm. If `horizontal_error` goes up, raise `clearance`. The tracks then get narrower than 1.3 mm at the XH pins, or do not fit.
- `horizontal_error` is used for copper gaps only. The edge clearance (0.5 mm), the annular rings and the holes have no allowance for it.
- `+5V_SENS` load path: 1.67 mm against 1.6 mm. `+6V_BEC`: 1.29 mm against 1.3 mm.
- Pad gap C6 to FB1: 2.03 mm against 2.0 mm.

## Not verified

- No review of this layout by a person or by `pcb-reviewer`. No KiCad GUI check. No kicad-happy analysis.
- The capacitor type: the footprint is a 5.0 mm pitch disc. The capacitor values of the schematic are TBD (C7, C8: 1 uF). A part with 2.5 mm lead pitch needs formed leads or a different footprint.
- The effect of the new positions of C2 and C4 (about 6 mm from the VIN pads) was not analyzed. The modules have their own input capacitors.
- The body height and the body size of the capacitors next to the modules and connectors (courtyards do not overlap in DRC).
- Rivet and solder access, 3D collisions, wire entry at J9 and J11.
- The routing is made again in each `make pcb-all` run. The track shapes can change.
- The mill did not cut this board. The schematic PDF of the mill variant is not plotted.
- A 2 mm copper gap with a single-pass contour toolpath leaves a loose copper strip of about 1.4 mm between the two cuts. The lab CAM must remove it or leave it. Not checked with the lab.

## Review findings on the first layout (`pcb-reviewer`, 2026-11-16)

No blocker, 2 major, 7 minor. All fixed in commit `adef37b`: the component gap check includes parts with an exception; a track or a pad of another part near a pad of an exception part is a `MILL-GAP` error; U3 zone clearance 0.34 mm; no island fragments on `+5V_SENS`; no sliver at the U3 GND strip. The reviewer compared all pad nets with rev A (0 differences).

## Questions for the lab tech

1. What is the real horizontal error of the mill? The tuning file uses 0.25 mm for each side.
2. Is a 2 mm copper gap cut as two passes with a loose strip between them, or cleared? Is a loose strip a problem?
3. Are the gaps at U3 (0.34 to 0.35 mm, cut width 0.292 mm) possible on this mill? If not, U3 needs a different package or a module.
4. Which through-hole ceramic capacitors are in stock (lead pitch, values up to 1 uF or more, voltage)?
5. Is a 0.8 mm ring sufficient for hand soldering on holes without plating? Is 0.45 mm at the XH headers and the modules acceptable?
