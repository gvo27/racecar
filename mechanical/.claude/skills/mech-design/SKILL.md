---
name: mech-design
description: Use when you design, change or review a 3D-printed part or assembly in mechanical/ - a new model, a parameter, a mount for a board or a sensor, a chassis interface, a check or an export - and before a claim that a part is correct, fits, prints or is ready for the SolidWorks review. Gives the workflow (intake, test first, model, checks, previews, independent review, handoff), the check matrix, the build123d notes and the lessons list. Keywords - build123d, CAD, STEP, STL, 3D print, mount, frame, clearance, interference, SolidWorks.
---

# Mechanical design (build123d)

The main session implements. The agent `mech-reviewer` reviews with a fresh context after each model change. The owner reviews the STEP file in SolidWorks and approves a release. This follows the user-scope engineering workflow: implement, verify, independent review, fix, report.

Project rules: `.claude/rules/mechanical.md`. Conventions (units, frame, labels, check ids): `docs/mechanical/conventions.md`. Handoff: `docs/mechanical/handoff.md`.

## References (read when the step starts)
| File | Use |
| --- | --- |
| `references/check-matrix.md` | Each check, its pass condition, what it cannot find, and the manual review questions |
| `references/build123d-notes.md` | API notes at the pinned version, the doc sources, the traps found on this project |
| `references/lessons.md` | Lessons from errors on this project. Read before a design step and before a review |

## Step 0: intake
1. Find the facts that the part needs: the board files, `docs/datasheets/`, `docs/hardware.md`, the fact files in `mechanical/config/` (`print.toml`, `hardware.toml`).
2. For each missing fact, add an `assumed` value with a source that names who must measure it. Never invent a confirmed value.
3. Write the acceptance criteria of the model before the geometry: holes (position, diameter), clearances, envelopes that must stay free, maximum height, bed fit.

## Workflow
1. **Test first.** Add the model test in `mechanical/tests/` and the `acceptance()` criteria in the model module. Run `make mech-test`. The new test must fail.
2. **Parameters.** Put each design choice in `mechanical/config/<model>.toml`. Put each fact in a fact file with `status` and `source`. Code reads both. No dimension constants in code.
3. **Model.** One module in `mechanical/src/rccar_mech/models/` with `build(cfg)`, `acceptance(asm, cfg)` and `STL_TOLERANCE`. Make each feature a function that returns a solid. Give each printed part a unique label and a color. Give each reference envelope a label with the `ref_` prefix.
4. **Modules, not branches.** A part that can change its type (for example the chassis interface) is a function per type with the same return contract. The model selects the type from the design file.
5. **Checks.** Run `make mech-check MODEL=<model>`. Fix each error in the geometry. Do not change a check, a tolerance or a limit to pass.
6. **Look at it.** Open `build/mech/<model>/<model>_iso.png` and the SVG views with the Read tool. A check that passes on a wrong shape is the most common failure. Compare the picture with the intent.
7. **Diff.** For a change of an existing model, run `make mech-diff A=<old.step> B=<new.step>`. Every change in the diff must be intended.
8. **Review.** Send the model to the agent `mech-reviewer`. Fix the findings. Then run the steps 5 to 7 again.
9. **Handoff.** Open the PR. Attach the iso PNG to the PR body. The owner downloads the CI artifact mech-outputs and reviews the STEP file in SolidWorks. After the owner approves: `make mech-release MODEL=<model> REV=<rev>`.

## Rules
- Exact selection. When code selects a face, an edge or a hole, assert the count of the result. An empty or a double selection is an error, not a default.
- Copy a part before you put it into a second Compound. A new Compound takes the part out of its parent assembly (`references/lessons.md`).
- Check the validity before each export. The CLI runs MECH-VALID, MECH-LABEL and the STEP round trip on every check.
- Keep the frame of the car: X forward, Y left, Z up, origin at the body-post center on the ground.
- For a printed hole that takes a screw or a pin, add `hole_comp` of `print.toml` to the diameter. Do not add it to a clearance envelope.
- Prefer heat-set inserts or through bolts to threads in plastic. Prefer self-tapping screws into plastic only when the chassis needs them.

## Report
1. Owner questions: each `assumed` table that changes a result, and what to measure.
2. The check results of `make mech-check` (errors, warnings), mass, center-of-gravity height, top height.
3. The iso PNG path, and what the owner must look at in SolidWorks.
4. Never write "fits" or "prints well" without a measurement or a print from the owner.

## Verify
- `make mech-test`: lint and tests. The new model test passes.
- `make mech-check MODEL=<model>`: give the error and warning counts from the output.
- `make checks`: the repo tests (skill, agent and link checks).
- Claim a result only with the command output from this session. A check that you did not run is "not run".
