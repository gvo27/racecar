# Lab directory: in-house isolation milling (Makera Carvera)

This directory holds the facts and files of one lab: the mill, its tools, the copper stock, the rivet kit and the lab CAM template. It also holds the mill tools and the waiver list of the milling check. It holds no board files. A board project reads it through one pointer: the `lab:` line of `.claude/CLAUDE.md`. In this repo, the board tools read that line through `pcb/libraries/lab.py`. The environment variable `LAB_DIR` overrides it.

## Contents

| Path | Content |
| --- | --- |
| `milling.toml` | The lab file: milling limits (cut depth, isolation bit, drill set, end mill, bored hole, via, stock, dowels), the machine and the lab inventory. Each value has `status` (`confirmed` or `assumed`) and `source`. The checks read it. Keep it current with the skill `pcb-lab-config` |
| `design_rules.toml` | The mill tuning file: the design rules for a board that this lab mills. See "Tune a prototype" below |
| `review/` | Review files of the mill board `pcb/mill` (`make pcb-review BOARD=mill`, `make pcb-mill-check BOARD=mill`) and `README.md` with the results |
| `milling_waivers.toml` | The waiver list for the milling check (skill `pcb-milling-check`) |
| `tools/milling_check.py`, `tools/fab_export.py` | The mill tools: the milling check of a board against the lab file, and the fab export (DXF, Excellon) in the frame of the lab CAM template. Their tests are `tools/test_*.py`. They run in the KiCad image (`make pcb-mill-check`, `make pcb-fab`, `make pcb-test`) and import `lab.py`, `paths.py` and `placement.py` from `pcb/libraries/`. `pcb/libraries/placement.py` loads the board data from `placement.py` in the board directory (for example `pcb/mill/placement.py`) |
| `example/README.md` | Facts read from the lab CAM file, the Fusion exports of the owner, and how to read a `.f3z` on Linux |
| `example/Pcb DXF's amd copper plate.f3z` | The lab's calibrated Fusion 360 CAM template (demo panel of 6 boards, setups A, B and C) |
| `example/demo_toolpaths_setupB.png` | Decoded toolpaths of setup B of the demo panel |
| `example/fusion_export/` | Fusion exports of the owner (2026-11-15): setup sheets of setups A, B, C and of all setups, tool library, sketch DXFs, screenshots |

## Tune a prototype

The mill is not accurate in X and Y. The board `pcb/mill` is a coarse copy of the rev1 board for this mill. `design_rules.toml` holds all values that make it coarse. To change the board for the next prototype:

1. Run `make pcb-fab BOARD=mill` and mill the board from `build/fab/mill/` (DXF for F.Cu, B.Cu and Edge.Cuts, Excellon drill file, in the frame of the lab CAM template). The parts list is `pcb/mill/bom.csv`.
2. Examine the board: bridges between nets, copper that lifted, pads that the cut damaged, holes that are off center, joints that were hard to solder. Use the symptom table below.
3. Edit `design_rules.toml`. Set `status` and `source` of each value that you change (for example `status = "confirmed"`, `source = "lab tech 2026-11-20, prototype 1"`).
4. Run `make pcb-all BOARD=mill`. It makes the schematic variant, writes the rules into the KiCad project, builds the board from `pcb/mill/placement.py`, routes it, writes the fab outputs and the review files, and runs the checks.
5. Run `make pcb-mill-check BOARD=mill`. Errors stop the board. Warnings list the thin copper and the gaps that a footprint fixes.
6. If a check fails, the parts or the planned zones do not fit the new values. Change `pcb/mill/placement.py`, then go to step 4.
7. Commit `design_rules.toml`, `pcb/mill/` and `review/`.

Rules for the loop:
- `make pcb-all` builds the board again from `placement.py` with `--force`. Manual edits of `pcb/mill/rc_power_board.kicad_pcb` in the KiCad GUI are lost. Put each change into `placement.py` or `design_rules.toml`.
- Do not edit the mill schematic, the net classes of the `.kicad_pro` or the `.kicad_dru` by hand. `make pcb-sch` and `make pcb-rules` make them.
- Machine facts (bit, cut depth, drills, stock) are in `milling.toml`, not in the tuning file.
- Do not tune a release in `pcb/releases/`. It has its own copy of the design rules.

What to change for each symptom:

| Symptom on the milled board | Key to change | Note |
| --- | --- | --- |
| Bridges, or cuts that touch the wrong copper | `horizontal_error` up, then `clearance` up to at least cut width + 2 x `horizontal_error` | Above 0.8 mm clearance the 1.3 mm tracks do not fit between XH pins: make `[netclass.*] track_width` smaller too |
| Copper areas too near each other | `zone_clearance` | Pours and planned zones. Areas with a smaller gap are in `pcb/mill/placement.py` (`_NEAR`, `_NEAR_GND`, `_FINE`) |
| Thin tracks lift or break | `[netclass.Default] track_width`, `cut_spacing_min` | `MILL-CUT-SPACING` lists copper below `cut_spacing_min` - `clearance` |
| Thin pour copper lifts | `zone_min_width` | 1.5 mm removes the GND copper between the XH pins and the board edge |
| Parts too close to cut between or to solder | `component_gap` | Pad to pad on different nets. Needs new positions in `pcb/mill/placement.py` |
| Pads lift during hand soldering | `annular_target` | Only pads of different nets limit the ring. XH headers, modules, C9 and the four F1 pads at the holder hole keep 0.45 mm |
| A part is too small for the mill | `[parts.footprint]` | A different footprint on the mill board. Needs a position in `placement.py` |
| A part must be left out | `[parts] exclude` | |
| Headers are not fitted for one round | `[parts.wire]` | Temporary. Remove the table to get the headers back |
| A footprint has a gap that cannot grow | `[[exception]]` | The checks list these gaps as `MILL-GAP-FIXED` |

| Key | Effect |
| --- | --- |
| `horizontal_error` | Position error of a cut for each side. The milling check needs gap >= cut width + 2 x this value (`MILL-GAP`). It is used for copper gaps only, not for the edge clearance, the annular ring or the holes. If you raise it, raise `clearance` and `zone_clearance` to at least cut width + 2 x this value |
| `cut_spacing_min` | Smallest distance between the centers of two isolation gaps. Copper between two gaps must be `cut_spacing_min` - `clearance` wide. `MILL-CUT-SPACING` lists thinner copper |
| `clearance` | Copper gap for tracks and pads. Set it to at least cut width + 2 x `horizontal_error` |
| `zone_clearance` | Copper gap that the pours and the planned zones keep from other copper (2.0 mm: the "2 mm copper gap wherever possible" rule). A zone in `pcb/mill/placement.py` can have a smaller value where 2 mm leaves no copper (`_NEAR`, `_FINE`) |
| `track_min` | Hard minimum track width |
| `[netclass.*] track_width` | Target track width of each net class. A track is narrower only where a pad gives no room |
| `zone_min_width` | Smallest width of pour copper |
| `component_gap` | Smallest gap between pads of two different parts on different nets (`MILL-COMP-GAP`) |
| `module_gap`, `edge_clearance`, `edge_band` | Module courtyard gap, copper to board edge, router band along the edge |
| `annular_min`, `annular_target` | Smallest annular ring, and the ring that a THT pad gets when its part has room (hand soldering). Only pads of different nets limit the ring. A pad next to an unplated hole of its part keeps its gap to the hole (F1). A part with an `[[exception]]` keeps its pads |
| `[[exception]]` | A part whose footprint fixes a smaller gap (`ref` or a `refs` list). `clearance` is that gap. `own_pads = true` (pin headers): only the pads of the part are that close, tracks and zones keep the board clearance. `zones = true` (U3): planned zones and pours can also use the lower clearance at all its pads. Use one of the two forms |
| `[parts] exclude` | Parts of the schematic that are not on the board |
| `[parts.footprint]` | Parts that have a different footprint on this board (same value). `make pcb-sch` writes it into the mill schematic. A new footprint needs a position in `pcb/mill/placement.py` |
| `[parts.wire]` | Temporary: JST XH headers that become wire solder pads (`refs`, `reason`). Same pads and positions as the header, no part in the BOM. Remove the table to get the headers back |

The values are start values with `status = "assumed"`. `make pcb-rules BOARD=mill` prints the assumed keys. A value must not be below the lab limit of the same name in `milling.toml`.

## Open items
- `design_rules.toml`: all values are `assumed`. The lab tech must confirm the horizontal error of the mill and the reading of "2 mm between cuts" (see `review/README.md`).

- The post `Carvera.cps` and the NC code of the setups: not received.
- `milled_hole_min` (3.3 mm) is `assumed`: the lab tech must confirm it.

## Use this lab in another project

1. Copy this directory into the other repo.
2. Add a `lab:` line with the new path to the `.claude/CLAUDE.md` of that repo.
3. Copy the skills `pcb-lab-config` and `pcb-milling-check`, and `lab.py` from `pcb/libraries/`. The mill tools come with this directory. They find `lab.py` at `pcb/libraries/` of the repo root.
4. Run the milling check on the board of that project.

For a different lab or mill, make a new lab directory with the skill `pcb-lab-config`, then change the `lab:` line.
