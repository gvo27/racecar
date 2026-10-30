#pragma once
// Device-agnostic rangefinder interface. Drivers only do I2C transactions on an already
// initialised Wire bus (Wire.begin lives in rangefinderTask in main.cpp) and never touch
// Serial or PWM. Device-specific code: src/rangefinder_*.cpp only.
#include <stdint.h>

struct RfCfg {
  uint8_t addr;  // 7-bit I2C address
};

struct RangefinderDriver {
  const char *name;
  // True if the device answers and is ready to measure.
  bool (*probe)(const RfCfg &);
  // One blocking (bounded, ~50 ms max) measurement. raw = device units (scaled by Config
  // rfScaleM), status = device status byte for diagnostics. False on any bus error/timeout.
  bool (*read)(const RfCfg &, uint32_t &raw, uint8_t &status);
};

// 0 = off -> nullptr, 1 = Garmin LIDAR-Lite v4 LED, unknown -> nullptr.
const RangefinderDriver *rangefinderDriver(uint8_t id);
