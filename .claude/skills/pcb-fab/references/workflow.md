# Upstream workflow and how this project runs it

kicad-happy (aklofas/kicad-happy, README "Workflow") describes 7 steps. The plugin has no hooks and no orchestrator: the agent chains the skills and scripts. This table shows how each step runs here.

| Upstream step | Here | Automated? |
| --- | --- | --- |
| 1. Design the schematic and lay out the PCB | skill `pcb-design` | owner and agent |
| 2. Sync datasheets: download the PDFs, extract structured specs for each MPN | skill `hw-research` (kicad-happy `lcsc` + `datasheets`) | scripts download. Extraction is agent work (the `datasheets` skill plans and merges) |
| 3. Design review: schematic, PCB, cross analysis, EMC, SPICE, thermal, datasheet cross-reference, report by severity | `make pcb-gate` (analyzers), then `pcb-reviewer` (verdicts, manual checks) | the analyzers yes. The verdicts no |
| 4. Iterate, compare with the previous run | `diff_analysis.py --run OLD --run NEW` on two `build/gate/` runs | script |
| 5. Source the components (DigiKey/Mouser for prototypes, LCSC for production) | skill `pcb-parts`, kicad-happy distributor skills | agent, with API keys for DigiKey and Mouser |
| 6. Export the BOM and the order files for each supplier | kicad-happy `bom`: `bom_manager.py export`, `bom_manager.py order --boards N --spares S`, `translate_bom_pnp.py` (JLCPCB BOM/CPL) | script |
| 7. Order from JLCPCB or PCBWay | the owner | manual |

## Notes
- The GitHub Action `aklofas/kicad-happy` runs steps 3 and 4 on each PR (`.github/workflows/pcb.yml`). It does not run `fab_release_gate.py`. `make pcb-gate` does.
- The mill path skips the Gerber analysis, JLCPCB tiers and assembly. `make pcb-mill-check` and `make pcb-fab` (DXF, Excellon) replace them.
- `fab_release_gate.py` exits 0 also for FAIL and INCOMPLETE. Read the header `FABRICATION RELEASE GATE — <status>` or `overall_status` in `gate.json`, not the exit code.
- The scripts need only the Python standard library. Run them in the KiCad image, not with the host python3.
