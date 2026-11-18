"""Placement of the selected board, plus the lab frame of the mill.

The board data (outline, part positions, zones, jumpers, bored holes) is in `placement.py` of the board directory
(`paths.board_dir()`, env BOARD_DIR). This module loads that file and gives its names: `placement.PLACEMENT`,
`placement.BUS_ZONES` and so on. Coordinates are mm from the outline's lower-left corner (x to the right, y up).
"""
import os
import runpy
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab  # noqa: E402
import paths  # noqa: E402

BOARD_FILE = os.path.join(paths.board_dir(), "placement.py")
REQUIRED = ("OUTLINE_W", "OUTLINE_H", "PLACEMENT", "BUS_ZONES", "GND_KEEPOUTS", "JUMPERS", "STITCH_VIAS", "MILLED_HOLES", "PATH_ROWS")


def load_board_file(path):
    """Run a board placement file and return its names. A board file can call this for another board and change the result."""
    return {k: v for k, v in runpy.run_path(path).items() if not k.startswith("_")}


_data = load_board_file(BOARD_FILE)
_missing = [k for k in REQUIRED if k not in _data]
if _missing:
    raise RuntimeError("%s: missing names: %s" % (BOARD_FILE, ", ".join(_missing)))
globals().update(_data)

# ---- lab frame (Task 9) ----------------------------------------------------------------------------------------
# Stock and dowels of the lab's Fusion 360 template: milling.toml [stock], [dowel] in the lab directory (lab.py).
# Stock coordinates: origin = stock lower-left corner, x along the long side, y along the short side.
with open(lab.limits_file(), "rb") as _fh:
    _LAB = tomllib.load(_fh)
STOCK = (_LAB["stock"]["width"], _LAB["stock"]["height"])
DOWEL_DIA = _LAB["dowel"]["diameter"]
DOWELS = [tuple(c) for c in _LAB["dowel"]["centers"]]

# The board is turned 90 degrees counter-clockwise (top view) and centered on the stock: the board's long side (140 mm)
# runs along stock x, with 6.2 mm at each end and 17.8 mm at each long side. The board's +y end (top, J14 side) then
# points to stock -x (dowel 1) and the board's +x side points to stock +y. Export transform only: the KiCad board
# does not move. The dowels sit outside the board, 14 mm from the nearest outline point.
MARGIN_X = (STOCK[0] - OUTLINE_H) / 2.0  # noqa: F821
MARGIN_Y = (STOCK[1] - OUTLINE_W) / 2.0  # noqa: F821


def board_to_stock(bx, by):
    """Board table coordinates (mm from the outline's lower-left corner, y up) -> stock coordinates."""
    return MARGIN_X + (OUTLINE_H - by), MARGIN_Y + bx  # noqa: F821


def stock_to_board(sx, sy):
    return sy - MARGIN_Y, OUTLINE_H - (sx - MARGIN_X)  # noqa: F821


def board_to_lab(bx, by):
    """Board table coordinates -> lab frame: origin = dowel 1 center (the Fusion Setup B WCS), x along the stock long side."""
    sx, sy = board_to_stock(bx, by)
    return sx - DOWELS[0][0], sy - DOWELS[0][1]


DOWELS_LAB = [(round(x - DOWELS[0][0], 4), round(y - DOWELS[0][1], 4)) for x, y in DOWELS]
