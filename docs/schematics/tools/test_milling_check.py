"""Tests for milling_check.py. Run: make pcb-test (stdlib unittest, KiCad image python3)."""
import os
import sys
import tempfile
import unittest

import pcbnew
from pcbnew import FromMM, VECTOR2I

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import milling_check as mc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LIMITS = os.path.join(HERE, "..", "milling.toml")


def limits():
    return mc.load_limits(LIMITS)


def rules(findings, sev=None):
    return sorted(f[0] for f in findings if f[0] != "MILL-DEPTH" and (sev is None or f[1] == sev))


class Synth:
    """Small synthetic board builder."""

    def __init__(self):
        self.b = pcbnew.BOARD()
        self.nets = {}

    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(n)
            self.nets[name] = n
        return self.nets[name]

    def track(self, x1, y1, x2, y2, net, w=0.5, layer=pcbnew.B_Cu):
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(VECTOR2I(FromMM(x1), FromMM(y1)))
        t.SetEnd(VECTOR2I(FromMM(x2), FromMM(y2)))
        t.SetWidth(FromMM(w))
        t.SetLayer(layer)
        t.SetNet(self.net(net))
        self.b.Add(t)
        return t

    def via(self, x, y, net, drill=1.2, dia=2.1):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        v.SetDrill(FromMM(drill))
        v.SetWidth(FromMM(dia))
        v.SetNet(self.net(net))
        self.b.Add(v)
        return v

    def fp(self, ref, x, y, side=pcbnew.F_Cu, court=None):
        f = pcbnew.FOOTPRINT(self.b)
        f.SetReference(ref)
        f.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        if court:
            r = pcbnew.PCB_SHAPE(f)
            r.SetShape(pcbnew.SHAPE_T_RECT)
            r.SetStart(VECTOR2I(FromMM(x - court), FromMM(y - court)))
            r.SetEnd(VECTOR2I(FromMM(x + court), FromMM(y + court)))
            r.SetLayer(pcbnew.F_CrtYd)  # Flip() moves it to B_CrtYd
            r.SetWidth(FromMM(0.05))
            f.Add(r)
        self.b.Add(f)
        if side == pcbnew.B_Cu:
            f.Flip(f.GetPosition(), False)
        return f

    def pad(self, fp, x, y, drill, size, net, attr=pcbnew.PAD_ATTRIB_PTH):
        p = pcbnew.PAD(fp)
        p.SetAttribute(attr)
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        p.SetSize(VECTOR2I(FromMM(size), FromMM(size)))
        p.SetDrillSize(VECTOR2I(FromMM(drill), FromMM(drill)))
        p.SetLayerSet(p.PTHMask())
        p.SetPosition(VECTOR2I(FromMM(x), FromMM(y)))
        p.SetNet(self.net(net))
        fp.Add(p)
        return p


class TestCutWidth(unittest.TestCase):
    def test_values(self):
        self.assertAlmostEqual(mc.cut_width(0.2, 30, 0.20), 0.307, places=3)
        self.assertAlmostEqual(mc.cut_width(0.1, 60, 0.20), 0.331, places=3)


class TestLimits(unittest.TestCase):
    def test_loads_and_derives(self):
        lim = limits()
        self.assertAlmostEqual(lim.depth_worst, 0.20)
        self.assertEqual([b.name for b in lim.bits], ["30deg/0.2", "60deg/0.1"])
        self.assertEqual(lim.drills, [0.8, 1.0, 1.2, 1.5])

    def test_rejects_value_without_status(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "bad.toml")
            with open(LIMITS, encoding="utf-8") as src:
                text = src.read()
            self.assertIn('status = "confirmed"\nsource = "Kepro', text)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(text.replace('status = "confirmed"\nsource = "Kepro', 'source = "Kepro'))
            with self.assertRaises(ValueError):
                mc.load_limits(p)


class TestGap(unittest.TestCase):
    def gap(self, g):
        s = Synth()
        s.track(0, 0, 10, 0, "A")
        s.track(0, 0.5 + g, 10, 0.5 + g, "B")
        return mc.check(s.b, limits())

    def test_030_error(self):
        f = self.gap(0.30)
        self.assertEqual(rules(f, "error"), ["MILL-GAP"])

    def test_032_bit_warning(self):
        f = self.gap(0.32)
        self.assertEqual(rules(f), ["MILL-GAP-BIT"])
        self.assertIn("30deg/0.2", f[[x[0] for x in f].index("MILL-GAP-BIT")][5])
        self.assertNotIn("60deg/0.1", f[[x[0] for x in f].index("MILL-GAP-BIT")][5])

    def test_045_none(self):
        self.assertEqual(rules(self.gap(0.45)), [])

    def test_same_net_ignored(self):
        s = Synth()
        s.track(0, 0, 10, 0, "A")
        s.track(0, 0.8, 10, 0.8, "A")
        self.assertEqual(rules(mc.check(s.b, limits())), [])


class TestDepth(unittest.TestCase):
    def test_depth_error_with_assumed_limits(self):
        f = [x for x in mc.check(pcbnew.BOARD(), limits()) if x[0] == "MILL-DEPTH"]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0][1], "error")
        self.assertAlmostEqual(f[0][3], 0.05)


class TestHoles(unittest.TestCase):
    def hole(self, d, size=3.5, attr=pcbnew.PAD_ATTRIB_PTH):
        s = Synth()
        fp = s.fp("J1", 20, 20)
        s.pad(fp, 20, 20, d, size, "A", attr)
        return mc.check(s.b, limits())

    def test_11_error(self):
        self.assertEqual(rules(self.hole(1.1), "error"), ["MILL-DRILL"])

    def test_24_milled(self):
        self.assertEqual(rules(self.hole(2.4)), [])

    def test_in_set(self):
        self.assertEqual(rules(self.hole(1.0, 2.0)), [])

    def test_annular(self):
        self.assertEqual(rules(self.hole(1.0, 1.5), "error"), ["MILL-ANNULAR"])


class TestFcuTht(unittest.TestCase):
    def test_fcu_track_on_tht_pad(self):
        s = Synth()
        fp = s.fp("J3", 20, 20)
        s.pad(fp, 20, 20, 1.0, 2.0, "A")
        s.track(20, 20, 30, 20, "A", layer=pcbnew.F_Cu)
        self.assertIn("MILL-FCU-THT", rules(mc.check(s.b, limits())))

    def test_bcu_track_on_tht_pad_ok(self):
        s = Synth()
        fp = s.fp("J3", 20, 20)
        s.pad(fp, 20, 20, 1.0, 2.0, "A")
        s.track(20, 20, 30, 20, "A", layer=pcbnew.B_Cu)
        self.assertNotIn("MILL-FCU-THT", rules(mc.check(s.b, limits())))


class TestVia(unittest.TestCase):
    def test_bad_via(self):
        s = Synth()
        s.via(20, 20, "A", drill=1.1, dia=2.0)
        self.assertIn("MILL-VIA", rules(mc.check(s.b, limits()), "error"))

    def test_good_via(self):
        s = Synth()
        s.via(20, 20, "A")
        self.assertEqual(rules(mc.check(s.b, limits())), [])

    def test_via_in_f_courtyard(self):
        s = Synth()
        s.fp("C1", 20, 20, pcbnew.F_Cu, court=5)
        s.via(20, 20, "A")
        self.assertIn("MILL-RIVET-ACCESS", rules(mc.check(s.b, limits()), "error"))

    def test_via_in_b_courtyard(self):
        s = Synth()
        s.fp("R1", 20, 20, pcbnew.B_Cu, court=5)
        s.via(21, 19, "A")
        self.assertIn("MILL-RIVET-ACCESS", rules(mc.check(s.b, limits()), "error"))

    def test_via_outside_courtyard(self):
        s = Synth()
        s.fp("C1", 20, 20, pcbnew.F_Cu, court=3)
        s.via(30, 30, "A")
        self.assertNotIn("MILL-RIVET-ACCESS", rules(mc.check(s.b, limits())))


def edge_board(s, w=60, h=60):
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        sh = pcbnew.PCB_SHAPE(s.b)
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetStart(VECTOR2I(FromMM(a[0]), FromMM(a[1])))
        sh.SetEnd(VECTOR2I(FromMM(b[0]), FromMM(b[1])))
        sh.SetLayer(pcbnew.Edge_Cuts)
        sh.SetWidth(FromMM(0.05))
        s.b.Add(sh)


class TestEdge(unittest.TestCase):
    def test_edge_clearance(self):
        s = Synth()
        edge_board(s)
        s.track(10, 0.6, 20, 0.6, "A")  # copper edge at 0.35 mm from the outline
        self.assertEqual(rules(mc.check(s.b, limits()), "error"), ["MILL-EDGE"])

    def test_edge_ok(self):
        s = Synth()
        edge_board(s)
        s.track(10, 3, 20, 3, "A")
        self.assertEqual(rules(mc.check(s.b, limits())), [])

    def test_connector_edge(self):
        s = Synth()
        edge_board(s)
        s.fp("J2", 30, 30, pcbnew.F_Cu, court=3)  # courtyard 27 mm from the edge
        self.assertEqual(rules(mc.check(s.b, limits()), "warning"), ["MILL-CONN-EDGE"])

    def test_connector_at_edge_ok(self):
        s = Synth()
        edge_board(s)
        s.fp("J2", 30, 3.5, pcbnew.F_Cu, court=3)  # courtyard 0.5 mm from the edge
        self.assertNotIn("MILL-CONN-EDGE", rules(mc.check(s.b, limits())))


def add_zone(s, net, x1, y1, x2, y2, layer=pcbnew.B_Cu):
    """Zone with a hand-set fill (no filler run)."""
    z = pcbnew.ZONE(s.b)
    z.SetLayer(layer)
    z.SetNet(s.net(net))
    ol = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        ol.Append(FromMM(x), FromMM(y))
    ol.SetClosed(True)
    z.Outline().AddOutline(ol)
    fill = pcbnew.SHAPE_POLY_SET()
    fill.AddOutline(ol)
    z.SetFilledPolysList(layer, fill)
    z.SetIsFilled(True)
    s.b.Add(z)
    return z


class TestIsland(unittest.TestCase):
    def test_overlapping_same_net_zones_one_pad(self):
        s = Synth()
        add_zone(s, "A", 0, 0, 10, 10)
        add_zone(s, "A", 8, 0, 20, 10)  # overlaps the first, touches no pad itself
        f = s.fp("J1", 2, 5)
        s.pad(f, 2, 5, 1.0, 2.0, "A")
        self.assertNotIn("MILL-ISLAND", rules(mc.check(s.b, limits())))

    def test_isolated_same_net_piece(self):
        s = Synth()
        add_zone(s, "A", 0, 0, 10, 10)
        add_zone(s, "A", 30, 0, 40, 10)  # apart, no item of net A
        f = s.fp("J1", 2, 5)
        s.pad(f, 2, 5, 1.0, 2.0, "A")
        self.assertEqual([r for r in rules(mc.check(s.b, limits())) if r == "MILL-ISLAND"], ["MILL-ISLAND"])


class TestSliver(unittest.TestCase):
    def slit_board(self, slit):
        s = Synth()
        z = add_zone(s, "A", 0, 0, 20, 10)
        if slit:
            ol = pcbnew.SHAPE_LINE_CHAIN()
            for x, y in ((0, 0), (20, 0), (20, 10), (0, 10), (0, 9.62), (18, 9.62), (0, 9.62)):
                ol.Append(FromMM(x), FromMM(y))
            ol.SetClosed(True)
            fill = pcbnew.SHAPE_POLY_SET()
            fill.AddOutline(ol)
            z.SetFilledPolysList(pcbnew.B_Cu, fill)
        f = s.fp("J1", 10, 5)
        s.pad(f, 10, 5, 1.0, 2.0, "A")
        return s

    def test_zero_width_slit_is_no_sliver(self):
        # the copper above the slit is 0.38 mm high but joins the rest: the slit is no gap
        self.assertNotIn("MILL-SLIVER", rules(mc.check(self.slit_board(True).b, limits())))

    def test_real_strip_is_sliver(self):
        s = Synth()
        add_zone(s, "A", 0, 0, 20, 0.4)  # 0.4 mm strip
        f = s.fp("J1", 10, 0.2)
        s.pad(f, 10, 0.2, 0.3, 0.4, "A", attr=pcbnew.PAD_ATTRIB_SMD)
        self.assertIn("MILL-SLIVER", rules(mc.check(s.b, limits())))


class TestWaivers(unittest.TestCase):
    def write(self, text):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "w.toml")
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def test_empty_file(self):
        self.assertEqual(mc.load_waivers(self.write("waiver = []\n")), [])

    def test_waiver_moves_finding(self):
        s = Synth()
        s.track(0, 0, 10, 0, "A")
        s.track(0, 0.8, 10, 0.8, "B")
        f = mc.check(s.b, limits())
        w = mc.load_waivers(self.write(
            '[[waiver]]\nrule="MILL-GAP"\nlocation="net A"\nreason="Test."\nwho="t"\ndate="2026-11-11"\n'))
        g = mc.triage(f, w)
        self.assertEqual([x[0] for x in g["errors"] if x[0] != "MILL-DEPTH"], [])
        self.assertEqual([x[0][0] for x in g["waived"]], ["MILL-GAP"])
        self.assertEqual(g["waived"][0][1]["reason"], "Test.")
        self.assertEqual([x[0] for x in g["questions"]], ["MILL-DEPTH"])

    def test_unwaived_stays_error(self):
        s = Synth()
        s.track(0, 0, 10, 0, "A")
        s.track(0, 0.8, 10, 0.8, "B")
        g = mc.triage(mc.check(s.b, limits()), [])
        self.assertIn("MILL-GAP", [x[0] for x in g["errors"]])

    def test_forbidden_waivers(self):
        for rule in ("MILL-FCU-THT", "MILL-RIVET-ACCESS"):
            p = self.write('[[waiver]]\nrule="%s"\nlocation="x"\nreason="r."\nwho="t"\ndate="d"\n' % rule)
            with self.assertRaises(ValueError):
                mc.load_waivers(p)

    def test_missing_field(self):
        with self.assertRaises(ValueError):
            mc.load_waivers(self.write('[[waiver]]\nrule="MILL-GAP"\nlocation="x"\n'))


if __name__ == "__main__":
    unittest.main()
