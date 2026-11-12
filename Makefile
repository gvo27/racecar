# RC car platform. Run `make help`. Setup steps: docs/setup.md
# Host needs only git, make, docker (+compose, buildx). Everything else runs in containers:
# car stack (ROS 2 + micro-ROS, deploy/car/compose.yaml): config, ros-image, car-*, teleop, calibrate, tune, test, mcu.
# Firmware targets (build/flash/monitor/clean/compiledb) run in docker (docker/firmware.Dockerfile); FW_ENV picks the env.
# USB cable goes in the board's right-hand USB-C port, labelled "COM".
FW_DIR   := firmware/esp32
FW_ENV   ?= esp32s3
FW_IMAGE ?= rccar-fw
# bump FW_VOL suffix when the image core-dir layout changes (v2: penv) so the volume reseeds
FW_VOL   ?= rccar-platformio-v2
DIALOUT_GID := $(shell getent group dialout 2>/dev/null | cut -d: -f3)
FW_RUN   := docker run --rm --user $(shell id -u):$(shell id -g) \
            $(if $(DIALOUT_GID),--group-add $(DIALOUT_GID),) \
            -v "$(CURDIR)":/work -v "$(FW_VOL)":/opt/platformio -w /work/$(FW_DIR)
# serial port: udev symlink from make install-host (override: PORT=/dev/ttyUSB0)
PORT     ?= /dev/rccar-esp32
# ROS stack
ROS_IMAGE      ?= rccar-ros:local
ROS_TEST_IMAGE ?= rccar-ros-test:local
ROS_TEST_OUT   ?= build/ros-test
ROS_BUILD_ARGS ?=
# KiCad 10 + Freerouting for the power board (docs/schematics); images pinned by digest
KICAD_IMAGE      ?= rccar-kicad:local
FREEROUTING_IMAGE := ghcr.io/freerouting/freerouting:2.5.0@sha256:6c195891c9b1d62620c140784ab91285b9350d12d905693defe0162eb128cf8e
SCH_DIR          := docs/schematics
# global lib tables: kicad-cli in a bare container finds no stock libraries (false ERC warnings), so copy the templates
KICAD_CFG        := $(CURDIR)/build/kicad-cfg
KICAD_RUN        = docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -e XDG_CONFIG_HOME=$(KICAD_CFG) \
                   -v "$(CURDIR)":"$(CURDIR)" -w "$(CURDIR)/$(SCH_DIR)" $(KICAD_IMAGE)
COMPOSE  := docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated

.DEFAULT_GOAL := help
.PHONY: help setup clean build flash monitor fw-image config models compiledb unit check-dev \
        ros-image ros-test ros-test-image ros-test-run ros-shell car-up car-down car-ps car-logs car-pull \
        car-shutdown install-host teleop calibrate tune test rangefinder viz lidar-imu lidar-snapshot lidar-record mcu unit-run \
        drivers-stop drivers-start lidar-hw-test kicad-image erc pcb-build pcb-route pcb-check pcb-mill-check pcb-review pcb-test \
        _kicad-cfg _clean-build _need-config _need-stack _need-stack-down _need-drivers-down

help:            ## list targets (grouped in README.md)
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-21s %s\n", $$1, $$2}'

# ---- setup / config -------------------------------------------------------------------------
setup:           ## check host prereqs (git, make, docker + compose/buildx), build the firmware and ROS images
	@for c in git make docker; do command -v $$c >/dev/null || { echo "MISSING host prerequisite: $$c"; exit 1; }; done
	@docker compose version >/dev/null 2>&1 || echo "WARN: docker compose plugin missing (needed for make car-up)"
	@docker buildx version >/dev/null 2>&1 || echo "WARN: docker buildx missing (needed for multi-arch images)"
	$(MAKE) fw-image
	$(MAKE) ros-image

config:          ## render deploy/car/.env.generated from .env + tuning.toml [platform.$PLATFORM] (runs in the ROS image)
	@test -n "$(DIALOUT_GID)" || { echo "group 'dialout' not found: sudo usermod -aG dialout $$USER (docs/setup.md)"; exit 1; }
	@docker image inspect $(ROS_IMAGE) >/dev/null 2>&1 || { echo "image $(ROS_IMAGE) missing: run make ros-image"; exit 1; }
	docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)":/work -w /work $(ROS_IMAGE) \
	  python3 deploy/render_env.py --repo-dir "$(CURDIR)" --dialout-gid $(DIALOUT_GID)

models:          ## print models/manifest.yaml (download + sha256 verify not implemented; needs tailnet)
	@cat models/manifest.yaml
	@echo "download + sha256 verify into models/cache/ not implemented yet (requires Tailscale tailnet, see models/README.md)"

install-host:    ## sudo: install udev rule (/dev/rccar-esp32) + systemd unit rccar.service, enable at boot
	@echo "install-host: udev rule -> /etc/udev/rules.d/99-rccar.rules (CH343 1a86:55d3 -> /dev/rccar-esp32, group dialout)"
	sudo install -m 0644 deploy/car/99-rccar.rules /etc/udev/rules.d/99-rccar.rules
	sudo udevadm control --reload-rules
	sudo udevadm trigger --subsystem-match=tty
	@echo "install-host: systemd unit -> /etc/systemd/system/rccar.service (WorkingDirectory=$(CURDIR), User=$(shell id -un))"
	sed -e 's|@REPO_DIR@|$(CURDIR)|g' -e 's|@USER@|$(shell id -un)|g' deploy/car/rccar.service \
	  | sudo tee /etc/systemd/system/rccar.service >/dev/null
	sudo systemctl daemon-reload
	sudo systemctl enable rccar.service
	@echo "install-host: done. The stack now starts at boot. Start it now: make car-up. Unplug/replug the USB cable once for the udev symlink."

# ---- car stack (ROS 2 in docker) ------------------------------------------------------------
ros-image: _need-drivers-down  ## build the ROS 2 image (docker/ros.Dockerfile -> rccar-ros:local)
	docker build -f docker/ros.Dockerfile $(ROS_BUILD_ARGS) -t $(ROS_IMAGE) .

ros-test-image:  ## build the ROS test image (target test: colcon build, all test deps)
	docker build -f docker/ros.Dockerfile --target test $(ROS_BUILD_ARGS) -t $(ROS_TEST_IMAGE) .

ros-test-run:    ## run colcon test in an already built test image; results in build/ros-test
	mkdir -p $(ROS_TEST_OUT)
	docker run --rm -e HOST_UID=$(shell id -u) -e HOST_GID=$(shell id -g) -v "$(CURDIR)/$(ROS_TEST_OUT)":/out $(ROS_TEST_IMAGE)

ros-test: ros-test-image ros-test-run  ## build the test image + colcon test + test-result (no hardware)

car-up: config   ## render config, start mcu-agent + core + drivers (docker compose up -d)
	$(COMPOSE) up -d
	@echo "car-up: check health with: make car-ps   logs: make car-logs"

car-down:        ## stop the car stack (the ESP32 failsafe disarms)
	$(COMPOSE) down

car-ps:          ## status + health of the car stack
	$(COMPOSE) ps

car-logs:        ## follow the car stack logs (Ctrl+C to exit)
	$(COMPOSE) logs -f --tail=100

car-pull: config ## pull the pinned third-party images (agent; core too when RCCAR_ROS_IMAGE is a registry image)
	$(COMPOSE) pull mcu-agent
	@grep -q '^RCCAR_ROS_IMAGE=rccar-ros:local$$' deploy/car/.env.generated || $(COMPOSE) pull core

car-shutdown:    ## disarm via supervisor, stop the stack, then sudo poweroff (asks first)
	-$(COMPOSE) exec -T core /entrypoint.sh ros2 service call /supervisor/disarm std_srvs/srv/Trigger "{}" \
	  || echo "WARN: disarm call failed (stack not running?). Stopping the stack; the ESP32 failsafe disarms."
	$(COMPOSE) down
	@printf "Stack stopped. Power off this machine now? [y/N] "; read ans; \
	  case "$$ans" in y|Y) sudo poweroff;; *) echo "not powering off";; esac

ros-shell: _need-config  ## shell in the tools container (ROS env sourced, repo at /ws/src/racecar)
	$(COMPOSE) run --rm tools bash

_need-config:
	@test -f deploy/car/.env.generated || { echo "deploy/car/.env.generated missing: run make config"; exit 1; }

_need-stack: _need-config
	@$(COMPOSE) ps --status running --services 2>/dev/null | grep -qx core \
	  || { echo "car stack is not running: make car-up (check: make car-ps)"; exit 1; }

# serial-port users (flash, monitor) must not collide with the micro-ROS agent
_need-stack-down:
	@if $(COMPOSE) ps --status running -q 2>/dev/null | grep -q .; then \
	  echo "car stack is running and holds the serial port: make car-down first"; exit 1; fi

# lidar driver container: stop before editing/rebuilding rccar_drivers (guard hook: .claude/hooks/hw_guard.py)
drivers-stop: _need-config  ## stop only the lidar driver container (safe; required before editing/rebuilding rccar_drivers)
	$(COMPOSE) stop drivers

drivers-start: _need-config  ## start the lidar driver container (hardware restart: humans/explicitly approved only)
	$(COMPOSE) up -d drivers

# no-op without a rendered config or a usable compose (CI, laptops)
_need-drivers-down:
	@if [ -f deploy/car/.env.generated ] && [ -n "$$($(COMPOSE) ps --status running -q drivers 2>/dev/null)" ]; then \
	  echo "lidar driver container is running: make drivers-stop first (before editing/rebuilding rccar_drivers)"; exit 1; fi

# Physical-Mapper acceptance (launch_testing, rccar_drivers/test_hw; criteria rccar_drivers/hw_criteria.py).
# Runs its own driver instance, so the compose service must be stopped. Never starts anything afterwards.
lidar-hw-test: _need-config _need-drivers-down  ## automated launch_testing against the PHYSICAL Mapper (read-only; car stationary); JSON report in logs/
	@echo "lidar-hw-test: car stationary, ESC power OFF. Read-only (getters only). Report: logs/hw_test_lidar_<UTC>.json"
	@rc=0; $(COMPOSE) run --rm -e MAPPER_HOST=$${MAPPER_HOST:-192.168.11.1} -e RCCAR_GIT_SHA=$(shell git rev-parse --short HEAD 2>/dev/null) \
	  -e RCCAR_HW_TEST=1 tools launch_test /ws/install/share/rccar_drivers/test_hw/test_mapper_hw.py || rc=$$?; \
	  echo "drivers left stopped; restarting it is a hardware restart: ask the user (make drivers-start)"; exit $$rc

# ---- power board (KiCad 10 in docker, docs/schematics; no hardware) ------------------------
kicad-image:     ## build the KiCad 10 image (docker/kicad.Dockerfile -> rccar-kicad:local)
	docker build -f docker/kicad.Dockerfile -t $(KICAD_IMAGE) .

_kicad-cfg:
	@test -f $(KICAD_CFG)/kicad/10.0/sym-lib-table || { mkdir -p $(KICAD_CFG)/kicad/10.0 && \
	  docker run --rm --user $(shell id -u):$(shell id -g) -v "$(KICAD_CFG)":/cfg $(KICAD_IMAGE) \
	  sh -c 'cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table /cfg/kicad/10.0/'; }

erc: _kicad-cfg  ## KiCad ERC on the power board schematic (0 errors required; warnings are printed)
	@mkdir -p "$(CURDIR)/build/erc"
	$(KICAD_RUN) kicad-cli sch erc --format json --severity-all \
	  -o "$(CURDIR)/build/erc/erc.json" rc_power_board.kicad_sch > "$(CURDIR)/build/erc/erc.txt"; rc=$$?; cat "$(CURDIR)/build/erc/erc.txt"; \
	  $(KICAD_RUN) python3 tools/erc_summary.py "$(CURDIR)/build/erc/erc.json"; s=$$?; \
	  if [ $$s -ne 0 ]; then echo "erc: FAIL"; exit 1; fi; echo "erc: PASS (0 errors)"

pcb-test: _kicad-cfg  ## unit tests for the PCB tools (stdlib unittest, image python3)
	$(KICAD_RUN) python3 -m unittest discover -s tools -p 'test_*.py' -v

# ---- ROS tools (need: make car-up) ----------------------------------------------------------
teleop: _need-stack  ## SSH keyboard driving via the supervisor (arrows, space=brake, d=disarm, a=arm, q/x=quit)
	$(COMPOSE) run --rm tools ros2 run rccar_teleop keyboard

calibrate: _need-stack  ## interactive servo center/left/right calibration, writes tuning.toml
	$(COMPOSE) run --rm tools ros2 run rccar_calibration calibrate

tune: _need-stack  ## push tuning.toml to the ESP32 and save it to flash
	$(COMPOSE) run --rm tools ros2 run rccar_calibration tune

test: _need-stack  ## steering sweep + failsafe check (motor stays off, never arms)
	$(COMPOSE) run --rm tools ros2 run rccar_calibration bench_test

rangefinder: _need-stack  ## live rangefinder feed: MCU timestamp, Pi time, range (Ctrl+C to exit)
	$(COMPOSE) run --rm tools ros2 run rccar_calibration rangefinder_monitor

viz: _need-stack  ## live websocket feed for Foxglove/Lichtblick on localhost:8765 (VS Code forwards it; Ctrl+C to exit)
	@echo "viz: open ws://localhost:8765 in Foxglove or Lichtblick (VS Code Remote-SSH forwards port 8765)"
	$(COMPOSE) run --rm tools ros2 launch rccar_bringup viz.launch.py

lidar-imu: _need-stack  ## live Mapper IMU feed (heading, yaw rate, horizontal accel, speed) + logs/lidar_imu_*.jsonl (Ctrl+C to exit)
	$(COMPOSE) run --rm tools ros2 run rccar_calibration lidar_imu_monitor

lidar-snapshot: _need-stack  ## one lidar capture -> logs/lidar_snapshot_<UTC>/ (map.png + scan, pose, summary; read-only)
	$(COMPOSE) run --rm tools ros2 run rccar_calibration lidar_snapshot

SECS ?= 30
lidar-record: _need-stack  ## record the lidar topics for SECS (default 30) -> logs/lidar_bag_<UTC>/ (mcap; read-only)
	@case '$(SECS)' in ''|*[!0-9]*) echo "SECS must be a whole number of seconds (1..600), got '$(SECS)'"; exit 1;; esac
	$(COMPOSE) run --rm tools ros2 run rccar_calibration lidar_record --secs $(SECS)

mcu: _need-stack  ## one McuCommand to the ESP32, e.g. make mcu CMD="GET" (stack up; CMD: GET INFO PING SET ...; ARM refused)
	@test -n "$(CMD)" || { echo 'usage: make mcu CMD="GET"'; exit 1; }
	@case "$(CMD)" in *\'*|*\"*) echo "CMD must not contain quotes"; exit 1;; \
	  [Aa][Rr][Mm]*) echo "ARM is refused here: arm through the supervisor (make teleop, key a)"; exit 1;; esac
	$(COMPOSE) run --rm tools timeout 10 ros2 service call /rccar/mcu/command rccar_msgs/srv/McuCommand "{command: '$(CMD)'}"

# ---- firmware (docker) ----------------------------------------------------------------------
fw-image:        ## build the firmware toolchain docker image (rccar-fw)
	docker build -f docker/firmware.Dockerfile -t $(FW_IMAGE) .

clean:           ## delete firmware/esp32/.pio completely (incl. the slow micro-ROS libdeps cache)
	rm -rf $(FW_DIR)/.pio

_clean-build:
	rm -rf $(FW_DIR)/.pio/build

build: _clean-build  ## clean .pio/build (keeps libdeps) + compile firmware (docker, FW_ENV=esp32s3)
	$(FW_RUN) $(FW_IMAGE) pio run -e $(FW_ENV)

flash: _need-stack-down _clean-build  ## compile + upload FW_ENV over the COM port (docker; ESC off, stack down)
	@test -e "$(PORT)" || { echo "$(PORT) not found: plug the COM port in (make install-host for the udev symlink) or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) --device $(PORT) $(FW_IMAGE) pio run -e $(FW_ENV) -t upload --upload-port $(PORT)

monitor: _need-stack-down  ## raw serial monitor (Ctrl+C to exit, docker)
	@test -e "$(PORT)" || { echo "$(PORT) not found: plug the COM port in (make install-host for the udev symlink) or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) -it --device $(PORT) $(FW_IMAGE) pio device monitor --port $(PORT)

compiledb:       ## firmware compile_commands.json for clangd, env FW_ENV (docker, host paths)
	@test -d .pio-core || { mkdir -p .pio-core && docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)/.pio-core":/seed $(FW_IMAGE) \
	  sh -c 'cp -a /opt/platformio/. /seed/'; }
	docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)":"$(CURDIR)" -w "$(CURDIR)/$(FW_DIR)" \
	  -e PLATFORMIO_CORE_DIR="$(CURDIR)/.pio-core" $(FW_IMAGE) pio run -e $(FW_ENV) -t compiledb

# ---- dev ------------------------------------------------------------------------------------
unit-run:        ## run deploy/tests (pytest) in an already built ROS test image, repo mounted read-only
	docker run --rm --user $(shell id -u):$(shell id -g) -e PYTHONDONTWRITEBYTECODE=1 \
	  -v "$(CURDIR)":/repo:ro -w /repo $(ROS_TEST_IMAGE) python3 -m pytest -q -p no:cacheprovider deploy/tests

unit: ros-test-image unit-run  ## deploy/tests (pytest) in the ROS test image, no hardware

check-dev:       ## check optional Claude Code dev tools (LSP binaries) on PATH
	@for c in pyright-langserver clangd; do command -v $$c >/dev/null && echo "OK   $$c" || echo "MISSING $$c (see docs/setup.md, Claude Code)"; done
