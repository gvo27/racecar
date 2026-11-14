"""Count the violations in a kicad-cli ERC JSON report. Exit 1 if there is any error."""
import collections
import json
import sys


def main(argv):
    with open(argv[1], encoding="utf-8") as fh:
        report = json.load(fh)
    counts = collections.Counter()
    for sheet in report.get("sheets", []):
        for item in sheet.get("violations", []):
            counts[(item["severity"], item["type"])] += 1
    for (severity, kind), n in sorted(counts.items()):
        print("erc: %d x %s %s" % (n, severity, kind))
    errors = sum(n for (severity, _), n in counts.items() if severity == "error")
    print("erc: %d errors, %d warnings" % (errors, sum(n for (s, _), n in counts.items() if s == "warning")))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
