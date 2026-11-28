---
paths:
  - "mechanical/**"
  - "docs/mechanical/**"
---

# Mechanical parts (build123d, 3D printing)

Workflow: skill `mech-design` (`mechanical/.claude/skills/mech-design/SKILL.md`). Review: agent `mech-reviewer`. Facts and conventions (units, frame, labels, check ids, handoff): `docs/mechanical/conventions.md`, `docs/mechanical/handoff.md`.

## Sources and generated files
- The Python model is the source. SolidWorks is for review only. A change found in SolidWorks goes back into the model.
- Run the tools only through `make cad-image` and the `make mech-*` targets. Never use the host python for them.
- Put each fact in a fact file (`print.toml`, `hardware.toml`) with `status` and `source`. Put each design choice in `mechanical/config/<model>.toml`. Never write a number of a part, a board or the chassis as a constant in code.
- Read the rev3 board geometry from `pcb/src/rc_power_board.kicad_pcb`. Never copy its hole positions.
- Never invent a dimension. An unknown value is `assumed`, with a source that says who must measure it.
- Do not commit generated files (`build/mech/`). Only `make mech-release` writes the files of an approved release.
- Never change a released file (folder `releases/` of `docs/mechanical/`). A change makes a new revision.

## Checks
- Never weaken a check, a tolerance or an acceptance criterion to make a model pass. Find the cause in the geometry. A limit change needs a statement of the owner.
- Each model has acceptance criteria in its `acceptance()` and a test in `mechanical/tests/`. Write the failing test first.
- Each printed part keeps a unique label. A reference envelope (not printed) has the `ref_` prefix.

## Design invariants
- The frame releases without tools. The battery swap must not need a screwdriver.
- No printed part or `ref_` envelope may block the battery lift-out path.
- Keep the chassis interface a replaceable module (body posts now, screw pads later). Other parts must not depend on its type.
- Keep the mass low and the parts low on the chassis. Report the center-of-gravity height and the top height in each review.
- The rev3 board underside is bare copper with `VBAT_RAW`. Keep its standoff and the insulation note in the design.

## Report
- Never claim that a part fits the car or prints well without a measurement or a print from the owner. Write "passes the checks with the assumed values" and list the `assumed` tables.
