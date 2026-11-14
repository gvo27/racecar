"""Tests for the lab frame (placement.py) and the fab outputs (fab_export.py). Run: make pcb-test, make pcb-fab.

The outputs are checked against pcbnew (copper area) and against `kicad-cli pcb export drill` (holes).
The DXF reader is a small stdlib one: the files must parse without any DXF library.
"""
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest

import pcbnew
from pcbnew import ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
SCH_DIR = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import fab_export  # noqa: E402
import milling_check as mc  # noqa: E402
import placement  # noqa: E402

BOARD = os.path.join(SCH_DIR, "rc_power_board.kicad_pcb")


# ---- stdlib DXF reader --------------------------------------------------------------------------------------------
def slurp(path):
    with open(path, encoding="ascii") as fh:
        return fh.read()


def read_dxf(path):
    """[(code, value)] pairs of an ASCII DXF; raises ValueError on a broken file."""
    lines = slurp(path).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) % 2:
        raise ValueError("odd number of lines")
    pairs = [(int(lines[i]), lines[i + 1]) for i in range(0, len(lines), 2)]
    if pairs[-1] != (0, "EOF"):
        raise ValueError("no EOF")
    return pairs


def entities(path):
    """[dict(type, layer, closed, pts | center, r)] of the ENTITIES section."""
    pairs = read_dxf(path)
    i = pairs.index((2, "ENTITIES")) + 1
    out, cur = [], None
    for code, val in pairs[i:]:
        if code == 0:
            if cur:
                out.append(cur)
            cur = None if val == "ENDSEC" else {"type": val, "pts": [], "layer": None}
            if val == "ENDSEC":
                break
        elif cur is not None:
            if code == 8:
                cur["layer"] = val
            elif code == 70:
                cur["closed"] = bool(int(val) & 1)
            elif code == 10:
                cur["pts"].append([float(val), None])
            elif code == 20:
                cur["pts"][-1][1] = float(val)
            elif code == 40:
                cur["r"] = float(val)
            elif code == 90:
                cur["n"] = int(val)
    return out


def layer_table(path):
    pairs = read_dxf(path)
    names, in_layer = [], False
    for k, (code, val) in enumerate(pairs):
        if code == 0 and val == "LAYER":
            in_layer = True
        elif in_layer and code == 2:
            names.append(val)
            in_layer = False
        elif code == 0:
            in_layer = False
    return names


def area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def covered(pt, loops):
    """True if the point is in copper: inside an odd number of loops (outer loops and holes nest)."""
    n = 0
    for pts, bb in loops:
        if bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3] and inside(pt, pts):
            n += 1
    return n % 2 == 1


def with_bbox(loops):
    return [(p, bbox(p)) for p in loops]


# ---- the lab frame ----------------------------------------------------------------------------------------------
class TestFrame(unittest.TestCase):
    def test_dowels_in_lab_frame(self):
        self.assertEqual(placement.DOWELS_LAB, [(0.0, 0.0), (145.8468, 0.0)])

    def test_matches_milling_toml(self):
        lim = mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))
        self.assertEqual(placement.STOCK, (lim.stock_w, lim.stock_h))
        self.assertEqual([tuple(d) for d in placement.DOWELS], lim.dowels)
        self.assertAlmostEqual(placement.DOWEL_DIA, lim.dowel_dia)

    def test_board_centered_in_stock(self):
        xs, ys = zip(*(placement.board_to_stock(x, y) for x in (0, placement.OUTLINE_W) for y in (0, placement.OUTLINE_H)))
        self.assertAlmostEqual(min(xs), 6.2, places=6)
        self.assertAlmostEqual(placement.STOCK[0] - max(xs), 6.2, places=6)
        self.assertAlmostEqual(min(ys), 17.8, places=6)
        self.assertAlmostEqual(placement.STOCK[1] - max(ys), 17.8, places=6)

    def test_turn_is_90_degrees_counter_clockwise(self):
        o = placement.board_to_stock(10, 10)
        px = placement.board_to_stock(11, 10)
        py = placement.board_to_stock(10, 11)
        self.assertAlmostEqual(px[0] - o[0], 0.0)
        self.assertAlmostEqual(px[1] - o[1], 1.0)   # board +x -> stock +y
        self.assertAlmostEqual(py[0] - o[0], -1.0)  # board +y -> stock -x
        self.assertAlmostEqual(py[1] - o[1], 0.0)

    def test_inverse(self):
        for p in ((0, 0), (12.5, 77.0), (66, 140)):
            self.assertAlmostEqual(placement.stock_to_board(*placement.board_to_stock(*p))[0], p[0], places=9)
            self.assertAlmostEqual(placement.stock_to_board(*placement.board_to_stock(*p))[1], p[1], places=9)

    def test_dowels_clear_of_the_board(self):
        w, h = placement.OUTLINE_W, placement.OUTLINE_H
        for sx, sy in placement.DOWELS:
            bx, by = placement.stock_to_board(sx, sy)
            dx = max(0 - bx, 0, bx - w)
            dy = max(0 - by, 0, by - h)
            dist = math.hypot(dx, dy)
            self.assertGreaterEqual(dist - placement.DOWEL_DIA / 2.0, 3.0, "dowel hole edge to the board outline")
            self.assertTrue(0 < sx < placement.STOCK[0] and 0 < sy < placement.STOCK[1])


# ---- the outputs ------------------------------------------------------------------------------------------------
class TestOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="fab-")
        cls.holes = fab_export.export(BOARD, cls.d)
        cls.board = pcbnew.LoadBoard(BOARD)
        cls.frame = fab_export.Frame(cls.board)

    def p(self, name):
        return os.path.join(self.d, name)

    def test_exact_file_set(self):
        self.assertEqual(sorted(os.listdir(self.d)), sorted(fab_export.FILES))
        self.assertEqual(len(fab_export.FILES), 5)

    def test_dxf_files_parse_one_layer_each(self):
        want = {"rc_power_board-F_Cu.dxf": "F.Cu", "rc_power_board-B_Cu.dxf": "B.Cu", "rc_power_board-Edge_Cuts.dxf": "Edge.Cuts"}
        for name, layer in want.items():
            with self.subTest(name):
                self.assertEqual(layer_table(self.p(name)), [layer])
                es = entities(self.p(name))
                self.assertTrue(es)
                self.assertEqual({e["layer"] for e in es}, {layer})
                self.assertEqual({e["type"] for e in es}, {"LWPOLYLINE"})  # no circles, text or lines

    def test_loops_closed_and_counted(self):
        for name in ("rc_power_board-F_Cu.dxf", "rc_power_board-B_Cu.dxf", "rc_power_board-Edge_Cuts.dxf"):
            for e in entities(self.p(name)):
                self.assertTrue(e["closed"], name)
                self.assertEqual(e["n"], len(e["pts"]), name)
                self.assertGreaterEqual(e["n"], 3, name)

    def test_edge_loop_is_140_by_66_at_the_expected_offset(self):
        es = entities(self.p("rc_power_board-Edge_Cuts.dxf"))
        self.assertEqual(len(es), 1)
        x0, y0, x1, y1 = bbox(es[0]["pts"])
        self.assertAlmostEqual(x1 - x0, 140.0, places=3)
        self.assertAlmostEqual(y1 - y0, 66.0, places=3)
        self.assertAlmostEqual(x0, 6.2 - placement.DOWELS[0][0], places=3)
        self.assertAlmostEqual(y0, 17.8 - placement.DOWELS[0][1], places=3)

    def copper_loops(self, name):
        return with_bbox([e["pts"] for e in entities(self.p(name))])

    def test_copper_inside_edge(self):
        edge = entities(self.p("rc_power_board-Edge_Cuts.dxf"))[0]["pts"]
        for name in ("rc_power_board-F_Cu.dxf", "rc_power_board-B_Cu.dxf"):
            for pts, _ in self.copper_loops(name):
                for pt in pts:
                    self.assertTrue(inside(pt, edge) or min(abs(pt[0] - e[0]) + abs(pt[1] - e[1]) for e in edge) < 1e-3, "%s %s" % (name, pt))

    def union_area_mm2(self, layer):
        """Independent copper area from pcbnew: every item added to one set with the outer error direction."""
        s = pcbnew.SHAPE_POLY_SET()
        b = self.board
        for z in b.Zones():
            if z.IsOnLayer(layer) and z.IsFilled() and not z.GetIsRuleArea():
                s.BooleanAdd(z.GetFilledPolysList(layer))
        for t in b.GetTracks():
            if t.IsOnLayer(layer):
                t.TransformShapeToPolygon(s, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_OUTSIDE)
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                if pad.IsOnLayer(layer) and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    q = pcbnew.SHAPE_POLY_SET()
                    pad.TransformShapeToPolygon(q, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_OUTSIDE)
                    s.BooleanAdd(q)
        s.Simplify()
        return abs(s.Area()) / 1e12

    def test_no_copper_graphics_outside_zones_tracks_pads(self):
        for fp in self.board.GetFootprints():
            for g in fp.GraphicalItems():
                self.assertNotIn(g.GetLayer(), (pcbnew.F_Cu, pcbnew.B_Cu), fp.GetReference())
        for d in self.board.GetDrawings():
            self.assertNotIn(d.GetLayer(), (pcbnew.F_Cu, pcbnew.B_Cu))

    def test_loops_do_not_overlap_and_area_matches_pcbnew(self):
        for name, layer in (("rc_power_board-F_Cu.dxf", pcbnew.F_Cu), ("rc_power_board-B_Cu.dxf", pcbnew.B_Cu)):
            with self.subTest(name):
                loops = self.copper_loops(name)
                # nesting depth of each loop = number of other loops that contain its first vertex
                total = 0.0
                for i, (pts, _) in enumerate(loops):
                    depth = sum(1 for j, (q, bb) in enumerate(loops) if j != i and bb[0] <= pts[0][0] <= bb[2] and bb[1] <= pts[0][1] <= bb[3] and inside(pts[0], q))
                    total += abs(area(pts)) * (1 if depth % 2 == 0 else -1)
                ref = self.union_area_mm2(layer)
                self.assertAlmostEqual(total / ref, 1.0, delta=0.005, msg="%s: loops %.2f mm2, pcbnew %.2f mm2" % (name, total, ref))
                # loops that overlap would make the signed sum differ from the union: also compare with the union of the loops
                s = pcbnew.SHAPE_POLY_SET()
                for pts, _ in loops:
                    one = pcbnew.SHAPE_POLY_SET()
                    one.NewOutline()
                    for x, y in pts:
                        one.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
                    s = self.xor(s, one)
                self.assertAlmostEqual(abs(s.Area()) / 1e12 / ref, 1.0, delta=0.005)

    @staticmethod
    def xor(a, b):
        """Symmetric difference: nested loops (holes) subtract, disjoint loops add, overlap would show as a difference."""
        r = pcbnew.SHAPE_POLY_SET(a)
        r.BooleanSubtract(b)
        c = pcbnew.SHAPE_POLY_SET(b)
        c.BooleanSubtract(a)
        r.BooleanAdd(c)
        return r

    def test_b_cu_not_mirrored_and_pads_centered(self):
        bcu = self.copper_loops("rc_power_board-B_Cu.dxf")
        fcu = self.copper_loops("rc_power_board-F_Cu.dxf")
        n_b = 0
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                x, y = self.frame.lab(pad.GetPosition().x, pad.GetPosition().y)
                if pad.IsOnLayer(pcbnew.B_Cu) and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    n_b += 1
                    self.assertTrue(covered((x, y), bcu), "B.Cu pad %s.%s at %.2f, %.2f" % (fp.GetReference(), pad.GetNumber(), x, y))
                if pad.IsOnLayer(pcbnew.F_Cu) and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                    self.assertTrue(covered((x, y), fcu))
        self.assertGreater(n_b, 100)

    def test_holes_centered_on_b_cu_pads(self):
        bcu = self.copper_loops("rc_power_board-B_Cu.dxf")
        pads = [e for e in entities(self.p("rc_power_board-drl_map.dxf")) if not e["layer"].startswith(("BORE", "DOWEL"))]
        self.assertGreater(len(pads), 50)
        for e in pads:
            self.assertTrue(covered(tuple(e["pts"][0]), bcu), "hole at %s" % (e["pts"][0],))

    # drill: Excellon and the map
    def read_drl(self):
        tools, holes, cur = {}, [], None
        for line in slurp(self.p("rc_power_board.drl")).split("\n"):
            m = re.match(r"T(\d+)C([0-9.]+)$", line)
            if m:
                tools[int(m.group(1))] = float(m.group(2))
                continue
            m = re.match(r"T(\d+)$", line)
            if m:
                cur = int(m.group(1)) or None
                continue
            m = re.match(r"X(-?[0-9.]+)Y(-?[0-9.]+)$", line)
            if m and cur:
                holes.append((tools[cur], round(float(m.group(1)), 3), round(float(m.group(2)), 3)))
        return tools, holes

    def test_excellon_header(self):
        text = slurp(self.p("rc_power_board.drl"))
        self.assertTrue(text.startswith("M48\n"))
        self.assertIn("\nMETRIC\n", text)
        self.assertTrue(text.rstrip().endswith("M30"))
        tools, _ = self.read_drl()
        self.assertEqual(len(set(tools.values())), len(tools), "one tool per diameter")
        self.assertIn(4.191, tools.values())
        self.assertIn("; T", text)

    def test_dowels_in_excellon(self):
        _, holes = self.read_drl()
        self.assertIn((4.191, 0.0, 0.0), holes)
        xs = sorted(x for d, x, y in holes if d == 4.191)
        self.assertEqual(len(xs), 2)
        self.assertAlmostEqual(xs[0], 0.0, places=3)
        self.assertAlmostEqual(xs[1], 145.8468, places=3)

    def test_holes_match_kicad_cli_drill(self):
        out = tempfile.mkdtemp(prefix="kcdrill-")
        subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--drill-origin", "plot",
                        "--excellon-units", "mm", "--excellon-zeros-format", "decimal", "-o", out + "/", BOARD],
                       check=True, stdout=subprocess.DEVNULL)
        ref = []
        for f in sorted(os.listdir(out)):
            if not f.endswith(".drl"):
                continue
            tools, cur = {}, None
            for line in slurp(os.path.join(out, f)).split("\n"):
                line = line.strip()
                m = re.match(r"T(\d+)C([0-9.]+)", line)
                if m:
                    tools[int(m.group(1))] = float(m.group(2))
                    continue
                m = re.match(r"T(\d+)$", line)
                if m:
                    cur = int(m.group(1))
                    continue
                m = re.match(r"X(-?[0-9.]+)Y(-?[0-9.]+)", line)
                if m and cur in tools:
                    ref.append((tools[cur], float(m.group(1)), float(m.group(2))))
        self.assertGreater(len(ref), 50)
        # KiCad's origin is the aux origin = the outline's lower-left corner; its y axis may point down.
        ys = [y for _, _, y in ref]
        sign = -1.0 if max(ys) <= 1e-6 else 1.0
        want = sorted((round(d, 3), round(a, 3), round(b, 3)) for d, a, b in
                      ((d, *placement.board_to_lab(x, sign * y)) for d, x, y in ref))
        _, mine = self.read_drl()
        mine = sorted((round(d, 3), round(x, 3), round(y, 3)) for d, x, y in mine if d != 4.191)
        self.assertEqual(len(mine), len(want))
        self.assertEqual([m[0] for m in mine].count(1.0), [w[0] for w in want].count(1.0))
        for a, b in zip(mine, want):
            self.assertEqual(a[0], b[0])
            self.assertAlmostEqual(a[1], b[1], delta=0.002)
            self.assertAlmostEqual(a[2], b[2], delta=0.002)

    def test_drill_map(self):
        es = entities(self.p("rc_power_board-drl_map.dxf"))
        self.assertEqual({e["type"] for e in es}, {"CIRCLE"})
        _, holes = self.read_drl()
        self.assertEqual(len(es), len(holes))
        self.assertEqual(sorted(layer_table(self.p("rc_power_board-drl_map.dxf"))), sorted({e["layer"] for e in es}))
        for e in es:
            use, d = e["layer"].split("_")
            self.assertAlmostEqual(2 * e["r"], float(d), places=3)
            self.assertEqual(use, "DOWEL" if abs(float(d) - 4.191) < 1e-6 else ("DRILL" if float(d) <= 2.0 + 1e-6 else "BORE"))
        self.assertIn("DOWEL_4.191", {e["layer"] for e in es})
        self.assertIn("BORE_3.4", {e["layer"] for e in es})

    def test_every_board_hole_is_makeable(self):
        lim = mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))
        for _, d, use in fab_export.tools(self.holes):
            if use == "DRILL":
                self.assertTrue(any(abs(d - s) < 0.005 for s in lim.drills), d)
            elif use == "BORE":
                self.assertGreaterEqual(d, lim.milled_hole_min - 0.005)


class TestCommitted(unittest.TestCase):
    def test_committed_fab_files_are_current(self):
        d = tempfile.mkdtemp(prefix="fabc-")
        fab_export.export(BOARD, d)
        for name in fab_export.FILES:
            with self.subTest(name):
                with open(os.path.join(SCH_DIR, "fab", name), "rb") as a, open(os.path.join(d, name), "rb") as b:
                    self.assertEqual(a.read(), b.read(), "run make pcb-fab and commit docs/schematics/fab/")


if __name__ == "__main__":
    unittest.main()
