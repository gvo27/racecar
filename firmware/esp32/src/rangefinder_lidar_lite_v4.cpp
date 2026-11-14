// Garmin LIDAR-Lite v4 LED driver (I2C, default addr 0x62, 400 kHz). The only file that
// knows this device's registers. Output: distance in cm (raw), STATUS register.
#include <Arduino.h>
#include <Wire.h>
#include "rangefinder.h"

namespace {

constexpr uint8_t REG_ACQ_COMMANDS = 0x00;  // write 0x04: take a measurement
constexpr uint8_t REG_STATUS       = 0x01;  // bit0 = busy
constexpr uint8_t REG_FULL_DELAY_L = 0x10;  // low byte, then high byte (auto-increment): cm
constexpr uint8_t CMD_MEASURE      = 0x04;
constexpr uint8_t STATUS_BUSY      = 0x01;
constexpr uint32_t POLL_TIMEOUT_MS = 50;

bool readRegs(uint8_t addr, uint8_t reg, uint8_t *buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(true) != 0) return false;
  if (Wire.requestFrom((uint16_t)addr, (size_t)n, true) != n) return false;
  for (size_t i = 0; i < n; ++i) {
    int b = Wire.read();
    if (b < 0) return false;
    buf[i] = (uint8_t)b;
  }
  return true;
}

bool writeReg(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission(true) == 0;
}

bool llv4Probe(const RfCfg &cfg) {
  uint8_t st;
  return readRegs(cfg.addr, REG_STATUS, &st, 1);
}

bool llv4Read(const RfCfg &cfg, uint32_t &raw, uint8_t &status) {
  if (!writeReg(cfg.addr, REG_ACQ_COMMANDS, CMD_MEASURE)) return false;
  const uint32_t t0 = millis();
  uint8_t st = STATUS_BUSY;
  for (;;) {
    vTaskDelay(1);
    if (!readRegs(cfg.addr, REG_STATUS, &st, 1)) return false;
    if (!(st & STATUS_BUSY)) break;
    if (millis() - t0 > POLL_TIMEOUT_MS) return false;
  }
  uint8_t d[2];
  if (!readRegs(cfg.addr, REG_FULL_DELAY_L, d, 2)) return false;
  raw = (uint32_t)d[0] | ((uint32_t)d[1] << 8);
  status = st;
  return true;
}

const RangefinderDriver DRIVER_LLV4 = {"garmin_lidar_lite_v4_led", llv4Probe, llv4Read};

}  // namespace

const RangefinderDriver *rangefinderDriver(uint8_t id) {
  switch (id) {
    case 1: return &DRIVER_LLV4;
    default: return nullptr;  // 0 = off, unknown = off
  }
}
