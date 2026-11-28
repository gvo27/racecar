# Mechanical conventions

## Units and frame
- All lengths are in millimeters. Angles in the code are in degrees, unless a name says `rad`. The STEP files are written in mm.
- Frame of a model on the car: X forward, Y left, Z up (ROS REP-103, the same as `base_link`). The origin is the center of the four body posts, at ground level. A test part uses its own center.
- SolidWorks uses Y up by default. On import, keep the STEP coordinates. Do not let SolidWorks move the part to its origin. Then the coordinates in the report match the CAD.

## Sources of values
- Facts (`mechanical/config/print.toml`, and later `hardware.toml`): each table has `status` (`confirmed` or `assumed`) and `source`, like the lab file of the mill. The loader rejects a table without them. An `assumed` value stays assumed until a measurement, a datasheet or a dated statement of the owner confirms it.
- Design parameters (`mechanical/config/<model>.toml`): values that the designer chooses. They have no status.
- The rev3 board geometry comes from `pcb/src/rc_power_board.kicad_pcb` at run time. No copy goes into the CAD code.

## Assembly, labels and colors
- A model is a `Compound` assembly. Each printed part has a plain label, for example `deck`.
- A reference envelope has a label that starts with `ref_`, for example `ref_pi5`. It shows a board, the battery or a chassis part for the clearance checks. It is never printed.
- The STEP file holds the whole assembly with the labels and the colors. The STL file holds only the printed parts.
- STEP keeps no feature history. SolidWorks gets plain solids (B-rep). A change goes back into the Python model, not into SolidWorks.

## Files of one build (`build/mech/<model>/`)
| File | Use |
| --- | --- |
| `<model>.step` | SolidWorks review (primary deliverable) |
| `<model>.stl` | Slicer only (binary) |
| `<model>_{top,front,side,iso}.svg` | Line views with hidden lines |
| `<model>_iso.png` | Shaded iso view for the PR |
| `report.json` | Bounding box, volume, mass estimate, center of gravity, holes, findings, assumed tables, file hashes |

## Check ids
| Id | Check |
| --- | --- |
| MECH-VALID | Each part is a valid solid with a volume |
| MECH-HOLE | The holes are at the expected positions and diameters (no missing hole, no extra hole) |
| MECH-WALL | The wall from each hole to the other faces is at least `min_wall` (`print.toml`) |
| MECH-INTERFERE | No two parts (printed or `ref_`) overlap |
| MECH-CLEAR | A named pair keeps its minimum gap (model acceptance) |
| MECH-BED | Each printed part fits the print bed |
| MECH-MESH | The STL is watertight and its winding is consistent |
| MECH-STEP | The STEP file read back has the model volume, bounding box and part labels |
| MECH-EXPORT | The STEP and STL files exist |
