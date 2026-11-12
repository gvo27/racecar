---
paths:
  - "docs/schematics/**"
---

# Schematics (power distribution board)

## Sources of truth
- Spec / build guide: `docs/schematics/power_board_plan.md` (exported from the live Claude Doc linked at its top). Schematic changes that contradict it => update the plan in the same change, or ask.
- Parts: symbol fields in the schematic (MPN, Manufacturer, Status, Unit cost USD, Supplier link, BOM Comments), exported by `make bom` to `docs/schematics/bom.csv` (commit it); off-board items in `bom_offboard.csv`; notes in `docs/schematics/bom.md`. CNC-milling (rev A) and later fab checklist: `docs/schematics/fab_handoff.md`.
- Meeting summary: `docs/schematics/design_overview.md` (concise, < 2 pages). Keep it in step with the schematic.
- Inventory and part facts: `docs/datasheets/` (components_list.xlsx, ESC manual, servo datasheet, Pololu D36V50F5 (U1), Pololu D24V90F5 (U2, `regulator_pololu_d24v90f5.md`)). Never invent a part value: unknown => `TBD` (repo rule: no unconfirmed parameters).
- Project KiCad version: 10.0. Do not save the project with an older KiCad; do not downgrade the file format (the schematic is KiCad 10 format since the U2 footprint change; see docs/schematics/README.md).

## Invariants
- Rails: `VBAT`, `+5V_CPU` (Pi 5 + ESP32 only), `+5V_SENS`, `+3V3_SENS` (LDO from `+5V_SENS`), `+6V_BEC` (ESC BEC, servo only, never joined to a 5 V rail). One common `GND`; never `GNDA`/`GNDD`/`GNDPWR`.
- Rails are project power symbols from `rc_power.kicad_sym` (pin name == Value == net name). Never rename a stock `power:` symbol's Value to make a rail.
- ESP32 powers nothing; sensors never take power from ESP32 pins; signals <= 3.3 V.
- Every net feeding a power_in pin through a fuse or ferrite has a PWR_FLAG.
- U1 (Pololu D36V50F5) EN is left unconnected (no-connect; ESP32 control archived). It never connects directly to an ESP32 GPIO: EN has a 100k pull-up to VIN (up to 8.4 V), and U1 powers the ESP32, so U1 must start on its own. Any future control goes through a transistor.
- ESC battery power is off-board (battery -> ESC on its own 12 AWG leads, up to 20 A). The board carries only the ESC's 3-wire lead (THROTTLE_PWM + `+6V_BEC`); size the fuse for board loads (~8.4 A at 6.4 V, ~9.0 A at the 6.0 V cutoff, ~9.3 A briefly at Mapper startup; F1 = 15 A, decided), but size VBAT_RAW/VBAT/GND copper for F1's rating (~16.5 A), not the load.
- Wiring style: each region's local nets are wired as one bus/trunk source-to-load with one net label, avoiding crossings; GND stays as symbols.
- U1 VRP is unused; the sensor buck is fed from VBAT (VRP would overload U1's 6 A VIN pin pair).
- Slamtec Mapper M2M1 is on J11 (+5V_SENS; harness XH -> 22 AWG 3 A USB-A pigtail, never Pi USB or straight from the pack): 0.75 A typ / 1.3 A max, 1.4-1.6 A startup, ripple <= 50 mV. +5V_SENS is 4.6 A running / 4.9 A startup, so U2 must be >= 6 A (assumed Pololu D24V90F5, owner 2026-11-11; the D24V60F5 is discontinued; dropout about 1.0 V at 5 A, bench check near the 6.0 V cutoff; facts in `docs/datasheets/regulator_pololu_d24v90f5.md`) and C9 (>= 100 uF low-ESR, TBD) sits at J11.
- One replaceable main fuse F1 (standard ATO/ATC blade in a Littelfuse FLR 178.6165 PCB holder) protects all board loads; no branch fuses (fuse inventory is high-current).
- Connectors: JST-XH (2.5 mm) for sensors and low-power parts (single Dupont jumper sockets push onto XH pins for breadboard debug; 2.54 mm multi-pin housings don't fit; lab stock); exceptions: J1 battery T-plug pads, J6/J7 USB-C pigtail screw terminals (>3 A).
- XH pin order (crimp table in `fab_handoff.md`; keep it in step with the schematic): Rule A, device with its own pinout, header follows the device (J3/J4: 1 GND, 2 +6V_BEC, 3 signal; J8: 1 +5V_SENS, 2 GND, 3 SDA, 4 SCL). Rule B, generic power header: 1 V+, 2 GND (J9, J11 +5V_SENS; J12-J14 +3V3_SENS). Rule C, signal harness: signals in order, GND last (J5: 1 U1_PG, 2 THROTTLE_PWM, 3 STEER_PWM, 4 I2C_SDA, 5 I2C_SCL, 6 GND). Layout: XH headers on the board edge, entry outward, pin 1 at the same end.
- J3/J4 XH current: 3 A/pin with 22 AWG only; BEC pin up to 3 A = 100 % of rating. Never claim it "fits" or is "within" rating.
- Garmin LIDAR-Lite v4 on J8 (4-pin XH, pin order = Garmin 1–4); I2C_SDA GPIO8, I2C_SCL GPIO9 via J5; no external pull-ups (13 kΩ internal to 3.3 V).
- Power to the Pi 5 and ESP32 leaves through 2-wire USB-C pigtails (J6/J7) so their own USB-C input protection stays in the path.
- Rev A prototype is milled in-house on a Makera Carvera from 2 oz double-sided FR-4 (3"×6"): no plated holes; vias are LPKF EasyContac 0.8 mm rivets (assumed drill 1.2 / pad 2.1 mm because the bit set has no 1.1 mm bit; see `fab_handoff.md`); DRC clearance ≥0.4 mm; route THT connector pins on the bottom; board outline fits the stock.
- Net classes live in `rc_power_board.kicad_pro`; clearance 0.4 mm all classes; HighCurrent 6.0, Power5A (`+5V_CPU`, `+5V_SENS`) 1.6, Power3A (`*+6V_BEC`) 1.0, Default 0.5 mm; DRC rules min clearance 0.4, track 0.5, via 2.0, annular 0.45, min hole 0.8; via 2.1/1.2 mm (assumed, EasyContac 0.8 mm rivet). `fab_handoff.md` matches the plan's net-class table for rev A; fab-house revisions restore the plan values.

## Tooling (kicad-happy@kicad-happy)
- Review/analysis => `kicad` skill; subcircuit checks => `spice` skill (needs ngspice); EMC once a PCB exists => `emc`.
- Analyzer output goes to `docs/schematics/analysis/` (config `.kicad-happy.json`; per-run JSON gitignored, manifest tracked).
- Treat analyzer findings as claims to verify against the raw `.kicad_sch` and datasheets; known false positives on this board: "U3 missing input capacitor" (C7 is its input cap), "U3 EN missing pull-up" (EN tied to VIN per AP2112 datasheet), "U1 PG missing pull-up" (ESP32 input pull-up), "VBAT plane split" (overlapping bus zones merge into one piece). More in `docs/schematics/review/README.md`.
- ERC/DRC results count only when run in KiCad 10 (user-run, or kicad-cli 10 if installed); never claim ERC passed without its output.

## Rev A PCB (review only; Gerber and CAM wait for the lab tech)
- Board: `docs/schematics/rc_power_board.kicad_pcb`, built by `tools/build_pcb.py` and routed by `tools/route_pcb.py` in the pinned KiCad 10.0.8 image (`docker/kicad.Dockerfile`) and Freerouting 2.5.0 (digest in the Makefile). Make targets: `kicad-image erc pcb-build pcb-route pcb-check pcb-mill-check pcb-review pcb-test bom`. No host Python for the tools. After the first build the `.kicad_pcb` is the owner's file: `pcb-build` refuses to overwrite it without `--force`.
- Rivet via (assumed): 1.2 mm drill / 2.1 mm pad, annular 0.45 mm, in every net class. Assumed drill set: 0.8, 1.0, 1.2, 1.5 mm; larger holes are milled (the list is `MILLED_HOLES` in `tools/placement.py`). Limits and their status: `docs/schematics/milling.toml`.
- `make pcb-check` also runs the opening test of `check_board.py` (`PATH_ROWS`): copper width along the GND, `VBAT` and 5 V paths on B.Cu. Power zones and the `U1_PG` jumper are planned in `tools/placement.py` (`BUS_ZONES`, `GND_KEEPOUTS`, `JUMPERS`); the router (no vias) handles signals only. `build_pcb.py --sync-fields` copies the symbol fields onto an existing board without other changes.
- After every board change run `make pcb-check pcb-mill-check` (skill `pcb-milling-check`). DRC clean does not mean millable. MILL-DEPTH is a finding about the assumed depth range (owner and lab tech), not a board error.
- Never put F.Cu copper on a THT pad. Never put a via inside a part courtyard. VBAT, VBAT_RAW and GND are B.Cu zones, not tracks.
- Connector pin order decides if a net can be routed on one layer: do not change a J3/J4/J5/J8 orientation without a new `make pcb-route`. Rule `U3_fine` is in `rc_power_board.kicad_dru`.

