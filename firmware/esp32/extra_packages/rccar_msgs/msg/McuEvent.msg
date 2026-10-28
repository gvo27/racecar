# Asynchronous MCU events (firmware READY/EVT equivalents). Reliable.
uint8 READY = 1        # firmware booted / micro-ROS entities created
uint8 FAILSAFE = 2     # drive command timeout -> disarmed + neutral
uint8 ARMED = 3
uint8 DISARMED = 4
uint8 ERROR = 255

builtin_interfaces/Time stamp
uint8 code
string<=64 text
