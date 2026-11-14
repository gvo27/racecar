"""BOM checks (stdlib unittest, run in the KiCad image by `make pcb-test`).

- bom.csv equals a fresh `kicad-cli sch export bom` of the schematic (drift check).
- Every symbol except TP*, H*, J1 has a non-empty MPN (or TBD) and an allowed Status.
- bom_total reproduces the numbers of the old hand-kept bom.md.
"""
import csv
import re
import tempfile
import unittest
from pathlib import Path

import bom_total

SCH_DIR = Path(__file__).resolve().parent.parent
SCH = SCH_DIR / "rc_power_board.kicad_sch"
BOM = SCH_DIR / "bom.csv"
OFFBOARD = SCH_DIR / "bom_offboard.csv"
ALLOWED_STATUS = {"proposed", "assumed", "in hand", "TBD"}
EXEMPT = re.compile(r"^(TP\d+|H\d+|J1)$")

# Expected totals from the old bom.md (Subtotal section), USD.
EXPECTED_TOTAL = 94.02
EXPECTED_WITHOUT_IN_HAND = 14.12


def expand_refs(field):
    """'C2,C4' -> ['C2', 'C4']; 'D2-D4' -> ['D2', 'D3', 'D4']."""
    refs = []
    for part in field.split(","):
        m = re.fullmatch(r"([A-Z]+)(\d+)-([A-Z]+)(\d+)", part)
        if m:
            refs += [f"{m.group(1)}{n}" for n in range(int(m.group(2)), int(m.group(4)) + 1)]
        else:
            refs.append(part)
    return refs


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class BomTest(unittest.TestCase):
    def test_bom_csv_matches_fresh_export(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "bom.csv"
            bom_total.export(SCH, out)
            self.assertEqual(out.read_text(encoding="utf-8"), BOM.read_text(encoding="utf-8"),
                             "bom.csv is stale: run `make bom` and commit it")

    def test_every_symbol_has_mpn_and_status(self):
        refs = []
        for row in read(BOM):
            for ref in expand_refs(row["Reference"]):
                refs.append(ref)
                if EXEMPT.match(ref):
                    continue
                self.assertTrue(row["MPN"].strip(), f"{ref}: MPN empty (use TBD)")
                self.assertIn(row["Status"], ALLOWED_STATUS, f"{ref}: Status")
        self.assertEqual(len(refs), 40, "symbol count changed: update this test deliberately")

    def test_offboard_columns(self):
        for row in read(OFFBOARD):
            self.assertIn(row["In total"], {"yes", "no"}, row["Reference"])

    def test_totals(self):
        total, without_in_hand = bom_total.totals(BOM, OFFBOARD)
        self.assertAlmostEqual(total, EXPECTED_TOTAL, places=2)
        self.assertAlmostEqual(without_in_hand, EXPECTED_WITHOUT_IN_HAND, places=2)


if __name__ == "__main__":
    unittest.main()
