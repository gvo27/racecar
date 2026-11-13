"""Bootstrap rc_power_board.kicad_pcb from the schematic netlist (first build only).

After the first build the .kicad_pcb is the owner's file: this script refuses to overwrite it without --force.
Runs with the python3 of the KiCad image (pcbnew, kicad-cli). Make target: pcb-build.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import placement  # noqa: E402

SCH_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCHEMATIC = "rc_power_board.kicad_sch"
BOARD_FILE = "rc_power_board.kicad_pcb"
FP_DIR = os.environ.get("KICAD10_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
LIMITS_FILE = os.path.join(SCH_DIR, "milling.toml")
with open(LIMITS_FILE, "rb") as _fh:
    DRILL_SET = sorted(tomllib.load(_fh)["drill_set"]["value"])  # owner's bit set (milling.toml)
VIA_DRILL, VIA_PAD = 1.1, 2.1  # EasyContac 0.8 rivet
ANNULAR_MIN = 0.45
COPPER_MM = 0.070
EDGE_INSET = 0.6
PIECE_MIN_MM2 = 200  # F.Cu pour pieces smaller than this are dropped unless connected (strips along the edge, slivers)
BOARD_MM = 1.57
# board position of the outline's lower-left corner (KiCad coordinates, y down, mm)
ORIGIN_X, ORIGIN_Y = 60.0, 180.0
STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS"
\t\t\t\t(type "Top Silk Screen")
\t\t\t)
\t\t\t(layer "F.Paste"
\t\t\t\t(type "Top Solder Paste")
\t\t\t)
\t\t\t(layer "F.Mask"
\t\t\t\t(type "Top Solder Mask")
\t\t\t)
\t\t\t(layer "F.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness %(cu).3f)
\t\t\t)
\t\t\t(layer "dielectric 1"
\t\t\t\t(type "core")
\t\t\t\t(thickness %(core).3f)
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "B.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness %(cu).3f)
\t\t\t)
\t\t\t(layer "B.Mask"
\t\t\t\t(type "Bottom Solder Mask")
\t\t\t)
\t\t\t(layer "B.Paste"
\t\t\t\t(type "Bottom Solder Paste")
\t\t\t)
\t\t\t(layer "B.SilkS"
\t\t\t\t(type "Bottom Silk Screen")
\t\t\t)
\t\t\t(copper_finish "None")
\t\t\t(dielectric_constraints no)
\t\t)
"""


def pt(x, y):
    """Table coordinates (mm from the lower-left corner, y up) -> KiCad VECTOR2I."""
    return VECTOR2I(FromMM(ORIGIN_X + x), FromMM(ORIGIN_Y - y))


def export_netlist(sch_dir, out_xml):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", out_xml,
                    os.path.join(sch_dir, SCHEMATIC)], check=True, stdout=subprocess.DEVNULL)


def parse_netlist(path):
    root = ET.parse(path).getroot()
    comps = {}
    for c in root.find("components"):
        ref = c.get("ref")
        fpn = c.findtext("footprint") or ""
        tst = c.findtext("tstamps") or (c.find("tstamps").text if c.find("tstamps") is not None else "")
        fields = {f.get("name"): (f.text or "") for f in (c.find("fields") if c.find("fields") is not None else [])}
        comps[ref] = {"value": c.findtext("value") or "", "footprint": fpn, "uuid": tst, "fields": fields}
    nets = {}
    for n in root.find("nets"):
        nets[n.get("name")] = [(nd.get("ref"), nd.get("pin")) for nd in n.findall("node")]
    return comps, nets


def load_footprint(fpid, sch_dir):
    lib, name = fpid.split(":", 1)
    path = os.path.join(sch_dir, lib + ".pretty") if lib == "rc_power" else os.path.join(FP_DIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("footprint not found: %s" % fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


SKIP_FIELDS = ("Reference", "Value", "Footprint")


def set_fields(fp, fields):
    """Copy every symbol field of the netlist onto the footprint, hidden (schematic parity needs them)."""
    for name, text in fields.items():
        if name in SKIP_FIELDS:
            continue
        fp.SetField(name, text)
        fp.GetField(name).SetVisible(False)


def sync_fields(board_path, sch_dir=SCH_DIR):
    """Apply the symbol fields to an existing board in place. No placement, zone or routing change."""
    tmp = tempfile.mkdtemp()
    xml = os.path.join(tmp, "net.xml")
    export_netlist(sch_dir, xml)
    comps, _ = parse_netlist(xml)
    board = pcbnew.LoadBoard(board_path)
    for fp in board.GetFootprints():
        info = comps.get(fp.GetReference())
        if info:
            set_fields(fp, info["fields"])
    board.Save(board_path)
    return len(comps)


def snap_drill(d_mm):
    """Smallest size in the drill set that is >= d_mm. A hole larger than the set is returned unchanged:
    it must be a bored hole of placement.MILLED_HOLES (fit_pad)."""
    for s in DRILL_SET:
        if d_mm <= s + 0.005:
            return s
    return d_mm


def milled_hole(ref):
    """The bored hole size (mm) of a part, or None."""
    sizes = [h for r, h in placement.MILLED_HOLES if r == ref]
    return max(sizes) if sizes else None


def fit_pad(pad, ref="", lib_pad=None):
    """Snap the hole to the bit set (bored holes: placement.MILLED_HOLES) and grow the pad to keep the annular ring
    (board copy only). A hole never gets smaller than the library drill."""
    if not pad.HasHole():
        return
    ds = (lib_pad or pad).GetDrillSize()  # lib_pad: the library footprint's pad (sync_drills); a board hole may already be snapped
    bored = milled_hole(ref)
    dx, dy = snap_drill(ToMM(ds.x)), snap_drill(ToMM(ds.y))
    if bored is not None and max(dx, dy) > max(DRILL_SET) + 0.005:
        dx = dy = max(bored, dx, dy)
    if max(dx, dy) > max(DRILL_SET) + 0.005 and bored is None:
        raise RuntimeError("%s: hole %.2f mm is not in the drill set and not in MILLED_HOLES" % (ref, max(dx, dy)))
    pad.SetDrillSize(VECTOR2I(FromMM(dx), FromMM(dy)))
    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
        pad.SetSize(VECTOR2I(FromMM(max(dx, dy)), FromMM(max(dx, dy))))  # NPTH: no copper, pad = hole
        return
    sz = pad.GetSize(pcbnew.F_Cu)
    need_x, need_y = max(dx, dy) + 2 * ANNULAR_MIN, max(dx, dy) + 2 * ANNULAR_MIN
    new = VECTOR2I(FromMM(max(ToMM(sz.x), need_x)), FromMM(max(ToMM(sz.y), need_y)))
    if new.x != sz.x or new.y != sz.y:
        pad.SetSize(new)


def add_outline(board):
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(pt(0, 0))
    r.SetEnd(pt(placement.OUTLINE_W, placement.OUTLINE_H))
    r.SetLayer(pcbnew.Edge_Cuts)
    r.SetWidth(FromMM(0.05))
    r.SetFilled(False)
    board.Add(r)


def add_zone(board, net, layer, pts, connection, clearance=0.4, min_w=0.5, prio=0, name="", island_area_mm2=None):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetIsRuleArea(False)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(pt(x, y))
    z.SetLocalClearance(FromMM(clearance))
    z.SetMinThickness(FromMM(min_w))
    z.SetPadConnection(connection)
    z.SetAssignedPriority(prio)
    if island_area_mm2 is None:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    else:
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
        z.SetMinIslandArea(int(island_area_mm2 * 1e12))
    z.SetThermalReliefGap(FromMM(0.5))
    z.SetThermalReliefSpokeWidth(FromMM(0.5))
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def fill_zones(board):
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def patch_file(path):
    """Write the 2-layer stackup (copper 0.070 mm) into the saved file: pcbnew Python cannot edit it."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    stack = STACKUP % {"cu": COPPER_MM, "core": BOARD_MM - 2 * COPPER_MM}
    text = text.replace('(paper "A4")', '(paper "A3")', 1)
    if "(stackup" not in text:
        text, n = re.subn(r"(\t\(setup\n)", lambda m: m.group(1) + stack, text, count=1)
        if n != 1:
            raise RuntimeError("no (setup block in the saved board")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def add_power_zones(board, netinfo):
    """GND pours on both layers and the B.Cu bus zones of placement.BUS_ZONES (netinfo: net name -> NETINFO_ITEM)."""
    gnd = netinfo["GND"]
    w, h = placement.OUTLINE_W, placement.OUTLINE_H
    m = EDGE_INSET  # the pour stops 0.6 mm inside the outline: the fill rounding would leave 0.476 mm from the edge
    outline = [(m, m), (w - m, m), (w - m, h - m), (m, h - m)]
    # F.Cu pour: no connection to pads (THT pads are open on an unplated board); B.Cu pour: solid.
    # F.Cu islands below PIECE_MIN_MM2 are removed (the pour joins B.Cu GND only through rivet vias).
    add_zone(board, gnd, pcbnew.F_Cu, outline, pcbnew.ZONE_CONNECTION_NONE, prio=0, name="GND_F", island_area_mm2=PIECE_MIN_MM2)
    add_zone(board, gnd, pcbnew.B_Cu, outline, pcbnew.ZONE_CONNECTION_FULL, prio=0, name="GND_B")
    for i, (net, pts) in enumerate(placement.BUS_ZONES):
        add_zone(board, netinfo[net], pcbnew.B_Cu, pts, pcbnew.ZONE_CONNECTION_FULL, prio=10 + i, name="BUS_%s_%d" % (net.lstrip("/"), i))


def sync_drills(board_path):
    """Apply the drill set and the bored holes to an existing board in place, set the via drill, refill the zones.
    Parts, tracks and the via positions stay. Pads grow to keep the annular ring; the footprint library is the
    source of the minimum drill, so a hole already larger than the new size stays as it is."""
    board = pcbnew.LoadBoard(board_path)
    for fp in board.GetFootprints():
        lib_pads = list(load_footprint(fp.GetFPID().GetUniStringLibId(), SCH_DIR).Pads())  # same pad order as the board copy
        for pad, lib_pad in zip(fp.Pads(), lib_pads):
            fit_pad(pad, fp.GetReference(), lib_pad)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            t.SetDrill(FromMM(VIA_DRILL))
            t.SetWidth(FromMM(VIA_PAD))
    fill_zones(board)
    board.Save(board_path)
    patch_file(board_path)


def sync_zones(board_path):
    """Rebuild all zones of an existing board from placement.py and refill them. Parts, tracks and vias stay."""
    board = pcbnew.LoadBoard(board_path)
    old = list(board.Zones())
    netinfo = {n: board.FindNet(n) for n in {"GND"} | {n for n, _ in placement.BUS_ZONES}}
    add_power_zones(board, netinfo)
    for z in old:  # (the old zones go last: pcbnew Python loses the ZONE type after the last zone is removed)
        board.Remove(z)
    fill_zones(board)
    board.Save(board_path)
    patch_file(board_path)


def build(out_path, sch_dir=SCH_DIR):
    tmp = tempfile.mkdtemp()
    xml = os.path.join(tmp, "net.xml")
    export_netlist(sch_dir, xml)
    comps, nets = parse_netlist(xml)

    # project files next to the board: the net classes and rules of the .kicad_pro load with it
    out_dir = os.path.dirname(os.path.abspath(out_path))
    stem = os.path.splitext(os.path.basename(out_path))[0]
    for ext in (".kicad_pro", ".kicad_dru"):
        src = os.path.join(sch_dir, "rc_power_board" + ext)
        dst = os.path.join(out_dir, stem + ext)
        if os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
    board = pcbnew.BOARD()
    board.GetDesignSettings().SetBoardThickness(FromMM(BOARD_MM))
    pcbnew.SaveBoard(out_path, board)
    board = pcbnew.LoadBoard(out_path)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(FromMM(BOARD_MM))
    ds.SetAuxOrigin(pt(0, 0))
    ds.SetGridOrigin(pt(0, 0))
    add_outline(board)

    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = netinfo[name]

    missing = sorted(set(comps) - set(placement.PLACEMENT))
    if missing:
        raise RuntimeError("no placement for: %s" % ", ".join(missing))
    for ref in sorted(comps):
        info = comps[ref]
        fp = load_footprint(info["footprint"], sch_dir)
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + info["uuid"]))
        set_fields(fp, info["fields"])
        for pad in fp.Pads():
            net = pin_net.get((ref, pad.GetNumber()))
            if net is not None and pad.GetNumber() != "":
                pad.SetNet(net)
            fit_pad(pad, ref)
        x, y, rot, side = placement.PLACEMENT[ref]
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)  # Flip needs the board
        if side == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        # every symbol is in the BOM: clear the stock footprints' "exclude from BOM" (schematic parity)
        fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)
        # no silkscreen on a milled board: the reference designator goes to the fab layer (1:1 print)
        fp.Reference().SetLayer(pcbnew.F_Fab if side == "F" else pcbnew.B_Fab)

    add_power_zones(board, netinfo)
    fill_zones(board)
    board.Save(out_path)
    patch_file(out_path)
    return board


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(SCH_DIR, BOARD_FILE))
    ap.add_argument("--sch-dir", default=SCH_DIR)
    ap.add_argument("--sync-fields", action="store_true", help="only copy the symbol fields onto an existing board (in place)")
    ap.add_argument("--sync-zones", action="store_true", help="only rebuild and refill the zones of an existing board from placement.py (in place)")
    ap.add_argument("--sync-drills", action="store_true", help="only apply the drill set, bored holes and via drill to an existing board (in place) and refill the zones")
    ap.add_argument("--force", action="store_true", help="overwrite an existing board (destroys manual edits)")
    args = ap.parse_args(argv)
    if args.sync_fields:
        n = sync_fields(args.out, args.sch_dir)
        print("pcb-build: synced symbol fields of %d parts into %s" % (n, args.out))
        return 0
    if args.sync_drills:
        sync_drills(args.out)
        print("pcb-build: synced drills and vias of %s" % args.out)
        return 0
    if args.sync_zones:
        sync_zones(args.out)
        print("pcb-build: rebuilt and refilled the zones of %s" % args.out)
        return 0
    if os.path.exists(args.out) and not args.force:
        print("pcb-build: %s exists. It may hold manual edits. Use --force to overwrite." % args.out, file=sys.stderr)
        return 1
    if os.path.exists(args.out):
        os.remove(args.out)
    build(args.out, args.sch_dir)
    print("pcb-build: wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
