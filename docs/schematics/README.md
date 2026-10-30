# Power distribution board (baseline schematic)

Draft KiCad project for the car's power board. A 2S LiPo comes in; the board puts out `VBAT`, `+5V_CPU`, `+5V_SENS` and `+3V3_SENS` on a common `GND`, and routes `+6V_BEC` from the ESC to the servo. The ESC's own battery power is off-board. This is a **review draft**: every value marked `TBD` is unconfirmed (project rule: no unconfirmed parameters).

| File | What it is |
| --- | --- |
| `design_overview.md` | The design meeting summary: one short entry per feature, the power budget and the decisions wanted. |
| `bom.md` | Standalone BOM for the schematic parts: proposed MPNs, links, key specs, estimated cost, fuse notes. |
| `fab_handoff.md` | Layout and fab checklist for KiCad 10: net-class widths, IPC-2221 table, pours, export, sign-off, open items. |
| `power_board_plan.md` | The build guide and background: rails, power budget, trace widths, a step-by-step KiCad guide and open questions. Exported from the live doc linked at its top. |
| `power_architecture.png` | Block diagram used by the plan. |
| `rc_power_board.kicad_pro` / `.kicad_sch` | KiCad project and the one-sheet A3 schematic (regions A to E plus notes). |
| `rc_power.kicad_sym` + `sym-lib-table` | Project symbol library: `D36V50F5` (all 12 module pins), `REG_MODULE` (generic VIN/GND/VOUT/EN, used by U2) and one power symbol per rail. |
| `rc_power_board.pdf` | Plot of the sheet, for review without KiCad. |
| `.kicad-happy.json` | Config for the kicad-happy Claude plugin (analysis output in `analysis/`, gitignored except the manifest). |

## KiCad version

The project version is **KiCad 10.0**; KiCad 9 or older cannot open a KiCad 10 save.

The committed `.kicad_sch` is KiCad 7 format until the owner re-saves it in KiCad 10; merge is gated on that re-save plus the owner's KiCad 10 ERC.

The single-fuse revision is regenerated in KiCad 7 format again. Owner steps: close KiCad, pull, open, Update Symbols from Library, save, run ERC, re-plot the PDF, push.

Previous revision: the meeting-cleanup revision was generated in KiCad 7 format, then opened, symbol-updated (D2–D4) and saved in KiCad 10.0 by the owner (94ccd72), with label positions tidied in dd946f3. Edit the KiCad 10 files from here on; close KiCad before pulling. `rc_power_board.kicad_pro` (net classes, ERC severities) is the owner's KiCad 10 file.

## ATO fuse, JST-XH convention, Garmin I2C (current revision)

- **F1** is a standard ATO/ATC blade fuse in a Littelfuse FLR 178.6165.0001 holder (`Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165`); value `TBD ATO/ATC blade 10-15A`. Proposed fuse: Littelfuse 0257015.PXPV (15 A). Details in `bom.md`.
- **JST-XH (2.5 mm) is the connector convention** for sensors and low-power parts (single Dupont jumper sockets push onto the XH pins for breadboard debugging; 2.54 mm multi-pin housings do not fit; parts in lab stock). Exceptions: J1 (battery T-plug pads), J6/J7 (USB-C pigtail screw terminals, over 3 A).
- **J3, J4:** 3-pin XH, pins 1 GND, 2 +6V_BEC, 3 signal (follows the ESC/servo lead; XH 2.50 mm does not mate with stock 2.54 mm plugs: re-terminate only 22 AWG leads, else an adapter lead). **J5:** 6-pin XH: 1 `U1_PG` (GPIO TBD), 2 `THROTTLE_PWM` GPIO5, 3 `STEER_PWM` GPIO4, 4 `I2C_SDA` GPIO8, 5 `I2C_SCL` GPIO9, 6 GND. **J8:** Garmin LIDAR-Lite v4, 4-pin XH, pin order = Garmin 1-4 (+5V_SENS, GND, SDA, SCL); no external I2C pull-ups. J9, J11-J14 stay 2-pin XH (1 V+, 2 GND). Pin order convention and crimp table: `fab_handoff.md`.
- **Netlist: 39 parts, 21 nets** (adds `I2C_SDA`, `I2C_SCL`); pending the owner's KiCad 10 ERC.
- **Power5A** track width is 1.6 mm. Computed IPC-2221 widths and the 2 oz recommendation are in `fab_handoff.md`.
- **Owner steps:** close KiCad, pull, open, Update Symbols from Library, save in KiCad 10, run ERC, Assign Footprints check (XH and ATO footprints), re-plot the PDF, push.

## Meeting-cleanup revision (what changed)

- **Wiring for traceability.** Each region's local nets (`VBAT_RAW`, `LDO_IN`, the rail outputs; `VIN_CPU`/`VIN_SENS` were merged into `VBAT`, see below) run as one bus from source to load, with no crossings. Each bus carries a single net label so the net keeps its name. GND is still drawn as symbols.
- **ESC power is off-board.** The battery feeds the ESC directly on its own 12 AWG leads, carrying up to 20 A of motor current. J2, F2 and `VBAT_ESC` are removed. On the board, the ESC is now only the J3 3-wire receiver lead: throttle PWM plus the 6 V BEC. Board load on `VBAT` is about 7.3 A worst case (about 7.8 A at the 6.0 V cutoff), so F1 is TBD (10-15 A; see the single-fuse revision). A note on the sheet records the ESC draw.
- **U1 EN is left unconnected (feature archived).** The module's internal pull-up keeps U1 always on. Q1, R4, `ESP_SHDN` and region F are removed. U1 PG still goes to the ESP32.
- **The radar header (J10) is removed.** The gap in reference numbers is deliberate, so J11 keeps its name.
- **`+6V_BEC`** now uses a project rail symbol, like the other rails.
- **J5** was 4-pin in this revision (now 6-pin, see the current revision): 1 `U1_PG`, 2 `THROTTLE_PWM` (GPIO5), 3 `STEER_PWM` (GPIO4), 4 GND. The `U1_PG` GPIO is TBD until firmware adds it; when it does, update `pins.h` and the README pin table together.

## Single-fuse revision (what changed)

- **One replaceable main fuse, F1, for the whole board** (compute and both sensor rails), because the fuse inventory is high-current. Branch fuses F3 (compute) and F4 (sensor) are removed.
- **Nets `VIN_CPU` and `VIN_SENS` are gone**, merged into `VBAT` (class HighCurrent). U1 VIN and U2 VIN sit directly on `VBAT`.
- **F1** was a Mini (ATM) blade fuse in a Keystone 3568 holder (superseded by the ATO/ATC revision above). Rating discussion is in `bom.md`.
- **Trade-off:** a sensor-branch short now opens F1 and drops compute too. U1 and U2 have their own output current limiting.
- **Netlist then: 39 parts, 19 nets (now 21, see the current revision).** Net classes: HighCurrent = `*VBAT*`, GND; Power5A = `+5V_CPU`; Power3A = `+5V_SENS`, `*+6V_BEC`.
- **U1 EN** stays unconnected until the rev 2 prototype board. U1 is in hand; U2 is not bought yet.
- **New docs:** `bom.md` and `fab_handoff.md`.

## Design notes

- **Rail symbols.** Each rail is a project power symbol whose hidden pin name and Value both equal the rail name, instead of a renamed `power:VCC`. This keeps nets correct in KiCad 7 (where the pin name sets the net) and in 8 and later (where the Value does).
- **U1, Pololu D36V50F5.**
  - Drawn with all 12 pins: 1 PG, 2 EN, 3–4 VRP, 5–6 VIN, 7–10 GND, 11–12 VOUT.
  - Footprint `PinHeader_2x06_P2.54mm_Vertical`. Check the pin numbering against Pololu's dimension drawing before layout.
  - Each header pin is rated 3 A, so VIN, VOUT and GND use their pin pairs.
  - VRP is unused: the sensor buck is fed from `VBAT` (VRP would overload U1's 6 A VIN pin pair).
  - Rated 5.0 V / 5.5 A, against the plan's 5.1 V / ≥ 6 A target.
- **J1** is a pair of wire pads for the battery's T-plug pigtail (12 AWG). The pad footprint is a placeholder; size TBD.
- **J6/J7** are 2-wire USB-C pigtails into the Pi 5 and the ESP32's left USB-C port, so each board's own USB-C input protection stays in the path. They are 20 AWG, 30 cm long, and drop about 0.10 V at 5 A; trim them to 10–15 cm.
- **PWR_FLAG** symbols are ERC-only markers. They tell ERC that power enters a net that is fed through a fuse or ferrite. They have no physical part and are not on the PCB. The probe points are TP1–TP3.
- **LED resistors** connect pin-to-pin to their LEDs, so those three nets carry KiCad's auto names (`Net-(D2-A)` and so on).
- **Net-class patterns** are `*VBAT*`, `+5V_CPU`, `+5V_SENS` and `*+6V_BEC`. The leading `*` matches the `/` that KiCad puts in front of local-label nets.
- **D1** is `Device:D_Zener`, used as a unidirectional TVS, cathode to `VBAT`.
- **Placeholder footprints.** All ratings are TBD; pick real parts before layout.
  - F1: `Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165` (ATO/ATC blade).
  - C1: 10 mm radial electrolytic.
  - D1: SMB.
  - FB1: 0805.
  - TP1–TP3: 1.5 mm pads.
  - U2: module TBD, no footprint yet.

## Verification so far

The current revision: **39 parts, 21 nets**, per the regenerated netlist; the owner's KiCad 10 ERC is pending. The figures below are from the previous (41 parts, 21 nets) revision.

The previous revision was checked with KiCad 7.0.11 `kicad-cli`, the kicad-happy analyzer and the owner's KiCad 10 ERC:

- **Netlist: 41 parts, 21 nets.** The only single-pin nets are U1 EN, U1 VRP ×2, U2 EN and U3 NC. All of them are intentionally unconnected and carry no-connect flags.
- **Analyzer:** finds the same 41 parts and 21 nets. U1 and U2 are classified as switching regulators, U3 as a 3.3 V LDO, and D2–D4 as resistor-limited LEDs. The remaining findings are expected for a draft:
  - no MPNs or datasheets (all TBD);
  - no footprint for U2;
  - "missing pull-up" on U1 PG (the ESP32's internal pull-up handles it);
  - "missing pull-up" on U3 EN (it is tied to VIN, per the AP2112 datasheet).
- **PDF:** rendered and visually checked: no wire crossings in any region, and no text overlaps.
- **ERC in KiCad 10 (owner-run, 94ccd72): clean**, after Update Symbols from Library. `rc_power_board.pdf` re-plotted from KiCad 10 (dd946f3).
- **Analyzer on the KiCad 10 save (dd946f3):** still 41 parts, 21 nets, 4 no-connects, so the upgrade and label tidy changed no connections.
- **Not yet done:** SPICE, PCB layout.

## Working on this folder with Claude Code

The repo enables the kicad-happy plugin (`.claude/settings.json`). Rules for this folder are in `.claude/rules/schematics.md`. Typical asks are "review docs/schematics", "check the power budget against the schematic" and "simulate the subcircuits". SPICE needs `ngspice` installed on the host.
