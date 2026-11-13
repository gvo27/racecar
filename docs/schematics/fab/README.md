# Fab outputs for the lab's Fusion 360 template

Made by `make pcb-fab` (`tools/fab_export.py`) from `rc_power_board.kicad_pcb`. `make pcb-fab` also runs `tools/test_fab.py`. `make pcb-test` fails if these files are not current. Do not edit them by hand. The CAM stays in the lab template; these files are its inputs.

KiCad's own DXF export is not used. It puts drill circles on Edge.Cuts, and it writes pad, track and zone outlines as separate overlapping lines. A contour along a pad circle inside a pour would cut the copper.

## Files

| File | Content |
| --- | --- |
| `rc_power_board-F_Cu.dxf` | All copper of F.Cu as one union: closed LWPOLYLINE loops (outer loops, and the holes of the pour). DXF layer `F.Cu`. No drill circles, no text |
| `rc_power_board-B_Cu.dxf` | The same for B.Cu. DXF layer `B.Cu`. Not mirrored |
| `rc_power_board-Edge_Cuts.dxf` | The board outline: one closed loop. DXF layer `Edge.Cuts` |
| `rc_power_board.drl` | Excellon, metric, decimal coordinates, one tool per diameter. A comment line names the use of each tool. The 2 dowel holes are their own tool (4.191 mm) |
| `rc_power_board-drl_map.dxf` | One circle per hole at its true diameter. One DXF layer per tool: `DRILL_<d>`, `BORE_<d>`, `DOWEL_4.191`. It imports into Fusion like the demo's drill map |

All DXF files are ASCII, R2000 (AC1015), units mm. A THT pad is solid copper in the copper files: the hole is not cut out of it (the drill comes after the isolation cut).

## Frame

All files use the lab frame. The origin is the center of dowel 1 (the Fusion Setup B WCS). X runs along the stock long side. The view is from the top. Units are mm.

- Stock: 152.4 x 101.6 mm (4 in x 6 in), Kepro P22-465G 2 oz, 1.57 mm.
- Dowel 1: (0, 0). Dowel 2: (145.8468, 0). Diameter 4.191 mm for 4.0 mm pins.
- The board is turned 90 degrees counter-clockwise (top view) and centered on the stock. The board length (140 mm) runs along stock X, with 6.2 mm at each end. The board width (66 mm) runs along stock Y, with 17.8 mm at each long side. The board +Y end (the J14 side) points to stock -X (dowel 1). The board +X side points to stock +Y. The J1 end is at the dowel 2 side.
- In the lab frame the outline is X 2.9234 to 142.9234 mm and Y 13.99 to 79.99 mm. The dowel holes are outside the board: the distance from a dowel hole edge to the outline is 11.9 mm (about 14.0 mm from the dowel center).
- The KiCad board does not move. The turn is an export transform (`placement.board_to_lab`). For review, the stock outline and the two dowel holes are drawn on the `Dwgs.User` layer of the board. They are not exported.

## Mapping to the lab template

| Lab setup | Input |
| --- | --- |
| Setup A (bore the dowels) | The `DOWEL_4.191` layer of the drill map, or the 2 dowel holes of the Excellon file. The template already has them |
| Setup B (top, WCS = dowel 1) | `-F_Cu.dxf` for the isolation contour; `.drl` and the drill map for the holes; `-Edge_Cuts.dxf` for the outline |
| Setup C (bottom, WCS = dowel 2, flipped about the stock Y axis) | `-B_Cu.dxf` as it is. Setup C does the flip. Do not mirror the file |

## Tools

| Diameter | Use |
| --- | --- |
| 0.8, 1.0, 1.1, 1.3, 1.4 mm | Drill. All are in the owner's bit set (0.1 to 2.0 mm) |
| 3.4 mm | Bore with the 3.175 mm end mill: H1 to H4 (M3), J1 wire pads, F1 locating peg. Holes from 2.0 to 3.3 mm cannot be made |
| 4.191 mm | Dowel, bored in Setup A |

Check the hole list in `rc_power_board.drl` (comment lines) and the console output of `make pcb-fab`.
