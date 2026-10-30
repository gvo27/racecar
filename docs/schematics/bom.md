# Power board BOM (Rev A draft, schematic parts only)

Companion to `design_overview.md`; layout and fab steps are in `fab_handoff.md`. Schematic values stay as drawn (TBD where unconfirmed); MPNs here are proposals. Every MPN below is **proposed**, pending owner approval. Reference list: 39 parts, per the regenerated netlist (21 nets). Connector convention: JST-XH (2.5 mm) for sensors and low-power parts; exceptions J1, J6, J7. J10 is intentionally absent (radar removed).

Prices/stock as checked 2026-10-30; confirm before ordering.

| Ref(s) | Qty | Function | Schematic value | Proposed MPN | Footprint | Key spec checked | Link | Est. unit cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 1 | Single main fuse, all board loads | `TBD ATO/ATC blade 10-15A` | Littelfuse 0257015.PXPV (ATO 257, 15 A, 32 V; recommended); alt. 0257010.PXPV (10 A) | via F1 holder | ATO/ATC 257: 32 VDC, 1000 A interrupting at 32 VDC, ISO 8820-3 / SAE J1284; melting I2t about 340 A2s (15 A, Littelfuse catalog); see fuse notes. 0257015.L is obsolete; DigiKey lists 0287015.PXCN (ATOF) as direct substitute | — | est. 0.40 (buy spares) |
| F1 holder | 1 | PCB holder for F1 | n/a (part of F1 symbol) | Littelfuse FLR 178.6165.0001 | `Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165` | Takes standard ATO/ATC blade fuses; 22.5 A continuous / 30 A max per the Littelfuse FLR datasheet; 32 V fuse system; either exceeds F1 | — | est. 3.00 (unverified) |
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
| J6, J7 | 2 | USB-C pigtail power out (Pi 5, ESP32) | J6 `USB-C Pi 5`; J7 `USB-C ESP32` | Phoenix Contact 1715721 (MKDS 1,5/2-5,08) | 2-pos, 5.08 mm | 15-17.5 A | [DigiKey](https://www.digikey.com/en/products/detail/phoenix-contact/1715721/260631) | est. 0.80 |
| J3, J4 | 2 | ESC lead (J3); servo DS3225MG (J4) | J3 `ESC Rx lead (BEC out, throttle in)`; J4 `Servo DS3225MG` | JST B3B-XH-A(LF)(SN) | 3-pos, 2.5 mm (XH) | 3 A/pin with 22 AWG only (lower for thinner wire); the BEC pin may carry up to the 3 A BEC limit = 100 % of the XH rating; servo stall 2.3 A = 77 %. Re-terminate ESC and servo leads only if they are 22 AWG (gauge TBD, measure); otherwise use a 22 AWG adapter lead. XH (2.50 mm) does not mate with stock 2.54 mm servo plugs. Pins: 1 GND, 2 +6V_BEC, 3 signal (see `fab_handoff.md`) | — | est. 0.15 |
| J5 | 1 | Signals to ESP32 | `Signals to ESP32` | JST B6B-XH-A(LF)(SN) | 6-pos, 2.5 mm (XH) | Pins: 1 U1_PG (GPIO TBD), 2 THROTTLE_PWM GPIO5, 3 STEER_PWM GPIO4, 4 I2C_SDA GPIO8, 5 I2C_SCL GPIO9, 6 GND | — | est. 0.15 |
| J8 | 1 | Garmin LIDAR-Lite v4 | `LIDAR-Lite v4` | JST B4B-XH-A(LF)(SN) | 4-pos, 2.5 mm (XH) | Pins match Garmin 1-4: 1 +5V_SENS (red; VIN 4.75-5.25 V, 85 mA acquiring), 2 GND (black), 3 I2C_SDA (white), 4 I2C_SCL (green). I2C address 0x62; internal 13 kohm pull-ups to 3.3 V, so no external pull-ups or level shifter. Source: branch `rangefinder` (5b409d0), not merged | — | est. 0.15 |
| J9, J11, J12, J13, J14 | 5 | 2-pos sensor / spare connectors | J9 `Camera USB hub`; J11 `Spare 5V`; J12 `IMU`; J13 `Shaft encoder`; J14 `Spare 3.3V` | JST B2B-XH-A(LF)(SN) | 2-pos, 2.5 mm (XH) | 3 A per pin | [Mouser](https://www.mouser.com/ProductDetail/JST-Commercial/B2B-XH-ALFSN?qs=cdbOS8ANM9DdcSn9qRmfCw%3D%3D) | est. 0.10 |
| mating, J3, J4 | 2 | XH housing, 3-pos | n/a | JST XHP-3 | n/a | Mates B3B-XH-A | — | est. 0.15 |
| mating, J5 | 1 | XH housing, 6-pos | n/a | JST XHP-6 | n/a | Mates B6B-XH-A | — | est. 0.15 |
| mating, J8 | 1 | XH housing, 4-pos | n/a | JST XHP-4 | n/a | Mates B4B-XH-A | — | est. 0.15 |
| mating, J9, J11-J14 | 5 | XH housing, 2-pos | n/a | JST XHP-2 | n/a | Mates B2B-XH-A | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/XHP-2/555485) | est. 0.10 |
| mating, all XH | 26 | Crimp contacts | n/a | JST SXH-001T-P0.6 | n/a | 22-28 AWG; 26 = 3+3+6+4+5x2 pins | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/SXH-001T-P0-6/527371) | est. 0.10 |
| J1 | 1 | Battery pigtail wire pads | `Battery T-plug pigtail 12AWG` | none (pads only; 12 AWG T-plug pigtail is the owner's) | `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm` (placeholder) | See J1 note | — | — |
| TP1-TP3 | 3 | Test points | `+5V_CPU`, `+5V_SENS`, `+3V3_SENS` | none (bare pads) | 1.5 mm pad | | — | — |
| H1-H4 | 4 | M3 mounting holes | `MountingHole_M3` | none; M3 screws/standoffs optional | M3 hole | | — | — |

## Subtotal (one board, estimated)

| Group | USD |
| --- | --- |
| F1 fuse 0.40 + holder 3.00 | 3.40 |
| U1 (in hand) | 39.95 |
| U2 (proposed) | 32.95 |
| D1, C1-C8, FB1, U3, R1-R3, D2-D4 | 3.82 |
| J6/J7 | 1.60 |
| XH: 9 headers (4 x 0.15 + 5 x 0.10 = 1.10) + 9 housings (1.10) + 26 crimps (2.60) | 4.80 |
| **Total** | **about 86.5** |

Excluding U1 (already owned): about 46.6. (Check: 3.40 + 39.95 + 32.95 + 3.82 + 1.60 + 4.80 = 86.52; minus 39.95 = 46.57.) PCB fabrication is not included; list it separately as est. (quote from the chosen fab). Buy spare fuses and a few spare passives.

## Out of stock / backorder (as checked)

- Samsung CL21A106KAYNNNE (10 uF): out of stock; replaced by YAGEO CC0805KRX5R8BB106.
- Murata GRM21BR61A226ME44L: DigiKey backorder; substitute YAGEO CC0805MKX5R6BB226 (no link verified).
- Samsung CL21B105KBFNNNE: DigiKey backorder; in stock at Mouser.

## Fuse notes (F1)

- **Series:** Littelfuse ATO 257 standard blade (32 VDC, 1000 A interrupting at 32 VDC; ISO 8820-3 / SAE J1284), in a Littelfuse FLR 178.6165.0001 holder (22.5 A continuous / 30 A max per the FLR datasheet; 32 V fuse system). Fast-acting standard characteristic, not time-delay. Proposed 0257015.PXPV (15 A); 10 A alternative 0257010.PXPV. 0257015.L is obsolete; DigiKey lists 0287015.PXCN (ATOF) as direct substitute. Melting I2t of the 15 A part is about 340 A2s (Littelfuse catalog). No confirmed retailer links; prices (fuse est. 0.40, holder est. 3.00) are unverified.
- **No dedicated slow-blow needed.** Plug-in inrush is C1 (470 uF) plus MLCCs charging: about V2 C / (2R) = 8.4^2 x 470 uF / (2 x 0.05 ohm) = 0.3 A2s, where R = 50 mohm is an **assumed** loop resistance; even at 10 mohm: about 1.7 A2s, about 200x margin below the 15 A fuse's 340 A2s melting I2t. The modules soft-start. Slow-blow parts are for motor inrush, and the motor/ESC is powered off-board.
- **Rating:** worst-case board load is about 7.3 A at 6.4 V and about 7.8 A at the 6.0 V cutoff (U1: 5.1 V x 5 A / (0.9 x 6.0 V) = 4.7 A, plus U2 about 3.1 A). On a 10 A fuse that is 73-78% of rating, at or over the ~75% continuous rule of thumb; a 15 A fuse gives 49-52%. Recommended 15 A, 10 A as the alternative; owner decides.
- **Copper must be sized for the fuse:** VBAT_RAW, VBAT and GND copper must carry F1's rating (a blade fuse holds 110% indefinitely: about 16.5 A for 15 A, 11 A for 10 A), not just the 7.8 A load. Widths: `fab_handoff.md`. If the copper is reduced, pick 10 A.
- **Pending:** F1 rating (10 vs 15 A), owner decides.

## J1 footprint note

KiCad's `Connector_Wire` library (checked locally) has `SolderWire-*` footprints up to 2.5 sqmm only (no 4 sqmm variant): the one in the schematic, `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm`, has a 3.0 mm drill and a 4.4 mm pad ("D2.4mm" is the conductor diameter, not the drill). 12 AWG stranded tinned wire (about 2.05 mm) fits the 3.0 mm hole; the concern is the thin 0.7 mm annular ring at F1's current. Proposed: keep the 3.0 mm drill, enlarge the pad OD to at least 5 mm (custom copy of the footprint), thermal reliefs off. Verify against the actual wire.
