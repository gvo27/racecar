"""Make the schematic of a board variant from the schematic of the base board. Make target: pcb-sch.

A variant has the same circuit as the base board (paths.base_board_dir()) without the parts in `[parts] exclude` of its design
rules, and with the footprints of `[parts.footprint]` (same part value, a package that the variant can make). For each excluded part the copy has `(on_board no)`, `(in_bom no)` and `(dnp yes)`: the part stays in the
drawing, is crossed out, and has no footprint and no BOM row. A part with a variant footprint gets TBD in its part
fields (MPN, Manufacturer, Supplier link, Status) and an empty unit cost: the base part number is for the base
footprint. The variant keeps its own title-block revision (`(rev "...")`): the first run copies the base revision. Nothing else changes, so the variant cannot drift from the base schematic. Do not edit the variant schematic by hand: edit the base schematic, then run `make pcb-sch`.

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


PROP = r'\(property "%s" "((?:[^"\\]|\\.)*)"'
REV = re.compile(r'\(rev "((?:[^"\\]|\\.)*)"\)')
# fields of the base part that are wrong for a part with another footprint: the variant sets them to TBD (no
# unconfirmed part numbers). The unit cost is empty: the cost total counts the part as 0.
PART_FIELDS = (("MPN", "TBD"), ("Manufacturer", "TBD"), ("Supplier link", "TBD"), ("Status", "TBD"), ("Unit cost USD", ""))


def clear_part_fields(block, ref, footprint):
    """Set the part fields of a symbol with a variant footprint to TBD. BOM Comments keeps the base part number."""
    old = re.search(PROP % "MPN", block)
    old_note = re.search(PROP % "BOM Comments", block)
    for name, val in PART_FIELDS:
        block, n = re.subn(PROP % re.escape(name), lambda m, name=name, val=val: '(property "%s" "%s"' % (name, val), block, count=1)
        if n != 1:
            raise RuntimeError("symbol %s has no %s property" % (ref, name))
    note = "Variant footprint %s: part number TBD (owner). Base board part %s: %s" % (
        footprint, old.group(1) if old else "-", old_note.group(1) if old_note else "-")
    block, n = re.subn(PROP % "BOM Comments", lambda m: '(property "BOM Comments" "%s"' % note, block, count=1)
    if n != 1:
        raise RuntimeError("symbol %s has no BOM Comments property" % ref)
    return block


WIRE_FP = "rc_power:SolderWire_1x%02d_P2.50mm"   # pcb/lib/rc_power.pretty: the pads of a JST XH header, no body
WIRE_FIELDS = (("MPN", "none"), ("Manufacturer", "none"), ("Supplier link", ""), ("Status", "none"), ("Unit cost USD", ""))


def wire_footprint(block, ref):
    """The solder-wire footprint for a JST XH 1xNN header of the base schematic (same pad positions)."""
    m = re.search(r'\(property "Footprint" "Connector_JST:JST_XH_[^"]*_1x(\d+)_P2\.50mm[^"]*"', block)
    if not m:
        raise RuntimeError("symbol %s: [parts.wire] needs a JST XH 2.50 mm header footprint in the base schematic" % ref)
    return WIRE_FP % int(m.group(1))


def set_wire_fields(block, ref):
    """Part fields of a header that becomes wire pads: no part. BOM Comments keeps the base part number."""
    old = re.search(PROP % "MPN", block)
    for name, val in WIRE_FIELDS:
        block, n = re.subn(PROP % re.escape(name), lambda m, name=name, val=val: '(property "%s" "%s"' % (name, val), block, count=1)
        if n != 1:
            raise RuntimeError("symbol %s has no %s property" % (ref, name))
    note = ("Temporary (first mill print round): wires soldered to the pads, no header. "
            "Base board part %s ([parts.wire] of the design rules)" % (old.group(1) if old else "-"))
    block, n = re.subn(PROP % "BOM Comments", lambda m: '(property "BOM Comments" "%s"' % note, block, count=1)
    if n != 1:
        raise RuntimeError("symbol %s has no BOM Comments property" % ref)
    return block


def keep_revision(text, old):
    """Return `text` with the title-block revision of `old` (the variant schematic before this run). `old` None: no change."""
    m = REV.search(old) if old else None
    return REV.sub(lambda _: m.group(0), text, count=1) if m else text


def make_variant(text, exclude, footprints=None, wires=None):
    """Return (new text, references that were changed). `footprints`: ref -> footprint of the variant.
    `wires`: refs whose JST XH header becomes solder-wire pads ([parts.wire])."""
    done = []
    footprints = footprints or {}
    wires = wires or set()

    def patch(m):
        block = m.group(0)
        ref = REF.search(block)
        if not ref:
            return block
        if ref.group(1) in footprints:
            block, n = re.subn(r'\(property "Footprint" "[^"]*"', '(property "Footprint" "%s"' % footprints[ref.group(1)], block, count=1)
            if n != 1:
                raise RuntimeError("symbol %s has no Footprint property" % ref.group(1))
            block = clear_part_fields(block, ref.group(1), footprints[ref.group(1)])
            done.append(ref.group(1))
        if ref.group(1) in wires:
            fp = wire_footprint(block, ref.group(1))
            block = re.sub(r'\(property "Footprint" "[^"]*"', '(property "Footprint" "%s"' % fp, block, count=1)
            block = set_wire_fields(block, ref.group(1))
            done.append(ref.group(1))
        if ref.group(1) not in exclude:
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
        text, done = make_variant(fh.read(), set(r.exclude), r.footprint, set(r.wire))
    missing = sorted((set(r.exclude) | set(r.footprint) | set(r.wire)) - set(done))
    if missing:
        print("pcb-sch: [parts] names parts that are not in the base schematic: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    target = os.path.join(board_dir, name)
    old = open(target, encoding="utf-8").read() if os.path.exists(target) else None
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(keep_revision(text, old))
    for f in COPY_ONCE:
        if not os.path.exists(os.path.join(board_dir, f)):
            shutil.copyfile(os.path.join(base_dir, f), os.path.join(board_dir, f))
    print("pcb-sch: wrote %s from %s, not on this board: %s, other footprint: %s, wire pads (temporary): %s" % (
        os.path.relpath(os.path.join(board_dir, name), paths.REPO_ROOT), os.path.basename(base_dir),
        ", ".join(sorted(r.exclude)) or "-", ", ".join(sorted(r.footprint)) or "-", ", ".join(sorted(r.wire)) or "-"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-dir", default=paths.base_board_dir())
    ap.add_argument("--board-dir", default=paths.board_dir())
    args = ap.parse_args(argv)
    return run(args.base_dir, args.board_dir)


if __name__ == "__main__":
    sys.exit(main())
