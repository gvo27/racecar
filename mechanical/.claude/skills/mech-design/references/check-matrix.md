# Check matrix

The automatic checks run in `make mech-check MODEL=<model>` (`mechanical/src/rccar_mech/checks.py` and the model `acceptance()`). The ids are in `docs/mechanical/conventions.md`.

| Id | Pass condition | It cannot find |
| --- | --- | --- |
| MECH-VALID | Each part is a valid solid with a volume | A valid solid with the wrong shape |
| MECH-LABEL | Each leaf part has a label. No two parts have the same label | A wrong label |
| MECH-HOLE | The holes of the acceptance list are there, with the expected diameter and position. No extra hole | Holes that are not full cylinders (slots, half holes). Holes on a tilted axis need their own criterion |
| MECH-WALL | The wall from a hole to the faces that do not touch it is at least `min_wall` | Thin walls without a hole: ribs, tabs, a thin floor |
| MECH-INTERFERE | No two parts overlap by more than the contact tolerance (printed and `ref_`) | A part that is too close but does not touch: use MECH-CLEAR |
| MECH-CLEAR | Each named pair of the acceptance list keeps its minimum gap | A pair that nobody listed |
| MECH-BED | Each printed part fits the print bed (turned about Z) | Print orientation, overhangs, supports |
| MECH-MESH | The STL is watertight and its winding is consistent | Tessellation that is too coarse for a small hole |
| MECH-STEP | The STEP file read back has the model volume, bounding box and labels | Colors in SolidWorks (owner check) |
| MECH-EXPORT | The STEP and STL files exist. A warning if the model has no printed part | - |

## Manual review (the checks cannot do this)
- Look at the iso PNG and the SVG views. Is the shape the intent? Are the ref envelopes at the correct places?
- Print orientation: which face is on the bed? Are there overhangs above 45 degrees or bridges longer than about 10 mm (estimate, not measured on the lab printer)?
- Load path: where do the forces of a crash or a jump go? Is there a thin section between two mounts?
- Screw and tool access: can a hand reach each screw, each clip and each connector with the parts in place?
- Cable path: is there a path for each cable, with slack for the frame lift?
- Battery swap: can the owner pull the clips, lift the frame and lift the battery out, with no tool? Does a part or a `ref_` envelope sit in the battery lift-out path?
- Heat: is a part near the motor or the ESC above the `heat_limit` of `print.toml`?
- Each number in a document agrees with the config files and the report.
