# Milling check: rule ids

The rules of `tools/milling_check.py` in the lab directory. Limits come from `milling.toml` and `design_rules.toml` (keys in backticks). The last four rows read the design rules of the board (`design_rules.toml`: board directory, else lab directory; `pcb/libraries/rules.py`).

| Id | Check | Severity |
| --- | --- | --- |
| MILL-GAP | Every copper-to-copper gap on one layer (track, pad, via, zone fill; same footprint included) between different nets >= the narrowest isolation bit's cut width at worst-case depth (depth max + depth error): `w = tip + 2 * d * tan(angle / 2)` | error |
| MILL-GAP-BIT | Gaps that only some bits can cut. Lists the area and the bits that fit, so the CAM step uses the right bit there | warning |
| MILL-DEPTH | Min depth (depth min - depth error) >= copper thickness, so each cut goes through the copper | error |
| MILL-DRILL | Every hole is in the drill set, or is > the largest drill and >= the smallest end mill (milled) | error |
| MILL-ANNULAR | Annular ring >= the configured minimum on every THT pad and via | error |
| MILL-FCU-THT | No F.Cu track or zone fill touches a THT pad (holes are not plated; the joint is on B.Cu) | error |
| MILL-VIA | Every via has the rivet drill and pad from the config | error |
| MILL-SLIVER | Copper narrower than the min track width, made by zone fill (zero-width slits from the zone filler are closed first) | warning |
| MILL-ISLAND | Zone islands with no net connection. The check joins the fills of all zones of one net on one layer (and their tracks and pads) first, so overlapping bus zones are not islands | warning |
| MILL-EDGE | Copper-to-board-edge distance >= the configured edge clearance | error |
| MILL-RIVET-ACCESS | A rivet via must be solderable on both sides: no via inside the courtyard of an F-side part (its body covers the top joint) or of a B-side part | error |
| MILL-CONN-EDGE | Each connector (J*) courtyard is within the configured distance of the board edge (wire entry outward) | warning |
| MILL-GAP (design rules) | With design rules that have a `horizontal_error`: each gap >= cut width + 2 x `horizontal_error` | error |
| MILL-GAP-FIXED | A gap below that value that the footprint fixes: two pads of one part, or zone fill at a pad of a part with an `[[exception]]` that has `zones = true`. Listed for the lab tech. A track or a pad of another part near such a pad is a `MILL-GAP` error | warning |
| MILL-CUT-SPACING | Tracks and zone copper narrower than the copper target (`cut_spacing_min` - `clearance`). Shows the thin areas | warning |
| MILL-COMP-GAP | Pads of two different parts on different nets are at least `component_gap` apart. Parts with an `[[exception]]` are included | error |

