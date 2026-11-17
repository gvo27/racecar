"""Make the schematic of a board variant from the schematic of the base board. Make target: pcb-sch.

A variant has the same circuit as the base board (pcb/fabhouse) without the parts in `[parts] exclude` of its design
rules. For each excluded part the copy has `(on_board no)`, `(in_bom no)` and `(dnp yes)`: the part stays in the
drawing, is crossed out, and has no footprint and no BOM row. Nothing else changes, so the variant cannot drift from
the base schematic. Do not edit the variant schematic by hand: edit the base schematic, then run `make pcb-sch`.

The first run also copies the project file and the lib tables of the base board. Stdlib only.
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
import rules  # noqa: E402

SYMBOL = re.compile(r'\n\t\(symbol\n\t\t\(lib_id .*?\n\t\)(?=\n)', re.S)
REF = re.compile(r'\(property "Reference" "([^"]+)"')
FLAGS = (("on_board", "no"), ("in_bom", "no"), ("dnp", "yes"))
COPY_ONCE = (paths.STEM + ".kicad_pro", "sym-lib-table", "fp-lib-table", ".gitignore")


def make_variant(text, exclude):
    """Return (new text, references that were changed)."""
    done = []

    def patch(m):
        block = m.group(0)
        ref = REF.search(block)
        if not ref or ref.group(1) not in exclude:
            return block
        for key, val in FLAGS:
            block, n = re.subn(r"\(%s (yes|no)\)" % key, "(%s %s)" % (key, val), block, count=1)
            if n != 1:
                raise RuntimeError("symbol %s has no (%s ...) flag" % (ref.group(1), key))
        done.append(ref.group(1))
        return block

    return SYMBOL.sub(patch, text), done


def run(base_dir, board_dir):
    r = rules.load(rules.rules_file(board_dir))
    if os.path.abspath(base_dir) == os.path.abspath(board_dir):
        print("pcb-sch: %s is the base board. Nothing to do" % os.path.basename(board_dir))
        return 0
    os.makedirs(board_dir, exist_ok=True)
    name = paths.STEM + ".kicad_sch"
    with open(os.path.join(base_dir, name), encoding="utf-8") as fh:
        text, done = make_variant(fh.read(), set(r.exclude))
    missing = sorted(set(r.exclude) - set(done))
    if missing:
        print("pcb-sch: [parts] exclude names parts that are not in the base schematic: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    with open(os.path.join(board_dir, name), "w", encoding="utf-8") as fh:
        fh.write(text)
    for f in COPY_ONCE:
        if not os.path.exists(os.path.join(board_dir, f)):
            shutil.copyfile(os.path.join(base_dir, f), os.path.join(board_dir, f))
    print("pcb-sch: wrote %s from %s, not on this board: %s" % (
        os.path.relpath(os.path.join(board_dir, name), paths.REPO_ROOT), os.path.basename(base_dir), ", ".join(sorted(done)) or "-"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-dir", default=os.path.join(paths.PCB_DIR, paths.DEFAULT_BOARD))
    ap.add_argument("--board-dir", default=paths.board_dir())
    args = ap.parse_args(argv)
    return run(args.base_dir, args.board_dir)


if __name__ == "__main__":
    sys.exit(main())
