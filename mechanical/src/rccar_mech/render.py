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


def _leaves(shape):
    if getattr(shape, "children", None):
        return [leaf for c in shape.children for leaf in _leaves(c)]
    return [shape]


def _rgba(part):
    c = getattr(part, "color", None)
    return tuple(c) if c is not None else DEFAULT_RGBA


def _basis(eye):
    d = eye / np.linalg.norm(eye)
    right = np.cross([0.0, 0.0, 1.0], d)
    right /= np.linalg.norm(right)
    up = np.cross(d, right)
    return d, right, up


def iso_png(shape, path: Path, title: str = "", tolerance: float = 0.2, dpi: int = 150) -> Path:
    matplotlib.use("Agg")
    d, right, up = _basis(EYE)
    light = LIGHT / np.linalg.norm(LIGHT)
    polys, depth, colors = [], [], []
    for part in _leaves(shape):
        verts, tris = part.tessellate(tolerance)
        if not tris:
            continue
        v = np.array([(p.X, p.Y, p.Z) for p in verts])
        tri = v[np.array(tris)]
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
        xy = p.reshape(-1, 2)
        lo, hi = xy.min(0), xy.max(0)
        pad = 0.05 * (hi - lo).max()
        ax.set_xlim(lo[0] - pad, hi[0] + pad)
        ax.set_ylim(lo[1] - pad, hi[1] + pad)
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
