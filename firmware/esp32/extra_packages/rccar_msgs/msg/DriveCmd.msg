# Drive command. REP-103: +heading = turn left (CCW).
# Producers publish on their own input topic (/rccar/cmd/<source>); the supervisor
# is the ONLY publisher on /rccar/mcu/drive. Priority comes from supervisor config,
# never from this message.
builtin_interfaces/Time stamp
float32 heading_rad    # desired heading change, rad, clamped to +-pi by firmware
float32 throttle       # dimensionless [-1, 1]; not m/s (no wheel odometry yet)
string<=16 source      # logging only (admin, captain, ...)
