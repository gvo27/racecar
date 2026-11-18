"""Tests for gate_suppress.py: it applies the board suppressions to the schematic and PCB analyzer JSON.

The kicad-happy module project_config is the boundary: a stub stands in for it (stdlib unittest, no plugin needed).
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_suppress  # noqa: E402

STUB = '''
import fnmatch, json
def load_config_from_path(path):
    return json.load(open(path))
def apply_suppressions(findings, suppressions):
    for f in findings:
        m = [s for s in suppressions if s["rule_id"] == f.get("rule_id")
             and any(fnmatch.fnmatch(c, p) for c in f.get("components", []) for p in s.get("components", ["*"]))]
        f["suppressed"] = bool(m)
        f["suppression_reason"] = m[0].get("reason", "") if m else ""
    return findings
'''


class TestGateSuppress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        os.makedirs(os.path.join(d, "kh"))
        open(os.path.join(d, "kh", "project_config.py"), "w").write(STUB)
        self.cfg = os.path.join(d, "cfg.json")
        json.dump({"suppressions": [{"rule_id": "PU-001", "components": ["U1"], "reason": "fp"}]}, open(self.cfg, "w"))
        self.sch = os.path.join(d, "schematic.json")
        json.dump({"findings": [{"rule_id": "PU-001", "components": ["U1"], "severity": "warning"},
                                {"rule_id": "PU-001", "components": ["U9"], "severity": "warning"}],
                   "statistics": {"total_components": 3}}, open(self.sch, "w"))
        self.kh = os.path.join(d, "kh")

    def tearDown(self):
        self.tmp.cleanup()

    def test_marks_matching_findings_and_keeps_the_rest(self):
        n = gate_suppress.run(self.kh, self.cfg, [self.sch])
        data = json.load(open(self.sch))
        self.assertEqual(n, 1)
        self.assertEqual([f["suppressed"] for f in data["findings"]], [True, False])
        self.assertEqual(data["findings"][0]["suppression_reason"], "fp")
        self.assertEqual(data["statistics"], {"total_components": 3})

    def test_missing_file_is_skipped(self):
        self.assertEqual(gate_suppress.run(self.kh, self.cfg, [os.path.join(self.tmp.name, "none.json")]), 0)


if __name__ == "__main__":
    unittest.main()
