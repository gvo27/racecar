# Layout and fab handoff (Rev A, KiCad 10)

For the owner doing layout. Parts: `bom.md`. Design intent: `design_overview.md`. Numbers come from the IPC tables in `power_board_plan.md`; nothing here is a verified fab limit.

## Layout

- **Stack:** 2 layers, 2 oz outer copper recommended (HighCurrent class). Set 0.07 mm in Board Setup > Physical Stackup.
- **Net classes** (from `rc_power_board.kicad_pro`; HighCurrent = `*VBAT*`, GND; Power5A = `+5V_CPU`; Power3A = `+5V_SENS`, `*+6V_BEC`):

| Class | Track width | Via (drill / pad) |
| --- | --- | --- |
| HighCurrent | 6.0 mm or a zone | 0.6 / 1.2 mm, many in parallel |
| Power5A | 1.5 mm | 0.4 / 0.8 mm |
| Power3A | 1.0 mm | 0.4 / 0.8 mm |
| Default | 0.25 mm | 0.3 / 0.6 mm |

  Clearance 0.2 mm. `VIN_CPU` / `VIN_SENS` no longer exist: U1 and U2 VIN sit on `VBAT`.
- **HighCurrent copper follows F1, not the load.** Copper for VBAT_RAW/VBAT/GND must be sized for F1's rating, not the 7.3 A load (a MINI fuse holds 110% indefinitely): a 15 A fuse means sizing for about 16.5 A; 10 A means about 11 A. `power_board_plan.md` has no IPC figure for these currents (its tables stop at 8 A and 20 A), so use KiCad Calculator Tools → Track Width (IPC-2152) for that current. A pour is preferred anyway.
- **U1 header:** neck the `VBAT` and `GND` copper down to the 2.54 mm pin pitch only at the pins; keep the wide pour up to the pad. Use both pins of each pair (3 A per pin).
- **Ground:** solid GND pour on both layers, stitching vias, star point at J1.
- **High-current pads** (J1, F1 holder, U1 VIN/GND, C1): thermal reliefs off, or heavier spokes.
- **F1:** holder on a board edge, accessible with the board mounted.
- **Noise:** keep U3, FB1/C6 and any IMU/encoder area away from the buck switching nodes and inductors.

## DRC

Use the fab's published capabilities or DRC rules file for 2-layer boards (JLCPCB, PCBWay); do not rely on KiCad defaults. Use 1.6 mm board thickness and 2 oz outer copper as the plan says.

## Gerber and drill export (KiCad 10 Plot)

- [ ] Layers: F.Cu, B.Cu, F.Mask, B.Mask, F.Silkscreen, B.Silkscreen, Edge.Cuts; F/B.Paste only if the fab assembles.
- [ ] Drill: Excellon, plus drill map.
- [ ] Zip the folder; open it in a Gerber viewer before upload.

## Sign-off

- [ ] ERC clean (KiCad 10, owner-run)
- [ ] DRC clean (fab rules)
- [ ] 3D view check
- [ ] Footprints vs real parts: U2 dimension drawing, J1 drill (12 AWG), F1 holder pins
- [ ] BOM reviewed (`bom.md`)

## Open items before publish

1. Fuse type (Mini/ATM assumed) and F1 rating, 10 vs 15 A.
2. Reverse-polarity decision: the proposal (P-FET) is in the PR, not on the board.
3. U2 selection and footprint (D24V50F5 proposed; none in schematic yet).
4. All `TBD` values in the schematic.
5. U1 EN stays unconnected until the rev 2 prototype board.
