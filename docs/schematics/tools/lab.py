"""Path of the lab directory (mill limits, machine, lab inventory, lab CAM example).

The repo keeps the path in one place: the `lab:` line of `.claude/CLAUDE.md`. All tools get the path from this module.
The environment variable LAB_DIR overrides the pointer (another lab, tests).
"""
import os
import re

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
POINTER = re.compile(r"^lab:\s*(\S+)", re.MULTILINE)


def read_pointer(root=REPO_ROOT):
    path = os.path.join(root, ".claude", "CLAUDE.md")
    with open(path, encoding="utf-8") as fh:
        m = POINTER.search(fh.read())
    if not m:
        raise RuntimeError("%s: no 'lab:' line. Add the path of the lab directory" % path)
    return os.path.normpath(os.path.join(root, m.group(1)))


def lab_dir():
    return os.environ.get("LAB_DIR") or read_pointer()


def limits_file():
    return os.path.join(lab_dir(), "milling.toml")
