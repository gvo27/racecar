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
- The motor plate (frame rev2): the center of its 4-hole M3 pattern from the front body posts (front to rear, and left to right from the car center line), and the height of the plate top above the ground. The anchor height comes from it. The DC motor barrel (a cylinder along the car, beside the drive shaft): how high its top rises above the mount points, and the length and width of the part above the plate, relative to the 4 holes (`[motor_barrel]`: now 24 x 12 mm, 20 mm high, assumed). The front end of the barrel is the critical value: the U front of the anchor is only 1 mm in front of the front hole line. The owner bound "at least 1 cm clearance on the longitudinal sides" gives a width of 4 mm or less, so the 12 mm envelope is conservative. Measure the temperature of the motor plate (degC) after a hard run: the anchor material must stay below its `heat_limit` (`print.toml`).
- The battery holder bar (D1) top and the top of its two snap pins, above the ground.
- The top of the tub wall, and the ground clearance setting in use.
- The battery space: length, width, height, and its position (center offset to the left of the car center line).
- The wheels: track (hub center to hub center), tyre diameter and width, and the room the front tyres need when they steer.
- The camera model, when it is chosen.
- The build height and the filament of the workshop printer, when the lab is ready.

## Owner steps at assembly
- The rev3 board underside is bare copper with `VBAT_RAW`. Put an insulating sheet (for example polyimide tape or fish paper) between the board and the standoffs and the deck (frame rev1: also the splice bolts). Frame rev2: the sheet must also cover the area above the deck cutout over the motor barrel (debris and heat).
- Frame rev2 anchor: do not print the anchor before the motor plate and the motor barrel are measured (`x`, `y` and `top_z` in `[motor_plate_position]`, and the length, width, height and temperature of the motor barrel in `[motor_barrel]`). The holes must agree with the plate, the latch has almost no tolerance in Z, and the U cutout of the anchor takes a barrel of at most about 12 mm width (1.1 mm gap each side).
- Frame rev2 anchor: screw the anchor to the motor plate with 4 M3 screws before the deck goes on. The barrel top is about 10 mm above the anchor top and 6 mm from each screw axis: use a hex key or a bit with a shaft of at least 17 mm and less than about 10 mm diameter. Each screw goes through the 3 mm floor of the anchor (`anchor_floor` in `mechanical/config/frame_rev2.toml`). Tell Claude how the plate holds a screw (tapped thread, self-tapping into plastic, or a nut under the plate). Select a screw length that does not touch the motor or the gears. The anchor stays on the car.
- Battery swap (frame rev2): pull the two front body clips. Pull the rear edge of the deck up off the snap pin of the anchor. Then lift the deck level up the front posts and off. Swap the battery. To install, lower the deck level down the front posts, then push down on the rear edge of the deck (not on the rev3 board) until the snap pin latches. Put the front clips back. Give each cable from the frame to the chassis (ESC, servo, battery) enough slack to put the frame aside.
- Battery swap (frame rev1): pull the four body clips, lift the frame up the posts and off. The frame lifts from the stay top to the post top (`[body_posts]` in `mechanical/config/hardware.toml`).
- Snap pin: make a test print of the anchor and a deck strip with the slot first. Print the anchor with its bottom on the bed: the prongs then bend across the layers, which is the weak direction. Latch and release it 20 times. Measure or estimate the release force (the estimate is some tens of newtons, not verified). Look for cracks at the prong root. If it is too tight or too loose, report it: the lip and the clearance are design values in `frame_rev2.toml`.
- Heat-set inserts and thread-forming screws: make a test print of one standoff first. The hole sizes in `[fasteners]` are start values.
