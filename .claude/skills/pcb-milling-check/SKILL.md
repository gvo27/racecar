---
name: pcb-milling-check
description: Use when a .kicad_pcb in docs/schematics/ is created, changed, re-routed or reviewed, or before any claim that the power board is millable. Checks the board against the Makera Carvera isolation-milling limits (V-bit cut width at depth, copper gaps, drill set, annular ring, unplated-hole rules, slivers, islands). DRC-clean does not mean CNC-millable.
---

# PCB milling check (rev A, Makera Carvera)

KiCad DRC checks the numbers in `rc_power_board.kicad_pro` and `.kicad_dru`. It does not know the cutter. This skill checks the board against the tool that removes the copper.

## Run
- `make pcb-mill-check`. The check runs `docs/schematics/tools/milling_check.py` in the pinned KiCad 10 image.
- Output: `docs/schematics/review/milling_check.json` and a text summary. Exit code 0 = no errors, 1 = errors, 2 = the check could not run.
- Limits: `docs/schematics/milling.toml`. Every value there is `confirmed` or `assumed`. Assumed values stay assumed until the lab tech confirms them. Do not change a limit to make a board pass.

## What it checks (rule ids)
| Id | Check | Severity |
| --- | --- | --- |
| MILL-GAP | Every copper-to-copper gap on one layer (track, pad, via, zone fill; same footprint included) between different nets >= the narrowest isolation bit's cut width at worst-case depth (depth max + depth error): `w = tip + 2 * d * tan(angle / 2)` | error |
| MILL-GAP-BIT | Gaps that only some bits can cut. Lists the area and the bits that fit, so the CAM step uses the right bit there | warning |
| MILL-DEPTH | Min depth (depth min - depth error) >= copper thickness, so each cut goes through the copper | error |
| MILL-DRILL | Every hole is in the drill set, or is > the largest drill and >= the smallest end mill (milled) | error |
| MILL-ANNULAR | Annular ring >= the configured minimum on every THT pad and via | error |
| MILL-FCU-THT | No F.Cu track or zone fill touches a THT pad (holes are not plated; the joint is on B.Cu) | error |
| MILL-VIA | Every via has the rivet drill and pad from the config | error |
| MILL-SLIVER | Copper narrower than the min track width, made by zone fill | warning |
| MILL-ISLAND | Zone islands with no net connection | warning |
| MILL-EDGE | Copper-to-board-edge distance >= the configured edge clearance | error |
| MILL-RIVET-ACCESS | A rivet via must be solderable on both sides: no via inside the courtyard of an F-side part (its body covers the top joint) or of a B-side part | error |
| MILL-CONN-EDGE | Each connector (J*) courtyard is within the configured distance of the board edge (wire entry outward) | warning |

## Loop: run, triage, fix, run again
1. **Run** the check.
2. **Triage** each finding as real or false positive. A false positive needs a waiver in `docs/schematics/milling_waivers.toml`: rule id, location (ref/net/xy), the reason in one sentence, who, date. The check reports waived findings in their own group; it never hides them. Never waive MILL-FCU-THT or MILL-RIVET-ACCESS. MILL-DEPTH is a finding about the limits (the lab tech decides), not about the board.
3. **Fix** the real findings. First try fixes that do not move parts: neck a track down (never below its net-class width), change a zone clearance, change a pad shape in the board copy. If one region keeps failing, re-lay that whole region, or swap equivalent pins through the schematic. Do not stack local patches or add rivets to escape a crowded area.
4. **Run again** until there are 0 unwaived errors. A board that is "nearly clean" is not done: report the open errors, not a percentage.

## Report format
Three groups: **errors** (unwaived), **waived** (with the reason), **owner/lab-tech questions** (limits that are assumed and change the result, for example MILL-DEPTH). Add the MILL-GAP-BIT areas.

## Rules for agents
- Run it after every board change and before any review request. Report the counts, every error and the MILL-GAP-BIT areas.
- Never claim "millable" or "ready to mill". The most you can say is "passes the milling check with the assumed limits", until the lab tech confirms the limits and the owner signs off.
- Fix a finding on the board (move, re-route, change a footprint through the schematic). Do not weaken `milling.toml`.
- The lab tech's machine and CAM instructions override this file. When they arrive, update `milling.toml` and this skill in the same change.
