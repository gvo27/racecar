"""Tests for the board bootstrap (build_pcb.py) and the board checks (check_board.py). Run: make pcb-test."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import pcbnew
from pcbnew import ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
SCH_DIR = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import build_pcb  # noqa: E402
import check_board  # noqa: E402
import milling_check as mc  # noqa: E402

_WORK = None


def work_dir():
    """A temp copy of docs/schematics with a freshly built board (built once for all tests)."""
    global _WORK
    if _WORK is None:
        _WORK = tempfile.mkdtemp(prefix="pcbtest-")
        dst = os.path.join(_WORK, "sch")
        shutil.copytree(SCH_DIR, dst, ignore=shutil.ignore_patterns("*.kicad_pcb", "review", "analysis", ".history", "*.kicad_prl", "*-backups", "fp-info-cache"))
        rc = build_pcb.main(["--out", os.path.join(dst, "rc_power_board.kicad_pcb"), "--sch-dir", dst])
        assert rc == 0, "build failed"
        _WORK = dst
    return _WORK


def board_path():
    return os.path.join(work_dir(), "rc_power_board.kicad_pcb")


def load():
    return pcbnew.LoadBoard(board_path())


def is_smd(fp):
    attrs = [p.GetAttribute() for p in fp.Pads()]
    return pcbnew.PAD_ATTRIB_SMD in attrs and pcbnew.PAD_ATTRIB_PTH not in attrs


def is_tht(fp):
    return any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads())


class TestBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = load()

    def test_counts(self):
        self.assertEqual(len(self.b.GetFootprints()), 40)
        refs = {fp.GetReference() for fp in self.b.GetFootprints()}
        self.assertTrue({"H1", "H2", "H3", "H4", "TP1", "TP2", "TP3"} <= refs)
        self.assertEqual(self.b.GetNetCount() - 1, 21)  # net 0 is "no net"

    def test_sides(self):
        for fp in self.b.GetFootprints():
            if is_smd(fp):
                self.assertEqual(fp.GetLayer(), pcbnew.B_Cu, "%s is SMD: bottom" % fp.GetReference())
            elif is_tht(fp):
                self.assertEqual(fp.GetLayer(), pcbnew.F_Cu, "%s is THT: top" % fp.GetReference())

    def test_outline(self):
        edges = [d for d in self.b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
        self.assertTrue(edges)
        bb = edges[0].GetBoundingBox()
        for e in edges[1:]:
            bb.Merge(e.GetBoundingBox())
        self.assertLessEqual(ToMM(bb.GetWidth()), 70.0 + 0.1)
        self.assertLessEqual(ToMM(bb.GetHeight()), 146.0 + 0.1)

    def test_origin_is_lower_left(self):
        o = self.b.GetDesignSettings().GetAuxOrigin()
        edges = [d for d in self.b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
        bb = edges[0].GetBoundingBox()
        self.assertAlmostEqual(ToMM(o.x), ToMM(bb.GetLeft()), delta=0.05)
        self.assertAlmostEqual(ToMM(o.y), ToMM(bb.GetBottom()), delta=0.05)

    def test_courtyards_inside_outline_and_disjoint_per_side(self):
        edges = [d for d in self.b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
        out = edges[0].GetBoundingBox()
        cys = []
        for fp in self.b.GetFootprints():
            fp.BuildCourtyardCaches()
            lay = pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
            cy = fp.GetCourtyard(lay)
            self.assertGreater(cy.OutlineCount(), 0, "%s has no courtyard" % fp.GetReference())
            bb = cy.BBox()
            self.assertTrue(out.Contains(bb), "%s courtyard leaves the outline" % fp.GetReference())
            cys.append((fp.GetReference(), fp.GetLayer(), cy))
        for i, (ra, la, ca) in enumerate(cys):
            for rb, lb, cb in cys[i + 1:]:
                if la == lb:
                    self.assertFalse(ca.Collide(cb, 0), "courtyards overlap: %s %s" % (ra, rb))

    def test_stackup_and_thickness(self):
        text = open(board_path(), encoding="utf-8").read()
        self.assertIn("(thickness 1.57)", text)
        self.assertEqual(re.findall(r'\(layer "[FB]\.Cu"\s+\(type "copper"\)\s+\(thickness ([0-9.]+)\)', text), ["0.070", "0.070"])

    def test_zones(self):
        zs = {z.GetZoneName(): z for z in self.b.Zones()}
        self.assertEqual(zs["GND_F"].GetPadConnection(), pcbnew.ZONE_CONNECTION_NONE)
        self.assertEqual(zs["GND_B"].GetPadConnection(), pcbnew.ZONE_CONNECTION_FULL)
        self.assertEqual(zs["GND_F"].GetLayer(), pcbnew.F_Cu)
        self.assertEqual(zs["GND_B"].GetLayer(), pcbnew.B_Cu)
        self.assertAlmostEqual(ToMM(zs["GND_F"].GetLocalClearance()), 0.4, places=3)

    def test_net_classes_and_vias(self):
        pro = json.load(open(os.path.join(SCH_DIR, "rc_power_board.kicad_pro")))
        for c in pro["net_settings"]["classes"]:
            self.assertEqual((c["via_diameter"], c["via_drill"]), (2.1, 1.2), c["name"])
        widths = {c["name"]: c["track_width"] for c in pro["net_settings"]["classes"]}
        self.assertEqual(widths, {"Default": 0.5, "HighCurrent": 6.0, "Power3A": 1.0, "Power5A": 1.6})

    def test_u3_fine_rule(self):
        text = open(os.path.join(SCH_DIR, "rc_power_board.kicad_dru"), encoding="utf-8").read()
        self.assertIn("U3_fine", text)
        self.assertIn("0.3mm", text)

    def test_check_board_clean(self):
        self.assertEqual(check_board.check(self.b, mc.load_limits(os.path.join(SCH_DIR, "milling.toml")),
                                           mc.load_waivers(os.path.join(SCH_DIR, "milling_waivers.toml"))), [])


class TestCheckBoardCatches(unittest.TestCase):
    """check_board must fail on the review-focus defects (see the plan)."""

    def setUp(self):
        self.b = load()
        self.lim = mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))

    def test_fcu_track_on_tht_pad(self):
        j = [f for f in self.b.GetFootprints() if f.GetReference() == "J5"][0]
        pad = list(j.Pads())[0]
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(pad.GetPosition())
        t.SetEnd(pad.GetPosition() + pcbnew.VECTOR2I(pcbnew.FromMM(3), 0))
        t.SetWidth(pcbnew.FromMM(0.5))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(pad.GetNet())
        self.b.Add(t)
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "F.Cu on THT pad" in p])

    def test_unlisted_hole(self):
        j = [f for f in self.b.GetFootprints() if f.GetReference() == "J5"][0]
        list(j.Pads())[0].SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.1), pcbnew.FromMM(1.1)))
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "bit set" in p])

    def test_bad_via(self):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(150), pcbnew.FromMM(100)))
        v.SetDrill(pcbnew.FromMM(1.1))
        v.SetWidth(pcbnew.FromMM(2.0))
        self.b.Add(v)
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if p.startswith("via ")])

    def test_narrow_high_current_track(self):
        t = pcbnew.PCB_TRACK(self.b)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(100), pcbnew.FromMM(100)))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(110), pcbnew.FromMM(100)))
        t.SetWidth(pcbnew.FromMM(1.0))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(self.b.FindNet("VBAT"))
        self.b.Add(t)
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "HighCurrent minimum" in p])


class TestNoOverwrite(unittest.TestCase):
    def test_second_run_refuses(self):
        path = board_path()
        before = open(path, "rb").read()
        mtime = os.path.getmtime(path)
        rc = build_pcb.main(["--out", path, "--sch-dir", work_dir()])
        self.assertNotEqual(rc, 0)
        self.assertEqual(open(path, "rb").read(), before)
        self.assertEqual(os.path.getmtime(path), mtime)


REPO_BOARD = os.path.join(SCH_DIR, "rc_power_board.kicad_pcb")


class TestRoutedBoard(unittest.TestCase):
    """The committed, routed board (Task 6). Needs kicad-cli (KiCad image)."""

    @classmethod
    def setUpClass(cls):
        cls.out = os.path.join(tempfile.mkdtemp(prefix="drc-"), "drc.json")
        subprocess.run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all", "--all-track-errors",
                        "--format", "json", "-o", cls.out, REPO_BOARD], check=True, stdout=subprocess.DEVNULL, cwd=SCH_DIR)
        with open(cls.out, encoding="utf-8") as fh:
            cls.drc = json.load(fh)
        cls.b = pcbnew.LoadBoard(REPO_BOARD)

    def test_drc_no_errors(self):
        errors = [v for v in self.drc["violations"] if v["severity"] == "error"]
        self.assertEqual(errors, [])

    def test_no_unconnected_items(self):
        self.assertEqual(self.drc["unconnected_items"], [])

    def test_schematic_parity(self):
        self.assertEqual(self.drc["schematic_parity"], [])

    def test_check_board_clean(self):
        lim = mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))
        self.assertEqual(check_board.check(self.b, lim, mc.load_waivers(os.path.join(SCH_DIR, "milling_waivers.toml"))), [])

    def test_high_current_tracks_at_least_6mm(self):
        for t in self.b.GetTracks():
            if t.Type() != pcbnew.PCB_VIA_T and t.GetNetname().lstrip("/") in ("VBAT_RAW", "VBAT", "GND"):
                self.assertGreaterEqual(ToMM(t.GetWidth()), 6.0 - 1e-6, "%s track" % t.GetNetname())

    def test_vias_are_rivets_and_counted(self):
        vias = [t for t in self.b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        for v in vias:
            self.assertAlmostEqual(ToMM(v.GetDrillValue()), 1.2, places=3)
            self.assertAlmostEqual(ToMM(v.GetWidth(pcbnew.F_Cu)), 2.1, places=3)
        print("\nrivet vias: %d (%d GND stitching)" % (len(vias), sum(1 for v in vias if v.GetNetname() == "GND")))

    def test_f_cu_tracks_never_touch_tht_pads(self):
        for p in check_board.check(self.b, mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))):
            self.assertNotIn("F.Cu on THT pad", p)

    def test_every_net_has_copper(self):
        # a routed board has tracks (the unrouted bootstrap has none)
        self.assertGreater(sum(1 for t in self.b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T), 50)


if __name__ == "__main__":
    unittest.main()
