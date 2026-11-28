# Rev3 (draft): review record of the active board `pcb/src`

Latest state, 2026-11-18. Board: `pcb/src/rc_power_board.kicad_pcb` (title-block revision `3 (draft)`), made by `make pcb-all BOARD=src` from `pcb/src/placement.py` and the mill tuning file (`design_rules.toml` in the lab directory). Only the latest review is kept here. The earlier layout reviews (2026-11-16 and 2026-11-17, all findings fixed or moved to the open items below) are in `docs/archive/pcb/review/2026-11-18-mill-review-record.md`. The rev1 board (`pcb/releases/rev1`) is not changed.

Release: rev2 (`pcb/releases/rev2`) is a frozen copy of this board with the JST XH headers and its own copy of the design rules (2026-11-17). After that copy, `pcb/src` got the temporary solder-wire pads (next section). The checks of rev2 give the results of the second layout: 96 milling warnings, BOM 91.83 USD.

Findings of the rev3 milling: [`../milling_findings.md`](../milling_findings.md).

## Temporary exception: wires soldered to the board (first print round only)

The owner (2026-11-17): for the first print round, solder the wires to the board directly. Do not fit the JST XH headers. The exception and its status are in `[parts.wire]` of the mill tuning file. Remove that table for the next round.

- J3, J4, J5, J8, J9, J11, J12, J13 and J14 get `rc_power:SolderWire_1xNN_P2.50mm` (`pcb/lib/rc_power.pretty`). The pads, the drills (1.0 mm for 2 pins, 0.95 mm for 3, 4 and 6 pins, then the lab drill set) and the pad positions are those of the XH footprint. The header body is not on the footprint. So the copper and the routing stay as they were.
- `make pcb-sch` sets MPN, Manufacturer and Status of these parts to `none`, the unit cost and the supplier link to empty. `BOM Comments` keeps the base part number. The XH housings and crimps of `docs/pcb/bom_offboard.csv` are not necessary for this round.
- Put the wire in from the top. Solder it on the bottom (B.Cu). A 1.0 mm hole takes stranded 22 AWG or thinner wire. 20 AWG wire does not fit without a larger drill. No strain relief is on the board: use glue or a cable tie.
- The courtyard of the wire pads is smaller than the header body. Thus 7 more `MILL-CONN-EDGE` warnings (J3, J4, J5, J8, J12, J13, J14). The wires still leave the board at the same edge.

Status: second layout, after the lab tech notes (owner, 2026-11-17). The checks pass. The agent `pcb-reviewer` reviewed the first layout on 2026-11-16 and the second layout on 2026-11-17 (model: Claude Opus 5.5). The findings of both reviews are fixed, except the items for the owner (see "Review findings on the second layout"). No person reviewed this layout. The values of the tuning file are `assumed`.

## Risks, most important first

This list ranks the risks of the mill board. The details are in the sections that each line names.

1. **Wires on the board, first round only.** No headers and no strain relief on the board. See "Temporary exception".
2. **U3 (SOT-23-5) is the weakest point.** Its gaps are 0.34 to 0.35 mm. With an error of 0.25 mm for each side, a cut can remove most of a 0.6 mm wide pad, prong or strip. Owner decision: U3 stays. If the first prototype fails at U3, U3 needs a different package or a module. See "Warnings to read".
3. **All 16 tuning values are `assumed`.** No value comes from a measurement of this mill (`make pcb-rules BOARD=src`).
4. **The 2 mm copper gap is not everywhere.** See "Areas without the 2 mm copper gap".
5. **Loose copper strips between two cuts**, and the meaning of "2 mm between cuts". See "Not verified" and "Questions for the lab tech".
6. **Margins without spare** (clearance, load paths). See that section.
7. **VOUT of U1 and U2.** The VOUT pads are 0.64 mm from the GND pads of the same module (2.54 mm pin pitch). The gap cannot change. A solder bridge there shorts the 5 V output to GND. Examine these pads after soldering.
8. **Through-hole capacitors C2 to C8** are an assumption about the lab stock. The part numbers are TBD. See "Not verified".
9. **Pads with a 0.45 mm ring** (XH headers, modules, C9, the four F1 pads at the holder hole) are the hardest to hand-solder on holes without plating. Thermal reliefs on C2 to C9 are an open owner decision.
10. **The depth margin is 0.01 mm** (0.08 mm cut in 0.070 mm copper). The lab tech accepts it (2026-11-13, `milling.toml`).
11. **The route can change between builds.** See "Not verified".

## Lab tech notes and what the board does

| Note | Board |
| --- | --- |
| The mill is not dialed in: error margin, bit size, step tolerance | `horizontal_error` 0.25 mm for each side (was 0.10). `clearance` 0.8 mm = cut width 0.292 mm + 2 x 0.25 mm, rounded up |
| 2 mm spacing between cuts, 2 mm spacing for components | Pours and planned zones keep a 2.0 mm copper gap from other copper (`zone_clearance`). Pads of two different parts on different nets are 2.0 mm or more apart (smallest: 2.03 mm, C6 to FB1). Where a 2 mm gap is not possible (see "Areas without the 2 mm copper gap"), the rule is 2 mm between cuts: 1.3 mm track + 0.8 mm gap = 2.1 mm |
| The surface mount ceramic capacitors are too close | C2 to C8 are through-hole ceramic capacitors with 5.0 mm lead pitch (`C_Disc_D5.0mm_W2.5mm_P5.00mm`, top side). The pads of one capacitor are 2.6 mm apart (0805: 0.9 mm). Same values as in the schematic |
| Check the through-hole capacitors | C1: 2.4 mm between its pads, 2.55 mm to D1. C9: 1.8 mm between its pads (3.5 mm lead pitch, not changed), 7.07 mm to J11. All zones of other nets keep 2.0 mm from C2 to C9, and the board clearance (0.8 mm) from C1.1 (see the areas table) |
| Thicken the small traces, add general thickness | Every track is 1.3 mm (rev1: 0.5 mm). 1.3 mm is the largest width that leaves an XH pin with 0.8 mm to the next pin. Zone copper is 1.2 mm or wider (`zone_min_width`), except the `_FINE` zones at U3 (0.5 mm minimum, prongs and strip 0.6 mm). The 3.3 V bars are 1.3 to 2.0 mm (the bar at U3.5 is 1.32 mm) |
| Do not worry about the pin headers | The XH headers keep their footprint. Their pads are 0.6 mm apart (listed as `MILL-GAP-FIXED`) |
| Drop the surface mount LEDs | No D2, D3, D4 and no R1, R2, R3 |
| Apply the 2 mm rule to the USB pigtail ports | J6 and J7 have no exception. Their pads are 2.18 mm apart and 2.8 mm or more from pads of other parts (J6.2 to TP1). The `+5V_CPU` bar between them moved 2 mm west, in line with the trunk: it is 2.35 mm from the GND pads J6.2 and J7.2. The branch to C3 is 2.25 mm from J7.2 |
| U1 and U2: add space at VOUT | The GND pours keep 2.0 mm from the VOUT pads on both layers. The VOUT necks (planned 5 V zones on the VOUT pads) and the GND areas at the module GND pads keep the board clearance (0.8 mm). The VOUT pads are 0.64 mm from the GND pads of the module (pin pitch 2.54 mm): this gap cannot change |
| Through-hole soldering is difficult | Annular ring 0.8 mm on the THT pads of C1, C2 to C8, J1, J6, J7 and on the four outer pads of F1 (`annular_target`). The four F1 pads next to the holder hole keep 0.45 mm: they are 0.31 mm from that unplated hole. XH headers, modules and C9 keep 0.45 mm (pitch) |

## Areas without the 2 mm copper gap

In these areas a zone has the board clearance (0.8 mm) or the footprint fixes a smaller gap. They are in `pcb/src/placement.py` (`_NEAR`, `_NEAR_GND`, `_FINE`) and in the `[[exception]]` entries of the tuning file.

| Area | Gap | Cause |
| --- | --- | --- |
| U3 (SOT-23-5): pads, two `/LDO_IN` prongs, GND strip, `+3V3_SENS` bar at U3.5 | 0.34 to 0.35 mm | Pad gap of the footprint. Owner decision: U3 stays |
| XH headers J3, J4, J5, J8, J9, J11 to J14: pad to pad | 0.6 mm | 2.5 mm pin pitch. Tracks and zones keep 0.8 mm from the pads |
| Modules U1, U2: pad to pad | 0.64 mm | 2.54 mm pin pitch (`own_pads = true`) |
| Modules U1, U2: VIN and VOUT necks, GND areas, to the module pads | 0.8 mm | The necks are as wide as the pads. With 2 mm they do not reach the pads |
| Left edge, x 0.6 to 12.5 mm, y 27 to 105.5 mm (x to 10.1 mm at y 86.9 to 95, 2 mm from C9.1): GND between header pins, tracks and the edge. `+5V_SENS` bar at J8.1/J11.1 and its branch to J9.1 | 0.8 mm | The 2 mm pour leaves no GND copper between the pins and the edge |
| Right edge, x 58.6 to 65.4 mm, y 103.5 to 132 mm: GND at J12 to J14 and the three `+3V3_SENS` teeth | 0.8 mm | Same |
| Bottom edge, y 0.6 to 7.4 mm, x 28 to 65.4 mm: GND trunk from J1.2, and the VBAT stub to C1. C1.1 is 0.8 mm from the trunk | 0.8 mm | The trunk needs 6.0 mm. With 2 mm to the C1.1 pad it has 5.4 mm |
| GND at the module GND pads (x 20.4 to 25.5 and 48.4 to 53.5 mm, y 41 to 51 mm) to the VIN and VOUT necks | 0.8 mm | With 2 mm on both sides the GND copper there is 1.6 mm wide. It is 1.9 mm now |
| All tracks (signals, `+6V_BEC`): track to track, track to pad | 0.8 mm | The tracks start at header pins |

All other copper has a 2.0 mm gap: the pours to the VBAT, 5 V, `/LDO_IN` and `+3V3_SENS` zones and to all pads except at U3, and the zones to the pads of C2 to C9, D1, FB1, F1, J1, J6, J7 and the test points. A gap scan of the board (all copper pairs below 2.0 mm, 2026-11-17) found no other gap.

## Other differences from rev1

- 34 parts (rev1: 40).
- C2 and C4 (input capacitors of U1 and U2) are north of the pin rows, about 6 mm from the VIN pads, on a VBAT stub. On rev1 they are under the modules on the bottom side. A through-hole part has no room under a module.
- C3 is on the `+5V_CPU` bar north of J7. C5 is on the `+5V_SENS` trunk. C6 and C7 are south of the `/LDO_IN` bar, C8 is on the `+3V3_SENS` bar.
- Test points TP1, TP2, TP3 are on the rail trunks.
- First print round only: wire solder pads in place of the JST XH headers (see the section above).
- J9 and J11 are at x = 4.3 mm (rev1: 3.65 mm).
- The `U1_PG` stub and its rivet are at x = 39.6 mm (rev1: 40.4 mm).
- The schematic variant sets MPN, Manufacturer, Supplier link and Status of C2 to C8 to TBD, and the unit cost to empty. The rev1 part numbers are 0805 parts. `BOM Comments` keeps the rev1 part number and note.
- Not changed: outline 66 x 140 mm, mounting holes, modules, fuse, D1 (SMB), FB1 (0805), the other connector positions, Power5A width (1.6 mm), edge clearance (0.5 mm).

## Check results

| Check | Result |
| --- | --- |
| `make erc BOARD=src` | 0 errors, 3 warnings (`lib_symbol_mismatch`, as rev1) |
| `make pcb-rules BOARD=src` | The project files agree with the design rules. 16 values assumed |
| `make pcb-check BOARD=src` | DRC: 0 errors, 0 unconnected, parity clean. 117 warnings: 26 `lib_footprint_mismatch` (pads changed by the build), 91 `silk_over_copper` (silkscreen of the library footprints; the milled board has no silkscreen). `check_board`: 0 problems |
| `make pcb-mill-check BOARD=src` | 2026-11-25, lab CAM isolation bits (0.6 mm corn, 0.2 mm end mill, F-006): 0 errors, 0 waived, 103 warnings: 85 `MILL-GAP-FIXED`, 9 `MILL-CUT-SPACING`, 9 `MILL-CONN-EDGE`. 127 `MILL-GAP-BIT` areas (only the 0.2 mm end mill fits). No `MILL-SLIVER`, no `MILL-ISLAND`. Tools to stage: 8 (`milling_check.json`, key `tools`) |
| `make pcb-fab BOARD=src` | Outputs in `build/fab/src/` (not committed). The target then runs `test_fab.py` on the mill board: 20 tests, OK |
| `make bom BOARD=src` | `pcb/src/bom.csv`. C2 to C8: part number TBD, no cost. Wire pads: no part. Total 90.73 USD |
| `make pcb-test` | 108 + 61 = 169 tests, OK (2026-11-18) |
| `make pcb-gate BOARD=src` | FAIL from the count false positive, 2 WARN (no silkscreen by design). EMC 71.5/100. Verdicts: section "kicad-happy analysis" |

Copper width along the current paths (opening test, B.Cu):

| Path | Need | Measured |
| --- | --- | --- |
| GND trunk J1 to the pour at U1 | 6.0 mm | 6.80 mm |
| GND entrance U1, entrance U2 | 1.6 mm | 2.14 mm, 1.88 mm |
| GND J6/J7 to U1 | 1.6 mm | 2.14 mm |
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

- **`MILL-GAP-FIXED` (85).** Gaps below 0.792 mm (cut width + 2 x 0.25 mm) that the footprints fix. A THT pad pair counts on both copper layers. Modules U1 and U2: pad to pad, 0.64 mm. XH headers: pad to pad, 0.6 mm. U3: pad to pad and zone to pad, 0.34 to 0.35 mm. With an error of 0.25 mm for each side, a cut at U3 can remove most of a 0.6 mm wide pad, prong or strip. U3 is the risk item of this board.
- **`MILL-CUT-SPACING` (9).** Copper below 1.2 mm (2.0 mm cut spacing - 0.8 mm clearance): the two `/LDO_IN` prongs (0.6 mm), the U3 GND strip (0.6 mm), the places where the three `+3V3_SENS` teeth meet the bar, the corners where the two VBAT capacitor stubs meet the necks, and a GND tongue of 0.6 mm south of U2.9 (between the 2 mm gap to VBAT prong B and the 0.8 mm gap to the `+5V_SENS` neck). A smaller GND area leaves a sliver below 0.5 mm there.
- **`MILL-CONN-EDGE` (9).** J9 and J11: the courtyard is more than 1.0 mm from the board edge (1.45 mm). The connectors moved in for the GND strip west of their pads. J3, J4, J5, J8, J12, J13 and J14: the courtyard of the wire pads is smaller than the header body (temporary exception).

## Margins without spare

- `clearance` 0.8 mm against the minimum 0.792 mm. If `horizontal_error` goes up, raise `clearance`. The tracks then get narrower than 1.3 mm at the XH pins, or do not fit.
- `horizontal_error` is used for copper gaps only. The edge clearance (0.5 mm), the annular rings and the holes have no allowance for it.
- `+5V_SENS` load path: 1.67 mm against 1.6 mm. `+6V_BEC`: 1.29 mm against 1.3 mm.
- Pad gap C6 to FB1: 2.03 mm against 2.0 mm.

## Not verified

- No review of this layout by a person. No KiCad GUI check. No second `pcb-reviewer` run after the fixes of 2026-11-17 (the kicad-happy review of 2026-11-18 changed no board file).
- The capacitor type: the footprint is a 5.0 mm pitch disc. The capacitor values of the schematic are TBD (C7, C8: 1 uF). A part with 2.5 mm lead pitch needs formed leads or a different footprint.
- The effect of the new positions of C2 and C4 (about 6 mm from the VIN pads) was not analyzed. The modules have their own input capacitors.
- The body height and the body size of the capacitors next to the modules and connectors (courtyards do not overlap in DRC).
- Rivet and solder access, 3D collisions, wire entry at J9 and J11.
- The wire solder pads: wire gauge of each harness, hole fit and strain relief. Not checked on real wires.
- The routing is made again in each `make pcb-all` run. Freerouting now runs with one thread (`-mt 1`): the same DSN gives the same route (3 runs). The DSN export of two builds is not identical, so the track shapes can still change. Two builds in a row passed all checks.
- The mill did not cut this board. The schematic PDF of the mill variant is not plotted.
- A 2 mm copper gap with a single-pass contour toolpath leaves a loose copper strip of about 1.4 mm between the two cuts. A 0.8 mm gap leaves a strip of 0.8 - 2 x 0.292 = 0.22 mm. The lab CAM must remove the strips or leave them. Not checked with the lab.
- The meaning of "2 mm between cuts". This record uses track + gap = 2.1 mm (gap center to gap center). Between the two toolpaths beside a 1.3 mm track the distance is 1.59 mm. Not confirmed by the lab tech.

## kicad-happy analysis (`make pcb-gate BOARD=src`, kicad-happy 2.3.2, 2026-11-18)

Gate: FAIL from the count false positive and WARN for the silkscreen (`pcb/.claude/skills/pcb-fab/references/fab-gate.md`). EMC score 71.5/100 with `analyze_pcb --full`. Verdicts from `pcb-reviewer` (2026-11-18), checked in the raw board file. Suppressed findings are in `pcb/src/.kicad-happy.json`, each with its reason.

| Finding | Verdict | Evidence | Action |
| --- | --- | --- | --- |
| GP-001 (error) `/THROTTLE_PWM`, `/I2C_SCL`, `/I2C_SDA`, `/STEER_PWM` | True geometry, the mechanism does not apply | The tracks are on B.Cu. The F.Cu pour `GND_F` has `connect_pads no` and joins GND at one rivet (68.1, 42.1), about 80 mm away, so it is not a return conductor. The return is the B.Cu GND beside the tracks (STEER 90 %, SDA 79 %, SCL 74 %, THROTTLE 0 % within 2.5 mm) and the harness GND. Servo PWM and I2C at 400 kHz or less, tracks 12 to 41 mm. The J5 pin order (rule C: 1 PG, 2 THROTTLE, 3 STEER) forces the crossing of the F.Cu `U1_PG` jumper | Owner decision: accept, or change the J5 pin order (schematic, harness, crimp table) |
| GP-001 (warning) `/U1_PG`, RP-001 `/U1_PG` | True, no EMC effect | PG is a static open-drain status line. The nearest GND via is about 85 mm from the PG rivets. Next to the west rivet there is no legal site for a GND rivet (J3.3 is 2.3 mm away) | Owner decision: accept |
| VS-001 | True | The board has one GND rivet | Owner decision: one GND rivet north of each module GND pad pair (open question 3) |
| DC-001 C4/U2, C2/U1 | True | 6.38 mm centre to centre, 4.23 mm pad edge to pad edge. 3 mm is not possible within `component_gap` 2.0 mm. The smallest legal distance is 3.32 mm (C4 pad 1 at placement (19.43, 49.75), C2 at (47.43, 49.75)), but the `U1_PG` jumper at y 130.2 must move north first. The gain is small: the modules are not bare ICs | Owner decision: one jumper re-route, or accept. A lab-confirmed lower `component_gap` changes the result |
| PM-002 J1 | False positive | Pad copper 1.0 mm from the edge (edge_clearance 0.5 mm). The courtyard at 0.8 mm meets connector_edge_distance (1.0 mm or less). The 3.4 mm bored hole leaves a 1.8 mm FR-4 web to the edge: the strain relief must be on the harness | Suppressed |
| TE-001 | False positive in practice | TP1 to TP3 are on the rails. Each signal ends on a bare B.Cu wire pad (J3, J4, J5, J8), which is a probe point | Suppressed |
| PU-001 U1 PG, U3 EN | False positive | `power_board_plan.md`, AP2112 datasheet | Suppressed. Open item: `firmware/esp32/include/pins.h` has no PG input with a pull-up yet, so J5.1 floats until the firmware has one (a GPIO that is not a strapping pin) |
| GP-004 GND fill | Owner decision | The 2.0 mm copper gap (`zone_clearance`, owner 2026-11-17) | Suppressed |

The analyzer also reports 9 GND islands in its connectivity graph. This is an analyzer artifact (overlapping zones of one net, and the F.Cu pour with `connect_pads no`). DRC reports 0 unconnected items.

## Open owner decisions

1. C2 to C8: radial capacitor part numbers and ratings. The rev1 values: 10 uF >= 16 V (C2, C4, C6), 22 uF >= 10 V (C3, C5), 1 uF (C7, C8), all with 5.0 mm lead pitch.
2. Thermal reliefs (spokes of 1.2 mm or more, relief gap of 0.8 mm or more) on the GND and VBAT pads of C2 to C9. They make hand soldering easier and add cuts near these pads. Keep the full connection on J1, F1, J6, J7 and the modules.


## Questions for the lab tech

1. What is the real horizontal error of the mill? The tuning file uses 0.25 mm for each side.
2. Is a 2 mm copper gap cut as two passes with a loose strip between them, or cleared? Is a loose strip a problem?
3. Are the gaps at U3 (0.34 to 0.35 mm, cut width 0.292 mm) possible on this mill? If not, U3 needs a different package or a module.
4. Which through-hole ceramic capacitors are in stock (lead pitch, values up to 1 uF or more, voltage)?
5. Is a 0.8 mm ring sufficient for hand soldering on holes without plating? Is 0.45 mm at the XH headers, the modules, C9 and four F1 pads acceptable?
6. Is "2 mm between cuts" the distance between the two toolpaths, or between the gap centers (track + gap)? How does the CAM cut a 0.8 mm gap: one pass with a 0.22 mm strip, or cleared?
