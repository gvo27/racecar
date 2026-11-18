# Fab release gate: how to read it on this project

`make pcb-gate BOARD=<board> [METHOD=fab|mill]` writes `build/gate/<BOARD>/` (schematic, pcb, emc, thermal, gerbers and gate JSON) and prints the gate text. The script is `pcb/libraries/pcb_gate.sh`. `METHOD` is `mill` for `BOARD=mill`, else `fab`.

## Categories
| Category | Source | Notes for this project |
| --- | --- | --- |
| Routing completeness | `analyze_pcb.py` | Also run `make pcb-check` (DRC unconnected items, parity). The gate does not replace it |
| BOM readiness | schematic fields | MPN for each placed part. A `TBD` field is a FAIL or a WARN: it needs an owner decision, not a fill-in |
| DFM | `analyze_pcb.py` | Fab-house tiers. For the mill, the limits are in the lab file: `make pcb-mill-check` is the DFM check |
| Documentation | silkscreen, title block | Revision and board name on the silkscreen: rev1 and rev2 have none (WARN, owner decision) |
| Schematic and PCB match | both JSON files | See "Known false positives" |
| Gerbers | `analyze_gerbers.py` | `METHOD=fab` only |
| Thermal | `analyze_thermal.py` | Check the junction temperature against the datasheet at the real input voltage |
| EMC | `analyze_emc.py` | A score and findings. Give each error finding a verdict |

## Known false positives
| Board | Gate line | Why |
| --- | --- | --- |
| `mill` | `Component count mismatch: schematic 40 vs PCB 34` and `net count gap: schematic 24 vs PCB 21` | The 6 parts of `[parts] exclude` (D2 to D4, R1 to R3) are `dnp` and `on_board no` in the mill schematic. The analyzer counts them. Their 3 LED nets are not on the board. Check: `make pcb-check BOARD=mill` reports parity clean |

Add each new false positive here, with the evidence.

## Snapshot (2026-11-18, kicad-happy 2.3.2)
A dated example of the output, to calibrate a reading. It goes stale: run `make pcb-gate` for the current state. The review records own the board status (`docs/pcb/review/README.md`, `docs/techctcarvera/review/README.md`).
- `BOARD=releases/rev1` (fab): `WARN`. All nets routed (24/24), all 33 parts with MPN, DFM standard tier, schematic and PCB match (40/40, 24 nets), Gerber layers present, EMC 88.0/100 with no critical finding. Warnings: no revision and no board name on the silkscreen.
- `BOARD=mill` (mill): `FAIL` from the false positive above. The other lines are as for rev1, without Gerbers.
