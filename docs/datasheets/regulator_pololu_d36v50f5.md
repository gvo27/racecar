# Pololu 5V, 5.5A Step-Down Voltage Regulator D36V50F5 (U1 `+5V_CPU` and U2 `+5V_SENS`)

Sources (read 2026-11-12):
- Product page: https://www.pololu.com/product/4091. The saved page is `Pololu - 5V, 5.5A Step-Down Voltage Regulator D36V50F5.htm` in this folder.
- Dimension drawing "D36V50Fx Step-Down Voltage Regulator", items 4090 to 4095, dev code reg24d, 24 December 2019: [pololu_d36v50fx_dimensions.pdf](pololu_d36v50fx_dimensions.pdf) (original: https://www.pololu.com/file/0J1732/d36v50fx-step-down-voltage-regulator-dimensions.pdf).
- Graphs from the product page: [efficiency](pololu_d36v50f5_efficiency.png), [max continuous current](pololu_d36v50f5_max_current.png), [dropout](pololu_d36v50f5_dropout.png). Photo with the labeled pinout: [pololu_d36v50f5_pinout_top.png](pololu_d36v50f5_pinout_top.png).

Status: **both regulators on the board** (owner decision 2026-11-12). The owner has two modules. The same part on both rails also gives a swap spare. This replaces the D24V90F5 assumption for U2 (`regulator_pololu_d24v90f5.md`, superseded).

## identity
- manufacturer: Pololu
- model: D36V50F5, item #4091
- type: synchronous buck module, fixed 5 V
- price: US$39.95 (qty 1)

## specs
| parameter | value |
| --- | --- |
| input voltage | 5.5 to 50 V (limited by dropout at the low end) |
| output voltage | 5 V, +-4 % |
| continuous output current | 5.5 A typical |
| max continuous current vs VIN (graph, no heat sink or air flow) | about 7.4 A at 6 V in, about 8 A at 8.4 V in |
| dropout | about 1.0 V at 5 A (graph) |
| reverse-voltage protection | to 40 V |
| header pin current | 3 A per pin |
| size | 25.4 x 25.4 mm. PCB 1.57 mm. Parts 6.1 mm above the module PCB, 1.8 mm below it |

## pins and footprint
- 12 pins in 2 rows of 6, 2.54 mm pitch, hole 1.02 mm. The pin row runs along one edge. The outer row is 1.27 mm from that edge. The inner row is 2.54 mm further in (3.81 mm from the edge). The end pins are 6.35 mm from the two side edges (the 6 pin pairs are centered on the edge).
- Each power function uses a pin pair (one pin per row). Along the edge, top view with the pin edge on the left: VOUT, GND, GND, VIN, VRP, then EN (outer row) and PG (inner row).
- 3 mounting holes, diameter 2.18 mm (#2 or M2 screws), 2.2 mm in from the edges. Top view with the pin edge at the bottom: the holes are at the top-right, bottom-left and bottom-right corners. The module body is always on the inner-row side of the pins.
- Symbol `rc_power:D36V50F5` pin numbers (odd = inner row, even = outer row): 1 PG, 2 EN, 3-4 VRP, 5-6 VIN, 7-10 GND, 11-12 VOUT.
- Footprint `rc_power:Pololu_D36V50Fx` (`docs/schematics/rc_power.pretty`): origin = pad 1, pin edge on the right, body on the inner-row side. F.Fab shows the full 25.4 x 25.4 mm body and the 3 mounting holes (circles only, no drill: the drill set has 4 sizes and the header holds the module). F.CrtYd is the body plus 0.25 mm. Test: `docs/schematics/tools/test_footprint.py`.
- Drawing tolerances: drill location +-0.1 mm, board edge +-0.3 mm.

## fit to this board
- **U1 (`+5V_CPU`):** Pi 5 and ESP32, about 5.5 A budget. EN and VRP not connected. PG goes to J5.1.
- **U2 (`+5V_SENS`):** 4.6 A running, 4.9 A at Mapper startup. The graph shows about 7.4 A at 6 V in and about 8 A at 8.4 V in, so the rule "U2 >= 6 A" is met at 6-8.4 V in. EN, VRP and PG not connected.
- **Dropout risk at the 6.0 V cutoff:** the dropout is about 1.0 V at 5 A. At the 2S cutoff (6.0 V) the output can fall below 5 V, and the Mapper needs at least 4.8 V. **Bench check:** measure the voltage at J11 during Mapper startup with the pack near 6.0 V.
- **Ripple:** not published (**TBD**). C9 (>= 100 uF low-ESR) at J11 stays.
- **Pin current:** VIN, VOUT and GND each use a pin pair (3 A per pin). U2 VOUT at 4.9 A is about 2.45 A per pin. U2 VIN is about 2.1 A per pin at 6.0 V in.
- **Standoff (open check):** the module has parts 1.8 mm below its PCB. The F.Cu GND pour is under the module and has no solder mask on the milled board. Check the module standoff on the real header (1:1 print and a mock-up) before milling.
