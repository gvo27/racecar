# Power distribution board: design overview (Rev A draft)

Netlist: 39 parts, 21 nets. Schematic: `rc_power_board.kicad_sch` / `.pdf` (KiCad 10 project; committed file is KiCad 7 generator output until re-saved). Background: `power_board_plan.md`. Parts: `bom.md`. Fab: `fab_handoff.md`.

**Architecture:** 2S LiPo (6.0–8.4 V) → J1 → F1 → `VBAT` (U1, U2 inputs sit on it) → three branches: U1 → `+5V_CPU` (Pi 5 + ESP32); U2 → `+5V_SENS`; U3 LDO from `+5V_SENS` → `+3V3_SENS`. One common GND. ESC and motor are powered off-board.

## Power entry (A)

- **ESC off-board.** Battery feeds ESC on its own 12 AWG leads (up to 20 A; THW-1060 rated 60 A continuous). Motor current never crosses the PCB, so fuse and copper are sized for board loads (about 7.3 A worst case, ≈ 7.8 A at 6.0 V cutoff).
- **J1 + F1.** 12 AWG T-plug pigtail solders to J1 pads. F1 is the single main fuse for the whole board: ATO/ATC blade in a Littelfuse FLR 178.6165 holder (22.5 A continuous, 32 V fuse system), 10 or 15 A (0257015.PXPV 15 A proposed). No branch fuses. Trade-off: a sensor short opens F1 and drops compute.
- **Fuse type.** Standard ATO 257 (ISO 8820-3, 32 VDC, 1000 A) suffices; no slow-blow needed (inrush ≈ 0.3–1.7 A²s vs ≈ 340 A²s melting I²t at 15 A; motor off-board).
- **D1 + C1.** D1: unidirectional TVS (standoff ≥ 9 V) for hot-plug/motor transients. C1: bulk reservoir.

## ESC signals and servo (B)

- **Connector convention.** JST-XH (2.5 mm) for sensors and low-power parts: single Dupont jumper sockets push onto the XH pins for breadboard debugging, and the parts are lab stock. Pin order convention + crimp table: `fab_handoff.md`. Exceptions: J1 (T-plug pigtail pads) and J6/J7 (USB-C pigtail screw terminals; J6 carries up to 5 A, above XH's 3 A/pin).
- **J3 (3-pin XH).** ESC receiver lead only: throttle PWM in, 6 V / 3 A BEC out.
- **J4 (3-pin XH), servo on `+6V_BEC`.** DS3225MG stalls at 2.3 A at 6.8 V, at the XH limit with 22 AWG wire (BEC pin up to 3 A = 100 %). `+6V_BEC` never joins a 5 V rail.
- **J5 (6-pin XH) to ESP32.** 1 `U1_PG` (GPIO TBD), 2 `THROTTLE_PWM` (GPIO5), 3 `STEER_PWM` (GPIO4), 4 `I2C_SDA` (GPIO8), 5 `I2C_SCL` (GPIO9), 6 GND. 3.3 V logic.

## Compute 5 V (C)

- **U1, Pololu D36V50F5, dedicated rail.** Feeds only Pi 5 and ESP32; sensor overload is limited by U2, not compute brownout. 5.0 V ± 4 %, 5.5 A typical, reverse protection to 40 V, soft-start, current limit.
- **PG.** Open-drain, read by ESP32 (internal pull-up).
- **EN unconnected until rev 2.** Module pull-up keeps it on. ESP32 control archived: EN pulls up to VIN (up to 8.4 V) and U1 powers the ESP32.
- **VRP unused.** Feeding the sensor buck from VRP would push ≈ 7.3 A through U1's VIN pair (rated 6 A).
- **J6/J7 USB-C pigtails.** Pi 5 and ESP32 powered via their own USB-C inputs, keeping input protection in path. 20 AWG, ≤ 15 cm: ≈ 0.05 V drop at 5 A.

## Sensor 5 V (D)

- **U2, 5 V buck ≥ 4 A** (module proposed in `bom.md`, not yet bought). Feeds LIDAR-Lite v4, camera hub, spare header, LDO.
- **J8 Garmin LIDAR-Lite v4, one 4-pin XH header.** Pins match Garmin 1–4: 1 `+5V_SENS` (red; 4.75–5.25 V, 85 mA acquiring), 2 GND (black), 3 `I2C_SDA` (white), 4 `I2C_SCL` (green); address 0x62. Sensor has internal 13 kΩ pull-ups to 3.3 V: no external pull-ups or level shifter. Why one header, not 2×2-pin: keyed, so it can't be half- or cross-plugged (two 2-pin headers could put 5 V on SDA); pin numbers match Garmin, so the harness is straight-through; GND beside I2C gives a short return; one crimp job. Source: branch `rangefinder` (5b409d0, not merged).

## Sensor 3.3 V (E)

- **U3, AP2112K-3.3 LDO from `+5V_SENS`.** 3.3 V for IMU and shaft encoder; 0.3 A, ≈ 0.5 W.
- **FB1 + C6 LC filter (optional).** Attenuates U2 ripple before the LDO. Keep or DNP on review.

## Across the board

- **Decoupling/probes.** C2/C4 buck inputs, C3/C5 buck outputs, C7/C8 per LDO datasheet; R + LED per rail (≈ 2 mA); TP1–TP3.
- **Net classes.** HighCurrent (`VBAT`, GND), Power5A (`+5V_CPU`), Power3A (`+5V_SENS`, `+6V_BEC`). Trace widths: IPC-2221 table in `fab_handoff.md`; 2 oz copper recommended.

## Power budget (worst case)

| Rail | Loads | Budget |
| --- | --- | --- |
| `+5V_CPU` | Pi 5 + ESP32 | 5.5 A |
| `+5V_SENS` | LIDAR, camera hub, spare, LDO input | 3.3 A |
| `+3V3_SENS` | IMU, encoder, spare | 0.3 A |
| `VBAT` on the board | U1 + U2 inputs at 6.4 V | about 7.3 A |
| ESC (off-board) | motor + servo BEC | up to 20 A |

## Decisions wanted

1. F1 rating, 10 vs 15 A (ATO/ATC blade assumed).
2. Size VBAT/GND copper for F1's rating (≈ 16.5 A for 15 A, 11 A for 10 A), not the 7.3 A load, or pick 10 A if copper is reduced.
3. U1: 5.0 V vs the Pi 5's preferred 5.1 V, and its dropout at 5.5 A with the battery near 6.0 V.
4. Keep the FB1/C6 filter, or is the LDO's ripple rejection enough?
5. Reverse-polarity protection: P-FET proposal (Q1 + R4 between F1 and VBAT) is in the PR, not on the board; U1 and proposed U2 have their own, C1/D1 are exposed. Also TVS part selection.
6. J1 pad size for 12 AWG; module footprints for U1 and U2 (U2 selection: `bom.md`).
7. I2C pull-ups: only the Garmin's internal 13 kΩ pulls up the bus; consider two DNP 0805 4.7–10 kΩ footprints on I2C_SDA/I2C_SCL to `+3V3_SENS` (the sensor rail; ESP32 powers nothing) for a future IMU (4.7 k ∥ 13 k ≈ 3.5 kΩ, fine at 400 kHz). Not drawn.
