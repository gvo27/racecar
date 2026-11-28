---
name: hw-research
description: Use when you research the facts of an electronic part for this car (datasheet, pinout, ratings, errata) or an ESP32 firmware, micro-ROS or ROS 2 API at the pinned stack version. For part choice on a board use pcb-parts. For general software tools, libraries or agent tooling use upstream-research.
---

# Hardware and firmware research

This skill adds hardware and firmware steps to the user skill `upstream-research`. Scope split: this skill owns electronic parts, datasheets and the pinned firmware and ROS stack of this repo. `upstream-research` owns general software tools, libraries, repos and agent tooling. Do not run both for one question. Read `~/.claude/skills/upstream-research/SKILL.md` first. Its rules apply here without change. Examples: public names only in queries, primary sources, a link with a version and a date for each fact, and "not found" instead of a guess.

## Sources, in this order
1. **The manufacturer datasheet** of the exact part number, and its revision. A distributor page is a lead, not the source. For a module (for example a Pololu regulator), the module vendor page and its schematic are primary for the module, and the IC datasheet is primary for the IC.
2. **Errata and application notes** of the manufacturer for the same part and revision.
3. **The pinned firmware and ROS versions.** Read the docs or the tagged source of the versions in `docs/dependencies.md` (section "Stack pins"). If a page is for a different major version, say so.
4. **Distributor parametric search** (LCSC, DigiKey, Mouser) to find candidates, stock and price. Then go back to step 1 for each candidate.

## Datasheets through kicad-happy
The plugin `kicad-happy@kicad-happy` is off by default. Enable it for the session first (`.claude/rules/plugins.md`).

1. Download the PDFs with the kicad-happy distributor skills. `lcsc` needs no API key. `digikey`, `mouser` and `element14` need keys in user scope. Never put a key in the repo.
   - From a schematic: `sync_datasheets_lcsc.py <file.kicad_sch>`.
   - From a list of part numbers: `sync_datasheets_lcsc.py --mpn-list <file> --output <dir>`.
   - Run the scripts in the KiCad image (`rccar-kicad:local`), not with the host python3. They use the Python standard library and call the network. Example:
     ```
     KH=$(ls -d ~/.claude/plugins/cache/kicad-happy/kicad-happy/* | sort | tail -1)
     docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v "$PWD":"$PWD" -v "$KH":"$KH":ro -w "$PWD" rccar-kicad:local \
       python3 "$KH/skills/lcsc/scripts/sync_datasheets_lcsc.py" --mpn-list build/mpns.txt --output build/datasheets
     ```
   - Put the downloads under `build/` (not committed). Archive only the PDF that the project uses, in `docs/datasheets/`.
2. Extract the structured specs with the kicad-happy `datasheets` skill (per-MPN cache, quality score). Follow the extraction procedure in that skill (`plan_extraction.py`, then `merge_results.py`).
3. Read the extraction as a lead. Check each value that the project uses against the PDF page, and write the page number.

## Output into the repo
- One note for each part model: `docs/datasheets/<kind>_<model>.md` (for example `rangefinder_lidar_lite_v4.md`). The form of the note is owned by skill `pcb-parts`, section "Store a datasheet note". A part with `tuning.toml` keys also gets a map from datasheet values to the keys.
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

## Verify
- Each fact has a primary source: the link, the revision or version, and the page or section.
- Read each value that the project uses again on the source page before you write it to the repo.
- A fact without a source is "not found", not a guess.
