# Layout and fab handoff (Rev A, KiCad 10)

For the owner doing layout. Parts: `bom.md`. Design intent: `design_overview.md`. Numbers come from the IPC tables in `power_board_plan.md`; nothing here is a verified fab limit.

## Layout

- **Stack:** 2 layers, 2 oz outer copper recommended (HighCurrent class). Set 0.07 mm in Board Setup > Physical Stackup.
- **Net classes** (from `rc_power_board.kicad_pro`; HighCurrent = `*VBAT*`, GND; Power5A = `+5V_CPU`; Power3A = `+5V_SENS`, `*+6V_BEC`):

| Class | Track width | Via (drill / pad) |
| --- | --- | --- |
| HighCurrent | 6.0 mm or a zone | 0.6 / 1.2 mm, many in parallel |
| Power5A | 1.6 mm | 0.4 / 0.8 mm |
| Power3A | 1.0 mm | 0.4 / 0.8 mm |
| Default | 0.25 mm | 0.3 / 0.6 mm |

  Clearance 0.2 mm. `VIN_CPU` / `VIN_SENS` no longer exist: U1 and U2 VIN sit on `VBAT`.
- **HighCurrent copper follows F1, not the load.** Copper for VBAT_RAW/VBAT/GND is sized for F1's rating, not the 7.8 A load (a blade fuse holds 110% indefinitely): 15 A means about 16.5 A; 10 A means about 11 A. Computed widths (IPC-2221, external layer, mm; `I = 0.048·ΔT^0.44·A^0.725`, A in mil², 1 oz = 1.378 mil):

| Net | Design current | 1 oz ΔT10 | 1 oz ΔT20 | 2 oz ΔT10 | 2 oz ΔT20 | Net class now |
| --- | --- | --- | --- | --- | --- | --- |
| VBAT_RAW / VBAT / GND (F1 15 A × 1.1) | 16.5 A | 14.4 | 9.4 | 7.2 | 4.7 | HighCurrent 6.0 |
| VBAT_RAW / VBAT / GND (F1 10 A × 1.1) | 11 A | 8.2 | 5.4 | 4.1 | 2.7 | HighCurrent 6.0 |
| VBAT load at 6.0 V (reference) | 7.8 A | 5.1 | 3.4 | 2.6 | 1.7 | — |
| +5V_CPU | 5.5 A | 3.2 | 2.1 | 1.6 | 1.0 | Power5A 1.6 |
| +5V_SENS (module max / budget) | 5.0 / 3.3 A | 2.8 / 1.6 | 1.8 / 1.0 | 1.4 / 0.8 | 0.9 / 0.5 | Power3A 1.0 |
| +6V_BEC | 3.0 A | 1.4 | 0.9 | 0.7 | 0.45 | Power3A 1.0 |
| +3V3_SENS, I2C, PWM, PG | ≤ 0.3 A | < 0.1 | < 0.1 | < 0.1 | < 0.1 | Default 0.25 |

  **Recommendation:** 2 oz copper. HighCurrent 6.0 mm or a pour covers the 15 A fuse (about ΔT 13–15 °C); Power5A is now 1.6 mm; Power3A 1.0 mm is OK. At 1 oz every width roughly doubles and HighCurrent must be a pour. IPC-2221 is conservative versus IPC-2152 for boards with planes. Neck down only at pads and the U1 header.
- **I2C:** keep `I2C_SDA`/`I2C_SCL` short-ish and routed together over the GND pour from J8 to J5.
- **J5 harness:** keep short; twist SDA and SCL each with a GND or route them beside GND; one GND pin for 5 signals is fine for a short lead.
- **U1 header:** neck the `VBAT` and `GND` copper down to the 2.54 mm pin pitch only at the pins; keep the wide pour up to the pad. Use both pins of each pair (3 A per pin).
- **Ground:** solid GND pour on both layers, stitching vias, star point at J1.
- **High-current pads** (J1, F1 holder, U1 VIN/GND, C1): thermal reliefs off, or heavier spokes.
- **F1:** FLR 178.6165 holder on a board edge, accessible with the board mounted (fuse replaceable in place).
- **Noise:** keep U3, FB1/C6 and any IMU/encoder area away from the buck switching nodes and inductors.

## Connector pin order and crimping

**Pin order convention** (all XH, pin numbers as in the schematic):

- **Rule A, device with its own standard pinout:** the header follows the device so wire colours run straight through. J3 (ESC lead) and J4 (servo): 1 GND (black/brown), 2 +6V_BEC (red), 3 signal (white/orange). J8 (Garmin): 1 +5V_SENS red, 2 GND black, 3 I2C_SDA white, 4 I2C_SCL green.
- **Rule B, generic power header:** 1 V+, 2 GND. J9, J11 (+5V_SENS); J12, J13, J14 (+3V3_SENS).
- **Rule C, signal harness:** signals in order, GND last. J5: 1 U1_PG, 2 THROTTLE_PWM, 3 STEER_PWM, 4 I2C_SDA, 5 I2C_SCL, 6 GND.

**Crimp table** (header JST B*n*B-XH-A, housing XHP-*n*, contact SXH-001T-P0.6; suggested wire colours; device colours are fixed only for J8 (Garmin) and the servo/ESC leads):

| Ref | XH size | Housing | Pin | Net | Wire colour | Far end |
| --- | --- | --- | --- | --- | --- | --- |
| J3 | 3 | XHP-3 | 1 | GND | black / brown | ESC receiver lead |
| | | | 2 | +6V_BEC | red | ESC receiver lead |
| | | | 3 | THROTTLE_PWM | white / orange | ESC receiver lead |
| J4 | 3 | XHP-3 | 1 | GND | black / brown | DS3225MG servo |
| | | | 2 | +6V_BEC | red | DS3225MG servo |
| | | | 3 | STEER_PWM | white / orange | DS3225MG servo |
| J5 | 6 | XHP-6 | 1 | U1_PG | any | ESP32 (GPIO TBD) |
| | | | 2 | THROTTLE_PWM | any | ESP32 GPIO5 |
| | | | 3 | STEER_PWM | any | ESP32 GPIO4 |
| | | | 4 | I2C_SDA | any | ESP32 GPIO8 |
| | | | 5 | I2C_SCL | any | ESP32 GPIO9 |
| | | | 6 | GND | black | ESP32 GND |
| J8 | 4 | XHP-4 | 1 | +5V_SENS | red | Garmin LIDAR-Lite v4 pin 1 |
| | | | 2 | GND | black | Garmin pin 2 |
| | | | 3 | I2C_SDA | white | Garmin pin 3 |
| | | | 4 | I2C_SCL | green | Garmin pin 4 |
| J9 | 2 | XHP-2 | 1 / 2 | +5V_SENS / GND | red / black | Camera USB hub |
| J11 | 2 | XHP-2 | 1 / 2 | +5V_SENS / GND | red / black | Spare 5 V |
| J12 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | IMU |
| J13 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | Shaft encoder |
| J14 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | Spare 3.3 V |

Verified against the kicad-cli netlist of `rc_power_board.kicad_sch`. J3/J4 current: XH is 3 A/pin with 22 AWG only; see `bom.md`.

**Finding cavity 1 before the PCB exists.** An XH header/housing pair is keyed, so header pin N always mates with housing cavity N regardless of PCB orientation; crimping depends only on pin numbers.

1. Find pin 1 on a loose header from JST's XH drawing (KiCad footprint: pad 1 is the roundrect pad) and mark it.
2. Snap an empty housing onto the header and mark the cavity over pin 1.
3. Crimp and insert contacts by pin number.
4. After crimping, plug each lead into the marked header and buzz pin-to-wire with a multimeter.

**Layout rule:** place XH headers on the board edge, wire entry facing outward, pin 1 at the same end for all headers; leave slack in harness lengths until layout fixes positions.

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
- [ ] Footprints vs real parts: U2 dimension drawing, J1 drill (12 AWG), F1 holder (FLR 178.6165) pins, XH header footprints
- [ ] BOM reviewed (`bom.md`)

## Open items before publish

1. F1 rating, 10 vs 15 A (ATO/ATC blade in FLR holder assumed).
2. Reverse-polarity decision: the proposal (P-FET) is in the PR, not on the board.
3. U2 selection and footprint (D24V50F5 proposed; none in schematic yet).
4. All `TBD` values in the schematic.
5. U1 EN stays unconnected until the rev 2 prototype board.
6. I2C pull-ups: bus is pulled up only by the Garmin's internal 13 kΩ; consider two DNP 0805 4.7–10 kΩ pull-up footprints on I2C_SDA/I2C_SCL to `+3V3_SENS` (the sensor rail; ESP32 powers nothing) for a future IMU on the same bus (4.7 k ∥ 13 k ≈ 3.5 kΩ, fine at 400 kHz). Not drawn.
