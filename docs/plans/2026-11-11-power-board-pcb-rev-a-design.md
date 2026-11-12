# Power board rev A: schematic to milled-ready PCB (design)

Branch: `schematic` (PR #3). Inputs: `docs/schematics/` (plan, `fab_handoff.md`, `bom.md`, the PR #3 migration comment) and `.claude/rules/schematics.md`.

## Intent

Take the KiCad schematic (40 parts, 21 nets) to a `.kicad_pcb` that the owner can open in KiCad 10, check, and send to MakeraCAM for the Makera Carvera. The agent has no KiCad GUI. All work runs headless through KiCad 10.0.8 (`kicad-cli` and `pcbnew` Python) in the official Docker image. So the PCB is built by a script, then the owner does the visual checks in the GUI.

## Goals

1. A reproducible bootstrap that creates `rc_power_board.kicad_pcb` from the schematic netlist: footprints, nets, net classes (from `rc_power_board.kicad_pro`), board outline, drill/place origin, stackup and custom DRC rules.
2. A first placement by schematic region that follows the PR rules: SMD parts on the bottom (B.Cu), THT parts on top, connectors on the board edge with the wire entry facing out and pin 1 at the same end, a short and wide J1 -> F1 -> D1/C1 -> U1/U2 path, regulator caps at the module pins, C9 at J11, U3/FB1/C6-C8 away from the bucks, H1-H4 at the corners.
3. Routing on B.Cu with the fewest possible rivet vias. The F.Cu GND pour connects to no pads (pad connection: none) and joins bottom GND only through rivet vias. The bottom also gets a GND fill, so the mill removes less copper.
4. Holes that match the assumed bit set (below).
5. A scripted export to `docs/schematics/fab/rev-A/`: Gerbers for F.Cu, B.Cu and Edge.Cuts on the drill/place origin, Excellon drill files in mm with PTH and NPTH in separate files, a DRC report and a 1:1 print PDF.
6. `make` targets for build, DRC and fab export, so the owner and CI run the same commands.
7. The docs are updated in the same change: README, `fab_handoff.md`, `bom.md`, `design_overview.md`, the plan, and `.claude/rules/schematics.md` where they change.

## Non-goals

- Fab-house revisions, solder mask, silkscreen and assembly files.
- Reverse-polarity protection (owner decision 2026-11-11: skip; no Q1/R4).
- Buying parts.
- A KiCad GUI on this host.
- "Update Symbols from Library" on the schematic. The 3 ERC warnings (`lib_symbol_mismatch`, D2-D4) stay an owner GUI step.

## Anti-goals (a failure even if it "works")

- A board that DRC calls connected but that is open on an unplated board: no top-side THT pad connections, and no top traces on pins under XH shrouds, terminal blocks, the F1 holder or the U1 header.
- Invented part values or dimensions. Unknown means `TBD`.
- Saving any project file in a format older than KiCad 10, or editing a connection only in the PCB (all connection changes go through the schematic).
- Claiming DRC or ERC passed without kicad-cli 10 output.

## Decided

| Item | Decision | Source |
| --- | --- | --- |
| Reverse polarity | Not on rev A | owner, 2026-11-11 |
| U3 | Keep the stock `SOT-23-5` footprint; add the `U3_fine` custom rule (clearance 0.3 mm on U3); mill that area with the 60°/0.1 mm V-bit | owner, 2026-11-11 |
| U2 | A Sonnet worker proposes candidates against the constraints; the owner picks one. The footprint goes in a project library `rc_power.pretty`, built from the maker's dimension drawing. If the module has pin pairs, the `REG_MODULE` symbol changes too | owner, 2026-11-11 |
| Drill bits | Assume 4 drill sizes: **0.8, 1.0, 1.2, 1.5 mm**. Larger holes are helical-milled with an end mill. Marked "assumed, lab tech to confirm" | owner said assume 4 common sizes; sizes are agent's call |
| Tooling | `kicad/kicad:10.0.8` by digest, from a `docker/kicad.Dockerfile` (repo rule: deps in a Dockerfile, pinned) | agent's call |

## Agent's calls (owner to check)

- **Hole snapping.** Each hole goes up to the next bit size; then pads grow, if needed, to keep the 0.45 mm annular ring. XH 0.95 -> 1.0; U1 header and C1 1.0 -> 1.0; C9 0.8 -> 0.8; MKDS J6/J7 1.3 -> 1.5; F1 pins 1.4 -> 1.5. The changes are made in the board's footprint copies, not in the stock libraries.
- **Rivet via.** The EasyContac 0.8 rivet (1.0 mm OD) needs a 1.1 mm hole and there is no 1.1 mm bit in the set, so the via becomes **1.2 mm drill / 2.1 mm pad** (annular 0.45). This changes the via size in `rc_power_board.kicad_pro` and the docs. Risk: the rivet sits loose by about 0.1 mm before soldering.
- **Milled holes (> 1.5 mm):** J1 wire pads, H1-H4 (3.2 mm) and the F1 2.4 mm NPTH peg.
- **Outline:** 66 x 140 mm, centred on the 76.2 x 152.4 mm stock (the docs propose "at most about 66 x 140", TBD). Dowel holes are added in MakeraCAM, outside the outline.
- **Stackup:** 2 layers, 0.070 mm copper, 1.57 mm total.
- **Routing engine:** Freerouting (open source, active) from its official image pinned by digest. KiCad exports Specctra DSN, Freerouting routes B.Cu only, and the script imports the SES. HighCurrent nets (`VBAT_RAW`, `VBAT`, GND) are routed as B.Cu zones or 6 mm tracks, not by the autorouter. If Freerouting cannot finish on one layer, the script lets it place vias (rivets) and reports the count; the goal is about 20 or fewer.
- **Stop condition:** if routing cannot reach 0 unrouted nets with DRC clean (apart from documented exceptions), deliver the placed and partly routed board with the DRC report, and stop there.

## Builder-check answers

- **Footprints:** the schematic footprint fields are authoritative (all 39 assigned footprints exist in the KiCad 10 libraries). Only U2 is missing. Footprint changes go into the schematic first.
- **THT pads:** each THT pad is soldered and connected on B.Cu only. Its F.Cu ring stays as copper but connects to nothing: no F.Cu tracks, and the F.Cu GND zone uses pad connection "none". The script check tests for F.Cu tracks or zone fill that touch THT pads.
- **Current:** HighCurrent copper (`VBAT_RAW`, `VBAT`, GND) is sized for F1's rating, about 16.5 A, per the IPC-2221 table in `fab_handoff.md` (2 oz). 6 mm is the minimum width; B.Cu zones may be wider.
- **Rivet count:** about 20 is a target, not a limit. More rivets are accepted, but the report must give the count. DRC pass = 0 errors and 0 unconnected; `U3_fine` is a rule, not an exception. Every warning goes in the report.
- **Outline:** 66 x 140 mm is the first try. If placement does not fit, the outline can grow up to 70 x 146 mm (3 mm clamp margin per side on the stock); report this.
- **U2 before the owner picks:** the board is built, routed and exported with the placeholder. The fab folder then gets a `NOT_FOR_MILLING.txt` that names U2 as the blocker. When the owner picks the part, the footprint is replaced, the board is re-routed locally and the files are re-exported.
- **Machine limits:** the `rc_power_board.kicad_pro` DRC values (clearance 0.4, track 0.5, annular 0.45, min hole 0.8) are the machine rules. Isolation milling happens on both sides with a dowel flip; there are no plated holes.
- **Mirroring and origin:** nothing is mirrored in KiCad (MakeraCAM mirrors the bottom for the flip). The drill/place origin is the outline's lower-left corner.
- **Digests:** commit both image digests (KiCad and Freerouting) in Dockerfiles or the Makefile; no `:latest`.
- **Pololu D24VxF5 drawing** (covers #2865 and #2866, read 2026-11-11): board 40.6 x 20.3 x 1.57 mm, 6.1 mm parts height, 12 x 1.02 mm holes on a 0.1" grid, larger holes for 5 mm terminal blocks (diameter not given: TBD), 4 x 2.18 mm mounting holes 15.2 x 35.6 mm apart. The pin-to-net map must come from the drawing plus the silkscreen labels (GND/VOUT at one end, GND/VIN at the other, VOUT/FB/PG/ENABLE along one side); confirm before building the footprint.

## Open (stays TBD, not blocking the bootstrap)

- Lab tech confirms the bit list, rivet hole and dowel size.
- U2 part choice (blocks the final U2 footprint; until then a `PinHeader_1x04_P2.54mm_Vertical` placeholder, marked as a placeholder). Worker finding 2026-11-11: the proposed D24V60F5 (Pololu #2865) is discontinued; its listed replacement D24V90F5 (#2866, 5-38 V in, up to 9 A, 40.6 x 20.3 x 7.6 mm, US$36.82, rationed) is the lead candidate. Its pin layout, hole size, dropout at 5 A and ripple are not verified (no dimension drawing read): TBD. The placement reserves a 40.6 x 20.3 mm keep-out for U2.
- J1 pad size, all `TBD` part values.

## Verification

- `kicad-cli sch erc`: 0 errors (the 3 known LED warnings allowed until the owner's GUI update).
- `kicad-cli pcb drc --schematic-parity --severity-all`: 0 errors, 0 unconnected, parity clean; every warning listed in the report.
- Netlist from the PCB vs the schematic: same 40 footprints (H1-H4 and TP1-TP3 included) and 21 nets.
- Every drill in the Excellon files is in {0.8, 1.0, 1.2, 1.5} mm, or is listed as a milled hole.
- No F.Cu copper on any THT pad of J3-J9, J11-J14, F1 or U1 (script check).
- Owner, in the GUI (user-run): 3D view (pin 1, fuse access, no collisions), 1:1 paper print with real parts, then MakeraCAM import.
