"""Compare two STEP files: bounding box, volume, part labels, hole inventory. It is not a full geometric proof."""

from pathlib import Path

from build123d import import_step

from rccar_mech import checks

POS_TOL = 0.01  # mm


def _key(h: checks.Hole):
    return (
        round(h.x / POS_TOL) * POS_TOL,
        round(h.y / POS_TOL) * POS_TOL,
        round(h.z / POS_TOL) * POS_TOL,
        round(h.diameter, 2),
    )


def diff(a_path: Path, b_path: Path) -> dict:
    a, b = import_step(a_path), import_step(b_path)
    ha = {_key(h): h for h in checks.holes(a)}
    hb = {_key(h): h for h in checks.holes(b)}
    sa, sb = a.bounding_box().size, b.bounding_box().size
    la = sorted(p.label for p in checks.parts(a))
    lb = sorted(p.label for p in checks.parts(b))
    out = {
        "volume_a": a.volume,
        "volume_b": b.volume,
        "volume_delta": b.volume - a.volume,
        "bbox_a": [sa.X, sa.Y, sa.Z],
        "bbox_b": [sb.X, sb.Y, sb.Z],
        "parts_removed": sorted(set(la) - set(lb)),
        "parts_added": sorted(set(lb) - set(la)),
        "holes_removed": [list(k) for k in sorted(set(ha) - set(hb))],
        "holes_added": [list(k) for k in sorted(set(hb) - set(ha))],
    }
    out["same"] = (
        abs(out["volume_delta"]) <= checks.REL_TOL * max(a.volume, 1.0)
        and all(abs(p - q) <= checks.BOX_TOL for p, q in zip(out["bbox_a"], out["bbox_b"]))
        and not (out["parts_removed"] or out["parts_added"] or out["holes_removed"] or out["holes_added"])
    )
    return out
