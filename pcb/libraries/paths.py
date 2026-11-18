"""Paths of the PCB project. All tools get the repo layout from this module.

pcb/<board>/   one KiCad project per board (schematic, board, rules, BOM export); releases in pcb/releases/<rev>/
pcb/lib/       symbol and footprint libraries, shared by all boards
pcb/libraries/ board tools and their Python libraries (this directory)
docs/pcb/      context of the board and the schematic (plan, overview, BOM notes, review, analysis)
The lab directory (mill limits, mill tools) comes from lab.py.

The environment variable BOARD_DIR selects the board directory. The default is DEFAULT_BOARD (the rev1 release).
"""
import os

LIBRARIES_DIR = os.path.dirname(os.path.abspath(__file__))
PCB_DIR = os.path.normpath(os.path.join(LIBRARIES_DIR, ".."))
REPO_ROOT = os.path.normpath(os.path.join(PCB_DIR, ".."))
LIB_DIR = os.path.join(PCB_DIR, "lib")
DOCS_DIR = os.path.join(REPO_ROOT, "docs", "pcb")
DEFAULT_BOARD = os.path.join("releases", "rev1")
STEM = "rc_power_board"


def base_board_dir():
    """The base board (the rev1 release): the source of the variant schematics and of the base placement."""
    return os.path.join(PCB_DIR, DEFAULT_BOARD)


def board_dir():
    return os.path.abspath(os.environ.get("BOARD_DIR") or base_board_dir())


def review_dir():
    """Review files of the selected board: docs/pcb/review for the base board, review/ of the lab directory for a mill board."""
    import lab
    base = os.path.abspath(board_dir()) == os.path.abspath(base_board_dir())
    return os.path.join(DOCS_DIR, "review") if base else os.path.join(lab.lab_dir(), "review")
