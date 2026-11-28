# Generic start values for gaps in the lab file

These are generic values for a desktop CNC mill in a college robotics lab. They are not the values of this lab. The values of this lab are in `milling.toml` and `design_rules.toml` in the lab directory. Use a value from this table only for a fact that no source gives. Always mark it `status = "assumed"`.

| Fact | Generic start value | Note |
| --- | --- | --- |
| Isolation bit | 30 degree V-bit, 0.2 mm tip, or 60 degree, 0.1 mm tip | Fusion "Taper angle" is the angle per side (from the tool axis): included angle = 2 x taper. The tool drawing in the Fusion tool library shows it. For a different CAM tool, check both readings |
| Cut depth | copper thickness + 0.03 to 0.05 mm | 1 oz copper is 0.035 mm, 2 oz is 0.070 mm |
| Depth error | 0.05 mm without surface probing, 0.02 mm with probing | 0 only on the owner's statement |
| Drill set | 0.8, 1.0, 1.2, 1.5 mm | Ask for the real set before footprints get their drills |
| End mill | 3.175 mm (1/8 in) flat, sometimes 0.8 and 2.0 mm | Smallest bored hole = tool + 0.125 mm |
| Via method | wire or rivet, soldered on the two sides | Holes are not plated |
| Annular ring | 0.45 mm minimum | |
| Track and gap | 0.5 mm track, 0.4 mm gap | Coarser than a fab house |
| Edge clearance | 0.5 mm | |
| Stock | FR-4, 1 oz, 1.6 mm, single or double sided | Read the label on the blank |
