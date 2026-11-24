# Rev2 (release): review record

Rev2 is a frozen copy of the mill board with the JST XH headers and its own copy of the design rules (`pcb/releases/rev2/design_rules.toml`, 2026-11-17). It is not reviewed again: the active board is `pcb/src` (rev3, record in `docs/pcb/releases/rev3/review/`). This record keeps only the latest state. The review history of this layout is in `docs/archive/pcb/review/2026-11-18-mill-review-record.md`.

Files: `drc.json`, `milling_check.json`, `rc_power_board_layers.pdf`, `rc_power_board_1to1.pdf` (`make pcb-review BOARD=releases/rev2`).

## Check results (2026-11-18)

| Check | Result |
| --- | --- |
| `make erc BOARD=releases/rev2` | 0 errors, 3 warnings (`lib_symbol_mismatch`) |
| `make pcb-rules BOARD=releases/rev2` | The project files agree with the design rules |
| `make pcb-check BOARD=releases/rev2` | DRC: 0 errors, 0 unconnected, parity clean. 117 warnings: 26 `lib_footprint_mismatch`, 91 `silk_over_copper`. `check_board` 0 problems |
| `make pcb-mill-check BOARD=releases/rev2` | 0 errors, 96 warnings |
| `make pcb-gate BOARD=releases/rev2` | FAIL from the count false positive (`pcb/.claude/skills/pcb-fab/references/fab-gate.md`), WARN for the silkscreen (no silkscreen on a milled board). EMC 65.5/100. No `.kicad-happy.json` suppressions for this release |

The board is the second mill layout, so the kicad-happy findings are the findings of the active board before the wire pads: see the verdicts in `docs/pcb/releases/rev3/review/README.md`.
