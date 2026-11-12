"""Tests for the project footprint rc_power:Pololu_D24VxF5 (Pololu D24V90F5 / D24V60F5 pinout, top view)."""
import collections
import math
import os
import unittest

import pcbnew
from pcbnew import ToMM

PRETTY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rc_power.pretty")


class TestPololuD24VxF5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fp = pcbnew.FootprintLoad(PRETTY, "Pololu_D24VxF5")

    def test_loads(self):
        self.assertIsNotNone(self.fp)

    def test_pad_counts(self):
        pads = self.fp.Pads()
        self.assertEqual(len(pads), 12)
        counts = collections.Counter(p.GetNumber() for p in pads)
        self.assertEqual(dict(counts), {"1": 2, "2": 4, "3": 3, "4": 1, "": 2})

    def test_drills(self):
        for p in self.fp.Pads():
            self.assertAlmostEqual(ToMM(p.GetDrillSize().x), 1.0, places=3)
            self.assertAlmostEqual(ToMM(p.GetDrillSize().y), 1.0, places=3)

    def test_vin_at_input_end(self):
        for p in self.fp.Pads():
            if p.GetNumber() == "1":
                self.assertLess(ToMM(p.GetPosition().x), 0)

    def test_enable_same_edge_as_first_gnd_pair(self):
        en = [p for p in self.fp.Pads() if p.GetNumber() == "4"][0]
        self.assertLess(ToMM(en.GetPosition().x), 0)
        self.assertLess(ToMM(en.GetPosition().y), 0)
        gnd_in = [p for p in self.fp.Pads() if p.GetNumber() == "2" and ToMM(p.GetPosition().x) < 0]
        self.assertEqual(len(gnd_in), 2)
        for p in gnd_in:
            self.assertLess(ToMM(p.GetPosition().y), 0)  # GND pair is on the signal-row edge
        vin_y = [ToMM(p.GetPosition().y) for p in self.fp.Pads() if p.GetNumber() == "1"]
        self.assertTrue(all(y > 0 for y in vin_y))

    def test_vout_pairs_at_output_end(self):
        xs = sorted(ToMM(p.GetPosition().x) for p in self.fp.Pads() if p.GetNumber() == "3")
        self.assertLess(xs[0], 1.0)  # the signal-row VOUT pad
        self.assertTrue(all(x > 15 for x in xs[1:]))

    def test_pad_clearance(self):
        pads = list(self.fp.Pads())
        for i, a in enumerate(pads):
            for b in pads[i + 1:]:
                d = math.dist((ToMM(a.GetPosition().x), ToMM(a.GetPosition().y)),
                              (ToMM(b.GetPosition().x), ToMM(b.GetPosition().y)))
                gap = d - ToMM(a.GetSize().x) / 2 - ToMM(b.GetSize().x) / 2
                self.assertGreaterEqual(gap, 0.4 - 1e-6, "%s-%s" % (a.GetNumber(), b.GetNumber()))

    def test_courtyard_is_outline_plus_half_mm(self):
        self.fp.BuildCourtyardCaches()
        bb = self.fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        self.assertAlmostEqual(ToMM(bb.GetWidth()), 41.6, delta=0.1)
        self.assertAlmostEqual(ToMM(bb.GetHeight()), 21.3, delta=0.1)


if __name__ == "__main__":
    unittest.main()
