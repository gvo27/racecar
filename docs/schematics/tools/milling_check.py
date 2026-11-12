"""Milling check for the power board (Makera Carvera isolation milling).

DRC-clean does not mean CNC-millable. Rule ids and groups: .claude/skills/pcb-milling-check/SKILL.md
Limits: docs/schematics/milling.toml. Waivers: docs/schematics/milling_waivers.toml.

CLI: milling_check.py <board> --limits <toml> [--waivers <toml>] --json <out>
Exit: 0 = no unwaived error, 1 = unwaived errors (MILL-DEPTH counts), 2 = the check could not run.
Runs with the python3 of the KiCad image (pcbnew).
"""
import argparse
import json
import math
import sys
import tomllib
from dataclasses import dataclass

import pcbnew
from pcbnew import FromMM, ToMM

# Finding = (rule_id, severity "error"|"warning", where, value, limit, message)
FORBIDDEN_WAIVERS = ("MILL-FCU-THT", "MILL-RIVET-ACCESS")
EPS = 1000  # 0.001 mm in nm: "touching" tolerance
SLIVER_MIN_AREA_MM2 = 0.05  # ignores corner rounding of the opening test (0.013 mm2 per corner)


@dataclass
class Bit:
    name: str
    angle: float
    tip: float


@dataclass
class Limits:
    copper: float
    bits: list
    depth_min: float
    depth_max: float
    depth_err: float
    drills: list
    endmill_min: float
    via_drill: float
    via_pad: float
    annular_min: float
    track_min: float
    edge_clear: float
    conn_edge: float

    @property
    def depth_worst(self):
        return self.depth_max + self.depth_err


def cut_width(tip, angle_deg, depth):
    return tip + 2.0 * depth * math.tan(math.radians(angle_deg) / 2.0)


def load_limits(path):
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    def val(key):
        t = raw[key]
        if t.get("status") not in ("assumed", "confirmed") or not t.get("source"):
            raise ValueError("%s: needs status (assumed|confirmed) and source" % key)
        return t["value"]

    bits = []
    for b in raw.get("isolation_bit", []):
        if b.get("status") not in ("assumed", "confirmed") or not b.get("source"):
            raise ValueError("isolation_bit %s: needs status and source" % b.get("name"))
        bits.append(Bit(b["name"], float(b["angle_deg"]), float(b["tip_mm"])))
    if not bits:
        raise ValueError("no isolation_bit")
    return Limits(
        copper=val("copper_thickness"), bits=bits, depth_min=val("cut_depth_min"),
        depth_max=val("cut_depth_max"), depth_err=val("cut_depth_error"),
        drills=sorted(val("drill_set")), endmill_min=val("endmill_min"),
        via_drill=val("via_drill"), via_pad=val("via_pad"), annular_min=val("annular_min"),
        track_min=val("track_min"), edge_clear=val("edge_clearance"), conn_edge=val("connector_edge_distance"))


def load_waivers(path):
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    out = []
    for w in raw.get("waiver", []):
        for k in ("rule", "location", "reason", "who", "date"):
            if not w.get(k):
                raise ValueError("waiver %r: missing field %s" % (w, k))
        if w["rule"] in FORBIDDEN_WAIVERS:
            raise ValueError("waiver for %s is not allowed" % w["rule"])
        out.append(dict(w))
    return out


def triage(findings, waivers):
    """Groups: errors (unwaived), waived [(finding, waiver)], questions (limits findings), bits, warnings."""
    g = {"errors": [], "waived": [], "questions": [], "bits": [], "warnings": []}
    for f in findings:
        if f[0] == "MILL-DEPTH":
            g["questions"].append(f)
            continue
        w = next((w for w in waivers if w["rule"] == f[0] and w["location"] in f[2]), None)
        if w:
            g["waived"].append((f, w))
        elif f[0] == "MILL-GAP-BIT":
            g["bits"].append(f)
        elif f[1] == "error":
            g["errors"].append(f)
        else:
            g["warnings"].append(f)
    return g


class Ctx:
    def __init__(self, board, lim):
        self.b = board
        self.lim = lim
        o = board.GetDesignSettings().GetAuxOrigin()
        self.ox, self.oy = o.x, o.y

    def xy(self, pos):
        return "(%.2f, %.2f)" % (ToMM(pos.x - self.ox), ToMM(pos.y - self.oy))


class Item:
    def __init__(self, shape, net, desc, pos, kind, layer):
        self.shape, self.net, self.desc, self.pos, self.kind, self.layer = shape, net, desc, pos, kind, layer
        self.bbox = shape.BBox()


def copper_layers(board):
    return [pcbnew.F_Cu, pcbnew.B_Cu]


def collect(ctx, layer):
    b = ctx.b
    lname = b.GetLayerName(layer)
    items = []
    for t in b.GetTracks():
        if not t.IsOnLayer(layer):
            continue
        is_via = t.Type() == pcbnew.PCB_VIA_T
        net = t.GetNetCode()
        kind = "via" if is_via else "track"
        items.append(Item(t.GetEffectiveShape(layer), net, "%s %s net %s at %s" % (kind, lname, t.GetNetname(), ctx.xy(t.GetStart() if not is_via else t.GetPosition())),
                          t.GetPosition() if is_via else t.GetStart(), kind, layer))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if not p.IsOnLayer(layer) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            items.append(Item(p.GetEffectiveShape(layer), p.GetNetCode(),
                              "pad %s.%s %s net %s at %s" % (fp.GetReference(), p.GetNumber(), lname, p.GetNetname() or "-", ctx.xy(p.GetPosition())),
                              p.GetPosition(), "pad", layer))
    for z in b.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer) or not z.IsFilled():
            continue
        ps = z.GetFilledPolysList(layer)
        if ps.OutlineCount() == 0:
            continue
        items.append(Item(ps, z.GetNetCode(), "zone fill %s net %s" % (lname, z.GetNetname()), ps.BBox().Centre(), "zone", layer))
    return items


def distance_nm(a, b, hi):
    lo = 0
    if a.Collide(b, 0):
        return 0.0
    for _ in range(14):
        mid = (lo + hi) // 2
        if a.Collide(b, mid):
            hi = mid
        else:
            lo = mid
    return float(hi) / 1e6


def check_gaps(ctx, out):
    lim = ctx.lim
    widths = [(bt, cut_width(bt.tip, bt.angle, lim.depth_worst)) for bt in lim.bits]
    wmin = min(w for _, w in widths)
    wmax = max(w for _, w in widths)
    reach = FromMM(wmax) + 1000
    for layer in copper_layers(ctx.b):
        items = collect(ctx, layer)
        for i in range(len(items)):
            a = items[i]
            abb = a.bbox.GetInflated(reach)
            for j in range(i + 1, len(items)):
                c = items[j]
                if a.net != 0 and a.net == c.net:
                    continue
                if not abb.Intersects(c.bbox):
                    continue
                if not a.shape.Collide(c.shape, reach):
                    continue
                d = distance_nm(a.shape, c.shape, reach)
                where = "%s | %s" % (a.desc, c.desc)
                if d < wmin - 1e-6:
                    out.append(("MILL-GAP", "error", where, d, wmin,
                                "gap %.3f mm is below the narrowest bit cut width %.3f mm at worst-case depth %.2f mm" % (d, wmin, lim.depth_worst)))
                elif d < wmax - 1e-6:
                    fits = [bt.name for bt, w in widths if w <= d + 1e-6]
                    out.append(("MILL-GAP-BIT", "warning", where, d, wmax,
                                "gap %.3f mm: only %s fit (cut width at worst-case depth)" % (d, ", ".join(fits))))


def check_depth(ctx, out):
    lim = ctx.lim
    dmin = lim.depth_min - lim.depth_err
    if dmin < lim.copper - 1e-9:
        out.append(("MILL-DEPTH", "error", "limits (milling.toml)", dmin, lim.copper,
                    "min depth %.3f mm (%.2f - %.2f) is below the copper thickness %.3f mm: a shallow cut may not go through. "
                    "The min depth must be at least %.2f mm. Question for the owner and the lab tech (assumed depth range)."
                    % (dmin, lim.depth_min, lim.depth_err, lim.copper, lim.copper + lim.depth_err)))


def hole_list(ctx):
    """(kind, label, pos, dmin, dmax) for each hole."""
    res = []
    for fp in ctx.b.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                s = p.GetDrillSize()
                res.append(("pad", "%s.%s" % (fp.GetReference(), p.GetNumber()), p.GetPosition(),
                            ToMM(min(s.x, s.y)), ToMM(max(s.x, s.y)), p))
    for t in ctx.b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            d = ToMM(t.GetDrillValue())
            res.append(("via", "via", t.GetPosition(), d, d, t))
    return res


def check_holes(ctx, out):
    lim = ctx.lim
    big = max(lim.drills)
    for kind, label, pos, dmin, dmax, item in hole_list(ctx):
        where = "%s %s hole %.2f mm at %s" % (kind, label, dmax, ctx.xy(pos))
        for d in (dmin, dmax):
            if any(abs(d - s) < 0.005 for s in lim.drills):
                continue
            if d > big + 0.005 and d >= lim.endmill_min:
                continue  # milled hole
            out.append(("MILL-DRILL", "error", where, d, None,
                        "hole %.3f mm is not in the drill set %s and is not a milled hole (> %.1f mm)" % (d, lim.drills, big)))
            break
        if kind == "via":
            dia = ToMM(item.GetWidth(pcbnew.F_Cu))
            ring = (dia - dmax) / 2.0
        elif item.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        else:
            sz = item.GetSize(pcbnew.F_Cu) if hasattr(item, "GetSize") else item.GetSize()
            ring = (ToMM(min(sz.x, sz.y)) - dmax) / 2.0
        if ring < lim.annular_min - 1e-6:
            out.append(("MILL-ANNULAR", "error", where, ring, lim.annular_min,
                        "annular ring %.3f mm is below %.2f mm" % (ring, lim.annular_min)))


def check_vias(ctx, out):
    lim = ctx.lim
    for t in ctx.b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T:
            continue
        drill, dia = ToMM(t.GetDrillValue()), ToMM(t.GetWidth(pcbnew.F_Cu))
        if abs(drill - lim.via_drill) > 0.005 or abs(dia - lim.via_pad) > 0.005:
            out.append(("MILL-VIA", "error", "via net %s at %s" % (t.GetNetname(), ctx.xy(t.GetPosition())), dia, lim.via_pad,
                        "via %.2f/%.2f mm (pad/drill) differs from the rivet via %.2f/%.2f mm" % (dia, drill, lim.via_pad, lim.via_drill)))


def check_fcu_tht(ctx, out):
    b = ctx.b
    tht = [(fp, p) for fp in b.GetFootprints() for p in fp.Pads()
           if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and p.IsOnLayer(pcbnew.F_Cu)]
    tracks = [t for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.F_Cu]
    zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(pcbnew.F_Cu) and z.IsFilled()]
    for fp, p in tht:
        ps = p.GetEffectiveShape(pcbnew.F_Cu)
        bb = ps.BBox().GetInflated(EPS)
        for t in tracks:
            ts = t.GetEffectiveShape(pcbnew.F_Cu)
            if bb.Intersects(ts.BBox()) and ts.Collide(ps, EPS):
                out.append(("MILL-FCU-THT", "error", "pad %s.%s | F.Cu track net %s at %s" % (fp.GetReference(), p.GetNumber(), t.GetNetname(), ctx.xy(t.GetStart())),
                            None, None, "F.Cu track touches a THT pad (holes are not plated; the joint is on B.Cu)"))
        for z in zones:
            fill = z.GetFilledPolysList(pcbnew.F_Cu)
            if fill.OutlineCount() and fill.Collide(ps, EPS):
                out.append(("MILL-FCU-THT", "error", "pad %s.%s | F.Cu zone fill net %s" % (fp.GetReference(), p.GetNumber(), z.GetNetname()),
                            None, None, "F.Cu zone fill touches a THT pad (holes are not plated; the joint is on B.Cu)"))


def courtyard(fp):
    layer = pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
    fp.BuildCourtyardCaches()
    cy = fp.GetCourtyard(layer)
    return cy if cy.OutlineCount() else None


def check_rivet_access(ctx, out):
    fps = [(fp, courtyard(fp)) for fp in ctx.b.GetFootprints()]
    for t in ctx.b.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T:
            continue
        vs = t.GetEffectiveShape(pcbnew.F_Cu)
        for fp, cy in fps:
            if cy is None:
                continue
            if cy.Contains(t.GetPosition()) or cy.Collide(vs, 0):
                out.append(("MILL-RIVET-ACCESS", "error", "via net %s at %s | footprint %s (%s side)" % (
                    t.GetNetname(), ctx.xy(t.GetPosition()), fp.GetReference(), "F" if fp.GetLayer() == pcbnew.F_Cu else "B"),
                    None, None, "via is inside a courtyard: the rivet cannot be soldered on both sides"))


def edge_shapes(board):
    return [d.GetEffectiveShape() for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]


def check_edges(ctx, out):
    edges = edge_shapes(ctx.b)
    if not edges:
        return
    lim = ctx.lim
    clr = FromMM(lim.edge_clear)
    for layer in copper_layers(ctx.b):
        for it in collect(ctx, layer):
            for e in edges:
                if it.shape.Collide(e, clr):
                    d = distance_nm(it.shape, e, clr)
                    out.append(("MILL-EDGE", "error", it.desc, d, lim.edge_clear,
                                "copper is %.3f mm from the board edge (minimum %.2f mm)" % (d, lim.edge_clear)))
                    break
    dist = FromMM(lim.conn_edge)
    for fp in ctx.b.GetFootprints():
        if not fp.GetReference().startswith("J"):
            continue
        cy = courtyard(fp)
        if cy is None:
            continue
        if not any(cy.Collide(e, dist) for e in edges):
            out.append(("MILL-CONN-EDGE", "warning", "footprint %s at %s" % (fp.GetReference(), ctx.xy(fp.GetPosition())), None, lim.conn_edge,
                        "connector courtyard is more than %.1f mm from the board edge" % lim.conn_edge))


def check_zones(ctx, out):
    lim = ctx.lim
    me = FromMM(0.005)
    r = FromMM(lim.track_min / 2.0)
    for z in ctx.b.Zones():
        if z.GetIsRuleArea():
            continue
        for layer in copper_layers(ctx.b):
            if not z.IsOnLayer(layer) or not z.IsFilled():
                continue
            fill = z.GetFilledPolysList(layer)
            if fill.OutlineCount() == 0:
                continue
            lname = ctx.b.GetLayerName(layer)
            # slivers: copper that an opening with half the min track width removes
            a = pcbnew.SHAPE_POLY_SET(fill)
            o = pcbnew.SHAPE_POLY_SET(fill)
            o.Deflate(r, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, me)
            o.Inflate(r, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, me)
            a.BooleanSubtract(o)
            for i in range(a.OutlineCount()):
                one = pcbnew.SHAPE_POLY_SET()
                one.AddOutline(a.COutline(i))
                area = abs(one.Area()) / 1e12
                if area >= SLIVER_MIN_AREA_MM2:
                    out.append(("MILL-SLIVER", "warning", "zone fill %s net %s at %s" % (lname, z.GetNetname(), ctx.xy(one.BBox().Centre())),
                                area, lim.track_min, "zone fill has copper narrower than %.2f mm (%.2f mm2 removed by an opening test)" % (lim.track_min, area)))
            # islands: fill pieces that touch no item of the zone net
            same = [it for it in collect(ctx, layer) if it.net == z.GetNetCode() and it.kind != "zone"]
            for i in range(fill.OutlineCount()):
                isl = pcbnew.SHAPE_POLY_SET()
                isl.AddOutline(fill.COutline(i))
                for h in range(fill.HoleCount(i)):
                    isl.AddHole(fill.CHole(i, h))
                if not any(isl.Collide(it.shape, EPS) or isl.Contains(it.pos) for it in same):
                    out.append(("MILL-ISLAND", "warning", "zone fill %s net %s at %s" % (lname, z.GetNetname(), ctx.xy(isl.BBox().Centre())),
                                abs(isl.Area()) / 1e12, None, "zone island touches no item of net %s" % z.GetNetname()))


def check(board, limits):
    ctx = Ctx(board, limits)
    out = []
    check_depth(ctx, out)
    check_gaps(ctx, out)
    check_holes(ctx, out)
    check_vias(ctx, out)
    check_fcu_tht(ctx, out)
    check_rivet_access(ctx, out)
    check_edges(ctx, out)
    check_zones(ctx, out)
    return out


def report(groups):
    lines = []
    lines.append("milling-check: %d errors (unwaived), %d waived, %d owner/lab-tech questions, %d warnings, %d gap-bit areas" % (
        len(groups["errors"]), len(groups["waived"]), len(groups["questions"]), len(groups["warnings"]), len(groups["bits"])))
    counts = {}
    for k in ("errors", "warnings", "bits"):
        for f in groups[k]:
            counts[f[0]] = counts.get(f[0], 0) + 1
    for rid, n in sorted(counts.items()):
        lines.append("  %-18s %d" % (rid, n))
    for title, key in (("ERRORS", "errors"), ("OWNER/LAB-TECH QUESTIONS", "questions"), ("MILL-GAP-BIT AREAS", "bits"), ("WARNINGS", "warnings")):
        if groups[key]:
            lines.append(title)
            for f in groups[key]:
                lines.append("  %s %s: %s" % (f[0], f[2], f[5]))
    if groups["waived"]:
        lines.append("WAIVED")
        for f, w in groups["waived"]:
            lines.append("  %s %s: waived by %s (%s): %s" % (f[0], f[2], w["who"], w["date"], w["reason"]))
    return "\n".join(lines)


def run(board_path, limits_path, waivers_path=None):
    board = pcbnew.LoadBoard(board_path)
    findings = check(board, load_limits(limits_path))
    waivers = load_waivers(waivers_path) if waivers_path else []
    return findings, triage(findings, waivers)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board")
    ap.add_argument("--limits", required=True)
    ap.add_argument("--waivers")
    ap.add_argument("--json")
    args = ap.parse_args(argv)
    try:
        findings, groups = run(args.board, args.limits, args.waivers)
    except Exception as exc:  # noqa: BLE001 - exit 2 = the check could not run
        print("milling-check: cannot run: %s" % exc, file=sys.stderr)
        return 2
    print(report(groups))
    if args.json:
        ser = {k: [list(f) for f in v] for k, v in groups.items() if k != "waived"}
        ser["waived"] = [{"finding": list(f), "waiver": w} for f, w in groups["waived"]]
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(ser, fh, indent=1)
    return 1 if groups["errors"] or any(f[1] == "error" for f in groups["questions"]) else 0


if __name__ == "__main__":
    sys.exit(main())
