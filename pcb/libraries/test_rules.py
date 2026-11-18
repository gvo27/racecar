"""Tests for the design rules (rules.py), the rule generator (gen_rules.py), the schematic variant (variant.py) and the
design-rule checks of the milling check on the mill board. Run: make pcb-test (stdlib unittest, KiCad image python3)."""
import dataclasses
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import paths  # noqa: E402
import rules  # noqa: E402
import gen_rules  # noqa: E402
import variant  # noqa: E402

BASE = paths.base_board_dir()
MILL = os.path.join(paths.PCB_DIR, "src")
MILL_RULES = os.path.join(lab.lab_dir(), rules.FILE_NAME)
REV_B = os.path.join(paths.PCB_DIR, "releases", "rev2")
XH = {"J3", "J4", "J5", "J8", "J9", "J11", "J12", "J13", "J14"}


def edited(path, old, new):
    """A temp copy of a rules file with one text change."""
    text = open(path, encoding="utf-8").read()
    assert old in text, old
    fd, tmp = tempfile.mkstemp(suffix=".toml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))
    return tmp


class TestLoad(unittest.TestCase):
    def test_base_board_has_its_own_file_and_the_mill_board_uses_the_lab_file(self):
        self.assertEqual(rules.rules_file(BASE), os.path.join(BASE, rules.FILE_NAME))
        self.assertEqual(rules.rules_file(MILL), MILL_RULES)

    def test_base_rules_are_the_rev_a_values(self):
        r = rules.load(rules.rules_file(BASE))
        self.assertEqual((r.clearance, r.track_min, r.annular_min, r.edge_clearance), (0.4, 0.5, 0.45, 0.5))
        self.assertEqual(r.track_width, {"Default": 0.5, "HighCurrent": 6.0, "Power3A": 1.0, "Power5A": 1.6})
        self.assertEqual(r.assumed(), [])
        self.assertEqual(r.exclude, ())
        self.assertAlmostEqual(r.copper_target, 0.5)

    def test_mill_rules_are_wider_and_exclude_the_leds(self):
        r, base = rules.load(MILL_RULES), rules.load(rules.rules_file(BASE))
        self.assertGreater(r.clearance, base.clearance)
        self.assertGreater(r.track_width["Default"], base.track_width["Default"])
        self.assertGreater(r.horizontal_error, 0)
        self.assertEqual(set(r.exclude), {"D2", "D3", "D4", "R1", "R2", "R3"})
        self.assertAlmostEqual(r.copper_target, r.cut_spacing_min - r.clearance)
        self.assertAlmostEqual(r.gap_min(0.292), 0.292 + 2 * r.horizontal_error)
        self.assertTrue(r.exception_for("U3").zones)
        self.assertTrue(r.exception_for("J5").own_pads)          # pin headers: one entry with a refs list
        self.assertFalse(r.exception_for("J5").zones)
        self.assertIsNone(r.exception_for("J6"))                 # the USB pigtail terminals have no exception
        self.assertTrue(r.exception_for("U1").own_pads)          # module pins: only the pad gaps of the module itself
        self.assertFalse(r.exception_for("U2").zones)
        self.assertEqual(set(r.footprint), {"C2", "C3", "C4", "C5", "C6", "C7", "C8"})
        self.assertGreater(r.annular_target, r.annular_min)
        self.assertEqual(set(r.wire), XH)                         # temporary: wires soldered to the pads, first print round
        self.assertIn("temporary", r.wire_reason.lower())

    def test_rev_b_is_the_mill_board_with_the_headers(self):
        r = rules.load(rules.rules_file(REV_B))
        self.assertEqual(os.path.dirname(r.path), REV_B)          # frozen copy, not the lab tuning file
        self.assertEqual(r.wire, ())
        self.assertEqual(set(r.footprint), {"C2", "C3", "C4", "C5", "C6", "C7", "C8"})

    def test_bad_files_are_rejected(self):
        for old, new in (('[clearance]\nvalue = 0.8', '[clearance]\nvalue = 50'),            # out of range
                         ('[clearance]\nvalue = 0.8', '[clearence]\nvalue = 0.8'),           # unknown key, missing key
                         ('unit = "mm"\nstatus = "assumed"\n', 'unit = "mm"\n'),  # no status
                         ('[netclass.Default]\ntrack_width = 1.3', '[netclass.Default]\ntrack_width = 0.2'),  # below track_min
                         ('[zone_clearance]\nvalue = 2.0', '[zone_clearance]\nvalue = 0.2'),                # below clearance
                         ('[annular_target]\nvalue = 0.8', '[annular_target]\nvalue = 0.2'),                # below annular_min
                         ('own_pads = true  # only the pads of one header', 'own_pad = true'),              # unknown exception field
                         ('own_pads = true  # only the pads of one header', 'own_pads = true\nzones = true'),  # both forms
                         ('[parts.wire]\nrefs = [', '[parts.wire]\nrefs = ["C2", '),             # wire and other footprint
                         ('[parts.wire]\nrefs = [', '[parts.wire]\nrefz = [')):                     # unknown wire field
            with self.subTest(new=new), self.assertRaises(ValueError):
                rules.load(edited(MILL_RULES, old, new))

    def test_rules_below_a_lab_limit_are_reported(self):
        r = dataclasses.replace(rules.load(MILL_RULES), track_min=0.3)
        lim = {"track_min": {"value": 0.5}, "edge_clearance": {"value": 0.5}, "annular_min": {"value": 0.45}}
        self.assertEqual(len(rules.check_against_lab(r, lim)), 1)


class TestBaseBoard(unittest.TestCase):
    def test_makefile_base_board_is_the_paths_default(self):
        # one owner for the default board: paths.DEFAULT_BOARD; the Makefile keeps a copy for make
        with open(os.path.join(paths.REPO_ROOT, "Makefile"), encoding="utf-8") as f:
            line = next(ln for ln in f if ln.startswith("BASE_BOARD"))
        self.assertEqual(line.split(":=", 1)[1].strip(), paths.DEFAULT_BOARD.replace(os.sep, "/"))


class TestReviewDir(unittest.TestCase):
    def test_each_board_reviews_into_its_release_folder(self):
        want = {os.path.join("releases", "rev1"): "rev1", os.path.join("releases", "rev2"): "rev2", "src": "rev3"}
        for board, rev in want.items():
            self.assertEqual(paths.release_of(os.path.join(paths.PCB_DIR, board)), rev, board)
        old = os.environ.get("BOARD_DIR")
        try:
            os.environ["BOARD_DIR"] = os.path.join(paths.PCB_DIR, "src")
            self.assertEqual(paths.review_dir(), os.path.join(paths.DOCS_DIR, "releases", "rev3", "review"))
        finally:
            if old is None:
                os.environ.pop("BOARD_DIR", None)
            else:
                os.environ["BOARD_DIR"] = old

    def test_makefile_working_release_is_the_paths_value(self):
        # one owner for the next release of the working board: paths.WORKING_RELEASE; the Makefile keeps a copy
        with open(os.path.join(paths.REPO_ROOT, "Makefile"), encoding="utf-8") as f:
            line = next(ln for ln in f if ln.startswith("SRC_RELEASE"))
        self.assertEqual(line.split(":=", 1)[1].split("#")[0].strip(), paths.WORKING_RELEASE["src"])


class TestGenRules(unittest.TestCase):
    def test_project_files_of_both_boards_agree_with_their_rules(self):
        for board in (BASE, MILL, REV_B):
            with self.subTest(board=board):
                self.assertEqual(gen_rules.run(board, write=False), 0, "run make pcb-rules BOARD=%s PCB_RULES_ARGS=--write" % os.path.basename(board))

    def test_a_changed_rule_is_found(self):
        r = dataclasses.replace(rules.load(MILL_RULES), clearance=0.7)
        import json
        pro = json.load(open(os.path.join(MILL, paths.STEM + ".kicad_pro"), encoding="utf-8"))
        changed = {".".join(p) for p, _, _ in gen_rules.diff_pro(pro, gen_rules.want_pro(r, 1.1, 2.1))}
        self.assertIn("net_settings.classes.Default.clearance", changed)

    def test_exception_rule_text(self):
        r = rules.load(rules.rules_file(BASE))
        self.assertEqual(gen_rules.want_dru(r), [("U3_fine", "A.Type == 'Pad' && A.Reference == 'U3' && B.Type != 'Zone'", 0.3)])
        self.assertEqual(gen_rules.read_dru(os.path.join(BASE, paths.STEM + ".kicad_dru")), gen_rules.want_dru(r))
        mill = rules.load(MILL_RULES)
        self.assertNotIn("Zone", gen_rules.want_dru(mill)[0][1])
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.kicad_dru")
        open(p, "w", encoding="utf-8").write(gen_rules.dru_text(mill))
        self.assertEqual(gen_rules.read_dru(p), gen_rules.want_dru(mill))


class TestVariant(unittest.TestCase):
    def setUp(self):
        self.base = open(os.path.join(BASE, paths.STEM + ".kicad_sch"), encoding="utf-8").read()

    def test_only_the_excluded_parts_change(self):
        text, done = variant.make_variant(self.base, {"D2", "R1"})
        self.assertEqual(sorted(done), ["D2", "R1"])
        a, b = self.base.splitlines(), text.splitlines()
        self.assertEqual(len(a), len(b))
        diff = [(x.strip(), y.strip()) for x, y in zip(a, b) if x != y]
        self.assertEqual(sorted(diff), sorted([("(in_bom yes)", "(in_bom no)"), ("(on_board yes)", "(on_board no)"), ("(dnp no)", "(dnp yes)")] * 2))

    def test_footprint_of_a_part_changes_and_its_part_fields_are_tbd(self):
        fp = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm"
        text, done = variant.make_variant(self.base, set(), {"C6": fp})
        self.assertEqual(done, ["C6"])
        diff = [(x.strip(), y.strip()) for x, y in zip(self.base.splitlines(), text.splitlines()) if x != y]
        self.assertEqual(diff[0], ('(property "Footprint" "Capacitor_SMD:C_0805_2012Metric"', '(property "Footprint" "%s"' % fp))
        new = {y.split('"')[1]: y.split('"')[3] for _, y in diff[1:]}
        self.assertEqual(set(new), {"MPN", "Manufacturer", "Supplier link", "Status", "Unit cost USD", "BOM Comments"})
        self.assertEqual((new["MPN"], new["Manufacturer"], new["Status"], new["Unit cost USD"]), ("TBD", "TBD", "TBD", ""))
        self.assertIn("Base board part", new["BOM Comments"])

    def test_wire_part_gets_solder_pads_and_no_part_number(self):
        text, done = variant.make_variant(self.base, set(), wires={"J11", "J5"})
        self.assertEqual(sorted(done), ["J11", "J5"])
        diff = [y.strip() for x, y in zip(self.base.splitlines(), text.splitlines()) if x != y]
        self.assertIn('(property "Footprint" "rc_power:SolderWire_1x02_P2.50mm"', diff)   # pin count from the XH footprint
        self.assertIn('(property "Footprint" "rc_power:SolderWire_1x06_P2.50mm"', diff)
        new = [(y.split('"')[1], y.split('"')[3]) for y in diff if not y.startswith('(property "Footprint"')]
        self.assertEqual(sorted(set(n for n, _ in new)), ["BOM Comments", "MPN", "Manufacturer", "Status", "Supplier link", "Unit cost USD"])
        self.assertTrue(all(v in ("none", "") for n, v in new if n != "BOM Comments"))
        notes = [v for n, v in new if n == "BOM Comments"]
        self.assertTrue(all(v.startswith("Temporary (first mill print round)") and ("B2B-XH-A" in v or "B6B-XH-A" in v) for v in notes))

    def test_variant_keeps_its_own_title_block_revision(self):
        old = self.base.replace('(rev "1")', '(rev "3 (draft)")', 1)
        self.assertEqual(variant.keep_revision(self.base, old).count('(rev "3 (draft)")'), 1)
        self.assertEqual(variant.keep_revision(self.base, None), self.base)   # first run: the base revision

    def test_no_exclude_list_gives_the_base_schematic(self):
        self.assertEqual(variant.make_variant(self.base, set())[0], self.base)

    def test_committed_mill_schematic_is_current(self):
        r = rules.load(MILL_RULES)
        have = open(os.path.join(MILL, paths.STEM + ".kicad_sch"), encoding="utf-8").read()
        want = variant.keep_revision(variant.make_variant(self.base, set(r.exclude), r.footprint, set(r.wire))[0], have)
        self.assertEqual(have, want, "run make pcb-sch BOARD=src")

    def test_committed_rev_b_schematic_is_current(self):
        r = rules.load(rules.rules_file(REV_B))
        have = open(os.path.join(REV_B, paths.STEM + ".kicad_sch"), encoding="utf-8").read()
        want = variant.keep_revision(variant.make_variant(self.base, set(r.exclude), r.footprint, set(r.wire))[0], have)
        self.assertEqual(have, want)


class TestRingAndWidth(unittest.TestCase):
    """Pure helpers of build_pcb (ring_for) and route_pcb (fit_width)."""
    def test_pads_of_one_net_do_not_limit_the_ring(self):
        import build_pcb
        # four pads 2.5 mm apart on one net, the next net 5.8 mm away (F1): the full ring fits
        pads = [(0, 0, 1.4, 2.3, 2.3, 1), (2.5, 0, 1.4, 2.3, 2.3, 1), (8.3, 0, 1.4, 2.3, 2.3, 2)]
        self.assertAlmostEqual(build_pcb.ring_for(pads, 0.8, 0.45, 2.0), 0.8)
        # two nets 3.5 mm apart: the ring gets smaller
        pads = [(0, 0, 1.0, 1.9, 1.9, 1), (3.5, 0, 1.0, 1.9, 1.9, 2)]
        self.assertAlmostEqual(build_pcb.ring_for(pads, 0.8, 0.45, 2.0), 0.45)
        # pads with no net have nets of their own
        self.assertAlmostEqual(build_pcb.ring_for([(0, 0, 1.0, 1.9, 1.9, "a"), (3.5, 0, 1.0, 1.9, 1.9, "b")], 0.8, 0.45, 2.0), 0.45)

    def test_npth_cap_keeps_the_library_gap_or_the_rule_gap(self):
        import build_pcb
        hole = [(0.0, 0.0, 1.7)]
        self.assertAlmostEqual(build_pcb.npth_cap((2.9, 0, 1.4, 2.3, 2.3, 1), hole, 2.0), 2.3)   # 0.05 mm now: stays
        self.assertAlmostEqual(build_pcb.npth_cap((6.4, 0, 1.4, 2.3, 2.3, 1), hole, 2.0), 5.4)   # far: 2 mm gap
        self.assertEqual(build_pcb.npth_cap((6.4, 0, 1.4, 2.3, 2.3, 1), [], 2.0), float("inf"))

    def test_fit_width_steps_down_and_tests_the_floor(self):
        import route_pcb
        self.assertEqual(route_pcb.fit_width(13, 5, 1, lambda w: w > 9), (9, True))
        self.assertEqual(route_pcb.fit_width(13, 5, 1, lambda w: False), (13, True))
        self.assertEqual(route_pcb.fit_width(13, 5, 1, lambda w: True), (5, False))   # floor collides: reported
        self.assertEqual(route_pcb.fit_width(13, 5, 8, lambda w: w > 5), (5, True))   # rev1: full width or floor
        self.assertEqual(route_pcb.fit_width(5, 5, 1, lambda w: False), (5, True))


class TestMillBoard(unittest.TestCase):
    """The committed mill board against the mill rules, and the effect of a rule change on the checks."""
    @classmethod
    def setUpClass(cls):
        import pcbnew
        import milling_check as mc
        cls.mc = mc
        cls.board = pcbnew.LoadBoard(os.path.join(MILL, paths.STEM + ".kicad_pcb"))
        cls.lim = mc.load_limits(lab.limits_file())
        cls.rules = rules.load(MILL_RULES)

    def errors(self, r):
        return [f for f in self.mc.check(self.board, self.lim, r) if f[1] == "error" and f[0] != "MILL-DEPTH"]

    def test_excluded_parts_are_not_on_the_board(self):
        refs = {fp.GetReference() for fp in self.board.GetFootprints()}
        self.assertFalse(refs & set(self.rules.exclude))
        self.assertTrue({"U3", "C6", "C7", "C8", "FB1", "TP3"} <= refs)

    def test_capacitors_are_through_hole_with_the_ring_target(self):
        import pcbnew
        for ref in ("C2", "C3", "C4", "C5", "C6", "C7", "C8"):
            fp = self.board.FindFootprintByReference(ref)
            self.assertEqual(str(fp.GetFPID().GetLibItemName()), "C_Disc_D5.0mm_W2.5mm_P5.00mm")
            for p in fp.Pads():
                ring = (pcbnew.ToMM(p.GetSize(pcbnew.B_Cu).x) - pcbnew.ToMM(p.GetDrillSize().x)) / 2.0
                self.assertAlmostEqual(ring, self.rules.annular_target, places=2)
        # C9 (3.5 mm pitch) keeps the minimum ring: a larger pad brings its two pads nearer than component_gap
        p = next(iter(self.board.FindFootprintByReference("C9").Pads()))
        self.assertAlmostEqual((pcbnew.ToMM(p.GetSize(pcbnew.B_Cu).x) - pcbnew.ToMM(p.GetDrillSize().x)) / 2.0, self.rules.annular_min, places=2)

    def test_board_has_no_milling_error_with_the_committed_rules(self):
        self.assertEqual(self.errors(self.rules), [])

    def test_fixed_gaps_and_thin_copper_are_listed(self):
        ids = {f[0] for f in self.mc.check(self.board, self.lim, self.rules)}
        self.assertIn("MILL-GAP-FIXED", ids)       # U3 pads
        self.assertIn("MILL-CUT-SPACING", ids)     # copper below the copper target

    def test_a_larger_horizontal_error_makes_gap_errors(self):
        r = dataclasses.replace(self.rules, horizontal_error=0.5)  # needs 1.292 mm, tracks and pads are 0.8 mm apart
        self.assertIn("MILL-GAP", {f[0] for f in self.errors(r)})

    def test_gap_at_an_exception_pad_is_fixed_only_for_its_own_pads_and_zone_fill(self):
        fixed = [f for f in self.mc.check(self.board, self.lim, self.rules) if f[0] == "MILL-GAP-FIXED"]
        self.assertTrue(fixed)
        zone_refs = {e.ref for e in self.rules.exceptions if e.zones}
        ref = lambda s: s.split()[1].split(".")[0] if s.startswith("pad ") else None  # noqa: E731
        for f in fixed:
            a, b = f[2].split(" | ")
            self.assertNotIn("track", f[2])
            if "zone fill" in a + b:   # zone fill only at a pad of a part with zones = true (U3)
                self.assertIn(ref(a) or ref(b), zone_refs, f[2])
            else:                      # else two pads of one part
                self.assertEqual(ref(a), ref(b), f[2])
        self.assertTrue(any("pad U3." in f[2] for f in fixed))
        self.assertTrue(any("pad J5." in f[2] for f in fixed))
        self.assertFalse(any("zone fill" in f[2] and ("pad U1." in f[2] or "pad U2." in f[2]) for f in fixed))

    def test_f1_rings_grow_except_at_the_holder_hole(self):
        import pcbnew
        fp = self.board.FindFootprintByReference("F1")
        hole = next(p for p in fp.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH)
        hr = pcbnew.ToMM(hole.GetDrillSize().x) / 2.0
        grown = 0
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or not p.HasHole():
                continue
            ring = (pcbnew.ToMM(p.GetSize(pcbnew.B_Cu).x) - pcbnew.ToMM(p.GetDrillSize().x)) / 2.0
            gap = pcbnew.ToMM((p.GetPosition() - hole.GetPosition()).EuclideanNorm()) - hr - pcbnew.ToMM(p.GetSize(pcbnew.B_Cu).x) / 2.0
            self.assertGreater(gap, 0.0)                      # no copper on the unplated hole
            grown += ring >= self.rules.annular_target - 0.005
        self.assertEqual(grown, 4)                            # the outer pads: pads of one net do not limit the ring

    def test_exception_part_is_in_the_component_gap_check(self):
        r = dataclasses.replace(self.rules, component_gap=2.6)  # U3 to C6 is 2.55 mm
        hits = [f[2] for f in self.errors(r) if f[0] == "MILL-COMP-GAP"]
        self.assertTrue(any("pad U3." in h for h in hits), hits)

    def test_a_larger_component_gap_makes_errors(self):
        r = dataclasses.replace(self.rules, component_gap=4.0)
        self.assertIn("MILL-COMP-GAP", {f[0] for f in self.errors(r)})

    def test_without_design_rules_the_lab_limits_alone_pass(self):
        ids = {f[0] for f in self.mc.check(self.board, self.lim) if f[1] == "error" and f[0] != "MILL-DEPTH"}
        self.assertEqual(ids, set())


if __name__ == "__main__":
    unittest.main()
