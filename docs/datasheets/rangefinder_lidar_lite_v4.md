# Garmin LIDAR-Lite v4 LED (rangefinder), part 010-02022-00

Sources: Garmin "LIDAR-Lite v4 LED Operation Manual and Technical Specifications" (Sept 2020), archived as [LIDAR-Lite LED v4 Instructions_EN-US.pdf](LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf) (original: https://static.garmin.com/pumac/LIDAR-Lite%20LED%20v4%20Instructions_EN-US.pdf). Garmin sample code, ANT and DFU material: https://github.com/garmin/ . In software this device is called the **rangefinder**; this file is the only place (with the PDF and README) that names the model. Project rules: [.claude/rules/rangefinder.md](../../.claude/rules/rangefinder.md).

## identity
- manufacturer: Garmin
- model: LIDAR-Lite v4 LED, 010-02022-00
- principle: time of flight of 940 nm near-infrared LED light (not a laser)
- soc: nRF52840 (ANT, Bluetooth 5 LE, secure DFU bootloader preloaded)
- certification: FCC-certified transmitter

## specs
| parameter | value |
| --- | --- |
| size (L x W x H) | 52.2 x 24 x 21.2 mm (no connector) |
| weight | 14.6 g |
| operating / storage temp | -20 to 60 C / -40 to 85 C |
| supply (VIN) | 4.75 to 5.25 V dc |
| current | 2 mA idle, 85 mA during an acquisition |
| signal level (all other pins) | 3.3 V max; above 3.3 V damages the device |
| range | 5 cm to 10 m |
| resolution | 1 cm |
| beam divergence | 4.77 deg |
| LED wavelength | 940 nm |
| optical aperture | 14.9 mm |
| update rate | I2C: > 200 Hz typical; ANT: up to 200 Hz (90 % target, 2 m, indoors) |
| repeatability (1 sigma, 90 % target, high accuracy mode) | +/-1 cm to 2 m; +/-2 cm to 4 m; +/-5 cm to 10 m |
| interfaces | I2C (400 kHz), ANT, SPI with user app |

## pinout
10 through-holes, 2 rows of 5, 2 mm pitch. Pin numbers as in the PDF connection table (order: VIN, GND, SDA, SCL, GPIOA, GPIOB, VRETURN, nRESET, SWCLK, SWDIO).

| pin | name | function | V max | our usage |
| --- | --- | --- | --- | --- |
| 1 | VIN | 5 V power | 5 V | red; regulated 5 V sensor rail (never ESP32 5V/3V3) |
| 2 | GND | ground | n/a | black; common ground |
| 3 | I2C SDA | I2C data | 3.3 V | white or green (TBD); ESP32 GPIO8 (P1-12) |
| 4 | I2C SCL | I2C clock | 3.3 V | white or green (TBD); ESP32 GPIO9 (P1-15) |
| 5 | GPIOA | TRIGGER input (mode control) | 3.3 V | unconnected |
| 6 | GPIOB | MONITOR busy output; boot pin | 3.3 V | unconnected (low at power-up = BLE bootloader) |
| 7 | VRETURN | nRF52840 debug | 3.3 V | unconnected |
| 8 | nRESET | nRF52840 debug | 3.3 V | unconnected |
| 9 | SWCLK | nRF52840 debug | 3.3 V | unconnected |
| 10 | SWDIO | nRF52840 debug | 3.3 V | unconnected |

## i2c
- address: 7-bit 0x62 default (8-bit 0xC4 write / 0xC5 read); no general call; no 10-bit addressing
- speed: 400 kHz Fast Mode supported
- pull-ups: internal 13 kOhm to 3.3 V, so no external pull-ups and no level shifter
- register pointer auto-increments on successive reads/writes in one transfer (read 0x10 + 0x11 as one 2-byte read)
- read = write register address, stop, new start with read bit (the last byte is NACKed by the master)
- power-up: self-test, registers reset to defaults; measurements valid after about 22 ms
- address can be changed (needs 0xEA flash enable + UNIT_ID unlock sequence); not used here

## registers
Used by the driver:
| addr | name | access | use |
| --- | --- | --- | --- |
| 0x00 | ACQ_COMMANDS | W | write 0x04 to start a measurement |
| 0x01 | STATUS | R | bit 0 (LSB) = busy; poll until low |
| 0x10 | FULL_DELAY_LOW | R | distance low byte, cm |
| 0x11 | FULL_DELAY_HIGH | R | distance high byte, cm |

Notable, not used (defaults kept; changing them needs a confirmed reason and a tuning key):
| addr | name | note |
| --- | --- | --- |
| 0x05 | ACQUISITION_COUNT | max acquisitions, default 0xFF |
| 0x1C | DETECTION_SENSITIVITY | peak-detection threshold bypass, default 0x00 |
| 0xE2 | POWER_MODE | power state, default 0xFF |
| 0xE3 | MEASUREMENT_INTERVAL | automatic measurement rate, default 0xFF |
| 0xE4 | FACTORY_RESET | reset defaults |
| 0xE5 | QUICK_TERMINATION | default 0x08 |
| 0xE6 | START_BOOTLOADER | starts BLE bootloader: never write |
| 0xEA | ENABLE_FLASH_STORAGE | persist settings: never write |
| 0xEB | HIGH_ACCURACY_MODE | default 0x14 |
| 0xE0 / 0xEC | BOARD / SOC_TEMPERATURE | diagnostics |
| 0x16-0x1A, 0x1B | UNIT_ID, I2C_SEC_ADDR, I2C_CONFIG | address change; not used |

## measurement sequence (I2C)
1. Write 0x04 to register 0x00.
2. Read register 0x01; repeat until bit 0 is low (busy clear). Use a timeout.
3. Read 2 bytes starting at 0x10 (low byte, then high byte): 16-bit distance in cm.

Optionally the read of 0x10/0x11 can overlap the next measurement (returns the previously triggered result); not used.

## no return
If the correlation peak is not above the valid-signal threshold, the device reports **1 cm**. The driver treats raw value 1 (and out of range values) as "no return" and publishes +inf.

## mode control pins and BLE bootloader
- GPIOA (pin 5): toggle to trigger a measurement (rising or falling edge; ignored while busy).
- GPIOB (pin 6): MONITOR, high = busy, low = idle.
- Not used here (I2C polling is enough). **Warning:** GPIOB grounded while power is applied starts the Bluetooth LE bootloader ("LLV4 DFU Mode"). Keep pins 5-10 unconnected so the sensor can never boot into DFU.

## mapping to tuning.toml [rangefinder]
| datasheet value | tuning key | value | notes |
| --- | --- | --- | --- |
| driver family | driver | 1 | 0 = off, 1 = Garmin LIDAR-Lite v4 LED (I2C); selects the driver table entry |
| I2C address 0x62 | i2c_addr | 98 | decimal 98 = 0x62 |
| measure period | period_ms | 20 | 50 Hz by our choice; the sensor does > 200 Hz over I2C |
| register unit 1 cm | reading_scale_m | 0.01 | metres per raw count |
| no return reports 1 cm | no_return_raw | 1 | raw value meaning "no target" |
| range 5 cm | min_range_m | 0.05 | Range.min_range |
| range 10 m | max_range_m | 10.0 | Range.max_range |
| beam divergence 4.77 deg | fov_rad | 0.0833 | Range.field_of_view |
| 940 nm LED | radiation_type | 1 | Range.INFRARED (0 = ultrasound) |

Authoritative values live in `tuning.toml`; this table maps datasheet to key (pushed to the MCU as `SET rf_*`). Keep it in sync when a value changes.

## project notes
- role: forward obstacle distance for the ESP32 firmware (later e-brake) and the Pi (sensor fusion). Topic `/rccar/rangefinder/range`, frame `rangefinder_link`.
- e-brake thresholds are deferred until bench data (needs confirmed values).
- power: 85 mA acquiring is small, but still from the sensor rail, not the ESP32.
