# Supervisor state. Reliable + transient_local so late joiners see a latched stop.
builtin_interfaces/Time stamp
bool armed
bool estop_latched
uint32 incident            # increments on every brake/disarm latch; Reset must quote it
string<=32 active_source   # input currently forwarded ("" = none)
string<=64 reason          # why latched / why not forwarding
