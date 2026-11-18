#!/bin/sh
# Fab release gate of one board (make pcb-gate). It runs the kicad-happy analyzers, then fab_release_gate.py.
# Runs in the KiCad image, in the board directory. Arguments: <kicad-happy plugin dir> <output dir> <method: fab|mill>
# Method fab: Gerber and drill export (kicad-cli), analyze_gerbers.py, gate with --gerbers.
# Method mill: no Gerbers (the lab mills from DXF and Excellon: make pcb-fab, make pcb-mill-check).
set -eu
KH="$1"; OUT="$2"; METHOD="$3"
S="$KH/skills/kicad/scripts"
STEM=rc_power_board
mkdir -p "$OUT"
python3 "$S/analyze_schematic.py" "$STEM.kicad_sch" --no-hierarchy -o "$OUT/schematic.json"
python3 "$S/analyze_pcb.py" "$STEM.kicad_pcb" --schematic "$STEM.kicad_sch" -o "$OUT/pcb.json"
python3 "$KH/skills/emc/scripts/analyze_emc.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" -o "$OUT/emc.json"
python3 "$S/analyze_thermal.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" -o "$OUT/thermal.json"
GERBERS=""
if [ "$METHOD" = fab ]; then
  rm -rf "$OUT/gerbers"; mkdir -p "$OUT/gerbers"
  kicad-cli pcb export gerbers -o "$OUT/gerbers/" "$STEM.kicad_pcb" >/dev/null
  kicad-cli pcb export drill -o "$OUT/gerbers/" "$STEM.kicad_pcb" >/dev/null
  python3 "$S/analyze_gerbers.py" "$OUT/gerbers" -o "$OUT/gerbers.json"
  GERBERS="--gerbers $OUT/gerbers.json"
elif [ "$METHOD" != mill ]; then
  echo "pcb-gate: METHOD must be fab or mill, not $METHOD" >&2; exit 2
fi
# shellcheck disable=SC2086
python3 "$S/fab_release_gate.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" -t "$OUT/thermal.json" -e "$OUT/emc.json" $GERBERS -o "$OUT/gate.json"
# shellcheck disable=SC2086
python3 "$S/fab_release_gate.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" -t "$OUT/thermal.json" -e "$OUT/emc.json" $GERBERS --text
