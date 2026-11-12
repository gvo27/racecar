# Pololu 5V, 9A Step-Down Voltage Regulator D24V90F5 (U2, `+5V_SENS`)

Sources (read 2026-11-11):
- Product page: https://www.pololu.com/product/2866 (specs: https://www.pololu.com/product/2866/specs).
- Dimension drawing "Pololu 5V, xA Step-Down Voltage Regulator D24VxF5", items 2865 and 2866, dev code reg15b, 21 September 2018: [pololu_d24vxf5_dimensions.pdf](pololu_d24vxf5_dimensions.pdf) (original: https://www.pololu.com/file/0J1581/step-down-voltage-regulator-d24vxf5-dimensions.pdf).
- Graphs from the product page: [dropout](pololu_d24v90f5_dropout.png), [max continuous current](pololu_d24v90f5_max_current.png), [efficiency](pololu_d24v90f5_efficiency.png).
- Photos from the product page: [top view with labeled pinout](pololu_d24v90f5_pinout_top.jpg), [bottom view with labels](pololu_d24v90f5_bottom.jpg).
- Not archived (link only): drill guide DXF https://www.pololu.com/file/0J915/reg15b02-drill.dxf, STEP model (5 MB) https://www.pololu.com/file/0J1582/step-down-voltage-regulator-d24vxf5.step.

Status: **assumed U2 part** (owner, 2026-11-11), not bought. It replaces the proposed D24V60F5 (#2865), which Pololu marks discontinued and names the D24V90F5 as its replacement. Both use the same PCB (reg15b) and the same drawing.

## identity
- manufacturer: Pololu
- model: D24V90F5, item #2866
- type: synchronous buck module, fixed 5 V
- pcb_dev_code: reg15b (markings "0J8008", blank white box)
- price: US$36.82 (qty 1), "Rationed (Active)", backorders allowed (2026-11-11)

## specs
| parameter | value (quoted from Pololu) |
| --- | --- |
| input voltage | 5 to 38 V |
| output voltage | 5 V fixed, "4% accuracy" (4.8 to 5.2 V) |
| continuous output current | 9 A (typical; "limited by thermal dissipation"); "typical maximum continuous output current between 4 A and 8 A" |
| max continuous current vs VIN (graph, no heat sink or air flow) | about 6.7 A at 6.5 V in (lowest point on the graph), about 8.1 A at 9 V in |
| dropout | "varies approximately linearly with the load from around 500 mV to 1.5 V". Graph: about 1.0 V at 5 A, about 0.95 V at 4.6 A |
| switching frequency | about 470 kHz, lower at light load |
| quiescent current | 800 µA typical no load. 15 mA max (typical worst case, VIN near 5 V) |
| efficiency | 80 % to 95 % |
| protections | reverse voltage, over-current, short circuit, over-temperature (about 160 °C), soft-start, under-voltage lockout (below 4.2 V typical) |
| size | 40.6 x 20.3 x 7.6 mm (1.6" x 0.8" x 0.3"). PCB 1.57 mm. Parts 6.1 mm high |
| weight | 4.8 g |
| output ripple | not published: **TBD** (bench) |

## pins
- **ENABLE:** pulled up to reverse-protected VIN through 100 kΩ, so the module is on by default. Below 0.6 V = low-power state. Pololu: "If you do not need this feature, you should leave the ENABLE pin disconnected." This board leaves EN unconnected (no-connect).
- **PG:** open drain, low when VOUT falls below 90 % (4.5 V). Needs an external pull-up. Not used on this board.
- **FB:** a resistor from FB to VOUT lowers the output. Not used.
- **VOUT (signal-row pin):** "not intended to source much current". The load current goes through the two VOUT pins at the output end.
- **Larger holes:** 2 pairs for the included 2-pin 5 mm terminal blocks. Hole diameter not given on the drawing: **TBD**. Not used on this board.
- **Mounting:** 4 x 2.18 mm holes for #2 or M2 screws, 15.2 x 35.6 mm apart. Not used on this board (the header pins carry the module).

### Hole positions for the KiCad footprint (top view, component side up)

Converted from the drawing's bottom view (view 2) and checked against the labeled photos. Origin = module centre. X is along the 40.6 mm length, with the VIN end at -X. Y points down (KiCad), with the signal row at -Y. All 12 holes are 1.02 mm on a 0.1" grid (footprint drill 1.0 mm, assumed bit set).

| Pin | X (mm) | Y (mm) |
| --- | --- | --- |
| GND (input end) x2 | -15.22 | -3.82, -1.28 |
| VIN x2 | -15.22 | +1.26, +3.80 |
| GND (output end) x2 | +15.22 | -3.82, -1.28 |
| VOUT x2 | +15.22 | +1.26, +3.80 |
| ENABLE | -7.60 | -8.88 |
| PG | -5.06 | -8.88 |
| FB | -2.52 | -8.88 |
| VOUT (signal) | +0.02 | -8.88 |

Drawing tolerances: drill location ±0.1 mm, board edge ±0.3 mm. Check the footprint against the real module (1:1 print) before milling.

## fit to this board
- **Current:** `+5V_SENS` load 4.6 A running, 4.9 A at Mapper startup: inside the 6.7 A graph value at 6.5 V in. VIN, VOUT and GND each use a pin pair, because a 0.1" header pin carries about 3 A. VOUT: about 2.45 A per pin at 4.9 A. VIN: about 2.1 A per pin at 4.26 A (6.0 V in).
- **Dropout risk at the 6.0 V cutoff:** from the graph, 5 V out at 4.6-5 A needs about 5.95-6.0 V at VIN. The F1 and trace drop come on top of this. At the 2S cutoff (6.0 V) the output can fall below 5 V. With the -4 % tolerance (4.8 V) the Mapper's 4.8 V minimum has no margin. **Bench check:** measure the voltage at J11 during Mapper startup with the pack near 6.0 V. Possible mitigations (owner decision, not designed in): raise the low-voltage cutoff, or move the Mapper to a supply with lower dropout.
- **Ripple:** not published. C9 (>= 100 µF low-ESR) at J11 is still needed for the Mapper's 50 mV limit. Bench check.
- **Reverse polarity:** built in (rev A has no board-level protection, owner decision 2026-11-11).
