# KiCad Power Rail Schematic Guide — RC Car Platform

Exported 2026-10-30 from the live doc: https://claude.ai/artifact/G7oi8ZxQaXkXNUEQmDbfmX (edit there, re-export here). Build guide and background for the schematic in this folder (`rc_power_board.kicad_sch`). Project KiCad version: 10.0.

> **For the design meeting:** the one-page summary of the current schematic is `docs/schematics/design_overview.md`. This guide is the step-by-step build and background reference.

## Overview

The goal is a first-draft KiCad schematic for one **power distribution board (PDB)** that takes the 2S LiPo and produces four rails, ready for a professional to critique. It is a draft: every part value you are unsure of is marked `TBD` so the reviewer sees exactly where your knowledge stops.

The board carries four power circuits, all sharing one ground:

| Rail (net name) | Voltage | Current budget | Made by | Feeds |
| --- | --- | --- | --- | --- |
| `VBAT` | 7.4 V nominal (6.0 to 8.4 V) | about 7.3 A of board loads (the ESC's 20 A is off-board) | battery, through the main fuse | &#32;inputs of the two switching regulators |
| `+5V_CPU` | 5.0 to 5.1 V | 5.5 A (regulator rated 6 A or more) | dedicated, higher-grade step-down regulator | Raspberry Pi 5, ESP32-S3 |
| `+5V_SENS` | 5.0 V | 3.3 A (buck rated 4 A, TBD) | buck converter | Garmin LIDAR-Lite v4, extra cameras and the 3.3 V LDO |
| `+3V3_SENS` | 3.3 V | 0.3 A (TBD) | low-noise LDO fed from `+5V_SENS` | IMU, shaft encoder, other light sensors |

The servo is powered by the ESC's built-in 6 V / 3 A output (its **BEC**, battery eliminator circuit), so it never touches this board's 5 V rails. Actuator signal lines (PWM from the ESP32, data to the Pi) are out of scope; the board only has to give every device power and a shared ground reference.

![Power architecture: battery, VBAT bus, four branches, common ground](power_architecture.png)

Everything hangs off one fused `VBAT` bus: a single replaceable main fuse protects all branches, and only the compute branch gets the higher-grade regulator.

**How the work flows.** You draw the schematic (a logical wiring diagram), assign each symbol a physical footprint, lay out the PCB (where copper actually goes), and export Gerber files that a fab house (JLCPCB, PCBWay, OSH Park) turns into a board. This guide gets you through the schematic in detail and sketches the later steps so you and the reviewer share vocabulary.

**What a good review draft contains:** a clean, readable schematic PDF; the KiCad project folder (zipped or in git); the power budget table below; and a list of open questions. Reviewers spend their time on design when the drawing itself is tidy, so the formatting section matters as much as the electrical one.

> **Repo note:** the KiCad project lives next to this file in `docs/schematics/`; see `README.md` there. The invariant "ESP32 powers nothing" from the project rules is what this board makes true.

## Electrical background for a first board

The one idea behind everything here: **copper has resistance, and current through resistance makes heat** (P = I² × R). At 20 A, a skinny trace becomes a fuse. Most of the rules below are ways of keeping that heat and the matching voltage drop small.

### Why a breadboard won't do

Breadboard contacts are rated around 1 A and loosen with vibration. At 20 A they melt, and in a moving car a loose contact causes brown-outs that reboot the Pi. A PCB gives you rated connectors, sized copper and soldered joints.

### Trace width and copper weight

A **trace** is a copper path on the PCB. Its current capacity depends on its cross-section: width (you choose it in layout) times thickness (you choose it when ordering). Thickness is sold as **copper weight**: 1 oz/ft² ≈ 35 µm (the default) and 2 oz ≈ 70 µm (a cheap upgrade at most fabs). Outer-layer traces cool better than inner ones.

The classic sizing rule is IPC-2221 (the newer, more accurate standard is IPC-2152, which reviewers may prefer). For an outer layer:

```latex
I = 0.048 \cdot \Delta T^{0.44} \cdot A^{0.725}
```

where I is current in amps, ΔT is the allowed temperature rise in °C, and A is the cross-section in mil² (1 mil = 0.0254 mm). KiCad has this built in: from the Project Manager, open **Calculator Tools → Track Width**. Widths for an outer layer from that formula:

| Current | 1 oz, +10 °C | 1 oz, +20 °C | 2 oz, +10 °C | 2 oz, +20 °C | Used for |
| --- | --- | --- | --- | --- | --- |
| 20 A | 18.7 mm | 12.3 mm | 9.4 mm | 6.1 mm | battery to ESC path |
| 8 A | 5.3 mm | 3.5 mm | 2.6 mm | 1.7 mm | `VBAT` feed to the two regulators |
| 5 A | 2.8 mm | 1.8 mm | 1.4 mm | 0.9 mm | `+5V_CPU` |
| 3 A | 1.4 mm | 0.9 mm | 0.7 mm | 0.4 mm | `+5V_SENS` |
| 1 A | 0.3 mm | 0.2 mm | 0.2 mm | 0.1 mm | `+3V3_SENS` |

Takeaways for this board:

- **20 A does not fit in a normal trace.** Use a **copper zone** (a filled polygon) on both layers, joined by many vias, with 2 oz copper. Some designers also leave the solder mask off the strip and add solder to thicken it.
- **Or keep 20 A off the board.** A common RC approach wires the battery straight to the ESC with 12 to 14 AWG silicone wire and taps a short, fused lead to the PDB for the electronics. Ask your reviewer which they prefer (open question 1).
- **Vias** (plated holes joining layers) carry roughly 1 A each for a standard 0.3 mm drill. A 20 A layer change needs 20 or more vias, or a larger drill.
- **Connectors and wire** must match the copper: the battery's T-plug (about 50 A, approx., check its datasheet) arrives on a 12 AWG pigtail soldered to board pads, screw terminals or XT30 for 5 A outputs, and check every terminal's datasheet current rating.

**Cross-check with IPC-2152.** The table above uses the 1950s-based IPC-2221 formula. Its successor, IPC-2152, is more accurate from 5 to 25 A and usually asks for more copper on a lone trace:

| Current, 2 oz copper | IPC-2221, +10 °C | IPC-2152, +10 °C | IPC-2152, +20 °C |
| --- | --- | --- | --- |
| 20 A | 9.4 mm | 33 mm | 16 mm |
| 8 A | 2.6 mm | 6.3 mm | 3.2 mm |
| 5 A | 1.4 mm | 2.7 mm | 1.4 mm |
| 3 A | 0.7 mm | 1.1 mm | 0.6 mm |

IPC-2152 figures use the approximate formula from secondary sources (the full standard is paywalled). A solid copper plane close to the trace lowers its temperature a lot, so real boards land between the two columns. The ESC's 20 A path is on wire off the board, so the board's copper only has to carry F1's rating: size `VBAT_RAW`, `VBAT` and `GND` for the fuse (a MINI fuse holds 110 % indefinitely, so about 16.5 A for a 15 A fuse), not for the 7.3 A load.

### Ground

All rails share one ground (`GND`) so signals between the Pi, ESP32 and sensors have a common reference. On the PCB, ground is usually one big copper zone on the bottom layer. The risk is that the motor's 20 A return current, which is noisy, flows under the sensors and shifts their ground by millivolts. The fix is layout: keep the ESC's ground path short and to one side, and join everything at a **star point** near the battery connector. In the schematic it is still one net called `GND`.

### Regulator, buck converter: what's the difference?

Both turn a higher voltage into a lower one. A **linear regulator** (LDO) burns the difference as heat: dropping 2.4 V at 5 A wastes 12 W, which is impossible on a small board. A **buck converter** (switching step-down regulator) switches on and off thousands of times a second and wastes only 5 to 15 %. So the two high-current rails use bucks; the "dedicated voltage regulator" for the compute rail means a higher-grade buck with more headroom, better transient response. The 3.3 V rail is the exception: its load is tiny (about 0.1 A), so an LDO fed from `+5V_SENS` wastes well under 0.5 W and gives far cleaner power than a buck. Chaining regulators this way costs almost nothing here because the efficiency loss only applies to the small 3.3 V load. Two things about bucks matter here:

- **Dropout.** A 2S LiPo sags to about 6.4 V near empty, leaving only 1.3 V of headroom above 5.1 V. The compute regulator must still hold 5.1 V at 5 A with 6.0 V in. Check the datasheet's minimum input voltage at full load.
- **Noise.** Switching makes ripple. IMUs are sensitive to it, which is why the 3.3 V rail is an LDO after the sensor buck; a ferrite-bead filter in front of the LDO may still help (open question 5).

### Fuses, flags and other protection

- **Fuse:** a sacrificial link that opens on overcurrent so a short burns the fuse, not the wiring or the battery. Size it above normal peak current and below what the copper and wire can carry. Placeholders here are `TBD`.
- **Bulk and decoupling capacitors:** a big electrolytic capacitor on `VBAT` absorbs the ESC's current spikes; small ceramic capacitors at each regulator's input and output keep it stable. Values come from each regulator's datasheet. Ceramic capacitors lose much of their capacitance under DC voltage ("DC bias"): a 22 µF 10 V part on a 5 V rail may act like 10 µF or less, so check its bias curve or choose a higher voltage rating.
- **TVS diode** (transient-voltage suppressor): clamps voltage spikes on `VBAT` caused by the motor. Its standoff voltage must be above 8.4 V.
- **Reverse-polarity protection:** the T-plug is keyed, but a hand-soldered pigtail can still be wired backwards. Proposal (open, not drawn): one P-channel MOSFET between F1 and `VBAT` with a gate resistor to GND, about 0.3 W of loss at 7 A. Details are in the PR.
- **Power LEDs and test points** on each rail let you see and probe what's alive during bring-up.

### Why the extra capacitors, LEDs and test points

They're standard practice, and most can't live inside the module:

- **C1 (bulk, on `VBAT`):** the ESC draws current in bursts, and the battery wires' inductance makes `VBAT` dip and spike. C1 is a local reservoir on the shared bus, so no single regulator can carry it.
- **C2/C3, C4/C5 (around the modules):** these are decoupling (bypass) caps, not low-pass filters. A cap from a rail to GND is a shunt: it gives fast current a short path to ground, and it only becomes a filter when something in series (a ferrite, an inductor) sits ahead of it. The input cap (C2, C4) supplies the buck's own pulsed input current at its \~500 kHz switching frequency, so that current doesn't run back up the battery wires, and it shunts some fast ESC spikes. It can't stop the ESC's slower (kHz) ripple; the regulator's own regulation rejects most of that, with C1 as the bulk reservoir. The output cap (C3, C5) lowers output ripple and holds the rail up when the load jumps. The modules carry their own ceramics, so these are optional: keep or drop them on the reviewer's advice. The real low-pass filter on this board is FB1 + C6 in front of the LDO; the same LC filter in front of a buck is the fix if ESC noise proves to be a problem.
- **C7/C8 (LDO):** required. The AP2112 is a bare chip with no capacitors of its own; its datasheet specifies them, and many LDOs oscillate without them.
- **R + LED pairs:** "rail is on" indicators for bring-up. The resistor limits the LED to about 2 mA; without it the LED would burn out. Mark them DNP (do not populate) if unwanted.
- **Test points:** pads for a multimeter probe on each rail.

## Power budget

Worst case, the board's battery input carries about **7.3 A** into the two switching regulators when the battery is nearly empty (about 7.8 A at the 6.0 V cutoff). The ESC (up to 20 A) is fed from the battery on its own leads, off-board. That load sets the main fuse; the `VBAT_RAW`, `VBAT` and `GND` copper and the J1 pads are sized for F1's rating (about 16.5 A for a 15 A fuse). The 3.3 V rail is a low-noise **LDO** fed from `+5V_SENS`, so its current is counted inside the sensor buck's load. Per-device figures marked "approx." are from memory and must be checked against each datasheet before the review.

| Rail | Load | Est. peak current | Notes |
| --- | --- | --- | --- |
| `+5V_CPU` | Raspberry Pi 5 | 3 A board alone (approx.), 5 A with USB devices | Official supply is 5.1 V / 5 A |
| `+5V_CPU` | ESP32-S3-N16R8 dev board | 0.5 A (approx., Wi-Fi bursts) | Stays here, see below |
| `+5V_CPU` | **Rail total** | **5.5 A** | Rate U1 at 6 A or more |
| `+5V_SENS` | Garmin LIDAR-Lite v4 LED | 0.1 A (approx.) | 5 V supply, 3.3 V logic |
| `+5V_SENS` | Extra cameras (USB, via powered hub) | 0.3 to 0.5 A each (approx.) | Cameras plugged directly into the Pi draw from `+5V_CPU`, not here |
| `+5V_SENS` | Radar (removed from scope) | TBD | Model not chosen |
| `+5V_SENS` | 3.3 V LDO input | 0.3 A | An LDO draws the same current it delivers |
| `+5V_SENS` | **Rail total** | **3.3 A (TBD)** | Pick a buck rated 4 A |
| `+3V3_SENS` | IMU | < 0.02 A (approx.) | Noise-sensitive; the reason for the LDO |
| `+3V3_SENS` | Shaft encoder | < 0.05 A (approx.) |  |
| `+3V3_SENS` | **Rail total** | **0.3 A (TBD)** | LDO heat at 0.3 A: (5 − 3.3) × 0.3 ≈ 0.5 W |
| ESC BEC (off-board) | DS3225MG servo | 2.3 A stall at 6.8 V (datasheet) | Fed by the ESC's 6 V / 3 A output |
| `VBAT` | ESC + motor (off-board, own 12 AWG leads) | 20 A | Peaks may exceed this briefly |
| `VBAT` | Two regulators' inputs | 7.3 A at 6.4 V in | U1 4.4 A + U2 2.9 A, at 90 % efficiency |
| `VBAT` | **Battery total** | **about 7.3 A on the board (7.8 A at 6.0 V)** | F1 10 or 15 A (TBD); the ESC is fused off-board |
|  |  |  |  |

**Why the ESP32 stays on `+5V_CPU` rather than moving to 3.3 V.** It would free at most about 0.5 A of the Pi's budget, and only during Wi-Fi bursts; idle it draws closer to 0.1 A. The costs outweigh that. Its radio bursts would put noise on the IMU's clean rail. The LDO would have to grow to about 1 A and shed about 1.7 W of heat. Feeding a dev board's 3V3 pin bypasses its own regulator and fights it when USB is plugged in. And the ESP32 controls the throttle, so it belongs with the protected compute rail, not the sensor rail. Rating U1 at 6 A buys more margin than moving the ESP32 would.

How the regulator input currents were worked out (do this yourself for each rail):

```latex
I_{in} = \frac{V_{out} \cdot I_{out}}{\eta \cdot V_{in,min}} = \frac{5.1 \cdot 5}{0.90 \cdot 6.4} \approx 4.4\ \text{A}
```

where η is the regulator's efficiency and V\_in,min is the lowest battery voltage you expect. The lowest battery voltage gives the highest input current, so it is the worst case.

## Install KiCad and create the project

KiCad is free, open-source and what most hobby and many professional reviewers use. Menu names below match KiCad 8 and 9; newer versions move little.

1. Download from [kicad.org/download](https://www.kicad.org/download/) and install with the default options, which include the standard symbol and footprint libraries (a few GB).
2. Start KiCad. The first window is the **Project Manager**: a file list on the left and big buttons on the right for each tool.
3. If asked about library tables on first launch, choose **Copy default global symbol library table** (and the same for footprints).
4. **File → New Project…**, pick a folder such as `Documents/kicad/rc_power_board`, keep **Create a new folder for the project** ticked, and name it `rc_power_board`.
5. KiCad creates three files: `rc_power_board.kicad_pro` (settings), `.kicad_sch` (schematic) and `.kicad_pcb` (board). All are plain text, so they work well in git.

### The tools you will use

| Tool (Project Manager button) | What it is for | When |
| --- | --- | --- |
| Schematic Editor | Draw the logical circuit: symbols and wires | Now |
| Symbol Editor | Make a symbol KiCad doesn't have (your buck modules) | Now |
| PCB Editor | Place footprints and draw copper | After the schematic is reviewed |
| Footprint Editor | Make a footprint KiCad doesn't have | Later, if needed |
| Calculator Tools | Track width, via current, resistor dividers | Whenever you size copper |
| Gerber Viewer | Check the files you send to the fab | Before ordering |
|  |  |  |

### Moving around the Schematic Editor

Open the schematic by double-clicking `rc_power_board.kicad_sch`. KiCad is keyboard-driven: hover the mouse where you want something, then press the key. Press **Esc** to cancel any tool.

| Key | Action |
| --- | --- |
| Scroll wheel | Zoom; hold the middle button to pan |
| Home | Zoom to fit the whole sheet |
| A | Add a symbol (part) |
| P | Add a power symbol (`GND`, `+5V`, `PWR_FLAG`) |
| W | Draw a wire; click to bend, double-click to end |
| L | Add a net label (names a wire) |
| Q | Mark a pin as intentionally unconnected |
| M / G | Move / drag (G keeps wires attached) |
| R, X, Y | Rotate, mirror horizontally, mirror vertically |
| E | Edit the properties of the item under the mouse |
| T | Add text (for notes) |
| Ctrl+Z / Ctrl+S | Undo / save (save often) |
| ? | Show every hotkey |

All of these also exist in the **Place** menu and the right-hand toolbar, so you can click instead if you forget a key.

## Draw the schematic, step by step

You will build one A3 sheet split into five labelled regions (A to E) plus a Notes area, with power flowing left to right. Work in this order and save after each step.

### Step 1: page settings

1. **File → Page Settings…**
2. Paper size: **A3**, landscape.
3. Fill the title block: Title `RC Car Power Distribution Board`, Revision `A (draft)`, Date (today), Company (your name), Comment 1 `Draft for review, values marked TBD are unconfirmed`.
4. Click **OK**. These fields print in the bottom-right corner on every PDF.

### Step 2: block out the regions

1. **Place → Add Rectangle** (or the rectangle button on the right toolbar). Drag five boxes across the sheet, left to right: **A Battery input**, **B ESC and servo**, **C Compute 5 V**, **D Sensor 5 V**, **E Sensor 3.3 V**. Put a sixth, smaller box at the bottom for **Notes**.
2. Press **T** inside each box's top edge and type its title in a larger text size (E → Text Size ≈ 2.5 mm).
3. These boxes are drawings only; they don't connect anything. They tell a reviewer where to look.

### Step 3: make one symbol for the regulator modules

KiCad has no symbol for a ready-made buck module, so you will make a simple 4-pin one and reuse it three times. For a first draft, **modules** (small pre-built regulator boards soldered onto your PCB with pin headers) are far easier than designing a regulator from a bare IC; your reviewer may later swap one or more for a chip-level design.

1. In the Project Manager, open the **Symbol Editor**.
2. **File → New Library…**, choose **Project** (keeps it with this design), name it `rc_power`.
3. Select `rc_power` in the left list, then **File → New Symbol…**. Name `REG_MODULE`, default reference designator `U`, click **OK**.
4. Press **P** to add a pin. Make four, one at a time:

| Pin number | Pin name | Electrical type | Side |
| --- | --- | --- | --- |
| 1 | VIN | Power input | left |
| 2 | GND | Power input | bottom |
| 3 | VOUT | Power output | right |
| 4 | EN | Input | left |

5. Draw a rectangle body between the pins (rectangle tool on the right toolbar). Keep pins on the 1.27 mm (50 mil) grid, the default, or wires won't snap to them.
6. **File → Save**. Close the Symbol Editor.

The **electrical type** matters: "Power output" on VOUT tells KiCad's checker that this pin drives the rail, so the checker won't complain that the rail has no source.

### Step 4: understand net names before placing anything

A **net** is everything electrically joined. KiCad joins things three ways: a wire, a **net label** with the same name, or a **power symbol** with the same name. That last one is the trap: every `+5V` power symbol on the sheet is the same net. If you put `+5V` on both 5 V rails, KiCad shorts the compute rail to the sensor rail.

So give every rail its own name. How depends on your KiCad version (**Help → About KiCad** shows it):

- **KiCad 8 or newer:** press **P**, choose `power:VCC`, place it, then press **E** and change **Value** to the rail name. From version 8 the Value sets the net name. Place a fresh symbol from the library each time rather than copy-pasting a renamed one.
- **KiCad 7 or older:** editing Value only changes the text on screen. The net is still named after the symbol's hidden pin, so every renamed `power:VCC` stays one net called `VCC`. Instead, put a **net label** (**L**) named `VBAT`, `+5V_CPU`, `+5V_SENS` or `+3V3_SENS` on the wire, or make a project power symbol in the Symbol Editor whose pin name is the rail name.

Either way, use the standard `power:GND` for ground everywhere, and never `GNDA`, `GNDD` or `GNDPWR`: those are separate nets and would break the common ground.

**Always check, in any version:** click a wire on each rail and read its net name in the **message panel** at the bottom of the window. `+5V_CPU` and `+5V_SENS` must show different names, and none of the rails may show `VCC`. A merged rail looks perfect on screen but ties the battery straight to every regulator output.

### Step 5: region A, battery input

Press **A**, type the symbol name in the search box, pick it, click to place. Then press **E** on each part to set its **Value** and later its **Footprint**.

1. Place `Connector_Generic:Conn_01x02` as **J1**, value `Battery T-plug pigtail 12AWG`. The battery has a T-plug (Deans) lead; a matching T-plug pigtail with bare 12 AWG ends is soldered into two wire pads on the board. Pin 1 is +, pin 2 is −.
2. Place `Device:Fuse` as **F1**, value `TBD ATM mini blade 10-15A`. Wire J1 pin 1 to one end of F1 with **W**.
3. Press **L** on the wire between J1 and F1 and name it `VBAT_RAW` (the unfused side). Put a `VBAT` power symbol on the other side of F1.
4. Place `Device:D_Zener` as **D1** (KiCad's stock `D_TVS` symbol is bidirectional; a unidirectional TVS is drawn with the Zener symbol), value `TVS unidir. TBD, standoff ≥ 9 V`, from `VBAT` to `GND`, cathode (the bar, pin 1) toward `VBAT`.
5. Place `Device:C_Polarized` as **C1**, value `TBD µF, ≥ 16 V, low ESR`, from `VBAT` to `GND`, + toward `VBAT`. This is the bulk capacitor.
6. Put `power:GND` on J1 pin 2.
7. Press **P**, choose `power:PWR_FLAG`, and put one on the `VBAT_RAW` wire and one on the `GND` wire near J1. A **PWR\_FLAG** tells the checker "power enters here", because a connector pin can't prove that on its own. A flag does not pass through a fuse or ferrite bead, so after the later steps also add one on `LDO_IN` (it feeds U3's power input through FB1), and on `VBAT` and `+6V_BEC`. Without them the checker reports "input power pin not driven" on U1, U2 and U3.

### Step 6: region B, ESC and servo

1. **No ESC power on the board.** The battery feeds the ESC directly on its own 12 AWG leads (up to 20 A motor current), so the board has no J2/F2 and its copper only carries the board's own loads.
2. **J3** `Connector_Generic:Conn_01x03`, value `ESC receiver lead (BEC in)`. The ESC's 3-wire lead carries the throttle signal *into* the ESC and the 6 V BEC power *out*. Pin 1 `GND`, pin 2 net label `+6V_BEC`, pin 3 net label `THROTTLE_PWM`.
3. **J4** `Connector_Generic:Conn_01x03`, value `Servo DS3225MG`. Pin 1 `GND`, pin 2 `+6V_BEC`, pin 3 `STEER_PWM`.
4. **J5** `Connector_Generic:Conn_01x04`, value `Signals to ESP32`. Pin 1 `U1_PG`, pin 2 `THROTTLE_PWM` (GPIO5), pin 3 `STEER_PWM` (GPIO4), pin 4 `GND`. Wire J3's and J4's signal pins straight to J5 (no labels needed inside the region). The `U1_PG` GPIO is TBD until the firmware adds it (`pins.h` and the README pin table change together).
5. Add a text note: `+6V_BEC comes only from the ESC. Never connect to any 5 V rail.`

### Step 7: region C, compute 5 V

1. **No branch fuse:** U1's input sits directly on `VBAT`; the single main fuse F1 protects every board load.
2. **U1** is the Pololu D36V50F5, soldered to the PCB on its 2 × 6, 0.1 in pin grid. Make a symbol `rc_power:D36V50F5` showing all 12 module pins, numbered to match the `PinHeader_2x06_P2.54mm` footprint: 1 `PG` (open collector), 2 `EN` (input), 3–4 `VRP`, 5–6 `VIN` (power input), 7–10 `GND` (power input), 11–12 `VOUT` (one power output, one passive, so ERC doesn't see two outputs fighting). Value `Pololu D36V50F5 buck (req 5.1V ≥6A TBD)`.
3. Join both `VIN` pins to `VBAT`, all four `GND` pins to `GND` and both `VOUT` pins to a `+5V_CPU` power symbol. Each header pin is rated 3 A, which is why every power connection uses its pin pair.
4. Mark both `VRP` pins no-connect (**Q**). VRP is the input after the module's reverse protection; the sensor buck stays fed from `VBAT`, so VRP is unused.
5. **EN** is left unconnected (no-connect flag). The module turns off below 1.2 V and on above 1.35 V, and has a 100 kΩ pull-up to VIN inside it, so unconnected means always on. Never wire EN straight to an ESP32 GPIO: it floats to battery voltage (8.4 V). ESP32 control of EN is archived for now (question 13).
6. **PG** (net `U1_PG`) to J5 pin 1. PG is open-drain and goes low when VOUT is more than 20 % high or 10 % low; the ESP32 reads it with its internal pull-up (3.3 V).
7. The module has input reverse protection to 40 V, so this branch needs no extra reverse-polarity part (question 6 covers the rest of the board).
8. **C2** `Device:C`, value `TBD µF, ≥ 16 V` on `VBAT`; **C3** `Device:C`, value `TBD µF, ≥ 10 V` on `+5V_CPU`.
9. Power LED: **R1** `Device:R`, value `1k5` (about 2 mA), in series with **D2** `Device:LED`, from `+5V_CPU` to `GND`, LED cathode toward `GND`.
10. **TP1** `Connector:TestPoint` on `+5V_CPU`.
11. **J6** and **J7** `Connector_Generic:Conn_01x02`, values `USB-C pigtail > Pi 5` and `USB-C pigtail > ESP32`. Each is a 2-wire USB-C cable with bare ends: the Pi 5 and the ESP32 (left, native USB port) take power through their own USB-C inputs and keep that input protection. Pin 1 `+5V_CPU`, pin 2 `GND`.

### Step 8: region D, sensor 5 V

Same pattern as region C:

1. **U2** `REG_MODULE` value `5 V buck rated 4 A, TBD`, input on `VBAT` (no branch fuse), input cap **C4**, output cap **C5**.
2. VOUT to a `+5V_SENS` power symbol. LED **R2** + **D3**, test point **TP2**.
3. Output headers, each `Conn_01x02` (pin 1 `+5V_SENS`, pin 2 `GND`): **J8** `LIDAR-Lite v4`, **J9** `Camera USB hub`, **J11** `Spare 5 V` (the radar header J10 was removed from scope).
4. `+5V_SENS` also feeds the 3.3 V LDO in region E. A net with the same name joins them; no wire across the sheet is needed.

### Step 9: region E, sensor 3.3 V

The 3.3 V rail is a **linear regulator (LDO)** fed from `+5V_SENS`, not a buck from the battery. KiCad has real symbols for common LDOs, so you don't need the custom `REG_MODULE` here.

1. Put a `+5V_SENS` power symbol at the left of region E. That is the LDO's supply; no separate fuse is needed because the main fuse F1 already protects this branch.
2. Optional noise filter: **FB1** `Device:FerriteBead` in series from `+5V_SENS` to the LDO input, plus **C6** `Device:C` to `GND`, values `TBD`. Leave it in so the reviewer can decide.
3. **U3**: press **A**, search `AP2112K-3.3` (a common 600 mA low-noise LDO, symbol `Regulator_Linear:AP2112K-3.3`) or search `LDO 3.3` and pick a similar one. Value `3.3 V LDO ≥ 300 mA, TBD`. Wire VIN to the filter output (or straight to `+5V_SENS`), GND to `GND`, VOUT to a `+3V3_SENS` power symbol. If it has an EN pin, tie it to VIN unless the datasheet says otherwise.
4. **C7** at the LDO input and **C8** at its output, `Device:C`, values from its datasheet (often 1 µF ceramic each). LDOs can oscillate with the wrong output capacitor, so follow the datasheet exactly.
5. LED **R3** + **D4**, value `680R` for a 3.3 V rail, test point **TP3**.
6. Output headers: **J12** `IMU`, **J13** `Shaft encoder`, **J14** `Spare 3.3 V`.
7. Note: the ESP32's own 3V3 pin must not power these sensors (project rule: the ESP32 powers nothing), and the ESP32 itself stays on `+5V_CPU`.

### Step 10: notes box

In the Notes region, press **T** and add numbered assumptions, for example:

1. Battery: 2S LiPo, 6.0 to 8.4 V, T-plug pigtail (12 AWG) on pads.
2. All fuses and protection values TBD; positions are proposals.
3. Single common `GND`; star point at J1 in layout.
4. `+6V_BEC` is ESC-supplied and isolated from the 5 V rails.
5. Signals are 3.3 V logic or lower.

### Step 11: number the parts and check

1. **Tools → Annotate Schematic… → Annotate.** This replaces any `U?` or `C?` with real numbers. If you numbered by hand as above, it leaves yours alone.
2. **Inspect → Electrical Rules Checker → Run ERC.** Fix every error; for each warning, either fix it or understand why it's harmless. The usual beginner errors are "input power pin not driven" (missing PWR\_FLAG) and "pin not connected" (missing wire or **Q** marker).
3. Click an error in the list and KiCad jumps to it on the sheet.

## Formatting a schematic a reviewer can read

A schematic is read like a page of text: left to right, top to bottom. These conventions are what an experienced engineer expects; breaking them won't stop the board working, but it slows the review.

- **Power flows left to right.** Inputs (battery, connectors in) on the left, outputs on the right.
- **Higher voltage on top, ground at the bottom.** Supply symbols point up, `GND` symbols point down.
- **No four-way wire crossings.** Where four wires meet, KiCad may or may not join them, and a reader can't tell. Use two T-junctions offset slightly instead. A dot means connected; a crossing without a dot means not connected.
- **Labels instead of long wires.** If a wire would cross half the sheet, end it with a net label or power symbol and pick it up again where needed.
- **Every part has a reference and a value.** References follow standard prefixes: J connector, F fuse, U regulator or IC, C capacitor, R resistor, D diode or LED, Q transistor, FB ferrite bead, TP test point.
- **Values say what matters.** A capacitor value includes its voltage rating (`22µF 16V`); a fuse includes its current (`TBD 5A`). Anything unconfirmed says `TBD`, following the project rule of no unconfirmed parameters.
- **Text stays readable.** Don't let labels overlap wires or symbols. Use **View → Show Hidden Pins** off and the default 1.27 mm grid on.
- **Net names are consistent.** Capitals, `+` for positive rails, voltage then purpose: `+5V_CPU`, `+5V_SENS`, `+3V3_SENS`. Write `3V3` rather than `3.3V` because dots can confuse some tools.
- **One sheet is fine here.** KiCad supports **hierarchical sheets** (one sub-sheet per rail, joined by hierarchical labels), which large designs need. For about 40 parts, one A3 sheet with region boxes is easier for you and the reviewer.

### Handing the draft to the reviewer

1. **File → Plot… → PDF**, colour, all pages. This is what most reviewers mark up.
2. Zip the whole project folder, or put it in git. Add `*-backups/`, `*.lck`, `fp-info-cache` and `*.kicad_prl` to `.gitignore`; those are local caches.
3. Send the PDF, the project, the power budget and the open questions (the last section) together.
4. After each review round, bump the title block revision (A, B, C…) and keep the old PDF so changes are easy to compare.

## From schematic to a printed board

The draft for the first review can stop at a clean, ERC-passing schematic. The steps below are what follows, so you know where trace width actually gets set and can talk about it with the reviewer.

### Footprints: the physical shape of each part

A **symbol** is the logical drawing; a **footprint** is the copper pads and holes it needs on the board. **Tools → Assign Footprints…** opens a three-pane window: libraries on the left, your parts in the middle, footprints on the right. Select a part, filter the right pane by typing, and double-click a footprint.

| Part | Search term in the footprint list | Check |
| --- | --- | --- |
| J1 battery (T-plug pigtail) | `SolderWire` (wire pads) | 12 AWG is 3.3 mm²; KiCad's largest stock pad is the 2.5 mm² one (3.0 mm hole, 4.4 mm pad, for 2.4 mm conductors); 12 AWG's conductor likely fits, but its current rating and thin copper ring need checking, so the final pad is TBD |
| F1 | `Fuse:Fuseholder_Blade_Mini_Keystone_3568` (Mini/ATM blade, replaceable; type pending confirmation) | Holder current rating (Keystone 3568 is listed at 20 to 30 A, so confirm it for the suffix ordered; F1 is 10 to 15 A) |
| U1 D36V50F5 | `PinHeader_2x06_P2.54mm` (pin numbering in Step 7) | Check against Pololu's dimension drawing; header pins are 3 A each |
| U2 module | Matches the chosen module | Pin order and spacing from the module drawing |
| U3 LDO | The footprint its symbol suggests (SOT-23-5) |  |
| Q1 (only if the PR's reverse-polarity proposal is adopted) | PowerPAK SO-8 (P-FET) |  |
| J3, J4 servo/ESC | `PinHeader_1x03_P2.54mm` | Standard servo spacing |
| J5 signals to ESP32 | `PinHeader_1x04_P2.54mm` |  |
| J6, J7 USB-C pigtails | `TerminalBlock` 5.08 mm, 2 pin | Clamps 20 AWG; ≥ 5 A per pin |
| J8 to J14 sensor outputs | `JST_XH` 2 pin, or pin headers | About 3 A per pin |
| C, R, LED | `C_0805`, `R_0805`, `LED_0805` (surface-mount, hand-solderable) | Capacitor voltage rating |
| Mounting holes | `MountingHole_3.2mm_M3` (add with **A**, symbol `Mechanical:MountingHole`) | Match the chassis mount |

### Net classes: where trace width is set

A **net class** is a group of nets that share copper rules. Set them in the Schematic Editor under **File → Schematic Setup… → Project → Net Classes**, then use **Netclass assignments** below it to match nets by name. The PCB Editor uses the same table.

| Net class | Nets (pattern) | Track width | Via (drill / pad) | Comment |
| --- | --- | --- | --- | --- |
| `HighCurrent` | `VBAT*`, `GND` | zones on both layers; 6 mm is only the IPC-2221 minimum at +20 °C | 0.6 / 1.2 mm, many in parallel | `GND` carries the board's return current (size it for F1's rating) back to the battery |
| `Power5A` | `+5V_CPU` | 1.5 mm | 0.4 / 0.8 mm | 2 oz copper |
| `Power3A` | `+5V_SENS`, `+6V_BEC` | 1.0 mm | 0.4 / 0.8 mm |  |
| `Default` | everything else, incl. `+3V3_SENS` and signals | 0.25 mm | 0.3 / 0.6 mm | KiCad's default |

The widths assume 2 oz copper and a 10 to 20 °C rise, from the table in the background section. Treat them as a starting proposal for the reviewer.

### Laying out the PCB (the short version)

1. In the PCB Editor, **File → Board Setup… → Board Stackup → Physical Stackup**: 2 copper layers; set copper thickness to 0.07 mm (2 oz).
2. **Tools → Update PCB from Schematic** (F8) pulls all footprints in, joined by thin "ratsnest" lines that show what must connect.
3. Draw the board outline on the `Edge.Cuts` layer with the rectangle tool. Size it to fit the chassis; add M3 mounting holes in the corners.
4. Place parts by region, matching the schematic: battery and ESC connectors on one edge, close together, so the 20 A loop is short; regulators near their outputs; sensor headers on the far side from the ESC.
5. Draw tracks (**X**) using each net class's width, or draw **filled zones** (**Ctrl+Shift+Z**) for `VBAT` and `GND`. Put a `GND` zone over the whole bottom layer.
6. **Inspect → Design Rules Checker → Run DRC**, fix everything, then press **B** to refill zones and run it again.

### Fabrication files

1. **File → Fabrication Outputs → Gerbers (.gbr)…**, click **Plot**, then **Generate Drill Files…** in the same window.
2. Open the output in KiCad's **Gerber Viewer** to check that every layer looks right.
3. Zip the folder and upload it to a fab such as JLCPCB, PCBWay or OSH Park. Choose 2 layers, 1.6 mm thickness, **2 oz outer copper**, HASL or ENIG finish.
4. Order a small batch (often 5) first and bring it up one rail at a time with a bench supply and current limit before ever connecting the LiPo.

## Before you send it, and what to ask

### Self-check

- [ ] ERC runs with zero errors; every remaining warning is understood
- [ ] The two 5 V rails have different net names (click a wire on each and read the message panel)
- [ ] Only `power:GND` is used for ground; no `GNDA`, `GNDD` or `GNDPWR`
- [ ] `+6V_BEC` touches only J3 and J4
- [ ] `PWR_FLAG` on `VBAT_RAW`, `GND`, `VBAT`, `LDO_IN` and `+6V_BEC`
- [ ] Every part has a reference and a value; unknowns say `TBD`
- [ ] Title block filled in, revision `A (draft)`
- [ ] Notes box lists the assumptions
- [ ] PDF plotted and checked for overlapping text

### Open questions for the reviewer

Put these in your hand-off message, numbered, so the reviewer can answer by number.

1. **20 A path (resolved):** the ESC is powered off-board, straight from the battery on its own 12 AWG leads. The board carries only its own loads, about 7.3 A worst case, so `HighCurrent` (6 mm, zones) is now oversized: should it be resized for F1's rating (about 16.5 A at 15 A, 11 A at 10 A) rather than the 7.3 A load?
2. **Fuses (resolved, rating open):** one replaceable main fuse F1 (Mini/ATM blade in a Keystone 3568 PCB holder; type pending confirmation) protects every board load. There are no branch fuses, because the fuse inventory is high-current. Trade-off: a sensor-branch short now opens F1 and drops compute too; U1 and U2 limit their own output current. Rating: 10 A or 15 A, against about 7.3 A worst-case board load (15 A keeps 7.3 to 7.8 A under 75 % of the rating; a 10 A fuse sits at 73 to 78 %). A standard MINI fuse (ISO 8820-3: 200 % opens in 0.15–5 s) rides through the board's capacitor inrush, so slow-blow isn't needed; the motor is off-board.
3. **Compute rail and the Pi:** the Pi 5 and ESP32 need about 5.5 A. The Pi takes power through a 2-wire USB-C pigtail, so it keeps its USB-C input protection but gets no USB-PD 5 A offer: it limits its USB ports to about 0.6 A total unless set in `config.txt`. Is that acceptable?
4. **Regulator U1:** the D36V50F5 outputs 5.0 V ± 4 % (not the Pi's preferred 5.1 V) and is rated 5.5 A typical. What is its dropout at 5.5 A with the battery near 6.0 V? Its VRP output is deliberately unused (the sensor buck stays on `VBAT`, because VRP would push about 7.3 A through U1's 6 A-rated VIN pin pair).
5. **IMU noise:** is the LDO's noise rejection enough at the sensor buck's switching frequency, or should the ferrite-bead filter in front of it stay?
6. **Protection:** U1 has its own reverse protection to 40 V, and so does the proposed U2 (D24V50F5). The rest (C1, D1) is exposed. The PR proposes Q1 (P-FET) + R4 between F1 and `VBAT`; it is not drawn yet. Adopt it for rev A? TVS proposed: SMBJ10A.
7. **Low battery:** the ESC's low-voltage cutoff stops the motor, but the regulators keep draining the pack. Add a resistor divider from `VBAT` to an ESP32 ADC pin so firmware can warn or shut down? A 100k / 33k divider gives about 2.1 V at 8.4 V.
8. **ESP32 back-feed:** the ESP32 gets 5 V on its left USB-C port (J7) and may also be connected by USB on its right COM port (to the laptop now, the Pi later). Does the dev board keep the two USB power inputs apart, or is a diode or a data-only cable needed?
9. **Cameras:** cameras plugged into the Pi draw from `+5V_CPU`. Move them to a powered USB hub on `+5V_SENS` (J9)?
10. **ESC and servo:** the repo's ESC manual confirms a 6 V / 3 A switch-mode BEC, and the servo datasheet gives 2.3 A stall at 6.8 V, so it fits with about 0.7 A to spare. Is that enough margin, or should the servo get its own buck?
11. **Layout:** where the ground star point should sit, and how to keep motor return current away from the sensor ground.
12. **Connectors and wire:** the board's battery feed is a T-plug pigtail with 12 AWG bare ends soldered to J1's pads. What pad size and strain relief? Wire gauge for each output?
13. **U1 enable control (archived):** EN is left unconnected, so U1 is always on. Any future ESP32 control must not touch EN directly (100 kΩ pull-up to VIN, up to 8.4 V), and U1 powers the ESP32, so U1 must start by itself. Options kept for later: a shutdown FET (power-cycles only), an enable on the sensor buck, a VIN-divider undervoltage cutoff on EN, or a latching power switch.
14. **USB-C pigtail cable:** the pigtails are 20 AWG, 30 cm (1 ft), and can be trimmed. 20 AWG is about 33 mΩ/m, so a 30 cm cable (60 cm of copper, there and back) loses about 0.10 V at 5 A; trimmed to 15 cm, about 0.05 V. USB-C contact resistance adds a little more. With U1 at 5.0 V ± 4 % (4.8 V worst case), trimming to 10–15 cm keeps the Pi 5 comfortably above its undervoltage warning (about 4.63 V, approx.). Is that margin enough?

### Verification record

On 2026-10-28 this guide's schematic steps were rebuilt as a KiCad 7.0.11 file and checked with the open-source [kicad-happy](https://github.com/aklofas/kicad-happy) analyzer (v2.3.2) and ngspice 42.

| Check | Result |
| --- | --- |
| Every symbol and footprint name in this guide exists in the standard KiCad libraries | Pass |
| Rails stay separate when named with net labels | Pass: `VBAT`, `+5V_CPU`, `+5V_SENS`, `+3V3_SENS` and `GND` are distinct |
| Renaming `power:VCC` by its Value in KiCad 7 | **Fail:** all four rails merged into one `VCC` net; Step 4 now gives per-version instructions |
| `PWR_FLAG` only at J1 | Warning: nets after each fuse and the ferrite bead had no power source; Step 5 now adds flags |
| Regulators recognised (U1, U2 switching; U3 LDO at 3.3 V) | Pass |
| SPICE checks (bulk and output capacitor impedance, power-up of each output) | 10 of 10 pass; regulator loop stability is not simulated |
| Analyzer's own power budget | Not usable: it can't see loads on connectors, so the hand-written budget in this guide stays the reference |
| "U3 missing input capacitor" | False positive: the analyzer lists C7 as U3's input capacitor elsewhere in the same report |

### Sources

- [KiCad download](https://www.kicad.org/download/) and the official [KiCad documentation](https://docs.kicad.org/) (Schematic Editor and PCB Editor manuals)
- Trace widths: IPC-2221 formula as implemented in KiCad's Calculator Tools; device currents marked "approx." are from memory and need datasheet checks
- Project facts (pins, ESC, servo, battery): `.claude/CLAUDE.md` and `docs/datasheets/` (ESC manual, servo datasheet, Pololu D36V50F5 page, `components_list.xlsx`)

* Power-symbol naming by KiCad version: tested directly in KiCad 7.0.11; the version 8 change is from KiCad forum threads ([two 3.3 V sources](https://forum.kicad.info/t/two-3-3v-different-sources/47769), [arbitrarily named power symbols](https://forum.kicad.info/t/can-you-create-arbitrarily-named-power-symbol-without-creating-new-library-component/62136)), not yet checked against the official version 8 or 9 manual
* IPC-2221A and IPC-2152 notes: kicad-happy's `standards-compliance.md` reference
