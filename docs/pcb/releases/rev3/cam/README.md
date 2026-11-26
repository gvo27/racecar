# Rev3 lab CAM file: facts read from `rc_power_board.f3d`

The lab tech made this Fusion 360 CAM file to mill the rev3 board (`pcb/src/rc_power_board.kicad_pcb`). The owner received it on 2026-11-25. The milling run from this file failed (findings: [`../milling_findings.md`](../milling_findings.md), F-005). So this record is the CAM of a failed run, not a reference. Only the dowel frame is a lab standard: the same dowels serve every job on this machine (owner, 2026-11-25).

- File: `rc_power_board.f3d`, 5.7 MB, sha256 `7593ef6aaffc2c39a0adc5f657b7041934ba875e051b4dbf642e01201091c6ce`. Not in git: the CAM logs in the file hold a user name of the lab PC, and the repo is public. The owner keeps the original.
- Fusion CAM 2706.1.17. Toolpaths generated 2026-11-20. Machine: Makera Carvera 3-axis, post `user://Carvera.cps`, 6-tool changer, air coolant only.
- The design comes from a KiCad export (components `rc_power_board`, `rc_68D_PCB`, `rc_68D_copper`). The stock is the model body (`job_stockMode = solid`), not a box.
- Status of each value: **read** = from the CAM XML (`theIronDoc.irondoc`). **decoded** = from the toolpath float data with a heuristic decoder (record tags `d`/`k` + 3 float32). Decoded values agree with the XML where both exist (hole counts, depths of the drill cycles).

![Lab CAM preview: blank sketch with the two dowels on one long edge, board at the far long edge](preview.png)

## Dowel frame (lab standard)

| Item | Value | Status |
| --- | --- | --- |
| WCS origin of each setup | A sketch point (`wcs_origin_mode = point`). Setup5 (top): sketch point ref 285. Setup3 (bottom): sketch point ref 1 | read |
| Flip | Setup3 = `axesZY`, `flipZ`: the stock turns about its short axis. Setup3 X = 145.82 - Setup5 X, Y unchanged | read (flip), decoded (offset) |
| Distance between the two WCS points | 145.82 mm +-0.03 (from the pocket extents of both setups: X 8.52..148.92 and -3.12..137.32). Lab file value: 145.8468 mm (`[dowel] centers`). Difference 0.03 mm, inside the decode error | decoded |
| Dowel holes in this file | No operation bores a dowel. The preview shows two dowel circles on the blank sketch. The left one has two circles (maybe 4.191 and 4.2672 mm, F-001: not read) | read, preview |
| Board on the blank | Board long side along the dowel line. Board outline in the Setup5 frame: X -2.88..137.12, Y 31.81..97.81. With dowel 1 at (3.2766, 3.81) of the blank: X 0.40..140.40, Y 35.62..101.62. The board edge is at the far long edge of the 101.6 mm blank (0.02 mm over) | decoded |
| Board turn | Setup5 X = 177.12 - y_kicad, Y = 157.81 - x_kicad (KiCad mm, y down). That is the top view turned 90 degrees clockwise. The fab export (`placement.board_to_lab`) turns it 90 degrees counter-clockwise and centers it on the blank: the two frames differ by 180 degrees and an offset | decoded |

## Setups and operations

| Setup | Operation | Tool (T = pocket) | Cut | Status |
| --- | --- | --- | --- | --- |
| Setup3 (bottom, B.Cu) | 2D Offset Roughing1 (pocket) | T3 "6mm Flute Corn", 0.6 mm flat, 2 flutes | 12000 rpm, 300 mm/min, plunge 50, stepover 0.18, stepdown max 0.08, depth "from contour" | read |
| Setup3 | 2D Offset Roughing1 (2) (rest pocket, rest tool 0.6 mm) | T6 0.2 mm flat end mill, 2 flutes, flood coolant | 5000 rpm, 1000 mm/min (0.1 mm/tooth), plunge 333, stepover 0.06 | read |
| Setup5 (top, F.Cu) | 2D Offset Roughing2 (pocket, no rest pass) | T3 0.6 mm corn | as Roughing1 | read |
| Setup5 | Drill1 | T4 drill 0.8 mm, 16 holes | 10000 rpm, plunge 100, chip-breaking, 0.4 mm through | read |
| Setup5 | Drill2 | T4 drill 1.0 mm, 52 holes | as Drill1 | read |
| Setup5 | Drill3 | T1 drill 1.1 mm, flood coolant, 6 holes | 12000 rpm, plunge 198, 0.5 mm through | read |
| Setup5 | Drill4 | T5 drill 1.4 mm, flood coolant, 8 holes | 12000 rpm, plunge 252, 0.5 mm through | read |
| Setup5 | Bore1 | T4 3.175 mm end mill "12mm Flute End Mill Metal" | 12000 rpm, 500 mm/min, 0.05 mm below the hole bottom | read |

- Not used by an operation: T2 "0.1mm Tip Engraving Metal" (30 deg, tip 0.2) and T2 "0.2mm Tip Engraving Metal" (15 deg, tip 0.2). No V-bit isolation pass. No board outline cut.
- T4 is the number of three tools (0.8 drill, 1.0 drill, 3.175 end mill), all with `manual-tool-change = 0`.
- NC programs: one, "rc_car_power_board side A". It holds only Setup3 Roughing1 and is marked invalid. The NC code member is empty. The `.cnc` files that ran are not in the file.
- Generation warnings: "Clamping helicalRampDiameter to minimumRampDiameter" (2 on each Setup3 pocket). No errors.

## Z frame and depths (decoded)

| Setup | Stock top in the WCS | Isolation Z | Depth below the stock top |
| --- | --- | --- | --- |
| Setup5 | -0.065 mm (drill cycle `stock` value; retract 5.015 = top + 5.08) | -0.14 | 0.075 mm |
| Setup3 | +0.075 mm (retract 5.155 = top + 5.08) | 0.00 | 0.075 mm |

- Z0 is the sketch point, not the stock top. A Z0 probed on the stock top moves every cut: Setup5 then cuts 0.14 mm deep, Setup3 cuts 0.00 mm (no isolation).
- Stock thickness in Setup5: 1.58 mm (top -0.065, bottom -1.645 from the Drill1 and Drill2 depths).
- Lab file: cut depth 0.08 mm on 0.070 mm copper (`[cut_depth_min]`, `[copper_thickness]`).

## Holes against the board

The holes map to the board with the turn above. 80 of 82 holes agree within 0.003 mm.

| Board drill | Board count | CAM |
| --- | --- | --- |
| 0.8 mm | 16 | Drill1 0.8 mm, 16 |
| 1.0 mm | 52 | Drill2 1.0 mm, 52 |
| 1.3 mm (J6, J7) | 4 | Drill3 1.1 mm (0.2 mm under) |
| 1.4 mm | 8 | Drill4 1.4 mm, 8 |
| 3.4 mm (H1 to H4, F1 NPTH; J1 PTH) | 7 | Bore1 with the 3.175 mm end mill |
| none | 0 | Drill3: 2 more holes at Setup5 (46.92, 58.21) and (49.22, 94.41) = KiCad (99.60, 130.20) and (63.40, 127.90). No rev3 hole is within 4.3 mm |

## How to read the file again

The `.f3d` is a zip with zstd members (method 93). Python 3.14 `zipfile` reads them: `uv run --no-project --python 3.14 python -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" <file.f3d> <empty dir>`. Extract to a scratch directory, not into the repo. The readable members are the same as in the lab template (`example/README.md` in the lab directory).
