---
paths:
  - "docs/schematics/**"
---

# Schematics (power distribution board)

## Sources of truth
- Spec: `docs/schematics/power_board_plan.md` (exported from the live Claude Doc linked at its top). Schematic changes that contradict it => update the plan in the same change, or ask.
- Inventory and part facts: `docs/datasheets/` (components_list.xlsx, ESC manual, servo datasheet, Pololu D36V50F5). Never invent a part value: unknown => `TBD` (repo rule: no unconfirmed parameters).
- Project KiCad version: 10.0. Do not save the project with an older KiCad; do not downgrade the file format.

## Invariants
- Rails: `VBAT`, `+5V_CPU` (Pi 5 + ESP32 only), `+5V_SENS`, `+3V3_SENS` (LDO from `+5V_SENS`), `+6V_BEC` (ESC BEC, servo only, never joined to a 5 V rail). One common `GND`; never `GNDA`/`GNDD`/`GNDPWR`.
- Rails are project power symbols from `rc_power.kicad_sym` (pin name == Value == net name). Never rename a stock `power:` symbol's Value to make a rail.
- ESP32 powers nothing; sensors never take power from ESP32 pins; signals <= 3.3 V.
- Every net feeding a power_in pin through a fuse or ferrite has a PWR_FLAG.
- Net classes live in `rc_power_board.kicad_pro` and must match the plan's net-class table (VIN_CPU/VIN_SENS included).

## Tooling (kicad-happy@kicad-happy)
- Review/analysis => `kicad` skill; subcircuit checks => `spice` skill (needs ngspice); EMC once a PCB exists => `emc`.
- Analyzer output goes to `docs/schematics/analysis/` (config `.kicad-happy.json`; per-run JSON gitignored, manifest tracked).
- Treat analyzer findings as claims to verify against the raw `.kicad_sch` and datasheets; known false positives on this board: "U3 missing input capacitor" (C7 is its input cap), "U3 EN missing pull-up" (EN tied to VIN per AP2112 datasheet).
- ERC/DRC results count only when run in KiCad 10 (user-run, or kicad-cli 10 if installed); never claim ERC passed without its output.
