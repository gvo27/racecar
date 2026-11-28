"""Generic geometry checks. Each check returns a list of Finding. Check ids: docs/mechanical/conventions.md

Units mm. A check never changes the shape.
"""

import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from build123d import Compound, Face, Shape, import_step
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Cylinder
from OCP.TopAbs import TopAbs_REVERSED

VOL_TOL = 1e-3  # mm3: overlap below this is contact (STEP and boolean noise), not interference
REL_TOL = 1e-4  # STEP round trip: relative volume tolerance
BOX_TOL = 1e-3  # mm
AXIS_TOL = 1e-6
FULL_TURN = 2 * math.pi - 1e-6


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str  # "error" or "warning"
    where: str
    message: str


@dataclass(frozen=True)
class Hole:
    diameter: float
    x: float  # center of the hole on its axis
    y: float
    z: float
    axis: tuple[float, float, float]  # unit vector, first non-zero component positive
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


def labels(asm: Shape) -> list[Finding]:
    """Each leaf part has a label, and no two leaf parts have the same label (findings and STEP use them)."""
    names = [p.label or "" for p in parts(asm)]
    out = [_err("MECH-LABEL", f"part {i}", "part has no label") for i, n in enumerate(names) if not n]
    out += [_err("MECH-LABEL", n, f"{c} parts have this label") for n, c in Counter(names).items() if n and c > 1]
    return out


# ---- holes ----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Cyl:
    face: Face
    radius: float
    origin: tuple[float, float, float]
    axis: tuple[float, float, float]
    span: float  # rad
    v0: float
    v1: float
    inner: bool  # material outside the cylinder: a hole wall, not a boss


def _canon(d):
    for c in d:
        if abs(c) > AXIS_TOL:
            return d if c > 0 else tuple(-x for x in d)
    return d


def _cyl(face: Face) -> _Cyl | None:
    s = BRepAdaptor_Surface(face.wrapped)
    if s.GetType() != GeomAbs_Cylinder:
        return None
    c = s.Cylinder()
    ax = c.Axis()
    loc, d = ax.Location(), ax.Direction()
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
    return _Cyl(
        face,
        c.Radius(),
        (loc.X(), loc.Y(), loc.Z()),
        (d.X(), d.Y(), d.Z()),
        u1 - u0,
        v0,
        v1,
        face.wrapped.Orientation() == TopAbs_REVERSED,
    )


def _line_key(c: _Cyl):
    """Same axis line and radius: (axis, foot of the axis line nearest the origin, radius), rounded."""
    a = _canon(c.axis)
    o = c.origin
    t = sum(o[i] * a[i] for i in range(3))
    foot = tuple(o[i] - t * a[i] for i in range(3))
    return tuple(round(x, 4) for x in a) + tuple(round(x, 4) for x in foot) + (round(c.radius, 4),)


def _groups(shape: Shape) -> dict:
    g: dict = {}
    for f in shape.faces():
        c = _cyl(f)
        if c is not None and c.inner:
            g.setdefault(_line_key(c), []).append(c)
    return g


def holes(shape: Shape) -> list[Hole]:
    """Inner cylinders with a full 360 degree wall (also when split into several faces). Fillets, slots and half
    holes at an edge are partial cylinders and are not holes."""
    out = []
    for cs in _groups(shape).values():
        # one hole per run of faces along the axis that closes the circle
        by_v: dict = {}
        for c in cs:
            # project v range onto the canonical axis so that split faces line up
            a, o = _canon(c.axis), c.origin
            sign = 1 if a == c.axis else -1
            base = sum(o[i] * a[i] for i in range(3))
            lo, hi = sorted((base + sign * c.v0, base + sign * c.v1))
            by_v.setdefault((round(lo, 3), round(hi, 3)), []).append(c)
        for (lo, hi), run in by_v.items():
            if sum(c.span for c in run) < FULL_TURN:
                continue
            c = run[0]
            a = _canon(c.axis)
            k = _line_key(c)
            foot = k[3:6]
            mid = (lo + hi) / 2
            x, y, z = (foot[i] + mid * a[i] for i in range(3))
            out.append(Hole(2 * c.radius, x, y, z, a, hi - lo))
    return sorted(out, key=lambda h: (round(h.x, 3), round(h.y, 3), round(h.z, 3), h.diameter))


def expect_holes(shape, expected, tol: float = 0.01) -> list[Finding]:
    """shape: a shape or a list of shapes. expected: (x, y, d) of the holes, one entry per hole (a bolt through two
    parts is two entries). Report each missing hole and each extra hole."""
    have = [h for s in (shape if isinstance(shape, list) else [shape]) for h in holes(s)]
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
            out.append(_err("MECH-HOLE", f"({h.x:.3f}, {h.y:.3f}, {h.z:.3f})", f"extra hole d {h.diameter:.3f}"))
    return out


# ---- walls ----------------------------------------------------------------------------------------------------


def _bbox_gap(a, b) -> float:
    """Gap between two bounding boxes (0 when they overlap)."""
    gaps = [max(a.min.X - b.max.X, b.min.X - a.max.X, 0.0), max(a.min.Y - b.max.Y, b.min.Y - a.max.Y, 0.0)]
    gaps.append(max(a.min.Z - b.max.Z, b.min.Z - a.max.Z, 0.0))
    return math.sqrt(sum(g * g for g in gaps))


def walls(shape: Shape, print_cfg: dict) -> list[Finding]:
    """Wall from each hole face to the faces that do not touch it (side faces, other holes) >= min_wall.

    Faces that share an edge with the hole face are skipped (the top and bottom face of a through hole). Coaxial
    cylinders are skipped (a counterbore step is not a wall).
    """
    min_wall = print_cfg["limits"]["min_wall"]
    faces = shape.faces()
    info = [(f, _cyl(f), f.bounding_box()) for f in faces]
    out = []
    for f, c, fb in info:
        if c is None or not c.inner:
            continue
        key = _line_key(c)
        f_edges = f.edges()
        for g, gc, gb in info:
            if g.is_same(f) or _bbox_gap(fb, gb) >= min_wall:
                continue
            if gc is not None and _line_key(gc)[:6] == key[:6]:
                continue
            if any(e.is_same(fe) for e in g.edges() for fe in f_edges):
                continue
            d = f.distance_to(g)
            if d < min_wall - 1e-6:
                where = f"hole d {2 * c.radius:.2f} at {tuple(round(x, 2) for x in fb.center())}"
                out.append(_err("MECH-WALL", where, f"wall {d:.2f} mm < {min_wall} mm"))
                break
    return out


# ---- assemblies -----------------------------------------------------------------------------------------------


def _volume(shapes) -> float:
    if shapes is None:
        return 0.0
    if isinstance(shapes, Shape):
        return shapes.volume
    return sum(s.volume for s in shapes)


def interference(items: list[Shape]) -> list[Finding]:
    out = []
    for a, b in combinations(items, 2):
        if _bbox_gap(a.bounding_box(), b.bounding_box()) > 0:
            continue
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
    bb = shape.bounding_box().size
    size = sorted((bb.X, bb.Y))
    bed = print_cfg["bed"]
    bx = sorted((bed["x"], bed["y"]))
    bz = print_cfg["bed_height"]["z"]
    if size[0] > bx[0] or size[1] > bx[1] or bb.Z > bz:
        msg = f"{size[1]:.1f} x {size[0]:.1f} x {bb.Z:.1f} mm > bed {bx[1]} x {bx[0]} x {bz} mm"
        return [_err("MECH-BED", shape.label or "shape", msg)]
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
    """Read the STEP file back. Volume (sum of the leaf parts), bounding box and part labels must equal the model."""
    back = import_step(step_path)
    out = []
    v0 = sum(p.volume for p in parts(shape))
    v1 = sum(s.volume for s in back.solids())
    if abs(v1 - v0) > REL_TOL * max(v0, 1.0):
        out.append(_err("MECH-STEP", step_path.name, f"volume {v1:.3f} != model {v0:.3f} mm3"))
    b0, b1 = shape.bounding_box(), back.bounding_box()
    for name, p, q in (("min", b0.min, b1.min), ("max", b0.max, b1.max)):
        if (p - q).length > BOX_TOL:
            out.append(_err("MECH-STEP", step_path.name, f"bbox {name} {q} != model {p}"))
    l0 = sorted(p.label for p in parts(shape))
    l1 = sorted(p.label for p in parts(back))
    if l0 != l1:
        out.append(_err("MECH-STEP", step_path.name, f"part labels {l1} != model {l0}"))
    return out


def parts(shape: Shape) -> list[Shape]:
    """The leaf parts of an assembly (labeled children)."""
    if isinstance(shape, Compound) and shape.children:
        return [leaf for c in shape.children for leaf in parts(c)]
    return [shape]
