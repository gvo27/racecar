#!/bin/sh
# Fab release gate of one board (make pcb-gate). It runs the kicad-happy analyzers, then fab_release_gate.py.
# Runs in the KiCad image, in the board directory. Arguments: <kicad-happy plugin dir> <output dir> <method: fab|mill>
# Method fab: Gerber and drill export (kicad-cli), analyze_gerbers.py, gate with --gerbers.
# Method mill: no Gerbers (the lab mills from DXF and Excellon: make pcb-fab, make pcb-mill-check).
set -eu
# shellcheck disable=SC2086 # $CFG and $GERBERS are option lists
KH="$1"; OUT="$2"; METHOD="$3"
S="$KH/skills/kicad/scripts"
STEM=rc_power_board
mkdir -p "$OUT"
# The analyzers look for .kicad-happy.json next to their input file. The EMC and thermal inputs are JSON files in $OUT,
# so pass the board config (suppressions, design intent) to each analyzer.
CFG=""
if [ -f .kicad-happy.json ]; then CFG="--config $(pwd)/.kicad-happy.json"; fi
python3 "$S/analyze_schematic.py" "$STEM.kicad_sch" --no-hierarchy $CFG -o "$OUT/schematic.json"
python3 "$S/analyze_pcb.py" "$STEM.kicad_pcb" --schematic "$STEM.kicad_sch" --full $CFG -o "$OUT/pcb.json"   # --full: per-track data for the EMC checks
if [ -n "$CFG" ]; then   # analyze_schematic and analyze_pcb do not apply suppressions (kicad-happy 2.3.2)
  python3 "$(dirname "$0")/gate_suppress.py" "$S" "$(pwd)/.kicad-happy.json" "$OUT/schematic.json" "$OUT/pcb.json"
fi
python3 "$KH/skills/emc/scripts/analyze_emc.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" $CFG -o "$OUT/emc.json"
python3 "$S/analyze_thermal.py" -s "$OUT/schematic.json" -p "$OUT/pcb.json" $CFG -o "$OUT/thermal.json"
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
