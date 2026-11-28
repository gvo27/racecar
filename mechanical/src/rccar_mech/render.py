"""Shaded isometric PNG without a display.

Each part is tessellated. The triangles of all parts are projected (orthographic) and drawn far to near
(painter's algorithm) with matplotlib Agg. Good enough for a review picture, not a CAD view.
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection

# view from front-right-above: X forward, Y left, Z up
EYE = np.array([1.0, -1.2, 0.9])
LIGHT = np.array([0.5, -0.3, 1.0])
DEFAULT_RGBA = (0.55, 0.6, 0.7, 1.0)
MAX_EDGE = 6.0  # mm: triangle edge limit for the depth sort


def _leaves(shape):
    if getattr(shape, "children", None):
        return [leaf for c in shape.children for leaf in _leaves(c)]
    return [shape]


def _rgba(part):
    c = getattr(part, "color", None)
    return tuple(c) if c is not None else DEFAULT_RGBA


def _subdivide(tri: np.ndarray, max_edge: float) -> np.ndarray:
    """Split each triangle at its edge midpoints until no edge is longer than max_edge.
    Small triangles sort better by depth (painter's algorithm)."""
    out = []
    while len(tri):
        e = np.max(np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2), axis=1)
        out.append(tri[e <= max_edge])
        big = tri[e > max_edge]
        a, b, c = big[:, 0], big[:, 1], big[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        tri = np.concatenate([np.stack(t, axis=1) for t in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
    return np.concatenate(out)


def _basis(eye):
    d = eye / np.linalg.norm(eye)
    right = np.cross([0.0, 0.0, 1.0], d)
    right /= np.linalg.norm(right)
    up = np.cross(d, right)
    return d, right, up


def iso_png(
    shape, path: Path, title: str = "", tolerance: float = 0.2, dpi: int = 150, ghost_prefix: str = "ref_"
) -> Path:
    """Printed parts are shaded solids. Parts with a label that starts with ghost_prefix are drawn as edges only."""
    matplotlib.use("Agg")
    d, right, up = _basis(EYE)
    light = LIGHT / np.linalg.norm(LIGHT)
    polys, depth, colors = [], [], []
    ghosts = []
    for part in _leaves(shape):
        if (part.label or "").startswith(ghost_prefix):
            ghosts.append(part)
            continue
        verts, tris = part.tessellate(tolerance)
        if not tris:
            continue
        v = np.array([(p.X, p.Y, p.Z) for p in verts])
        tri = _subdivide(v[np.array(tris)], MAX_EDGE)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        front = n @ d > 0  # back-face culling: the tessellation has outward normals
        tri, n = tri[front], n[front]
        shade = 0.4 + 0.6 * np.clip(np.abs(n @ light), 0, 1)
        r, g, b, a = _rgba(part)
        rgb = np.clip(shade[:, None] * np.array([r, g, b]), 0, 1)
        polys.append(np.stack([tri @ right, tri @ up], axis=-1))
        depth.append((tri @ d).mean(axis=1))
        colors.append(np.column_stack([rgb, np.full(len(tri), a)]))
    fig, ax = plt.subplots(figsize=(10, 7.5))
    if polys:
        p, z, c = np.concatenate(polys), np.concatenate(depth), np.concatenate(colors)
        order = np.argsort(z)  # far first
        ax.add_collection(PolyCollection(p[order], facecolors=c[order], edgecolors=c[order], linewidths=0.15))
    for part in ghosts:
        r, g, b, _ = _rgba(part)
        for e in part.edges():
            n = 2 if e.geom_type.name == "LINE" else 24
            pts = np.array([tuple(e.position_at(i / (n - 1))) for i in range(n)])
            ax.plot(pts @ right, pts @ up, color=(r * 0.7, g * 0.7, b * 0.7), linewidth=0.7)
    ax.autoscale_view()
    ax.margins(0.04)
    ax.set_aspect("equal")
    ax.axis("off")
    # axis triad, lower left
    o = np.array([0.08, 0.1])
    for vec, name, col in (((1, 0, 0), "X fwd", "red"), ((0, 1, 0), "Y left", "green"), ((0, 0, 1), "Z up", "blue")):
        e = np.array([np.dot(vec, right), np.dot(vec, up)]) * 0.06
        ax.annotate("", xy=o + e, xytext=o, xycoords="axes fraction", arrowprops={"arrowstyle": "->", "color": col})
        ax.annotate(name, xy=o + e * 1.25, xycoords="axes fraction", color=col, fontsize=8)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path
