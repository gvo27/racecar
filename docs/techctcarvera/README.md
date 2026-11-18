# Lab directory: in-house isolation milling (Makera Carvera)

This directory holds the facts and files of one lab: the mill, its tools, the copper stock, the rivet kit and the lab CAM template. It also holds the mill tools and the waiver list of the milling check. It holds no board files. A board project reads it through one pointer: the `lab:` line of `.claude/CLAUDE.md`. In this repo, the board tools read that line through `pcb/libraries/lab.py`. The environment variable `LAB_DIR` overrides it.

## Contents

| Path | Content |
| --- | --- |
| `milling.toml` | The lab file: milling limits (cut depth, isolation bit, drill set, end mill, bored hole, via, stock, dowels), the machine and the lab inventory. Each value has `status` (`confirmed` or `assumed`) and `source`. The checks read it. Keep it current with the skill `pcb-lab-config` |
| `milling_waivers.toml` | The waiver list for the milling check (skill `pcb-milling-check`) |
| `tools/milling_check.py`, `tools/fab_export.py` | The mill tools: the milling check of a board against the lab file, and the fab export (DXF, Excellon) in the frame of the lab CAM template. Their tests are `tools/test_*.py`. They run in the KiCad image (`make pcb-mill-check`, `make pcb-fab`, `make pcb-test`) and import `lab.py`, `paths.py` and `placement.py` from `pcb/libraries/` |
| `example/README.md` | Facts read from the lab CAM file, the Fusion exports of the owner, and how to read a `.f3z` on Linux |
| `example/Pcb DXF's amd copper plate.f3z` | The lab's calibrated Fusion 360 CAM template (demo panel of 6 boards, setups A, B and C) |
| `example/demo_toolpaths_setupB.png` | Decoded toolpaths of setup B of the demo panel |
| `example/fusion_export/` | Fusion exports of the owner (2026-11-15): setup sheets of setups A, B, C and of all setups, tool library, sketch DXFs, screenshots |

## Open items

- The post `Carvera.cps` and the NC code of the setups: not received.
- `milled_hole_min` (3.3 mm) is `assumed`: the lab tech must confirm it.

## Use this lab in another project

1. Copy this directory into the other repo.
2. Add a `lab:` line with the new path to the `.claude/CLAUDE.md` of that repo.
3. Copy the skills `pcb-lab-config` and `pcb-milling-check`, and `lab.py` from `pcb/libraries/`. The mill tools come with this directory. They find `lab.py` at `pcb/libraries/` of the repo root.
4. Run the milling check on the board of that project.

For a different lab or mill, make a new lab directory with the skill `pcb-lab-config`, then change the `lab:` line.
