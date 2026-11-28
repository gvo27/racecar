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
- The four body posts: front to rear and left to right spacing (center to center), post diameter, the height of the stay top where each post starts, the post-top height, and the height of each body-clip hole above the ground. A clip hole must sit just above the deck top, or the deck can lift.
- The battery holder bar (D1) top and the top of its two snap pins, above the ground.
- The top of the tub wall, and the ground clearance setting in use.
- The battery space: length, width, height, and its position (center offset to the left of the car center line).
- The wheels: track (hub center to hub center), tyre diameter and width, and the room the front tyres need when they steer.
- The camera model, when it is chosen.
- The printer and the filament, when the lab is ready.

## Owner steps at assembly
- The rev3 board underside is bare copper with `VBAT_RAW`. Put an insulating sheet (for example polyimide tape or fish paper) between the board and the standoffs and splice bolts.
- Battery swap: pull the four body clips, lift the frame up the posts and off, swap the battery. The frame lifts from the stay top to the post top (`[body_posts]` in `mechanical/config/hardware.toml`). Give each cable from the frame to the chassis (ESC, servo, battery) enough slack for that lift and to put the frame aside.
- Heat-set inserts and thread-forming screws: make a test print of one standoff first. The hole sizes in `[fasteners]` are start values.
