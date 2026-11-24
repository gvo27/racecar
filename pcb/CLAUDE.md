# pcb/: agent notes

Facts and conventions: `docs/pcb/conventions.md`.

## Verify
- `make pcb-test`: unit tests of `pcb/libraries/` and of the lab tools.
- `make pcb-check BOARD=src` and `make pcb-mill-check BOARD=src`: DRC, board checks and milling check of the active board.
- `make erc BOARD=<board>` after a schematic change.
- The tools run only in the KiCad image (`make kicad-image`). Do not run them with the host python.
