"""Board checks that KiCad DRC does not make (unplated, milled board). Make target: pcb-check.

check(board) -> list[str] of problems. CLI: check_board.py <board> [--limits milling.toml --waivers milling_waivers.toml]
exit 1 if there is any problem. Runs with the python3 of the KiCad image.
"""
import argparse
import os
import sys

import pcbnew
from pcbnew import ToMM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import milling_check as mc  # noqa: E402
import placement  # noqa: E402

SCH_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DRILL_SET = [0.8, 1.0, 1.2, 1.5]
VIA_DRILL, VIA_PAD = 1.2, 2.1
HIGH_CURRENT_MIN_W = 6.0
HIGH_CURRENT_NETS = ("VBAT_RAW", "VBAT")


def short(name):
    return name.lstrip("/")


def holes(board):
    """Every hole: (label, ref, diameter mm) for pads and vias."""
    out = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                s = p.GetDrillSize()
                out.append(("%s.%s" % (fp.GetReference(), p.GetNumber() or "-"), fp.GetReference(), ToMM(max(s.x, s.y))))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            out.append(("via", "via", ToMM(t.GetDrillValue())))
    return out


def check(board, limits=None, waivers=None):
    problems = []
    # 1. F.Cu copper on a THT pad (open on an unplated board)
    lim = limits or mc.load_limits(os.path.join(SCH_DIR, "milling.toml"))
    ctx = mc.Ctx(board, lim)
    found = []
    mc.check_fcu_tht(ctx, found)
    problems += ["F.Cu on THT pad: %s" % f[2] for f in found]
    # 2. holes outside the bit set and not listed as milled
    milled = set(placement.MILLED_HOLES)
    for label, ref, d in holes(board):
        if any(abs(d - s) < 0.005 for s in DRILL_SET):
            continue
        if any(r == ref and abs(d - m) < 0.005 for r, m in milled):
            continue
        problems.append("hole %.2f mm at %s is not in the bit set %s and not in MILLED_HOLES" % (d, label, DRILL_SET))
    # 3. rivet vias
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            drill, dia = ToMM(t.GetDrillValue()), ToMM(t.GetWidth(pcbnew.F_Cu))
            if abs(drill - VIA_DRILL) > 0.005 or abs(dia - VIA_PAD) > 0.005:
                problems.append("via %.2f/%.2f mm at %s (rivet via is %.1f/%.1f)" % (dia, drill, ctx.xy(t.GetPosition()), VIA_PAD, VIA_DRILL))
    # 4. HighCurrent tracks
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T and short(t.GetNetname()) in HIGH_CURRENT_NETS + ("GND",):
            if ToMM(t.GetWidth()) < HIGH_CURRENT_MIN_W - 1e-6:
                problems.append("%s track %.2f mm wide at %s (HighCurrent minimum %.1f mm)" % (short(t.GetNetname()), ToMM(t.GetWidth()), ctx.xy(t.GetStart()), HIGH_CURRENT_MIN_W))
    # 5. milling check: unwaived errors. MILL-DEPTH is a finding about the assumed limits (owner/lab tech), not the board:
    #    it is the only rule id left out here, and `make pcb-mill-check` keeps it visible.
    findings = mc.check(board, lim)
    groups = mc.triage(findings, waivers or [])
    for f in groups["errors"]:
        problems.append("%s %s: %s" % (f[0], f[2], f[5]))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("board")
    ap.add_argument("--limits", default=os.path.join(SCH_DIR, "milling.toml"))
    ap.add_argument("--waivers", default=os.path.join(SCH_DIR, "milling_waivers.toml"))
    args = ap.parse_args(argv)
    board = pcbnew.LoadBoard(args.board)
    problems = check(board, mc.load_limits(args.limits), mc.load_waivers(args.waivers))
    for p in problems:
        print("check_board: " + p)
    print("check_board: %d problems" % len(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
