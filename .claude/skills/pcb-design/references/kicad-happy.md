# kicad-happy in this project

Plugin `kicad-happy@kicad-happy` (aklofas/kicad-happy, ref in `.claude/settings.json`, 2.3.2 when this file was written). It is off by default: enable it for the session with `.claude/rules/plugins.md`.

## What it gives
- No hooks and no orchestrator. It is a set of skills and stdlib Python scripts that write JSON. This project chains them with `make pcb-gate` (`pcb/libraries/pcb_gate.sh`).
- Skills: `kicad` (schematic, PCB, Gerber, cross analysis, thermal, fab release gate, diff), `emc`, `spice` (needs `ngspice`), `datasheets` (extraction with a per-MPN cache), `bom`, the distributor skills `lcsc` (no key), `digikey`, `mouser`, `element14` (keys in user scope), and the guidance skills `jlcpcb`, `pcbway`.

## Which analyzer in which phase
| Phase | Analyzer | How |
| --- | --- | --- |
| Parts and datasheets | `datasheets`, `lcsc` | skill `hw-research` |
| Schematic | `analyze_schematic.py` (stage `schematic`) | `make pcb-gate` runs it. For a schematic without a board, run the script alone (below) |
| Subcircuits | `spice` | only with `ngspice`. Without it, write "SPICE not run" |
| Board | `analyze_pcb.py`, `analyze_emc.py`, `analyze_thermal.py` | `make pcb-gate` |
| Before an order | `analyze_gerbers.py`, `fab_release_gate.py` | `make pcb-gate METHOD=fab` (skill `pcb-fab`) |
| Between two reviews | `diff_analysis.py <old>.json <new>.json --text` | `make pcb-gate` overwrites `build/gate/<BOARD>/`: copy it to `build/gate-old/<BOARD>/` before the next run, then compare `schematic.json`, `pcb.json` and `emc.json` one pair at a time |

## Run one script alone
The scripts use the Python standard library. Run them with `python3` in the KiCad image, with the plugin directory mounted read-only. Write the output below `build/`.
```
KH=$(ls -d ~/.claude/plugins/cache/kicad-happy/kicad-happy/* | sort | tail -1)   # the same directory as KICAD_HAPPY in the Makefile
docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD":"$PWD" -v "$KH":"$KH":ro -w "$PWD/pcb/releases/rev1" rccar-kicad:local \
  python3 "$KH/skills/kicad/scripts/analyze_schematic.py" rc_power_board.kicad_sch --text
```
Read each script's `--help` first: the options change between plugin versions.

## Findings are claims
- `make pcb-gate` runs `analyze_pcb.py --full` (per-track data). The EMC grounding checks (GP-001, RP-001, VS-001) need it. Without it the EMC score is too high.
- A verified false positive or owner decision goes into `suppressions` of the board's `.kicad-happy.json` (`.claude/skills/pcb-fab/references/fab-gate.md`).
- The full CI reports are artifacts of the `pcb` workflow run: `gh run download <run-id> --dir build/ci-report`.
- Give each finding a verdict: true, false positive (with the reason), or owner decision. Check it in the raw file first.
- Known false positives of this board: `docs/pcb/releases/rev1/review/README.md` (rev1) and `fab-gate.md` of skill `pcb-fab` (the gate).
- Load the skill (`kicad`, `emc`) to read the meaning of a rule id.
