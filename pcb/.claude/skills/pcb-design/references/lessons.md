# Lessons from the rev1 power board

Each lesson has the event that caused it. Sources: PR #3, `docs/pcb/README.md`, `docs/pcb/releases/rev1/review/README.md`, the git history of `pcb/` (before 2026-11-16 the project was in the schematics directory under `docs/`). Add a lesson when a review finds an error that a rule could prevent.

## Owner rules (PR #3, 2026-11-14)
1. **Wire the schematic.** Draw wired connections between the parts of a region, so a person can follow the circuit. Use one label for each bus. Labels alone connect regions, not parts in one region.
2. **Part choice.** Prefer redundancy, consistency, availability, a known manufacturer and reliability. Example: U1 and U2 are the same Pololu module, so one spare serves the two rails.
3. **One connector family.** Use the same header type across the board (JST-XH here), with one written pin-order rule. Each exception has a written reason.
4. **Think about the physical use.** Vibration, heat, battery capacity and cutoff voltage, start currents, wire gauge, service access.
5. **Holes for milling.** When a hole size is not sure, choose the smaller size. The lab makes the hole wider in a second pass if the part does not fit.

## Requirements and parts
6. **Add each new load to the budget on the day it arrives.** The Mapper lidar put `+5V_SENS` at 4.6 A on a 4 A regulator. No table had the load.
7. **Read the connector from the datasheet figure, not from memory.** The first Mapper note gave a 2-pin receptacle. The device has a USB-A socket.
8. **Check the lifecycle before you propose a part.** The proposed D24V60F5 was discontinued.
9. **Check a regulator at the minimum input voltage.** Dropout of about 1.0 V at 5 A leaves no margin for a 4.8 V load at the 6.0 V battery cutoff. This became a bench check.
10. **A measurement is stronger than a label.** The rivet bag label "0.8" was the inner diameter. The caliper gave 1.0 mm outer diameter.
11. **An unknown value stays `TBD`.** Never write a typical value as a fact. Size the fuse for the load and the copper for the fuse rating.
12. **A current "at 100 % of the pin rating" is not "within rating".** Write the percentage.

## Schematic
13. **Each rail is a project power symbol** with pin name, Value and net name equal. A stock `power:` symbol with a changed Value gives different nets in different KiCad versions.
14. **A net behind a fuse or a ferrite needs a PWR_FLAG**, or ERC reports a power input with no source.
15. **Do not save the project with an older KiCad.** Run `kicad-cli` in the pinned image with the stock library tables. Without them ERC gives about 111 false library warnings.
16. **Draw a module with all its pins.** Use pin pairs for current above one pin's rating. Put a no-connect flag on each unused pin.

## Board
17. **A module footprint shows the real body.** U1 had a pin-header footprint. Its 25.4 mm body covered J6 and J7 and went 3 mm over the board edge. No check found it, because no courtyard existed.
18. **DRC, ERC and the milling check do not measure copper width along a current path.** The record said "GND trunks at least 6 mm". The real neck was 0.59 mm. The opening test (`check_board.py` `PATH_ROWS`) now checks it.
19. **A document statement needs a check that can fail.** If you write a dimension, name the check that gives it.
20. **Connector pin order decides if a net routes on one layer.** Do a planarity check of the edge pins before placement. A turned connector is cheaper than a rivet.
21. **Plan the power copper. Let the router do the signals only.** Power nets are zones in `placement.py`. The router does not place vias.
22. **The router is not deterministic.** Do not route a reviewed board again from zero. Use the sync tools.
23. **Keep the rivet count low.** Each rivet is pressed and soldered by hand on the two sides. No rivet in a part courtyard.
24. **Overlapping zones of one net are one piece.** Join the fills before an island or a split test.

## Milling (holes are not plated)
25. **DRC clean does not mean millable.** The V-bit cut width at the cut depth sets the minimum gap.
26. **No F.Cu copper on a THT pad.** The joint is on B.Cu. SMD parts go on the routing side.
27. **A hole between the largest drill and the smallest bored hole cannot be made** (the lab file gives the two values). Change the footprint drill.
28. **Get the lab's CAM file early.** It gave the stock size, the dowel positions, the flip axis, the origin of each setup, the bits and the depth. The first board frame was wrong for it.
29. **A CAM "taper" angle can be the angle of one side or the included angle.** Fusion uses the angle per side: the tool drawing in its tool library shows it. For a different CAM tool, check the two readings until a drawing or a document decides.
30. **A cut depth close to the copper thickness leaves a small margin** (0.01 mm on the first board). The lab tech decides if that is sufficient. The agent does not change the limit.
31. **KiCad's native DXF draws pads, tracks and fills as overlapping outlines.** A contour cut needs one merged outline for each copper island (`fab_export.py`).
32. **State the frame of each fab file:** origin, axis, units, top view or bottom view, mirror state. Test the hole positions against a second export.

## Process
33. **An analyzer finding is a claim.** Check it in the raw file. Record each false positive with its reason.
34. **The main session implements. `pcb-reviewer` reviews with a fresh context.** An agent's "passes" is not evidence: the main session runs each check again before the report.
35. **Lab limits live in one file with `status` and `source`** (skill `pcb-mill`). Never change a limit to make a board pass.
36. **Two owner gates:** the plan before the schematic, the schematic before the board.
## Fable review (2026-11-15)
37. **An exemption in a check hides findings.** The path-width test counted all copper within 2.5 mm of a narrow pad. It hid two necks of 1.9 mm by 6.9 mm, and the record said 6.39 mm. A check prints the value with the exemption and without it, or has no exemption.
38. **A check must fail when it has nothing to check.** The path-width test passed for a net with no copper and for missing pads.
39. **Read a graph at the point where its curve starts.** The record said "7.4 A at 6 V in". The curve starts at 6.6 V in. No data is not a value.
40. **Check each regulator against the cutoff voltage, not only the one with the largest load.** The dropout flag was on U2 only. U1 feeds the Pi and has the same dropout.
41. **A check uses only the tools that the lab CAM uses.** The gap check used a 0.1 mm tip bit that the lab CAM does not have.
42. **Isolation milling leaves the copper between the contours.** Ask the lab for a pocket operation where a floating piece lies between pads of different nets. Bare copper on the two faces needs insulation from the chassis and from module undersides.
43. **Do not commit build debris.** A 90 MB Python core dump (file `core.1` in the schematics directory) was committed with a tool change. Run `git status` and read the file list before each commit.
44. **Measure the gaps after a clearance exception.** A pad clearance applies to all zones of other nets, not only to the planned zone. The U1 and U2 exception (`zones = true`, 0.64 mm) let the GND pours come to 0.64 mm of the VOUT, VIN and VRP pads. DRC and the milling check passed, because the exception allowed it. Scan the gaps of the pours and the zones at the part after each exception.
45. **Make the router result repeatable before a fix of a routed track.** Freerouting with more than one thread gives a different route from one run to the next. A fix that passed in one run failed in the next. Use `-mt 1`, then fix the placement.
