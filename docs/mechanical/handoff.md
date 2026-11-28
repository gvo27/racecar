# Handoff: Linux, GitHub, SolidWorks

1. Claude changes a model on the Linux VM and runs `make mech-test` and `make mech-check MODEL=<model>`.
2. Claude opens a PR. CI (`.github/workflows/mechanical.yml`) builds and checks each model again. It uploads the outputs as the run artifact `mech-outputs` (30 days).
3. The owner downloads `mech-outputs` from the Actions run of the PR and imports `<model>.step` in SolidWorks on the Win11 workstation:
   - Units: mm. Keep the STEP coordinates (see `conventions.md`).
   - Check the part names and colors, the fit to the reference envelopes (`ref_*`), and the printability.
   - Write the findings as a PR comment. A change goes back into the Python model, not into SolidWorks.
4. After the owner approves a design, Claude runs `make mech-release MODEL=<model> REV=<rev>`. It copies the checked files to `docs/mechanical/releases/<rev>/`. A release is frozen. A new change makes a new revision.

Generated files stay out of git, except an approved release. Git LFS is not used: one release is a few MB.

## What the owner measures
The car values in the models are `assumed` until the owner measures them. Give each value with the date:
- The four body posts: front to rear and left to right spacing (center to center), post diameter, and post-top height above the ground.
- The battery holder bar (D1) top and the top of its two snap pins, above the ground.
- The top of the tub wall, and the ground clearance setting in use.
- The battery space: length, width, height.
- The camera model, when it is chosen.
- The printer and the filament, when the lab is ready.
