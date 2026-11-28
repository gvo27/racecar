# build123d notes

The pinned version is in `mechanical/pyproject.toml`. Read the API of that version, not of `latest`:
- The docs for language models: `https://build123d.readthedocs.io/en/latest/llms.txt`. The `latest` docs can be newer than the pin. If a doc and the pin disagree, read the source at the git tag of the pin (`https://github.com/gumyr/build123d`).
- In doubt, probe the API in the image: `docker run --rm -v <dir>:/w:ro rccar-cad:local python /w/probe.py`. Put probe scripts in the scratchpad, not in the repo.

## Style used in this project
- Algebra mode (`Box(...) - Pos(x, y, z) * Cylinder(...)`), not builder mode. It returns plain shapes that tests can inspect.
- An assembly is `Compound(children=[...], label=...)`. Set `label` and `color` on each part.
- `Pos` and `Rot` place a part. `Location` objects are for repeated placement.

## Traps found on this project
- `Compound(children=[part])` moves `part` out of its old parent. Copy first: `copy.copy(part)`, then set the label and the color again.
- `Compound.volume` of a nested assembly (children only) can be smaller than the sum of its parts. Sum the leaf parts.
- `Face.radius` can be `None` on a cylinder face (for example after two holes overlap). Read the radius and the axis from the surface: `BRepAdaptor_Surface(face.wrapped).Cylinder()`.
- A hole wall can be split into several faces. Group the faces by axis and radius, then add their angle spans.
- `export_step` has no switch for the schema (AP214 or AP242). It keeps labels and colors. Its `timestamp` argument makes the file the same on each run.
- `ExportSVG` colors: use color names or normalized values. 0-255 tuples are deprecated.
- `intersect` returns a Shape, a ShapeList or None. Sum the volumes of a ShapeList.

## Fasteners
- `bd_warehouse` (pinned in `mechanical/pyproject.toml`) has screws, nuts and threads. Use it for a screw envelope or a thread. A heat-set insert hole is a plain cylinder from the insert datasheet.
