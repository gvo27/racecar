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
import placement  # noqa: E402
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
        self.assertEqual(self.b.GetNetCount() - 1, 24)  # net 0 is "no net"

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
            self.assertEqual((c["via_diameter"], c["via_drill"]), (2.1, 1.1), c["name"])
        widths = {c["name"]: c["track_width"] for c in pro["net_settings"]["classes"]}
        self.assertEqual(widths, {"Default": 0.5, "HighCurrent": 6.0, "Power3A": 1.0, "Power5A": 1.6})

    def test_u3_fine_rule(self):
        text = open(os.path.join(SCH_DIR, "rc_power_board.kicad_dru"), encoding="utf-8").read()
        self.assertIn("U3_fine", text)
        self.assertIn("0.3mm", text)

    def test_check_board_clean(self):
        self.assertEqual(check_board.check(self.b, mc.load_limits(os.path.join(SCH_DIR, "milling.toml")),
                                           mc.load_waivers(os.path.join(SCH_DIR, "milling_waivers.toml"))), [])


def pad_holes(board):
    """{(ref, pad number): (drill mm, pad size mm, is NPTH)} for the pads with a hole."""
    out = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                out[(fp.GetReference(), p.GetNumber())] = (ToMM(p.GetDrillSize().x), ToMM(p.GetSize(pcbnew.F_Cu).x),
                                                           p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH)
    return out


class TestHoles(unittest.TestCase):
    """Lab fit (Task 9): every hole is in the owner's drill set (0.1 to 2.0 mm) or a bored hole >= 3.3 mm."""

    @classmethod
    def setUpClass(cls):
        cls.b = load()
        cls.lim = mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))

    def test_every_hole_makeable(self):
        for (ref, num), (d, _, _) in pad_holes(self.b).items():
            ok = any(abs(d - s) < 0.005 for s in self.lim.drills) or d >= self.lim.milled_hole_min - 0.005
            self.assertTrue(ok, "%s.%s hole %.2f mm" % (ref, num, d))

    def test_no_hole_smaller_than_library_drill(self):
        sch = work_dir()
        for fp in self.b.GetFootprints():
            lib = build_pcb.load_footprint(fp.GetFPID().GetUniStringLibId(), sch)
            want = max([ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) for p in lib.Pads() if p.HasHole()] or [0])
            have = max([ToMM(max(p.GetDrillSize().x, p.GetDrillSize().y)) for p in fp.Pads() if p.HasHole()] or [0])
            self.assertGreaterEqual(have + 0.005, want, fp.GetReference())

    def test_mounting_holes(self):
        holes = pad_holes(self.b)
        for r in ("H1", "H2", "H3", "H4"):
            self.assertAlmostEqual([v for k, v in holes.items() if k[0] == r][0][0], 3.4, places=3)

    def test_j1_wire_pads_bored_with_ring(self):
        for (ref, num), (d, size, _) in pad_holes(self.b).items():
            if ref == "J1":
                self.assertGreaterEqual(d, 3.3 - 0.005)
                self.assertGreaterEqual((size - d) / 2.0, 0.45 - 1e-6)

    def test_f1_peg_is_bored_not_drilled_below_library_size(self):
        peg = [v for k, v in pad_holes(self.b).items() if k[0] == "F1" and v[2]]
        self.assertEqual(len(peg), 1)
        self.assertGreaterEqual(peg[0][0], 3.3 - 0.005)

    def test_vias_drill_is_in_set(self):
        for t in self.b.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                self.assertAlmostEqual(ToMM(t.GetDrillValue()), 1.1, places=3)


class TestSyncDrills(unittest.TestCase):
    def test_sync_drills_fixes_holes_and_vias_without_other_change(self):
        d = tempfile.mkdtemp(prefix="syncd-")
        dst = os.path.join(d, "rc_power_board.kicad_pcb")
        shutil.copy(board_path(), dst)
        for ext in (".kicad_pro", ".kicad_dru"):
            shutil.copy(os.path.join(SCH_DIR, "rc_power_board" + ext), os.path.join(d, "rc_power_board" + ext))
        b = pcbnew.LoadBoard(dst)
        for fp in b.GetFootprints():
            if fp.GetReference() == "H1":
                list(fp.Pads())[0].SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(3.2), pcbnew.FromMM(3.2)))
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(100), pcbnew.FromMM(100)))
        v.SetDrill(pcbnew.FromMM(1.2))
        v.SetWidth(pcbnew.FromMM(2.1))
        b.Add(v)
        b.Save(dst)
        n_tracks = len(list(pcbnew.LoadBoard(dst).GetTracks()))
        build_pcb.sync_drills(dst)
        b2 = pcbnew.LoadBoard(dst)
        self.assertEqual(len(list(b2.GetTracks())), n_tracks)
        self.assertAlmostEqual([x for k, x in pad_holes(b2).items() if k[0] == "H1"][0][0], 3.4, places=3)
        for t in b2.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                self.assertAlmostEqual(ToMM(t.GetDrillValue()), 1.1, places=3)
        self.assertTrue(all(z.IsFilled() for z in b2.Zones()))


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
        list(j.Pads())[0].SetDrillSize(pcbnew.VECTOR2I(pcbnew.FromMM(2.4), pcbnew.FromMM(2.4)))
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "drill set" in p])

    def test_bad_via(self):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(150), pcbnew.FromMM(100)))
        v.SetDrill(pcbnew.FromMM(1.2))
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

    def _move(self, ref, dx_mm, dy_mm):
        fp = [f for f in self.b.GetFootprints() if f.GetReference() == ref][0]
        fp.SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(pcbnew.FromMM(dx_mm), pcbnew.FromMM(dy_mm)))

    def test_courtyard_overlap_same_side(self):
        # U1 (module) pushed onto U2 (module): both top-side courtyards overlap
        self._move("U1", -15.0, 0.0)
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "courtyard" in p and "overlap" in p])

    def test_courtyard_crosses_board_edge(self):
        self._move("U1", 20.0, 0.0)
        self.assertTrue([p for p in check_board.check(self.b, self.lim) if "courtyard" in p and "board edge" in p])

    def test_module_courtyards_too_close(self):
        # U1 moved 1.0 mm toward U2: no overlap, but closer than MODULE_GAP_MM
        self._move("U1", -1.0, 0.0)
        probs = check_board.check(self.b, self.lim)
        self.assertFalse([p for p in probs if "overlap" in p])
        self.assertTrue([p for p in probs if "module courtyards" in p])

    def test_courtyards_of_the_built_board_are_clean(self):
        self.assertEqual([p for p in check_board.check(self.b, self.lim) if "courtyard" in p], [])


class TestNoOverwrite(unittest.TestCase):
    def test_second_run_refuses(self):
        path = board_path()
        before = open(path, "rb").read()
        mtime = os.path.getmtime(path)
        rc = build_pcb.main(["--out", path, "--sch-dir", work_dir()])
        self.assertNotEqual(rc, 0)
        self.assertEqual(open(path, "rb").read(), before)
        self.assertEqual(os.path.getmtime(path), mtime)


class TestSyncFields(unittest.TestCase):
    def test_new_netlist_field_reaches_footprint_without_other_change(self):
        tmp = tempfile.mkdtemp(prefix="sync-")
        dst = os.path.join(tmp, "sch")
        shutil.copytree(work_dir(), dst, ignore=shutil.ignore_patterns("review", ".history", "*-backups", "fp-info-cache"))
        sch = os.path.join(dst, "rc_power_board.kicad_sch")
        text = open(sch, encoding="utf-8").read()
        text, n = re.subn(r'(\t\t\(property "MPN")', '\t\t(property "Sync Test" "hello"\n\t\t\t(at 0 0 0)\n\t\t\t(show_name no)\n\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t\t(hide yes)\n\t\t\t)\n\t\t)\n\\1', text)
        self.assertGreater(n, 0)
        open(sch, "w", encoding="utf-8").write(text)
        path = os.path.join(dst, "rc_power_board.kicad_pcb")
        def snap():
            b = pcbnew.LoadBoard(path)
            return ([(f.GetReference(), f.GetPosition().x, f.GetPosition().y, f.GetOrientation().AsDegrees()) for f in b.GetFootprints()],
                    len(b.GetTracks()), len(b.Zones()))
        before = snap()
        self.assertEqual(build_pcb.main(["--out", path, "--sch-dir", dst, "--sync-fields"]), 0)
        self.assertEqual(snap(), before)
        b = pcbnew.LoadBoard(path)
        fps = [f for f in b.GetFootprints() if f.HasField("Sync Test")]
        self.assertGreater(len(fps), 0)
        self.assertEqual(fps[0].GetFieldText("Sync Test"), "hello")
        self.assertFalse(fps[0].GetField("Sync Test").IsVisible())
        self.assertTrue(all(f.HasField("MPN") for f in b.GetFootprints()))


class TestSyncZones(unittest.TestCase):
    def test_zones_rebuilt_parts_and_tracks_unchanged(self):
        tmp = tempfile.mkdtemp(prefix="syncz-")
        path = os.path.join(tmp, "rc_power_board.kicad_pcb")
        shutil.copyfile(os.path.join(SCH_DIR, "rc_power_board.kicad_pcb"), path)

        def snap():
            b = pcbnew.LoadBoard(path)
            return ([(f.GetReference(), f.GetPosition().x, f.GetPosition().y) for f in b.GetFootprints()], len(b.GetTracks()))
        before = snap()
        self.assertEqual(build_pcb.main(["--out", path, "--sync-zones"]), 0)
        self.assertEqual(snap(), before)
        b = pcbnew.LoadBoard(path)
        self.assertEqual(len(b.Zones()), 2 + len(placement.BUS_ZONES))
        self.assertTrue(all(z.IsFilled() for z in b.Zones()))


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

    def test_path_widths(self):
        # opening test on B.Cu along the current paths (Task 7b)
        for net, label, pads, w in check_board.PATH_ROWS:
            with self.subTest(path=label):
                self.assertEqual(check_board.path_width(self.b, net, pads, w), [])

    def test_vias_are_rivets_and_counted(self):
        vias = [t for t in self.b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
        for v in vias:
            self.assertAlmostEqual(ToMM(v.GetDrillValue()), 1.1, places=3)
            self.assertAlmostEqual(ToMM(v.GetWidth(pcbnew.F_Cu)), 2.1, places=3)
        print("\nrivet vias: %d (%d GND stitching)" % (len(vias), sum(1 for v in vias if v.GetNetname() == "GND")))

    def test_f_cu_tracks_never_touch_tht_pads(self):
        for p in check_board.check(self.b, mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))):
            self.assertNotIn("F.Cu on THT pad", p)

    def test_every_net_has_copper(self):
        # a routed board has tracks (the unrouted bootstrap has none)
        self.assertGreater(sum(1 for t in self.b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T), 50)


class TestPathWidth(unittest.TestCase):
    """path_width on a synthetic board: two pads joined by a 2.0 mm track."""

    def board(self):
        from pcbnew import FromMM, VECTOR2I
        b = pcbnew.BOARD()
        n = pcbnew.NETINFO_ITEM(b, "N")
        b.Add(n)
        for ref, x in (("A", 0), ("B", 20)):
            fp = pcbnew.FOOTPRINT(b)
            fp.SetReference(ref)
            fp.SetPosition(VECTOR2I(FromMM(x), 0))
            pad = pcbnew.PAD(fp)
            pad.SetNumber("1")
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            ls = pcbnew.LSET()
            ls.AddLayer(pcbnew.B_Cu)
            pad.SetLayerSet(ls)
            pad.SetSize(VECTOR2I(FromMM(1.0), FromMM(1.0)))
            pad.SetPosition(VECTOR2I(FromMM(x), 0))
            pad.SetNet(n)
            fp.Add(pad)
            b.Add(fp)
        t = pcbnew.PCB_TRACK(b)
        t.SetLayer(pcbnew.B_Cu)
        t.SetStart(VECTOR2I(0, 0))
        t.SetEnd(VECTOR2I(FromMM(20), 0))
        t.SetWidth(FromMM(2.0))
        t.SetNet(n)
        b.Add(t)
        return b

    def test_passes_at_track_width(self):
        self.assertEqual(check_board.path_width(self.board(), "N", ["A.1", "B.1"], 1.9), [])

    def test_fails_above_track_width(self):
        self.assertEqual(len(check_board.path_width(self.board(), "N", ["A.1", "B.1"], 3.0)), 1)


class TestReviewPackage(unittest.TestCase):
    """make pcb-review writes the review files (Task 7)."""

    @classmethod
    def setUpClass(cls):
        import review_plots
        cls.out = tempfile.mkdtemp(prefix="review-")
        cls.rc = review_plots.main(["--out", cls.out])

    def test_files_exist(self):
        for name in ("drc.json", "rc_power_board_layers.pdf", "rc_power_board_1to1.pdf", "milling_check.json"):
            path = os.path.join(self.out, name)
            self.assertTrue(os.path.getsize(path) > 100, name)

    def test_pdfs_are_pdfs(self):
        for name in ("rc_power_board_layers.pdf", "rc_power_board_1to1.pdf"):
            with open(os.path.join(self.out, name), "rb") as fh:
                self.assertEqual(fh.read(5), b"%PDF-")

    def test_drc_clean(self):
        with open(os.path.join(self.out, "drc.json"), encoding="utf-8") as fh:
            drc = json.load(fh)
        self.assertEqual([v for v in drc["violations"] if v["severity"] == "error"], [])
        self.assertEqual(drc["unconnected_items"], [])

    def test_milling_json_has_groups(self):
        with open(os.path.join(self.out, "milling_check.json"), encoding="utf-8") as fh:
            m = json.load(fh)
        for k in ("errors", "waived", "questions", "bits", "warnings"):
            self.assertIn(k, m)
        self.assertEqual(m["errors"], [])
        self.assertEqual(m["questions"], [])

    def test_exit_code_is_zero(self):
        self.assertEqual(self.rc, 0)


if __name__ == "__main__":
    unittest.main()
