# Power distribution board: design overview (Rev A draft)

Netlist: 40 parts, 21 nets. Schematic: `rc_power_board.kicad_sch` / `.pdf` (KiCad 10 project). Background: `power_board_plan.md`. Parts: `bom.md`. Milling/layout: `fab_handoff.md`.

**Architecture:** 2S LiPo (6.0–8.4 V) → J1 → F1 → `VBAT` (U1, U2 inputs sit on it) → three branches: U1 → `+5V_CPU` (Pi 5 + ESP32); U2 → `+5V_SENS`; U3 LDO from `+5V_SENS` → `+3V3_SENS`. One common GND. ESC and motor are powered off-board.

## Power entry (A)

- **ESC off-board.** Battery feeds ESC on its own 12 AWG leads (up to 20 A; THW-1060 rated 60 A continuous). Motor current never crosses the PCB, so fuse and copper are sized for board loads (about 8.4 A worst case at 6.4 V, ≈ 9.0 A at the 6.0 V cutoff, ≈ 9.3 A briefly at Mapper startup).
- **J1 + F1.** 12 AWG T-plug pigtail solders to J1 pads. F1 is the single main fuse for the whole board: ATO/ATC blade in a Littelfuse FLR 178.6165 holder (22.5 A continuous, 32 V fuse system), 15 A (0257015.PXPV proposed; 10 A would run at 84–93 % of rating). No branch fuses. A sensor short opens F1 and drops compute.
- **Fuse type.** Standard ATO 257 suffices; no slow-blow (inrush ≈ 0.3–1.7 A²s vs ≈ 340 A²s melting I²t at 15 A).
- **D1 + C1.** D1: unidirectional TVS (≥ 9 V standoff); C1: bulk.

## ESC signals and servo (B)

- **Connector convention.** JST-XH (2.5 mm) for sensors and low-power parts: single Dupont jumper sockets push onto the XH pins for breadboard debugging, and the parts are lab stock. Pin order convention + crimp table: `fab_handoff.md`. Exceptions: J1 (T-plug pigtail pads) and J6/J7 (USB-C pigtail screw terminals; J6 carries up to 5 A, above XH's 3 A/pin); JST VH/XH options in `fab_handoff.md`.
- **J3 (3-pin XH).** ESC receiver lead only: throttle PWM in, 6 V / 3 A BEC out.
- **J4 (3-pin XH), servo on `+6V_BEC`.** DS3225MG stalls at 2.3 A at 6.8 V, at the XH limit with 22 AWG wire (BEC pin up to 3 A = 100 %). `+6V_BEC` never joins a 5 V rail.
- **J5 (6-pin XH) to ESP32.** 1 `U1_PG` (GPIO TBD), 2 `THROTTLE_PWM` (GPIO5), 3 `STEER_PWM` (GPIO4), 4 `I2C_SDA` (GPIO8), 5 `I2C_SCL` (GPIO9), 6 GND. 3.3 V logic.

## Compute 5 V (C)

- **U1, Pololu D36V50F5, dedicated rail.** Feeds only Pi 5 and ESP32. 5.0 V, 5.5 A typical, reverse protection, soft-start, current limit.
- **PG.** Open-drain, read by ESP32 (internal pull-up).
- **EN unconnected until rev 2.** Module pull-up keeps it on. ESP32 control archived: EN pulls up to VIN (up to 8.4 V) and U1 powers the ESP32.
- **VRP unused.** Feeding the sensor buck from VRP would push ≈ 8.4 A through U1's VIN pair (rated 6 A).
- **J6/J7 USB-C pigtails.** Pi 5 and ESP32 powered via their own USB-C inputs, keeping input protection in path. 20 AWG, ≤ 15 cm.

## Sensor 5 V (D)

- **U2, 5 V buck ≥ 6 A** (proposal Pololu D24V60F5, not bought; dropout near 6.0 V TBD, `bom.md`). Feeds Mapper, LIDAR-Lite v4, camera hub, LDO.
- **J11 Slamtec Mapper M2M1.** Harness: XH to 22 AWG 3 A USB-A pigtail (pin 1 `+5V_SENS` red, 2 GND black); never from Pi USB or the pack. 0.75 A typ, 1.3 A max, 1.4–1.6 A startup; ripple ≤ 50 mV. C9 (≥ 100 µF low-ESR, TBD) sits right at J11.
- **J8 Garmin LIDAR-Lite v4, one 4-pin XH header.** Pins match Garmin 1–4: 1 `+5V_SENS` (red; 4.75–5.25 V, 85 mA acquiring), 2 GND (black), 3 `I2C_SDA` (white), 4 `I2C_SCL` (green); address 0x62. Internal 13 kΩ pull-ups to 3.3 V: no external pull-ups. One keyed header (not 2×2-pin) so it can't be cross-plugged; harness is straight-through.

## Sensor 3.3 V (E)

- **U3, AP2112K-3.3 LDO from `+5V_SENS`.** 3.3 V for IMU and shaft encoder; 0.3 A, ≈ 0.5 W.
- **FB1 + C6 LC filter (optional).** Attenuates U2 ripple before the LDO.

## Across the board

- **Decoupling/probes.** C2/C4 in, C3/C5 out, C7/C8 per LDO datasheet; R + LED per rail; TP1–TP3.
- **Net classes.** HighCurrent (`VBAT`, GND), Power5A (`+5V_CPU`, `+5V_SENS`), Power3A (`+6V_BEC`), Default 0.5 mm. IPC-2221 widths: `fab_handoff.md`.
- **Rev A is a CNC-milled prototype** (Makera Carvera, in-house); details and provisional values in `fab_handoff.md`.
  - Stock: 2 oz double-sided FR-4, 3" x 6"; no plated holes, vias are LPKF EasyContac 0.8 mm rivets from lab stock (drill 1.1 mm, pad 2.0 mm; 1.2 mm optional for high current; 1.1 mm bit availability TBD).
  - DRC clearance 0.4 mm, min track 0.5 mm; THT connector pins routed on the bottom.

## Power budget (worst case)

| Rail | Loads | Budget |
| --- | --- | --- |
| `+5V_CPU` | Pi 5 + ESP32 | 5.5 A |
| `+5V_SENS` | Mapper, LIDAR, camera hub, LDO input | 4.6 A (4.9 A startup) |
| `+3V3_SENS` | IMU, encoder, spare | 0.3 A |
| `VBAT` on the board | U1 + U2 inputs at 6.4 V | about 8.4 A (9.0 A at 6.0 V) |
| ESC (off-board) | motor + servo BEC | up to 20 A |

## Decisions wanted

1. Size VBAT/GND copper for F1's 15 A (≈ 16.5 A), not the 9.0 A load.
2. U1: 5.0 V vs the Pi 5's preferred 5.1 V; dropout at 5.5 A near 6.0 V.
3. Keep the FB1/C6 filter, or rely on LDO ripple rejection?
4. Reverse-polarity protection: P-FET proposal (Q1 + R4 between F1 and VBAT) is in the PR, not on the board; U1 has its own (to −40 V); proposed U2's is TBD; C1/D1 are exposed.
5. J1 pad size for 12 AWG; module footprints for U1 and U2.
6. I2C pull-ups: only the Garmin's internal 13 kΩ pulls up the bus; consider two DNP 0805 4.7–10 kΩ footprints to `+3V3_SENS` for a future IMU. Not drawn.
7. U3 footprint vs V-bit clearance: AP2112K SOT-23-5 pad gap about 0.35 mm < 0.4 mm DRC. Custom narrower pads (gap about 0.45 mm), mill with the 60°/0.1 mm bit, or a local DRC exception.
