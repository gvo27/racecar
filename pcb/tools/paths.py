"""Paths of the PCB project. All tools get the repo layout from this module.

pcb/<board>/   one KiCad project per board (schematic, board, rules, BOM export, fab outputs)
pcb/lib/       symbol and footprint libraries, shared by all boards
pcb/tools/     board tools (this directory)
docs/pcb/      context of the board and the schematic (plan, overview, BOM notes, review, analysis)
The lab directory (mill limits, mill tools) comes from lab.py.

The environment variable BOARD_DIR selects the board directory. The default is pcb/fabhouse.
"""
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(TOOLS_DIR, ".."))
REPO_ROOT = os.path.normpath(os.path.join(PCB_DIR, ".."))
LIB_DIR = os.path.join(PCB_DIR, "lib")
DOCS_DIR = os.path.join(REPO_ROOT, "docs", "pcb")
DEFAULT_BOARD = "fabhouse"
STEM = "rc_power_board"


def board_dir():
    return os.path.abspath(os.environ.get("BOARD_DIR") or os.path.join(PCB_DIR, DEFAULT_BOARD))
