"""Write STEP (assembly with labels and colors), binary STL, SVG views and the iso PNG of one model.

STEP is the file for SolidWorks. STL is for the slicer only. Units mm, frame: docs/mechanical/conventions.md
"""

from pathlib import Path

from build123d import Compound, ExportSVG, LineType, Unit, export_step, export_stl

# viewport origins (look at the model center): X forward, Y left, Z up
VIEWS = {
    "top": ((0, 0, 1000), (1, 0, 0)),
    "front": ((1000, 0, 0), (0, 0, 1)),
    "side": ((0, 1000, 0), (0, 0, 1)),
    "iso": ((-600, -600, 500), (0, 0, 1)),
}
STL_ANGULAR = 0.1  # rad


def write_step(shape: Compound, path: Path) -> Path:
    # fixed timestamp: the same model gives the same file
    export_step(shape, path, unit=Unit.MM, timestamp="2000-01-01T00:00:00")
    return path


def write_stl(shape: Compound, path: Path, tolerance: float) -> Path:
    export_stl(shape, path, tolerance=tolerance, angular_tolerance=STL_ANGULAR, ascii_format=False)
    return path


def write_svg(shape: Compound, path: Path, view: str) -> Path:
    origin, up = VIEWS[view]
    c = shape.bounding_box().center()
    eye = (c.X + origin[0], c.Y + origin[1], c.Z + origin[2])
    visible, hidden = shape.project_to_viewport(eye, viewport_up=up, look_at=c)
    svg = ExportSVG(unit=Unit.MM, margin=5)
    svg.add_layer("hidden", line_color="gray", line_type=LineType.ISO_DOT)
    svg.add_layer("visible", line_color="black", line_weight=0.25)
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    svg.write(path)
    return path


def write_all(
    shape: Compound, out_dir, name: str, stl_tolerance: float, previews: bool = False, stl_parts: list | None = None
) -> dict:
    """STEP of the whole assembly (with the ref_ envelopes). One STL per part of stl_parts (`<name>_<label>.stl`:
    each part prints alone, and touching parts in one mesh are not watertight). Without stl_parts: `<name>.stl`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if stl_parts is None:
        stls = [write_stl(shape, out_dir / f"{name}.stl", stl_tolerance)]
    else:
        stls = [write_stl(p, out_dir / f"{name}_{p.label}.stl", stl_tolerance) for p in stl_parts]
    out = {"step": write_step(shape, out_dir / f"{name}.step"), "stl": stls}
    if previews:
        from rccar_mech import render

        for view in VIEWS:
            out[f"svg_{view}"] = write_svg(shape, out_dir / f"{name}_{view}.svg", view)
        out["png_iso"] = render.iso_png(shape, out_dir / f"{name}_iso.png", title=name)
    return out
