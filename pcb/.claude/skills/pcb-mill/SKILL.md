---
name: pcb-mill
description: Use when a .kicad_pcb in pcb/ is created, changed, re-routed or reviewed, before any claim that a board is millable, or when a lab fact (machine, bits, drills, end mills, cut depth, copper stock, rivets, dowels, CAM file) is given, changed, questioned or missing. Checks the board against the lab mill limits and keeps the lab file milling.toml correct. DRC-clean does not mean millable.
---

# Lab mill: lab file and milling check

KiCad DRC checks the numbers in the KiCad project. It does not know the cutter. This skill keeps the lab facts in one file and checks the board against them.

## Lab directory and lab file
- The lab directory is key `dir` of `pcb/config/lab.toml`. Code reads it through `pcb/libraries/lab.py`. The environment variable `LAB_DIR` overrides it. Documents write "the lab directory". They do not write the path.
- `milling.toml` in the lab directory holds the facts of the machine and the lab inventory. `design_rules.toml` in the lab directory (or in the board directory) holds the design limits that follow from the machine accuracy. `milling_waivers.toml` holds the waivers. Index: `README.md` in the lab directory.
- Each table has `status` and `source`. `confirmed`: from the machine file, a manufacturer document, a measurement, or a dated statement of the owner or the lab tech. `assumed`: all other values. An assumed value stays assumed until a person confirms it. `load_limits` in `tools/milling_check.py` rejects a limit without `status` or `source`.
- No tool, document or skill keeps a copy of a lab value. Write the key name (for example `drill_set`), not the value.

## Fill or change the lab file
1. Collect the inputs from the owner: machine and model, CAM tool and CAM file, bit and drill inventory (a photo is sufficient), copper stock, rivet or via method, fixture method.
2. Read the official sources first: the manufacturer manual (skill `upstream-research`), then the lab CAM file (`example/README.md` in the lab directory). The lab CAM file wins over a manufacturer default.
3. For a gap, use a generic start value from `references/gap-defaults.md`. Set `status = "assumed"`. Write in `source` who must confirm it.
4. A caliper measurement of the real part replaces a label or a catalog value.
5. Change only the tables that the new fact changes. When a confirmed value changes, keep the old value and its date in `source`.
6. Run the checks (see Verify). After a change of `design_rules.toml`, run `make pcb-all BOARD=src`.
7. Search for copies of the old value (`grep -rn` in `docs/`, `.claude/`, `pcb/.claude/`). Replace each copy with the key name.

## Milling check
- Run `make pcb-mill-check BOARD=<board>`. It runs `tools/milling_check.py` of the lab directory in the KiCad image. It writes `milling_check.json` to the review directory of the board (`REVIEW_DIR` in the Makefile). Exit code 0 = no errors, 1 = errors, 2 = the check could not run.
- Rule ids, checks and severities: `references/mill-rules.md`.
- Loop:
  1. Run the check.
  2. Triage each finding as real or false positive. A false positive gets a waiver in `milling_waivers.toml`: rule id, location (ref, net or xy), reason in one sentence, who, date. Never waive MILL-FCU-THT or MILL-RIVET-ACCESS. MILL-DEPTH is a question about the limits for the lab tech, not a board finding.
  3. Fix the real findings. First try fixes that do not move parts: neck a track (never below its net-class width), change a zone clearance, change a pad shape. If one region keeps failing, lay out the region again or swap equivalent pins through the schematic. Do not stack local patches or add rivets to escape a crowded area.
  4. Run again until there are 0 unwaived errors. Report the open errors, not a percentage.

## Rules
- Never change a limit or a design rule to make a board pass. Add a waiver only for a false positive (Loop, step 2). A limit change needs a statement of the owner or the lab tech.
- When a hole size is not sure, choose the smaller hole. The lab can make it wider. A hole that is too large cannot be repaired.
- A hole between the largest drill (`drill_set`) and `milled_hole_min` cannot be made. Change the footprint drill, not the limit.
- Never write "millable" or "ready to mill". Write "passes the milling check with the assumed limits" until the lab tech confirms the limits and the owner signs off.
- The instructions of the lab tech and the lab CAM file override the generic values. When they arrive, change the lab file. Change this skill only when the procedure changes.
- Part facts go to `docs/datasheets/` (skill `pcb-parts`). Fab-house limits come from the fab house (skill `pcb-fab`).

## Report
1. **Owner or lab-tech questions:** each `assumed` table that changes a check result, its key, and who can confirm it.
2. Lab values changed in this session: key, old value, new value, source.
3. Milling check: **errors** (unwaived), **waived** (with the reason), the MILL-GAP-BIT areas.
4. Tools to stage: the "TOOLS TO STAGE" list of the check output (`tools` in the JSON). It gives each drill size with its hole count, the end mill and each isolation bit with its exact spec. The owner stages the tools between rounds. Give this list with each board for the lab.

## Verify
- `make pcb-test`: lab tools and `pcb/libraries` tests, including `load_limits`.
- `make pcb-check BOARD=src` and `make pcb-mill-check BOARD=src`: give the counts and every error from the output.
- Claim a result only with the command output from this session. A check that you did not run is "not run".
