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
2. **Inspect > Electrical Rules Checker > Run ERC.** Never run on this baseline in any KiCad version (KiCad 7's command-line tool has no ERC), so treat its output as the first real check and fix or explain every error. U1/U2 EN pins carry no-connect flags; U3's NC pin is hidden and already no-connect type.
3. Click one wire on each rail and read the net name in the message panel: `VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`, `GND` must all be distinct.
4. **Tools > Assign Footprints**: confirm none show as missing in the KiCad 10 libraries. U1 and U2 are intentionally blank (module footprint TBD).
5. **File > Schematic Setup > Net Classes**: check the four classes and the assignment patterns loaded from the `.kicad_pro`.

## How the baseline differs from the step-by-step guide

The schematic follows `power_board_plan.md` part for part (same references, nets and values). Deliberate differences, each for a reason:

- **Rail symbols:** each rail is a project power symbol whose hidden pin name and Value both equal the rail name, instead of a renamed `power:VCC`. This keeps nets correct in KiCad 7 (pin name) and 8+ (Value) alike.
- **`+6V_BEC`** uses net labels (two connectors only), not a power symbol.
- **U1** value is the inventory part, Pololu D36V50F5, which differs from the plan's 5.1 V / >= 6 A target (open question 4). U1 and U2 footprints are left blank: module header pins are rated 3 A each, so a 1x4 header cannot carry 5.5 A.
- **LED resistors** connect pin-to-pin to their LEDs, so those three nets carry KiCad's auto names (`Net-(D2-A)`, `Net-(D3-A)`, `Net-(D4-A)`) instead of `LED_*` labels.
- **J3, J4** are drawn rotated so pin 1 (GND) sits at the bottom; pin numbering is unchanged.
- **Mounting holes** H1 to H4 (M3) are included from the plan's footprint table.
- **Net names the plan leaves open:** the F2-to-J2 net is named `VBAT_ESC`.
- **Net-class patterns** are `*VBAT*`, `*VIN_CPU`, `*VIN_SENS`, `*+6V_BEC` (plan: `VBAT*`, `VIN_CPU`, ...). KiCad prefixes local-label nets with `/` (`/VBAT_RAW`, `/+6V_BEC`), which the plan's patterns would miss.
- **D1** uses `Device:D_Zener` as a unidirectional TVS, cathode to `VBAT` (the plan now says the same).
- **Shortened values** to fit the sheet: J2 "ESC power (XT60)", J3 "ESC Rx lead (BEC in)", J7 "ESP32-S3 5V", C1/C2-C5 drop "uF"/"low-ESR", C7/C8 "1uF 10V TBD", U1 "D36V50F5 buck TBD (req 5.1V >=6A)".
- **Placeholder footprints the plan doesn't fix** (all ratings TBD, pick real parts before layout): F1/F2 ATO blade holder (`Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin`; F1 must carry about 27-30 A), F3/F4 mini-blade holder (`Fuseholder_Blade_Mini_Keystone_3568`), C1 10 mm radial electrolytic, D1 SMB, FB1 0805, TP1-TP3 1.5 mm pads. J1/J2 use `AMASS_XT60-M`, whose KiCad description says "female": gender TBD.

## Verification so far

Built and checked with KiCad 7.0.11 `kicad-cli` and the kicad-happy analyzer (v2.3.2):

- Netlist (rev with the LED fix): 44 parts, 19 nets. Every net and pin was compared against plan steps 5 to 9 by an independent review; the only single-pin nets are U1/U2 EN and U3 NC (intentionally unconnected). An earlier push of this baseline had all three power LEDs disconnected from their resistors; the review caught it and it is fixed.
- All 7 PWR_FLAGs confirmed attached to their nets; all assigned footprints exist in the KiCad 7 libraries; embedded symbols match the KiCad 7 library pin for pin.
- Net classes: every net resolves to the intended class (checked with KiCad 7's pcbnew API in the review, and with a wildcard emulation after the `*+6V_BEC` fix).
- Analyzer: U1/U2 switching, U3 3.3 V LDO, D2-D4 resistor-limited. Remaining findings are expected for a draft: no datasheets / MPNs (all TBD), U3 EN "missing pull-up" (tied to VIN per AP2112 datasheet), and `VBAT_ESC` "no declared source" (analyzer heuristic; the net has only passive pins, so KiCad's ERC should not flag it).
- Not yet done: ERC in any KiCad version, KiCad 10 file upgrade, footprint check against KiCad 10 libraries, SPICE, any PCB layout.

## Working on this folder with Claude Code

The repo enables the kicad-happy plugin (`.claude/settings.json`); rules for this folder are in `.claude/rules/schematics.md`. Typical asks: "review docs/schematics", "check the power budget against the schematic", "simulate the subcircuits". SPICE needs `ngspice` installed on the host.
