"""Read the outline and the mounting holes of a KiCad board file (text, no KiCad needed).

Result frame: board-centered, X along KiCad x, Y up (KiCad y points down). Units mm.
"""

import re
from dataclasses import dataclass
from pathlib import Path

RECT_RE = re.compile(
    r'\(gr_rect\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\).*?\(layer\s+"Edge\.Cuts"\)',
    re.DOTALL,
)
FOOTPRINT_RE = re.compile(r'\(footprint\s+"([^"]*MountingHole[^"]*)"')
AT_RE = re.compile(r"\(at\s+([-\d.]+)\s+([-\d.]+)")
DRILL_RE = re.compile(r"\(drill\s+([-\d.]+)")


@dataclass(frozen=True)
class BoardHole:
    x: float
    y: float
    d: float


@dataclass(frozen=True)
class Board:
    width: float
    height: float
    holes: tuple[BoardHole, ...]


def _blocks(text: str, start: int):
    """The text of the s-expression that opens at index start."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unbalanced s-expression")


def read_board(path) -> Board:
    text = Path(path).read_text()
    rects = RECT_RE.findall(text)
    if len(rects) != 1:
        raise ValueError(f"{path}: expected one Edge.Cuts rectangle, found {len(rects)}")
    x0, y0, x1, y1 = (float(v) for v in rects[0])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    holes = []
    for m in FOOTPRINT_RE.finditer(text):
        block = _blocks(text, m.start())
        at = AT_RE.search(block)
        drill = DRILL_RE.search(block)
        if at is None or drill is None:
            raise ValueError(f"{path}: footprint {m.group(1)} without position or drill")
        holes.append(BoardHole(float(at.group(1)) - cx, cy - float(at.group(2)), float(drill.group(1))))
    return Board(abs(x1 - x0), abs(y1 - y0), tuple(sorted(holes, key=lambda h: (h.x, h.y))))
