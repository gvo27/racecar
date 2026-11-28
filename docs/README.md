# docs/: index

One line for each entry. Folders have their own README.

| Path | Purpose |
|---|---|
| [setup.md](setup.md) | Zero to driving: host, wiring, flash, stack, drive, sensors, bench checklist |
| [commands.md](commands.md) | Make commands: once per Pi, sensors, when needed |
| [hardware.md](hardware.md) | Inventory, rangefinder wiring, power rules, power-up sequence |
| [invariants.md](invariants.md) | Rules that are true for every change (loaded in each agent session) |
| [adr/](adr/README.md) | Architecture decision records |
| [interfaces/sensor_contract.md](interfaces/sensor_contract.md) | Hardware-boundary topics, frames, QoS, TF and their source code (tested) |
| [interfaces/ros2.md](interfaces/ros2.md) | Topics above the boundary, services, subscribers |
| [deploy.md](deploy.md) | Car stack deploy: config split, compose, host files, image stages |
| [dependencies.md](dependencies.md) | Stack pins, host prerequisites, toolchain images, plugin sources |
| [claude-tooling.md](claude-tooling.md) | Claude Code plugins, session targets, hook, test scopes |
| [docker_ros_plan.md](docker_ros_plan.md) | Roadmap and phases of the ROS 2 and docker stack |
| [firmware/](firmware/README.md) | ESP32 firmware reference: build, tasks, limits, command grammar |
| [tools/](tools/README.md) | Calibration, teleop and monitor tools |
| [rangefinder/](rangefinder/README.md) | Rangefinder status and findings |
| [lidar/](lidar/README.md) | Lidar status, driver reference, roadmap |
| [sim/](sim/README.md) | Car-side sim findings |
| [pcb/](pcb/README.md) | Power board context: plan, conventions, BOM, review records |
| [techctcarvera/](techctcarvera/README.md) | The lab directory: mill limits, tools, CAM template |
| [datasheets/](datasheets/) | Part datasheets and digests |
| [plans/](plans/) | Plans in progress (done plans go to `archive/plans/`) |
| [archive/](archive/README.md) | Stale plans, proposals and reviews |
| [tuning-notes.txt](tuning-notes.txt) | Raw bench tuning notes |
