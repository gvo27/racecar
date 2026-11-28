"""Command line: build, check and diff one model. Make targets: mech-build, mech-check, mech-diff.

Exit codes: 0 = no errors (diff: same), 1 = check errors (diff: different), 2 = the command could not run.
"""

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

from build123d import Compound

from rccar_mech import checks, diff, export, models, params

FACT_FILES = ("print.toml", "hardware.toml")
DENSITY_UNIT = 1e-3  # g/cm3 * mm3 -> g


def _overrides(pairs):
    out = {}
    for p in pairs or []:
        key, _, value = p.partition("=")
        out[key] = value
    return out


def _facts() -> dict[str, dict]:
    return {n: params.load_facts(params.config_path(n)) for n in FACT_FILES if params.config_path(n).exists()}


def _copy(part):
    """A copy with label and color. Never put a part of the model into a new Compound: that moves it (new parent)."""
    c = copy.copy(part)
    c.label, c.color = part.label, part.color
    return c


def printed(asm: Compound) -> Compound:
    parts = [_copy(p) for p in checks.parts(asm) if not models.is_ref(p)]
    return Compound(children=parts, label=f"{asm.label}_printed")


def run_checks(name: str, asm: Compound, cfg: dict, out_dir: Path) -> list[checks.Finding]:
    print_cfg = params.load_facts(params.config_path("print.toml"))
    found = []
    every = checks.parts(asm)
    found += checks.labels(asm)
    if all(models.is_ref(p) for p in every):
        found.append(checks.Finding("MECH-EXPORT", "warning", name, "no printed part (all parts are ref_)"))
    for part in every:
        found += checks.validity(part)
    for part in every:
        if not models.is_ref(part):
            found += checks.walls(part, print_cfg)
            found += checks.bed_fit(part, print_cfg)
    found += checks.interference(every)
    found += models.acceptance(name, asm, cfg)
    step, stl = out_dir / f"{name}.step", out_dir / f"{name}.stl"
    for path in (step, stl):
        if not path.exists():
            found.append(checks.Finding("MECH-EXPORT", "error", path.name, "missing: run make mech-build"))
    if step.exists():
        found += checks.step_round_trip(asm, step)
    if stl.exists():
        found += checks.mesh(stl)
    return found


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report(name: str, asm: Compound, cfg: dict, found, out_dir: Path) -> dict:
    facts = _facts()
    density = facts["print.toml"]["material"]["density"]
    pr = printed(asm)
    bb = pr.bounding_box()
    cog = pr.center() if pr.children else None
    rep = {
        "model": name,
        "units": "mm",
        "parameters": cfg,
        "bbox_printed": {"min": [bb.min.X, bb.min.Y, bb.min.Z], "max": [bb.max.X, bb.max.Y, bb.max.Z]},
        "volume_printed_mm3": pr.volume,
        "mass_g": pr.volume * density * DENSITY_UNIT,
        "cog_printed": [cog.X, cog.Y, cog.Z] if cog is not None else None,
        "top_z_printed": bb.max.Z if pr.children else None,
        "parts": [{"label": p.label, "ref": models.is_ref(p), "volume_mm3": p.volume} for p in checks.parts(asm)],
        "holes": [h.__dict__ for h in checks.holes(pr)],
        "assumed": [f"{f}: [{t}]" for f, data in facts.items() for t in params.assumed(data)],
        "errors": sum(1 for f in found if f.severity == "error"),
        "warnings": sum(1 for f in found if f.severity == "warning"),
        "findings": [f.__dict__ for f in found],
        "files": {p.name: _sha(p) for p in sorted(out_dir.glob(f"{name}*")) if p.suffix in (".step", ".stl")},
    }
    (out_dir / "report.json").write_text(json.dumps(rep, indent=2, default=list) + "\n")
    return rep


def cmd_build(a) -> int:
    asm, _ = models.build(a.model, _overrides(a.set))
    mod = models.module(a.model)
    out_dir = Path(a.out)
    export.write_all(asm, out_dir, a.model, mod.STL_TOLERANCE, previews=not a.no_previews, stl_shape=printed(asm))
    print(f"mech-build: {a.model} -> {out_dir}")
    return 0


def cmd_check(a) -> int:
    asm, cfg = models.build(a.model, _overrides(a.set))
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    found = run_checks(a.model, asm, cfg, out_dir)
    rep = report(a.model, asm, cfg, found, out_dir)
    for f in found:
        print(f"  {f.id:<15} {f.severity:<7} {f.where}: {f.message}")
    heights = ""
    if rep["cog_printed"] is not None:
        heights = f", cog z {rep['cog_printed'][2]:.1f} mm, top z {rep['top_z_printed']:.1f} mm"
    print(
        f"mech-check: {a.model}: {rep['errors']} errors, {rep['warnings']} warnings, mass {rep['mass_g']:.1f} g{heights}"
    )
    for item in rep["assumed"]:
        print(f"  assumed: {item}")
    return 1 if rep["errors"] else 0


def cmd_diff(a) -> int:
    d = diff.diff(Path(a.a), Path(a.b))
    print(json.dumps(d, indent=2))
    return 0 if d["same"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rccar_mech")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("build", cmd_build), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("model")
        p.add_argument("--out", required=True)
        p.add_argument("--set", action="append", metavar="KEY=VALUE", help="override a design parameter")
        if name == "build":
            p.add_argument("--no-previews", action="store_true")
        p.set_defaults(fn=fn)
    p = sub.add_parser("diff")
    p.add_argument("a")
    p.add_argument("b")
    p.set_defaults(fn=cmd_diff)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (KeyError, params.ParamError, FileNotFoundError) as e:
        print(f"rccar_mech: {e}", file=sys.stderr)
        return 2
    except (ValueError, TypeError, RuntimeError, OSError, AttributeError) as e:  # a crash is not a check result
        print(f"rccar_mech: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
