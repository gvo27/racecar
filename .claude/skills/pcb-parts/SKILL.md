---
name: pcb-parts
description: Use when a part for a KiCad board must be chosen, replaced or checked, when a schematic value or BOM field is TBD, when a new load, sensor or module joins the board, when a datasheet must be found and stored, when the owner gives or changes the parts inventory, or before a claim that parts, connectors, harnesses or ratings are compatible. Keywords - BOM, MPN, datasheet, pinout, part selection, compatible connector, crimp, power draw, ripple, inventory, make bom.
---

# Parts manager (choice, datasheet notes, BOM, compatibility)

## Where part data lives (one place for each kind of fact)
| Fact | Place | Rule |
| --- | --- | --- |
| The BOM | Symbol fields in the `.kicad_sch`: `MPN`, `Manufacturer`, `Status`, `Unit cost USD`, `Supplier link`, `BOM Comments` | `make bom` exports `bom.csv` of the board directory (`pcb/<BOARD>/`) with `kicad-cli`. Commit the two files together. Never edit `bom.csv` by hand |
| Parts with no symbol | `docs/pcb/bom_offboard.csv` | Housings, crimps, wire, stock, rivets. Kept by hand |
| Part facts | `docs/datasheets/<kind>_<model>.md`, with the archived PDF, drawing or page beside it | One note for each part model. Each number has its source (page, figure, graph) |
| Inventory | `docs/datasheets/components_list.xlsx` (owner file) and `Status = in hand` in the symbol field | Ask the owner before you write "in hand" |
| Lab stock (bits, blanks, rivets) | The lab file (skill `pcb-lab-config`) | Not part data |

`Status` values: `in hand`, `proposed`, `assumed`, `TBD`. An unknown value is `TBD`. Never write a typical value as a fact.

## Choose a part (fill a blank)
1. **Write the requirement first:** voltage, current (typical, maximum, start), ripple, package, temperature, connector, the rail that feeds it.
2. **Look in the inventory first.** A part in hand that meets the requirement is the first choice.
3. **Then prefer, in this order:**
   - a part family that is already on the board (consistency: one spare serves two positions),
   - an active part (not "not recommended for new designs", not discontinued) with stock at two distributors,
   - a known manufacturer with a full datasheet,
   - margin: voltage rating at least 1.5 times the rail, continuous current at 75 % or less of the rating, a ceramic capacitor checked for DC bias.
4. **Research with official sources.** Manufacturer page and datasheet first (skill `upstream-research`). For price and stock use the kicad-happy distributor skills (`digikey`, `mouser`, `lcsc`, `element14`). They need API keys in user scope. Without keys, read the public product page and write "price not confirmed".
5. **Propose, do not decide.** Give the owner 1 to 3 candidates with the reason for each. Set `Status = proposed`. The owner approves a part.

## Store a datasheet note
Make `docs/datasheets/<kind>_<model>.md` (see `regulator_pololu_d36v50f5.md` for the form). Archive the source document beside it. The kicad-happy skill `datasheets` can extract a PDF into structured data. The note must contain, where the part has them:
- Supply range, typical and maximum current, start current and its duration, standby current.
- Ripple limit or output ripple. Dropout, efficiency, and maximum output current against input voltage (read from the graph, say "about").
- Absolute maximum ratings. Protection that the part has (reverse voltage, over-current, thermal).
- Pinout with pin numbers, the view (top or bottom), and the function of each pin. Default state of enable and status pins, with internal pull resistors.
- Mechanical data: body size, hole and pad positions, header pitch, mounting holes, height, parts on the underside.
- The connector on the part, the mating housing and contact, the wire gauge range, the usual harness, wire colors.
- Signals: type (PWM, I2C, UART, analog), voltage level, frequency or address, pull-ups.
- What the note does not know: write "not in the datasheet" or `TBD`.

A new sensor also needs `.claude/rules/<sensor>.md` (repo rule).

## Check compatibility (run for each schematic or board review)
For each item, find the two values in the notes and write the result with the numbers. "Fits" needs the numbers.
1. **Rail budget:** sum of the maximum load currents on each rail against the regulator output at the minimum input voltage. Add the start current of the largest load.
2. **Regulator input:** minimum battery voltage minus the path drop against output voltage plus dropout at the load.
3. **Voltage ratings:** each capacitor, diode and IC against the maximum rail voltage (the full battery voltage for input parts).
4. **Ripple:** the regulator output ripple against the strictest load on the rail.
5. **Connector current:** each pin against its rating, for the wire gauge in use. Write the percentage of the rating.
6. **Mating parts:** board header against housing, contact and wire gauge. Pin order against the device pinout, the crimp table and the harness colors.
7. **Signals:** logic levels of the two ends, pull-ups present one time and to the correct rail, bus address conflicts.
8. **Footprint against package:** the footprint in the schematic against the package of the chosen MPN. Pad numbers of a module footprint against the manufacturer drawing, in the correct view.
9. **Mechanical:** body size and height against neighbors, parts on the underside of a module against copper below it, hole sizes against the lab drill set (skill `pcb-lab-config`).
10. **Fuse:** continuous load at 75 % or less of the rating, the I2t of the inrush against the fuse, the holder rating, copper sized for the fuse rating.
11. **Lifecycle and stock:** each MPN active. Write the date of the stock check.

## After a change
1. Change the symbol fields in the schematic (kicad-happy `bom` skill script `edit_properties.py`, or the KiCad Symbol Fields Table).
2. `make bom`, then `make pcb-test` (it fails if `bom.csv` is old, if a symbol has no MPN field or an invalid `Status`).
3. If a board exists: `make pcb-build PCB_BUILD_ARGS=--sync-fields`, then `make pcb-check`.
4. Update the budget numbers in the plan and the rules file if a load or a regulator changed.

## Report
List: parts changed (old, new, reason), each `TBD` that stops the build, each compatibility item that failed or has less than 20 % margin, and the facts that need an owner measurement or a bench check.
