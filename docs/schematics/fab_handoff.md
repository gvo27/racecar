# Layout and fab handoff (Rev A, KiCad 10)

For the owner doing layout. Parts: `bom.csv` and `bom_offboard.csv` (made by `make bom`; notes in `bom.md`). Design intent: `design_overview.md`. Widths come from the IPC tables in `power_board_plan.md`; nothing here is a verified machine or fab limit. **Provisional** = derived from the tool geometry below, not yet confirmed with the lab tech. Repo rule: unconfirmed => `TBD`.

# A. Prototype rev A: in-house CNC (Makera Carvera)

V-bit isolation milling in the lab's calibrated Fusion 360 template (`example/README.md`), with DXF and Excellon files from `make pcb-fab` (`fab/README.md`). The board is not fabricated by a fab house for this revision.

## Stock and tools

- **Stock:** Kepro P22-465G FR-4, 2 oz Cu, double-sided, 4" x 6" x 0.062" (101.6 x 152.4 x 1.57 mm), lab stock (owner, 2026-11-12). The earlier 3" x 6" blank (P22-365G, 76.2 x 152.4 mm) is also in stock but is too small for the dowel line of the lab template. The blank is even (depth error 0, owner). Scrub oxide off before milling. 2 oz matches the trace-width plan, so the 2 oz columns below apply directly. Other lab stock: generic double-sided 10 x 15 cm, 10 pcs, copper weight TBD (likely 1 oz): not for this board.
- **Lab tools (from the lab .f3z and the owner's photos):**
  - Isolation: 1 contour pass, 0.08 mm deep, chamfer mill with 0.2 mm tip (Fusion taper 30). Copper is 0.070 mm, so the margin is 0.01 mm. The lab tech accepts this margin (2026-11-13); if necessary, the lab adds a second, deeper pass in the CAM file. Cut width at depth: 0.243 mm (30 degrees included) or 0.292 mm (60 degrees included); the 0.4 mm design clearance passes both.
  - Drill bits: 0.1 to 2.0 mm in 0.1 mm steps (owner inventory). The lab CAM uses 0.9, 1.0 and 1.1 mm.
  - End mill: one, 3.175 mm (1/8 in). It bores the dowel holes. A hole of 2.0 to 3.3 mm cannot be made.
  - Dowels: 2 holes of 4.191 mm for 4.0 mm pins, at (3.2766, 3.81) and (149.1234, 3.81) mm from the stock lower-left corner.
- **Makera PCB Fabrication Pack:** 2x 1/8" 60° 0.1 mm-tip V-bit, 2x 1/8" 30° 0.2 mm-tip V-bit, 20x milling/drilling bits, dowel pins, UV solder-mask paint. The lab CAM uses only the 0.2 mm tip V-bit.
- **Fixturing:** rigid flat; double-sided tape on a flat sacrificial board.

## Layer strategy

- **Bottom (B.Cu):** signal and power routing; VBAT / HighCurrent as wide pours.
- **Top (F.Cu):** GND pour, stitched to bottom GND with a few rivets near connectors and regulators. Each rivet is manual: keep the count low. Unplated, so THT pads cannot be soldered on top: set the F.Cu GND zone to "Pad connections: None" for THT pads (or a custom rule excluding THT pads from the F.Cu zone), and connect every THT GND pin on B.Cu. The top pour joins bottom GND only through soldered rivet stitching.
- **Placement:** place all SMD parts on the bottom (B.Cu side; select + F to flip); THT parts on top, soldered from the bottom. SMD on the bottom is soldered on the routing side, so no rivets are needed per pad.
- Keep current-carrying paths off rivets. A 0.8 mm EasyContac rivet is fine for signals and GND stitching; for HighCurrent use several rivets in parallel (optionally the 1.2 mm size) or avoid the layer change.

## DRC and net classes (provisional)

Isolation width per pass is about tip + 2·depth·tan(half-angle): 30°/0.2 mm tip at 0.1 mm depth is about 0.25 mm; 60°/0.1 mm tip is about 0.22 mm. 2 oz copper is 70 µm, so depth is at least 0.1 mm.

| Rule | Value (provisional) |
| --- | --- |
| Min clearance (all net classes) | 0.4 mm (was 0.2) |
| Min track | 0.5 mm |
| Min annular ring | 0.45 mm for the rivet pad ((2.0 - 1.1) / 2; no plating); enlarge pads where possible |
| Via (EasyContac 0.8 rivet), all classes | 2.0 mm pad / 1.1 mm hole |

Net classes (`rc_power_board.kicad_pro`; HighCurrent = `*VBAT*`, GND; Power5A = `+5V_CPU`, `+5V_SENS`; Power3A = `*+6V_BEC`). Clearance 0.4 mm everywhere:

| Class | Track width | Via (EasyContac rivet, pad / hole) |
| --- | --- | --- |
| HighCurrent | 6.0 mm or a zone | 2.0 / 1.1 mm, several in parallel if a layer change is unavoidable (optional 1.2 mm rivet: 3.0 / 1.7 mm) |
| Power5A (`+5V_CPU`, `+5V_SENS`) | 1.6 mm | 2.0 / 1.1 mm |
| Power3A (`*+6V_BEC`) | 1.0 mm | 2.0 / 1.1 mm |
| Default | 0.5 mm (was 0.25) | 2.0 / 1.1 mm |

The project DRC rules in `rc_power_board.kicad_pro` are set to match: `min_clearance` 0.4, `min_track_width` 0.5, `min_via_diameter` 2.0, `min_via_annular_width` 0.45 ((2.0 - 1.1) / 2 for the rivet pad), `min_through_hole_diameter` 0.8 (C9 drill 0.8 mm; methods TBD per the bit list). Confirm in Board Setup > Design Rules. `VIN_CPU` / `VIN_SENS` no longer exist: U1 and U2 VIN sit on `VBAT`.

**U3 flag (owner decides).** AP2112K SOT-23-5 pads are 0.6 mm wide at 0.95 mm pitch, so the gap is 0.35 mm, below 0.4 mm. Options: (1) custom U3 footprint with pads about 0.5 mm wide (gap about 0.45 mm); (2) accept a local DRC exception: Board Setup > Design Rules > Custom Rules, `(version 1) (rule U3_fine (condition "A.memberOfFootprint('U3') || B.memberOfFootprint('U3')") (constraint clearance (min 0.3mm)))`. Either way, mill U3 with the 60°/0.1 mm bit. 0805 passives are fine. XH pads (1.7 x 2.0 mm at 2.5 mm pitch) leave a 0.8 mm gap.

## Rev A KiCad board (review only, 2026-11-11)

`rc_power_board.kicad_pcb` is built and routed headless in the pinned KiCad 10.0.8 image. It is for owner review. DXF and Excellon files for the lab's Fusion 360 template are in `fab/` (`make pcb-fab`, Task 9). The CAM stays in the lab template and has not run for this board. The Gerber and MakeraCAM steps below are an older plan. Values marked "assumed" wait for the lab tech.

- **Via (confirmed):** the EasyContac 0.8 rivet (1.0 mm OD, owner caliper 2026-11-13, measured on the shaft: 0.8 bag 1.0 mm, 1.0 bag 1.45 mm, 1.2 bag 1.6 mm OD (old caliper, small error possible)) needs a 1.1 mm hole (lab tech rule: OD + 0.1 mm). Rivet stock is the LPKF EasyContac kit (owner photo 2026-11-13). The owner's bit set has a 1.1 mm bit, so the via is **1.1 mm drill / 2.1 mm pad** (annular ring 0.5 mm) in every net class. If a rivet does not fit, the lab widens the hole in a second pass.
- **Bit set (owner photo, 2026-11-12):** drill 0.1 to 2.0 mm in 0.1 mm steps. A footprint hole is snapped up to the smallest size in the set in the board copies (XH 0.95 to 1.0, MKDS 1.3 stays 1.3, F1 pins 1.4 stays 1.4); pads grow to keep the 0.45 mm annular ring. A hole larger than 2.0 mm is bored with the 3.175 mm end mill and must be 3.3 mm or more (`milled_hole_min`, assumed: tool + 0.125 mm).
- **Hole list from the board (lab fit, Task 9):** 0.8 mm x 2 (C9); 1.0 mm x 52 (U1, U2 (12 each), C1, J3, J4, J5, J8, J9, J11 to J14); 1.1 mm x 3 (rivet vias); 1.3 mm x 4 (J6, J7); 1.4 mm x 8 (F1 pins); bored: 3.4 mm x 7 (H1 to H4 M3 clearance, J1 wire pads, F1 locating peg), plus 2 dowel holes of 4.191 mm outside the board. Before Task 9 the board had 2.4 mm (F1 peg), 3.0 mm (J1) and 3.2 mm (H1 to H4) holes, which the lab tools cannot make.
- **F1 peg:** the KiCad library footprint of the Littelfuse FLR 178.6165 has a 2.4 mm NPTH for the central locating peg. The Littelfuse drawing was not reachable from the build host (HTTP 403), so the peg diameter is **not confirmed**. It is larger than 2.0 mm in any case (the library hole is 2.4 mm), so it is a loose 3.4 mm locator hole. If the real peg is 2.0 mm or less, a drill from the set can replace it. Check the peg against the holder before milling.
- **J1 wire pads:** hole 3.4 mm (was 3.0 mm), pad 4.4 mm, annular ring 0.5 mm. The 12 AWG conductor (about 2.05 mm) is loose in the hole.
- **Frame:** the board is turned 90 degrees and centered on the stock; the two dowel holes are outside the board. Details and file list: `fab/README.md`.
- **Outline:** 66 x 140 mm, drill/place origin at the lower-left corner. The U1 and U2 bodies (25.4 x 25.4 mm) lie inside it: U2 x 8.0 to 33.4, y 22.3 to 47.7; U1 x 36.0 to 61.4, y 22.3 to 47.7 (mm from the origin). Stackup: 2 layers, 0.070 mm copper, 1.57 mm total.
- **Layers:** SMD parts on B.Cu, THT parts on F.Cu. Routing on B.Cu. `VBAT_RAW`, `VBAT` and GND are B.Cu zones. The F.Cu GND pour has pad connection "none" and joins B.Cu GND through one rivet via. F.Cu has one jumper track (`U1_PG`, U1.1 to J5.1, about 75 mm) on two rivet vias. The I2C jumpers of the first layout are removed. No F.Cu copper touches a THT pad (check in `make pcb-check`).
- **Rivet vias: 3** (2 for the `U1_PG` jumper, 1 GND stitching). No via is inside a part courtyard (a rivet needs both sides soldered).
- **Make targets:** `make kicad-image erc pcb-build pcb-route pcb-check pcb-mill-check pcb-review pcb-test`. Details: `review/README.md`.
- **U3 rule:** `rc_power_board.kicad_dru` rule `U3_fine` sets 0.3 mm clearance for U3 pads against pads, tracks and vias. The pour keeps 0.4 mm.

## Vias: LPKF EasyContac rivets

No plated through-holes. Vias are **LPKF EasyContac** through-hole rivets from the lab kit (owner photo 2026-11-13: bags 0.6 / 0.8 / 1.0 / 1.2 mm and a setting tool; this photo is the reference for rivets, not the lab .f3z). The bag label is the inner diameter (owner caliper 2026-11-13, measured on the shaft: 0.8 bag 1.0 mm, 1.0 bag 1.45 mm, 1.2 bag 1.6 mm OD (old caliper, small error possible)). Press each rivet with the kit's setting tool, then **solder both sides**. Max board thickness for rivets is 1.6 mm (stock 1.57 mm OK). Sizes from the Vanderbilt design-guide table for LPKF EasyContac (https://my.vanderbilt.edu/daniel/?p=200); the LPKF US store lists outer diameters 0.8 / 1.0 / 1.4 / 1.6 mm, inner 0.2-0.4 mm smaller. The owner's caliper values match the outer diameters in the table (1.0 bag: 1.45 mm measured vs 1.4 mm in the table). The collar is the wider face on one end; the setting tool flares the other end.

| Rivet (inner) | Outer | Drill | Collar |
| --- | --- | --- | --- |
| 0.6 mm | 0.8 mm | 0.9 mm | 1.3 mm |
| 0.8 mm | 1.0 mm | 1.1 mm | 1.6 mm |
| 1.0 mm | 1.4 mm | 1.5 mm | 2.2 mm |
| 1.2 mm | 1.6 mm | 1.7 mm | 2.6 mm |

Rule (lab tech 2026-11-13): drill = rivet outer diameter + 0.1 mm. If a rivet does not fit, the lab widens the hole in a second pass.

- **Default via: EasyContac 0.8 mm** (about 20 needed): drill 1.1 mm, pad 2.0 mm (collar 1.6 + margin), annular 0.45 mm. Matches the via settings already in `rc_power_board.kicad_pro` (2.0 / 1.1), so no change there. Rivet size is fixed by lab stock and the drill size by the rivet; the board now uses a 2.1 mm pad (annular 0.5 mm). The 1.1 mm bit is in the owner's set. If the rivet does not fit, the lab widens the hole in a second pass (lab tech 2026-11-13).
- **Optional, high current (VBAT / GND layer changes): EasyContac 1.2 mm**, several in parallel: drill 1.7 mm, collar 2.6 mm, pad at least 3.0 mm. If used, define it as a separate via size in Board Setup > Design Rules > Pre-defined Sizes.
- **Optional, plated THT hole:** an EasyContac 1.0 mm rivet can "plate" a THT hole so a component pin is soldered on one side and still connects both layers. Round leads up to about 0.8 mm fit; 0.64 mm square pins (diagonal about 0.905 mm vs 1.0 mm bore) are a tight fit: test first. The 2.4 mm pad (2.2 mm collar) needs ≥2.8 mm pitch for 0.4 mm clearance, so it does not fit XH (2.5 mm) or 2.54 mm headers; use it only on wider-pitch parts (e.g. C9 3.5 mm, VH 3.96 mm, screw terminals). The footprint hole then becomes 1.5 mm drill with a pad of at least 2.4 mm. Not the default: the default stays "THT pins routed on the bottom".

## Holes (size, method: TBD per lab bit list)

| Feature | Hole | Method |
| --- | --- | --- |
| Rivet vias (EasyContac 0.8) | 1.1 mm | drill (1.1 mm bit is in the set) |
| U1 and U2 headers (D36V50F5) | 1.0 mm | drill, TBD. The 3 module mounting holes (2.18 mm) are not drilled: the header holds the module |
| JST XH pins | B2B 1.0 mm; B3B/B4B/B6B 0.95 mm (or drill all at 1.0 mm) | drill, TBD |
| C9 (CP_Radial_D8.0mm_P3.50mm) | 0.8 mm | drill, TBD |
| C1 (CP_Radial_D10.0mm_P5.00mm) | 1.0 mm | drill, TBD |
| Phoenix MKDS (J6/J7) | 1.3 mm | drill |
| F1 FLR holder | 1.4 mm pins; 3.4 mm NPTH locating peg hole | pins: drill; peg hole: bore with the end mill (peg size not confirmed) |
| J6 VH option | 1.7 mm (only if chosen) | drill or helical mill, TBD |
| J1 SolderWire | 3.4 mm | bore with the 3.175 mm end mill |
| M3 mounting (H1-H4) | 3.4 mm | bore with the 3.175 mm end mill |
| Dowel pins | 4.191 mm for 4.0 mm pins (lab template), 2 holes | bore in Setup A, outside the board outline |

## Unplated THT soldering

Solder each THT pin on every layer where it has copper. JST XH shrouds and screw terminals block top-side soldering: route those pins on the **bottom (solder side) only**, or bring the top connection through a rivet (on wide-pitch parts only, an EasyContac 1.0 mm rivet in the THT hole, see Vias). Same for the F1 holder and the U1 header.

## Registration and outline

- 2 dowel holes (4.191 mm for 4.0 mm pins) on one line along the stock long side, bored in Setup A of the lab template. B.Cu is not mirrored in the files: Setup C flips the stock.
- The board (66 x 140 mm) is turned 90 degrees and centered on the 152.4 x 101.6 mm stock: 6.2 mm at each end, 17.8 mm at each long side. The dowel holes are about 14 mm from the outline. Outputs: `fab/` (`make pcb-fab`).

## Export and CAM

- [x] Export: `make pcb-fab` writes the DXF files (F.Cu, B.Cu, Edge.Cuts), the Excellon file and the drill-map DXF to `fab/`, in the lab frame (`fab/README.md`). B.Cu is not mirrored: Setup C of the lab template flips the stock.
- [ ] Lab template: import the files, check the dowel positions (0, 0) and (145.8468, 0) against the template, and run the lab tech's CAM. Not done.
- [ ] Isolation as in the lab template: 0.2 mm tip V-bit, 1 pass, 0.08 mm deep, on an even blank (copper 0.070 mm, margin 0.01 mm, accepted by the lab tech). If copper stays in a cut, add a second, deeper pass. Drills and bores from the Excellon tool list. Outline cut: the lab tech decides.

## Finishing and checks

- **No solder mask or silkscreen by default.** Optional: Makera UV solder-mask paint; otherwise tin or lacquer the copper. Mark pin 1 and polarity by milling text in copper or with a marker.
- **Before populating:** continuity check every net against the netlist; check for shorts across adjacent isolation cuts (especially U3, J5).
- **Open items:** lab tech to confirm bit diameters (incl. a 1.1 mm bit for the rivet holes); U3 option.

## Layout

- **Budget note:** U1 is computed at 5.1 V × 5 A input-equivalent; at a full 5.5 A rail the board is about 9.35 A (9.6 A at startup), still 62-64 % of 15 A.

- **Stack:** 2 layers, 2 oz (70 µm) copper, 1.57 mm board. Set Board Setup > Physical Stackup accordingly.
- **HighCurrent copper follows F1, not the load.** Copper for VBAT_RAW/VBAT/GND is sized for F1's rating, not the 9.0 A load (a blade fuse holds 110% indefinitely): 15 A (decided; 10 A would run at 84-93 % under the Mapper load) means about 16.5 A. Computed widths (IPC-2221, external layer, mm; `I = 0.048·ΔT^0.44·A^0.725`, A in mil², 1 oz = 1.378 mil):

| Net | Design current | 1 oz ΔT10 | 1 oz ΔT20 | 2 oz ΔT10 | 2 oz ΔT20 | Net class now |
| --- | --- | --- | --- | --- | --- | --- |
| VBAT_RAW / VBAT / GND (F1 15 A × 1.1) | 16.5 A | 14.4 | 9.4 | 7.2 | 4.7 | HighCurrent 6.0 |
| VBAT load at 6.0 V, Mapper running (reference) | 9.0 A | 6.2 | 4.1 | 3.1 | 2.0 | — |
| +5V_CPU | 5.5 A | 3.2 | 2.1 | 1.6 | 1.0 | Power5A 1.6 |
| +5V_SENS (Mapper startup; 4.6 A running) | 4.9 A | 2.7 | 1.8 | 1.3 | 0.9 | Power5A 1.6 |
| +6V_BEC | 3.0 A | 1.4 | 0.9 | 0.7 | 0.45 | Power3A 1.0 |
| +3V3_SENS, I2C, PWM, PG | ≤ 0.3 A | < 0.1 | < 0.1 | < 0.1 | < 0.1 | Default 0.5 |

  Stock is 2 oz, so use the 2 oz columns. HighCurrent 6.0 mm or a pour covers the 15 A fuse (about ΔT 13-15 °C). IPC-2221 is conservative versus IPC-2152 for boards with planes. Neck down only at pads and the U1 header.
- **I2C:** keep `I2C_SDA`/`I2C_SCL` short-ish and routed together over the GND pour from J8 to J5.
- **J5 harness:** keep short; twist SDA and SCL each with a GND or route them beside GND; one GND pin for 5 signals is fine for a short lead.
- **U1 header:** neck the `VBAT` and `GND` copper down to the 2.54 mm pin pitch only at the pins; keep the wide pour up to the pad. Use both pins of each pair (3 A per pin).
- **High-current pads** (J1, F1 holder, U1 VIN/GND, C1): thermal reliefs off, or heavier spokes.
- **F1:** FLR 178.6165 holder on a board edge, accessible with the board mounted.
- **Noise:** keep U3, FB1/C6 and any IMU/encoder area away from the buck switching nodes and inductors.

## Connector pin order and crimping

**Pin order convention** (all XH, pin numbers as in the schematic):

- **Rule A, device with its own standard pinout:** the header follows the device so wire colours run straight through. J3 (ESC lead) and J4 (servo): 1 GND (black/brown), 2 +6V_BEC (red), 3 signal (white/orange). J8 (Garmin): 1 +5V_SENS red, 2 GND black, 3 I2C_SDA white, 4 I2C_SCL green.
- **Rule B, generic power header:** 1 V+, 2 GND. J9, J11 (+5V_SENS); J12, J13, J14 (+3V3_SENS).
- **Rule C, signal harness:** signals in order, GND last. J5: 1 U1_PG, 2 THROTTLE_PWM, 3 STEER_PWM, 4 I2C_SDA, 5 I2C_SCL, 6 GND.

**Crimp table** (header JST B*n*B-XH-A, housing XHP-*n*, contact SXH-001T-P0.6; suggested wire colours; device colours are fixed only for J8 (Garmin) and the servo/ESC leads):

| Ref | XH size | Housing | Pin | Net | Wire colour | Far end |
| --- | --- | --- | --- | --- | --- | --- |
| J3 | 3 | XHP-3 | 1 | GND | black / brown | ESC receiver lead |
| | | | 2 | +6V_BEC | red | ESC receiver lead |
| | | | 3 | THROTTLE_PWM | white / orange | ESC receiver lead |
| J4 | 3 | XHP-3 | 1 | GND | black / brown | DS3225MG servo |
| | | | 2 | +6V_BEC | red | DS3225MG servo |
| | | | 3 | STEER_PWM | white / orange | DS3225MG servo |
| J5 | 6 | XHP-6 | 1 | U1_PG | any | ESP32 (GPIO TBD) |
| | | | 2 | THROTTLE_PWM | any | ESP32 GPIO5 |
| | | | 3 | STEER_PWM | any | ESP32 GPIO4 |
| | | | 4 | I2C_SDA | any | ESP32 GPIO8 |
| | | | 5 | I2C_SCL | any | ESP32 GPIO9 |
| | | | 6 | GND | black | ESP32 GND |
| J8 | 4 | XHP-4 | 1 | +5V_SENS | red | Garmin LIDAR-Lite v4 pin 1 |
| | | | 2 | GND | black | Garmin pin 2 |
| | | | 3 | I2C_SDA | white | Garmin pin 3 |
| | | | 4 | I2C_SCL | green | Garmin pin 4 |
| J9 | 2 | XHP-2 | 1 / 2 | +5V_SENS / GND | red / black | Camera USB hub |
| J11 | 2 | XHP-2 | 1 / 2 | +5V_SENS / GND | red / black | Slamtec Mapper (5 V); harness to 22 AWG 3 A USB-A male pigtail, red = VBUS |
| J12 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | IMU |
| J13 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | Shaft encoder |
| J14 | 2 | XHP-2 | 1 / 2 | +3V3_SENS / GND | red / black | Spare 3.3 V |

Verified against the kicad-cli netlist of `rc_power_board.kicad_sch`. J3/J4 current: XH is 3 A/pin with 22 AWG only; see `bom.md`.

**Finding cavity 1 before the PCB exists.** An XH header/housing pair is keyed, so header pin N always mates with housing cavity N regardless of PCB orientation; crimping depends only on pin numbers.

1. Find pin 1 on a loose header from JST's XH drawing (KiCad footprint: pad 1 is the roundrect pad) and mark it.
2. Snap an empty housing onto the header and mark the cavity over pin 1.
3. Crimp and insert contacts by pin number.
4. After crimping, plug each lead into the marked header and buzz pin-to-wire with a multimeter.

**Layout rule:** place XH headers on the board edge, wire entry facing outward, pin 1 at the same end for all headers; leave slack in harness lengths until layout fixes positions.

**Rev A exception (pending owner approval):** the B.Cu routing without rivets needs other turns. On the left edge, pin 1 is at the bottom, except J4 and J8 (pin 1 at the top). J6 and J7 are on the right edge with pin 1 at the top. J1 is turned 180 degrees (GND on the left, BAT+ on the right). The pin numbers of each connector and the crimp table are unchanged; only the orientation on the board changed. Header pin N still mates with housing cavity N, so crimping is not affected. J8 turned means the Garmin pins 1 to 4 run from the top to the bottom of the board.

## External connections: JST PCB headers

Suggested top-entry vertical through-hole headers; MPNs are proposals. XH is 2.5 mm pitch, 3 A/pin with 22 AWG; crimp SXH-001T-P0.6 (22-28 AWG). KiCad footprints below exist in `/usr/share/kicad/footprints/Connector_JST.pretty` (checked locally).

| Ref | Function | Current | Suggested PCB header | Mating housing + crimp | Wire | KiCad footprint | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J3, J4 | ESC lead, servo | up to 3 A (BEC pin 100 %) | B3B-XH-A(LF)(SN) | XHP-3 + SXH-001T-P0.6 | 22-28 AWG | `JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical` | 3 A/pin with 22 AWG only |
| J5 | Signals to ESP32 | < 0.1 A | B6B-XH-A(LF)(SN) | XHP-6 + SXH-001T-P0.6 | 22-28 AWG | `JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical` | |
| J8 | Garmin LIDAR-Lite v4 | about 0.1 A | B4B-XH-A(LF)(SN) | XHP-4 + SXH-001T-P0.6 | 22-28 AWG | `JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical` | |
| J9 | Camera USB hub | TBD (camera hub; 0.3-0.5 A per camera) | B2B-XH-A(LF)(SN) | XHP-2 + SXH-001T-P0.6 | 22-28 AWG | `JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical` | load current TBD; XH limit 3 A |
| J11 | Slamtec Mapper (5V) | 0.75 A typ, 1.3 A max, 1.4-1.6 A startup (few s) | B2B-XH-A(LF)(SN) | XHP-2 + SXH-001T-P0.6 | 22 AWG (3 A USB-A pigtail) | same | Within the XH 3 A limit. C9 (>=100 uF low-ESR) placed right at J11; Mapper ripple limit 50 mV. Never from Pi USB or straight from the pack. Verify >= 4.8 V at the Mapper during startup (U2 tolerance TBD, about 0.03-0.05 V pigtail drop at 1.6 A) |
| J12-J14 | IMU, encoder, spare 3.3 V | ≤ 0.3 A | B2B-XH-A(LF)(SN) | XHP-2 + SXH-001T-P0.6 | 22-28 AWG | same | |
| J7 | ESP32 USB-C pigtail | about 0.5 A | **Option:** B2B-XH-A(LF)(SN) | XHP-2 + SXH-001T-P0.6 | 20 AWG pigtail does not fit (22-28 AWG): trim/splice to 22 AWG | same | Current choice: Phoenix screw terminal |
| J6 | Pi 5 USB-C pigtail | up to 5 A | **Option:** B2P-VH(LF)(SN) (3.96 mm) | VHR-2N + SVH-21T-P1.1 (18-22 AWG, confirm) | 20 AWG | `JST_VH_B2P-VH_1x02_P3.96mm_Vertical` (pads 2.7 mm, drill 1.7 mm) | Above XH 3 A/pin. VH rating per JST VH datasheet, confirm (about 10 A with 16 AWG). Current choice: Phoenix MKDS screw terminal |
| J1 | Battery T-plug pigtail | 16.5 A (F1 rating) | none suitable | n/a | 12 AWG | `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm` | Pigtail pads stay (owner exception) |

- **Side-entry option** for board-edge wire exit: S*n*B-XH-A, e.g. `JST_XH_S3B-XH-A_1x03_P2.50mm_Horizontal` (footprints S2B to S16B exist). Same unplated-THT soldering rule applies.
- F1 holder and U1 module headers are part mounting, not external connections.
- On unplated boards the header shroud blocks top-side soldering: route XH/VH pins on the bottom only (section A).

# B. Later revisions: fab house

Not the rev A path. Essentials if the board goes to a fab house:

- Use the fab's published 2-layer capabilities or DRC rules file (not KiCad defaults); 1.6 mm board, 2 oz outer copper for HighCurrent; plated vias replace the rivets (restore small via sizes and 0.2 mm class clearance at that point).
- Plot: F.Cu, B.Cu, F/B.Mask, F/B.Silkscreen, Edge.Cuts (F/B.Paste only if the fab assembles); Excellon drill plus drill map; zip and view in a Gerber viewer before upload.

# Sign-off (both paths)

- [ ] ERC clean (KiCad 10, owner-run)
- [ ] DRC clean (rev A: table above)
- [ ] 3D view check
- [ ] Footprints vs real parts: U1 and U2 (D36V50F5 body 25.4 x 25.4 mm on the 1:1 print, standoff over the F.Cu pour, 1.8 mm parts under the module), J1 drill (12 AWG), F1 holder (FLR 178.6165) pins, XH header footprints
- [ ] BOM reviewed (`bom.csv`, `bom_offboard.csv`)

# Open items before publish

1. F1: 15 A decided by the load (ATO/ATC blade in FLR holder assumed).
2. Reverse-polarity decision: the proposal (P-FET) is in the PR, not on the board.
3. U2 = Pololu D36V50F5, the same part as U1 (owner 2026-11-12; two modules owned). Footprint `rc_power:Pololu_D36V50Fx` from the Pololu drawing: VIN, VOUT and GND each use a pin pair (about 2.45 A per VOUT pin at 4.9 A). About 7.4 A at 6 V in (Pololu graph), so the 6 A need is met. Dropout about 1.0 V at 5 A: the output can fall below 5 V near the 6.0 V cutoff. Check the footprint against the real module (1:1 print) before milling. Details: `docs/datasheets/regulator_pololu_d36v50f5.md`. Verify >= 4.8 V at the Mapper during startup (U2 tolerance TBD, about 0.03-0.05 V pigtail drop at 1.6 A).
4. All `TBD` values in the schematic.
5. U1 EN stays unconnected until the rev 2 prototype board.
6. I2C pull-ups: bus is pulled up only by the Garmin's internal 13 kΩ; consider two DNP 0805 4.7-10 kΩ pull-up footprints to `+3V3_SENS` for a future IMU. Not drawn.
7. Rev A CNC: bit list (incl. 1.1 mm for rivet holes), U3 footprint option.
