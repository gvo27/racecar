# Reverse-polarity protection: proposal and status

This file is the one source for the status of this proposal. Other docs point here and do not repeat the status.

Status: **rejected for rev A.** Decision (owner, 2026-11-11): ship rev A with the keyed connector only. This file keeps the proposal for a later revision. Source: the body of PR #3 (2026-11-11), copied here before the merge into `main`.

Changes since the proposal:
- U2 is now the Pololu D36V50F5, the same part as U1 (owner 2026-11-12). Both modules have their own reverse-voltage protection (`docs/datasheets/regulator_pololu_d36v50f5.md`).
- The board draws 8.4 A to 9.0 A from the pack, about 9.3 A at Mapper start-up (`README.md`, budget).

## Risk

The T-plug is keyed, but the pigtail is soldered to J1 by hand, so a reversed lead is possible.

- **Protected:** U1 and U2 (D36V50F5, to -40 V). U3 is behind U2.
- **Not protected:**
  - C1 and C9. They are polarized.
  - D1. It conducts forward when the pack is reversed, and F1 must open before D1 fails.

## Circuit

One high-side P-channel MOSFET (Q1) between F1 and `VBAT`, and one gate resistor (R4).

```
J1+ ── F1 ──D┤Q1├S── VBAT (D1, C1, U1, U2)
              G
              └─ R4 10k ── GND
```

- **Correct polarity:** the body diode conducts first. Then Vgs is about -VBAT, and the channel turns fully on.
- **Reversed polarity:** Q1 stays off, and the body diode blocks.
- **Loss:** at the 9 A worst case, I² x Rds(on) = 9² x 5 mΩ = about 0.4 W, a drop of about 45 mV. A Schottky diode loses about 4 W at the same current.
- **Gate Zener:** optional on 2S. Vgs is at most -8.4 V, or about -17 V while D1 clamps. This is in the -20 V limit. Reversed, Vgs is at most +8.4 V. If the pack grows, add a footprint for a 12 V to 15 V gate-source Zener.

## Selection criteria for Q1

- Vds -20 V or more negative.
- Vgs(max) -20 V or more negative, and +12 V or more on the positive side.
- Rds(on) 10 mΩ or less at Vgs -4.5 V.
- Id 20 A or more.
- Power package with a thermal pad. On the milled board it goes on the bottom side with the other SMD parts.

Candidate: Vishay SiRA99DP: -30 V, PowerPAK SO-8, Vgs +16/-20 V. These values come from a datasheet mirror. Check them against the current Vishay datasheet before you use the part.
