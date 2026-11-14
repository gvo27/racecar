"""Board checks that KiCad DRC does not make (unplated, milled board). Make target: pcb-check.

check(board) -> list[str] of problems. CLI: check_board.py <board> [--limits milling.toml --waivers milling_waivers.toml]
exit 1 if there is any problem. Runs with the python3 of the KiCad image.
"""
import argparse
import os
import sys

import pcbnew
from pcbnew import FromMM, ToMM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import milling_check as mc  # noqa: E402
import placement  # noqa: E402

SCH_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
HIGH_CURRENT_MIN_W = 6.0
HIGH_CURRENT_NETS = ("VBAT_RAW", "VBAT")


def short(name):
    return name.lstrip("/")


def holes(board):
    """Every hole: (label, ref, diameter mm) for pads and vias."""
    out = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                s = p.GetDrillSize()
                out.append(("%s.%s" % (fp.GetReference(), p.GetNumber() or "-"), fp.GetReference(), ToMM(max(s.x, s.y))))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            out.append(("via", "via", ToMM(t.GetDrillValue())))
    return out


# Copper width along the current paths (Task 7b). Opening test on B.Cu: deflate the copper of the net by w/2 and
# inflate it by w/2; the listed pads must stay in one piece. (net, label, pads, width mm). A pad is "REF.PIN";
# "U2.GND_IN" / "U2.GND_OUT" are the two U2 GND pads (7, 8) next to VIN / the two (9, 10) next to VOUT.
STUB_MM = 2.5  # copper within this distance of a pad that is narrower than the opening counts at its own width
PATH_ROWS = [
    ("GND", "GND trunk J1 - U2 input - U1", ["J1.2", "U2.GND_IN", "U1.7", "U1.8", "U1.9", "U1.10"], 6.0),
    ("GND", "GND J6/J7 - U1", ["J6.2", "J7.2", "U1.7", "U1.8", "U1.9", "U1.10"], 1.6),
    ("GND", "GND U2 output - J8/J9/J11/C9", ["U2.GND_OUT", "J8.2", "J9.2", "J11.2", "C9.2"], 1.6),
    ("/VBAT_RAW", "VBAT_RAW J1 - F1", ["J1.1", "F1.1"], 6.0),
    ("VBAT", "VBAT F1 - U2 VIN - U1 VIN", ["F1.2", "U2.5", "U2.6", "U1.5", "U1.6"], 6.0),
    ("+5V_CPU", "+5V_CPU all pads", None, 1.6),
    ("+5V_SENS", "+5V_SENS all pads", None, 1.6),
]


def _net_copper(board, net, layer):
    """B.Cu copper of one net (zone fills, tracks, pads) as one polygon set, plus the pad polygons by label."""
    s = pcbnew.SHAPE_POLY_SET()
    pads = {}
    for z in board.Zones():
        if z.GetNetname() == net and not z.GetIsRuleArea() and z.IsOnLayer(layer):
            s.BooleanAdd(z.GetFilledPolysList(layer))
    for t in board.GetTracks():
        if t.GetNetname() == net and t.IsOnLayer(layer):
            t.TransformShapeToPolygon(s, layer, 0, FromMM(0.005), pcbnew.ERROR_INSIDE)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net and p.IsOnLayer(layer):
                q = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(q, layer, 0, FromMM(0.005), pcbnew.ERROR_INSIDE)
                s.BooleanAdd(q)
                pads.setdefault(fp.GetReference() + "." + p.GetNumber(), []).append((p.GetPosition(), q))
    s.Simplify()
    return s, pads


def _u2_gnd_ends(board):
    """Split the U2 GND pads (7-10) into the pair nearest the VIN pads (5, 6) and the pair nearest VOUT (11, 12)."""
    fp = board.FindFootprintByReference("U2")
    vin = [p.GetPosition() for p in fp.Pads() if p.GetNumber() in ("5", "6")]
    cx = sum(v.x for v in vin) / len(vin)
    cy = sum(v.y for v in vin) / len(vin)
    gnd = [p for p in fp.Pads() if p.GetNumber() in ("7", "8", "9", "10")]
    gnd.sort(key=lambda p: (p.GetPosition().x - cx) ** 2 + (p.GetPosition().y - cy) ** 2)
    return gnd[:2], gnd[2:]


def _opened_groups(board, net, labels, width_mm):
    """Groups of pad labels that stay joined after the opening of width_mm. Pads narrower than the opening
    are added back at their own width (they cannot pass the opening, but they must touch the opened copper)."""
    layer = pcbnew.B_Cu
    s, pads = _net_copper(board, net, layer)
    if net == "GND" and labels and any(l.startswith("U2.GND") for l in labels):
        near, far = _u2_gnd_ends(board)
        for name, plist in (("U2.GND_IN", near), ("U2.GND_OUT", far)):
            for p in plist:
                q = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(q, layer, 0, FromMM(0.005), pcbnew.ERROR_INSIDE)
                pads.setdefault(name, []).append((p.GetPosition(), q))
    o = pcbnew.SHAPE_POLY_SET(s)
    r = FromMM(width_mm / 2.0)
    o.Deflate(r, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
    o.Inflate(r, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
    if labels is None:
        labels = sorted(pads)
    for l in labels:
        for _, q in pads.get(l, []):
            o.BooleanAdd(q)
            # a pad narrower than the opening is measured at its own width: the copper within STUB_MM of it counts
            near = pcbnew.SHAPE_POLY_SET(q)
            near.Inflate(FromMM(STUB_MM), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.01))
            hit = pcbnew.SHAPE_POLY_SET()
            hit.BooleanIntersection(near, s)
            o.BooleanAdd(hit)
    o.Simplify()
    groups = {}
    for l in labels:
        if l not in pads:
            groups.setdefault("missing", []).append(l)
            continue
        for pos, _ in pads[l]:
            idx = -1
            for i in range(o.OutlineCount()):
                if o.Contains(pos, i):
                    idx = i
                    break
            groups.setdefault(idx, []).append(l)
    return groups


def path_width(board, net, pads, width_mm):
    """Opening test on B.Cu: the pads of `net` (list of "REF.PIN", or None = all pads of the net) must stay in one
    piece after deflate+inflate by width_mm / 2. Returns the problems ([] = the path is at least width_mm wide)."""
    g = _opened_groups(board, net, pads, width_mm)
    if len(g) <= 1:
        return []
    return ["%s: pads split into %d pieces at %.1f mm: %s" % (
        net, len(g), width_mm, "; ".join(",".join(sorted(set(v))) for v in g.values()))]


def path_opening_mm(board, net, pads, lo=0.5, hi=8.0, step=0.05):
    """Largest opening width (mm) at which the pads stay in one piece (bisection, 0.05 mm steps). 0.0 if none."""
    if len(_opened_groups(board, net, pads, hi)) <= 1:
        return hi
    if len(_opened_groups(board, net, pads, lo)) > 1:
        return 0.0
    while hi - lo > step:
        mid = (lo + hi) / 2
        if len(_opened_groups(board, net, pads, mid)) <= 1:
            lo = mid
        else:
            hi = mid
    return round(lo, 2)


def check_paths(board):
    problems = []
    for net, label, pads, w in PATH_ROWS:
        problems += ["path width %s: %s" % (label, p) for p in path_width(board, net, pads, w)]
    return problems


MODULE_GAP_MM = 1.5  # min courtyard gap between two Pololu_D36V50Fx modules (body gap >= 2.0 mm: +-0.3 mm edge tolerance, heat)
EDGE_TOL_MM = 0.05  # a courtyard that touches the outline line is inside (the mounting holes sit on it)


def check_courtyards(board):
    """Courtyards of parts on one side must not overlap each other and must not cross the board edge.
    KiCad DRC reports the overlap (courtyards_overlap) once the footprints have real courtyards; the edge crossing
    it does not report, and a module whose body sticks out of the board is a fab and fit problem."""
    problems = []
    edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    out = edges[0].GetBoundingBox()
    for e in edges[1:]:
        out.Merge(e.GetBoundingBox())
    out.Inflate(FromMM(EDGE_TOL_MM))
    cys = []
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        side = pcbnew.F_Cu if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_Cu
        cy = fp.GetCourtyard(pcbnew.F_CrtYd if side == pcbnew.F_Cu else pcbnew.B_CrtYd)
        if not cy.OutlineCount():
            problems.append("courtyard: %s has none" % fp.GetReference())
            continue
        if not out.Contains(cy.BBox()):
            problems.append("courtyard of %s crosses the board edge" % fp.GetReference())
        cys.append((fp.GetReference(), side, cy))
    for i, (ra, sa, ca) in enumerate(cys):
        for rb, sb, cb in cys[i + 1:]:
            if sa == sb and ca.Collide(cb, 0):
                problems.append("courtyards overlap on %s: %s and %s" % ("F" if sa == pcbnew.F_Cu else "B", ra, rb))
    mods = [(fp.GetReference(), cy) for fp in board.GetFootprints()
            if fp.GetFPID().GetLibItemName() == "Pololu_D36V50Fx"
            for cy in [fp.GetCourtyard(pcbnew.F_CrtYd)]]
    for i, (ra, ca) in enumerate(mods):
        for rb, cb in mods[i + 1:]:
            if ca.Collide(cb, FromMM(MODULE_GAP_MM)) and not ca.Collide(cb, 0):
                problems.append("module courtyards of %s and %s are closer than %.1f mm" % (ra, rb, MODULE_GAP_MM))
    return problems


def check(board, limits=None, waivers=None):
    problems = []
    # 1. F.Cu copper on a THT pad (open on an unplated board)
    lim = limits or mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))
    ctx = mc.Ctx(board, lim)
    found = []
    mc.check_fcu_tht(ctx, found)
    problems += ["F.Cu on THT pad: %s" % f[2] for f in found]
    # 2. holes: in the drill set, or a bored hole (>= milled_hole_min) listed in MILLED_HOLES
    milled = set(placement.MILLED_HOLES)
    for label, ref, d in holes(board):
        if any(abs(d - s) < 0.005 for s in lim.drills):
            continue
        if d >= lim.milled_hole_min - 0.005 and any(r == ref and abs(d - m) < 0.005 for r, m in milled):
            continue
        problems.append("hole %.2f mm at %s is not in the drill set (%.1f to %.1f mm) and not a bored hole (MILLED_HOLES, >= %.2f mm)" % (
            d, label, min(lim.drills), max(lim.drills), lim.milled_hole_min))
    # 3. rivet vias
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            drill, dia = ToMM(t.GetDrillValue()), ToMM(t.GetWidth(pcbnew.F_Cu))
            if abs(drill - lim.via_drill) > 0.005 or abs(dia - lim.via_pad) > 0.005:
                problems.append("via %.2f/%.2f mm at %s (rivet via is %.1f/%.1f)" % (dia, drill, ctx.xy(t.GetPosition()), lim.via_pad, lim.via_drill))
    # 4. HighCurrent tracks
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and short(t.GetNetname()) in HIGH_CURRENT_NETS + ("GND",):
            if ToMM(t.GetWidth()) < HIGH_CURRENT_MIN_W - 1e-6:
                problems.append("%s track %.2f mm wide at %s (HighCurrent minimum %.1f mm)" % (short(t.GetNetname()), ToMM(t.GetWidth()), ctx.xy(t.GetStart()), HIGH_CURRENT_MIN_W))
    # 5. courtyards (overlap per side, board edge)
    problems += check_courtyards(board)
    # 6. milling check: unwaived errors. MILL-DEPTH is a finding about the assumed limits (owner/lab tech), not the board:
    #    it is the only rule id left out here, and `make pcb-mill-check` keeps it visible.
    findings = mc.check(board, lim)
    groups = mc.triage(findings, waivers or [])
    for f in groups["errors"]:
        problems.append("%s %s: %s" % (f[0], f[2], f[5]))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board")
    ap.add_argument("--limits", default=os.path.join(SCH_DIR, "milling.toml"))
    ap.add_argument("--waivers", default=os.path.join(SCH_DIR, "milling_waivers.toml"))
    ap.add_argument("--widths", action="store_true", help="print the measured opening width per path row")
    args = ap.parse_args(argv)
    board = pcbnew.LoadBoard(args.board)
    problems = check(board, mc.load_limits(args.limits), mc.load_waivers(args.waivers)) + check_paths(board)
    if args.widths:
        for net, label, pads, w in PATH_ROWS:
            print("check_board: opening %-34s need %.1f mm, measured %.2f mm" % (label, w, path_opening_mm(board, net, pads)))
    for p in problems:
        print("check_board: " + p)
    print("check_board: %d problems" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
