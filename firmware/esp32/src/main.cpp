// RC car actuator bridge: USB serial commands -> hardware PWM for
// DS3225 steering servo + THW-1060 brushed ESC.
//
// Architecture
//   loop()        : USB serial parser + telemetry (comms only)
//   controlTask() : 100 Hz, owns the actuators: failsafe, slew, reverse logic
//   LEDC hardware : generates the 50 Hz pulse trains with zero CPU load
// The comms layer is selected at build time; controlTask() and the PWM layer
// are shared by both:
//   RCCAR_COMMS_ASCII   : ASCII lines on Serial (legacy, tools/rccar.py)
//   RCCAR_COMMS_MICROROS: micro-ROS node over Serial (UART0), see the section before setup()

#include <Arduino.h>
#include <Preferences.h>
#include <driver/ledc.h>
#include <esp_task_wdt.h>
#include <esp_timer.h>
#include <sys/time.h>
#include <cmath>

#ifdef RCCAR_COMMS_MICROROS
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <rmw_microros/rmw_microros.h>
#include <rccar_msgs/msg/drive_cmd.h>
#include <rccar_msgs/msg/telemetry.h>
#include <rccar_msgs/msg/mcu_event.h>
#include <rccar_msgs/srv/mcu_command.h>
#endif

#include "pins.h"

#if defined(RCCAR_COMMS_MICROROS) == defined(RCCAR_COMMS_ASCII)
#error "define exactly one of RCCAR_COMMS_MICROROS / RCCAR_COMMS_ASCII (see platformio.ini)"
#endif

static const char *FW_VERSION = "0.2.0";

// ---------------------------------------------------------------------------
// Fixed limits from the datasheets (docs/datasheets/*.md). Never exceeded, even in RAW.
// ---------------------------------------------------------------------------
// DS3225: 500..2500 us, 1500 us neutral, 50..330 Hz frame, 3 us deadband
constexpr uint16_t SERVO_ABS_MIN_US = 500;
constexpr uint16_t SERVO_ABS_MAX_US = 2500;
constexpr uint16_t SERVO_MAX_HZ     = 330;
// THW-1060: standard RC throttle. Hard window; tuned endpoints live in Config.
constexpr uint16_t ESC_ABS_MIN_US   = 900;
constexpr uint16_t ESC_ABS_MAX_US   = 2100;
constexpr uint16_t ESC_MAX_HZ       = 400;   // above 50 Hz: verify ESC first
constexpr uint16_t BOOT_NEUTRAL_US  = 1500;

constexpr uint32_t PWM_RES_BITS = 14;   // at 50 Hz: 20000 us / 16384 = 1.22 us per tick

constexpr ledc_mode_t      LEDC_MODE      = LEDC_LOW_SPEED_MODE;
constexpr ledc_timer_t     STEER_TIMER    = LEDC_TIMER_0;
constexpr ledc_timer_t     THROTTLE_TIMER = LEDC_TIMER_1;
constexpr ledc_channel_t   STEER_CH       = LEDC_CHANNEL_0;
constexpr ledc_channel_t   THROTTLE_CH    = LEDC_CHANNEL_1;

// ---------------------------------------------------------------------------
// Tunable config, persisted in NVS flash
// ---------------------------------------------------------------------------
constexpr uint32_t CFG_MAGIC = 0xC0FFEE02;  // bump when Config layout changes

struct Config {
  uint32_t magic        = CFG_MAGIC;
  uint16_t steerCenterUs = 1500;
  uint16_t steerLeftUs   = 1800;   // pulse at full LEFT lock (may be < center)
  uint16_t steerRightUs  = 1200;   // pulse at full RIGHT lock
  float    maxSteerDeg   = 25.0f;  // road-wheel angle at full lock
  float    headingGain   = 1.0f;   // steering deg per heading deg
  float    speedLimit    = 0.30f;  // speed 1.0 -> this fraction of full throttle
  uint16_t deadbandUs    = 0;      // ESC dead zone skipped around neutral
  float    accelPerSec   = 2.0f;   // max change of speed command per second
  uint16_t timeoutMs     = 300;    // no command for this long -> failsafe
  uint8_t  doubleTapRev  = 1;      // ESC needs brake-neutral-reverse sequence
  uint16_t brakeMs       = 150;    // double-tap reverse: brake pulse length
  uint16_t gapMs         = 150;    // double-tap reverse: neutral gap length
  float    brakeLevel    = 0.5f;   // double-tap reverse: brake strength
  uint16_t escMinUs      = 1000;   // full reverse
  uint16_t escNeutralUs  = 1500;
  uint16_t escMaxUs      = 2000;   // full forward
  uint16_t servoHz       = 50;     // DS3225 accepts 50..330
  uint16_t escHz         = 50;     // RC standard; raise only if the ESC accepts it
  uint16_t controlHz     = 100;    // control loop rate
};

struct Command {
  float    headingDeg = 0.0f;  // + = left (ROS REP-103), relative to car's nose
  float    speed      = 0.0f;  // -1..1 normalized
  uint64_t stampMs    = 0;
};

struct Output {
  uint16_t steerUs    = 1500;
  uint16_t throttleUs = BOOT_NEUTRAL_US;
  float    steerDeg   = 0.0f;
};

static portMUX_TYPE g_mux = portMUX_INITIALIZER_UNLOCKED;
static Config  g_cfg;
static Command g_cmd;
static Output  g_out;
static bool    g_armed       = false;
static int     g_rawSteerUs  = -1;     // >0: calibration override
static bool    g_failsafeEvt = false;  // set by control task, reported by loop
#ifdef RCCAR_COMMS_MICROROS
static uint32_t g_telemetryHz = 10;   // /rccar/mcu/telemetry rate; "TEL 0" turns it off
#else
static uint32_t g_telemetryHz = 0;    // ASCII: streamed only after "TEL <hz>"
#endif
static bool    g_timeSynced  = false;

static Preferences g_prefs;

static uint64_t nowMs() { return esp_timer_get_time() / 1000ULL; }

template <typename T>
static T clampv(T v, T lo, T hi) { return v < lo ? lo : (v > hi ? hi : v); }

// ---------------------------------------------------------------------------
// PWM layer (LEDC). Once a duty is set the hardware keeps emitting pulses.
// ---------------------------------------------------------------------------
static uint32_t usToDuty(uint32_t us, uint32_t hz) {
  const uint32_t periodUs = 1000000UL / hz;
  return (uint32_t)(((uint64_t)us << PWM_RES_BITS) / periodUs);
}

static void pwmInit(int pin, ledc_timer_t timer, ledc_channel_t ch,
                    uint32_t hz, uint16_t initialUs) {
  ledc_timer_config_t t = {};
  t.speed_mode      = LEDC_MODE;
  t.duty_resolution = (ledc_timer_bit_t)PWM_RES_BITS;
  t.timer_num       = timer;
  t.freq_hz         = hz;
  t.clk_cfg         = LEDC_AUTO_CLK;
  ESP_ERROR_CHECK(ledc_timer_config(&t));

  ledc_channel_config_t c = {};
  c.gpio_num   = pin;
  c.speed_mode = LEDC_MODE;
  c.channel    = ch;
  c.timer_sel  = timer;
  c.duty       = usToDuty(initialUs, hz);
  c.hpoint     = 0;
  ESP_ERROR_CHECK(ledc_channel_config(&c));
}

static void pwmWriteUs(ledc_channel_t ch, uint32_t hz, uint16_t us) {
  ledc_set_duty(LEDC_MODE, ch, usToDuty(us, hz));
  ledc_update_duty(LEDC_MODE, ch);
}

// ---------------------------------------------------------------------------
// Mapping
// ---------------------------------------------------------------------------
// heading (deg) -> road-wheel steering angle (deg), open loop for now.
// With an IMU this becomes a closed heading loop; the interface stays.
static float headingToSteerDeg(float headingDeg, const Config &c) {
  return clampv(headingDeg * c.headingGain, -c.maxSteerDeg, c.maxSteerDeg);
}

// steering angle -> pulse, piecewise linear so an asymmetric linkage works.
static uint16_t steerDegToUs(float deg, const Config &c) {
  float frac = deg / c.maxSteerDeg;  // -1 (right) .. +1 (left)
  float us = frac >= 0 ? c.steerCenterUs + frac * (c.steerLeftUs - c.steerCenterUs)
                       : c.steerCenterUs + -frac * (c.steerRightUs - c.steerCenterUs);
  uint16_t lo = min(c.steerLeftUs, c.steerRightUs);
  uint16_t hi = max(c.steerLeftUs, c.steerRightUs);
  return clampv<uint16_t>((uint16_t)lroundf(us), lo, hi);
}

// throttle fraction (-1..1, already speed-limited) -> ESC pulse
static uint16_t throttleToUs(float u, const Config &c) {
  if (fabsf(u) < 0.001f) return c.escNeutralUs;
  float span = (u > 0 ? c.escMaxUs - c.escNeutralUs : c.escNeutralUs - c.escMinUs) - c.deadbandUs;
  float us = c.escNeutralUs + (u > 0 ? 1 : -1) * (c.deadbandUs + fabsf(u) * span);
  return clampv<uint16_t>((uint16_t)lroundf(us), c.escMinUs, c.escMaxUs);
}

// ---------------------------------------------------------------------------
// Control task: the only writer of the PWM outputs
// ---------------------------------------------------------------------------
enum class RevState { Forward, Brake, Gap, Reverse };

static void controlTask(void *) {
  esp_task_wdt_add(nullptr);  // hang -> chip reset -> no pulses -> ESC cuts in 0.1 s
  TickType_t last = xTaskGetTickCount();
  float speedOut = 0.0f;
  RevState rs = RevState::Forward;
  uint64_t rsSince = 0;
  uint16_t servoHz = 50, escHz = 50;  // what the LEDC timers currently run at
  uint16_t controlHz = 100;

  for (;;) {
    vTaskDelayUntil(&last, pdMS_TO_TICKS(1000 / controlHz));
    esp_task_wdt_reset();

    Config cfg; Command cmd; bool armed; int raw;
    portENTER_CRITICAL(&g_mux);
    cfg = g_cfg; cmd = g_cmd; armed = g_armed; raw = g_rawSteerUs;
    portEXIT_CRITICAL(&g_mux);

    // Runtime frame-rate changes (tuning.toml -> SET servo_hz / esc_hz)
    if (cfg.servoHz != servoHz) { ledc_set_freq(LEDC_MODE, STEER_TIMER, cfg.servoHz); servoHz = cfg.servoHz; }
    if (cfg.escHz != escHz)     { ledc_set_freq(LEDC_MODE, THROTTLE_TIMER, cfg.escHz); escHz = cfg.escHz; }
    controlHz = cfg.controlHz;

    const uint64_t now = nowMs();
    const bool stale = (now - cmd.stampMs) > cfg.timeoutMs;
    if (armed && stale) {
      armed = false;
      portENTER_CRITICAL(&g_mux);
      g_armed = false; g_failsafeEvt = true;
      portEXIT_CRITICAL(&g_mux);
    }

    // Speed: slew-limited toward target; disarm snaps to neutral.
    const float target = armed ? clampv(cmd.speed, -1.0f, 1.0f) : 0.0f;
    const float step = cfg.accelPerSec / controlHz;
    speedOut = armed ? speedOut + clampv(target - speedOut, -step, step) : 0.0f;
    float u = speedOut * cfg.speedLimit;

    // Many brushed ESCs (Fwd/Brake/Rev mode) treat the first reverse pulse as
    // BRAKE and only reverse after a return to neutral. Do that sequence here.
    if (cfg.doubleTapRev) {
      switch (rs) {
        case RevState::Forward:
          if (u < 0) { rs = RevState::Brake; rsSince = now; u = -cfg.brakeLevel; }
          break;
        case RevState::Brake:
          if (u >= 0) rs = RevState::Forward;
          else if (now - rsSince >= cfg.brakeMs) { rs = RevState::Gap; rsSince = now; u = 0; }
          else u = -cfg.brakeLevel;
          break;
        case RevState::Gap:
          if (u >= 0) rs = RevState::Forward;
          else if (now - rsSince >= cfg.gapMs) rs = RevState::Reverse;
          else u = 0;
          break;
        case RevState::Reverse:
          if (u > 0) rs = RevState::Forward;
          break;
      }
    }

    // Steering follows commands even when disarmed (safe steering tuning).
    const float steerDeg = headingToSteerDeg(cmd.headingDeg, cfg);
    const uint16_t steerUs = raw > 0
        ? clampv<uint16_t>((uint16_t)raw, SERVO_ABS_MIN_US, SERVO_ABS_MAX_US)
        : steerDegToUs(steerDeg, cfg);
    const uint16_t thrUs = throttleToUs(u, cfg);

    pwmWriteUs(STEER_CH, servoHz, steerUs);
    pwmWriteUs(THROTTLE_CH, escHz, thrUs);

    portENTER_CRITICAL(&g_mux);
    g_out.steerUs = steerUs; g_out.throttleUs = thrUs; g_out.steerDeg = steerDeg;
    portEXIT_CRITICAL(&g_mux);
  }
}

// ---------------------------------------------------------------------------
// Persistence
// ---------------------------------------------------------------------------
static void loadConfig() {
  Config c;
  g_prefs.begin("rccar", true);
  size_t n = g_prefs.getBytes("cfg", &c, sizeof(c));
  g_prefs.end();
  if (n == sizeof(c) && c.magic == CFG_MAGIC) g_cfg = c;
}

static bool saveConfig() {
  Config c;
  portENTER_CRITICAL(&g_mux); c = g_cfg; portEXIT_CRITICAL(&g_mux);
  g_prefs.begin("rccar", false);
  size_t n = g_prefs.putBytes("cfg", &c, sizeof(c));
  g_prefs.end();
  return n == sizeof(c);
}

// ---------------------------------------------------------------------------
// Serial protocol (one ASCII command per line, see docs)
// ---------------------------------------------------------------------------
static void printConfig(Print &out) {
  Config c;
  portENTER_CRITICAL(&g_mux); c = g_cfg; portEXIT_CRITICAL(&g_mux);
  out.printf("CFG center=%u left=%u right=%u maxdeg=%.1f gain=%.2f limit=%.2f "
                "deadband=%u accel=%.2f timeout=%u revmode=%u brake_ms=%u gap_ms=%u "
                "brake_level=%.2f esc_min=%u esc_neutral=%u esc_max=%u servo_hz=%u "
                "esc_hz=%u control_hz=%u\n",
                c.steerCenterUs, c.steerLeftUs, c.steerRightUs, c.maxSteerDeg,
                c.headingGain, c.speedLimit, c.deadbandUs, c.accelPerSec,
                c.timeoutMs, c.doubleTapRev, c.brakeMs, c.gapMs, c.brakeLevel,
                c.escMinUs, c.escNeutralUs, c.escMaxUs, c.servoHz, c.escHz, c.controlHz);
}

#ifdef RCCAR_COMMS_ASCII
static void printTelemetry(Print &out) {
  Command cmd; Output o; bool armed;
  portENTER_CRITICAL(&g_mux); cmd = g_cmd; o = g_out; armed = g_armed; portEXIT_CRITICAL(&g_mux);
  struct timeval tv; gettimeofday(&tv, nullptr);
  uint64_t unixMs = g_timeSynced ? (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000 : 0;
  out.printf("TEL t=%llu unix=%llu hdg=%.1f spd=%.2f steer_deg=%.1f steer_us=%u thr_us=%u armed=%d\n",
                nowMs(), unixMs, cmd.headingDeg, cmd.speed, o.steerDeg,
                o.steerUs, o.throttleUs, armed);
}
#endif

static bool setKey(Config &c, const char *key, float v) {
  if      (!strcasecmp(key, "maxdeg"))   c.maxSteerDeg = clampv(v, 1.0f, 60.0f);
  else if (!strcasecmp(key, "gain"))     c.headingGain = clampv(v, 0.0f, 10.0f);
  else if (!strcasecmp(key, "limit"))    c.speedLimit  = clampv(v, 0.0f, 1.0f);
  else if (!strcasecmp(key, "deadband")) c.deadbandUs  = (uint16_t)clampv(v, 0.0f, 200.0f);
  else if (!strcasecmp(key, "accel"))    c.accelPerSec = clampv(v, 0.1f, 100.0f);
  else if (!strcasecmp(key, "timeout"))  c.timeoutMs   = (uint16_t)clampv(v, 50.0f, 2000.0f);
  else if (!strcasecmp(key, "revmode"))  c.doubleTapRev = v != 0;
  else if (!strcasecmp(key, "brake_ms")) c.brakeMs     = (uint16_t)clampv(v, 0.0f, 1000.0f);
  else if (!strcasecmp(key, "gap_ms"))   c.gapMs       = (uint16_t)clampv(v, 0.0f, 1000.0f);
  else if (!strcasecmp(key, "brake_level")) c.brakeLevel = clampv(v, 0.0f, 1.0f);
  else if (!strcasecmp(key, "esc_min"))     c.escMinUs     = (uint16_t)clampv(v, (float)ESC_ABS_MIN_US, 1500.0f);
  else if (!strcasecmp(key, "esc_neutral")) c.escNeutralUs = (uint16_t)clampv(v, 1300.0f, 1700.0f);
  else if (!strcasecmp(key, "esc_max"))     c.escMaxUs     = (uint16_t)clampv(v, 1500.0f, (float)ESC_ABS_MAX_US);
  else if (!strcasecmp(key, "servo_hz"))    c.servoHz   = (uint16_t)clampv(v, 50.0f, (float)SERVO_MAX_HZ);
  else if (!strcasecmp(key, "esc_hz"))      c.escHz     = (uint16_t)clampv(v, 50.0f, (float)ESC_MAX_HZ);
  else if (!strcasecmp(key, "control_hz"))  c.controlHz = (uint16_t)clampv(v, 20.0f, 500.0f);
  else return false;
  return true;
}

static void handleLine(char *line, Print &out) {
  char *tok = strtok(line, " \t\r");
  if (!tok) return;
  char *a1 = strtok(nullptr, " \t\r");
  char *a2 = strtok(nullptr, " \t\r");

  if (!strcasecmp(tok, "D")) {  // D <heading_deg> <speed>
    if (!a1 || !a2) { out.println("ERR usage: D <heading_deg> <speed>"); return; }
    portENTER_CRITICAL(&g_mux);
    g_cmd.headingDeg = clampv(strtof(a1, nullptr), -180.0f, 180.0f);
    g_cmd.speed      = clampv(strtof(a2, nullptr), -1.0f, 1.0f);
    g_cmd.stampMs    = nowMs();
    portEXIT_CRITICAL(&g_mux);
    // no reply: commands stream at 20-50 Hz, telemetry is the feedback
  } else if (!strcasecmp(tok, "ARM")) {
    portENTER_CRITICAL(&g_mux);
    g_cmd.speed = 0; g_cmd.stampMs = nowMs(); g_armed = true;
    portEXIT_CRITICAL(&g_mux);
    out.println("OK ARM");
  } else if (!strcasecmp(tok, "DISARM") || !strcasecmp(tok, "STOP")) {
    portENTER_CRITICAL(&g_mux); g_armed = false; g_cmd.speed = 0; portEXIT_CRITICAL(&g_mux);
    out.println("OK DISARM");
  } else if (!strcasecmp(tok, "PING")) {
    out.printf("PONG %s %llu\n", a1 ? a1 : "0", nowMs());
  } else if (!strcasecmp(tok, "TIME")) {  // TIME <unix_ms>
#ifdef RCCAR_COMMS_MICROROS
    // settimeofday() would shift CLOCK_REALTIME, which the XRCE client uses as its clock.
    out.println("ERR TIME unsupported: micro-ROS syncs the clock with the agent");
#else
    if (!a1) { out.println("ERR usage: TIME <unix_ms>"); return; }
    uint64_t ms = strtoull(a1, nullptr, 10);
    struct timeval tv = { (time_t)(ms / 1000), (suseconds_t)((ms % 1000) * 1000) };
    settimeofday(&tv, nullptr);
    g_timeSynced = true;
    out.printf("OK TIME %llu\n", ms);
#endif
  } else if (!strcasecmp(tok, "RAW")) {  // RAW <steer_us> | RAW OFF
    if (!a1) { out.println("ERR usage: RAW <us>|OFF"); return; }
    int us = strcasecmp(a1, "OFF") ? clampv<int>(atoi(a1), SERVO_ABS_MIN_US, SERVO_ABS_MAX_US) : -1;
    portENTER_CRITICAL(&g_mux); g_rawSteerUs = us; portEXIT_CRITICAL(&g_mux);
    out.printf("OK RAW %d\n", us);
  } else if (!strcasecmp(tok, "CAL")) {  // CAL LEFT|CENTER|RIGHT <us>
    if (!a1 || !a2) { printConfig(out); return; }
    uint16_t us = clampv<int>(atoi(a2), SERVO_ABS_MIN_US, SERVO_ABS_MAX_US);
    bool ok = true;
    portENTER_CRITICAL(&g_mux);
    if      (!strcasecmp(a1, "LEFT"))   g_cfg.steerLeftUs = us;
    else if (!strcasecmp(a1, "CENTER")) g_cfg.steerCenterUs = us;
    else if (!strcasecmp(a1, "RIGHT"))  g_cfg.steerRightUs = us;
    else ok = false;
    portEXIT_CRITICAL(&g_mux);
    if (ok) printConfig(out); else out.println("ERR CAL LEFT|CENTER|RIGHT <us>");
  } else if (!strcasecmp(tok, "SET")) {  // SET <key> <value>
    if (!a1 || !a2) { out.println("ERR usage: SET <key> <value>"); return; }
    Config c;
    portENTER_CRITICAL(&g_mux); c = g_cfg; portEXIT_CRITICAL(&g_mux);
    if (!setKey(c, a1, strtof(a2, nullptr))) { out.printf("ERR unknown key %s\n", a1); return; }
    if (!(c.escMinUs < c.escNeutralUs && c.escNeutralUs < c.escMaxUs)) {
      out.println("ERR need esc_min < esc_neutral < esc_max"); return;
    }
    portENTER_CRITICAL(&g_mux); g_cfg = c; portEXIT_CRITICAL(&g_mux);
    printConfig(out);
  } else if (!strcasecmp(tok, "GET")) {
    printConfig(out);
  } else if (!strcasecmp(tok, "SAVE")) {
    Config c;
    portENTER_CRITICAL(&g_mux); c = g_cfg; portEXIT_CRITICAL(&g_mux);
    bool between = (c.steerCenterUs > min(c.steerLeftUs, c.steerRightUs)) &&
                   (c.steerCenterUs < max(c.steerLeftUs, c.steerRightUs));
    if (!between) { out.println("ERR center must lie between left and right"); return; }
    out.println(saveConfig() ? "OK SAVE" : "ERR SAVE failed");
  } else if (!strcasecmp(tok, "DEFAULTS")) {
    portENTER_CRITICAL(&g_mux); g_cfg = Config(); portEXIT_CRITICAL(&g_mux);
    printConfig(out);  // not persisted until SAVE
  } else if (!strcasecmp(tok, "TEL")) {  // TEL <hz>, 0 = off
    g_telemetryHz = a1 ? clampv<int>(atoi(a1), 0, 50) : 10;
    out.printf("OK TEL %u\n", g_telemetryHz);
  } else if (!strcasecmp(tok, "SENS")) {  // reserved: future sensor reads
    out.printf("ERR SENS %s not implemented\n", a1 ? a1 : "?");
  } else if (!strcasecmp(tok, "INFO")) {
    out.printf("INFO fw=%s chip=%s rev=%d psram=%u flash=%u steer_pin=%d throttle_pin=%d\n",
                  FW_VERSION, ESP.getChipModel(), ESP.getChipRevision(),
                  ESP.getPsramSize(), ESP.getFlashChipSize(),
                  PIN_STEER_PWM, PIN_THROTTLE_PWM);
  } else {
    out.printf("ERR unknown command %s\n", tok);
  }
}

// ---------------------------------------------------------------------------
#ifdef RCCAR_COMMS_MICROROS
// micro-ROS comms layer (jazzy, XRCE-DDS framed over Serial/UART0). Same rules as the
// ASCII layer: runs in loop() only, shared state only inside g_mux, never writes PWM.
// UART0 carries the XRCE stream, so nothing else may print to Serial after setup.
//
// Safety is unchanged and lives in controlTask(): if /rccar/mcu/drive stops (agent lost,
// cable pulled, supervisor stopped) the D-timeout disarms and centres the outputs.
// This layer adds no way to arm other than the "ARM" command handled by handleLine().
//
//   sub  /rccar/mcu/drive     rccar_msgs/msg/DriveCmd    best effort  (same effect as "D")
//   pub  /rccar/mcu/telemetry rccar_msgs/msg/Telemetry   best effort  (g_telemetryHz)
//   pub  /rccar/mcu/event     rccar_msgs/msg/McuEvent    reliable
//   srv  /rccar/mcu/command   rccar_msgs/srv/McuCommand  handleLine() over a service
// Entity limits are in rccar.meta; keep them in sync when adding entities.
// ---------------------------------------------------------------------------
constexpr float RAD_TO_DEG_F = 57.29577951f;
constexpr float DEG_TO_RAD_F = 0.01745329252f;

// Event codes = rccar_msgs/msg/McuEvent constants (kept local to avoid depending on the
// generated enum names).
constexpr uint8_t EVT_READY = 1, EVT_FAILSAFE = 2, EVT_ARMED = 3, EVT_DISARMED = 4;

// Bounded string capacities incl. NUL (contract: command<=64, reply<=384, text<=64, source<=16)
constexpr size_t CMD_CAP   = 65;
constexpr size_t REPLY_CAP = 385;
constexpr size_t EVT_CAP   = 65;
constexpr size_t SRC_CAP   = 17;

// Print sink that captures handleLine() replies; truncates instead of overflowing.
class StrPrint : public Print {
 public:
  StrPrint() : len_(0) { buf_[0] = '\0'; }
  using Print::write;
  size_t write(uint8_t c) override {
    if (len_ < sizeof(buf_) - 1) { buf_[len_++] = (char)c; buf_[len_] = '\0'; }
    return 1;  // report success even when truncating, so Print does not retry
  }
  void reset() { len_ = 0; buf_[0] = '\0'; }
  size_t length() const { return len_; }
  const char *c_str() const { return buf_; }
 private:
  char buf_[REPLY_CAP];
  size_t len_;
};

// Arduino loop task stack (weak symbol in the core, default 8 KB): rcl + CDR need more.
size_t getArduinoLoopTaskStackSize(void) { return 16384; }

// Messages and their string storage are static: no heap use per message.
static rccar_msgs__msg__DriveCmd             g_driveMsg;
static rccar_msgs__msg__Telemetry            g_telMsg;
static rccar_msgs__msg__McuEvent             g_evtMsg;
static rccar_msgs__srv__McuCommand_Request   g_cmdReq;
static rccar_msgs__srv__McuCommand_Response  g_cmdRes;
static char g_srcBuf[SRC_CAP];
static char g_evtBuf[EVT_CAP];
static char g_reqBuf[CMD_CAP];
static char g_resBuf[REPLY_CAP];
static StrPrint g_reply;

static void initMessages() {
  memset(&g_driveMsg, 0, sizeof(g_driveMsg));
  memset(&g_telMsg, 0, sizeof(g_telMsg));
  memset(&g_evtMsg, 0, sizeof(g_evtMsg));
  memset(&g_cmdReq, 0, sizeof(g_cmdReq));
  memset(&g_cmdRes, 0, sizeof(g_cmdRes));
  g_srcBuf[0] = g_evtBuf[0] = g_reqBuf[0] = g_resBuf[0] = '\0';
  g_driveMsg.source.data = g_srcBuf;  g_driveMsg.source.size = 0;  g_driveMsg.source.capacity = SRC_CAP;
  g_evtMsg.text.data     = g_evtBuf;  g_evtMsg.text.size = 0;      g_evtMsg.text.capacity = EVT_CAP;
  g_cmdReq.command.data  = g_reqBuf;  g_cmdReq.command.size = 0;   g_cmdReq.command.capacity = CMD_CAP;
  g_cmdRes.reply.data    = g_resBuf;  g_cmdRes.reply.size = 0;     g_cmdRes.reply.capacity = REPLY_CAP;
}

// ---- entities --------------------------------------------------------------
static rcl_allocator_t    g_alloc;
static rclc_support_t     g_support;
static rcl_node_t         g_node;
static rcl_publisher_t    g_telPub;
static rcl_publisher_t    g_evtPub;
static rcl_subscription_t g_driveSub;
static rcl_service_t      g_cmdSrv;
static rclc_executor_t    g_exec;

// How far creation got, so a failed or lost session is torn down exactly as far as needed.
enum { ST_NONE = 0, ST_SUPPORT, ST_NODE, ST_TELPUB, ST_EVTPUB, ST_DRIVESUB, ST_CMDSRV, ST_EXEC };
static int g_stage = ST_NONE;

#define RCCAR_STEP(call, stage) \
  do { if ((call) != RCL_RET_OK) return false; g_stage = (stage); } while (0)

// "D heading_deg speed" for DriveCmd: same clamps, same stamp, same critical section.
static void driveCb(const void *msgin) {
  const rccar_msgs__msg__DriveCmd *m = (const rccar_msgs__msg__DriveCmd *)msgin;
  const float h = m->heading_rad * RAD_TO_DEG_F;
  const float t = m->throttle;
  if (!std::isfinite(h) || !std::isfinite(t)) return;  // drop: no stamp refresh -> failsafe
  portENTER_CRITICAL(&g_mux);
  g_cmd.headingDeg = clampv(h, -180.0f, 180.0f);
  g_cmd.speed      = clampv(t, -1.0f, 1.0f);
  g_cmd.stampMs    = nowMs();
  portEXIT_CRITICAL(&g_mux);
}

// McuCommand: run the ASCII parser, capture its reply.
static void commandCb(const void *reqin, void *resout) {
  const rccar_msgs__srv__McuCommand_Request *req = (const rccar_msgs__srv__McuCommand_Request *)reqin;
  rccar_msgs__srv__McuCommand_Response *res = (rccar_msgs__srv__McuCommand_Response *)resout;

  char line[CMD_CAP];  // handleLine() tokenizes in place
  size_t n = req->command.data ? req->command.size : 0;
  if (n > CMD_CAP - 1) n = CMD_CAP - 1;
  if (n) memcpy(line, req->command.data, n);
  line[n] = '\0';

  g_reply.reset();
  handleLine(line, g_reply);

  size_t rl = g_reply.length();
  while (rl && (g_reply.c_str()[rl - 1] == '\n' || g_reply.c_str()[rl - 1] == '\r')) --rl;
  memcpy(res->reply.data, g_reply.c_str(), rl);
  res->reply.data[rl] = '\0';
  res->reply.size = rl;
  res->ok = strncmp(res->reply.data, "ERR", 3) != 0;
}

static bool createEntities() {
  initMessages();
  g_alloc    = rcl_get_default_allocator();
  g_node     = rcl_get_zero_initialized_node();
  g_telPub   = rcl_get_zero_initialized_publisher();
  g_evtPub   = rcl_get_zero_initialized_publisher();
  g_driveSub = rcl_get_zero_initialized_subscription();
  g_cmdSrv   = rcl_get_zero_initialized_service();
  g_exec     = rclc_executor_get_zero_initialized_executor();

  RCCAR_STEP(rclc_support_init(&g_support, 0, NULL, &g_alloc), ST_SUPPORT);
  RCCAR_STEP(rclc_node_init_default(&g_node, "rccar_mcu", "", &g_support), ST_NODE);
  RCCAR_STEP(rclc_publisher_init_best_effort(&g_telPub, &g_node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(rccar_msgs, msg, Telemetry), "/rccar/mcu/telemetry"), ST_TELPUB);
  RCCAR_STEP(rclc_publisher_init_default(&g_evtPub, &g_node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(rccar_msgs, msg, McuEvent), "/rccar/mcu/event"), ST_EVTPUB);
  RCCAR_STEP(rclc_subscription_init_best_effort(&g_driveSub, &g_node,
      ROSIDL_GET_MSG_TYPE_SUPPORT(rccar_msgs, msg, DriveCmd), "/rccar/mcu/drive"), ST_DRIVESUB);
  RCCAR_STEP(rclc_service_init_default(&g_cmdSrv, &g_node,
      ROSIDL_GET_SRV_TYPE_SUPPORT(rccar_msgs, srv, McuCommand), "/rccar/mcu/command"), ST_CMDSRV);
  RCCAR_STEP(rclc_executor_init(&g_exec, &g_support.context, 2, &g_alloc), ST_EXEC);  // sub + service
  if (rclc_executor_add_subscription(&g_exec, &g_driveSub, &g_driveMsg, &driveCb, ON_NEW_DATA) != RCL_RET_OK) return false;
  if (rclc_executor_add_service(&g_exec, &g_cmdSrv, &g_cmdReq, &g_cmdRes, commandCb) != RCL_RET_OK) return false;
  return true;
}

static void destroyEntities() {
  if (g_stage >= ST_SUPPORT) {  // agent may be gone: do not wait for it to confirm the deletes
    rmw_context_t *rmw = rcl_context_get_rmw_context(&g_support.context);
    (void)rmw_uros_set_context_entity_destroy_session_timeout(rmw, 0);
  }
  if (g_stage >= ST_EXEC)     (void)rclc_executor_fini(&g_exec);
  if (g_stage >= ST_CMDSRV)   (void)rcl_service_fini(&g_cmdSrv, &g_node);
  if (g_stage >= ST_DRIVESUB) (void)rcl_subscription_fini(&g_driveSub, &g_node);
  if (g_stage >= ST_EVTPUB)   (void)rcl_publisher_fini(&g_evtPub, &g_node);
  if (g_stage >= ST_TELPUB)   (void)rcl_publisher_fini(&g_telPub, &g_node);
  if (g_stage >= ST_NODE)     (void)rcl_node_fini(&g_node);
  if (g_stage >= ST_SUPPORT)  (void)rclc_support_fini(&g_support);
  g_stage = ST_NONE;
}

// ---- publishing ------------------------------------------------------------
// Stamp = agent epoch time. settimeofday() is NOT used: the XRCE client's clock is
// CLOCK_REALTIME, so changing it would corrupt session timeouts and the sync offset.
static void fillStamp(builtin_interfaces__msg__Time &t) {
  int64_t ns = g_timeSynced ? rmw_uros_epoch_nanos() : 0;
  if (ns < 0) ns = 0;
  t.sec = (int32_t)(ns / 1000000000LL);
  t.nanosec = (uint32_t)(ns % 1000000000LL);
}

static void publishEvent(uint8_t code, const char *text) {
  fillStamp(g_evtMsg.stamp);
  g_evtMsg.code = code;
  size_t n = strlen(text);
  if (n > EVT_CAP - 1) n = EVT_CAP - 1;
  memcpy(g_evtBuf, text, n);
  g_evtBuf[n] = '\0';
  g_evtMsg.text.size = n;
  (void)rcl_publish(&g_evtPub, &g_evtMsg, NULL);  // a dead link is caught by the ping
}

static void publishTelemetry() {
  Command cmd; Output o; bool armed;
  portENTER_CRITICAL(&g_mux); cmd = g_cmd; o = g_out; armed = g_armed; portEXIT_CRITICAL(&g_mux);
  fillStamp(g_telMsg.stamp);
  g_telMsg.mcu_ms       = nowMs();
  g_telMsg.heading_rad  = cmd.headingDeg * DEG_TO_RAD_F;
  g_telMsg.throttle     = cmd.speed;
  g_telMsg.steer_rad    = o.steerDeg * DEG_TO_RAD_F;
  g_telMsg.steer_us     = o.steerUs;
  g_telMsg.throttle_us  = o.throttleUs;
  g_telMsg.armed        = armed;
  g_telMsg.time_synced  = g_timeSynced;
  (void)rcl_publish(&g_telPub, &g_telMsg, NULL);
}

// ---- reconnection state machine (agent may appear, vanish and return at any time) ------
enum class AgentState { Wait, Available, Connected, Disconnected };
static AgentState g_state = AgentState::Wait;
static uint64_t g_nextPingMs = 0;
static uint64_t g_lastTelMs  = 0;
static bool     g_lastArmed  = false;

static void onConnected() {
  g_timeSynced = (rmw_uros_sync_session(1000) == RMW_RET_OK);
  portENTER_CRITICAL(&g_mux); g_failsafeEvt = false; g_lastArmed = g_armed; portEXIT_CRITICAL(&g_mux);
  char text[EVT_CAP];
  snprintf(text, sizeof(text), "fw=%s", FW_VERSION);
  publishEvent(EVT_READY, text);
}

static void microrosSetup() {
  set_microros_serial_transports(Serial);  // Serial.begin() already done in setup()
  g_state = AgentState::Wait;
}

static void microrosLoop() {
  switch (g_state) {
    case AgentState::Wait:
      if (nowMs() >= g_nextPingMs) {
        g_nextPingMs = nowMs() + 500;
        if (rmw_uros_ping_agent(100, 1) == RMW_RET_OK) g_state = AgentState::Available;
      }
      break;

    case AgentState::Available:  // can block for seconds; controlTask keeps running
      if (createEntities()) {
        onConnected();
        g_lastTelMs = nowMs();
        g_nextPingMs = nowMs() + 1000;
        g_state = AgentState::Connected;
      } else {
        destroyEntities();
        g_nextPingMs = nowMs() + 1000;
        g_state = AgentState::Wait;
      }
      break;

    case AgentState::Connected: {
      (void)rclc_executor_spin_some(&g_exec, RCL_MS_TO_NS(2));  // short: loop() must not block

      bool fs, armed;
      portENTER_CRITICAL(&g_mux); fs = g_failsafeEvt; g_failsafeEvt = false; armed = g_armed; portEXIT_CRITICAL(&g_mux);
      if (fs) publishEvent(EVT_FAILSAFE, "command timeout -> disarmed");
      if (armed != g_lastArmed) {
        g_lastArmed = armed;
        publishEvent(armed ? EVT_ARMED : EVT_DISARMED, "");
      }

      const uint64_t now = nowMs();
      const uint32_t hz = g_telemetryHz;
      if (hz && now - g_lastTelMs >= 1000 / hz) {
        g_lastTelMs = now;
        publishTelemetry();
      }
      if (now >= g_nextPingMs) {  // sparse: a ping costs up to 200 ms when the agent is gone
        g_nextPingMs = now + 1000;
        if (rmw_uros_ping_agent(100, 2) != RMW_RET_OK) g_state = AgentState::Disconnected;
      }
      break;
    }

    case AgentState::Disconnected:
      destroyEntities();
      g_timeSynced = false;
      g_nextPingMs = nowMs() + 500;
      g_state = AgentState::Wait;
      break;
  }
  delay(1);  // let lower-priority tasks run
}
#endif  // RCCAR_COMMS_MICROROS

// ---------------------------------------------------------------------------
void setup() {
  // Outputs first: neutral pulses from the very first moment, so the ESC
  // learns 1500 us as neutral when it is switched on.
  // Always boot at 50 Hz / 1500 us; saved frame rates are applied by the
  // control task once it starts.
  pwmInit(PIN_STEER_PWM, STEER_TIMER, STEER_CH, 50, BOOT_NEUTRAL_US);
  pwmInit(PIN_THROTTLE_PWM, THROTTLE_TIMER, THROTTLE_CH, 50, BOOT_NEUTRAL_US);

#ifdef RCCAR_COMMS_MICROROS
  Serial.setRxBufferSize(1024);  // before begin(); NVS writes can stall loop() for a while
#endif
  Serial.begin(115200);
  loadConfig();
  xTaskCreatePinnedToCore(controlTask, "control", 4096, nullptr,
                          configMAX_PRIORITIES - 2, nullptr, 1);
#ifdef RCCAR_COMMS_MICROROS
  microrosSetup();  // no Serial prints from here on: UART0 carries the XRCE stream
#else
  Serial.printf("READY fw=%s\n", FW_VERSION);
#endif
}

void loop() {
#ifdef RCCAR_COMMS_MICROROS
  microrosLoop();
#else
  static char buf[96];
  static size_t len = 0;
  static uint64_t lastTel = 0;

  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n') { buf[len] = '\0'; handleLine(buf, Serial); len = 0; }
    else if (len < sizeof(buf) - 1) buf[len++] = ch;
    else len = 0;  // overlong line: drop it
  }

  bool fs;
  portENTER_CRITICAL(&g_mux); fs = g_failsafeEvt; g_failsafeEvt = false; portEXIT_CRITICAL(&g_mux);
  if (fs) Serial.println("EVT FAILSAFE command timeout -> disarmed");

  if (g_telemetryHz && nowMs() - lastTel >= 1000 / g_telemetryHz) {
    lastTel = nowMs();
    printTelemetry(Serial);
  }
  delay(1);
#endif
}
