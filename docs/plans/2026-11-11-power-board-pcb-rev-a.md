# Power board rev A PCB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DRC-clean, routed `rc_power_board.kicad_pcb` for owner review, from the existing schematic with U2 = Pololu D24V90F5.

**Scope (owner, 2026-11-11):** a valid KiCad PCB for review only. Gerber/drill export, CAM and machine setup are out of scope: the lab tech will give separate instructions for the path from the KiCad file to the milling machine. The milling rules already in the project (clearance, hole sizes, B.Cu routing, unplated holes) still apply to the board, so that it does not need a redesign later.

**Architecture:** All KiCad work runs headless in the pinned KiCad 10.0.8 image (`kicad-cli` plus `pcbnew` Python). Python scripts in `docs/schematics/tools/` build the board, route it through Freerouting (pinned image, Specctra DSN/SES), check it, and plot review files. `make` targets wrap each step. Tests are stdlib `unittest` files that run with the image's `python3`. After the bootstrap, the `.kicad_pcb` is the owner's file: the scripts are for the first build and for re-checks, not a generator the owner must keep using.

**Tech Stack:** KiCad 10.0.8 (`kicad/kicad:10.0.8@sha256:3f4a01786dfbe803a65f345c3342b765db9add913f5e9448f8356793714ddc34`), Freerouting 2.5.0 (`ghcr.io/freerouting/freerouting:2.5.0`, pin by digest at Task 2), GNU make, Docker.

**Spec:** `docs/plans/2026-11-11-power-board-pcb-rev-a-design.md`

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
- Create: `docs/schematics/milling.toml`, `docs/schematics/tools/milling_check.py`, `docs/schematics/tools/test_milling_check.py`
- Modify: `Makefile` (target `pcb-mill-check`; add the tests to `pcb-test`)

**`milling.toml`** (each value carries `status = "assumed"` or `"confirmed"` and a `source`):
- copper thickness 0.070 mm (Kepro P22-365G, 2 oz; confirmed, `fab_handoff.md`)
- isolation bits: 30°, tip 0.2 mm; 60°, tip 0.1 mm (Makera PCB pack; confirmed)
- cut depth 0.10 to 0.15 mm (`fab_handoff.md`; assumed); depth error ±0.05 mm with probe auto-levelling (assumed)
- drill set 0.8, 1.0, 1.2, 1.5 mm (owner: assume 4 common sizes; assumed); smallest end mill 1.0 mm (assumed); a milled hole must be > 1.5 mm
- rivet via 1.2 mm drill / 2.1 mm pad; annular min 0.45 mm; track min 0.5 mm; edge clearance 0.5 mm (`min_copper_edge_clearance` in `.kicad_pro`)

**Interfaces:** `load_limits(path: str) -> Limits`; `cut_width(tip: float, angle_deg: float, depth: float) -> float` (`tip + 2 * depth * tan(angle / 2)`); `check(board: pcbnew.BOARD, limits: Limits) -> list[Finding]`, `Finding = (rule_id: str, severity: "error"|"warning", where: str, value: float|None, limit: float|None, message: str)`; CLI `milling_check.py <board> --limits <toml> --json <out>`, exit 0/1/2. Task 5's `check_board.py` calls `check()` and fails on any error.

**Numbers to pin in tests:** worst-case depth = 0.15 + 0.05 = 0.20 mm. `cut_width(0.2, 30, 0.20)` = 0.307 mm; `cut_width(0.1, 60, 0.20)` = 0.331 mm. MILL-GAP: a gap is an error when it is < the narrowest bit's cut width at worst-case depth (0.307 mm); MILL-GAP-BIT (warning): gaps where only some bits fit, listing the bits that fit (here, gaps from 0.307 to < 0.331 mm fit only the 30° bit). MILL-DEPTH: 0.10 - 0.05 = 0.05 mm < 0.070 mm => **error with the assumed limits.** Do not hide it: report it to the owner as a finding about the assumed depth range (the min depth must be at least 0.12 mm with ±0.05 error).

- [ ] **Step 1:** Write `test_milling_check.py` (stdlib `unittest`, image `python3`): the `cut_width` values above; a synthetic board made in the test with `pcbnew`: two tracks of different nets 0.30 mm apart => MILL-GAP error; 0.32 mm => MILL-GAP-BIT warning (30° only); 0.45 mm => none; a 1.1 mm hole => MILL-DRILL error; a 2.4 mm hole => none (milled); an F.Cu track on a THT pad => MILL-FCU-THT error; a 2.0/1.1 via => MILL-VIA error. `load_limits` rejects a value with no `status`.
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

**Approach:** Before the DSN export, set F.Cu to "not routable" in the DSN (only B.Cu is a signal layer). Route `VBAT_RAW` and `VBAT` by hand in the script as 6.0 mm B.Cu tracks along the input chain (pad-to-pad on the placement), and let the B.Cu GND zone carry GND; Freerouting routes the rest, with net-class widths from the DSN. Allow vias only if B.Cu-only routing can't finish; then each via is a rivet and the count goes in the report.

- [ ] **Step 1:** Add tests: `kicad-cli pcb drc --schematic-parity --severity-all --format json` gives 0 errors and 0 unconnected items; `check_board()` is []; every `VBAT_RAW`/`VBAT` track is ≥ 6.0 mm; the via count is printed.
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
- [ ] **Step 4b:** Review (main session): a Sonnet reviewer, fix the findings, then an Opus reviewer, fix the findings.
- [ ] **Step 5:** Commit `pcb: rev A review package and docs`, push to `schematic`, comment on PR #3 (owner GUI checks: Update Symbols, 3D view, 1:1 print, U2 footprint vs the real module).

### Task 8 (later, separate): KiRI visual diff trial

Owner, 2026-11-11: try leoheck/kiri (tag 1.0.0) with KiCad 10. Do not commit anything until it works with KiCad 10. If the setup is too buggy, drop it and record that in the PR. Work in the scratchpad, in a container based on the pinned KiCad image. Pass = `kiri` makes a schematic and layout diff between two commits of `docs/schematics/` with no errors. Only then propose a pinned CI job (kiri-github-action by SHA, after a read of its permissions).
