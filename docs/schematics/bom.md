# Power board BOM (Rev A draft, schematic parts only)

Companion to `design_overview.md`; layout and CNC-milling steps are in `fab_handoff.md`. Rev A is milled in-house (Makera Carvera), so there is no PCB fab-house cost. Schematic values stay as drawn (TBD where unconfirmed); MPNs here are proposals. Every MPN below is **proposed**, pending owner approval. Reference list: 40 parts, per the regenerated netlist (21 nets). Connector convention: JST-XH (2.5 mm) for sensors and low-power parts; exceptions J1, J6, J7 (JST options in `fab_handoff.md`). J10 is intentionally absent (radar removed).

Prices/stock as checked 2026-10-30; confirm before ordering.

| Ref(s) | Qty | Function | Schematic value | Proposed MPN | Footprint | Key spec checked | Link | Est. unit cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | 1 | Single main fuse, all board loads | `TBD ATO/ATC blade 15A` | Littelfuse 0257015.PXPV (ATO 257, 15 A, 32 V) | via F1 holder | ATO/ATC 257: 32 VDC, 1000 A interrupting at 32 VDC, ISO 8820-3 / SAE J1284; melting I2t about 340 A2s (15 A, Littelfuse catalog); see fuse notes. 0257015.L is obsolete; DigiKey lists 0287015.PXCN (ATOF) as direct substitute | — | est. 0.40 (buy spares) |
| F1 holder | 1 | PCB holder for F1 | n/a (part of F1 symbol) | Littelfuse FLR 178.6165.0001 | `Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165` | Takes standard ATO/ATC blade fuses; 22.5 A continuous / 30 A max per the Littelfuse FLR datasheet; 32 V fuse system; either exceeds F1 | — | est. 3.00 (unverified) |
| U1 | 1 | Compute 5 V buck (Pi 5 + ESP32) | `Pololu D36V50F5 buck (req 5.1V >=6A TBD)` | Pololu D36V50F5 (in hand) | `PinHeader_2x06_P2.54mm_Vertical` | 5.0 V, 5.5 A typ; reverse protection to 40 V; 3 A per header pin | [Pololu 4091](https://www.pololu.com/product/4091) | 39.95 (in hand) |
| U2 | 1 | Sensor 5 V buck | `5V buck >=6A module, TBD` | Pololu D24V60F5 (5 V, 6 A; proposed; not bought; replaces the D24V50F5 proposal, which is too small for the Mapper load) | TBD: needs Pololu dimension drawing (none in schematic yet) | 5 V, 6 A; +5V_SENS needs 4.6 A running, 4.9 A at Mapper startup. Input range, protections (reverse protection TBD) and dropout: **TBD, check the Pololu product page and dropout curve** near the 6.0 V battery cutoff (flag, verify at load). Pin count and current per pin from the D24V60F5 drawing (+5V_SENS 4.9 A vs about 3 A per 0.1" header pin); update the REG_MODULE symbol/footprint if it has multiple VOUT/GND pins | [Pololu 2865](https://www.pololu.com/product/2865) | TBD (placeholder 32.95 = D24V50F5 price; update) |
| D1 | 1 | TVS on VBAT | `TVS >=9V TBD` | Littelfuse SMBJ10A | SMB | Unidirectional; 10 V standoff, 11.1 V min breakdown, 17.0 V max clamp at 35.3 A; 600 W | [DigiKey](https://www.digikey.com/en/products/detail/littelfuse-inc/SMBJ10A/285966) | 0.43 |
| C1 | 1 | VBAT bulk | `TBD uF >=16V` | Panasonic EEU-FR1E471 | `CP_Radial_D10.0mm_P5.00mm` | 470 uF, 25 V, 10 mm dia, 5 mm pitch, 105 C; footprint matches | [DigiKey](https://www.digikey.com/en/products/detail/panasonic-industry/EEU-FR1E471/2433553) | est. 0.70 |
| C9 | 1 | Bulk cap at J11 (Mapper startup surge, ripple) | `TBD >=100uF low-ESR >=10V` | TBD: >=100 uF, >=10 V low-ESR radial electrolytic or polymer; MPN TBD | `CP_Radial_D8.0mm_P3.50mm` (exists in KiCad; confirm vs the chosen part) | Mapper ripple limit 50 mV max (20 mV typ); startup 1.4-1.6 A for a few seconds. Place at J11 | — | est. 0.50 |
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
| J9, J11, J12, J13, J14 | 5 | 2-pos sensor / spare connectors | J9 `Camera USB hub`; J11 `Slamtec Mapper (5V)`; J12 `IMU`; J13 `Shaft encoder`; J14 `Spare 3.3V` | JST B2B-XH-A(LF)(SN) | 2-pos, 2.5 mm (XH) | 3 A per pin | [Mouser](https://www.mouser.com/ProductDetail/JST-Commercial/B2B-XH-ALFSN?qs=cdbOS8ANM9DdcSn9qRmfCw%3D%3D) | est. 0.10 |
| mating, J3, J4 | 2 | XH housing, 3-pos | n/a | JST XHP-3 | n/a | Mates B3B-XH-A | — | est. 0.15 |
| mating, J5 | 1 | XH housing, 6-pos | n/a | JST XHP-6 | n/a | Mates B6B-XH-A | — | est. 0.15 |
| mating, J8 | 1 | XH housing, 4-pos | n/a | JST XHP-4 | n/a | Mates B4B-XH-A | — | est. 0.15 |
| mating, J9, J11-J14 | 5 | XH housing, 2-pos | n/a | JST XHP-2 | n/a | Mates B2B-XH-A | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/XHP-2/555485) | est. 0.10 |
| mating, J11 (Mapper harness) | 1 | Slamtec Mapper M2M1 power pigtail | n/a | 22 AWG 3 A USB-A male 2-wire pigtail (XHP-2 on the board end); lab/owner stock? **TBD** | n/a | J11 pin 1 +5V_SENS to red/VBUS, pin 2 GND to black. Non-board item; not in totals. Never power the Mapper from Pi USB or straight from the pack | — | not in totals |
| mating, all XH | 26 | Crimp contacts | n/a | JST SXH-001T-P0.6 | n/a | 22-28 AWG; 26 = 3+3+6+4+5x2 pins | [DigiKey](https://www.digikey.com/en/products/detail/jst-sales-america-inc/SXH-001T-P0-6/527371) | est. 0.10 |
| Stock | 1 | Copper-clad board blank | n/a | Kepro P22-365G FR-4, 2 oz, double-sided, 3" x 6" x 0.062" | n/a | 76.2 x 152.4 x 1.57 mm; lab stock (5 pcs, dated 1997, unsensitized: scrub oxide before milling) | — | 0.00 (lab stock) |
| Rivets | about 20 | PCB through-hole rivets (vias) | n/a | LPKF EasyContac kit (0.6/0.8/1.0/1.2 mm) + setting tool, lab stock, $0; use 0.8 mm (≈20) | n/a | 0.8 mm: hole 1.1 mm, collar 1.6 mm; max board 1.6 mm; solder both sides; 1.2 mm / 1.0 mm optional, see `fab_handoff.md` | — | 0.00 (lab stock) |
| Dowel pins | 2-3 | Flip registration | n/a | from Makera PCB Fabrication Pack (diameter TBD) | n/a | lab stock | — | 0.00 (lab stock) |
| V-bits / drill bits | n/a | Isolation milling, drilling | n/a | Makera pack: 2x 60° 0.1 mm, 2x 30° 0.2 mm V-bits; 20x milling/drilling bits (diameters TBD) | n/a | lab stock | — | 0.00 (lab stock) |
| J6 option | 1 | Pi 5 pigtail header (replaces Phoenix 1715721 if chosen) | n/a | JST B2P-VH(LF)(SN) + VHR-2N + 2x SVH-21T-P1.1 | `JST_VH_B2P-VH_1x02_P3.96mm_Vertical` | 3.96 mm; rating per JST VH datasheet, confirm; SVH-21T-P1.1 takes 18-22 AWG (confirm) | — | TBD; not in totals |
| J7 option | 1 | ESP32 pigtail header (replaces Phoenix if chosen) | n/a | JST B2B-XH-A(LF)(SN) + XHP-2 + SXH-001T-P0.6 | `JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical` | 0.5 A ok; 20 AWG pigtail must be trimmed/spliced to 22 AWG | see rows above | not in totals |
| J1 | 1 | Battery pigtail wire pads | `Battery T-plug pigtail 12AWG` | none (pads only; 12 AWG T-plug pigtail is the owner's) | `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm` (placeholder) | See J1 note | — | — |
| TP1-TP3 | 3 | Test points | `+5V_CPU`, `+5V_SENS`, `+3V3_SENS` | none (bare pads) | 1.5 mm pad | | — | — |
| H1-H4 | 4 | M3 mounting holes | `MountingHole_M3` | none; M3 screws/standoffs optional | M3 hole | | — | — |

## Subtotal (one board, estimated)

| Group | USD |
| --- | --- |
| F1 fuse 0.40 + holder 3.00 | 3.40 |
| U1 (in hand) | 39.95 |
| U2 (proposed D24V60F5; price TBD, placeholder = D24V50F5 price) | 32.95 |
| D1, C1-C9, FB1, U3, R1-R3, D2-D4 | 4.32 |
| J6/J7 | 1.60 |
| XH: 9 headers (4 x 0.15 + 5 x 0.10 = 1.10) + 9 housings (1.10) + 26 crimps (2.60) | 4.80 |
| Stock, rivets (EasyContac kit), dowels, bits: lab stock | 0.00 |
| **Total** | **about 87.0** |

Excluding U1 (already owned): about 47.1. (Check: 3.40 + 39.95 + 32.95 + 4.32 + 1.60 + 4.80 + 0.00 = 87.02; minus 39.95 = 47.07.) The U2 figure is a placeholder until the D24V60F5 price is checked. No PCB fab cost: rev A is milled in-house. J6/J7 JST options are not included. Buy spare fuses and a few spare passives.

## Out of stock / backorder (as checked)

- Samsung CL21A106KAYNNNE (10 uF): out of stock; replaced by YAGEO CC0805KRX5R8BB106.
- Murata GRM21BR61A226ME44L: DigiKey backorder; substitute YAGEO CC0805MKX5R6BB226 (no link verified).
- Samsung CL21B105KBFNNNE: DigiKey backorder; in stock at Mouser.

## Fuse notes (F1)

- **Series:** Littelfuse ATO 257 standard blade (32 VDC, 1000 A interrupting at 32 VDC; ISO 8820-3 / SAE J1284), in a Littelfuse FLR 178.6165.0001 holder (22.5 A continuous / 30 A max per the FLR datasheet; 32 V fuse system). Fast-acting standard characteristic, not time-delay. Proposed 0257015.PXPV (15 A); the 10 A part (0257010.PXPV) is rejected by the load (see Rating). 0257015.L is obsolete; DigiKey lists 0287015.PXCN (ATOF) as direct substitute. Melting I2t of the 15 A part is about 340 A2s (Littelfuse catalog). No confirmed retailer links; prices (fuse est. 0.40, holder est. 3.00) are unverified.
- **No dedicated slow-blow needed.** Plug-in inrush is C1 (470 uF) plus MLCCs charging: about V2 C / (2R) = 8.4^2 x 470 uF / (2 x 0.05 ohm) = 0.3 A2s, where R = 50 mohm is an **assumed** loop resistance; even at 10 mohm: about 1.7 A2s, about 200x margin below the 15 A fuse's 340 A2s melting I2t. The modules soft-start. Slow-blow parts are for motor inrush, and the motor/ESC is powered off-board.
- **Rating:** worst-case board load (with the Slamtec Mapper on J11) is about 8.4 A at 6.4 V and about 9.0 A at the 6.0 V cutoff, about 9.3 A briefly at Mapper startup (U1: 5.1 V x 5 A / (0.9 x 6.0 V) = 4.7 A, plus U2: 5 V x 4.6 A / (0.9 x 6.0 V) = 4.3 A). On a 10 A fuse that is 84-93% of rating, well over the ~75% continuous rule of thumb; a 15 A fuse gives 56-62%. **Decided: 15 A** (previous load without the Mapper: 7.3 / 7.8 A).
- **Copper must be sized for the fuse:** VBAT_RAW, VBAT and GND copper must carry F1's rating (a blade fuse holds 110% indefinitely: about 16.5 A for 15 A, 11 A for 10 A), not just the 9.0 A load. Widths: `fab_handoff.md`.
- **Resolved:** F1 = 15 A (set by the load; copper stays sized for 16.5 A).

## J1 footprint note

KiCad's `Connector_Wire` library (checked locally) has `SolderWire-*` footprints up to 2.5 sqmm only (no 4 sqmm variant): the one in the schematic, `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm`, has a 3.0 mm drill and a 4.4 mm pad ("D2.4mm" is the conductor diameter, not the drill). 12 AWG stranded tinned wire (about 2.05 mm) fits the 3.0 mm hole; the concern is the thin 0.7 mm annular ring at F1's current. Proposed: keep the 3.0 mm drill, enlarge the pad OD to at least 5 mm (custom copy of the footprint), thermal reliefs off. Verify against the actual wire.
