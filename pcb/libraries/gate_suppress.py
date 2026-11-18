"""Apply the board suppressions to the schematic and PCB analyzer JSON (make pcb-gate, pcb_gate.sh).

kicad-happy 2.3.2 applies the `suppressions` of .kicad-happy.json in analyze_emc.py and analyze_thermal.py, but not in
analyze_schematic.py and analyze_pcb.py. This script uses the plugin's own functions (project_config.load_config_from_path
and apply_suppressions), so the matching rules are the upstream rules. Findings are marked, never removed.

Usage: gate_suppress.py <kicad scripts dir> <config file> <analyzer json> [...]. Stdlib only.
"""
import json
import os
import sys


def run(scripts_dir, config_path, json_paths):
    """Mark the suppressed findings in each JSON file. Return the count of suppressed findings."""
    sys.path.insert(0, scripts_dir)
    import project_config  # the kicad-happy module (the boundary)
    suppressions = project_config.load_config_from_path(config_path).get("suppressions", [])
    count = 0
    for path in json_paths:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        findings = data.get("findings") or []
        project_config.apply_suppressions(findings, suppressions)
        count += sum(1 for f in findings if f.get("suppressed"))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    return count


def main(argv):
    if len(argv) < 3:
        print("usage: gate_suppress.py <kicad scripts dir> <config file> <analyzer json> [...]", file=sys.stderr)
        return 2
    n = run(argv[0], argv[1], argv[2:])
    print("gate_suppress: %d finding(s) suppressed in %s" % (n, ", ".join(os.path.basename(p) for p in argv[2:])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
