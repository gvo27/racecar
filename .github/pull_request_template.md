<!-- Write this PR in ASD-STE100 style (STE-flavored): see .claude/rules/writing.md. -->

## Summary
<!-- What changed and why, in a few sentences. -->

## Changes
<!-- Bullet list by area (firmware, ROS packages, tuning, docs). Show protocol and tuning key changes. -->

## CI
<!-- Which checks cover this change: firmware build, ros-test, unit. Link the runs or paste the results. -->

## Bench checklist (user-run)
<!-- Agents never tick hardware boxes. Wheels off the ground, ESC power switch within reach. Paste the output under each step. -->

Deploy:
- [ ] `git pull` / check out this branch
- [ ] `make setup` (rebuilds firmware + ROS images, picks up dependency changes)
- [ ] `make config`
- [ ] `make car-down`
- [ ] `make flash` (if `firmware/` changed. Use `make clean && make flash` if `rccar.meta`, `extra_packages` or `platformio.ini` changed)
- [ ] `make car-up && make car-ps` (all services healthy)

Feature checks:
- [ ] <!-- feature-specific hardware checks, one per box, with the expected output. For a sensor PR, paste the `make lidar-hw-test` report table. -->

Regression:
- [ ] `make test` passes
- [ ] `make teleop`: drive, brake and disarm behave as before
