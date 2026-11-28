# Hardware: inventory, wiring and power

The parts on the car, the rangefinder wiring, the power rules and the power-up sequence. Pin map: [README.md](../README.md#microcontroller-pinout) (owner: `firmware/esp32/include/pins.h`). Power board: [pcb/](../pcb/README.md). Invariants: [invariants.md](invariants.md).

## Inventory

| Component | Item | Documentation |
| --- | --- | --- |
| chassis | Tamiya TT-02 | — |
| battery | 2S 7.4V 80C 5200mAh LiPo Battery Pack | — |
| microcontroller | ESP32 S3 N16R8 | [user guide](https://github.com/microrobotics/ESP32-S3-N16R8/blob/main/ESP32-S3-N16R8_User_Guide.pdf) |
| edge compute | Raspberry Pi 5 | 5V 5A |
| voltage regulator for compute rail | Pololu D36V50F5 (5V 5.5A, 6-50V in) | [pololu.com/product/4091](https://www.pololu.com/product/4091), [archived](datasheets/Pololu%20-%205V%2C%205.5A%20Step-Down%20Voltage%20Regulator%20D36V50F5.htm) |
| rangefinder | Garmin LIDAR-Lite v4 LED, part number 010-02022-00 | [archived PDF](datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](datasheets/rangefinder_lidar_lite_v4.md), [instructions](https://static.garmin.com/pumac/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf) (software name: rangefinder) |
| lidar | Slamtec Mapper M2M1 | [datasheet digest](datasheets/slamtec_mapper_M2M1_datasheet.md) |
| motor controller | THW-1060-BRUSHED | [thw-1060-brushed-esc.md](datasheets/thw-1060-brushed-esc.md) |
| steering servo | DS3225MG | [ds3225_servo.md](datasheets/ds3225_servo.md) |

## Wiring: Rangefinder (Garmin LIDAR-Lite v4 LED)

The software name is *rangefinder*. Datasheet: [archived PDF](datasheets/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf), [summary](datasheets/rangefinder_lidar_lite_v4.md). Power off while wiring.

| Garmin pin | Name | Wire | Connect to |
| --- | --- | --- | --- |
| 1 | VIN (5 V, 4.75-5.25 V) | red | regulated 5 V **sensor rail** (never ESP32 5V/3V3) |
| 2 | GND | black | common ground (P1-22) |
| 3 | I2C SDA | **white** | GPIO8 (P1-12) |
| 4 | I2C SCL | **green** | GPIO9 (P1-15) |
| 5-10 | GPIOA, GPIOB, nRF debug | n/a | leave unconnected |

## Power rules

1. Invariants 1 and 2 apply: the ESP32 powers nothing, and the sensors use their own rail ([invariants.md](invariants.md)).
2. Servo power comes from the built-in 6 V / 3 A BEC of the ESC (red wire of the throttle lead). Connect it with a Y-harness.
3. Connect the grounds of the ESP32, ESC and servo (P1-22).

## Power-up sequence

1. ESC **off**. Wheels off the ground.
2. Connect the USB cable to **COM**. The ESP32 boots and sends neutral (1500 µs) on both channels. Then run `make car-up`.
3. ESC **on**. It beeps and learns neutral.
4. To power down, do the steps in reverse order. Switch the ESC off first. **Always switch the ESC off before `make flash`.**
