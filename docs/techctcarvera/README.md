# Lab directory: in-house isolation milling (Makera Carvera)

This directory holds the facts and files of one lab: the mill, its tools, the copper stock, the rivet kit and the lab CAM template. It also holds the mill tools and the waiver list of the milling check. It holds no board files. A board project reads it through one pointer: the `lab:` line of `.claude/CLAUDE.md`. In this repo, the board tools read that line through `pcb/tools/lab.py`. The environment variable `LAB_DIR` overrides it.

## Contents

| Path | Content |
| --- | --- |
| `milling.toml` | The lab file: milling limits (cut depth, isolation bit, drill set, end mill, bored hole, via, stock, dowels), the machine and the lab inventory. Each value has `status` (`confirmed` or `assumed`) and `source`. The checks read it. Keep it current with the skill `pcb-lab-config` |
| `design_rules.toml` | The mill tuning file: the design rules for a board that this lab mills. See "Tune a prototype" below |
| `review/` | Review files of the mill board `pcb/mill` (`make pcb-review BOARD=mill`, `make pcb-mill-check BOARD=mill`) and `README.md` with the results |
| `milling_waivers.toml` | The waiver list for the milling check (skill `pcb-milling-check`) |
| `tools/milling_check.py`, `tools/fab_export.py` | The mill tools: the milling check of a board against the lab file, and the fab export (DXF, Excellon) in the frame of the lab CAM template. Their tests are `tools/test_*.py`. They run in the KiCad image (`make pcb-mill-check`, `make pcb-fab`, `make pcb-test`) and import `lab.py`, `paths.py` and `placement.py` from `pcb/tools/` |
| `example/README.md` | Facts read from the lab CAM file, the Fusion exports of the owner, and how to read a `.f3z` on Linux |
| `example/Pcb DXF's amd copper plate.f3z` | The lab's calibrated Fusion 360 CAM template (demo panel of 6 boards, setups A, B and C) |
| `example/demo_toolpaths_setupB.png` | Decoded toolpaths of setup B of the demo panel |
| `example/fusion_export/` | Fusion exports of the owner (2026-11-15): setup sheets of setups A, B, C and of all setups, tool library, sketch DXFs, screenshots |

## Tune a prototype

The mill is not accurate in X and Y. The board `pcb/mill` is a coarse copy of the rev A board for this mill. `design_rules.toml` holds all values that make it coarse. To change the board for the next prototype:

1. Edit `design_rules.toml`. Set `status` and `source` of each value that you change.
2. Run `make pcb-all BOARD=mill`. It makes the schematic variant, writes the rules into the KiCad project, builds the board from `pcb/mill/placement.py`, routes it, writes the fab outputs and the review files, and runs the checks.
3. Run `make pcb-mill-check BOARD=mill`. Read the errors and the warnings.
4. If a check fails, the parts or the planned zones do not fit the new values. Change `pcb/mill/placement.py`, then go to step 2.
5. Commit `design_rules.toml`, `pcb/mill/` and `review/`.

| Key | Effect |
| --- | --- |
| `horizontal_error` | Position error of a cut for each side. The milling check needs gap >= cut width + 2 x this value (`MILL-GAP`) |
| `cut_spacing_min` | Smallest distance between the centers of two isolation gaps. Copper between two gaps must be `cut_spacing_min` - `clearance` wide. `MILL-CUT-SPACING` lists thinner copper |
| `clearance`, `zone_clearance` | Copper gap between two nets, and between a pour and other copper |
| `track_min` | Hard minimum track width |
| `[netclass.*] track_width` | Target track width of each net class. A track is narrower only where a pad gives no room |
| `zone_min_width` | Smallest width of pour copper |
| `component_gap` | Smallest gap between pads of two different parts on different nets (`MILL-COMP-GAP`) |
| `module_gap`, `edge_clearance`, `edge_band`, `annular_min` | Module courtyard gap, copper to board edge, router band along the edge, annular ring |
| `[[exception]]` | A part whose footprint fixes a smaller gap (U3). `zones = true`: planned zones can use the lower clearance at its pads |
| `[parts] exclude` | Parts of the schematic that are not on the board |

The values are start values with `status = "assumed"`. `make pcb-rules BOARD=mill` prints the assumed keys. A value must not be below the lab limit of the same name in `milling.toml`.

## Open items
- `design_rules.toml`: all values are `assumed`. The lab tech must confirm the horizontal error of the mill and the reading of "2 mm between cuts" (see `review/README.md`).

- The post `Carvera.cps` and the NC code of the setups: not received.
- `milled_hole_min` (3.3 mm) is `assumed`: the lab tech must confirm it.

## Use this lab in another project

1. Copy this directory into the other repo.
2. Add a `lab:` line with the new path to the `.claude/CLAUDE.md` of that repo.
3. Copy the skills `pcb-lab-config` and `pcb-milling-check`, and `lab.py` from `pcb/tools/`. The mill tools come with this directory. They find `lab.py` at `pcb/tools/` of the repo root.
4. Run the milling check on the board of that project.

For a different lab or mill, make a new lab directory with the skill `pcb-lab-config`, then change the `lab:` line.
