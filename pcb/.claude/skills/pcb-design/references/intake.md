# Intake and plan

## Inputs
The owner gives three inputs: the application, the parts inventory, and the manufacturing method. If one is missing, ask for it.

## Start questions
Read the project rules, the plan documents, `docs/datasheets/` and the lab file first. Then ask in one message only what the files do not answer:
- Loads: voltage, typical and maximum current, start current, ripple limit, connector on the device.
- Source: battery chemistry, cell count, cutoff voltage, maximum current, connector.
- Environment: vibration, heat, enclosure, mounting holes, board size limit.
- Inventory: parts in hand, connector families in stock, wire gauges, crimp tools.
- Method: mill (machine, bits, stock, rivets: skill `pcb-lab-config`) or fab house (name, layer count, assembly).
- Review: who approves, and the deadline.

Do not continue until the owner answers. An unknown value stays `TBD`. Never invent a part value.

## Plan (owner gate 1)
Write the plan to `docs/plans/YYYY-MM-DD-<board>.md` with `Status: active`:
- requirements
- rails and the power budget from datasheet maximum values
- part choices with reasons (skill `pcb-parts`)
- the connector convention and the pin-order rules
- the check list for each phase (`check-matrix.md`)
- open questions

Apply `lessons.md` when you write the plan. Give the plan to the owner. Do not start the schematic before the owner approves it.

## Environment check (before the first step)
Report each missing item:
- Host: git, make, docker with buildx. No system Python.
- KiCad 10: `make kicad-image` builds `rccar-kicad:local` (`docker/kicad.Dockerfile`). It gives `kicad-cli` and the `pcbnew` Python module.
- Router: the Freerouting image (digest in the Makefile), for `make pcb-route` only.
- Plugin kicad-happy (enable it for the session: `.claude/rules/plugins.md`).
- Optional: `ngspice` (SPICE), `zstd` (to read a Fusion `.f3z`), distributor API keys in user scope. If one is missing, skip the related step and say so in the report.
- The owner has the KiCad 10 GUI. GUI steps are owner steps: Update Symbols from Library, 3D view, 1:1 print.
