# Power distribution board (baseline schematic)

Draft KiCad project for the car's power board. A 2S LiPo comes in; the board puts out `VBAT`, `+5V_CPU`, `+5V_SENS` and `+3V3_SENS` on a common `GND`, and routes `+6V_BEC` from the ESC to the servo. The ESC's own battery power is off-board. This is a **review draft**: every value marked `TBD` is unconfirmed (project rule: no unconfirmed parameters).

| File | What it is |
| --- | --- |
| `design_overview.md` | The design meeting summary: one short entry per feature, the power budget and the decisions wanted. |
| `bom.md` | How the BOM is made (`make bom`, symbol fields), fuse notes, stock notes. |
| `bom.csv` | BOM exported from the schematic fields by `make bom` (generated; commit it). |
| `bom_offboard.csv` | Hand-kept BOM of parts with no symbol (XH housings, crimps, stock, J6/J7 options). |
| `fab_handoff.md` | Rev A CNC-milling handoff (Makera Carvera) plus later-revision fab checklist: DRC/net classes, rivets, holes, IPC-2221 table, connector table, export, sign-off. |
| `power_board_plan.md` | The build guide and background: rails, power budget, trace widths, a step-by-step KiCad guide and open questions. Exported from the live doc linked at its top. |
| `power_architecture.png` | Block diagram used by the plan. |
| `rc_power_board.kicad_pro` / `.kicad_sch` | KiCad project and the one-sheet A3 schematic (regions A to E plus notes). |
| `rc_power.kicad_sym` + `sym-lib-table` | Project symbol library: `D36V50F5` (all 12 module pins, used by U1 and U2), `REG_MODULE` (generic VIN/GND/VOUT/EN, no longer used on the board) and one power symbol per rail. |
| `rc_power_board.kicad_pcb` / `.kicad_dru` | Rev A board, routed, for review only (no Gerber or CAM files). The `.kicad_dru` holds rule `U3_fine`. |
| `rc_power.pretty/` + `fp-lib-table` | Project footprint library: `Pololu_D36V50Fx` (U1 and U2: 12 pads and the full 25.4 x 25.4 mm body, from Pololu's drawing; facts in `docs/datasheets/regulator_pololu_d36v50f5.md`). |
| `milling.toml`, `milling_waivers.toml` | Milling limits (each value `assumed` or `confirmed`) and the waiver list for the milling check. |
| `tools/` | Python tools and tests that run in the KiCad image: `build_pcb.py`, `placement.py`, `route_pcb.py`, `check_board.py`, `milling_check.py`, `review_plots.py`. |
| `review/` | Review package: DRC report, milling check, layer PDF, 1:1 PDF, `README.md`. |
| `rc_power_board.pdf` | Plot of the sheet, for review without KiCad. |
| `.kicad-happy.json` | Config for the kicad-happy Claude plugin (analysis output in `analysis/`, gitignored except the manifest). |

## KiCad version

The project version is **KiCad 10.0**; KiCad 9 or older cannot open a KiCad 10 save.

The committed `.kicad_sch` is now KiCad 10 format: `kicad-cli sch upgrade` (10.0.8) saved it with the U2 footprint change. The owner's GUI steps stay open: Update Symbols from Library (the 3 `lib_symbol_mismatch` warnings, D2 to D4), a re-plot of the PDF, and the owner's KiCad 10 ERC.

The single-fuse revision is regenerated in KiCad 7 format again. Owner steps: close KiCad, pull, open, Update Symbols from Library, save, run ERC, re-plot the PDF, push.

Previous revision: the meeting-cleanup revision was generated in KiCad 7 format, then opened, symbol-updated (D2–D4) and saved in KiCad 10.0 by the owner (94ccd72), with label positions tidied in dd946f3. Edit the KiCad 10 files from here on; close KiCad before pulling. `rc_power_board.kicad_pro` (net classes, ERC severities) is the owner's KiCad 10 file.

## U1 and U2 = Pololu D36V50F5 (current revision)

- **U1 and U2** are both the Pololu D36V50F5 (#4091, 5 V, 5.5 A typical). Owner decision 2026-11-12: the owner has two modules, and the same part on both rails gives a swap spare. This replaces the D24V90F5 assumption for U2 (2026-11-11).
- Facts, archived drawing and graphs: `docs/datasheets/regulator_pololu_d36v50f5.md`. The D24V90F5 note stays as history (`regulator_pololu_d24v90f5.md`, superseded).
- Both modules use the symbol `rc_power:D36V50F5` and the footprint `rc_power:Pololu_D36V50Fx`. The footprint shows the real 25.4 x 25.4 mm body (the first rev A layout used a plain pin header and put the body over J6 and J7). U2 EN, VRP and PG have no-connect flags, as U1 EN and VRP.
- **Flag:** dropout is about 1.0 V at 5 A (Pololu graph). Near the 6.0 V cutoff the +5V_SENS output can fall below 5 V, and the Mapper needs at least 4.8 V. Bench check at J11 during Mapper startup.
- Decisions on 2026-11-11 (owner): no reverse-polarity protection on rev A (the modules have their own); U3 keeps the stock SOT-23-5 footprint with the `U3_fine` DRC rule.
- Plan: `docs/plans/2026-11-11-power-board-pcb-rev-a.md` (Task 7c).

## Rev A PCB (review only)

The board is built and routed headless in the pinned KiCad 10.0.8 image: `make kicad-image`, then `make erc pcb-build pcb-route pcb-check pcb-mill-check pcb-review pcb-test`. Freerouting 2.5.0 (pinned by digest) routes it. `pcb-build` refuses to overwrite an existing board without `--force`: after the first build the `.kicad_pcb` is the owner's file. Results, assumptions and the owner's GUI checks are in `review/README.md`. Gerber, drill and CAM export wait for the lab tech.

## ATO fuse, JST-XH convention, Garmin I2C (earlier revision)

- **F1** is a standard ATO/ATC blade fuse in a Littelfuse FLR 178.6165.0001 holder (`Fuse:FuseHolder_Blade_ATO_Littelfuse_FLR_178.6165`); value `TBD ATO/ATC blade 15A` (15 A decided by the Mapper load, see the Mapper revision below). Proposed fuse: Littelfuse 0257015.PXPV (15 A). Details in `bom.md`.
- **JST-XH (2.5 mm) is the connector convention** for sensors and low-power parts (single Dupont jumper sockets push onto the XH pins for breadboard debugging; 2.54 mm multi-pin housings do not fit; parts in lab stock). Exceptions: J1 (battery T-plug pads), J6/J7 (USB-C pigtail screw terminals, over 3 A).
- **J3, J4:** 3-pin XH, pins 1 GND, 2 +6V_BEC, 3 signal (follows the ESC/servo lead; XH 2.50 mm does not mate with stock 2.54 mm plugs: re-terminate only 22 AWG leads, else an adapter lead). **J5:** 6-pin XH: 1 `U1_PG` (GPIO TBD), 2 `THROTTLE_PWM` GPIO5, 3 `STEER_PWM` GPIO4, 4 `I2C_SDA` GPIO8, 5 `I2C_SCL` GPIO9, 6 GND. **J8:** Garmin LIDAR-Lite v4, 4-pin XH, pin order = Garmin 1-4 (+5V_SENS, GND, SDA, SCL); no external I2C pull-ups. J9, J11-J14 stay 2-pin XH (1 V+, 2 GND); J11 now hosts the Slamtec Mapper (see below). Pin order convention and crimp table: `fab_handoff.md`.
- **Netlist then: 39 parts, 21 nets** (adds `I2C_SDA`, `I2C_SCL`); now 40 parts, 21 nets (see the Mapper revision).
- **Power5A** track width is 1.6 mm (now also `+5V_SENS`, see below). Computed IPC-2221 widths are in `fab_handoff.md` (2 oz stock).
- **Owner steps:** close KiCad, pull, open, Update Symbols from Library, save in KiCad 10, run ERC, Assign Footprints check (XH and ATO footprints), re-plot the PDF, push.

## Slamtec Mapper on `+5V_SENS` (earlier revision)

- **J11** (was `Spare 5V`) now hosts the Slamtec Mapper M2M1 lidar. Harness: J11 2-pin XH, XHP-2 housing, 22 AWG 3 A USB-A male 2-wire pigtail (pin 1 `+5V_SENS` to red/VBUS, pin 2 GND to black). Mapper supply 4.8 V min / 5 V typ / 12 V max; running 0.75 A typ, 1.3 A max; startup 1.4-1.6 A for a few seconds; ripple 20 mV typ, 50 mV max (from its datasheet on branch `lidar`). Not powered from Pi USB or straight from the pack.
- **C9** (`Device:C_Polarized`, `TBD >=100uF low-ESR >=10V`, footprint `CP_Radial_D8.0mm_P3.50mm`) added on `+5V_SENS` / GND at J11 for the startup surge and ripple.
- **Budget (computed):** `+5V_SENS` 3.3 A -> 4.6 A worst case running, 4.9 A at Mapper startup. U2 must now be >= 6 A: the Pololu D36V50F5 (owner 2026-11-12) gives about 7.4 A at 6 V in and about 8 A at 8.4 V in (Pololu graph); dropout near the 6.0 V cutoff is a bench check. U2 input 3.99 A at 6.4 V, 4.26 A at 6.0 V; U1 input 4.43 A / 4.72 A. Board `VBAT` load about 8.4 A at 6.4 V, 9.0 A at 6.0 V, about 9.3 A briefly at startup (was 7.3 / 7.8 A).
- **F1 = 15 A** (10 A would run at 84-93 % of rating, over the ~75 % rule; 15 A gives 56-62 %). Copper stays sized for 16.5 A. Inrush margin unchanged.
- **Net classes:** `+5V_SENS` moved from Power3A (1.0 mm) to Power5A (1.6 mm) in `rc_power_board.kicad_pro` (about 4.9 A; IPC-2221 5.0 A row, 2 oz: 1.4 mm at ΔT 10 C). `*+6V_BEC` stays Power3A.
- **DRC rules** in `rc_power_board.kicad_pro` (board.design_settings.rules) set to match the CNC docs: `min_clearance` 0.4, `min_track_width` 0.5, `min_via_diameter` 2.0, `min_via_annular_width` 0.45, `min_through_hole_diameter` 0.8 (C9 drill; methods TBD).
- **Schematic:** J3 and its wires/symbols sit 1.27 mm up-left of the generator's old position, ported from the owner's 53ac275 save. Netlist: 40 parts, 21 nets; everything but C9 is identical to the previous revision. Notes box updated (budget, F1, U2, `+5V_SENS` class, new note 14 for the Mapper).
- **Owner steps:** open in KiCad 10, Update Symbols, save, run ERC, re-plot; choose C9 and U2 parts.

## CNC-milled prototype (Makera Carvera)

Rev A is milled in-house from Kepro P22-365G 2 oz double-sided FR-4 (3" x 6"); no fab house, no plated holes, vias are soldered copper rivets.

- **Rivets (update):** lab stock is an LPKF EasyContac kit (0.6/0.8/1.0/1.2 mm, with setting tool). Default via = 0.8 mm rivet, drill 1.1 mm, pad 2.0 mm (matches the existing `.kicad_pro` via settings); 1.2 mm optional for high current. Table and source: `fab_handoff.md`. BOM rivets now $0.

- **`rc_power_board.kicad_pro`:** all four net classes clearance 0.2 -> 0.4 mm; Default track 0.25 -> 0.5 mm; via diameter/drill for all classes -> 2.0 / 1.1 mm (LPKF EasyContac 0.8 mm rivet). DRC rules set: clearance 0.4, track 0.5, via 2.0/1.1, annular 0.45, min hole 0.8; plan's net-class table updated.
- **Docs:** `fab_handoff.md` restructured (A: CNC prototype, B: fab house later) with a JST header table for every external connection; `bom.md` adds stock, rivets, dowels, bits and optional VH/XH rows, no PCB fab cost (total about 87.0 USD, about 47.1 excluding U1 after the rivet update); `design_overview.md` and `.claude/rules/schematics.md` updated.
- **Owner steps:** pull; open Board Setup in KiCad 10 and verify the preloaded design-rule minimums (clearance 0.4, track 0.5, via 2.0, annular 0.45, min hole 0.8); the net-class values are provisional; confirm the bit list (incl. a 1.1 mm bit) with the lab tech; decide the U3 footprint option. (The DRC minimums are now set in `rc_power_board.kicad_pro`, see the Mapper revision; the Mapper question is decided.)

## Meeting-cleanup revision (what changed)

- **Wiring for traceability.** Each region's local nets (`VBAT_RAW`, `LDO_IN`, the rail outputs; `VIN_CPU`/`VIN_SENS` were merged into `VBAT`, see below) run as one bus from source to load, with no crossings. Each bus carries a single net label so the net keeps its name. GND is still drawn as symbols.
- **ESC power is off-board.** The battery feeds the ESC directly on its own 12 AWG leads, carrying up to 20 A of motor current. J2, F2 and `VBAT_ESC` are removed. On the board, the ESC is now only the J3 3-wire receiver lead: throttle PWM plus the 6 V BEC. Board load on `VBAT` was then about 7.3 A worst case (about 7.8 A at the 6.0 V cutoff; now 8.4 / 9.0 A with the Mapper, F1 = 15 A). A note on the sheet records the ESC draw.
- **U1 EN is left unconnected (feature archived).** The module's internal pull-up keeps U1 always on. Q1, R4, `ESP_SHDN` and region F are removed. U1 PG still goes to the ESP32.
- **The radar header (J10) is removed.** The gap in reference numbers is deliberate, so J11 keeps its name.
- **`+6V_BEC`** now uses a project rail symbol, like the other rails.
- **J5** was 4-pin in this revision (now 6-pin, see the current revision): 1 `U1_PG`, 2 `THROTTLE_PWM` (GPIO5), 3 `STEER_PWM` (GPIO4), 4 GND. The `U1_PG` GPIO is TBD until firmware adds it; when it does, update `pins.h` and the README pin table together.

## Single-fuse revision (what changed)

- **One replaceable main fuse, F1, for the whole board** (compute and both sensor rails), because the fuse inventory is high-current. Branch fuses F3 (compute) and F4 (sensor) are removed.
- **Nets `VIN_CPU` and `VIN_SENS` are gone**, merged into `VBAT` (class HighCurrent). U1 VIN and U2 VIN sit directly on `VBAT`.
- **F1** was a Mini (ATM) blade fuse in a Keystone 3568 holder (superseded by the ATO/ATC revision above). Rating discussion is in `bom.md`.
- **Trade-off:** a sensor-branch short now opens F1 and drops compute too. U1 and U2 have their own output current limiting.
- **Netlist then: 39 parts, 19 nets (now 40 parts, 21 nets, see the Mapper revision).** Net classes then: HighCurrent = `*VBAT*`, GND; Power5A = `+5V_CPU`; Power3A = `+5V_SENS`, `*+6V_BEC` (now `+5V_SENS` is Power5A).
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

The current revision (Mapper on J11): **40 parts, 21 nets**, per the regenerated netlist (KiCad 7.0.11 `kicad-cli`); the only netlist change vs the previous revision is C9 added to `+5V_SENS` / GND. The kicad-happy analyzer finds 40 parts, 21 nets, 4 no-connects and the same findings as before. The owner's KiCad 10 ERC on this revision is pending (the previous save, 53ac275, was clean). The figures below are from the earlier (41 parts, 21 nets) revision.

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
