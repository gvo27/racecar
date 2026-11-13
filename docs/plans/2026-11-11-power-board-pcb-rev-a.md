# Power board rev A PCB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DRC-clean, routed `rc_power_board.kicad_pcb` for owner review, from the existing schematic with U2 = Pololu D24V90F5.

**Scope (owner, 2026-11-11):** a valid KiCad PCB for review only. Gerber/drill export, CAM and machine setup are out of scope: the lab tech will give separate instructions for the path from the KiCad file to the milling machine. The milling rules already in the project (clearance, hole sizes, B.Cu routing, unplated holes) still apply to the board, so that it does not need a redesign later.

**Architecture:** All KiCad work runs headless in the pinned KiCad 10.0.8 image (`kicad-cli` plus `pcbnew` Python). Python scripts in `docs/schematics/tools/` build the board, route it through Freerouting (pinned image, Specctra DSN/SES), check it, and plot review files. `make` targets wrap each step. Tests are stdlib `unittest` files that run with the image's `python3`. After the bootstrap, the `.kicad_pcb` is the owner's file: the scripts are for the first build and for re-checks, not a generator the owner must keep using.

**Tech Stack:** KiCad 10.0.8 (`kicad/kicad:10.0.8@sha256:3f4a01786dfbe803a65f345c3342b765db9add913f5e9448f8356793714ddc34`), Freerouting 2.5.0 (`ghcr.io/freerouting/freerouting:2.5.0`, pin by digest at Task 2), GNU make, Docker.

**Spec:** `docs/plans/2026-11-11-power-board-pcb-rev-a-design.md`

**Execution and review (owner, 2026-11-11):**
1. A Sonnet agent builds the baseline board: Tasks 2–7 (Step 4b excluded). It commits locally and does not push.
2. The main session (Opus) reviews the baseline and reports to the owner.
3. After the owner confirms, a Fable agent does the final review with full context. The main session fixes the findings, then pushes and comments on PR #3.

## Global Constraints

- KiCad 10 format only; never save a project file in an older format.
- No host installs: tools run in Docker images pinned by digest; no `:latest`.
- No invented values: unknown => `TBD`. Assumed values say "assumed".
- Assumed drill set: 0.8, 1.0, 1.2, 1.5 mm. Holes > 1.5 mm are milled.
- Via (EasyContac 0.8 rivet): 1.2 mm drill / 2.1 mm pad, annular ≥ 0.45 mm.
- DRC minimums: clearance 0.4, track 0.5, annular 0.45, min hole 0.8 mm. `U3_fine`: clearance 0.3 mm on U3 only.
- Net classes: HighCurrent (`*VBAT*`, GND) 6.0 mm; Power5A (`+5V_CPU`, `+5V_SENS`) 1.6; Power3A (`*+6V_BEC`) 1.0; Default 0.5.
- SMD on B.Cu, THT on F.Cu (top), routing on B.Cu, F.Cu GND zone with pad connection none.
- Outline 66 x 140 mm (may grow to 70 x 146 mm); drill/place origin = outline lower-left.
- Project text in STE-flavored English (`.claude/rules/writing.md`).

## Review Focus

1. A THT pad that DRC calls connected only through F.Cu copper (open on an unplated board): `check_board.py` fails on any F.Cu track/zone touching a THT pad. Test in Task 5.
2. A drill outside the bit set that is not in the milled list: `check_board.py` lists every hole. Test in Task 5.
3. U2 pin map mirrored (footprint drawn as the bottom view): the footprint test pins VIN at the end nearest ENABLE and the signal row on the same long edge as GND. Test in Task 4.
4. High-current nets autorouted at Default width: the check asserts every `VBAT_RAW`/`VBAT`/GND track is ≥ 6.0 mm. Test in Task 6.
5. Re-running the build over an owner-edited board destroys the edits: `build_pcb.py` refuses to overwrite an existing `.kicad_pcb` without `--force`. Test in Task 5.

---

### Task 1: D24V90F5 documentation (owner request 2026-11-11)

**Files:**
- Create: `docs/datasheets/regulator_pololu_d24v90f5.md`
- Create: `docs/datasheets/pololu_d24vxf5_dimensions.pdf`, `docs/datasheets/pololu_d24v90f5_dropout.png`, `docs/datasheets/pololu_d24v90f5_max_current.png`, `docs/datasheets/pololu_d24v90f5_efficiency.png` (archived from pololu.com)
- Modify: `docs/schematics/bom.md`, `docs/schematics/README.md`, `docs/schematics/design_overview.md`, `docs/schematics/fab_handoff.md`, `docs/schematics/power_board_plan.md`, `.claude/rules/schematics.md` (U2 = D24V90F5 assumed, D24V60F5 discontinued, dropout risk)

- [ ] **Step 1:** Write the datasheet doc in the `rangefinder_lidar_lite_v4.md` style: sources with URLs, identity, specs table (quoted values), pinout table in footprint (top-view) coordinates, dropout risk (about 1.0 V at 5 A => about 6.0 V in for 5 V out; at the 6.0 V cutoff the Mapper's 4.8 V floor is at risk: bench check), unverified items (terminal-hole diameter, ripple).
- [ ] **Step 2:** Update the U2 rows and notes in the docs listed above. `power_board_plan.md` is an export of a live doc: change it, and note in the PR that the live doc needs the same change.
- [ ] **Step 3:** Verify: `grep -rn D24V60F5 docs .claude` shows only "discontinued" history lines.
- [ ] **Step 4:** Commit `docs: U2 = Pololu D24V90F5 (assumed), archive its drawing and graphs`.

### Task 2: KiCad and Freerouting tooling

**Files:**
- Create: `docker/kicad.Dockerfile` (`FROM kicad/kicad:10.0.8@sha256:3f4a…ddc34`; nothing else)
- Modify: `Makefile` (variables `KICAD_IMAGE ?= rccar-kicad:local`, `FREEROUTING_IMAGE := ghcr.io/freerouting/freerouting:2.5.0@sha256:<digest>`, `SCH_DIR := docs/schematics`; targets `kicad-image`, `erc`, `pcb-build`, `pcb-route`, `pcb-check`, `pcb-review`, `pcb-test`)
- Modify: `.claude/rules/dependencies.md` (toolchain image entry), `.claude/CLAUDE.md` (`make:` list)

**Interfaces:** Produces `KICAD_RUN = docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v $(CURDIR):$(CURDIR) -w $(CURDIR)/$(SCH_DIR) $(KICAD_IMAGE)`; every later target uses it.

- [ ] **Step 1:** Run `make erc` before the target exists. Expected: "No rule to make target".
- [ ] **Step 2:** Add the Dockerfile and targets. `erc` runs `kicad-cli sch erc --format json --severity-all --exit-code-violations` and passes when there are 0 errors (warnings are printed).
- [ ] **Step 3:** Run `make kicad-image erc`. Expected: 0 errors, 3 `lib_symbol_mismatch` warnings (D2–D4). The stock lib tables come from `/usr/share/kicad/template`, which the image's KiCad finds without a user config. If it doesn't, copy them into a `-e XDG_CONFIG_HOME` dir in the target.
- [ ] **Step 4:** Commit `build: pinned KiCad 10 + Freerouting images, make erc/pcb-* targets`.

### Task 3: Milling check (project skill `pcb-milling-check`)

The skill entry `.claude/skills/pcb-milling-check/SKILL.md` exists (written by the main session). It defines the rule ids, the severities, the exit codes and the agent rules. This task builds what the skill runs. DRC-clean does not mean CNC-millable.

**Files:**
- Create: `docs/schematics/milling.toml`, `docs/schematics/milling_waivers.toml` (empty list), `docs/schematics/tools/milling_check.py`, `docs/schematics/tools/test_milling_check.py`
- Modify: `Makefile` (target `pcb-mill-check`; add the tests to `pcb-test`)

**`milling.toml`** (each value carries `status = "assumed"` or `"confirmed"` and a `source`):
- copper thickness 0.070 mm (Kepro P22-365G, 2 oz; confirmed, `fab_handoff.md`)
- isolation bits: 30°, tip 0.2 mm; 60°, tip 0.1 mm (Makera PCB pack; confirmed)
- cut depth 0.10 to 0.15 mm (`fab_handoff.md`; assumed); depth error ±0.05 mm with probe auto-levelling (assumed)
- drill set 0.8, 1.0, 1.2, 1.5 mm (owner: assume 4 common sizes; assumed); smallest end mill 1.0 mm (assumed); a milled hole must be > 1.5 mm
- rivet via 1.2 mm drill / 2.1 mm pad; annular min 0.45 mm; track min 0.5 mm; edge clearance 0.5 mm (`min_copper_edge_clearance` in `.kicad_pro`)

**Interfaces:** `load_limits(path: str) -> Limits`; `cut_width(tip: float, angle_deg: float, depth: float) -> float` (`tip + 2 * depth * tan(angle / 2)`); `check(board: pcbnew.BOARD, limits: Limits) -> list[Finding]`, `Finding = (rule_id: str, severity: "error"|"warning", where: str, value: float|None, limit: float|None, message: str)`; CLI `milling_check.py <board> --limits <toml> --json <out>`, exit 0/1/2. Task 5's `check_board.py` calls `check()` and fails on any error.

**Numbers to pin in tests:** worst-case depth = 0.15 + 0.05 = 0.20 mm. `cut_width(0.2, 30, 0.20)` = 0.307 mm; `cut_width(0.1, 60, 0.20)` = 0.331 mm. MILL-GAP: a gap is an error when it is < the narrowest bit's cut width at worst-case depth (0.307 mm); MILL-GAP-BIT (warning): gaps where only some bits fit, listing the bits that fit (here, gaps from 0.307 to < 0.331 mm fit only the 30° bit). MILL-DEPTH: 0.10 - 0.05 = 0.05 mm < 0.070 mm => **error with the assumed limits.** Do not hide it: report it to the owner as a finding about the assumed depth range (the min depth must be at least 0.12 mm with ±0.05 error).

- [ ] **Step 1:** Write `test_milling_check.py` (stdlib `unittest`, image `python3`): the `cut_width` values above; a via inside an F-side footprint courtyard => MILL-RIVET-ACCESS error; a waiver in a temp `milling_waivers.toml` moves its finding to the waived group (and a waiver for MILL-FCU-THT is rejected); a synthetic board made in the test with `pcbnew`: two tracks of different nets 0.30 mm apart => MILL-GAP error; 0.32 mm => MILL-GAP-BIT warning (30° only); 0.45 mm => none; a 1.1 mm hole => MILL-DRILL error; a 2.4 mm hole => none (milled); an F.Cu track on a THT pad => MILL-FCU-THT error; a 2.0/1.1 via => MILL-VIA error. `load_limits` rejects a value with no `status`.
- [ ] **Step 2:** Run `make pcb-test`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement. For gaps, use the KiCad shape API (`GetEffectiveShape()` / `SHAPE_POLY_SET` distance) per copper layer, between items of different nets, pads in one footprint included.
- [ ] **Step 4:** Run `make pcb-test`. Expected: PASS.
- [ ] **Step 5:** Commit `tools: pcb milling check (V-bit width, drills, unplated rules)`.

### Task 4: U2 footprint and schematic assignment

**Files:**
- Create: `docs/schematics/rc_power.pretty/Pololu_D24VxF5.kicad_mod`, `docs/schematics/fp-lib-table` (`rc_power` -> `${KIPRJMOD}/rc_power.pretty`)
- Create: `docs/schematics/tools/test_footprint.py`
- Modify: `docs/schematics/rc_power_board.kicad_sch` (U2 Value `Pololu D24V90F5 (assumed)`, Footprint `rc_power:Pololu_D24VxF5`), then run `kicad-cli sch upgrade` so the file is KiCad 10 format

**Footprint (top view, origin = module centre, X along the 40.6 mm length, VIN end at -X):** from the Pololu drawing, converted to module-centre coordinates. Pads are THT circles 2.0 mm, drill 1.0 mm (1.02 snapped to the bit set). Pad numbers follow the `REG_MODULE` symbol: 1 VIN, 2 GND, 3 VOUT, 4 EN. FB and PG pads have no number (no net).

| Pad | Net | X (mm) | Y (mm) |
| --- | --- | --- | --- |
| 2 | GND (input end) | -15.22 | -3.82, -1.28 |
| 1 | VIN | -15.22 | +1.26, +3.80 |
| 2 | GND (output end) | +15.22 | -3.82, -1.28 |
| 3 | VOUT | +15.22 | +1.26, +3.80 |
| 4 | ENABLE | -7.60 | -8.88 |
| (PG) | — | -5.06 | -8.88 |
| (FB) | — | -2.52 | -8.88 |
| 3 | VOUT (signal) | +0.02 | -8.88 |

Fab layer: 40.6 x 20.3 mm outline. Courtyard: outline + 0.5 mm. The terminal-block holes and the four M2 holes are not in the footprint (header pins carry the module; terminal-hole diameter TBD).

- [ ] **Step 1:** Write `test_footprint.py`: loads the footprint with `pcbnew.FootprintLoad`; asserts 12 pads; pad counts per number {1:2, 2:4, 3:3, 4:1, "":2}; all drills 1.0 mm; VIN pads have X < 0; the ENABLE pad has X < 0 and Y < 0 (same long edge as the first GND pair, at the VIN end); pad-to-pad clearance ≥ 0.4 mm.
- [ ] **Step 2:** Run `make pcb-test`. Expected: FAIL (file not found).
- [ ] **Step 3:** Write the footprint, the fp-lib-table and the schematic change; run `sch upgrade`.
- [ ] **Step 4:** Run `make pcb-test erc`. Expected: the tests pass; ERC 0 errors. The netlist has 40 components, 21 nets, U2 footprint set.
- [ ] **Step 5:** Commit `schematic: U2 footprint Pololu_D24VxF5, KiCad 10 format`.

### Task 5: Board bootstrap and checks

**Files:**
- Create: `docs/schematics/tools/build_pcb.py` (`main(argv) -> int`; `--force`), `docs/schematics/tools/placement.py` (table `PLACEMENT: dict[str, tuple[float, float, float, str]]` = ref -> x, y, rotation, layer `"F"`/`"B"`, in mm from the outline's lower-left corner), `docs/schematics/tools/check_board.py` (`check(board) -> list[str]` returns the problems; CLI exits 1 if there are any), `docs/schematics/tools/test_board.py`, `docs/schematics/rc_power_board.kicad_dru` (`U3_fine`)
- Modify: `docs/schematics/rc_power_board.kicad_pro` (via 2.1 / 1.2 mm in every net class)

**Approach:** `build_pcb.py` exports the netlist with `kicad-cli`, then makes the board with `pcbnew`: load each footprint from the stock/project libraries, set ref, value and pad nets; outline 66 x 140 mm on Edge.Cuts; drill/place origin at the lower-left corner; 2-layer stackup with 0.070 mm copper and 1.57 mm total; apply `PLACEMENT`; snap THT drills to the next size in {0.8, 1.0, 1.2, 1.5}, growing the pad to keep a 0.45 mm annular ring (holes > 1.5 mm stay as milled); F.Cu GND zone over the board, clearance 0.4, min width 0.5, pad connection none; B.Cu GND zone, pad connection solid (thermal reliefs off: the mill cuts them poorly). Placement follows the spec's goal 2: input chain J1, F1, D1, C1 on one short end; U1 and U2 next, each with its caps; connectors on the two long edges, wire entry outward, pin 1 toward the input end; U3, FB1, C6–C8 at the far end from the bucks; H1–H4 at 3.5 mm from the corners.

- [ ] **Step 1:** Write `test_board.py`: build into a temp dir, then assert 40 footprints (H1–H4 and TP1–TP3 included) and 21 nets; every SMD footprint on B.Cu and every THT one on F.Cu; the outline bbox is ≤ 70 x 146 mm; every footprint courtyard is inside the outline and no two courtyards overlap; `check_board()` returns []; a second run without `--force` exits non-zero and leaves the file unchanged.
- [ ] **Step 2:** Run `make pcb-test`. Expected: FAIL.
- [ ] **Step 3:** Implement `build_pcb.py`, `placement.py`, the `.kicad_dru` and the `.kicad_pro` via change. `check_board()` reports: F.Cu tracks or F.Cu zone fill touching a THT pad; any drill not in the bit set and not listed in `MILLED_HOLES`; via drill ≠ 1.2 or pad ≠ 2.1; HighCurrent tracks narrower than 6.0 mm.
- [ ] **Step 4:** Run `make pcb-build pcb-test`. Expected: PASS. Render `kicad-cli pcb export svg` (F.Cu, B.Cu, Edge.Cuts, F.Fab) and look at it for placement sanity.
- [ ] **Step 5:** Commit `pcb: bootstrap rev A board (placement, outline, zones, rules)`.

### Task 6: Routing

**Files:**
- Create: `docs/schematics/tools/route_pcb.py` (`main(argv) -> int`: export DSN, run the Freerouting image, import SES, refill zones, save)
- Modify: `docs/schematics/tools/test_board.py`

**Approach:** Route in priority order: HighCurrent first (scripted 6 mm tracks/zones), then Power5A, Power3A, then signals (I2C_SDA/I2C_SCL together). If an area gets tangled, rip up and re-route that whole area, or re-place parts there, rather than add rivets. Before the DSN export, set F.Cu to "not routable" in the DSN (only B.Cu is a signal layer). Route `VBAT_RAW` and `VBAT` by hand in the script as 6.0 mm B.Cu tracks along the input chain (pad-to-pad on the placement), and let the B.Cu GND zone carry GND; Freerouting routes the rest, with net-class widths from the DSN. Allow vias only if B.Cu-only routing can't finish; then each via is a rivet and the count goes in the report.

- [ ] **Step 1:** Add tests: `kicad-cli pcb drc --schematic-parity --severity-all --format json` gives 0 errors and 0 unconnected items; `check_board()` is [] (milling check: 0 unwaived errors); every `VBAT_RAW`/`VBAT` track is ≥ 6.0 mm; the via count is printed.
- [ ] **Step 2:** Run `make pcb-route pcb-test`, then iterate on placement (Task 5 table) until it passes. Stop condition (spec): if it can't reach 0 unrouted with DRC clean, commit the best board with the DRC report and stop.
- [ ] **Step 3:** Commit `pcb: route rev A (B.Cu, N rivet vias)`.

### Task 7: Review package and docs

**Files:**
- Create: `docs/schematics/tools/review_plots.py` (`main(argv) -> int`), `docs/schematics/review/` (`drc.json`, `rc_power_board_layers.pdf` with F.Cu, B.Cu, Edge.Cuts, F.Fab, B.Fab, `rc_power_board_1to1.pdf` at scale 1 for the paper check, `README.md` with the via count, the assumptions and the owner GUI checks)
- Modify: `docs/schematics/README.md`, `fab_handoff.md` (via size, assumed bit set, hole list from the board, make targets; Gerber/CAM steps marked "pending lab tech instructions"), `.claude/rules/schematics.md` (via 2.1/1.2, bit set, scripts, make targets), `.claude/CLAUDE.md` (`next:` / `make:`)

No Gerbers, drill files or CAM files in this plan (scope above).

- [ ] **Step 1:** Add a test: `make pcb-review` writes the files above; `drc.json` has 0 errors and 0 unconnected items.
- [ ] **Step 2:** Run `make pcb-review pcb-test`. Expected: PASS.
- [ ] **Step 3:** Update the docs; run the STE lint on the changed prose.
- [ ] **Step 4:** Run `make pcb-mill-check` and the kicad-happy `kicad` skill (PCB review) and `emc` skill on the board. Treat their findings as claims: verify each against the board, then fix it or list it in `review/README.md`.
- [ ] **Step 4b:** Review (not the builder): the main session (Opus) reviews and reports to the owner. After the owner confirms, a Fable agent does the final review. See "Execution and review" above.
- [ ] **Step 5:** Commit `pcb: rev A review package and docs`, push to `schematic`, comment on PR #3 (owner GUI checks: Update Symbols, 3D view, 1:1 print, U2 footprint vs the real module).

### Task 7b: Copper width along the current paths (Opus review, 2026-11-11)

The baseline board (e0ba889) passes DRC, ERC and the milling check, but these checks do not measure the copper width along a current path. An opening test (deflate then inflate the B.Cu copper of one net by w/2, then check that the pads stay in one piece) found:
- U1 GND (pins 7–10, C2, C4) is in a pocket between the `+5V_CPU` track, the VBAT zone and the U1_PG track. The pocket joins the GND pour through a 0.5–0.6 mm neck. Two MILL-SLIVER warnings near U1 mark this neck.
- J1 GND joins U2 input GND and the J6/J7 GND through 1.2–1.4 mm. The VBAT_RAW/VBAT zones make a wall from the bottom edge up to U2. The U1_PG track (94 mm) and the `+5V_CPU` track cross the board.
- VBAT from F1 to U1 VIN: 2.35 mm neck. `+5V_CPU`: one 1.03 mm segment.
- The U2 signal-row VOUT pad has number "3", so the router adds a 25 mm `+5V_SENS` track to it. Pololu: this pin is "not intended to source much current".
- The F.Cu GND pour joins GND at one rivet only. It does not carry return current.
- `review/README.md` says the GND trunks are at least 6 mm wide. This is not true.

**Files:**
- Modify: `docs/schematics/tools/check_board.py` (new check `path_width(board, net, pads, width_mm) -> list[str]`), `test_board.py`, `rc_power.pretty/Pololu_D24VxF5.kicad_mod` (signal VOUT pad number → "", the same as PG and FB), `test_footprint.py`, `placement.py`, `build_pcb.py`, `route_pcb.py`, `review/README.md`

**Required widths (opening test on B.Cu, the pads in each set stay in one piece; a pad narrower than the opening is measured at its own width: the copper within 2.5 mm of it counts, `STUB_MM` in `check_board.py`):**
| Net | Pads | Width |
| --- | --- | --- |
| GND | J1.2, U2 GND (input end), U1.7–10 | 6.0 mm |
| GND | J6.2, J7.2, U1.7–10 | 1.6 mm |
| GND | U2 GND (output end), J8.2, J9.2, J11.2, C9.2 | 1.6 mm |
| `/VBAT_RAW`, VBAT | J1.1 → F1 → U2.1, U1.5/6 | 6.0 mm (pads narrower than this are measured at their own width) |
| `+5V_CPU`, `+5V_SENS` | all pads of the net | 1.6 mm |

- [x] **Step 1:** Add the tests for the table above and for the U2 pad change. Run `make pcb-test`. Expected: FAIL on the e0ba889 board.
- [x] **Step 2:** Re-lay the power region; do not stack local patches. Make GND a planned B.Cu trunk zone (as VBAT), from J1.2 past U2 and U1. Keep long low-current signals (U1_PG, the PWM nets) out of the path between J1 and the regulators: route them along an edge, or as F.Cu jumpers on rivets. List each new rivet. Fixes go through the scripts (`make pcb-route` routes from scratch).
- [x] **Step 3:** Run `make pcb-build pcb-route pcb-test pcb-check pcb-mill-check pcb-review`. Expected: tests PASS, DRC 0 errors / 0 unconnected / parity clean, 0 unwaived milling errors (MILL-DEPTH stays an owner/lab-tech question).
- [x] **Step 4:** Update `review/README.md` (measured widths, rivet count, removed owner questions). Commit `pcb: GND and power path widths (opening-test check, power region re-lay)`.

**Result (builder, 2026-11-12):** all rows pass. Measured widths and the layout changes are in `review/README.md`. The layout has 3 rivets (one `U1_PG` F.Cu jumper, one pour stitching via). `make pcb-route` runs the router without vias; jumpers are planned in `placement.py` (`JUMPERS`). Deviations: J4, J8, J6, J7 have pin 1 at the top, J1 is turned 180 degrees, J11 and J9 sit 0.25 mm further from the edge (all listed as owner questions).

### Task 7c: D36V50F5 for U1 and U2, real module footprint (2026-11-12)

**Findings (Opus review):** U1 used the generic footprint `PinHeader_2x06_P2.54mm_Vertical`. Its outline covers only the pins. The real module is 25.4 x 25.4 mm with the 12 pins along one edge. At the old U1 position the real body (x 103.7 to 129.1, y 137.1 to 162.5 in board coordinates) covered J6 and J7 and went 3 mm past the right board edge. No check found it: the footprint had no courtyard of the body, and `check_board.py` had no courtyard check.

**Owner decision (2026-11-12):** U1 and U2 are both the Pololu D36V50F5 (#4091). The owner has two modules; the same part on both rails gives a swap spare. The D24V90F5 assumption for U2 is dropped.

**Files:** `rc_power.pretty/Pololu_D36V50Fx.kicad_mod` (new; `Pololu_D24VxF5.kicad_mod` deleted), `tools/test_footprint.py`, `rc_power_board.kicad_sch` (U2 = `rc_power:D36V50F5`), `tools/placement.py`, `tools/check_board.py`, `tools/test_board.py`, `tools/route_pcb.py` (`stub_a` for a jumper), `docs/datasheets/regulator_pololu_d36v50f5.md` and the docs that name U2.

- [x] **Step 1:** Footprint test first (`test_footprint.py`: 12 pad positions and numbers from the drawing, 25.4 mm body on the inner-row side, courtyard covers the body, 3 mounting holes as F.Fab circles only). It failed with no footprint. Then the footprint: THT pads (drill 1.0 mm, pad 1.9 mm), F.Fab body, F.CrtYd body + 0.25 mm, F.SilkS body outline, pin 1 marker. Origin = pad 1, pin edge on the right.
- [x] **Step 2:** Schematic: U2 changed to `rc_power:D36V50F5` with the same nets (VIN pins on `VBAT`, GND pins on GND, VOUT on `+5V_SENS`), no-connect flags on U2 EN, VRP, PG. U1 and U2 use `rc_power:Pololu_D36V50Fx`. BOM fields of U2 and U1 are equal, so `bom.csv` has one row `U1,U2`. ERC: 0 errors.
- [x] **Step 3:** Check first: `check_board.py` `check_courtyards` (F-side courtyard overlap, courtyard past the board edge); two tests fail on the old code, pass after. KiCad DRC already reports `courtyards_overlap` and `pth_inside_courtyard` once the courtyard is real (confirmed: it flagged J1/C1 during this task). It does not report a courtyard past the board edge, so the new check adds that.
- [x] **Step 4:** Re-lay. Both modules side by side, pin row on the north edge (rot 90), so the 6.35 mm of pin row per module is a short wall. `VBAT` is an E-shaped zone (arm plus one prong per module, ending in a pad-width neck at the VIN pads). J1 now has GND on the right so that the 6 mm GND path from J1.2 runs east of the `VBAT` tree to both modules. J6 and J7 are above U1 on the right edge. Layouts that were tried and dropped: modules stacked in one column (the `+5V_SENS` trunk and the `VBAT` spine fence the GND pads), and pin row on the south edge (the pin row is a wall across the GND flow).
- [x] **Step 4b (Opus review, round 1):** the two bodies were 0.72 mm apart (Pololu edge tolerance +-0.3 mm, two 2 W modules). U1 moved 1.8 mm east and the board re-routed. New rule: `check_board.py` `MODULE_GAP_MM` = 1.5 (courtyard gap between two `Pololu_D36V50Fx` footprints), test first in `test_board.py`.
- [x] **Step 5:** `make pcb-build PCB_BUILD_ARGS=--force pcb-route`, then `--sync-fields`, `--sync-zones` for zone fixes. `make pcb-test pcb-check pcb-mill-check pcb-review bom erc`.

**Result (builder, 2026-11-12):** see the commit messages and `review/README.md`. Both module bodies are inside the outline (U2 x 8.0 to 33.4, U1 x 36.0 to 61.4, both y 22.3 to 47.7; body gap 2.6 mm, courtyard gap 2.0 mm). Copper widths: GND 7.41 mm (need 6.0), GND J6/J7 4.07, GND U2 output 1.76, `VBAT_RAW` 6.18, `VBAT` 6.39, `+5V_CPU` 1.99, `+5V_SENS` 1.79. Judgement calls: B-side parts (C2, C4) stay under the module bodies (the module is on the other face of the board; they are clear of the pins); the module mounting holes are not drilled; the left connector GND now joins J1.2 through the U2 GND pads.

### Task 8 (later, separate): KiRI visual diff trial

Owner, 2026-11-11: try leoheck/kiri (tag 1.0.0) with KiCad 10. Do not commit anything until it works with KiCad 10. If the setup is too buggy, drop it and record that in the PR. Work in the scratchpad, in a container based on the pinned KiCad image. Pass = `kiri` makes a schematic and layout diff between two commits of `docs/schematics/` with no errors. Only then propose a pinned CI job (kiri-github-action by SHA, after a read of its permissions).

### Task 9: lab fit and fab outputs (2026-11-13)

**Scope change:** the work is the board plus the fab files. The CAM stays in the lab's Fusion 360 template.

**Findings (Opus, from the lab .f3z):** stock 152.4 x 101.6 mm; 2 dowel holes of 4.191 mm at (3.2766, 3.81) and (149.1234, 3.81) mm; one end mill (3.175 mm); one isolation pass at 0.08 mm with a 0.2 mm tip V-bit; drills 0.9, 1.0 and 1.1 mm; the lab makes holes from the KiCad drill-map DXF. Owner (PR #3, 2026-11-12): the blank is even (depth error 0); drill bits 0.1 to 2.0 mm in 0.1 mm steps; dowel holes always; deliver DXF for F.Cu, B.Cu and Edge.Cuts, and drill files in Excellon and DXF; B.Cu not mirrored. KiCad's native DXF is not contour-safe (drill circles on Edge.Cuts; overlapping pad, track and zone outlines), so the DXF files come from `tools/fab_export.py`.

**Files:** `docs/schematics/example/README.md` (new), `milling.toml`, `tools/milling_check.py`, `tools/placement.py`, `tools/build_pcb.py`, `tools/check_board.py`, `tools/route_pcb.py`, `tools/fab_export.py` (new), `tools/test_fab.py` (new), `fab/` (new, committed outputs), `rc_power_board.kicad_pcb`, `rc_power_board.kicad_pro`, `Makefile` (`pcb-fab`), `fab_handoff.md`, `bom.md`, `bom_offboard.csv`, `review/README.md`.

- [x] **Step 1:** Lab limits (tests first in `test_milling_check.py`): cut depth 0.08 mm, depth error 0, drill set 0.1 to 2.0 mm, end mill 3.175 mm, `milled_hole_min` 3.3 mm (assumed), `[stock]`, `[dowel]`, the lab V-bit with both readings of the taper (0.243 mm and 0.292 mm cut width). MILL-DRILL: a hole is in the drill set or at least 3.3 mm. MILL-DEPTH uses the new values and passes (margin 0.01 mm; the lab tech accepts it, 2026-11-13, and adds a second, deeper pass if necessary).
- [x] **Step 2:** Board fit (tests first in `test_board.py`): `build_pcb.py` reads the drill set from `milling.toml`; new `--sync-drills` (no re-route, zones refilled). H1 to H4, J1 and the F1 peg hole are 3.4 mm bored holes; vias 1.1/2.1 mm; MKDS 1.3 mm, F1 pins 1.4 mm. The F1 peg size is not confirmed (the Littelfuse drawing was not reachable): 3.4 mm is a loose locator hole.
- [x] **Step 3:** Lab frame: `placement.py` has `STOCK`, `DOWELS` and the board-to-lab transform. The board is turned 90 degrees counter-clockwise and centered on the stock (6.2 mm at each end, 17.8 mm at each long side). The dowel holes are about 14 mm from the outline. The stock and the dowels are drawn on `Dwgs.User` for review.
- [x] **Step 4:** `make pcb-fab` writes 5 files to `docs/schematics/fab/` (see `fab/README.md`). `test_fab.py` checks: file set, one layer per DXF, closed loops, no overlap, copper area against pcbnew (0.5 %), copper inside the outline, holes against `kicad-cli pcb export drill`, dowels at (0, 0) and (145.8468, 0), B.Cu not mirrored, committed files current.
- [x] **Step 5:** Docs: `example/README.md`, `fab_handoff.md`, `bom.md`, `bom_offboard.csv`, `review/README.md`, this plan, `.claude/CLAUDE.md`, `.claude/rules/schematics.md`.

**Open (owner / lab tech):** F1 peg size; Fusion taper meaning (per side or included); `milled_hole_min` 3.3 mm; rivet 1.1 mm hole on a test piece; the Fusion import of the files in the lab template.
