"""Compare two STEP files: bounding box, volume, part labels, hole inventory. It is not a full geometric proof."""

from pathlib import Path

from build123d import import_step

from rccar_mech import checks

POS_TOL = 0.01  # mm
D_TOL = 0.01  # mm


def _close(h: checks.Hole, k: checks.Hole) -> bool:
    return (
        abs(h.x - k.x) <= POS_TOL
        and abs(h.y - k.y) <= POS_TOL
        and abs(h.z - k.z) <= POS_TOL
        and abs(h.diameter - k.diameter) <= D_TOL
        and all(abs(p - q) <= 1e-4 for p, q in zip(h.axis, k.axis))
    )


def _unmatched(a: list[checks.Hole], b: list[checks.Hole]) -> list[checks.Hole]:
    """The holes of a with no close hole in b (each hole of b matches once)."""
    free = list(b)
    out = []
    for h in a:
        hit = next((k for k in free if _close(h, k)), None)
        if hit is None:
            out.append(h)
        else:
            free.remove(hit)
    return out


def _row(h: checks.Hole) -> list[float]:
    return [round(h.x, 3), round(h.y, 3), round(h.z, 3), round(h.diameter, 3)]


def diff(a_path: Path, b_path: Path) -> dict:
    a, b = import_step(a_path), import_step(b_path)
    ha, hb = checks.holes(a), checks.holes(b)
    va = sum(s.volume for s in a.solids())
    vb = sum(s.volume for s in b.solids())
    sa, sb = a.bounding_box().size, b.bounding_box().size
    la = sorted(p.label for p in checks.parts(a))
    lb = sorted(p.label for p in checks.parts(b))
    out = {
        "volume_a": va,
        "volume_b": vb,
        "volume_delta": vb - va,
        "bbox_a": [sa.X, sa.Y, sa.Z],
        "bbox_b": [sb.X, sb.Y, sb.Z],
        "parts_removed": sorted(set(la) - set(lb)),
        "parts_added": sorted(set(lb) - set(la)),
        "holes_removed": [_row(h) for h in _unmatched(ha, hb)],
        "holes_added": [_row(h) for h in _unmatched(hb, ha)],
    }
    out["same"] = (
        abs(out["volume_delta"]) <= checks.REL_TOL * max(va, 1.0)
        and all(abs(p - q) <= checks.BOX_TOL for p, q in zip(out["bbox_a"], out["bbox_b"]))
        and not (out["parts_removed"] or out["parts_added"] or out["holes_removed"] or out["holes_added"])
    )
    return out
