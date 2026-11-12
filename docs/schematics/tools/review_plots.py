"""Write the review files for the rev A board into docs/schematics/review/. Make target: pcb-review.

  drc.json                     kicad-cli DRC with schematic parity
  milling_check.json           milling check (groups: errors, waived, questions, bits, warnings)
  rc_power_board_layers.pdf    one page per layer: F.Cu, B.Cu, F.Fab, B.Fab (each with Edge.Cuts)
  rc_power_board_1to1.pdf      scale 1, pads and holes drawn on the fab layers, for the paper check with real parts
No Gerber, drill or CAM files: the lab tech gives those steps later. Runs with the python3 of the KiCad image.
Exit 0 when DRC has no error and no unconnected item, and the milling check has no unwaived error other than
MILL-DEPTH (a finding about the assumed limits); exit 1 otherwise.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drc_summary  # noqa: E402
import milling_check as mc  # noqa: E402

SCH_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, cwd=SCH_DIR)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--board", default=os.path.join(SCH_DIR, "rc_power_board.kicad_pcb"))
    ap.add_argument("--out", default=os.path.join(SCH_DIR, "review"))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    drc = os.path.join(args.out, "drc.json")
    run(["kicad-cli", "pcb", "drc", "--schematic-parity", "--severity-all", "--all-track-errors", "--format", "json",
         "-o", drc, args.board])
    run(["kicad-cli", "pcb", "export", "pdf", "--mode-multipage", "--layers", "F.Cu,B.Cu,F.Fab,B.Fab",
         "--common-layers", "Edge.Cuts", "-o", os.path.join(args.out, "rc_power_board_layers.pdf"), args.board])
    run(["kicad-cli", "pcb", "export", "pdf", "--mode-single", "--layers", "Edge.Cuts,F.Fab,B.Fab", "--scale", "1",
         "--sketch-pads-on-fab-layers", "--drill-shape-opt", "2", "--black-and-white",
         "-o", os.path.join(args.out, "rc_power_board_1to1.pdf"), args.board])
    findings, groups = mc.run(args.board, os.path.join(SCH_DIR, "milling.toml"), os.path.join(SCH_DIR, "milling_waivers.toml"))
    ser = {k: [list(f) for f in v] for k, v in groups.items() if k != "waived"}
    ser["waived"] = [{"finding": list(f), "waiver": w} for f, w in groups["waived"]]
    with open(os.path.join(args.out, "milling_check.json"), "w", encoding="utf-8") as fh:
        json.dump(ser, fh, indent=1)
    print(mc.report(groups))
    with open(drc, encoding="utf-8") as fh:
        s = drc_summary.summarise(json.load(fh))
    print("drc: %d errors, %d warnings %s, %d unconnected, parity %s" % (
        sum(s["errors"].values()), sum(s["warnings"].values()), dict(s["warnings"]), s["unconnected"], dict(s["parity"]) or "clean"))
    bad = sum(s["errors"].values()) or s["unconnected"] or s["parity"] or groups["errors"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
