"""Route rc_power_board.kicad_pcb with Freerouting (Specctra DSN/SES). Make target: pcb-route.

Two steps, because pcbnew runs in the KiCad image and Freerouting in its own image (make runs both):
  route_pcb.py dsn <board> --dsn <out.dsn>          work copy -> DSN (F.Cu not routable; GND/VBAT nets and the B.Cu
                                                    bus zones are obstacles, they are not autorouted)
  route_pcb.py ses <board> --ses <in.ses> [--out <board>]   import SES, add stitching vias, refill zones, save
The board is routed from scratch: existing tracks and vias are removed (use --keep to refuse instead).
"""
import argparse
import os
import re
import sys

import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pcb  # noqa: E402
import placement  # noqa: E402

NOT_ROUTED = ("GND", "VBAT", "/VBAT_RAW", "+5V_CPU", "+5V_SENS", "/U1_PG")  # planned zones, the GND pour and planned jumpers (placement.py)
VIA_DRILL, VIA_PAD = 1.2, 2.1
EDGE_BAND = float(os.environ.get("ROUTE_EDGE_BAND", "2.0"))
ROUTER_CLEARANCE_UM = 430  # board clearance is 0.4 mm; the router rounds, so give it 0.03 mm extra


def clear_copper(board):
    for t in list(board.GetTracks()):
        board.Remove(t)


def box_pts(bb, margin_mm):
    m = FromMM(margin_mm)
    return [VECTOR2I(bb.GetLeft() - m, bb.GetTop() - m), VECTOR2I(bb.GetRight() + m, bb.GetTop() - m),
            VECTOR2I(bb.GetRight() + m, bb.GetBottom() + m), VECTOR2I(bb.GetLeft() - m, bb.GetBottom() + m)]


def tab(pts):
    """Table coordinates (mm) -> KiCad points."""
    return [build_pcb.pt(x, y) for x, y in pts]


def prepare(board_path, dsn_path, allow_vias=False):
    work = pcbnew.LoadBoard(board_path)
    for fp in work.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() in NOT_ROUTED:
                p.SetNetCode(0)
    # No tracks on F.Cu without --allow-vias. With it: F.Cu tracks only where they do not touch a THT pad
    # (holes are not plated, the joint is on B.Cu), and no via inside any footprint courtyard (a rivet needs both sides).
    w, h = placement.OUTLINE_W, placement.OUTLINE_H
    blocks = []
    if not allow_vias:
        blocks.append((pcbnew.F_Cu, tab([(0, 0), (w, 0), (w, h), (0, h)]), True, False))
    else:
        for fp in work.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    bb = pad.GetBoundingBox()
                    blocks.append((pcbnew.F_Cu, box_pts(bb, 0.0), True, True))
            fp.BuildCourtyardCaches()
            cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
            if cy.OutlineCount():
                blocks.append((pcbnew.F_Cu, box_pts(cy.BBox(), 0.0), False, True))
                blocks.append((pcbnew.B_Cu, box_pts(cy.BBox(), 0.0), False, True))
    # the router knows no copper-to-edge clearance and would run tracks between the edge and the connector pads, which
    # blocks the GND ring that joins the GND pads: keep tracks out of a band along the outline
    e = EDGE_BAND
    if e > 0:
        for rect in ([(0, 0), (w, 0), (w, e), (0, e)], [(0, h - e), (w, h - e), (w, h), (0, h)],
                     [(0, 0), (e, 0), (e, h), (0, h)], [(w - e, 0), (w, 0), (w, h), (w - e, h)]):
            blocks.append((pcbnew.B_Cu, tab(rect), True, True))
            if allow_vias:
                blocks.append((pcbnew.F_Cu, tab(rect), True, True))
    for layer, pts, no_tracks, no_vias in blocks:
        z = pcbnew.ZONE(work)
        z.SetIsRuleArea(True)
        z.SetLayer(layer)
        z.SetDoNotAllowTracks(no_tracks)
        z.SetDoNotAllowVias(no_vias)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
        ol = z.Outline()
        ol.NewOutline()
        for q in pts:
            ol.Append(q)
        work.Add(z)
    # bus zones are obstacles for the router
    for _, pts in placement.BUS_ZONES:
        z = pcbnew.ZONE(work)
        z.SetIsRuleArea(True)
        z.SetLayer(pcbnew.B_Cu)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in pts:
            ol.Append(build_pcb.pt(x, y))
        work.Add(z)
    # GND trunks: no tracks or vias, so that no signal fences the pour (Task 7b)
    for x0, y0, x1, y1 in placement.GND_KEEPOUTS:
        z = pcbnew.ZONE(work)
        z.SetIsRuleArea(True)
        z.SetLayer(pcbnew.B_Cu)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
        ol = z.Outline()
        ol.NewOutline()
        for q in tab([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
            ol.Append(q)
        work.Add(z)
    # planned jumpers: no router track on F.Cu along the path, no track or via near a rivet
    def keepout(layer, x0, y0, x1, y1):
        z = pcbnew.ZONE(work)
        z.SetIsRuleArea(True)
        z.SetLayer(layer)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
        ol = z.Outline()
        ol.NewOutline()
        for q in tab([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]):
            ol.Append(q)
        work.Add(z)

    for j in placement.JUMPERS:
        m = 1.2
        for (ax, ay), (bx, by) in zip(j["path"], j["path"][1:]):
            keepout(pcbnew.F_Cu, min(ax, bx) - m, min(ay, by) - m, max(ax, bx) + m, max(ay, by) + m)
        for vx, vy in (j["via_a"], j["via_b"]):
            for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                keepout(layer, vx - 2.4, vy - 2.4, vx + 2.4, vy + 2.4)
    clear_copper(work)
    # (the copper zones go last: pcbnew Python loses the ZONE type after the last zone is removed)
    for z in list(work.Zones()):
        if not z.GetIsRuleArea():
            work.Remove(z)
    work.BuildListOfNets()
    if not pcbnew.ExportSpecctraDSN(work, dsn_path):
        raise RuntimeError("DSN export failed")
    with open(dsn_path, encoding="utf-8") as fh:
        text = fh.read()
    text, n = re.subn(r"\(clearance 400\)", "(clearance %d)" % ROUTER_CLEARANCE_UM, text)
    if n == 0:
        raise RuntimeError("no clearance rule found in the DSN")
    with open(dsn_path, "w", encoding="utf-8") as fh:
        fh.write(text)


def widen_tracks(board):
    """The router narrows tracks near pads. Set each track back to its net-class width where that keeps 0.4 mm
    clearance to other-net copper on its layer; a track that does not fit stays as routed (never below 0.5 mm)."""
    ns = board.GetDesignSettings().m_NetSettings
    clr = FromMM(0.4 + 0.005)
    clr_u3 = FromMM(0.3 + 0.005)  # rule U3_fine (rc_power_board.kicad_dru)
    items = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    for layer in items:
        for t in board.GetTracks():
            if t.IsOnLayer(layer):
                items[layer].append((t, t.GetNetCode(), t.GetEffectiveShape(layer)))
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(layer) and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    items[layer].append((p, p.GetNetCode(), p.GetEffectiveShape(layer)))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            continue
        want = ns.GetEffectiveNetClass(t.GetNetname()).GetTrackWidth()
        old = t.GetWidth()
        if old >= want:
            continue
        t.SetWidth(want)
        shape = t.GetEffectiveShape(t.GetLayer())
        box = shape.BBox().GetInflated(clr)
        for other, net, osh in items[t.GetLayer()]:
            if other is t or (net == t.GetNetCode() and net != 0):
                continue
            c = clr_u3 if other.Type() == pcbnew.PCB_PAD_T and other.GetParentFootprint().GetReference() == "U3" else clr
            if box.Intersects(osh.BBox().GetInflated(c)) and shape.Collide(osh, c):
                t.SetWidth(old)
                break


def add_jumpers(board):
    """Planned F.Cu jumpers (placement.JUMPERS): B.Cu stub from pad A to a rivet, F.Cu track, rivet, B.Cu stub to pad B."""
    def pad_pos(ref, num):
        for p in board.FindFootprintByReference(ref).Pads():
            if p.GetNumber() == num:
                return p.GetPosition()
        raise RuntimeError("no pad %s.%s" % (ref, num))

    def track(a, b, layer, net, width=0.5):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(a)
        t.SetEnd(b)
        t.SetLayer(layer)
        t.SetWidth(FromMM(width))
        t.SetNet(net)
        board.Add(t)

    n = 0
    for j in placement.JUMPERS:
        net = board.FindNet(j["net"])
        va, vb = build_pcb.pt(*j["via_a"]), build_pcb.pt(*j["via_b"])
        chain = [pad_pos(*j["pad_a"])] + [build_pcb.pt(*q) for q in j.get("stub_a", [])] + [va]
        for a, b in zip(chain, chain[1:]):
            track(a, b, pcbnew.B_Cu, net)
        track(vb, pad_pos(*j["pad_b"]), pcbnew.B_Cu, net)
        pts = [build_pcb.pt(*p) for p in j["path"]]
        for a, b in zip(pts, pts[1:]):
            track(a, b, pcbnew.F_Cu, net)
        for v in (va, vb):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(v)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetDrill(FromMM(VIA_DRILL))
            via.SetWidth(FromMM(VIA_PAD))
            via.SetNet(net)
            board.Add(via)
            n += 1
    return n


def drop_dangling_vias(board):
    """Remove router vias that join only one layer (a rivet that connects nothing on one side)."""
    removed = 0
    for v in [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]:
        vs = v.GetEffectiveShape(pcbnew.F_Cu)
        ok = {pcbnew.F_Cu: False, pcbnew.B_Cu: False}
        for layer in ok:
            for t in board.GetTracks():
                if t is v or t.Type() == pcbnew.PCB_VIA_T or not t.IsOnLayer(layer) or t.GetNetCode() != v.GetNetCode():
                    continue
                if t.GetEffectiveShape(layer).Collide(vs, 0):
                    ok[layer] = True
                    break
        if v.GetNetname() == "GND":
            continue
        if not (ok[pcbnew.F_Cu] and ok[pcbnew.B_Cu]):
            board.Remove(v)
            removed += 1
    return removed


def add_stitching_vias(board):
    """Tie each F.Cu GND pour piece (>= PIECE_MIN_MM2) to the B.Cu GND zone with one rivet via, in the freest spot.

    A spot must lie inside both fills, outside every footprint courtyard (a rivet needs both sides), 0.4 mm from
    every other-net copper on both layers, 0.5 mm from the edge, 0.25 mm hole clearance. Best spot = most room.
    """
    gnd = board.FindNet("GND")
    zf = [z for z in board.Zones() if z.GetZoneName() == "GND_F"][0]
    zb = [z for z in board.Zones() if z.GetZoneName() == "GND_B"][0]
    fill_f = zf.GetFilledPolysList(pcbnew.F_Cu)
    fill_b = zb.GetFilledPolysList(pcbnew.B_Cu)
    others = []  # (bbox, shape) of copper that is not GND, both layers, plus holes
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        for t in board.GetTracks():
            if t.IsOnLayer(layer) and t.GetNetname() != "GND":
                others.append(t.GetEffectiveShape(layer))
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(layer) and p.GetNetname() != "GND" and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    others.append(p.GetEffectiveShape(layer))
    holes = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.HasHole():
                holes.append(p.GetEffectiveHoleShape())
    courts = []
    for fp in board.GetFootprints():
        fp.BuildCourtyardCaches()
        cy = fp.GetCourtyard(pcbnew.F_CrtYd if fp.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd)
        if cy.OutlineCount():
            courts.append(cy)
    edges = [d.GetEffectiveShape() for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
    keep = FromMM(0.4 + 0.05)
    reach = FromMM(4.5)
    others = [(sh, sh.BBox()) for sh in others]
    n = 0
    step = FromMM(1.5)
    for i in range(fill_f.OutlineCount()):
        piece = pcbnew.SHAPE_POLY_SET()
        piece.AddOutline(fill_f.COutline(i))
        for h in range(fill_f.HoleCount(i)):
            piece.AddHole(fill_f.CHole(i, h))
        if abs(piece.Area()) / 1e12 < build_pcb.PIECE_MIN_MM2:
            continue
        bb = piece.BBox()
        best = None
        y = bb.GetTop()
        while y < bb.GetBottom():
            x = bb.GetLeft()
            while x < bb.GetRight():
                pos = VECTOR2I(x, y)
                x += step
                near = [sh for sh, b in others if b.GetInflated(reach).Contains(pos)]
                vs = pcbnew.SHAPE_CIRCLE(pos, FromMM(VIA_PAD / 2.0))
                if any(sh.Collide(vs, keep) for sh in near):
                    continue
                if not (piece.Contains(pos) and fill_b.Contains(pos)):
                    continue
                if any(c.Contains(pos) or c.Collide(vs, 0) for c in courts):
                    continue
                if any(e.Collide(vs, FromMM(0.6)) for e in edges):
                    continue
                if any(hs.Collide(vs, FromMM(0.3)) for hs in holes):
                    continue
                # room = distance to the nearest other copper (coarse, 0.25 mm steps up to 4 mm)
                room = keep
                for k in range(1, 16):
                    c = keep + FromMM(0.25 * k)
                    if any(sh.Collide(vs, c) for sh in near):
                        break
                    room = c
                if best is None or room > best[0]:
                    best = (room, pos)
            y += step
        if best is None:
            raise RuntimeError("no free spot for a stitching via in the F.Cu GND piece %d (%.0f mm2, x %.1f..%.1f, y %.1f..%.1f)" % (i, abs(piece.Area()) / 1e12, ToMM(bb.GetLeft()) - build_pcb.ORIGIN_X, ToMM(bb.GetRight()) - build_pcb.ORIGIN_X, build_pcb.ORIGIN_Y - ToMM(bb.GetBottom()), build_pcb.ORIGIN_Y - ToMM(bb.GetTop())))
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(best[1])
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetDrill(FromMM(VIA_DRILL))
        v.SetWidth(FromMM(VIA_PAD))
        v.SetNet(gnd)
        board.Add(v)
        n += 1
        zf.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)  # the pour is connected now: drop every island
        print("route: stitching via at (%.1f, %.1f) mm" % (ToMM(best[1].x) - build_pcb.ORIGIN_X, build_pcb.ORIGIN_Y - ToMM(best[1].y)))
    return n


def finish(board_path, ses_path, out_path):
    board = pcbnew.LoadBoard(board_path)
    clear_copper(board)
    if not pcbnew.ImportSpecctraSES(board, ses_path):
        raise RuntimeError("SES import failed")
    n_jump = add_jumpers(board)
    dropped = drop_dangling_vias(board)
    widen_tracks(board)
    build_pcb.fill_zones(board)
    n_stitch = add_stitching_vias(board)
    build_pcb.fill_zones(board)
    board.Save(out_path)
    nvia = sum(1 for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T)
    ntrk = sum(1 for t in board.GetTracks() if t.Type() != pcbnew.PCB_VIA_T)
    print("route: %d tracks, %d rivet vias (%d stitching, %d dangling router vias removed)" % (ntrk, nvia, n_stitch, dropped))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dsn")
    d.add_argument("board")
    d.add_argument("--dsn", required=True)
    d.add_argument("--allow-vias", action="store_true", help="let the router place rivet vias")
    s = sub.add_parser("ses")
    s.add_argument("board")
    s.add_argument("--ses", required=True)
    s.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "dsn":
        prepare(a.board, a.dsn, a.allow_vias)
    else:
        finish(a.board, a.ses, a.out or a.board)
    return 0


if __name__ == "__main__":
    sys.exit(main())
