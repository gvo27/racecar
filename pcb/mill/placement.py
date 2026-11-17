"""Placement of the mill prototype (pcb/mill). It starts from the rev A placement (pcb/fabhouse) and changes it.

Same parts and footprints as rev A, without the parts in `[parts] exclude` of the design rules (LEDs and their
resistors). The SMD parts are spread to the component gap of the design rules. Coordinates: mm from the outline's
lower-left corner (x to the right, y up). pcb/tools/placement.py loads this file.
"""
import os

import placement as _loader  # pcb/tools/placement.py is being imported: only load_board_file is used

_base = _loader.load_board_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fabhouse", "placement.py"))
globals().update(_base)


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


_EXCLUDED = ("D2", "D3", "D4", "R1", "R2", "R3")
PLACEMENT = {ref: pos for ref, pos in _base["PLACEMENT"].items() if ref not in _EXCLUDED}

# ---- part moves ------------------------------------------------------------------------------------------------
# Rule for this board: pads of two different parts on different nets are at least component_gap apart (design rules).
PLACEMENT.update({
    # J11 and J9 0.1 mm further in: the GND strip west of the pads keeps the Power5A width with the larger clearance
    "J11": (3.75, 89.8, 90, "F"),
    "J9": (3.75, 98.9, 90, "F"),
    # test points sit on their rail trunks (no stub, no neighbour pad)
    "TP1": (55.0, 53.0, 0, "B"),
    # C3 0.3 mm north: 2.0 mm from the U1 GND pads
    "C3": (52.3, 50.3, 0, "B"),
    "TP2": (27.05, 76.0, 0, "B"),
    # 3.3 V chain: FB1 -> /LDO_IN bar (y 99 to 101) with C6 and C7 below it and U3 above it -> +3V3_SENS bar to the
    # right edge connectors. Each capacitor has pad 1 on its rail and pad 2 in the GND pour.
    "C6": (47.8, 98.55, 270, "B"),
    "C7": (51.3, 98.55, 270, "B"),
    "U3": (50.0, 103.8, 90, "B"),
    "C8": (54.0, 105.9, 90, "B"),
    "TP3": (57.0, 112.0, 0, "B"),
})

# ---- zones ------------------------------------------------------------------------------------------------------
# Two zones of different nets keep the board clearance (0.5 mm) from each other, also at U3. Only a zone and a U3 pad can be
# 0.34 mm apart. So the fine zones start inside their pad and stay 0.5 mm from the fine zone of the next net.
_FINE = {"clearance": 0.34, "min_w": 0.5}   # zones at U3: the [[exception]] clearance of the design rules
_DROP = {"TP1", "R1", "TP2", "R2", "C3", "C5"}  # stubs of rev A that this board does not have or draws again


def _keep(row):
    """Rev A zone rows without the stubs to the parts that moved or are not on this board."""
    net, pts = row[0], row[1]
    x0, y0, x1, y1 = pts[0][0], pts[0][1], pts[2][0], pts[2][1]
    stubs = {("+5V_CPU", 52.8, 49.4): "C3", ("+5V_CPU", 51.8, 52.2): "TP1", ("+5V_CPU", 52.2, 54.4): "R1",
             ("+5V_SENS", 27.2, 68.5): "C5", ("+5V_SENS", 27.2, 73.0): "TP2", ("+5V_SENS", 27.2, 75.6): "R2",
             ("+5V_SENS", 26.1, 43.0): "trunk",
             ("+5V_SENS", 3.5, 82.3): "J11", ("+5V_SENS", 5.3, 87.5): "J9", ("+5V_SENS", 4.0, 98.1): "J9"}
    return stubs.get((net, x0, y0)) is None


BUS_ZONES = [row for row in _base["BUS_ZONES"] if _keep(row)] + [
    # +5V_SENS trunk: ends 0.1 mm inside the FB1 bar (y 99.1 to 100.9). The rev A trunk overlaps the whole bar end, and
    # the fill then leaves fragments of 0.003 mm2 there (MILL-ISLAND)
    ("+5V_SENS", _rect(26.1, 43.0, 28.0, 99.2)),
    # capacitor stubs: as tall as the pad plus 0.15 mm, so the stub has the Default width
    ("+5V_CPU", _rect(52.75, 49.5, 54.2, 51.1)),         # C3
    ("+5V_SENS", _rect(27.2, 68.25, 30.25, 69.85)),      # C5
    # J8.1 + J11.1 bar and the J9.1 branch, moved with J11 and J9
    ("+5V_SENS", _rect(3.5, 82.3, 5.6, 90.5)),
    ("+5V_SENS", _rect(5.3, 87.5, 7.1, 99.5)),
    ("+5V_SENS", _rect(4.0, 98.1, 5.7, 99.7)),
    # /LDO_IN: bar from FB1.2 to C6.1, C7.1 and the two prongs to U3.1 and U3.3 (pad wide)
    ("/LDO_IN", _rect(44.62, 99.0, 52.2, 101.0)),
    ("/LDO_IN", _rect(48.75, 100.8, 49.35, 102.4), _FINE),
    ("/LDO_IN", _rect(50.65, 100.8, 51.25, 102.4), _FINE),
    # GND of U3.2: strip under the body, out between pad 4 and pad 5, into the pour north of U3
    ("GND", _rect(49.7, 102.9, 50.3, 106.3), _FINE),
    ("GND", _rect(49.0, 105.6, 51.0, 107.65), _FINE),   # wide end of the strip in the pour: no thin corner pieces
    # +3V3_SENS: U3.5 -> bar east (C8.1 on it) -> bar north along x 56 to 58 (TP3 on it) -> teeth to J12.1, J13.1, J14.1
    ("+3V3_SENS", _rect(50.85, 104.28, 58.0, 105.6), _FINE),
    ("+3V3_SENS", _rect(56.0, 104.28, 58.0, 126.55)),
    ("+3V3_SENS", _rect(57.0, 106.65, 61.6, 108.55)),
    ("+3V3_SENS", _rect(57.0, 115.65, 61.6, 117.55)),
    ("+3V3_SENS", _rect(57.0, 124.65, 61.6, 126.55)),
]

# Copper width rows: the rev A rows, plus the 3.3 V chain (planned zones on this board).
PATH_ROWS = list(_base["PATH_ROWS"]) + [
    ("+3V3_SENS", "+3V3_SENS bar - J12/J13/J14", ["C8.1", "TP3.1", "J12.1", "J13.1", "J14.1"], 1.2),
    ("/LDO_IN", "LDO_IN bar FB1 - C6/C7", ["FB1.2", "C6.1", "C7.1"], "Default"),
]

# U1_PG jumper: the B.Cu stub and its rivet are 0.5 mm further west than on rev A. The stub then has the Default width
# (1.5 mm) with the board clearance to U1.2. Rev A: x = 40.4, 0.5 mm track.
JUMPERS = [
    {"net": "/U1_PG", "pad_a": ("U1", "1"), "via_a": (39.9, 49.8),
     "stub_a": [(39.9, 43.89)],
     "path": [(39.9, 49.8), (8.0, 49.8), (8.0, 52.1), (3.4, 52.1)],
     "via_b": (3.4, 52.1), "pad_b": ("J5", "1")},
]
