# Rev3 milling: brief for the lab tech (B.Cu and F.Cu, rest machining)

Status: active, 2026-11-20. Archive to `docs/archive/plans/` after the rev3 milling.

## Context
The lab tech imports `pcb/src/rc_power_board.kicad_pcb` into Fusion 360 and posts a `.cnc` file for the Carvera. The inventory changed during the rev3 milling (findings F-001 to F-004, draft PR #22). This brief lists only the facts that the CAM plan needs. Owner of each value: `docs/techctcarvera/milling.toml`. Log: `docs/pcb/releases/rev3/milling_findings.md`.

## Board
- 66 x 140 mm, 2 layers, 2 oz copper (0.070 mm), FR-4 1.57 mm, blank 4 x 6 in. No plated holes.
- B.Cu: most tracks, the power zones, the GND pour, the SMD parts (U3 SOT-23-5, D1 SMB, the 0805 inductor). Wires are soldered on B.Cu.
- F.Cu: GND pour (`GND_F`) and the `U1_PG` jumper (7 segments). F.Cu has no copper on THT pads.
- 3 rivet vias (EasyContac 0.8, 1.1 mm hole): (39.6, 49.8), (3.4, 52.1), (8.1, 137.9) mm from the board lower-left corner.

## Tools
| Tool | Use | Cut width |
|---|---|---|
| T2 V-bit, Makera C1-BIT-ENGRAVE-M-30-0.2 (0.2 mm tip, 30 deg per side) | isolation on both sides, all gaps | 0.292 mm at 0.08 mm |
| 0.2 mm micro end mill (10 pcs, 2.5 mm cutting length) | rest pass in narrow gaps. New, no CAM data, no cutting data | 0.2 mm |
| 0.6 mm corn bit (smallest corn) | wide clearing only | ~0.6 mm |
| T4 3.175 mm end mill | dowels, bores | n/a |
| T5 0.3 mm face bit | face, as in the template | n/a |

Cut depth: 0.08 mm, one pass (copper 0.070 mm: margin only 0.01 mm). Spindle max 15000 rpm.

## Rest-machining order (recommended)
1. Wide tool first: 0.6 mm corn bit where the gap is 1.1 mm or more (0.6 mm + 2 x 0.25 mm error).
2. Rest with T2 (2D Contour or Trace) on all other boundaries. Fusion 2D rest uses the previous tool geometry, not the real stock: give it the corn bit as the previous tool.
3. Optional 0.2 mm micro end mill only where T2 leaves copper.
4. Never send the corn bit into these gaps (it cannot cut them):
   - U3 (SOT-23-5, B.Cu): 0.34 to 0.35 mm.
   - Wire pads J3, J4, J5, J8, J9, J11 to J14: 0.6 mm.
   - U1/U2 VOUT to GND: 0.64 mm. A bridge here shorts 5 V to GND.

## Holes
| Drill | Count | Note |
|---|---|---|
| 0.8 | 16 | C2 to C9. Not in the template drill ops: add |
| 1.0 | 52 | in template |
| 1.1 | 3 | rivet vias, in template |
| 1.3 | 4 | J6, J7. Not in template: add |
| 1.4 | 8 | F1. Not in template: add |
| 3.4 bore (T4) | 7 | H1 to H4, J1, F1 peg |
| 4.2672 bore (T4) | 2 | dowels. Template Bore1 still 4.191 mm: change (F-001) |

The template 0.9 mm drill op is not used by rev3. Each drill is a manual tool change (all drills run as T4).

## Setups and flip
- A: bore the dowels. B: first side (isolation, drills, face). C: flip on the dowels, second side.
- Dowel play is now about 0.27 mm. Annular rings 0.45 to 0.8 mm: a large shift breaks rings.
- Mirror once only. Setup C does the flip. Check the mirror state of B.Cu after the Fusion import (not verified for a KiCad import). Check: a drill hole must be in the center of its pad on both sides.
- Cut the outline last, or use tabs.

## Open (lab tech)
- F-004: Fusion limits the chamfer-mill tool type in some operations. Send the Fusion version, the operation and the error text.
- Feeds and speeds for the 0.2 mm micro end mill: the seller gives none.
- `Carvera.cps` post: the repo does not have it.

