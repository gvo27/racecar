# Lab example: Fusion 360 setup and demo panel

This directory holds the lab's calibrated Fusion 360 CAM setup: `Pcb DXF's amd copper plate.f3z`. It contains a demo panel of 6 small boards that the lab already milled. The power board and its outputs (`docs/schematics/fab/`) must fit this setup. No binary was added by Task 9. The file was committed by the owner.

## Facts read from the file

Source: the CAM XML (`Toolpath/Iron.Document/theIronDoc.irondoc`), the toolpath float data and `Iron.Machine/1.mch`. Status: verified by reading the file, except where a line says "not in the file".

| Item | Value |
| --- | --- |
| Machine | Makera Carvera, 3 axes, post `Carvera.cps`, tool changer, air coolant |
| Stock | 152.4 x 101.6 mm (4 in x 6 in). X runs along the long side. The Fusion model is 1.4859 mm thick. The real blank is Kepro P22-465G, 2 oz, 1.57 mm (owner, 2026-11-12) |
| Dowel holes | 2 holes, diameter 4.191 mm (0.165 in) for 4.0 mm pins. Centers at (3.2766, 3.81) and (149.1234, 3.81) mm from the stock lower-left corner. They are 145.8468 mm apart on one line along a long side, 3.2766 mm from each short end |
| How the dowels were found | The Bore1 toolpath floats are +-72.9234 mm in X and -46.99 mm in Y from the stock center. The helix radius is 0.508 mm for the 3.175 mm tool: (4.191 - 3.175) / 2 |
| Setup A | Bore1 cuts the dowel holes with a 1/8 in (3.175 mm) flat end mill, through the stock (-0.02 mm), 10000 rpm. This is the only end mill in the file |
| Setup B (top) | WCS origin = dowel 1 center. Operations: 2D contour isolation, drills, Face2 |
| Setup C (bottom) | WCS origin = dowel 2 center. The stock is flipped about its short (Y) axis, so the two dowels swap places. Isolation contours and Face3 |
| Isolation | One contour pass, depth 0.08 mm below the contour, compensation left. Tool: chamfer mill "0.1mm Tip Engraving" with tip 0.2 mm and taper 30 (Fusion value), 12000 rpm, feed 500, plunge 200 |
| Drills | 0.9, 1.0 and 1.1 mm. Chip breaking, 10000 rpm, through (-0.02 mm) |
| Face2 | 0.3 mm tip, 15 degree "solder mask removal" tool, stepover 0.2 mm |
| Drill map | The preview shows a "Drill Map" legend. The lab makes the holes from the KiCad drill-map DXF |

Owner statements (PR #3, 2026-11-12): the blank is even (depth error 0); the drill bits are 0.1 to 2.0 mm in 0.1 mm steps; dowel holes are always made; B.Cu is not mirrored.

Not in the file, so not known: whether Fusion "taper 30" is the angle per side or the included angle (`milling.toml` checks both); the post-processed `.cnc` code; the tool library export.

## What follows for the board

- A hole between 2.0 mm and 3.3 mm cannot be made. The largest drill is 2.0 mm and the only end mill is 3.175 mm. `milled_hole_min` is 3.3 mm (assumed: tool + 0.125 mm).
- The cut depth is 0.08 mm on 0.070 mm copper: the margin is 0.01 mm on an even blank. MILL-DEPTH passes with error 0. A real depth error larger than 0.01 mm leaves copper in the isolation cut.
- The board is turned 90 degrees and centered on the stock, clear of the dowels. See `docs/schematics/fab/README.md`.

## How to read the file again

The `.f3z` is a zip that holds a `.f3d`. The `.f3d` is a zip too, but its members use zstd (zip method 93). Python `zipfile` cannot read method 93. Read the raw member bytes with the zip offsets and decompress them with the host `zstd -d`. This is a one-time analysis step, not a repo tool.

```python
import io, os, struct, subprocess, sys, zipfile
src, out = sys.argv[1], sys.argv[2]            # the .f3z file, an empty output directory
outer = zipfile.ZipFile(src)
f3d = outer.read([n for n in outer.namelist() if n.endswith(".f3d")][0])
z = zipfile.ZipFile(io.BytesIO(f3d))
for i in z.infolist():
    if i.is_dir():
        continue
    dst = os.path.join(out, i.filename)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if i.compress_type == 93:                  # zstd
        n, m = struct.unpack("<HH", f3d[i.header_offset + 26:i.header_offset + 30])
        start = i.header_offset + 30 + n + m
        data = subprocess.run(["zstd", "-d", "-c"], input=f3d[start:start + i.compress_size],
                              capture_output=True, check=True).stdout
    else:
        data = z.read(i)
    open(dst, "wb").write(data)
```

The file gives 61 members. These are readable: `Toolpath/Iron.Document/theIronDoc.irondoc` (CAM XML: setups, operations, tools, stock), `Iron.Machine/1.mch` (JSON), the message logs and the PNG previews. The toolpath data holds float32 XYZ values. The BREP (`.smb`) and bulk-stream members are proprietary and stay unread. Put the extracted files in a scratch directory, not in the repository.
