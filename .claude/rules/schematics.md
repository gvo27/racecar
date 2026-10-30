---
paths:
  - "docs/schematics/**"
---

# Schematics (power distribution board)

## Sources of truth
- Spec / build guide: `docs/schematics/power_board_plan.md` (exported from the live Claude Doc linked at its top). Schematic changes that contradict it => update the plan in the same change, or ask.
- Parts: `docs/schematics/bom.md`. Layout/fab checklist: `docs/schematics/fab_handoff.md`.
- Meeting summary: `docs/schematics/design_overview.md` (concise, < 2 pages). Keep it in step with the schematic.
- Inventory and part facts: `docs/datasheets/` (components_list.xlsx, ESC manual, servo datasheet, Pololu D36V50F5). Never invent a part value: unknown => `TBD` (repo rule: no unconfirmed parameters).
- Project KiCad version: 10.0. Do not save the project with an older KiCad; do not downgrade the file format (exception: generator output in KiCad 7 format is allowed until the owner re-saves it in KiCad 10; see docs/schematics/README.md).

## Invariants
- Rails: `VBAT`, `+5V_CPU` (Pi 5 + ESP32 only), `+5V_SENS`, `+3V3_SENS` (LDO from `+5V_SENS`), `+6V_BEC` (ESC BEC, servo only, never joined to a 5 V rail). One common `GND`; never `GNDA`/`GNDD`/`GNDPWR`.
- Rails are project power symbols from `rc_power.kicad_sym` (pin name == Value == net name). Never rename a stock `power:` symbol's Value to make a rail.
- ESP32 powers nothing; sensors never take power from ESP32 pins; signals <= 3.3 V.
- Every net feeding a power_in pin through a fuse or ferrite has a PWR_FLAG.
- U1 (Pololu D36V50F5) EN is left unconnected (no-connect; ESP32 control archived). It never connects directly to an ESP32 GPIO: EN has a 100k pull-up to VIN (up to 8.4 V), and U1 powers the ESP32, so U1 must start on its own. Any future control goes through a transistor.
- ESC battery power is off-board (battery -> ESC on its own 12 AWG leads, up to 20 A). The board carries only the ESC's 3-wire lead (THROTTLE_PWM + `+6V_BEC`); size the fuse for board loads (~7.3 A at 6.4 V, ~7.8 A at the 6.0 V cutoff), but size VBAT_RAW/VBAT/GND copper for F1's rating (~16.5 A for 15 A, ~11 A for 10 A), not the load.
- Wiring style: each region's local nets are wired as one bus/trunk source-to-load with one net label, avoiding crossings; GND stays as symbols.
- U1 VRP is unused; the sensor buck is fed from VBAT (VRP would overload U1's 6 A VIN pin pair).
- One replaceable main fuse F1 protects all board loads; no branch fuses (fuse inventory is high-current).
- Power to the Pi 5 and ESP32 leaves through 2-wire USB-C pigtails (J6/J7) so their own USB-C input protection stays in the path.
- Net classes live in `rc_power_board.kicad_pro` and must match the plan's net-class table.

## Tooling (kicad-happy@kicad-happy)
- Review/analysis => `kicad` skill; subcircuit checks => `spice` skill (needs ngspice); EMC once a PCB exists => `emc`.
- Analyzer output goes to `docs/schematics/analysis/` (config `.kicad-happy.json`; per-run JSON gitignored, manifest tracked).
- Treat analyzer findings as claims to verify against the raw `.kicad_sch` and datasheets; known false positives on this board: "U3 missing input capacitor" (C7 is its input cap), "U3 EN missing pull-up" (EN tied to VIN per AP2112 datasheet).
- ERC/DRC results count only when run in KiCad 10 (user-run, or kicad-cli 10 if installed); never claim ERC passed without its output.
