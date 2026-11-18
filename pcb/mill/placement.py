"""Placement of the mill prototype (pcb/mill). It starts from the rev1 placement (placement.py of the base board, paths.base_board_dir()) and changes it.

Differences from rev1: no LEDs and LED resistors (`[parts] exclude` of the design rules). C2 to C8 are through-hole
capacitors with 5.0 mm lead pitch on the top side (`[parts.footprint]`). The 3.3 V nets are planned zones. Pads of
two different parts on different nets are at least component_gap apart. Coordinates: mm from the outline's lower-left
corner (x to the right, y up). pcb/libraries/placement.py loads this file.

Through-hole capacitor (C_Disc, P5.00mm): the position is pad 1. Pad 2 is 5.0 mm to the east (rot 0), north (rot 90),
west (rot 180) or south (rot 270).
"""
import os

import placement as _loader  # pcb/libraries/placement.py is being imported: only load_board_file is used

import paths as _paths  # noqa: E402
_base = _loader.load_board_file(os.path.join(_paths.base_board_dir(), "placement.py"))
globals().update(_base)


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


_EXCLUDED = ("D2", "D3", "D4", "R1", "R2", "R3")
PLACEMENT = {ref: pos for ref, pos in _base["PLACEMENT"].items() if ref not in _EXCLUDED}

# ---- part moves ------------------------------------------------------------------------------------------------
PLACEMENT.update({
    # J11 and J9 further in: the planned GND strip west of the pads has the Power5A width (Mapper return current)
    "J11": (4.3, 89.8, 90, "F"),
    "J9": (4.3, 98.9, 90, "F"),
    # test points sit on their rail trunks (no stub, no neighbour pad)
    "TP1": (55.0, 53.0, 0, "B"),
    "TP2": (27.05, 76.0, 0, "B"),
    "TP3": (57.0, 120.0, 0, "B"),
    # input capacitors of the modules: north of the pin rows (the top side under a module body is not free).
    # Pad 1 on a VBAT stub north of the VIN pads, pad 2 in the GND pour north of the GND pads
    # y = 52.6: the pads are 0.95 mm from the F.Cu jumper of U1_PG along y = 49.8 (board clearance 0.8 mm)
    "C4": (17.8, 52.6, 0, "F"),      # U2
    "C2": (45.8, 52.6, 0, "F"),      # U1
    # output capacitors: C5 on the +5V_SENS trunk, C3 on the +5V_CPU bar north of J7
    "C5": (27.05, 62.0, 0, "F"),
    "C3": (55.0, 74.2, 180, "F"),
    # 3.3 V chain: FB1 -> /LDO_IN bar (y 99 to 101) with C6 and C7 south of it and U3 north of it -> +3V3_SENS bar to
    # the right edge connectors, C8 on that bar
    "C6": (46.6, 100.0, 270, "F"),
    "C7": (54.0, 100.0, 270, "F"),
    "U3": (50.0, 103.8, 90, "B"),
    "C8": (56.6, 111.0, 180, "F"),
})

# ---- zones ------------------------------------------------------------------------------------------------------
# The pours and the planned zones keep zone_clearance (2 mm) from other copper. Where that is not possible, a zone has
# its own clearance:
#   _FINE: at U3. A zone and a U3 pad can be 0.34 mm apart (the [[exception]] of the design rules). Two zones of
#          different nets keep the board clearance (0.8 mm), so the fine zones start inside their pad
#          and end 0.8 mm from the fine zone of the next net.
#   _NEAR: next to a pin header or a module, where 2 mm leaves no copper. Board clearance (0.8 mm).
#   _NEAR_GND: GND area at the pin headers of an edge. The router can put signal tracks in it (keepout False).
#   Other _NEAR GND areas are router keepouts: a track there would make the GND trunk narrower.
_FINE = {"clearance": 0.34, "min_w": 0.5}
_NEAR = {"clearance": 0.8, "min_w": 1.2}
_NEAR_GND = {"clearance": 0.8, "min_w": 1.2, "keepout": False}

# rev1 zone rows that this board does not have or draws again: (net, x0, y0) of the rectangle
_DROP = {("+5V_CPU", 52.8, 49.4), ("+5V_CPU", 51.8, 52.2), ("+5V_CPU", 52.2, 54.4),          # C3, TP1, R1
         ("+5V_SENS", 27.2, 68.5), ("+5V_SENS", 27.2, 73.0), ("+5V_SENS", 27.2, 75.6),       # C5, TP2, R2
         ("+5V_SENS", 3.5, 82.3), ("+5V_SENS", 5.3, 87.5), ("+5V_SENS", 4.0, 98.1),          # J8/J11 bar, J9 branch
         ("+5V_SENS", 26.1, 43.0),
         ("+5V_CPU", 56.0, 55.6),                                                            # trunk, bar J6 to J7
         ("+5V_CPU", 54.0, 43.0),                                                            # U1 VOUT trunk: again
         ("VBAT", 18.48, 40.5), ("VBAT", 46.48, 40.5), ("VBAT", 37.5, 7.9)}                  # VIN necks, C1 stub: again as _NEAR


def _keep(row):
    return (row[0], row[1][0][0], row[1][0][1]) not in _DROP


BUS_ZONES = [
    # GND at the pin headers of the left and the right edge: the 2 mm pour leaves no copper between the pins, the tracks
    # and the edge, so these two areas are GND zones with the board clearance. They are first in the list: every other
    # zone has priority over them.
    # (left edge: x to 10.1 at y 86.9 to 95.0, so that the area is 2 mm from the C9.1 pad and leaves no sliver at C9.2)
    ("GND", [(0.6, 27.0), (12.5, 27.0), (12.5, 86.9), (10.1, 86.9), (10.1, 95.0), (12.5, 95.0), (12.5, 105.5), (0.6, 105.5)],
     _NEAR_GND),
    ("GND", _rect(58.6, 103.5, 65.4, 132.0), _NEAR_GND),
    # GND trunk from J1.2 along the bottom edge (need 6.0 mm): 2 mm from the C1.1 pad leaves 5.4 mm, so this part of the
    # trunk and the C1 stub have the board clearance (C1.1 is 0.8 mm from the trunk)
    ("GND", _rect(28.0, 0.6, 65.4, 7.4), _NEAR),
    # GND at the GND pads of the modules: between the VIN neck and the 5 V trunk. With the board clearance to the neck
    # (0.8 mm) and 2 mm to the trunk, the GND copper north of the pads is 2.8 mm wide (1.6 mm with the 2 mm pour only)
    # (U2: south of pad 9 the 2 mm gap to VBAT prong B and the 0.8 mm gap to the +5V_SENS neck leave a GND tongue of
    # 0.6 mm, a MILL-CUT-SPACING warning. A smaller area leaves a sliver below 0.5 mm there)
    ("GND", _rect(20.4, 41.0, 25.5, 51.0), _NEAR),
    ("GND", _rect(48.4, 41.0, 53.5, 51.0), _NEAR),
] + [row for row in _base["BUS_ZONES"] if _keep(row)] + [
    # +5V_SENS trunk: ends 0.1 mm inside the FB1 bar (y 99.1 to 100.9). The rev1 trunk overlaps the whole bar end, and
    # the fill then leaves fragments of 0.003 mm2 there (MILL-ISLAND)
    ("+5V_SENS", _rect(26.1, 49.0, 28.0, 99.2)),
    ("+5V_CPU", _rect(54.0, 49.0, 56.0, 57.4)),
    # VOUT necks at the module pins (U2.11/12, U1.11/12): board clearance to the GND pads 9 and 10 (0.64 mm pad gap).
    # With 2 mm the trunk does not reach the VOUT pads. The 2 mm trunks start north of the pin rows (y 49): a 2 mm trunk
    # over the pin row leaves a GND tongue of 0.6 mm south of pad 9
    ("+5V_SENS", _rect(26.1, 42.9, 28.0, 49.6), _NEAR),
    ("+5V_CPU", _rect(54.0, 42.9, 56.0, 49.6), _NEAR),
    # J8.1 + J11.1 bar and the J9.1 branch, moved with J11 and J9
    ("+5V_SENS", _rect(3.5, 82.3, 6.2, 90.5), _NEAR),
    ("+5V_SENS", _rect(5.9, 87.5, 7.7, 99.5), _NEAR),
    ("+5V_SENS", _rect(4.6, 98.1, 6.3, 99.7), _NEAR),
    # VBAT at the module pins. The VIN necks are as wide as the pads (rev1 rows) and go on north of the pin row to the
    # stubs of the input capacitors. Board clearance (_NEAR): the GND pads are 0.64 mm from the VIN pads, and the GND
    # copper between the VIN neck and the 5 V trunk is then 2.8 mm wide. North of y 50.5 the neck is 1.3 mm wide: the
    # full width would be 1.2 mm from the GND pad of the input capacitor (C4.2, C2.2). 1.3 mm is above min_w
    ("VBAT", _rect(18.48, 40.5, 20.38, 50.5), _NEAR),
    ("VBAT", _rect(18.2, 50.4, 19.5, 53.0), _NEAR),
    ("VBAT", _rect(46.48, 40.5, 48.38, 50.5), _NEAR),
    ("VBAT", _rect(46.2, 50.4, 47.5, 53.0), _NEAR),
    ("VBAT", _rect(16.6, 51.4, 20.38, 53.8)),           # C4.1
    ("VBAT", _rect(44.6, 51.4, 48.38, 53.8)),           # C2.1
    ("VBAT", _rect(37.5, 7.9, 39.5, 11.5), _NEAR),      # stub to C1 (rev1 row)
    # +5V_CPU: the bar from J6.1 to J7.1 is in line with the trunk (x 54 to 56), 2 mm from the GND pads J6.2 and J7.2
    # (rev1: x 56 to 58). It goes on north of J7 to C3.1
    ("+5V_CPU", _rect(54.0, 55.6, 56.0, 75.4)),
    ("+5V_CPU", _rect(54.0, 67.0, 60.1, 69.6)),
    # /LDO_IN: bar from FB1.2 to C6.1 and C7.1, and the two prongs to U3.1 and U3.3 (pad wide)
    ("/LDO_IN", _rect(44.62, 99.0, 55.2, 101.0)),
    ("/LDO_IN", _rect(48.75, 100.8, 49.35, 102.15), _FINE),
    ("/LDO_IN", _rect(50.65, 100.8, 51.25, 102.15), _FINE),
    # GND of U3.2: strip under the body, out between pad 4 and pad 5, with a wide end in the pour north of U3
    ("GND", _rect(49.7, 102.9, 50.3, 106.3), _FINE),
    ("GND", _rect(48.5, 105.6, 51.5, 110.5), _FINE),
    # +3V3_SENS: U3.5 -> bar east -> bar north along x 56 to 58 (C8.1 and TP3 on it) -> teeth to J12.1, J13.1, J14.1
    ("+3V3_SENS", _rect(51.12, 104.28, 56.1, 105.6), _FINE),
    ("+3V3_SENS", _rect(56.0, 104.28, 58.0, 126.55)),
    ("+3V3_SENS", _rect(57.0, 106.65, 61.6, 108.55), _NEAR),
    ("+3V3_SENS", _rect(57.0, 115.65, 61.6, 117.55), _NEAR),
    ("+3V3_SENS", _rect(57.0, 124.65, 61.6, 126.55), _NEAR),
]

# Copper width rows: the rev1 rows, plus the 3.3 V chain (planned zones on this board).
PATH_ROWS = list(_base["PATH_ROWS"]) + [
    ("+3V3_SENS", "+3V3_SENS bar - J12/J13/J14", ["C8.1", "TP3.1", "J12.1", "J13.1", "J14.1"], 1.2),
    ("/LDO_IN", "LDO_IN bar FB1 - C6/C7", ["FB1.2", "C6.1", "C7.1"], "Default"),
]

# U1_PG jumper: the B.Cu stub and its rivet are 0.8 mm further west than on rev1. The stub then has the Default width
# with the board clearance to U1.2. Rev1: x = 40.4, 0.5 mm track.
JUMPERS = [
    {"net": "/U1_PG", "pad_a": ("U1", "1"), "via_a": (39.6, 49.8),
     "stub_a": [(39.6, 43.89)],
     "path": [(39.6, 49.8), (8.0, 49.8), (8.0, 52.1), (3.4, 52.1)],
     "via_b": (3.4, 52.1), "pad_b": ("J5", "1")},
]

