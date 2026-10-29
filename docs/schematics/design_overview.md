# Power distribution board: design overview (Rev A draft)

One-page summary for the design meeting. Schematic: `rc_power_board.kicad_sch` / `.pdf` (KiCad 10). Full build guide and background: `power_board_plan.md`.

**Architecture:** 2S LiPo (6.0–8.4 V) → J1 → F1 → `VBAT` bus, then three branches:
- compute 5 V: U1 → `+5V_CPU` → Pi 5 + ESP32
- sensor 5 V: U2 → `+5V_SENS`
- sensor 3.3 V: U3, an LDO fed from `+5V_SENS` → `+3V3_SENS`

All branches share one common GND. The ESC and motor are powered off-board.

## Power entry (sheet region A)

- **ESC power is off-board.** The battery feeds the ESC on its own 12 AWG leads (up to 20 A motor current; the THW-1060 is rated 60 A continuous). Motor current never crosses the PCB, so its copper and fuse are sized for board loads only: about 7.3 A worst case.
- **J1 + F1.** The battery T-plug pigtail (12 AWG) solders to J1's pads. F1 is the main fuse for the board branch, about 10 A (rating TBD).
- **D1 + C1 on `VBAT`.** D1 is a unidirectional TVS (standoff ≥ 9 V) that clamps hot-plug and motor transients. C1 is the bulk reservoir that rides through wiring inductance at the regulator inputs.

## ESC signals and servo (B)

- **J3 ESC receiver lead.** Only the ESC's 3-wire lead lands on the board: throttle PWM in, 6 V / 3 A BEC out.
- **Servo on the BEC (`+6V_BEC`).** The DS3225MG stalls at 2.3 A at 6.8 V, which fits the 3 A BEC. `+6V_BEC` is never joined to a 5 V rail.
- **J5 to the ESP32.** Pins: 1 `U1_PG`, 2 `THROTTLE_PWM` (GPIO5), 3 `STEER_PWM` (GPIO4), 4 GND. All signals are 3.3 V logic.

## Compute 5 V (C)

- **U1, Pololu D36V50F5, on a dedicated rail.** It feeds only the Pi 5 and the ESP32, so a sensor fault can't brown out compute. Rated 5.0 V ± 4 %, 5.5 A typical, with input reverse protection to 40 V, soft-start and current limiting. All 12 pins are drawn, and the power pins are used in pairs because each header pin is rated 3 A.
- **PG to the ESP32.** Open-drain power-good, read on the ESP32 with its internal pull-up, so firmware can flag a compute-rail fault.
- **EN is left unconnected.** The module's internal pull-up keeps it always on. ESP32 control is archived: EN pulls up to VIN (up to 8.4 V), and U1 powers the ESP32 itself.
- **VRP is unused.** Feeding the sensor buck from VRP would push about 7.3 A through U1's VIN pin pair, which is rated 6 A.
- **J6/J7 USB-C pigtails.** The Pi 5 and the ESP32 take power through their own USB-C inputs, so their input protection stays in the path. The pigtails are 20 AWG; at ≤ 15 cm they drop about 0.05 V at 5 A.

## Sensor 5 V (D)

- **U2, 5 V buck rated ≥ 4 A, behind fuse F4.** Feeds the LIDAR-Lite v4, a camera USB hub and a spare header, and also feeds the 3.3 V LDO. It is isolated from compute, so a sensor short trips F4, not the Pi.

## Sensor 3.3 V (E)

- **U3, AP2112K-3.3 LDO fed from `+5V_SENS`.** Gives low-noise 3.3 V for the IMU and shaft encoder. The budget is 0.3 A, so the LDO dissipates about 0.5 W, and cascading it behind U2 costs almost nothing at that load.
- **FB1 + C6 LC filter (optional).** Attenuates U2's switching ripple before the LDO. Keep or DNP on review.

## Across the board

- **Decoupling.** C2/C4 handle each buck's pulsed input current; C3/C5 handle output ripple and load steps. C7/C8 are required by the LDO datasheet.
- **Indicators and probes.** An R + LED on each rail (about 2 mA) plus test points TP1–TP3 for bring-up.
- **Net classes.** HighCurrent (`VBAT`, GND), Power5A (`+5V_CPU`, `VIN_CPU`), Power3A (`+5V_SENS`, `VIN_SENS`, `+6V_BEC`). Widths come from the IPC-2221/2152 table in the plan.
- **PWR_FLAG.** ERC-only markers with no physical part; they tell ERC where power enters a net.

## Power budget (worst case)

| Rail | Loads | Budget |
| --- | --- | --- |
| `+5V_CPU` | Pi 5 + ESP32 | 5.5 A |
| `+5V_SENS` | LIDAR, camera hub, spare, LDO input | 3.3 A |
| `+3V3_SENS` | IMU, encoder, spare | 0.3 A |
| `VBAT` on the board | U1 + U2 inputs at 6.4 V | about 7.3 A |
| ESC (off-board) | motor + servo BEC | up to 20 A |

## Decisions wanted

1. Fuse ratings and types for F1, F3 and F4.
2. Resize HighCurrent for about 8 A, now that the ESC is off-board?
3. U1: 5.0 V vs the Pi 5's preferred 5.1 V, and its dropout at 5.5 A with the battery near 6.0 V.
4. Keep the FB1/C6 filter, or is the LDO's ripple rejection enough?
5. Board-level reverse-polarity protection for the U2 branch; TVS part selection.
6. J1 pad size for 12 AWG; module footprints for U1 and U2.
7. EN control (archived): which option, if any, to revisit later.
