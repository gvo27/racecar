---
name: firmware-rtos
description: Use when you add, change or review a FreeRTOS task, priority, core, stack, shared state, critical section, blocking call, task watchdog or ISR in firmware/esp32. For keys, pins, Config and build steps use firmware-change.
---

# Firmware tasks and interrupts (ESP32-S3, FreeRTOS)

The project rules win over this skill: `.claude/rules/firmware.md` ("Architecture", "Safety"). Facts (tasks, cores, priorities, shared state, peripheral owners): `docs/firmware/README.md` ("Tasks and peripherals"). Source: rovinax/embedded-skills (`LICENSE.upstream`), adapted to this firmware.

## Task change
1. Give each task one job. The jobs are acquisition (one sensor), control (`controlTask`), comms (`loop()`) and service.
2. Do not add a second job to `controlTask` or `loop()`. Make a new task for it.
3. Each peripheral has one owner task. Other tasks give data to the owner through shared state. They do not use the peripheral.
4. `vTaskDelayUntil` in `controlTask` sets the control period. A message arrival never starts a control step. A stopped command stream starts the failsafe timeout. It does not stop the loop.
5. `controlTask` has the highest priority of the application tasks. A new task gets a lower priority. Put a sensor task on the core that does not run `controlTask` (cores: the doc).
6. A periodic loop uses `vTaskDelayUntil`, not `vTaskDelay`. Then the period does not drift.
7. After a retry wait (`vTaskDelay`) in a periodic loop, set `last = xTaskGetTickCount()`. If you do not, `vTaskDelayUntil` runs the missed periods with no wait (example: `rangefinderTask`).
8. Write each new or changed task in `docs/firmware/README.md` ("Tasks and peripherals"): period, core, priority, stack and owned peripherals. `deploy/tests/test_firmware_tasks.py` checks that each created task is there.

## Shared state
The rule gives the critical-section pattern. This section adds the ESP32 details.
- Add each new `g_` value to the shared-state list of the doc.
- `portENTER_CRITICAL` is a spinlock. It masks the normal interrupts on this core. The other core waits for the lock. Copy the data in or out, then exit.
- Inside a critical section: no I2C, no NVS, no `vTaskDelay`, no FreeRTOS call that can block, no loop with a variable bound.
- A 64-bit value (for example a `uint64_t` time stamp) is not atomic on the ESP32-S3. Read and write it only inside the critical section. `volatile` does not make it safe. An aligned 32-bit read is atomic.
- For events where each event counts, use a FreeRTOS queue or a task notification. For a value where only the newest value counts, use the `g_mux` copy.
- For a resource that two tasks must use for a long time (rare here), use a mutex with a timeout. Never use a mutex to pass data.

## Blocking and timing
- The only wait in `controlTask` is `vTaskDelayUntil`. It never waits on I2C, NVS, `Serial`, a mutex or a queue.
- An NVS write (`SAVE`, `Preferences`) turns off the flash cache on both cores. Each task and each ISR that runs from flash stops for that time. This includes `controlTask`. Write NVS only from `loop()`, and only on a command.
- A sensor driver waits with a timeout (example: `POLL_TIMEOUT_MS` in `src/rangefinder_lidar_lite_v4.cpp`). It never waits without a limit.

## Watchdog and stack
- Only the watched task resets its watchdog (`esp_task_wdt_reset()`, once in each period).
- Keep the period of a watched task much shorter than the watchdog timeout.
- Do not decrease a task stack without a bench measurement of `uxTaskGetStackHighWaterMark` (user-run). After `setup()`, do not print the result on `Serial` (rule). Send it in a command reply (the micro-ROS service), within `REPLY_CAP`.

## Interrupts
Before you add or change an ISR, read `references/isr.md`. First, try a hardware peripheral that needs no ISR: PCNT for encoder counts, RMT for RC pulse input, LEDC for PWM. Check the API at the pinned framework version (skill `hw-research`).

## Verify
- `make checks` (`test_firmware_tasks.py`: each task is in the doc, each ISR handler is `IRAM_ATTR`). The test does not check the functions that a handler calls.
- `make build`. Then `make compiledb` and the clangd diagnostics of the changed files.
- Read the diff of each changed task. For each critical section, list the code inside it. For each wait, name the task that waits and its limit.
- User-run only: `make flash`, the bench checklist. For a change to `controlTask` or a priority, add to the PR checklist: stop the command stream and see the `FAILSAFE` event within `timeoutMs`.
- Claim a result only with the command output from this session. A check that you did not run is "not run".
