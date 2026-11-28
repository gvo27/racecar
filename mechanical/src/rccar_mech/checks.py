"""Generic geometry checks. Each check returns a list of Finding. Rule ids: references/check-matrix.md of skill mech-design.

Units mm. A check never changes the shape.
"""

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from build123d import Compound, Face, GeomType, Shape, import_step

VOL_TOL = 1e-6  # mm3: overlap below this is contact, not interference
REL_TOL = 1e-4  # STEP round trip: relative volume tolerance
BOX_TOL = 1e-3  # mm


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str  # "error" or "warning"
    where: str
    message: str


@dataclass(frozen=True)
class Hole:
    diameter: float
    x: float
    y: float
    z: float
    axis: tuple[float, float, float]
    depth: float


def _err(rule, where, msg):
    return Finding(rule, "error", where, msg)


def validity(shape: Shape) -> list[Finding]:
    where = shape.label or "shape"
    if shape.is_null or not shape.solids():
        return [_err("MECH-VALID", where, "no solid")]
    out = []
    for i, s in enumerate(shape.solids()):
        if not s.is_valid:
            out.append(_err("MECH-VALID", f"{where} solid {i}", "invalid B-rep"))
        if s.volume <= VOL_TOL:
            out.append(_err("MECH-VALID", f"{where} solid {i}", "zero volume"))
    return out


def _cylinder_hole(face: Face) -> Hole | None:
    """A full 360 degree cylindrical face whose normal points to its axis (material outside) is a hole."""
    if face.geom_type != GeomType.CYLINDER:
        return None
    bb = face.bounding_box()
    c = bb.center()
    axis = face.axis_of_rotation.direction if hasattr(face, "axis_of_rotation") else None
    if axis is None:
        return None
    r = face.radius
    # full circle: the bbox across the axis is 2r in both directions
    across = [abs(v) for v in (bb.size.X, bb.size.Y, bb.size.Z)]
    along = abs(bb.size.dot(axis)) if hasattr(bb.size, "dot") else max(across)
    p = face.position_at(0.5, 0.5)
    n = face.normal_at(p)
    to_axis = c - p
    to_axis = to_axis - axis * to_axis.dot(axis)
    if to_axis.length < 1e-9 or n.dot(to_axis) <= 0:
        return None
    if sum(1 for v in across if abs(v - 2 * r) < 1e-3) < 2:
        return None
    return Hole(2 * r, c.X, c.Y, c.Z, (axis.X, axis.Y, axis.Z), along)


def holes(shape: Shape) -> list[Hole]:
    found = [h for f in shape.faces() if (h := _cylinder_hole(f))]
    return sorted(found, key=lambda h: (round(h.x, 3), round(h.y, 3), round(h.z, 3)))


def expect_holes(shape: Shape, expected, tol: float = 0.01) -> list[Finding]:
    """expected: (x, y, d) for vertical holes. Report each expected hole that is missing and each extra hole."""
    have = holes(shape)
    out, used = [], set()
    for x, y, d in expected:
        hit = next(
            (
                i
                for i, h in enumerate(have)
                if i not in used and abs(h.x - x) <= tol and abs(h.y - y) <= tol and abs(h.diameter - d) <= tol
            ),
            None,
        )
        if hit is None:
            out.append(_err("MECH-HOLE", f"({x:.3f}, {y:.3f})", f"missing hole d {d:.3f}"))
        else:
            used.add(hit)
    for i, h in enumerate(have):
        if i not in used:
            out.append(_err("MECH-HOLE", f"({h.x:.3f}, {h.y:.3f})", f"extra hole d {h.diameter:.3f}"))
    return out


def walls(shape: Shape, print_cfg: dict) -> list[Finding]:
    """Wall from each hole to the faces that do not touch it (side faces, other holes) >= min_wall."""
    min_wall = print_cfg["limits"]["min_wall"]
    out = []
    faces = shape.faces()
    for f in faces:
        h = _cylinder_hole(f)
        if h is None:
            continue
        for g in faces:
            if g.is_same(f):
                continue
            if any(e.is_same(fe) for e in g.edges() for fe in f.edges()):
                continue
            d = f.distance_to(g)
            if d < min_wall - 1e-6:
                out.append(
                    _err(
                        "MECH-WALL",
                        f"hole d {h.diameter:.2f} at ({h.x:.2f}, {h.y:.2f})",
                        f"wall {d:.2f} mm < {min_wall} mm",
                    )
                )
                break
    return out


def _volume(shapes) -> float:
    if shapes is None:
        return 0.0
    if isinstance(shapes, Shape):
        return shapes.volume
    return sum(s.volume for s in shapes)


def interference(parts: list[Shape]) -> list[Finding]:
    out = []
    for a, b in combinations(parts, 2):
        v = _volume(a.intersect(b))
        if v > VOL_TOL:
            out.append(_err("MECH-INTERFERE", f"{a.label} / {b.label}", f"overlap {v:.3f} mm3"))
    return out


def clearance(a: Shape, b: Shape, minimum: float) -> list[Finding]:
    d = a.distance_to(b)
    if d < minimum - 1e-6:
        return [_err("MECH-CLEAR", f"{a.label} / {b.label}", f"gap {d:.2f} mm < {minimum} mm")]
    return []


def bed_fit(shape: Shape, print_cfg: dict) -> list[Finding]:
    """Fits the bed in some orientation turned about Z (both XY orders), Z within the height."""
    size = sorted((shape.bounding_box().size.X, shape.bounding_box().size.Y))
    sz = shape.bounding_box().size.Z
    bed = print_cfg["bed"]
    bx = sorted((bed["x"], bed["y"]))
    if size[0] > bx[0] or size[1] > bx[1] or sz > bed["z"]:
        return [
            _err(
                "MECH-BED",
                shape.label or "shape",
                f"{size[1]:.1f} x {size[0]:.1f} x {sz:.1f} mm > bed {bx[1]} x {bx[0]} x {bed['z']} mm",
            )
        ]
    return []


def mesh(stl_path: Path) -> list[Finding]:
    import trimesh

    m = trimesh.load(str(stl_path), force="mesh")
    out = []
    if not m.is_watertight:
        out.append(_err("MECH-MESH", stl_path.name, "STL is not watertight"))
    if not m.is_winding_consistent:
        out.append(_err("MECH-MESH", stl_path.name, "STL winding is not consistent"))
    return out


def step_round_trip(shape: Shape, step_path: Path) -> list[Finding]:
    """Read the STEP file back. Volume, bounding box and part labels must equal the model."""
    back = import_step(step_path)
    out = []
    v0, v1 = shape.volume, back.volume
    if abs(v1 - v0) > REL_TOL * max(v0, 1.0):
        out.append(_err("MECH-STEP", step_path.name, f"volume {v1:.3f} != model {v0:.3f} mm3"))
    b0, b1 = shape.bounding_box(), back.bounding_box()
    for name, p, q in (("min", b0.min, b1.min), ("max", b0.max, b1.max)):
        if (p - q).length > BOX_TOL:
            out.append(_err("MECH-STEP", step_path.name, f"bbox {name} {q} != model {p}"))
    leaves0 = sorted(s.label for s in _leaves(shape))
    leaves1 = sorted(s.label for s in _leaves(back))
    if leaves0 != leaves1:
        out.append(_err("MECH-STEP", step_path.name, f"part labels {leaves1} != model {leaves0}"))
    return out


def _leaves(shape: Shape) -> list[Shape]:
    if isinstance(shape, Compound) and shape.children:
        return [leaf for c in shape.children for leaf in _leaves(c)]
    return [shape]


def parts(shape: Shape) -> list[Shape]:
    """The leaf parts of an assembly (labeled children)."""
    return _leaves(shape)
