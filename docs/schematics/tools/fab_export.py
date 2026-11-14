"""Fab outputs of the power board for the lab's Fusion 360 template (Carvera isolation milling). Make target: pcb-fab.

Writes 5 files to the output directory, all in the lab frame (placement.board_to_lab): origin = dowel 1 center,
x along the stock long side, mm, top view. B.Cu is NOT mirrored (Setup C flips the stock).
  rc_power_board-F_Cu.dxf, rc_power_board-B_Cu.dxf   union of all copper of the layer, closed LWPOLYLINE loops
                                                    (outer loops and the holes of the pour), one DXF layer each
  rc_power_board-Edge_Cuts.dxf                      board outline, one closed loop
  rc_power_board.drl                                Excellon, metric, one tool per diameter, 2 dowels as own tool
  rc_power_board-drl_map.dxf                        one circle per hole at its true diameter, one DXF layer per tool
KiCad's own DXF is not used: it has drill circles on Edge.Cuts and overlapping pad, track and zone outlines.
Runs with the python3 of the KiCad image (pcbnew).
"""
import argparse
import os
import sys
import tomllib

import pcbnew
from pcbnew import FromMM, ToMM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import placement  # noqa: E402

SCH_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STEM = "rc_power_board"
FILES = [STEM + "-F_Cu.dxf", STEM + "-B_Cu.dxf", STEM + "-Edge_Cuts.dxf", STEM + ".drl", STEM + "-drl_map.dxf"]
MAX_ERR = FromMM(0.005)  # arc and circle approximation (mm)
HEAL = FromMM(0.001)  # close zero-width slits of the zone filler (same value as milling_check.py)
DEC = 4  # decimals (0.1 um)


def drill_max():
    with open(os.path.join(SCH_DIR, "milling.toml"), "rb") as fh:
        return max(tomllib.load(fh)["drill_set"]["value"])


def edge_rect(board):
    edges = [e for e in board.GetDrawings() if e.GetLayer() == pcbnew.Edge_Cuts]
    if len(edges) != 1 or edges[0].GetShape() != pcbnew.SHAPE_T_RECT:
        raise RuntimeError("Edge.Cuts must be one rectangle")
    return edges[0]


# ---- board -> lab frame -----------------------------------------------------------------------------------------
class Frame:
    """KiCad nm coordinates (y down) -> lab frame mm. The outline's lower-left corner is the board table origin."""

    def __init__(self, board):
        e = edge_rect(board)  # the line centers, not the stroke: the table origin is the outline's lower-left corner
        self.left, self.bottom = min(e.GetStart().x, e.GetEnd().x), max(e.GetStart().y, e.GetEnd().y)
        self.w, self.h = ToMM(abs(e.GetEnd().x - e.GetStart().x)), ToMM(abs(e.GetEnd().y - e.GetStart().y))
        if abs(self.w - placement.OUTLINE_W) > 0.1 or abs(self.h - placement.OUTLINE_H) > 0.1:
            raise RuntimeError("outline %.2f x %.2f mm differs from placement.py %.1f x %.1f" % (self.w, self.h, placement.OUTLINE_W, placement.OUTLINE_H))

    def lab(self, x, y):
        return placement.board_to_lab(ToMM(x - self.left), ToMM(self.bottom - y))


# ---- DXF writer (R2000 ASCII, mm) -------------------------------------------------------------------------------
class Dxf:
    def __init__(self, layers):
        self.layers = list(layers)
        self.ents = []
        self.h = 0x20

    def handle(self):
        self.h += 1
        return "%X" % self.h

    def _g(self, out, code, val):
        out.append("%3d" % code)
        out.append(str(val))

    def polyline(self, layer, pts):
        e = []
        for c, v in ((0, "LWPOLYLINE"), (5, self.handle()), (100, "AcDbEntity"), (8, layer), (100, "AcDbPolyline"),
                     (90, len(pts)), (70, 1)):
            self._g(e, c, v)
        for x, y in pts:
            self._g(e, 10, "%.*f" % (DEC, x))
            self._g(e, 20, "%.*f" % (DEC, y))
        self.ents.append(e)

    def circle(self, layer, x, y, r):
        e = []
        for c, v in ((0, "CIRCLE"), (5, self.handle()), (100, "AcDbEntity"), (8, layer), (100, "AcDbCircle"),
                     (10, "%.*f" % (DEC, x)), (20, "%.*f" % (DEC, y)), (30, "0.0"), (40, "%.*f" % (DEC, r))):
            self._g(e, c, v)
        self.ents.append(e)

    def text(self):
        out = []
        g = lambda c, v: self._g(out, c, v)  # noqa: E731
        g(0, "SECTION"); g(2, "HEADER")
        g(9, "$ACADVER"); g(1, "AC1015")
        g(9, "$INSUNITS"); g(70, 4)
        g(9, "$MEASUREMENT"); g(70, 1)
        g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "TABLES")
        g(0, "TABLE"); g(2, "LTYPE"); g(5, "5"); g(100, "AcDbSymbolTable"); g(70, 1)
        g(0, "LTYPE"); g(5, "6"); g(100, "AcDbSymbolTableRecord"); g(100, "AcDbLinetypeTableRecord")
        g(2, "CONTINUOUS"); g(70, 0); g(3, "Solid line"); g(72, 65); g(73, 0); g(40, "0.0")
        g(0, "ENDTAB")
        g(0, "TABLE"); g(2, "LAYER"); g(5, "10"); g(100, "AcDbSymbolTable"); g(70, len(self.layers))
        for i, name in enumerate(self.layers):
            g(0, "LAYER"); g(5, "%X" % (0x11 + i)); g(100, "AcDbSymbolTableRecord"); g(100, "AcDbLayerTableRecord")
            g(2, name); g(70, 0); g(62, 1 + i % 7); g(6, "CONTINUOUS")
        g(0, "ENDTAB")
        g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "ENTITIES")
        for e in self.ents:
            out.extend(e)
        g(0, "ENDSEC")
        g(0, "EOF")
        return "\n".join(out) + "\n"

    def write(self, path):
        with open(path, "w", encoding="ascii", newline="\n") as fh:
            fh.write(self.text())


# ---- copper ----------------------------------------------------------------------------------------------------
def copper_union(board, layer):
    """All copper of one layer (zone fills, tracks, vias, pads) as one polygon set. A THT pad is solid: the drill hole
    is not cut out of it (the drill comes after the isolation cut). Holes in the set are voids of the copper."""
    s = pcbnew.SHAPE_POLY_SET()
    for z in board.Zones():
        if z.GetIsRuleArea() or not z.IsOnLayer(layer) or not z.IsFilled():
            continue
        s.BooleanAdd(z.GetFilledPolysList(layer))
    for t in board.GetTracks():
        if t.IsOnLayer(layer):
            t.TransformShapeToPolygon(s, layer, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.IsOnLayer(layer) and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                q = pcbnew.SHAPE_POLY_SET()
                p.TransformShapeToPolygon(q, layer, 0, MAX_ERR, pcbnew.ERROR_INSIDE)
                s.BooleanAdd(q)
    s.Simplify()
    s.Inflate(HEAL, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.001))
    s.Deflate(HEAL, pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, FromMM(0.001))
    s.Simplify()
    return s


def loops(polyset, frame):
    """All loops of a polygon set (outer loops and holes) as lists of lab-frame points (mm)."""
    out = []
    for i in range(polyset.OutlineCount()):
        for j in range(polyset.HoleCount(i) + 1):
            ch = polyset.COutline(i) if j == 0 else polyset.CHole(i, j - 1)
            out.append([frame.lab(ch.CPoint(k).x, ch.CPoint(k).y) for k in range(ch.PointCount())])
    return out


def write_copper(board, frame, layer, name, path):
    d = Dxf([name])
    for pts in loops(copper_union(board, layer), frame):
        d.polyline(name, pts)
    d.write(path)


def write_edge(board, frame, path):
    e = edge_rect(board)
    x0, y0, x1, y1 = e.GetStart().x, e.GetStart().y, e.GetEnd().x, e.GetEnd().y
    d = Dxf(["Edge.Cuts"])
    d.polyline("Edge.Cuts", [frame.lab(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
    d.write(path)


# ---- holes -----------------------------------------------------------------------------------------------------
def holes(board, frame):
    """[(x, y, diameter mm)] in the lab frame: pad holes (round) and vias."""
    res = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                s = p.GetDrillSize()
                if s.x != s.y:
                    raise RuntimeError("%s.%s: slot holes are not supported" % (fp.GetReference(), p.GetNumber()))
                x, y = frame.lab(p.GetPosition().x, p.GetPosition().y)
                res.append((x, y, ToMM(s.x)))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            x, y = frame.lab(t.GetPosition().x, t.GetPosition().y)
            res.append((x, y, ToMM(t.GetDrillValue())))
    return res


def tool_use(d):
    """Dowel: own tool. Drill: in the drill set (<= largest drill). Bore: larger, cut with the end mill."""
    if abs(d - placement.DOWEL_DIA) < 1e-6:
        return "DOWEL"
    return "DRILL" if d <= drill_max() + 0.005 else "BORE"


def tools(hs):
    """Sorted unique diameters (rounded to 0.001) with their use."""
    ds = sorted({round(d, 3) for _, _, d in hs})
    return [(i + 1, d, tool_use(d)) for i, d in enumerate(ds)]


def all_holes(board, frame):
    hs = holes(board, frame)
    for x, y in placement.DOWELS_LAB:
        hs.append((x, y, placement.DOWEL_DIA))
    return hs


def tool_name(use, d):
    return "%s_%s" % (use, ("%.3f" % d).rstrip("0").rstrip("."))


def write_drl(hs, path):
    ts = tools(hs)
    num = {d: n for n, d, _ in ts}
    lines = ["M48", "; DRILL file for the Fusion 360 lab template, made by tools/fab_export.py",
             "; lab frame: origin = dowel 1 center, x along the stock long side, top view, mm",
             "; FORMAT={-:-/ absolute / metric / decimal}", "FMAT,2", "METRIC"]
    for n, d, use in ts:
        lines.append("; T%d %s: %s %.3f mm (%d holes)" % (n, tool_name(use, d), {"DRILL": "drill", "BORE": "bore with the end mill", "DOWEL": "bore the dowel with the end mill"}[use], d,
                                                      sum(1 for _, _, h in hs if round(h, 3) == d)))
        lines.append("T%dC%.3f" % (n, d))
    lines += ["%", "G90", "G05"]
    for n, d, _ in ts:
        lines.append("T%d" % n)
        for x, y, h in sorted(hs, key=lambda t: (t[0], t[1])):
            if round(h, 3) == d:
                lines.append("X%.*fY%.*f" % (DEC, x, DEC, y))
    lines += ["T0", "M30"]
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def write_map(hs, path):
    ts = tools(hs)
    names = {d: tool_name(use, d) for _, d, use in ts}
    dxf = Dxf([names[d] for _, d, _ in ts])
    for x, y, h in sorted(hs, key=lambda t: (t[2], t[0], t[1])):
        dxf.circle(names[round(h, 3)], x, y, h / 2.0)
    dxf.write(path)


def export(board_path, out_dir):
    board = pcbnew.LoadBoard(board_path)
    frame = Frame(board)
    os.makedirs(out_dir, exist_ok=True)
    out = lambda n: os.path.join(out_dir, n)  # noqa: E731
    write_copper(board, frame, pcbnew.F_Cu, "F.Cu", out(FILES[0]))
    write_copper(board, frame, pcbnew.B_Cu, "B.Cu", out(FILES[1]))
    write_edge(board, frame, out(FILES[2]))
    hs = all_holes(board, frame)
    write_drl(hs, out(FILES[3]))
    write_map(hs, out(FILES[4]))
    return hs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board", nargs="?", default=os.path.join(SCH_DIR, STEM + ".kicad_pcb"))
    ap.add_argument("--out", default=os.path.join(SCH_DIR, "fab"))
    args = ap.parse_args(argv)
    hs = export(args.board, args.out)
    for n, d, use in tools(hs):
        print("fab_export: T%d %-12s %2d holes" % (n, tool_name(use, d), sum(1 for _, _, h in hs if round(h, 3) == d)))
    print("fab_export: wrote %s to %s" % (", ".join(FILES), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
