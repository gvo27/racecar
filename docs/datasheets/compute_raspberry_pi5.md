# Raspberry Pi 5 (compute), mechanical summary

Source: Raspberry Pi Ltd, "Raspberry Pi 5 Product Brief" (RP-008348-DS, published November 2026), archived as [RP-008348-DS-10-raspberry-pi-5-product-brief.pdf](RP-008348-DS-10-raspberry-pi-5-product-brief.pdf), page 3 "Physical specification" (added by the owner, 2026-11-27). The drawing note says: "All dimensions are approximate and for reference purposes only". The official mechanical drawing and a STEP model are on the Raspberry Pi product information portal (https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf). In software, this board is called the **Pi**. Power facts: [docs/hardware.md](../hardware.md).

## board
| parameter | value |
| --- | --- |
| board (L x W) | 85 x 56 mm, 4 rounded corners |
| mounting holes | 4 x ø2.7 mm (for M2.5) |
| hole pattern | 58 x 49 mm (center to center) |
| hole position | 3.5 mm from the left edge and from the bottom edge (the edge with the USB-C and micro-HDMI ports) |
| keep-out around each hole | ø6 mm pad (the standoff must be ø6 mm or smaller) |
| port overhang | USB and Ethernet stand 3 mm out of the 85 mm edge |
| side ports (USB-C power, 2 x micro-HDMI) | centers 11.2, 25.8 and 39.2 mm from the left edge |
| GPIO header | 2 x 20 pins along the top edge (between the two top holes) |

## heights (not in the product brief)
| item | value | status |
| --- | --- | --- |
| USB and Ethernet stack above the board top | about 17 mm | estimate: read it from the official STEP model or measure |
| Active Cooler, overall | 13.7 mm with the push pins, 63.5 x 42.5 mm | official cooler drawing (https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-mechanical-drawing.pdf), not in this archive |
| parts under the board | about 3 mm | estimate |

## mounting notes
- Use M2.5 screws and standoffs, ø6 mm or smaller at the holes.
- Keep air above the Active Cooler fan. Keep the USB, Ethernet and USB-C ports reachable for the cables.
