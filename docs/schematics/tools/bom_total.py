"""BOM export and cost total (stdlib only; runs in the KiCad image).

    python3 tools/bom_total.py --export   # kicad-cli export to bom.csv, then totals
    python3 tools/bom_total.py            # totals only

Total = sum(Qty x Unit cost USD) of bom.csv (all rows) and of bom_offboard.csv
(rows with In total = yes). "Without in hand" leaves out rows with Status "in hand".
"""
import csv
import subprocess
import sys
from pathlib import Path

SCH_DIR = Path(__file__).resolve().parent.parent
SCH = SCH_DIR / "rc_power_board.kicad_sch"
BOM = SCH_DIR / "bom.csv"
OFFBOARD = SCH_DIR / "bom_offboard.csv"

FIELDS = ["Reference", "QUANTITY", "Value", "Footprint", "MPN", "Manufacturer", "Status",
          "Unit cost USD", "Supplier link", "BOM Comments"]
LABELS = ["Reference", "Qty", "Value", "Footprint", "MPN", "Manufacturer", "Status",
          "Unit cost USD", "Supplier link", "BOM Comments"]
GROUP_BY = ["Value", "Footprint", "MPN"]


def export(sch, out):
    """Write the grouped BOM CSV with kicad-cli."""
    subprocess.run(
        ["kicad-cli", "sch", "export", "bom", "--fields", ",".join(FIELDS),
         "--labels", ",".join(LABELS), "--group-by", ",".join(GROUP_BY),
         "--exclude-dnp", "-o", str(out), str(sch)],
        check=True, stdout=subprocess.DEVNULL)


def _rows(path, only_in_total=False):
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if only_in_total and row.get("In total") != "yes":
                continue
            yield row


def _line(row):
    cost = row["Unit cost USD"].strip()
    return int(row["Qty"]) * float(cost) if cost else 0.0


def totals(bom, offboard):
    """Return (total, total without in hand parts) in USD."""
    rows = list(_rows(bom)) + list(_rows(offboard, only_in_total=True))
    total = sum(_line(r) for r in rows)
    in_hand = sum(_line(r) for r in rows if r["Status"] == "in hand")
    return round(total, 2), round(total - in_hand, 2)


def main(argv):
    if "--export" in argv:
        export(SCH, BOM)
        print(f"wrote {BOM}")
    total, without = totals(BOM, OFFBOARD)
    print(f"BOM total (one board, USD): {total:.2f}")
    print(f"BOM total without in hand parts: {without:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
