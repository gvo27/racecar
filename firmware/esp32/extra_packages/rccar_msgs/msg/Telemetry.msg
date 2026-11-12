# MCU telemetry (firmware TEL line equivalent). Published by the ESP32, best effort.
builtin_interfaces/Time stamp   # MCU clock after rmw_uros_sync_session; zero if not synced
uint64 mcu_ms                   # MCU monotonic ms since boot
float32 heading_rad             # last accepted command
float32 throttle                # last accepted command
float32 steer_rad               # commanded steering angle
uint16 steer_us                 # servo pulse
uint16 throttle_us              # ESC pulse
bool armed
bool time_synced
