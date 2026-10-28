# Power distribution board (baseline schematic)

Draft KiCad project for the car's power board: 2S LiPo in, four rails out (`VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`), common `GND`. It is a **review draft**: every value marked `TBD` is unconfirmed (project rule: no unconfirmed parameters).

| File | What it is |
| --- | --- |
| `power_board_plan.md` | The spec: rails, power budget, trace widths, step-by-step KiCad guide, open questions for the reviewer. Exported from the live doc linked at its top. |
| `power_architecture.png` | Block diagram used by the plan. |
| `rc_power_board.kicad_pro` / `.kicad_sch` | KiCad project and the one-sheet A3 schematic (regions A to F + notes). |
| `rc_power.kicad_sym` + `sym-lib-table` | Project symbol library: `D36V50F5` (all 12 module pins), `REG_MODULE` (generic VIN/GND/VOUT/EN, used by U2) and one power symbol per rail. |
| `rc_power_board.pdf` | Plot of the baseline sheet, for review without KiCad. |
| `.kicad-happy.json` | Config for the kicad-happy Claude plugin (analysis output in `analysis/`, gitignored except the manifest). |

## KiCad version

Project version: **KiCad 10.0**. The baseline file was generated in KiCad 7 format (the newest available where it was built); KiCad 10 opens it and upgrades it on save. After the first save in KiCad 10, commit the upgraded files; from then on, everyone working on this board uses 10.0. KiCad 9 and older cannot open a file saved by 10, so confirm the reviewer's version before sending the project (the PDF works for anyone).

## First open in KiCad 10 (checklist)

1. Open `rc_power_board.kicad_pro`. Accept the format-upgrade prompt, then **File > Save**.
2. **Inspect > Electrical Rules Checker > Run ERC.** Never run on this baseline in any KiCad version (KiCad 7's command-line tool has no ERC), so treat its output as the first real check and fix or explain every error. Intentional no-connects: U1 VRP (2 pins), U2 EN; U3's NC pin is hidden and already no-connect type. Expect "symbol doesn't match library" warnings for the embedded stock symbols where KiCad 10's libraries changed; they're harmless (update from library or exclude). (The kicad-happy analyzer separately flags U1 EN/PG as missing pull-ups: EN's is inside the module, PG uses the ESP32's internal pull-up.)
3. Click one wire on each rail and read the net name in the message panel: `VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`, `GND` must all be distinct.
4. **Tools > Assign Footprints**: confirm none show as missing in the KiCad 10 libraries. U2 is intentionally blank (module TBD). J1/J2 use the 2.5 mm2 wire-pad placeholder, too small for 12 AWG (3.3 mm2).
5. **File > Schematic Setup > Net Classes**: check the four classes and the assignment patterns loaded from the `.kicad_pro`.

## How the baseline differs from the step-by-step guide

The schematic follows `power_board_plan.md` part for part (same references, nets and values). Deliberate differences, each for a reason:

- **Rail symbols:** each rail is a project power symbol whose hidden pin name and Value both equal the rail name, instead of a renamed `power:VCC`. This keeps nets correct in KiCad 7 (pin name) and 8+ (Value) alike.
- **`+6V_BEC`** uses net labels (two connectors only), not a power symbol.
- **U1** is the inventory part, Pololu D36V50F5, drawn with all 12 pins and soldered to the board on its 2x6 0.1 in grid (footprint `PinHeader_2x06_P2.54mm_Vertical`). Pin numbers: 1 PG, 2 EN, 3-4 VRP, 5-6 VIN, 7-10 GND, 11-12 VOUT (module column k = pins 2k+1 top row, 2k+2 bottom row). Check this against Pololu's dimension drawing before layout. Each header pin is rated 3 A, so VIN, VOUT and GND use their pin pairs. Its 5.0 V / 5.5 A rating differs from the plan's 5.1 V / >= 6 A target (open question 4). VRP is unused: the sensor buck stays on `VBAT` through F4.
- **U1 EN / PG (region F, proposal):** EN goes to Q1 (2N7002), whose gate is `ESP_SHDN` with R4 (100k) holding it low, so U1 is on by default. Driving `ESP_SHDN` high power-cycles U1 (the ESP32 loses power, Q1 turns off, U1 restarts and the Pi 5 reboots); it is not a latching shutdown. Use non-strapping GPIOs with no reset pull-up for both signals. PG goes to J5. The EN approach is open question 13 (also at the top of the PR).
- **J5** has 5 pins: THROTTLE_PWM, STEER_PWM, U1_PG, ESP_SHDN, GND. GPIOs for the two new signals are TBD until firmware adds them (pins.h and the README pin table together).
- **J1/J2** are wire pads for T-plug pigtails (12 AWG bare ends), not board connectors.
- **J6/J7** are 2-wire USB-C pigtails into the Pi 5 and the ESP32's left USB-C port, so each board's own USB-C input protection is used. The pigtails are 24 AWG; keep them short (open question 14).
- **LED resistors** connect pin-to-pin to their LEDs, so those three nets carry KiCad's auto names (`Net-(D2-A)`, `Net-(D3-A)`, `Net-(D4-A)`) instead of `LED_*` labels.
- **J3, J4** are drawn rotated so pin 1 (GND) sits at the bottom; pin numbering is unchanged.
- **Mounting holes** H1 to H4 (M3) are included from the plan's footprint table.
- **Net names the plan leaves open:** the F2-to-J2 net is named `VBAT_ESC`.
- **Net-class patterns** are `*VBAT*`, `*VIN_CPU`, `*VIN_SENS`, `*+6V_BEC` (plan: `VBAT*`, `VIN_CPU`, ...). KiCad prefixes local-label nets with `/` (`/VBAT_RAW`, `/+6V_BEC`), which the plan's patterns would miss.
- **D1** uses `Device:D_Zener` as a unidirectional TVS, cathode to `VBAT` (the plan now says the same).
- **Shortened values** to fit the sheet: J3 "ESC Rx lead (BEC in)", J6/J7 "USB-C > Pi 5 / ESP32", D1 "TVS unidir. >=9V TBD", C1/C2-C5 drop "uF"/"low-ESR", C7/C8 "1uF 10V TBD", U1 "Pololu D36V50F5 buck (req 5.1V >=6A TBD)".
- **Placeholder footprints the plan doesn't fix** (all ratings TBD, pick real parts before layout): F1/F2 ATO blade holder (`Fuseholder_Blade_ATO_Littelfuse_Pudenz_2_Pin`; F1 must carry about 27-30 A), F3/F4 mini-blade holder (`Fuseholder_Blade_Mini_Keystone_3568`), C1 10 mm radial electrolytic, D1 SMB, FB1 0805, TP1-TP3 1.5 mm pads. J1/J2 use `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm`, KiCad's largest stock wire pad; 12 AWG needs a bigger hole, so the pad is TBD.

## Verification so far

Built and checked with KiCad 7.0.11 `kicad-cli` and the kicad-happy analyzer (v2.3.2):

- Netlist (D36V50F5 revision): 46 parts, 23 nets. The only single-pin nets are U1 VRP x2, U2 EN and U3 NC (intentionally unconnected). An independent review compared every net with plan steps 5 to 9 on the previous revision and caught all three power LEDs disconnected from their resistors in the first push; that is fixed. This revision's U1, Q1, R4 and J5 nets were checked against the netlist, and a fresh independent review was run on it (see the PR).
- All 7 PWR_FLAGs confirmed attached to their nets; all assigned footprints exist in the KiCad 7 libraries; embedded symbols match the KiCad 7 library pin for pin.
- Net classes: every net resolves to the intended class (checked with KiCad 7's pcbnew API in the review, and with a wildcard emulation after the `*+6V_BEC` fix).
- Analyzer: U1/U2 switching, U3 3.3 V LDO, D2-D4 resistor-limited. Remaining findings are expected for a draft: no datasheets / MPNs (all TBD), "missing pull-up" on U1 EN (inside the module), U1 PG (ESP32 internal pull-up) and U3 EN (tied to VIN per AP2112 datasheet), and `VBAT_ESC` "no declared source" (analyzer heuristic; the net has only passive pins, so KiCad's ERC should not flag it).
- Not yet done: ERC in any KiCad version, KiCad 10 file upgrade, footprint check against KiCad 10 libraries, SPICE, any PCB layout.

## Working on this folder with Claude Code

The repo enables the kicad-happy plugin (`.claude/settings.json`); rules for this folder are in `.claude/rules/schematics.md`. Typical asks: "review docs/schematics", "check the power budget against the schematic", "simulate the subcircuits". SPICE needs `ngspice` installed on the host.
