"""Write the design rules of a board (design_rules.toml, rules.py) into its KiCad project files. Make target: pcb-rules.

- `<board>.kicad_pro`: rule minimums, and clearance, track width and rivet via of each net class.
- `<board>.kicad_dru`: one clearance rule for each `[[exception]]` (`<ref>_fine`).

`--check` (the default) compares and writes nothing. Exit 1 = the project files do not agree with the design rules.
`--write` changes a file only when it does not agree. Stdlib only.
"""
import argparse
import json
import os
import re
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab  # noqa: E402
import paths  # noqa: E402
import rules  # noqa: E402

DRU_RULE = re.compile(r'\(rule\s+(\S+)\s+\(condition\s+"([^"]*)"\)\s+\(constraint\s+clearance\s+\(min\s+([0-9.]+)mm\)\)\s*\)', re.S)


def condition(e):
    """zones = false (rev A): the lower clearance is for the pads of the part against pads, tracks and vias, not zone fill.
    zones = true: against pads and zone fill, not tracks and vias. Note: build_pcb.py also puts the lower clearance on
    the pads then (the zone filler needs it), and KiCad DRC uses that pad value for tracks too. The milling check
    (MILL-GAP) reports a track that is too near such a pad."""
    if e.own_pads:  # a pin header: only its own pads are closer than the board clearance
        return "A.Type == 'Pad' && B.Type == 'Pad' && A.Reference == '%s' && B.Reference == '%s'" % (e.ref, e.ref)
    base = "A.Type == 'Pad' && A.Reference == '%s'" % e.ref
    return base + (" && B.Type != 'Track' && B.Type != 'Via'" if e.zones else " && B.Type != 'Zone'")


def want_dru(r):
    return [("%s_fine" % e.ref, condition(e), e.clearance) for e in r.exceptions]


def read_dru(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [(n, c, float(v)) for n, c, v in DRU_RULE.findall(fh.read())]


def dru_text(r):
    out = ["(version 1)", "",
           "# Made by pcb/tools/gen_rules.py from the [[exception]] entries of the design rules (%s)." % os.path.basename(r.path),
           "# Do not edit: change the design rules, then run `make pcb-rules`. Zone fill is not covered: a pour keeps the",
           "# zone clearance from these pads, unless the exception has zones = true."]
    for e in r.exceptions:
        out += ["# %s: %s" % (e.ref, e.reason),
                "(rule %s_fine" % e.ref, '\t(condition "%s")' % condition(e),
                "\t(constraint clearance (min %smm))" % ("%g" % e.clearance), ")"]
    return "\n".join(out) + "\n"


def want_pro(r, via_drill, via_pad):
    """(path in the JSON, wanted value) pairs."""
    # min_clearance is the board clearance: the exception rules of the .kicad_dru go below it for their parts only.
    # An exception with zones = true puts the lower clearance on the pads (build_pcb.py), and KiCad reports a pad
    # clearance below min_clearance, so min_clearance is then the lowest of these exceptions.
    w = [(("board", "design_settings", "rules", "min_clearance"), min([r.clearance] + [e.clearance for e in r.exceptions if e.zones])),
         (("board", "design_settings", "rules", "min_track_width"), r.track_min),
         (("board", "design_settings", "rules", "min_copper_edge_clearance"), r.edge_clearance),
         (("board", "design_settings", "rules", "min_via_annular_width"), r.annular_min)]
    for name in rules.CLASS_ORDER:
        for key, val in (("clearance", r.clearance), ("track_width", r.track_width[name]), ("via_diameter", via_pad), ("via_drill", via_drill)):
            w.append((("net_settings", "classes", name, key), val))
    return w


def _get(pro, path):
    node = pro
    for i, key in enumerate(path):
        if path[:2] == ("net_settings", "classes") and i == 2:
            node = next(c for c in node if c["name"] == key)
        else:
            node = node[key]
    return node


def _set(pro, path, val):
    parent = _get(pro, path[:-1])
    parent[path[-1]] = val


def diff_pro(pro, wanted):
    return [(p, _get(pro, p), v) for p, v in wanted if abs(float(_get(pro, p)) - v) > 1e-9]


def run(board_dir, write):
    r = rules.load(rules.rules_file(board_dir))
    with open(lab.limits_file(), "rb") as fh:
        lim = tomllib.load(fh)
    problems = rules.check_against_lab(r, lim)
    pro_path = os.path.join(board_dir, paths.STEM + ".kicad_pro")
    dru_path = os.path.join(board_dir, paths.STEM + ".kicad_dru")
    with open(pro_path, encoding="utf-8") as fh:
        pro = json.load(fh)
    wanted = want_pro(r, lim["via_drill"]["value"], lim["via_pad"]["value"])
    changes = diff_pro(pro, wanted)
    dru_ok = read_dru(dru_path) == want_dru(r)
    for p, old, new in changes:
        print("pcb-rules: %s %s: %s -> %s" % (os.path.basename(pro_path), ".".join(p), old, new))
    if not dru_ok:
        print("pcb-rules: %s does not hold the exception rules of the design rules" % os.path.basename(dru_path))
    if write:
        if changes:
            for p, _, new in changes:
                _set(pro, p, new)
            with open(pro_path, "w", encoding="utf-8") as fh:
                json.dump(pro, fh, indent=2, sort_keys=True)
                fh.write("\n")
        if not dru_ok:
            with open(dru_path, "w", encoding="utf-8") as fh:
                fh.write(dru_text(r))
        changes, dru_ok = [], True
    for p in problems:
        print("pcb-rules: %s" % p, file=sys.stderr)
    assumed = r.assumed()
    print("pcb-rules: %s, %d values assumed%s" % (os.path.relpath(r.path, paths.REPO_ROOT), len(assumed), ": " + ", ".join(assumed) if assumed else ""))
    ok = not changes and dru_ok and not problems
    print("pcb-rules: %s" % ("project files agree with the design rules" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--board-dir", default=paths.board_dir())
    ap.add_argument("--write", action="store_true", help="change the project files that do not agree")
    args = ap.parse_args(argv)
    return run(args.board_dir, args.write)


if __name__ == "__main__":
    sys.exit(main())
