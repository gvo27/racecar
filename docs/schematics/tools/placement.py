"""Placement of the rev A power board. First-build data for build_pcb.py.

Coordinates are mm from the outline's lower-left corner (x to the right, y up).
rot = KiCad orientation in degrees (counter-clockwise, seen from the top) applied to the footprint
BEFORE the part is flipped to its side. Side "F" = top (THT), "B" = bottom (SMD). A part on "B" is flipped
left-right about its origin.
"""

OUTLINE_W = 66.0
OUTLINE_H = 140.0

# ref -> (x, y, rot, side)
PLACEMENT = {
    # mounting holes, 3.5 mm from the corners
    "H1": (3.5, 3.5, 0, "F"),
    "H2": (62.5, 3.5, 0, "F"),
    "H3": (3.5, 136.5, 0, "F"),
    "H4": (62.5, 136.5, 0, "F"),
    # input chain at the bottom end
    "J1": (16.0, 3.5, 0, "F"),
    "F1": (14.5, 19.5, 0, "F"),
    "C1": (35.0, 20.0, 0, "F"),
    "D1": (34.0, 15.5, 180, "B"),
    # buck modules, input end down: U2 (5 V sensors) left of the VBAT trunk, U1 (5 V compute) right of it
    "U2": (22.5, 53.0, 90, "F"),
    "C4": (31.5, 36.0, 90, "B"),
    "C5": (25.0, 72.5, 0, "B"),
    "R2": (36.0, 62.0, 90, "B"),
    "D3": (36.0, 65.9, 270, "B"),
    "TP2": (36.0, 70.0, 0, "B"),
    "U1": (47.5, 23.9, 180, "F"),
    "C2": (39.5, 33.0, 90, "B"),
    "C3": (50.5, 41.0, 90, "B"),
    "TP1": (44.0, 41.0, 0, "B"),
    "R1": (56.0, 44.0, 90, "B"),
    "D2": (56.0, 47.9, 270, "B"),
    # left edge: all wiring hub (USB power, ESP32 signals, ESC, servo, sensors), pin 1 at the bottom
    "J6": (6.25, 33.1, 90, "F"),
    "J7": (6.25, 44.9, 90, "F"),
    "J5": (3.4, 56.7, 90, "F"),
    "J4": (4.5, 80.8, 270, "F"),
    "J3": (3.4, 87.4, 90, "F"),
    "J8": (3.4, 99.0, 90, "F"),
    "J11": (3.4, 113.1, 90, "F"),
    "C9": (13.0, 113.1, 90, "F"),
    "J9": (3.4, 122.2, 90, "F"),
    # right edge: 3.3 V connectors
    "J12": (61.1, 107.6, 90, "F"),
    "J13": (61.1, 116.6, 90, "F"),
    "J14": (61.1, 125.6, 90, "F"),
    # 3.3 V chain, top right
    "FB1": (44.0, 100.0, 0, "B"),
    "C6": (44.0, 104.0, 0, "B"),
    "C7": (48.0, 104.0, 0, "B"),
    "U3": (46.0, 110.0, 0, "B"),
    "C8": (52.0, 110.0, 0, "B"),
    "R3": (36.0, 112.0, 90, "B"),
    "D4": (36.0, 115.9, 270, "B"),
    "TP3": (40.0, 120.0, 0, "B"),
}

# Copper buses drawn as B.Cu zones: (net name, [(x, y), ...]) in the same frame as PLACEMENT.
# Trunks are at least 6.0 mm wide (HighCurrent class). Necks at pad rows are narrower (header pitch).
def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


BUS_ZONES = [
    ("/VBAT_RAW", _rect(12.8, 2.0, 19.3, 21.0)),        # J1 -> F1
    ("VBAT", _rect(22.7, 15.0, 29.9, 38.8)),            # trunk F1 -> U2 VIN pads
    ("VBAT", _rect(29.8, 26.0, 42.0, 32.0)),            # band to U1
    ("VBAT", _rect(41.9, 27.8, 48.5, 30.15)),           # neck to the U1 VIN row
    ("VBAT", _rect(29.8, 18.8, 35.8, 21.2)),            # stub to C1
    ("VBAT", _rect(29.8, 14.3, 31.9, 16.7)),            # stub to D1
    ("VBAT", _rect(29.8, 34.3, 31.6, 35.8)),            # stub to C4
]

# Rivet vias that tie the F.Cu GND pour to the B.Cu GND zone: (x, y, net). Each one is a rivet; the count goes in the report.
STITCH_VIAS = []

# Holes larger than the drill set that the mill cuts with an end mill: (ref, hole mm).
MILLED_HOLES = [
    ("J1", 3.0),
    ("H1", 3.2), ("H2", 3.2), ("H3", 3.2), ("H4", 3.2),
    ("F1", 2.4),
]
