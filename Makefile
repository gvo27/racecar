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
# KiCad 10 + Freerouting for the power board (pcb/); images pinned by digest
KICAD_IMAGE      ?= rccar-kicad:local
FREEROUTING_IMAGE := ghcr.io/freerouting/freerouting:2.5.0@sha256:6c195891c9b1d62620c140784ab91285b9350d12d905693defe0162eb128cf8e
# pcb/<BOARD>/ = one KiCad project (default: the rev1 release). Shared Python libraries: pcb/libraries. Mill tools: tools/ of the lab directory (lab: in .claude/CLAUDE.md)
# base board = DEFAULT_BOARD in pcb/libraries/paths.py (test_rules checks that they agree)
BASE_BOARD       := releases/rev1
BOARD            ?= $(BASE_BOARD)
BOARD_DIR        := pcb/$(BOARD)
PCB_LIBS         := $(CURDIR)/pcb/libraries
PCB_DOCS         := docs/pcb
LAB_DIR          := $(patsubst %/,%,$(shell sed -n "s/^lab:[[:space:]]*\\([^[:space:]]*\\).*/\\1/p" .claude/CLAUDE.md))
LAB_TOOLS        := $(CURDIR)/$(LAB_DIR)/tools
# review files: docs/pcb/releases/<rev>/review (paths.review_dir). The active board pcb/src reviews into its next release.
SRC_RELEASE      := rev3   # copy of paths.WORKING_RELEASE["src"] (test_rules checks it)
REVIEW_DIR       := $(PCB_DOCS)/releases/$(if $(filter src,$(BOARD)),$(strip $(SRC_RELEASE)),$(notdir $(BOARD)))/review
# global lib tables: kicad-cli in a bare container finds no stock libraries (false ERC warnings), so copy the templates
KICAD_CFG        := $(CURDIR)/build/kicad-cfg
KICAD_RUN        = docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -e XDG_CONFIG_HOME=$(KICAD_CFG) \
                   -e BOARD_DIR="$(CURDIR)/$(BOARD_DIR)" -v "$(CURDIR)":"$(CURDIR)" -w "$(CURDIR)/$(BOARD_DIR)" $(KICAD_IMAGE)
# Session targets (make open / make close, template: skill setup-shop). Host tools outside the uv .venv.
REQUIRED    := git make uv direnv docker
RECOMMENDED := gh
PYTHON_MIN  := 3.12
# Other git repos that open and close also sync and check (fast-forward only).
EXTRA_REPOS :=
COMPOSE  := docker compose -f deploy/car/compose.yaml --env-file deploy/car/.env.generated

.DEFAULT_GOAL := help
.PHONY: help open close context plugins-reset check-host setup clean build pcb-rules pcb-sch pcb-all flash monitor fw-image config models compiledb unit check-dev dev-setup \
        ros-image ros-test ros-test-image ros-test-run ros-shell car-up car-down car-ps car-logs car-pull \
        car-shutdown install-host teleop calibrate tune test rangefinder viz lidar-imu lidar-snapshot lidar-record mcu unit-run \
        drivers-stop drivers-start lidar-hw-test kicad-image erc pcb-build pcb-route pcb-check pcb-mill-check pcb-review pcb-fab pcb-test pcb-gate bom \
        _kicad-cfg _clean-build _need-config _need-stack _need-stack-down _need-drivers-down

help:            ## list targets (grouped in README.md)
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-21s %s\n", $$1, $$2}'

# ---- Claude Code session (not the car setup: that is make setup) -----------------------------
open: check-host  ## start a Claude Code session: git fast-forward, uv sync + direnv allow, missing plugins, checklist; safe to rerun
	uv run --no-project python scripts/open.py . $(EXTRA_REPOS)

close: plugins-reset  ## end a Claude Code session: clean caches, report uncommitted/unpushed work and done plans; safe to rerun
	uv run --no-project python scripts/close.py . $(EXTRA_REPOS)

# check script of the user skill project-context (not in the repo; WARN when missing)
CONTEXT_CHECK ?= $(HOME)/.claude/skills/project-context/scripts/context_check.py
context:         ## report context drift: dead pointers, orphan docs, size budgets (user skill project-context); changes nothing
	@if [ -f "$(CONTEXT_CHECK)" ]; then uv run --no-project python "$(CONTEXT_CHECK)" --exclude docs/archive .; \
	else echo "WARN    $(CONTEXT_CHECK) not found: install the user skill project-context"; fi

plugins-reset:   ## remove the session-only plugin enables (local scope) from .claude/settings.local.json; safe to rerun
	@uv run --no-project python scripts/plugins_reset.py

check-host:      ## check the host tools outside .venv (git, make, uv, direnv, docker); fails if a required one is missing
	@fail=0; \
	for c in $(REQUIRED); do \
	  if command -v $$c >/dev/null; then echo "OK      $$c"; \
	  elif [ $$c = uv ] && [ -x "$$HOME/.local/bin/uv" ]; then echo "MISSING uv on PATH: add ~/.local/bin to PATH"; fail=1; \
	  else echo "MISSING $$c"; fail=1; fi; \
	done; \
	for c in $(RECOMMENDED); do \
	  command -v $$c >/dev/null && echo "OK      $$c" || echo "WARN    $$c not found (recommended)"; \
	done; \
	if command -v uv >/dev/null; then \
	  if p=$$(uv python find --system --no-project '>=$(PYTHON_MIN)' 2>/dev/null); then echo "OK      python>=$(PYTHON_MIN) ($$p)"; \
	  else echo "MISSING system python>=$(PYTHON_MIN)"; fail=1; fi; \
	fi; \
	case " $(REQUIRED) " in *" docker "*) \
	  if command -v docker >/dev/null && ! docker info >/dev/null 2>&1; then \
	    echo "MISSING docker daemon access: start docker, or add your user to the docker group"; fail=1; fi;; \
	esac; \
	if command -v direnv >/dev/null && ! grep -qs 'direnv hook' ~/.bashrc ~/.zshrc ~/.config/fish/config.fish; then \
	  echo "WARN    direnv hook not in shell rc: .venv will not load in your shell"; fi; \
	if command -v gh >/dev/null && ! gh auth status >/dev/null 2>&1; then echo "WARN    gh not logged in: run gh auth login"; fi; \
	exit $$fail

# ---- setup / config -------------------------------------------------------------------------
setup:           ## check host prereqs (git, make, docker + compose/buildx, uv), dev tools into .venv (dev-setup), build the firmware and ROS images; safe to rerun
	@for c in git make docker uv; do command -v $$c >/dev/null || { echo "MISSING host prerequisite: $$c (docs/setup.md)"; exit 1; }; done
	@docker compose version >/dev/null 2>&1 || echo "WARN: docker compose plugin missing (needed for make car-up)"
	@docker buildx version >/dev/null 2>&1 || echo "WARN: docker buildx missing (needed for multi-arch images)"
	$(MAKE) dev-setup
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

# Physical-Mapper acceptance (launch_testing, ros2_ws/src/rccar_drivers/test_hw; criteria ros2_ws/src/rccar_drivers/rccar_drivers/hw_criteria.py).
# Runs its own driver instance, so the compose service must be stopped. Never starts anything afterwards.
lidar-hw-test: _need-config _need-drivers-down  ## automated launch_testing against the PHYSICAL Mapper (read-only; car stationary); JSON report in logs/
	@echo "lidar-hw-test: car stationary, ESC power OFF. Read-only (getters only). Report: logs/hw_test_lidar_<UTC>.json"
	@rc=0; $(COMPOSE) run --rm -e MAPPER_HOST=$${MAPPER_HOST:-192.168.11.1} -e RCCAR_GIT_SHA=$(shell git rev-parse --short HEAD 2>/dev/null) \
	  -e RCCAR_HW_TEST=1 tools launch_test /ws/install/share/rccar_drivers/test_hw/test_mapper_hw.py || rc=$$?; \
	  echo "drivers left stopped; restarting it is a hardware restart: ask the user (make drivers-start)"; exit $$rc

# ---- power board (KiCad 10 in docker, pcb/<BOARD>, default releases/rev1; no hardware) ------------------------
kicad-image:     ## build the KiCad 10 image (docker/kicad.Dockerfile -> rccar-kicad:local)
	docker build -f docker/kicad.Dockerfile -t $(KICAD_IMAGE) .

_kicad-cfg:
	@test -f $(KICAD_CFG)/kicad/10.0/sym-lib-table || { mkdir -p $(KICAD_CFG)/kicad/10.0 && \
	  docker run --rm --user $(shell id -u):$(shell id -g) -v "$(KICAD_CFG)":/cfg $(KICAD_IMAGE) \
	  sh -c 'cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table /cfg/kicad/10.0/'; }

pcb-rules: _kicad-cfg  ## check the KiCad project files of BOARD against its design rules (design_rules.toml); PCB_RULES_ARGS=--write changes them
	$(KICAD_RUN) python3 $(PCB_LIBS)/gen_rules.py $(PCB_RULES_ARGS)

pcb-sch: _kicad-cfg  ## make the schematic of a board variant (BOARD=src) from the base schematic (BASE_BOARD) and its [parts] exclude list
	$(KICAD_RUN) python3 $(PCB_LIBS)/variant.py

# One command after a change of the design rules. The part positions stay (placement.py of the board is the source).
pcb-all:         ## BOARD=src: schematic variant, rules into the project, build from placement.py, route, checks, fab outputs, review files
	$(MAKE) pcb-sch BOARD=$(BOARD)
	$(MAKE) pcb-rules BOARD=$(BOARD) PCB_RULES_ARGS=--write
	$(MAKE) pcb-build BOARD=$(BOARD) PCB_BUILD_ARGS=--force
	$(MAKE) pcb-route BOARD=$(BOARD)
	$(MAKE) pcb-fab BOARD=$(BOARD)
	$(MAKE) pcb-review BOARD=$(BOARD)
	$(MAKE) pcb-check BOARD=$(BOARD)

erc: _kicad-cfg  ## KiCad ERC on the power board schematic (0 errors required; warnings are printed)
	@mkdir -p "$(CURDIR)/build/erc"
	$(KICAD_RUN) kicad-cli sch erc --format json --severity-all \
	  -o "$(CURDIR)/build/erc/erc.json" rc_power_board.kicad_sch > "$(CURDIR)/build/erc/erc.txt"; rc=$$?; cat "$(CURDIR)/build/erc/erc.txt"; \
	  $(KICAD_RUN) python3 $(PCB_LIBS)/erc_summary.py "$(CURDIR)/build/erc/erc.json"; s=$$?; \
	  if [ $$s -ne 0 ]; then echo "erc: FAIL"; exit 1; fi; echo "erc: PASS (0 errors)"

pcb-build: _kicad-cfg  ## bootstrap pcb/<BOARD>/rc_power_board.kicad_pcb from the schematic (first build; refuses to overwrite, --force destroys manual edits)
	$(KICAD_RUN) python3 $(PCB_LIBS)/build_pcb.py $(PCB_BUILD_ARGS)

# Freerouting runs in its own image; pcbnew (DSN export, SES import) runs in the KiCad image
pcb-route: _kicad-cfg  ## route the board from scratch (Freerouting 2.5.0): B.Cu, planned F.Cu jumpers on rivets (placement.py), stitching via for the F.Cu pour
	@mkdir -p "$(CURDIR)/build/route/user" && rm -f "$(CURDIR)/build/route/in.dsn" "$(CURDIR)/build/route/out.ses"
	$(KICAD_RUN) python3 $(PCB_LIBS)/route_pcb.py dsn rc_power_board.kicad_pcb --dsn "$(CURDIR)/build/route/in.dsn"
	docker run --rm --user $(shell id -u):$(shell id -g) -v "$(CURDIR)/build/route":/data --entrypoint java $(FREEROUTING_IMAGE) \
	  -jar /app/freerouting-executable.jar --gui-enabled=false --api_server-enabled=false --user_data_path=/data/user \
	  -de /data/in.dsn -do /data/out.ses -mp 40 -mt 1 > "$(CURDIR)/build/route/freerouting.log" 2>&1; tail -n 3 "$(CURDIR)/build/route/freerouting.log"
	$(KICAD_RUN) python3 $(PCB_LIBS)/route_pcb.py ses rc_power_board.kicad_pcb --ses "$(CURDIR)/build/route/out.ses"

pcb-check: _kicad-cfg  ## DRC (with schematic parity) + board checks + milling check; fails on DRC errors, unconnected items, check_board problems
	@mkdir -p "$(CURDIR)/build/drc"
	$(KICAD_RUN) kicad-cli pcb drc --schematic-parity --severity-all --all-track-errors --format json \
	  -o "$(CURDIR)/build/drc/drc.json" rc_power_board.kicad_pcb > /dev/null
	$(KICAD_RUN) python3 $(PCB_LIBS)/drc_summary.py "$(CURDIR)/build/drc/drc.json"
	$(KICAD_RUN) python3 $(PCB_LIBS)/check_board.py rc_power_board.kicad_pcb

pcb-review: _kicad-cfg  ## write the review directory of BOARD (docs/pcb/releases/<rev>/review; BOARD=src: rev3): drc.json, milling_check.json, layer PDF, 1:1 PDF
	$(KICAD_RUN) python3 $(PCB_LIBS)/review_plots.py

pcb-mill-check: _kicad-cfg  ## milling check of the board vs the lab limits (milling.toml in the lab directory, waivers); exit 1 = unwaived errors
	@mkdir -p "$(CURDIR)/$(REVIEW_DIR)"
	$(KICAD_RUN) python3 $(LAB_TOOLS)/milling_check.py rc_power_board.kicad_pcb \
	  --waivers "$(CURDIR)/$(LAB_DIR)/milling_waivers.toml" --json "$(CURDIR)/$(REVIEW_DIR)/milling_check.json"

pcb-fab: _kicad-cfg  ## DXF (F.Cu, B.Cu, Edge.Cuts), Excellon and drill-map DXF for the lab's Fusion 360 template -> build/fab/<BOARD>/ (not committed), then test_fab
	$(KICAD_RUN) python3 $(LAB_TOOLS)/fab_export.py rc_power_board.kicad_pcb --out "$(CURDIR)/build/fab/$(BOARD)"
	$(KICAD_RUN) python3 -m unittest discover -s $(LAB_TOOLS) -p 'test_fab.py' -v

# kicad-happy plugin directory (the installed version, ref in .claude/settings.json); override with KICAD_HAPPY=<dir>
KICAD_HAPPY      ?= $(lastword $(sort $(wildcard $(HOME)/.claude/plugins/cache/kicad-happy/kicad-happy/*)))
# fab = fab house (Gerbers checked), mill = the lab mill (no Gerbers). The active board pcb/src is made on the mill.
METHOD           ?= $(if $(filter src,$(BOARD)),mill,fab)
pcb-gate: _kicad-cfg  ## kicad-happy analyzers + fab release gate of BOARD -> build/gate/<BOARD>/ (METHOD=fab|mill; needs the kicad-happy plugin)
	@test -n "$(KICAD_HAPPY)" -a -d "$(KICAD_HAPPY)/skills/kicad/scripts" || { echo "pcb-gate: kicad-happy plugin not found. Run: claude plugin install kicad-happy@kicad-happy --scope project, or set KICAD_HAPPY=<dir>"; exit 1; }
	docker run --rm --user $(shell id -u):$(shell id -g) -e HOME=/tmp -e XDG_CONFIG_HOME=$(KICAD_CFG) \
	  -v "$(CURDIR)":"$(CURDIR)" -v "$(KICAD_HAPPY)":"$(KICAD_HAPPY)":ro -w "$(CURDIR)/$(BOARD_DIR)" $(KICAD_IMAGE) \
	  sh $(PCB_LIBS)/pcb_gate.sh "$(KICAD_HAPPY)" "$(CURDIR)/build/gate/$(BOARD)" "$(METHOD)"

pcb-test: _kicad-cfg  ## unit tests for the PCB libraries and the mill tools (stdlib unittest, image python3)
	$(KICAD_RUN) python3 -m unittest discover -s $(PCB_LIBS) -p 'test_*.py' -v
	$(KICAD_RUN) python3 -m unittest discover -s $(LAB_TOOLS) -p 'test_*.py' -v

bom: _kicad-cfg  ## export pcb/<BOARD>/bom.csv from the schematic fields (kicad-cli) and print the cost total
	$(KICAD_RUN) python3 $(PCB_LIBS)/bom_total.py --export

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

dev-setup:       ## host dev tools (ruff, pyright, pytest) from uv.lock into .venv, then direnv allow (skipped if direnv is missing); safe to rerun
	uv sync --frozen
	@if command -v direnv >/dev/null; then direnv allow || echo "WARN: direnv allow failed: run it by hand in the repo"; else echo "WARN: direnv missing: .venv/bin is not on your shell PATH (docs/setup.md, Claude Code)"; fi

check-dev:       ## check optional Claude Code dev tools (uv, direnv, LSP binaries) on PATH
	@for c in uv direnv pyright-langserver clangd; do command -v $$c >/dev/null && echo "OK   $$c" || echo "MISSING $$c (see docs/setup.md, Claude Code)"; done
