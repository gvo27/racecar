# Power board BOM (Rev A draft, schematic parts only)

Companion to `design_overview.md`; layout and fab steps are in `fab_handoff.md`. Schematic values stay as drawn (TBD where unconfirmed); MPNs here are proposals. Every MPN below is **proposed**, pending owner approval. Reference list: 39 parts, per the regenerated netlist. J10 is intentionally absent (radar removed).

Prices/stock as checked 2026-10-30; confirm before ordering.

| Ref(s) | Qty | Function | Schematic value | Proposed MPN | Footprint | Key spec checked | Link | Est. unit cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 1 | Single main fuse, all board loads | TBD ATM mini blade 10-15A | Littelfuse 0297015.WXNV (15 A, recommended); alt. 0297010.WXNV (10 A) | via F1 holder | MINI 297: 32 VDC, 1000 A interrupting; see fuse notes | — | est. 0.30 (buy spares) |
| F1 holder | 1 | PCB holder for F1 | n/a (part of F1 symbol) | Keystone 3568 | `Fuse:Fuseholder_Blade_Mini_Keystone_3568` | Vertical-entry THT; listed 30 A (DigiKey) / 20 A (some listings); confirm on the datasheet for the suffix ordered; either exceeds F1; takes Littelfuse 297/997, Bussmann ATM | [DigiKey](https://www.digikey.com/en/products/detail/keystone-electronics/3568/2137306) | 0.76-1.31 (est. 1.00) |
| U1 | 1 | Compute 5 V buck (Pi 5 + ESP32) | `Pololu D36V50F5 buck (req 5.1V >=6A TBD)` | Pololu D36V50F5 (in hand) | `PinHeader_2x06_P2.54mm_Vertical` | 5.0 V, 5.5 A typ; reverse protection to 40 V; 3 A per header pin | [Pololu 4091](https://www.pololu.com/product/4091) | 39.95 (in hand) |
| U2 | 1 | Sensor 5 V buck | `5V buck >=4A module, TBD` | Pololu D24V50F5 (proposed; not bought) | TBD: needs Pololu dimension drawing (none in schematic yet) | 5 V, 5 A; 38 V max in; reverse-voltage, OC, short-circuit and OT protection; soft start. Dropout about 0.7-1.5 V depending on load: output may sag near the 6.0 V battery cutoff (flag, verify at load) | [Pololu 2851](https://www.pololu.com/product/2851) | 32.95 |
| D1 | 1 | TVS on VBAT | `TVS >=9V TBD` | Littelfuse SMBJ10A | SMB | Unidirectional; 10 V standoff, 11.1 V min breakdown, 17.0 V max clamp at 35.3 A; 600 W | [DigiKey](https://www.digikey.com/en/products/detail/littelfuse-inc/SMBJ10A/285966) | 0.43 |
| C1 | 1 | VBAT bulk | `TBD uF >=16V` | Panasonic EEU-FR1E471 | `CP_Radial_D10.0mm_P5.00mm` | 470 uF, 25 V, 10 mm dia, 5 mm pitch, 105 C; footprint matches | [DigiKey](https://www.digikey.com/en/products/detail/panasonic-industry/EEU-FR1E471/2433553) | est. 0.70 |
| C2, C4, C6 | 3 | Buck inputs (C2, C4); LC filter cap (C6) | C2, C4 `TBD >=16V`; C6 `TBD filter` | YAGEO CC0805KRX5R8BB106 | 0805 | 10 uF, 25 V, X5R. X5R loses capacity under DC bias; verify effective value at 8.4 V. Samsung CL21A106KAYNNNE was out of stock | [DigiKey](https://www.digikey.com/en/products/detail/yageo/CC0805KRX5R8BB106/7164387) | est. 0.10 |
| C3, C5 | 2 | 5 V outputs (U1, U2) | `TBD >=10V` | Murata GRM21BR61A226ME44L | 0805 | 22 uF, 10 V, X5R. **Flag:** 10 V X5R on a 5 V rail loses much capacitance to DC bias; consider a 16 V part (e.g. 22 uF 16 V X5R 0805/1206). DigiKey backorder; YAGEO CC0805MKX5R6BB226 listed as substitute (no link) | [DigiKey](https://www.digikey.com/en/products/detail/murata-electronics/GRM21BR61A226ME44L/4905527) | 0.30 |
| C7, C8 | 2 | LDO in / out | `1uF TBD` | Samsung CL21B105KBFNNNE | 0805 | 1 uF, 50 V, X7R. DigiKey backorder; Mouser in stock | [DigiKey](https://www.digikey.com/en/products/detail/samsung-electro-mechanics/CL21B105KBFNNNE/3886687) | 0.12 |
| FB1 | 1 | Ripple filter ahead of LDO (optional) | `TBD filter` | Murata BLM21PG221SN1D | 0805 | 220 ohm at 100 MHz, 2 A, 45 mohm | [DigiKey](https://www.digikey.com/en/products/detail/murata-electronics/BLM21PG221SN1D/364909) | est. 0.10 |
| U3 | 1 | 3.3 V LDO (IMU, encoder) | `AP2112K-3.3 (>=300 mA LDO, TBD)` | Diodes AP2112K-3.3TRG1 | SOT-25 | 600 mA; 6 V max in (fed from 5 V) | [DigiKey](https://www.digikey.com/en/products/detail/diodes-incorporated/AP2112K-3-3TRG1/4470746) | est. 0.40 |
| R1, R2 | 2 | LED resistors (5 V rails) | `1k5` | YAGEO RC0805FR-071K5L | 0805 | 1.5 kohm; LED current about (5 - 2.1) / 1.5k = 2 mA | [DigiKey](https://www.digikey.com/en/products/detail/yageo/RC0805FR-071K5L/727496) | est. 0.10 |
| R3 | 1 | LED resistor (3.3 V rail) | `680R` | YAGEO RC0805FR-07680RL | 0805 | 680 ohm; about (3.3 - 2.1) / 680 = 1.8 mA | [DigiKey](https://www.digikey.com/en/products/detail/yageo/RC0805FR-07680RL/728101) | est. 0.10 |
| D2-D4 | 3 | Rail indicator LEDs | `LED` | Lite-On LTST-C171GKT | 0805 | Green; Vf 2.1 V typ at 20 mA | [DigiKey](https://www.digikey.com/en/products/detail/liteon/LTST-C171GKT/386793) | est. 0.25 |
| J3, J4 | 2 | ESC lead (J3); servo DS3225MG (J4) | J3 `ESC Rx lead (BEC out, throttle in)`; J4 `Servo DS3225MG` | 2.54 mm male break-away header, Adafruit 392 (36-pin, 10-pack) | 1x03 P2.54 mm | One pack covers J3-J5 | [Adafruit 392](https://www.adafruit.com/product/392) | 4.95 per pack |
| J5 | 1 | 1x04 header to ESP32 | `Signals to ESP32` | as above | 1x04 P2.54 mm | Pins: U1_PG, THROTTLE_PWM, STEER_PWM, GND | (same pack) | (same pack) |
| J6, J7 | 2 | USB-C pigtail power out (Pi 5, ESP32) | J6 `USB-C Pi 5`; J7 `USB-C ESP32` | Phoenix Contact 1715721 (MKDS 1,5/2-5,08) | 2-pos, 5.08 mm | 15-17.5 A | [DigiKey](https://www.digikey.com/en/products/detail/phoenix-contact/1715721/260631) | est. 0.80 |
| J8, J9, J11, J12, J13, J14 | 6 | 2-pos sensor / spare connectors | J8 `LIDAR-Lite v4`; J9 `Camera USB hub`; J11 `Spare 5V`; J12 `IMU`; J13 `Shaft encoder`; J14 `Spare 3.3V` | JST B2B-XH-A(LF)(SN) | 2-pos, 2.5 mm | 3 A | [Mouser](https://www.mouser.com/ProductDetail/JST-Commercial/B2B-XH-ALFSN?qs=cdbOS8ANM9DdcSn9qRmfCw%3D%3D) | est. 0.10 |
| mating, J8 etc. | 6 | XH housing | n/a | JST XHP-2 | n/a | Mates B2B-XH-A | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/XHP-2/555485) | est. 0.10 |
| mating, J8 etc. | 12 | Crimp contacts | n/a | JST SXH-001T-P0.6 | n/a | 22-28 AWG | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/SXH-001T-P0-6/527371) | est. 0.10 |
| J1 | 1 | Battery pigtail wire pads | `Battery T-plug pigtail 12AWG` | none (pads only; 12 AWG T-plug pigtail is the owner's) | `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm` (placeholder) | See J1 note | — | — |
| TP1-TP3 | 3 | Test points | `+5V_CPU`, `+5V_SENS`, `+3V3_SENS` | none (bare pads) | 1.5 mm pad | | — | — |
| H1-H4 | 4 | M3 mounting holes | `MountingHole_M3` | none; M3 screws/standoffs optional | M3 hole | | — | — |

## Subtotal (one board, estimated)

| Group | USD |
| --- | --- |
| F1 + holder (1 fuse) | 1.30 |
| U1 (in hand) | 39.95 |
| U2 (proposed) | 32.95 |
| D1, C1-C8, FB1, U3, R1-R3, D2-D4 | 3.82 |
| Headers (one Adafruit pack) | 4.95 |
| J6/J7 | 1.60 |
| J8-J14 JST (6) + housings (6) + crimps (12) at 0.10 each | 2.40 |
| **Total** | **about 87.0** |

Excluding U1 (already owned): about 47.0. (Check: 1.30 + 39.95 + 32.95 + 3.82 + 4.95 + 1.60 + 2.40 = 86.97; minus 39.95 = 47.02.) PCB fabrication is not included; list it separately as est. (quote from the chosen fab). Buy spare fuses and a few spare passives.

## Out of stock / backorder (as checked)

- Samsung CL21A106KAYNNNE (10 uF): out of stock; replaced by YAGEO CC0805KRX5R8BB106.
- Murata GRM21BR61A226ME44L: DigiKey backorder; substitute YAGEO CC0805MKX5R6BB226 (no link verified).
- Samsung CL21B105KBFNNNE: DigiKey backorder; in stock at Mouser.

## Fuse notes (F1)

- **Series:** Littelfuse MINI 297 (32 VDC, 1000 A interrupting). It is a standard (fast-acting per distributors) ISO 8820-3 characteristic fuse, not time-delay. Opening time per the Littelfuse MINI 297 datasheet: 110% >= 100 h; 135% 0.75-600 s; 200% 0.15-5 s. (The 350% and 600% rows are per datasheet, confirm before relying on them.) Melting I2t of the 10 A part is about 93 A2s.
- **No dedicated slow-blow needed.** Plug-in inrush is C1 (470 uF) plus MLCCs charging: about V2 C / (2R) = 8.4^2 x 470 uF / (2 x 0.05 ohm) = 0.3 A2s, where R = 50 mohm is an **assumed** loop resistance; even at 10 mohm: about 1.7 A2s, ~55x margin below the 10 A fuse's melting I2t. The modules soft-start. Slow-blow parts (e.g. MAXI 299 Slo-Blo) are for motor inrush, and the motor/ESC is powered off-board.
- **Rating:** worst-case board load is about 7.3 A at 6.4 V and about 7.8 A at the 6.0 V cutoff (U1: 5.1 V x 5 A / (0.9 x 6.0 V) = 4.7 A, plus U2 about 3.1 A). On a 10 A fuse that is 73-78% of rating, at or over the ~75% continuous rule of thumb; a 15 A fuse gives 49-52%. Recommended 15 A, 10 A as the alternative; owner decides.
- **Copper must be sized for the fuse:** VBAT_RAW, VBAT and GND copper must carry F1's rating (a MINI fuse holds 110% indefinitely: about 16.5 A for 15 A, 11 A for 10 A), not just the 7.3 A load. If the copper is reduced, pick 10 A.
- **Pending:** fuse type confirmation by the owner before final publish.

## J1 footprint note

KiCad's `Connector_Wire` library (checked locally) has `SolderWire-*` footprints up to 2.5 sqmm only (no 4 sqmm variant): the one in the schematic, `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm`, has a 3.0 mm drill and a 4.4 mm pad ("D2.4mm" is the conductor diameter, not the drill). 12 AWG stranded tinned wire (about 2.05 mm) fits the 3.0 mm hole; the concern is the thin 0.7 mm annular ring at F1's current. Proposed: keep the 3.0 mm drill, enlarge the pad OD to at least 5 mm (custom copy of the footprint), thermal reliefs off. Verify against the actual wire.
