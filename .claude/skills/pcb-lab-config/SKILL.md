---
name: pcb-lab-config
description: Use when the lab machine, drill or end-mill set, isolation bits, cut depth, copper stock, rivets, dowels or another lab fact for board manufacture is given, changed, questioned or missing, when the owner sends a photo or file of lab inventory, when the board moves to a different mill or lab, or before a check or a design step reads a lab limit. Keywords - lab tech, mill, Carvera, bits, stock, inventory, milling.toml, machine limits.
---

# Lab config (one file for the machine and the lab inventory)

All lab facts that the board depends on are in one file: `milling.toml` in the lab directory. The checks read it: `tools/milling_check.py` and `tools/fab_export.py` in the lab directory, `pcb/tools/check_board.py` and `pcb/tools/placement.py`. Documents cite it. No tool and no document keeps its own copy of a lab value.

A move to a different machine or a change of inventory is then one change of this file, followed by the checks.

## Lab directory (one pointer)
- The `lab:` line of `.claude/CLAUDE.md` is the only place that names the lab directory. Documents, rules, skills and agents write "the lab directory" and point to that line. They do not write the path.
- Code reads the line through `pcb/tools/lab.py`. The environment variable `LAB_DIR` overrides it.
- Contents: `milling.toml` (the lab file), `README.md` (index), `example/` (the lab CAM file and its `README.md`), `example/fusion_export/` (setup sheet, tool library, sketch DXFs and screenshots that the owner exports from the CAM tool).
- `design_rules.toml` in the lab directory is the mill tuning file: the limits that a board for this mill must keep (horizontal error, cut spacing, clearance, track widths, component gap, exceptions, parts that are not on the board). `milling.toml` holds facts of the machine. `design_rules.toml` holds design choices that follow from the accuracy of the machine. It uses the same `status` and `source` fields. After a change run `make pcb-all BOARD=mill`.
- The lab directory holds lab facts and lab files only. Board files stay in the board directory.
- To use the lab in a different project or repo, copy the lab directory and set the `lab:` line there.

## File format
- One TOML table for each fact. Each table has `status` and `source`.
- `status = "confirmed"`: the value comes from the machine file, a manufacturer document, a measurement, or a dated statement of the owner or the lab tech.
- `status = "assumed"`: all other values. An assumed value stays assumed until a person confirms it.
- `source`: where the value comes from, with the date for a statement, a photo or a measurement.
- `[machine]` gives manufacturer, model, axes, work area and the CAM tool. `[inventory.*]` tables list stock that does not set a limit directly (rivet kit, blanks).
- `tools/milling_check.py` (lab directory) `load_limits` rejects a limit without `status` or `source`.

## Fill or change the file
1. **Collect the inputs.** Ask the owner for: machine manufacturer and model, CAM tool, the machine or CAM file if one exists, bit and drill inventory (a photo is sufficient), copper stock (manufacturer, part number, copper weight, size), rivet or via method, the fixture method (dowels, tape, clamps).
2. **Use official sources first.** Read the manufacturer page or manual for the machine and for each named tool (skill `upstream-research`). A lab CAM file is stronger than a manufacturer default, because it holds the values that the lab uses. Read it (`example/README.md` in the lab directory shows how to read a Fusion `.f3z`). Put the CAM exports of the owner in `example/fusion_export/`.
3. **Fill the gaps with usual values.** For a value that no source gives, use the usual value for this machine class and for a college robotics lab. Mark it `assumed`. Write in `source` that it is a usual value and who must confirm it. The table below gives start values.
4. **Measured value before label.** A caliper measurement of the real part replaces a label or a catalog value. Example: the rivet bag label was the inner diameter, not the outer diameter.
5. **Write the file.** Change only the tables that the new fact changes. Keep the old value and its date in `source` when a confirmed value changes.
6. **Run the checks.** `make pcb-test pcb-check pcb-mill-check`. A new failure after a limit change is a finding about the board, or a question for the lab tech. Never set a limit to the value that makes the board pass.
7. **Update the readers.** Search for the old value (`grep -rn` in `docs/`, `.claude/rules/`, `.claude/skills/`). Replace each copy with a pointer to the lab file.

## Usual values for gaps (always `assumed`)
| Fact | Usual value | Note |
| --- | --- | --- |
| Isolation bit | 30 degree V-bit, 0.2 mm tip, or 60 degree, 0.1 mm tip | Fusion "Taper angle" is the angle per side (from the tool axis): included angle = 2 x taper. The tool drawing in the Fusion tool library shows it. For a different CAM tool, check both readings |
| Cut depth | copper thickness + 0.03 to 0.05 mm | 1 oz copper is 0.035 mm, 2 oz is 0.070 mm |
| Depth error | 0.05 mm without surface probing, 0.02 mm with probing | 0 only on the owner's statement |
| Drill set | 0.8, 1.0, 1.2, 1.5 mm | Ask for the real set before footprints get their drills |
| End mill | 3.175 mm (1/8 in) flat, sometimes 0.8 and 2.0 mm | Smallest bored hole = tool + 0.125 mm |
| Via method | wire or rivet, soldered on the two sides | Holes are not plated |
| Annular ring | 0.45 mm minimum | |
| Track and gap | 0.5 mm track, 0.4 mm gap | Coarser than a fab house |
| Edge clearance | 0.5 mm | |
| Stock | FR-4, 1 oz, 1.6 mm, single or double sided | Read the label on the blank |

## Report
Put this block at the top of each report that uses the file:
1. **Owner feedback necessary:** each `assumed` table that changes a check result, with its value, and the person who can confirm it (owner or lab tech).
2. Values that changed in this session: old value, new value, source.
3. Check results after the change.

## Rules
- Holes for milling: when a size is not sure, choose the smaller hole. The lab makes it wider in a second pass. A hole that is too large cannot be repaired.
- A hole between the largest drill and the smallest bored hole cannot be made. Change the footprint drill, not the limit.
- The lab tech's instructions and the lab CAM file override the usual values and this skill. When they arrive, change the file and the skills `pcb-lab-config` and `pcb-milling-check` in the same change.
- This file holds lab facts only. Part facts go to `docs/datasheets/` (skill `pcb-parts`). Fab-house limits are not lab facts: they come from the fab house (kicad-happy skills `jlcpcb`, `pcbway`).
