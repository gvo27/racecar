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

BASE = os.path.join(paths.PCB_DIR, "fabhouse")
MILL = os.path.join(paths.PCB_DIR, "mill")
MILL_RULES = os.path.join(lab.lab_dir(), rules.FILE_NAME)


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

    def test_bad_files_are_rejected(self):
        for old, new in (('[clearance]\nvalue = 0.5', '[clearance]\nvalue = 50'),            # out of range
                         ('[clearance]\nvalue = 0.5', '[clearence]\nvalue = 0.5'),           # unknown key, missing key
                         ('status = "assumed"\nsource = "start value (owner', 'source = "start value (owner'),  # no status
                         ('[netclass.Default]\ntrack_width = 1.5', '[netclass.Default]\ntrack_width = 0.2'),  # below track_min
                         ('[zone_clearance]\nvalue = 0.5', '[zone_clearance]\nvalue = 0.2')):  # below clearance
            with self.subTest(new=new), self.assertRaises(ValueError):
                rules.load(edited(MILL_RULES, old, new))

    def test_rules_below_a_lab_limit_are_reported(self):
        r = dataclasses.replace(rules.load(MILL_RULES), track_min=0.3)
        lim = {"track_min": {"value": 0.5}, "edge_clearance": {"value": 0.5}, "annular_min": {"value": 0.45}}
        self.assertEqual(len(rules.check_against_lab(r, lim)), 1)


class TestGenRules(unittest.TestCase):
    def test_project_files_of_both_boards_agree_with_their_rules(self):
        for board in (BASE, MILL):
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

    def test_no_exclude_list_gives_the_base_schematic(self):
        self.assertEqual(variant.make_variant(self.base, set())[0], self.base)

    def test_committed_mill_schematic_is_current(self):
        want = variant.make_variant(self.base, set(rules.load(MILL_RULES).exclude))[0]
        self.assertEqual(open(os.path.join(MILL, paths.STEM + ".kicad_sch"), encoding="utf-8").read(), want, "run make pcb-sch BOARD=mill")


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

    def test_board_has_no_milling_error_with_the_committed_rules(self):
        self.assertEqual(self.errors(self.rules), [])

    def test_fixed_gaps_and_thin_copper_are_listed(self):
        ids = {f[0] for f in self.mc.check(self.board, self.lim, self.rules)}
        self.assertIn("MILL-GAP-FIXED", ids)       # U3 pads
        self.assertIn("MILL-CUT-SPACING", ids)     # copper below the copper target

    def test_a_larger_horizontal_error_makes_gap_errors(self):
        r = dataclasses.replace(self.rules, horizontal_error=0.2)  # needs 0.692 mm, the board has 0.5 mm gaps
        self.assertIn("MILL-GAP", {f[0] for f in self.errors(r)})

    def test_a_larger_component_gap_makes_errors(self):
        r = dataclasses.replace(self.rules, component_gap=4.0)
        self.assertIn("MILL-COMP-GAP", {f[0] for f in self.errors(r)})

    def test_without_design_rules_the_lab_limits_alone_pass(self):
        ids = {f[0] for f in self.mc.check(self.board, self.lim) if f[1] == "error" and f[0] != "MILL-DEPTH"}
        self.assertEqual(ids, set())


if __name__ == "__main__":
    unittest.main()
