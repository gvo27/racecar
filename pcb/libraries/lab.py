"""Path of the lab directory (mill limits, machine, lab inventory, lab CAM example).

The repo keeps the path in one place: key `dir` of `pcb/config/lab.toml`. All tools get the path from this module.
The mill tools are in `tools/` of the lab directory. This module adds that directory to `sys.path`.
The environment variable LAB_DIR overrides the pointer (another lab, tests).
"""
import os
import sys
import tomllib

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONFIG = os.path.join("pcb", "config", "lab.toml")


def read_pointer(root=REPO_ROOT):
    path = os.path.join(root, CONFIG)
    with open(path, "rb") as fh:
        rel = tomllib.load(fh).get("dir")
    if not rel:
        raise RuntimeError("%s: no key 'dir'. Add the path of the lab directory" % path)
    return os.path.normpath(os.path.join(root, rel))


def lab_dir():
    return os.environ.get("LAB_DIR") or read_pointer()


def limits_file():
    return os.path.join(lab_dir(), "milling.toml")


def waivers_file():
    return os.path.join(lab_dir(), "milling_waivers.toml")


def tools_dir():
    return os.path.join(lab_dir(), "tools")


# The mill tools (milling_check.py, fab_export.py) are in the lab directory. A tool that imports this module can import them.
if tools_dir() not in sys.path:
    sys.path.insert(1, tools_dir())
