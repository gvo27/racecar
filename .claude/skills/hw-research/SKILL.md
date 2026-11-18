---
name: hw-research
description: Use when you research a hardware part, sensor, module, connector or regulator, its datasheet, pinout, ratings or errata. Use when you research a firmware or ROS 2 API at the pinned stack version (arduino-esp32 2.0.17, ESP-IDF 4.4.7, ROS 2 Jazzy). It adds hardware and firmware steps to the user skill upstream-research.
disable-model-invocation: true
---

# Hardware and firmware research

This skill adds hardware and firmware steps to the user skill `upstream-research`. Read `~/.claude/skills/upstream-research/SKILL.md` first. Its rules apply here without change. Examples: public names only in queries, primary sources, a link with a version and a date for each fact, and "not found" instead of a guess.

## Sources, in this order
1. **The manufacturer datasheet** of the exact part number, and its revision. A distributor page is a lead, not the source. For a module (for example a Pololu regulator), the module vendor page and its schematic are primary for the module, and the IC datasheet is primary for the IC.
2. **Errata and application notes** of the manufacturer for the same part and revision.
3. **The pinned firmware and ROS versions.** Read the docs or the tagged source of: arduino-esp32 2.0.17 (core 2.x, not 3.x), ESP-IDF 4.4.7, PlatformIO espressif32 6.9.0, ROS 2 Jazzy, micro-ROS jazzy. The pins are in `docs/dependencies.md` and `firmware/esp32/platformio.ini`. If a page is for a different major version, say so.
4. **Distributor parametric search** (LCSC, DigiKey, Mouser) to find candidates, stock and price. Then go back to step 1 for each candidate.

## Datasheets through kicad-happy
The plugin `kicad-happy@kicad-happy` is off by default. Enable it for the session first (`.claude/rules/plugins.md`).

1. Download the PDFs with the kicad-happy distributor skills. `lcsc` needs no API key. `digikey`, `mouser` and `element14` need keys in user scope. Never put a key in the repo.
   - From a schematic: `sync_datasheets_lcsc.py <file.kicad_sch>`.
   - From a list of part numbers: `sync_datasheets_lcsc.py --mpn-list <file> --output <dir>`.
   - Run the scripts in the KiCad image (`rccar-kicad:local`, stdlib python3), not with the host python3. Put the downloads under `build/` (not committed). Archive only the PDF that the project uses, in `docs/datasheets/`.
2. Extract the structured specs with the kicad-happy `datasheets` skill (per-MPN cache, quality score). Use its own plan and merge steps.
3. Read the extraction as a lead. Check each value that the project uses against the PDF page, and write the page number.

## Output into the repo
- One summary for each part: `docs/datasheets/<role>_<model>.md` (for example `rangefinder_lidar_lite_v4.md`). It has the source link, the revision and the date, the specs the project uses with the page, the pinout as the project wires it, and a map from datasheet values to `tuning.toml` keys if the part has keys.
- A new sensor also gets `.claude/rules/<sensor>.md` (`.claude/rules/claude-tooling.md`).
- A value goes into `tuning.toml` or a schematic field only when it is confirmed. Unknown stays `TBD`.
- Part choice for a board: hand over to the skill `pcb-parts` with the summary.

## Red flags (hardware)
- A clone or a "compatible" module with a different revision than the datasheet.
- A rating from a product listing, not from the datasheet (current, voltage, temperature).
- A logic level above 3.3 V on an ESP32 pin. A sensor that needs power from the ESP32.
- A pinout that only a forum post or a photo gives.
- An API example for arduino-esp32 3.x or ESP-IDF 5.x.

## Report
Use the report format of `upstream-research`. Add for each part: the part number with the revision, the datasheet link with the page for each fact, and "not verified on the bench" for each value that the bench has not confirmed.
