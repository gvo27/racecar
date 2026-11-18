# Fab release gate: how to read it on this project

`make pcb-gate BOARD=<board> [METHOD=fab|mill]` writes `build/gate/<BOARD>/` (schematic, pcb, emc, thermal, gerbers and gate JSON) and prints the gate text. The script is `pcb/libraries/pcb_gate.sh`. `METHOD` is `mill` for `BOARD=src`, else `fab`.

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

## Suppressions and known false positives
- A verified false positive or an owner decision on an analyzer finding goes into `suppressions` of the board's `.kicad-happy.json` (rule id, components or nets, and a reason that names the evidence). The analyzers mark the finding as suppressed and keep it in the report. `make pcb-gate` passes the file with `--config` to each analyzer and applies it to the schematic and PCB JSON too (`pcb/libraries/gate_suppress.py`: kicad-happy 2.3.2 does not do this itself). The CI action reads the same file.
- Never suppress a finding without its evidence. A gate line (below) has no rule id and cannot be suppressed: write it in this table.

| Board | Gate line | Why |
| --- | --- | --- |
| `src`, `releases/rev2` | `Component count mismatch: schematic 40 vs PCB 34` and `net count gap: schematic 24 vs PCB 21` | The 6 parts of `[parts] exclude` (D2 to D4, R1 to R3) are `dnp`, `on_board no` and `in_bom no` in the mill schematic. In kicad-happy 2.3.2 the statistic `dnp_parts` counts only the DNP parts that are in the BOM, so it is 0 and the gate counts the 6 parts as missing (upstream gap). Their 3 LED nets are not on the board. Check: `make pcb-check BOARD=src` reports parity clean |
| `src`, `releases/rev2` | `No revision marking` and `No board name on silkscreen` | The mill board has no silkscreen by design (`build_pcb.py` puts the reference designators on the fab layer). A copper marking is an owner decision |

Add each new false positive here, with the evidence.

## Snapshot (2026-11-18, kicad-happy 2.3.2)
A dated example of the output, to calibrate a reading. It goes stale: run `make pcb-gate` for the current state. The review records own the board status (`docs/pcb/releases/rev1/review/README.md`, `docs/pcb/releases/rev3/review/README.md`).
- `BOARD=releases/rev1` (fab): `WARN`. All nets routed (24/24), all 33 parts with MPN, DFM standard tier, schematic and PCB match (40/40, 24 nets), Gerber layers present, EMC 88.0/100 with no critical finding. Warnings: no revision and no board name on the silkscreen.
- `BOARD=src` (mill): `FAIL` from the false positive above. The other lines are as for rev1, without Gerbers.
