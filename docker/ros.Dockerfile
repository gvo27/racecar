# ros runtime: ROS 2 Jazzy + the rccar_* workspace. Notes: .claude/rules/dependencies.md
# Build: make ros-image    Test: make ros-test (builds target `test`, runs colcon test)
# Context = repo root, filtered by docker/ros.Dockerfile.dockerignore. Stages:
#   builder  rosdep (apt deps from package.xml) + colcon build --merge-install -> /ws/install
#   test     builder + `colcon test` entrypoint (CI, make ros-test)
#   runtime  ros-base + runtime deps + /ws/install only (default target; no compilers/sources)
# Runtime layout: the repo is bind-mounted at /ws/src/racecar (tuning.toml, read-write for
# calibration); /ws/install holds the built packages. Devices come in via compose group_add.
# rosdep needs raw.githubusercontent.com + packages.ros.org. Offline/sandbox builds only:
# --build-arg ROSDEP_INSTALL=0 skips rosdep install (every dep must then already be in the
# base image; ros-base has them today). Default 1 = real resolution, fails loudly on a bad key.

# TODO(bump): refresh with `docker pull ros:jazzy-ros-base && docker inspect --format '{{index .RepoDigests 0}}' ros:jazzy-ros-base`
ARG ROS_BASE=ros:jazzy-ros-base@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617
ARG ROSDEP_INSTALL=1

FROM ${ROS_BASE} AS builder
ARG ROSDEP_INSTALL
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /ws

# packages first (cache: only changes when package.xml files change)
COPY rccar_msgs/package.xml src/racecar/rccar_msgs/package.xml
COPY rccar_mcu_bridge/package.xml src/racecar/rccar_mcu_bridge/package.xml
COPY rccar_supervisor/package.xml src/racecar/rccar_supervisor/package.xml
COPY rccar_teleop/package.xml src/racecar/rccar_teleop/package.xml
COPY rccar_calibration/package.xml src/racecar/rccar_calibration/package.xml
COPY rccar_bringup/package.xml src/racecar/rccar_bringup/package.xml
COPY repos/ src/racecar/repos/

# third-party sources (manifest is empty today; vcs import is skipped then)
RUN if grep -Eq '^\s+type:' src/racecar/repos/rccar.repos; then \
      vcs import src < src/racecar/repos/rccar.repos; \
    else echo "repos/rccar.repos is empty: nothing to import"; fi

# apt deps from package.xml via rosdep (exec + build + test deps). apt cache cleaned.
RUN if [ "${ROSDEP_INSTALL}" = "1" ]; then \
      rosdep update --rosdistro jazzy \
      && apt-get update \
      && rosdep install --from-paths src --ignore-src -y --rosdistro jazzy \
      && rm -rf /var/lib/apt/lists/*; \
    else echo "WARN: ROSDEP_INSTALL=0, skipping rosdep install (offline build)"; fi

# full sources + what the tests read from the repo root (tuning.toml, firmware setKey names)
COPY rccar_msgs/ src/racecar/rccar_msgs/
COPY rccar_mcu_bridge/ src/racecar/rccar_mcu_bridge/
COPY rccar_supervisor/ src/racecar/rccar_supervisor/
COPY rccar_teleop/ src/racecar/rccar_teleop/
COPY rccar_calibration/ src/racecar/rccar_calibration/
COPY rccar_bringup/ src/racecar/rccar_bringup/
COPY tuning.toml src/racecar/tuning.toml
COPY firmware/esp32/src/main.cpp src/racecar/firmware/esp32/src/main.cpp

RUN source /opt/ros/jazzy/setup.bash \
 && colcon build --merge-install --event-handlers console_cohesion+ \
      --cmake-args -DCMAKE_BUILD_TYPE=Release

# --- test: colcon test + results (docker run exit code = test result; /out gets log + xml) --
FROM builder AS test
COPY docker/entrypoint.sh docker/ros-test.sh /
RUN chmod 0755 /entrypoint.sh /ros-test.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/ros-test.sh"]

# --- runtime ------------------------------------------------------------------------------
FROM ${ROS_BASE} AS runtime
ARG ROSDEP_INSTALL
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp
WORKDIR /ws

# runtime (exec) deps only: rosdep resolves the package.xml of the built workspace
COPY --from=builder /ws/src/racecar/rccar_msgs/package.xml /tmp/src/rccar_msgs/package.xml
COPY --from=builder /ws/src/racecar/rccar_mcu_bridge/package.xml /tmp/src/rccar_mcu_bridge/package.xml
COPY --from=builder /ws/src/racecar/rccar_supervisor/package.xml /tmp/src/rccar_supervisor/package.xml
COPY --from=builder /ws/src/racecar/rccar_teleop/package.xml /tmp/src/rccar_teleop/package.xml
COPY --from=builder /ws/src/racecar/rccar_calibration/package.xml /tmp/src/rccar_calibration/package.xml
COPY --from=builder /ws/src/racecar/rccar_bringup/package.xml /tmp/src/rccar_bringup/package.xml
RUN if [ "${ROSDEP_INSTALL}" = "1" ]; then \
      rosdep update --rosdistro jazzy \
      && apt-get update \
      && rosdep install --from-paths /tmp/src --ignore-src -y --rosdistro jazzy \
           --dependency-types exec \
      && rm -rf /var/lib/apt/lists/* /root/.ros; \
    else echo "WARN: ROSDEP_INSTALL=0, skipping rosdep install (offline build)"; fi \
 && rm -rf /tmp/src

COPY --from=builder /ws/install /ws/install
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh \
 && usermod -aG dialout ubuntu

# non-root default: the base image's `ubuntu` user (uid 1000); compose overrides user: with the host uid/gid so calibration
# can write the bind-mounted tuning.toml, and adds the host dialout gid via group_add.
USER ubuntu
ENV RCCAR_TUNING=/ws/src/racecar/tuning.toml \
    ROS_LOG_DIR=/tmp/roslog \
    ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "rccar_bringup", "car.launch.py"]
