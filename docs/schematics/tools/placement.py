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
    "J1": (24.8, 3.5, 180, "F"),
    "F1": (23.5, 19.5, 0, "F"),
    "C1": (39.5, 8.5, 0, "F"),
    "D1": (34.0, 11.0, 180, "B"),
    # buck modules, input end down: U2 (5 V sensors) with GND pair left and VIN pair right, U1 (5 V compute) right of it
    "U2": (22.5, 53.0, 90, "F"),
    "C4": (31.0, 36.0, 90, "B"),
    "C5": (29.5, 70.0, 90, "B"),
    "TP2": (29.5, 73.5, 0, "B"),
    "R2": (29.5, 77.0, 90, "B"),
    "D3": (29.5, 80.9, 270, "B"),
    "U1": (47.5, 23.9, 180, "F"),
    "C2": (39.5, 33.0, 90, "B"),
    "C3": (50.5, 41.0, 90, "B"),
    "TP1": (44.5, 40.5, 0, "B"),
    "R1": (53.5, 41.5, 90, "B"),
    "D2": (53.5, 45.4, 270, "B"),
    # right edge: USB power for the Pi and the ESP32, next to U1 (entry outward)
    "J6": (59.8, 36.6, 270, "F"),
    "J7": (59.8, 48.4, 270, "F"),
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
# Trunks of HighCurrent nets are at least 6.0 mm wide; short stubs reach one pad.
BUS_ZONES = [
    # J1.1 -> F1 input
    ("/VBAT_RAW", _rect(22.3, 1.9, 28.5, 21.0)),
    # F1 output -> trunk -> band to U1 and trunk to U2 VIN
    ("VBAT", _rect(31.5, 15.0, 41.0, 24.5)),
    ("VBAT", _rect(22.65, 24.4, 42.2, 30.4)),
    ("VBAT", _rect(22.65, 24.4, 28.9, 38.5)),
    ("VBAT", _rect(41.8, 28.05, 47.6, 30.4)),          # pad-width neck to the U1 VIN row
    ("VBAT", _rect(31.0, 11.2, 32.7, 15.2)),            # stub to D1
    ("VBAT", _rect(38.3, 7.5, 40.7, 15.1)),             # stub to C1
    ("VBAT", _rect(38.8, 30.0, 40.2, 31.7)),            # stub to C2
    ("VBAT", _rect(28.8, 34.5, 31.3, 35.6)),            # stub to C4
    # +5V_CPU: U1 VOUT row -> J6.1 / J7.1 and the small parts above the trunk
    ("+5V_CPU", _rect(43.9, 35.5, 48.6, 37.7)),
    ("+5V_CPU", _rect(48.0, 35.4, 60.0, 37.8)),
    ("+5V_CPU", _rect(56.2, 35.4, 57.9, 49.5)),
    ("+5V_CPU", _rect(57.8, 47.3, 59.9, 49.4)),
    ("+5V_CPU", _rect(49.9, 37.5, 51.1, 40.3)),         # C3
    ("+5V_CPU", _rect(43.9, 37.5, 45.1, 40.3)),         # TP1
    ("+5V_CPU", _rect(52.9, 37.5, 54.1, 41.0)),         # R1
    # +5V_SENS: U2 VOUT pair -> trunk north -> tooth to the J8.1/J11.1 bar, branch to J9.1, C9, FB1
    ("+5V_SENS", _rect(23.0, 66.8, 27.3, 69.6)),
    ("+5V_SENS", _rect(23.0, 66.8, 27.3, 101.0)),
    ("+5V_SENS", _rect(4.0, 85.0, 23.2, 88.0)),
    ("+5V_SENS", _rect(3.5, 82.3, 5.5, 90.5)),        # J8.1 + J11.1 bar
    ("+5V_SENS", _rect(5.3, 87.5, 7.1, 99.5)),
    ("+5V_SENS", _rect(4.0, 98.1, 5.6, 99.7)),          # J9.1
    ("+5V_SENS", _rect(12.2, 87.5, 13.8, 89.9)),        # C9
    ("+5V_SENS", _rect(27.2, 99.1, 43.0, 100.9)),       # FB1
    ("+5V_SENS", _rect(27.2, 68.5, 29.8, 69.6)),        # C5
    ("+5V_SENS", _rect(27.2, 73.0, 29.5, 74.0)),        # TP2
    ("+5V_SENS", _rect(27.2, 75.6, 29.8, 76.6)),        # R2
]

# Areas where the router may not put a track or via (they would fence the GND trunks): (x0, y0, x1, y1).
GND_KEEPOUTS = [
    (10.0, 3.0, 44.0, 53.0),     # left trunk and the corridor from U2 to U1
    (48.5, 22.0, 65.0, 35.2),    # channel right of U1 to J6.2
]

# Planned F.Cu jumpers on rivets (low-current signals that would cross a GND trunk): net, pad A, via A, F.Cu path, via B, pad B.
JUMPERS = [
    {"net": "/U1_PG", "pad_a": ("U1", "1"), "via_a": (52.0, 23.9),
     "path": [(52.0, 23.9), (52.0, 40.6), (9.5, 40.6), (9.5, 52.1), (3.4, 52.1)],
     "via_b": (3.4, 52.1), "pad_b": ("J5", "1")},
]

# Rivet vias that tie the F.Cu GND pour to the B.Cu GND zone: (x, y, net). Each one is a rivet; the count goes in the report.
STITCH_VIAS = []

# Holes larger than the drill set that the mill cuts with an end mill: (ref, hole mm).
MILLED_HOLES = [
    ("J1", 3.0),
    ("H1", 3.2), ("H2", 3.2), ("H3", 3.2), ("H4", 3.2),
    ("F1", 2.4),
]
