# RC car ESP32-S3 bring-up. Run `make help`. Setup steps: docs/setup.md
# Firmware targets (build/flash/monitor/clean) run in docker (docker/firmware.Dockerfile).
# Host-python targets (check/detect/ping/tune/test/...) use .venv until the ROS phase.
# USB cable goes in the board's right-hand USB-C port, labelled "COM".
# Linux/macOS. On Windows use Git Bash and set VENV_BIN=.venv/Scripts.
PYTHON   ?= python3
VENV     := .venv
VENV_BIN ?= $(VENV)/bin
PY       := $(VENV_BIN)/python
FW_DIR   := firmware/esp32
FW_IMAGE ?= rccar-fw
FW_VOL   ?= rccar-platformio
DIALOUT_GID := $(shell getent group dialout 2>/dev/null | cut -d: -f3)
FW_RUN   := docker run --rm --user $(shell id -u):$(shell id -g) \
            $(if $(DIALOUT_GID),--group-add $(DIALOUT_GID),) \
            -v "$(CURDIR)":/work -v "$(FW_VOL)":/opt/platformio -w /work/$(FW_DIR)
CLI      := $(PY) tools/rccar.py
ifeq ($(origin PORT),undefined)       # auto-detect once per make run
PORT     := $(shell $(CLI) find-port 2>/dev/null)
endif
PORT_ARG := $(if $(PORT),--port $(PORT),)

.DEFAULT_GOAL := help
.PHONY: help setup check detect ping sync-time tune clean build flash monitor \
        fw-image config models compiledb unit check-dev test test-throttle calibrate \
        teleop session

help:            ## list targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

$(PY):
	$(PYTHON) -m venv $(VENV)

setup: $(PY)     ## check host prereqs, create .venv + install deps, build firmware image
	@for c in git make docker; do command -v $$c >/dev/null || { echo "MISSING host prerequisite: $$c"; exit 1; }; done
	@docker compose version >/dev/null 2>&1 || echo "WARN: docker compose plugin missing (needed from the ROS phase)"
	@docker buildx version >/dev/null 2>&1 || echo "WARN: docker buildx missing (needed for multi-arch images)"
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt
	$(MAKE) fw-image

fw-image:        ## build the firmware toolchain docker image (rccar-fw)
	docker build -f docker/firmware.Dockerfile -t $(FW_IMAGE) .

config:          ## check .env exists (rendering deploy config arrives in phase 2)
	@test -f .env || { echo ".env missing: cp .env.example .env, then fill it in"; exit 1; }
	@echo ".env found. Rendering deploy/car/.env.generated from tuning.toml + .env arrives in phase 2."

models:          ## validate models/manifest.yaml (download not implemented; needs tailnet)
	@$(PY) -c "import sys,yaml; m=yaml.safe_load(open('models/manifest.yaml')); print('models/manifest.yaml:', len(m['models']), 'model(s)'); [print(' ', x['name'], x['version'], x['file'], x['sha256'][:12]) for x in m['models']]" 2>/dev/null \
	  || cat models/manifest.yaml
	@echo "download + sha256 verify into models/cache/ not implemented yet (requires Tailscale tailnet, see models/README.md)"

check: $(PY)     ## verify python packages, pio, serial permissions
	$(CLI) check-env

detect: $(PY)    ## find the ESP32 on USB, read chip id, query firmware
	$(CLI) $(PORT_ARG) detect

ping: $(PY)      ## check the firmware answers + USB round-trip time
	$(CLI) $(PORT_ARG) ping

sync-time: $(PY) ## set the ESP32 clock from this laptop
	$(CLI) $(PORT_ARG) sync-time

tune: $(PY)      ## push tuning.toml to the ESP32 and save it to flash
	$(CLI) $(PORT_ARG) tune

clean:           ## delete firmware/esp32/.pio build cache
	rm -rf $(FW_DIR)/.pio

build: clean     ## clean + compile firmware (docker)
	$(FW_RUN) $(FW_IMAGE) pio run

flash: clean     ## clean + compile + upload over the COM port (docker)
	@test -n "$(PORT)" || { echo "no serial port found: plug the COM port in or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) --device $(PORT) $(FW_IMAGE) pio run -t upload --upload-port $(PORT)

monitor:         ## raw serial monitor (Ctrl+C to exit, docker)
	@test -n "$(PORT)" || { echo "no serial port found: plug the COM port in or pass PORT=/dev/ttyUSB0"; exit 1; }
	$(FW_RUN) -it --device $(PORT) $(FW_IMAGE) pio device monitor --port $(PORT)

compiledb:       ## firmware compile_commands.json for clangd (docker, host paths)
	@test -d .pio-core || { mkdir -p .pio-core && docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)/.pio-core":/seed $(FW_IMAGE) \
	  sh -c 'cp -a /opt/platformio/. /seed/'; }
	docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)":"$(CURDIR)" -w "$(CURDIR)/$(FW_DIR)" \
	  -e PLATFORMIO_CORE_DIR="$(CURDIR)/.pio-core" $(FW_IMAGE) pio run -t compiledb

unit: $(PY)      ## host-python unit tests, no hardware (pytest tools/tests)
	$(PY) -m pytest -q tools/tests

check-dev:       ## check optional Claude Code dev tools (LSP binaries) on PATH
	@for c in pyright-langserver clangd; do command -v $$c >/dev/null && echo "OK   $$c" || echo "MISSING $$c (see docs/setup.md, Claude Code)"; done

test: $(PY)      ## steering sweep + failsafe check (motor stays off)
	$(CLI) $(PORT_ARG) test

test-throttle: $(PY) ## test + short motor run, WHEELS OFF THE GROUND
	$(CLI) $(PORT_ARG) test --throttle

calibrate: $(PY) ## interactive servo center/left/right calibration
	$(CLI) $(PORT_ARG) calibrate

teleop: $(PY)    ## keyboard driving: arrows = heading/speed
	$(CLI) $(PORT_ARG) teleop

session: $(PY)   ## interactive tuning/test session (tools/esp32_session.py)
	$(PY) tools/esp32_session.py $(PORT_ARG)
