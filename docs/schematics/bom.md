# Power board BOM (Rev A draft)

The BOM comes from the schematic. Each symbol carries part fields. `make bom` exports them with `kicad-cli` to `bom.csv` (commit the file) and prints the cost total. Companion files: `design_overview.md` (design), `fab_handoff.md` (layout and CNC-milling steps). Rev A is milled in-house (Makera Carvera), so there is no PCB fab-house cost. Every MPN is **proposed**, pending owner approval, unless `Status` says otherwise. Prices and stock were checked 2026-10-30; confirm before ordering. J10 is intentionally absent (radar removed).

## How the BOM is made

- `make bom` writes `bom.csv`: one row per group of symbols with equal Value, Footprint and MPN. Columns: Reference, Qty, Value, Footprint, MPN, Manufacturer, Status, Unit cost USD, Supplier link, BOM Comments. It then runs `tools/bom_total.py`, which prints the total and the total without parts that are in hand.
- Symbol fields: `MPN`, `Manufacturer`, `Status` (`proposed`, `assumed`, `in hand` or `TBD`), `Unit cost USD` (number only; "Price est." in BOM Comments marks an estimate), `Supplier link`, `BOM Comments` (key specs, flags, decisions). Unknown value => `TBD`. TP*, H* and J1 have no part (`none`).
- To edit a field in KiCad 10: Schematic Editor > Tools > Edit Symbol Fields (Symbol Fields Table). Edit the cells, save, then run `make bom` and commit `bom.csv` with the schematic. Do not change `Value`, `Footprint` or `Datasheet` for BOM reasons. F1 `MPN` lists the fuse and the holder (comma-separated); its cost is fuse plus holder.
- `make pcb-test` fails if `bom.csv` is not equal to a fresh export, if a symbol has no MPN or an invalid Status, or if the totals change. After a field change, KiCad "Update PCB from Schematic" copies the fields to the footprints; DRC parity warns until then.
- Parts with no schematic symbol (XH housings, crimps, board blank, rivets, dowels, bits, J6/J7 options, Mapper pigtail) are in `bom_offboard.csv`. Same columns plus `In total` (`yes` or `no`). It is kept by hand.
- Total for one board (2026-11-12): about 94.0 USD. Without the parts already owned (U1 and U2, two Pololu D36V50F5 at 39.95 USD each, qty 1): about 14.1. No PCB fab cost: rev A is milled in-house. The J6/J7 JST options are not in the total. Buy spare fuses and a few spare passives.

## Out of stock / backorder (as checked)

- Samsung CL21A106KAYNNNE (10 uF): out of stock; replaced by YAGEO CC0805KRX5R8BB106.
- Murata GRM21BR61A226ME44L: DigiKey backorder; substitute YAGEO CC0805MKX5R6BB226 (no link verified).
- Samsung CL21B105KBFNNNE: DigiKey backorder; in stock at Mouser.

## Fuse notes (F1)

- **Series:** Littelfuse ATO 257 standard blade (32 VDC, 1000 A interrupting at 32 VDC; ISO 8820-3 / SAE J1284), in a Littelfuse FLR 178.6165.0001 holder (22.5 A continuous / 30 A max per the FLR datasheet; 32 V fuse system). Fast-acting standard characteristic, not time-delay. Proposed 0257015.PXPV (15 A); the 10 A part (0257010.PXPV) is rejected by the load (see Rating). 0257015.L is obsolete; DigiKey lists 0287015.PXCN (ATOF) as direct substitute. Melting I2t of the 15 A part is about 340 A2s (Littelfuse catalog). No confirmed retailer links; prices (fuse est. 0.40, holder est. 3.00) are unverified.
- **No dedicated slow-blow needed.** Plug-in inrush is C1 (470 uF) plus MLCCs charging: about V2 C / (2R) = 8.4^2 x 470 uF / (2 x 0.05 ohm) = 0.3 A2s, where R = 50 mohm is an **assumed** loop resistance; even at 10 mohm: about 1.7 A2s, about 200x margin below the 15 A fuse's 340 A2s melting I2t. The modules soft-start. Slow-blow parts are for motor inrush, and the motor/ESC is powered off-board.
- **Rating:** worst-case board load (with the Slamtec Mapper on J11) is about 8.4 A at 6.4 V and about 9.0 A at the 6.0 V cutoff, about 9.3 A briefly at Mapper startup (U1: 5.1 V x 5 A / (0.9 x 6.0 V) = 4.7 A, plus U2: 5 V x 4.6 A / (0.9 x 6.0 V) = 4.3 A). On a 10 A fuse that is 84-93% of rating, well over the ~75% continuous rule of thumb; a 15 A fuse gives 56-62%. **Decided: 15 A** (previous load without the Mapper: 7.3 / 7.8 A).
- **Copper must be sized for the fuse:** VBAT_RAW, VBAT and GND copper must carry F1's rating (a blade fuse holds 110% indefinitely: about 16.5 A for 15 A, 11 A for 10 A), not just the 9.0 A load. Widths: `fab_handoff.md`.
- **Resolved:** F1 = 15 A (set by the load; copper stays sized for 16.5 A).

## J1 footprint note

KiCad's `Connector_Wire` library (checked locally) has `SolderWire-*` footprints up to 2.5 sqmm only (no 4 sqmm variant): the one in the schematic, `SolderWire-2.5sqmm_1x02_P8.8mm_D2.4mm_OD4.4mm`, has a 3.0 mm drill and a 4.4 mm pad ("D2.4mm" is the conductor diameter, not the drill). 12 AWG stranded tinned wire (about 2.05 mm) fits the 3.0 mm hole; the concern is the thin 0.7 mm annular ring at F1's current. Proposed: keep the 3.0 mm drill, enlarge the pad OD to at least 5 mm (custom copy of the footprint), thermal reliefs off. Verify against the actual wire.
