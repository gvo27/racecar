"""Summarise a kicad-cli DRC JSON report. Exit 1 on any error or unconnected item; warnings are listed."""
import collections
import json
import sys


def summarise(report):
    out = {"errors": collections.Counter(), "warnings": collections.Counter(), "unconnected": 0, "parity": collections.Counter()}
    for v in report.get("violations", []):
        (out["errors"] if v["severity"] == "error" else out["warnings"])[v["type"]] += 1
    out["unconnected"] = len(report.get("unconnected_items", []))
    for v in report.get("schematic_parity", []):
        out["parity"][v["severity"] + " " + v["type"]] += 1
    return out


def main(argv):
    with open(argv[1], encoding="utf-8") as fh:
        s = summarise(json.load(fh))
    print("drc: %d errors %s" % (sum(s["errors"].values()), dict(s["errors"])))
    print("drc: %d warnings %s" % (sum(s["warnings"].values()), dict(s["warnings"])))
    print("drc: %d unconnected items" % s["unconnected"])
    print("drc: parity %s" % (dict(s["parity"]) or "clean"))
    return 1 if sum(s["errors"].values()) or s["unconnected"] or s["parity"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
