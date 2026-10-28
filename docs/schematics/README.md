# Power distribution board (baseline schematic)

Draft KiCad project for the car's power board: 2S LiPo in, four rails out (`VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`), common `GND`. It is a **review draft**: every value marked `TBD` is unconfirmed (project rule: no unconfirmed parameters).

| File | What it is |
| --- | --- |
| `power_board_plan.md` | The spec: rails, power budget, trace widths, step-by-step KiCad guide, open questions for the reviewer. Exported from the live doc linked at its top. |
| `power_architecture.png` | Block diagram used by the plan. |
| `rc_power_board.kicad_pro` / `.kicad_sch` | KiCad project and the one-sheet A3 schematic (regions A to E + notes). |
| `rc_power.kicad_sym` + `sym-lib-table` | Project symbol library: `REG_MODULE` (VIN, GND, VOUT, EN) and one power symbol per rail. |
| `rc_power_board.pdf` | Plot of the baseline sheet, for review without KiCad. |
| `.kicad-happy.json` | Config for the kicad-happy Claude plugin (analysis output in `analysis/`, gitignored except the manifest). |

## KiCad version

Project version: **KiCad 10.0**. The baseline file was generated in KiCad 7 format (the newest available where it was built); KiCad 10 opens it and upgrades it on save. After the first save in KiCad 10, commit the upgraded files; from then on, everyone working on this board uses 10.0. KiCad 9 and older cannot open a file saved by 10, so confirm the reviewer's version before sending the project (the PDF works for anyone).

## First open in KiCad 10 (checklist)

1. Open `rc_power_board.kicad_pro`. Accept the format-upgrade prompt, then **File > Save**.
2. **Inspect > Electrical Rules Checker > Run ERC.** Not yet run on this baseline (KiCad 7's command-line tool has no ERC). Expected: no errors. Likely warnings: `VBAT_ESC` has no power source (connector-only net, harmless), unconnected EN/NC pins are marked with no-connect flags.
3. Click one wire on each rail and read the net name in the message panel: `VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`, `GND` must all be distinct.
4. **Tools > Assign Footprints**: confirm none show as missing in the KiCad 10 libraries. U1 and U2 are intentionally blank (module footprint TBD).
5. **File > Schematic Setup > Net Classes**: check the four classes and the assignment patterns loaded from the `.kicad_pro`.

## How the baseline differs from the step-by-step guide

The schematic follows `power_board_plan.md` part for part (same references, nets and values). Deliberate differences, each for a reason:

- **Rail symbols:** each rail is a project power symbol whose hidden pin name and Value both equal the rail name, instead of a renamed `power:VCC`. This keeps nets correct in KiCad 7 (pin name) and 8+ (Value) alike.
- **`+6V_BEC`** uses net labels (two connectors only), not a power symbol.
- **U1** value is the inventory part, Pololu D36V50F5, which differs from the plan's 5.1 V / >= 6 A target (open question 4). U1 and U2 footprints are left blank: module header pins are rated 3 A each, so a 1x4 header cannot carry 5.5 A.
- **LED resistors** connect pin-to-pin to their LEDs, so those three nets carry KiCad's auto names (`Net-(D2-A)` and so on) instead of `LED_*` labels.
- **J3, J4** are drawn rotated so pin 1 (GND) sits at the bottom; pin numbering is unchanged.
- **Mounting holes** H1 to H4 (M3) are included from the plan's footprint table.

## Verification so far

Built and checked with KiCad 7.0.11 `kicad-cli` and the kicad-happy analyzer (v2.3.2):

- Netlist: 44 parts, 22 nets; every connection matches the plan's steps 5 to 9.
- Analyzer: U1/U2 detected as switching regulators, U3 as a 3.3 V LDO; no unsourced power rails except `VBAT_ESC` (connector only). Expected draft findings: no datasheets / no MPNs (all TBD), and an EN pull-up warning on U3 (AP2112 EN tied to VIN is the datasheet's normal use).
- Not yet done: ERC in KiCad 10, footprint check against KiCad 10 libraries, any PCB layout.

## Working on this folder with Claude Code

The repo enables the kicad-happy plugin (`.claude/settings.json`); rules for this folder are in `.claude/rules/schematics.md`. Typical asks: "review docs/schematics", "check the power budget against the schematic", "simulate the subcircuits". SPICE needs `ngspice` installed on the host.
