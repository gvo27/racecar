"""Tests for the project footprint rc_power:Pololu_D36V50Fx (Pololu D36V50F5 / D36V50Fx, 25.4 x 25.4 mm module).

Local frame: origin = pad 1 (inner row, top), x to the right, y down, seen from the top. The pin edge is on the
right, the body lies on the inner-row side (-x). Pad numbers follow the symbol rc_power:D36V50F5 (odd = inner row,
even = outer row): 1 PG, 2 EN, 3-4 VRP, 5-6 VIN, 7-10 GND, 11-12 VOUT. Source: docs/datasheets/pololu_d36v50fx_dimensions.pdf.
"""
import math
import os
import unittest

import pcbnew
from pcbnew import ToMM

PRETTY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rc_power.pretty")
BODY = 25.4
PITCH = 2.54


def mm(v):
    return ToMM(v)


class TestPololuD36V50Fx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fp = pcbnew.FootprintLoad(PRETTY, "Pololu_D36V50Fx")
        cls.pads = {p.GetNumber(): p for p in cls.fp.Pads()} if cls.fp else {}

    def pos(self, n):
        p = self.pads[str(n)].GetPosition()
        return mm(p.x), mm(p.y)

    def test_loads(self):
        self.assertIsNotNone(self.fp)

    def test_twelve_numbered_pads(self):
        self.assertEqual(sorted(self.pads, key=int), [str(i) for i in range(1, 13)])
        self.assertEqual(len(self.fp.Pads()), 12)

    def test_pad_positions_on_the_0_1_inch_grid(self):
        for n in range(1, 13):
            x, y = self.pos(n)
            self.assertAlmostEqual(x, 0.0 if n % 2 else PITCH, places=3, msg="pad %d x" % n)
            self.assertAlmostEqual(y, ((n - 1) // 2) * PITCH, places=3, msg="pad %d y" % n)

    def test_pads_are_through_holes_in_the_drill_set(self):
        for p in self.fp.Pads():
            self.assertEqual(p.GetAttribute(), pcbnew.PAD_ATTRIB_PTH)
            self.assertAlmostEqual(mm(p.GetDrillSize().x), 1.0, places=3)
            self.assertAlmostEqual(mm(p.GetDrillSize().y), 1.0, places=3)

    def test_pad_clearance(self):
        pads = list(self.fp.Pads())
        for i, a in enumerate(pads):
            for b in pads[i + 1:]:
                d = math.dist(self.pos(a.GetNumber()), self.pos(b.GetNumber()))
                gap = d - mm(a.GetSize().x) / 2 - mm(b.GetSize().x) / 2
                self.assertGreaterEqual(gap, 0.4 - 1e-6, "%s-%s" % (a.GetNumber(), b.GetNumber()))

    def _shapes(self):
        return [s for s in self.fp.GraphicalItems() if hasattr(s, "GetShape")]

    def _rect(self, layer):
        for s in self._shapes():
            if s.GetLayer() == layer and s.GetShape() == pcbnew.SHAPE_T_RECT:
                return (mm(s.GetStart().x), mm(s.GetStart().y), mm(s.GetEnd().x), mm(s.GetEnd().y))
        self.fail("no rectangle on layer %s" % layer)

    def test_fab_body_is_25_4_square_on_the_inner_row_side(self):
        x0, y0, x1, y1 = self._rect(pcbnew.F_Fab)
        self.assertAlmostEqual(x1 - x0, BODY, places=2)
        self.assertAlmostEqual(y1 - y0, BODY, places=2)
        # pin edge: outer row is 1.27 mm from it; inner row is 3.81 mm from it; body extends to the inner-row side
        self.assertAlmostEqual(x1, PITCH + 1.27, places=2)
        self.assertAlmostEqual(x0, PITCH + 1.27 - BODY, places=2)
        # 6 pin pairs centred on the edge: end pins 6.35 mm from the side edges
        self.assertAlmostEqual(self.pos(1)[1] - y0, 6.35, places=2)
        self.assertAlmostEqual(y1 - self.pos(11)[1], 6.35, places=2)

    def test_courtyard_covers_the_body(self):
        self.fp.BuildCourtyardCaches()
        bb = self.fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        x0, y0, x1, y1 = self._rect(pcbnew.F_Fab)
        self.assertLessEqual(mm(bb.GetLeft()), x0 - 0.24)
        self.assertLessEqual(mm(bb.GetTop()), y0 - 0.24)
        self.assertGreaterEqual(mm(bb.GetRight()), x1 + 0.24)
        self.assertGreaterEqual(mm(bb.GetBottom()), y1 + 0.24)
        self.assertAlmostEqual(mm(bb.GetWidth()), BODY + 0.5, delta=0.15)
        self.assertAlmostEqual(mm(bb.GetHeight()), BODY + 0.5, delta=0.15)

    def test_three_mounting_holes_are_fab_circles_only(self):
        x0, y0, x1, y1 = self._rect(pcbnew.F_Fab)
        circles = [s for s in self._shapes() if s.GetLayer() == pcbnew.F_Fab and s.GetShape() == pcbnew.SHAPE_T_CIRCLE]
        self.assertEqual(len(circles), 3)
        want = {(round(x1 - 2.2, 2), round(y1 - 2.2, 2)), (round(x1 - 2.2, 2), round(y0 + 2.2, 2)), (round(x0 + 2.2, 2), round(y0 + 2.2, 2))}
        got = {(round(mm(c.GetCenter().x), 2), round(mm(c.GetCenter().y), 2)) for c in circles}
        self.assertEqual(got, want)
        for c in circles:
            self.assertAlmostEqual(mm(c.GetRadius()) * 2, 2.18, places=2)

    def test_silk_does_not_cross_pads(self):
        for s in self._shapes():
            if s.GetLayer() != pcbnew.F_SilkS:
                continue
            bb = s.GetBoundingBox()
            for p in self.fp.Pads():
                pb = p.GetBoundingBox()
                self.assertFalse(bb.Intersects(pb) and s.GetShape() != pcbnew.SHAPE_T_RECT, "silk item touches pad %s" % p.GetNumber())
        # the body outline is a rectangle: its edge must be outside every pad
        x0, y0, x1, y1 = self._rect(pcbnew.F_SilkS)
        for p in self.fp.Pads():
            px, py = self.pos(p.GetNumber())
            r = mm(p.GetSize().x) / 2
            self.assertGreater(x1 - px, r + 0.12 / 2 + 0.2)


if __name__ == "__main__":
    unittest.main()
