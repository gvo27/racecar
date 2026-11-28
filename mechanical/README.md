# mechanical/: 3D-printed parts (build123d)

Parametric CAD of the printed mounts for the Tamiya TT-02: the frame for the Pi 5 and the power board, and the sensor rail blocks. Claude designs and checks the parts on Linux. The owner reviews the STEP file in SolidWorks.

```
make cad-image                      # one time: the CAD image (docker)
make mech-test                      # lint + tests
make mech-check MODEL=test_bracket  # build + check -> build/mech/<MODEL>/ (STEP, STL, SVG, iso PNG, report.json)
```

- `src/rccar_mech/`: the library (params, checks, export, render, diff) and `models/`, one module per model. The current frame is `frame_rev2`. `frame_rev1` (four posts, deck in two halves) stays for a comparison.
- `config/`: `print.toml` (print limits, `assumed`), one design file per model.
- Conventions, units, frame and the SolidWorks handoff: [docs/mechanical/](../docs/mechanical/README.md).
- `COLCON_IGNORE` keeps this folder out of the ROS 2 build.
