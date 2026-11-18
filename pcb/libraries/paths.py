"""Paths of the PCB project. All tools get the repo layout from this module.

pcb/<board>/   one KiCad project per board (schematic, board, rules, BOM export); releases in pcb/releases/<rev>/
pcb/lib/       symbol and footprint libraries, shared by all boards
pcb/libraries/ board tools and their Python libraries (this directory)
docs/pcb/      context of the board and the schematic (plan, overview, BOM notes); review files in docs/pcb/releases/<rev>/review/
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
# The active board is pcb/src (the working board, not in pcb/releases/). It reviews into the folder of its next release.
# The Makefile keeps a copy (SRC_RELEASE); test_rules checks that they agree.
WORKING_RELEASE = {"src": "rev3"}


def base_board_dir():
    """The base board (the rev1 release): the source of the variant schematics and of the base placement."""
    return os.path.join(PCB_DIR, DEFAULT_BOARD)


def board_dir():
    return os.path.abspath(os.environ.get("BOARD_DIR") or base_board_dir())


def release_of(board):
    """The release name of a board directory: rev<N> for pcb/releases/rev<N>, WORKING_RELEASE for a working board."""
    rel = os.path.relpath(os.path.abspath(board), PCB_DIR).replace(os.sep, "/")
    if rel.startswith("releases/"):
        return rel.split("/", 1)[1]
    if rel in WORKING_RELEASE:
        return WORKING_RELEASE[rel]
    raise ValueError("board %s has no release name: add it to paths.WORKING_RELEASE" % rel)


def review_dir():
    """Review files of the selected board: docs/pcb/releases/<rev>/review (README.md, drc.json, milling_check.json, PDFs)."""
    return os.path.join(DOCS_DIR, "releases", release_of(board_dir()), "review")
