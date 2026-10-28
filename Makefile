# RC car platform. Run `make help`. Setup steps: docs/setup.md
# Car stack (ROS 2 + micro-ROS in docker, deploy/car/compose.yaml): config, ros-image, car-*, teleop, calibrate, tune, test.
# Firmware targets (build/flash/monitor/clean) run in docker (docker/firmware.Dockerfile); FW_ENV picks the env.
# legacy-* targets: ASCII fallback (firmware env esp32s3_ascii + tools/ in .venv); removed after the bench parity test.
# USB cable goes in the board's right-hand USB-C port, labelled "COM".
# Linux/macOS. On Windows use Git Bash and set VENV_BIN=.venv/Scripts.
PYTHON   ?= python3
VENV     := .venv
VENV_BIN ?= $(VENV)/bin
PY       := $(VENV_BIN)/python
FW_DIR   := firmware/esp32
FW_ENV   ?= esp32s3
FW_IMAGE ?= rccar-fw
FW_VOL   ?= rccar-platformio
DIALOUT_GID := $(shell getent group dialout 2>/dev/null | cut -d: -f3)
FW_RUN   := docker run --rm --user $(shell id -u):$(shell id -g) \
            $(if $(DIALOUT_GID),--group-add $(DIALOUT_GID),) \
            -v "$(CURDIR)":/work -v "$(FW_VOL)":/opt/platformio -w /work/$(FW_DIR)
CLI      := $(PY) tools/rccar.py
# serial port: udev symlink (make install-host) when present, else auto-detect via the legacy CLI
ifeq ($(origin PORT),undefined)
PORT     := $(shell if [ -e /dev/rccar-esp32 ]; then echo /dev/rccar-esp32; else $(CLI) find-port 2>/dev/null; fi)
endif
PORT_ARG := $(if $(PORT),--port $(PORT),)
# ROS stack
ROS_IMAGE      ?= rccar-ros:local
ROS_TEST_IMAGE ?= rccar-ros-test:local
ROS_TEST_OUT   ?= build/ros-test
ROS_BUILD_ARGS ?=
COMPOSE  := docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated

.DEFAULT_GOAL := help
.PHONY: help setup check clean build flash monitor fw-image config models compiledb unit check-dev \
        ros-image ros-test ros-test-image ros-test-run ros-shell car-up car-down car-ps car-logs car-pull \
        car-shutdown install-host teleop calibrate tune test \
        legacy-detect legacy-ping legacy-sync-time legacy-tune legacy-test legacy-test-throttle \
        legacy-calibrate legacy-teleop legacy-session \
        _clean-build _need-config _need-stack _need-stack-down

help:            ## list targets (grouped in README.md; legacy-* replace the old detect/ping/... names)
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-21s %s\n", $$1, $$2}'

$(PY):
	$(PYTHON) -m venv $(VENV)

# ---- setup / config -------------------------------------------------------------------------
setup: $(PY)     ## check host prereqs, create .venv (unit tests + legacy tools), build the firmware image
	@for c in git make docker; do command -v $$c >/dev/null || { echo "MISSING host prerequisite: $$c"; exit 1; }; done
	@docker compose version >/dev/null 2>&1 || echo "WARN: docker compose plugin missing (needed for make car-up)"
	@docker buildx version >/dev/null 2>&1 || echo "WARN: docker buildx missing (needed for multi-arch images)"
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt
	$(MAKE) fw-image

config:          ## render deploy/car/.env.generated from .env + tuning.toml [platform.$PLATFORM]
	$(PYTHON) deploy/render_env.py

models:          ## validate models/manifest.yaml (download not implemented; needs tailnet)
	@$(PY) -c "import sys,yaml; m=yaml.safe_load(open('models/manifest.yaml')); print('models/manifest.yaml:', len(m['models']), 'model(s)'); [print(' ', x['name'], x['version'], x['file'], x['sha256'][:12]) for x in m['models']]" 2>/dev/null \
	  || cat models/manifest.yaml
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
ros-image:       ## build the ROS 2 image (docker/ros.Dockerfile -> rccar-ros:local)
	docker build -f docker/ros.Dockerfile $(ROS_BUILD_ARGS) -t $(ROS_IMAGE) .

ros-test-image:  ## build the ROS test image (target test: colcon build, all test deps)
	docker build -f docker/ros.Dockerfile --target test $(ROS_BUILD_ARGS) -t $(ROS_TEST_IMAGE) .

ros-test-run:    ## run colcon test in an already built test image; results in build/ros-test
	mkdir -p $(ROS_TEST_OUT)
	docker run --rm -e HOST_UID=$(shell id -u) -e HOST_GID=$(shell id -g) -v "$(CURDIR)/$(ROS_TEST_OUT)":/out $(ROS_TEST_IMAGE)

ros-test: ros-test-image ros-test-run  ## build the test image + colcon test + test-result (no hardware)

car-up: config   ## render config, start mcu-agent + core (docker compose up -d)
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

# serial-port users (flash, monitor, legacy-*) must not collide with the micro-ROS agent
_need-stack-down:
	@if $(COMPOSE) ps --status running -q 2>/dev/null | grep -q .; then \
	  echo "car stack is running and holds the serial port: make car-down first"; exit 1; fi

# ---- ROS tools (need: make car-up) ----------------------------------------------------------
teleop: _need-stack  ## SSH keyboard driving via the supervisor (arrows, space=brake, d=disarm, a=arm, q/x=quit)
	$(COMPOSE) run --rm tools ros2 run rccar_teleop keyboard

calibrate: _need-stack  ## interactive servo center/left/right calibration, writes tuning.toml
	$(COMPOSE) run --rm tools ros2 run rccar_calibration calibrate

tune: _need-stack  ## push tuning.toml to the ESP32 and save it to flash
	$(COMPOSE) run --rm tools ros2 run rccar_calibration tune

test: _need-stack  ## steering sweep + failsafe check (motor stays off, never arms)
	$(COMPOSE) run --rm tools ros2 run rccar_calibration bench_test

# ---- firmware (docker) ----------------------------------------------------------------------
fw-image:        ## build the firmware toolchain docker image (rccar-fw)
	docker build -f docker/firmware.Dockerfile -t $(FW_IMAGE) .

check: $(PY)     ## verify python packages, pio, serial permissions
	$(CLI) check-env

clean:           ## delete firmware/esp32/.pio completely (incl. the slow micro-ROS libdeps cache)
	rm -rf $(FW_DIR)/.pio

_clean-build:
	rm -rf $(FW_DIR)/.pio/build

build: _clean-build  ## clean .pio/build (keeps libdeps) + compile firmware env FW_ENV=esp32s3|esp32s3_ascii (docker)
	$(FW_RUN) $(FW_IMAGE) pio run -e $(FW_ENV)

flash: _need-stack-down _clean-build  ## compile + upload FW_ENV over the COM port (docker; ESC off, stack down)
	@test -n "$(PORT)" || { echo "no serial port found: plug the COM port in or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) --device $(PORT) $(FW_IMAGE) pio run -e $(FW_ENV) -t upload --upload-port $(PORT)

monitor: _need-stack-down  ## raw serial monitor (Ctrl+C to exit, docker)
	@test -n "$(PORT)" || { echo "no serial port found: plug the COM port in or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) -it --device $(PORT) $(FW_IMAGE) pio device monitor --port $(PORT)

compiledb:       ## firmware compile_commands.json for clangd, env FW_ENV (docker, host paths)
	@test -d .pio-core || { mkdir -p .pio-core && docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)/.pio-core":/seed $(FW_IMAGE) \
	  sh -c 'cp -a /opt/platformio/. /seed/'; }
	docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)":"$(CURDIR)" -w "$(CURDIR)/$(FW_DIR)" \
	  -e PLATFORMIO_CORE_DIR="$(CURDIR)/.pio-core" $(FW_IMAGE) pio run -e $(FW_ENV) -t compiledb

# ---- dev ------------------------------------------------------------------------------------
unit: $(PY)      ## host-python unit tests, no hardware (pytest tools/tests deploy/tests)
	$(PY) -m pytest -q tools/tests deploy/tests

check-dev:       ## check optional Claude Code dev tools (LSP binaries) on PATH
	@for c in pyright-langserver clangd; do command -v $$c >/dev/null && echo "OK   $$c" || echo "MISSING $$c (see docs/setup.md, Claude Code)"; done

# ---- legacy ASCII path (flash FW_ENV=esp32s3_ascii first; stack must be down) ---------------
legacy-detect: $(PY) _need-stack-down  ## legacy: find the ESP32 on USB, read chip id, query firmware (was detect)
	$(CLI) $(PORT_ARG) detect

legacy-ping: $(PY) _need-stack-down  ## legacy: check the firmware answers + USB round-trip time (was ping)
	$(CLI) $(PORT_ARG) ping

legacy-sync-time: $(PY) _need-stack-down  ## legacy: set the ESP32 clock from this laptop (was sync-time)
	$(CLI) $(PORT_ARG) sync-time

legacy-tune: $(PY) _need-stack-down  ## legacy: push tuning.toml to the ESP32 and save it to flash (was tune)
	$(CLI) $(PORT_ARG) tune

legacy-test: $(PY) _need-stack-down  ## legacy: steering sweep + failsafe check, motor off (was test)
	$(CLI) $(PORT_ARG) test

legacy-test-throttle: $(PY) _need-stack-down  ## legacy: test + short motor run, WHEELS OFF THE GROUND (was test-throttle)
	$(CLI) $(PORT_ARG) test --throttle

legacy-calibrate: $(PY) _need-stack-down  ## legacy: interactive servo center/left/right calibration (was calibrate)
	$(CLI) $(PORT_ARG) calibrate

legacy-teleop: $(PY) _need-stack-down  ## legacy: keyboard driving, arrows = heading/speed (was teleop)
	$(CLI) $(PORT_ARG) teleop

legacy-session: $(PY) _need-stack-down  ## legacy: interactive tuning/test session, tools/esp32_session.py (was session)
	$(PY) tools/esp32_session.py $(PORT_ARG)
