# firmware toolchain: PlatformIO + esptool for firmware/esp32. Notes: .claude/rules/dependencies.md
# Build: make fw-image    Run: make build | flash | monitor
# The default env (esp32s3) pulls micro_ros_platformio, which colcon-builds the micro-ROS
# library during the first `pio run` (git clone of ROS repos + pip into the PlatformIO penv:
# needs network). That build is NOT baked into the image; with the named volume
# `rccar-platformio-v2` and `.pio/libdeps` kept by `make build` it only happens once.
FROM python:3.12-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLATFORMIO_CORE_DIR=/opt/platformio \
    PLATFORMIO_SETTING_ENABLE_TELEMETRY=no \
    HOME=/tmp \
    PATH=/opt/platformio/penv/bin:$PATH

# micro_ros_platformio build-time tools (README: git, cmake, pip3). python:3.12 already ships
# pip and venv; build-essential gives make/gcc for the colcon host tools and python sdists.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git cmake build-essential \
 && rm -rf /var/lib/apt/lists/*

# PlatformIO lives in its standard virtualenv $PLATFORMIO_CORE_DIR/penv (the layout the
# official installer creates). micro_ros_platformio sources penv/bin/activate and pip-installs
# its build tools (colcon, catkin-pkg, empy) into the env pio runs from, so pio must run from it.
RUN python -m venv /opt/platformio/penv \
 && /opt/platformio/penv/bin/pip install platformio==6.1.16 esptool==4.8.1 pyserial==3.5

# Pre-install the project's packages (espressif32@6.9.0 platform, board toolchain,
# arduino-esp32 2.0.17 framework, scons) into the core dir. A project-context install
# is needed: a global `pio pkg install -p` skips the board-specific optional packages.
# `-e esp32s3` also clones micro_ros_platformio into the throwaway seed dir; the micro-ROS
# library itself is only built at the first `pio run` (not baked into the image).
# A named volume mounted on PLATFORMIO_CORE_DIR is seeded from this layer on first use;
# a bind mount is not (packages are then downloaded on the first build).
# a+rwX: the Makefile runs as the host uid (--user), which differs from root/rccar.
COPY firmware/esp32/platformio.ini /tmp/seed/platformio.ini
RUN pio pkg install -d /tmp/seed -e esp32s3 \
 && rm -rf /tmp/seed \
 && chmod -R a+rwX /opt/platformio

# non-root default; the Makefile overrides with --user $(id -u):$(id -g) --group-add <dialout gid>.
# HOME=/tmp is world-writable, so any uid has a writable HOME/cache.
RUN useradd -m -u 1000 -G dialout rccar
USER rccar
WORKDIR /work/firmware/esp32
