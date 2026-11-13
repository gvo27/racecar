"""Placement of the rev A power board. First-build data for build_pcb.py.

Coordinates are mm from the outline's lower-left corner (x to the right, y up).
rot = KiCad orientation in degrees (counter-clockwise, seen from the top) applied to the footprint
BEFORE the part is flipped to its side. Side "F" = top (THT), "B" = bottom (SMD). A part on "B" is flipped
left-right about its origin.
"""

OUTLINE_W = 66.0
OUTLINE_H = 140.0

# ref -> (x, y, rot, side)
# Layout rules (Task 7b): GND is one B.Cu pour with planned trunks (left trunk J1 -> U2, corridor U2 -> U1, both >= 6 mm).
# VBAT, +5V_CPU and +5V_SENS are planned B.Cu zones that end at their loads (peninsulas); none of them
# joins two board edges, so none cuts the GND pour. The +5V_CPU loads (J6, J7) are on the right edge next to U1.
PLACEMENT = {
    # mounting holes, 3.5 mm from the corners
    "H1": (3.5, 3.5, 0, "F"),
    "H2": (62.5, 3.5, 0, "F"),
    "H3": (3.5, 136.5, 0, "F"),
    "H4": (62.5, 136.5, 0, "F"),
    # input chain at the bottom end: J1 GND on the left (rotated 180 deg), BAT+ on the right, F1 above BAT+
    "J1": (23.7, 3.5, 0, "F"),
    "F1": (22.2, 19.5, 0, "F"),
    "C1": (38.5, 9.0, 0, "F"),
    "D1": (41.0, 12.5, 180, "B"),
    # buck modules, input end down: U2 (5 V sensors) with GND pair left and VIN pair right, U1 (5 V compute) right of it
    "U2": (14.35, 43.89, 90, "F"),
    "C4": (23.1, 34.0, 180, "B"),
    "C5": (29.5, 70.0, 90, "B"),
    "TP2": (29.5, 73.5, 0, "B"),
    "R2": (29.5, 77.0, 90, "B"),
    "D3": (29.5, 80.9, 270, "B"),
    "U1": (42.35, 43.89, 90, "F"),
    "C2": (51.0, 34.0, 180, "B"),
    "C3": (52.3, 50.0, 0, "B"),
    "TP1": (51.8, 52.8, 0, "B"),
    "R1": (52.8, 55.9, 90, "B"),
    "D2": (52.8, 61.0, 270, "B"),
    # right edge: USB power for the Pi and the ESP32, next to U1 (entry outward)
    "J6": (59.8, 56.6, 270, "F"),
    "J7": (59.8, 68.4, 270, "F"),
    # left edge: wiring hub (ESP32 signals, ESC, servo, sensors)
    "J4": (4.5, 36.0, 270, "F"),
    "J3": (3.4, 42.5, 90, "F"),
    "J5": (3.4, 56.7, 90, "F"),
    "J8": (4.5, 83.2, 270, "F"),    # turned 180 deg: SDA/SCL order matches J5 without a crossing
    "J11": (3.65, 89.8, 90, "F"),    # pin column 0.25 mm in: J11.2 reaches GND through a 1.7 mm strip west of the pads
    "C9": (13.0, 89.8, 90, "F"),
    "J9": (3.65, 98.9, 90, "F"),
    # right edge: 3.3 V connectors
    "J12": (61.1, 107.6, 90, "F"),
    "J13": (61.1, 116.6, 90, "F"),
    "J14": (61.1, 125.6, 90, "F"),
    # 3.3 V chain, top right
    "FB1": (44.0, 100.0, 180, "B"),
    "C6": (44.0, 104.0, 0, "B"),
    "C7": (48.0, 104.0, 0, "B"),
    "U3": (46.0, 110.0, 0, "B"),
    "C8": (52.0, 110.0, 0, "B"),
    "R3": (36.0, 112.0, 90, "B"),
    "D4": (36.0, 115.9, 270, "B"),
    "TP3": (40.0, 120.0, 0, "B"),
}


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# Copper buses drawn as B.Cu zones: (net name, [(x, y), ...]) in the same frame as PLACEMENT.
# Trunks of HighCurrent nets are at least 6.0 mm wide; short stubs (pad-width necks) reach one pad.
# VBAT is an "E" tree: F1.2 -> arm (y 22.4..28.4) -> prong B up to U2 VIN and prong A up to U1 VIN. Both modules sit
# with the pin row on the north edge (rot 90), so each prong ends in a pad-width neck at the VIN pads and the GND
# pads next to them (pad 7-10) reach the pour on both sides of the row.
BUS_ZONES = [
    # J1.1 -> F1.1 input
    ("/VBAT_RAW", _rect(20.9, 1.9, 27.1, 21.0)),
    # F1.2 -> arm -> prongs -> necks to the VIN pads
    ("VBAT", _rect(30.2, 15.0, 40.5, 24.5)),
    ("VBAT", _rect(16.3, 22.4, 50.6, 28.8)),            # arm
    ("VBAT", _rect(16.3, 22.4, 22.9, 41.0)),            # prong B (U2 VIN)
    ("VBAT", _rect(18.48, 40.5, 20.38, 47.4)),          # pad-width neck to U2.5/6
    ("VBAT", _rect(44.0, 22.4, 50.6, 41.0)),            # prong A (U1 VIN)
    ("VBAT", _rect(46.48, 40.5, 48.38, 47.4)),          # pad-width neck to U1.5/6
    ("VBAT", _rect(37.5, 7.9, 39.5, 13.0)),             # stub to C1
    ("VBAT", _rect(37.5, 11.3, 40.5, 15.2)),            # stub to D1
    # +5V_CPU: U1 VOUT pads -> north -> J6.1 / J7.1 and the small parts
    ("+5V_CPU", _rect(54.0, 43.0, 56.0, 57.4)),
    ("+5V_CPU", _rect(54.0, 55.6, 60.1, 57.6)),
    ("+5V_CPU", _rect(56.0, 55.6, 58.0, 69.5)),
    ("+5V_CPU", _rect(57.8, 67.0, 60.1, 69.6)),
    ("+5V_CPU", _rect(52.8, 49.4, 54.2, 50.6)),         # C3
    ("+5V_CPU", _rect(51.8, 52.2, 54.2, 53.4)),         # TP1
    ("+5V_CPU", _rect(52.2, 54.4, 54.2, 55.6)),         # R1
    # +5V_SENS: U2 VOUT pads -> trunk north -> tooth to the J8.1/J11.1 bar, branch to J9.1, C9, FB1
    ("+5V_SENS", _rect(26.1, 43.0, 28.0, 100.9)),
    ("+5V_SENS", _rect(4.0, 85.0, 27.0, 88.0)),
    ("+5V_SENS", _rect(3.5, 82.3, 5.5, 90.5)),        # J8.1 + J11.1 bar
    ("+5V_SENS", _rect(5.3, 87.5, 7.1, 99.5)),
    ("+5V_SENS", _rect(4.0, 98.1, 5.6, 99.7)),          # J9.1
    ("+5V_SENS", _rect(12.2, 87.5, 13.8, 89.9)),        # C9
    ("+5V_SENS", _rect(26.1, 99.1, 43.0, 100.9)),       # FB1
    ("+5V_SENS", _rect(27.2, 68.5, 29.8, 69.6)),        # C5
    ("+5V_SENS", _rect(27.2, 73.0, 29.5, 74.0)),        # TP2
    ("+5V_SENS", _rect(27.2, 75.6, 29.8, 76.6)),        # R2
]

# Areas where the router may not put a track or via (they would fence the GND pour): (x0, y0, x1, y1).
GND_KEEPOUTS = [
    (22.8, 28.8, 42.2, 47.0),    # pocket between the VBAT prongs
]

# Planned F.Cu jumpers on rivets (low-current signals that would cross a GND trunk): net, pad A, via A, F.Cu path, via B, pad B.
JUMPERS = [
    {"net": "/U1_PG", "pad_a": ("U1", "1"), "via_a": (40.4, 49.8),
     "stub_a": [(40.4, 43.89)],                         # B.Cu stub: pad -> waypoints -> via (keeps 0.4 mm from U1.2)
     "path": [(40.4, 49.8), (8.0, 49.8), (8.0, 52.1), (3.4, 52.1)],
     "via_b": (3.4, 52.1), "pad_b": ("J5", "1")},
]

# Rivet vias that tie the F.Cu GND pour to the B.Cu GND zone: (x, y, net). Each one is a rivet; the count goes in the report.
STITCH_VIAS = []

# Holes larger than the largest drill (2.0 mm) that the mill bores with the 3.175 mm end mill: (ref, hole mm).
# A bored hole is at least milled_hole_min (3.3 mm, milling.toml); holes between 2.0 and 3.3 mm cannot be made.
# H1 to H4: M3 clearance. J1: 12 AWG wire pads (pad 4.4 mm, ring 0.5 mm). F1: locating peg of the FLR 178.6165 holder;
# the library hole is 2.4 mm, the peg size is not confirmed (datasheet not reachable), so it is a loose 3.4 mm locator hole.
MILLED_HOLES = [
    ("J1", 3.4),
    ("H1", 3.4), ("H2", 3.4), ("H3", 3.4), ("H4", 3.4),
    ("F1", 3.4),
]

# ---- lab frame (Task 9) ----------------------------------------------------------------------------------------
# Stock and dowels of the lab's Fusion 360 template (docs/schematics/example/README.md; milling.toml [stock], [dowel]).
# Stock coordinates: origin = stock lower-left corner, x along the long side (152.4 mm), y along the short side.
STOCK = (152.4, 101.6)
DOWEL_DIA = 4.191
DOWELS = [(3.2766, 3.81), (149.1234, 3.81)]

# The board is turned 90 degrees counter-clockwise (top view) and centered on the stock: the board's long side (140 mm)
# runs along stock x, with 6.2 mm at each end and 17.8 mm at each long side. The board's +y end (top, J14 side) then
# points to stock -x (dowel 1) and the board's +x side points to stock +y. Export transform only: the KiCad board
# does not move. The dowels sit outside the board, 14 mm from the nearest outline point.
MARGIN_X = (STOCK[0] - OUTLINE_H) / 2.0
MARGIN_Y = (STOCK[1] - OUTLINE_W) / 2.0


def board_to_stock(bx, by):
    """Board table coordinates (mm from the outline's lower-left corner, y up) -> stock coordinates."""
    return MARGIN_X + (OUTLINE_H - by), MARGIN_Y + bx


def stock_to_board(sx, sy):
    return sy - MARGIN_Y, OUTLINE_H - (sx - MARGIN_X)


def board_to_lab(bx, by):
    """Board table coordinates -> lab frame: origin = dowel 1 center (the Fusion Setup B WCS), x along the stock long side."""
    sx, sy = board_to_stock(bx, by)
    return sx - DOWELS[0][0], sy - DOWELS[0][1]


DOWELS_LAB = [(round(x - DOWELS[0][0], 4), round(y - DOWELS[0][1], 4)) for x, y in DOWELS]
