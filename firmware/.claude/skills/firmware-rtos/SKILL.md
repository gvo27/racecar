---
name: firmware-rtos
description: Use when you add, change or review a FreeRTOS task, a task priority, core or stack, the state that tasks share, a critical section, a blocking call, the task watchdog or an interrupt handler (ISR) in firmware/esp32. Keeps the control loop on time and each peripheral with one owner. For keys, pins, Config and build steps use firmware-change.
---

# Firmware tasks and interrupts (ESP32-S3, FreeRTOS)

The project rules win over this skill: `.claude/rules/firmware.md` ("Architecture", "Safety"). Facts (tasks, cores, priorities, shared state, peripheral owners): `docs/firmware/README.md` ("Tasks and peripherals"). Source: rovinax/embedded-skills (`LICENSE.upstream`), adapted to this firmware.

## Task change
1. Give each task one job: acquisition (one sensor), control (`controlTask`), comms (`loop()`) or service. Do not add a second job to `controlTask` or `loop()`. Make a new task for it.
2. Each peripheral has one owner task. Other tasks give data to the owner through shared state. They do not use the peripheral.
3. `vTaskDelayUntil` in `controlTask` sets the control period. A message arrival never starts a control step. A stopped command stream starts the failsafe timeout. It does not stop the loop.
4. `controlTask` has the highest priority of the application tasks. A new task gets a lower priority. Put a sensor task on the core that does not run `controlTask` (cores: the doc).
5. A periodic loop uses `vTaskDelayUntil`, not `vTaskDelay`. Then the period does not drift.
6. After a retry wait (`vTaskDelay`) in a periodic loop, set `last = xTaskGetTickCount()`. If you do not, `vTaskDelayUntil` runs the missed periods with no wait (example: `rangefinderTask`).
7. Write each new or changed task in `docs/firmware/README.md` ("Tasks and peripherals"): period, core, priority, stack and owned peripherals. `deploy/tests/test_firmware_tasks.py` checks that each created task is there.

## Shared state
- Put a value that two tasks, or a task and an ISR, use in a `g_` variable under `g_mux`. Add it to the shared-state list of the doc.
- `portENTER_CRITICAL` is a spinlock. It also stops the interrupts on that core. Copy the data in or out, then exit.
- Inside a critical section: no I2C, no NVS, no `Serial`, no `vTaskDelay`, no FreeRTOS call that can block, no loop with a variable bound.
- A 64-bit value (for example a `uint64_t` time stamp) is not atomic on the ESP32-S3. Read and write it only inside the critical section. `volatile` does not make it safe.
- For events where each event counts, use a FreeRTOS queue or a task notification. For a value where only the newest value counts, use the `g_mux` copy.

## Blocking and timing
- The only wait in `controlTask` is `vTaskDelayUntil`. It never waits on I2C, NVS, `Serial`, a mutex or a queue.
- An NVS write (`SAVE`, `Preferences`) stops the flash cache. Code that runs from flash can stop for that time, also on the other core. Write NVS only from `loop()`, and only on a command.
- A sensor driver waits with a timeout (`POLL_TIMEOUT_MS` style). It never waits without a limit.

## Watchdog and stack
- A task that writes an actuator is on the task watchdog: `esp_task_wdt_add(nullptr)` at the start, `esp_task_wdt_reset()` once in each period. Only the watched task resets its watchdog.
- Keep the period of a watched task much shorter than the watchdog timeout.
- Do not decrease a task stack without a bench measurement of `uxTaskGetStackHighWaterMark` (user-run). After `setup()`, `Serial` is not available for the result (rule).

## Interrupts
Before you add or change an ISR, read `references/isr.md`. First, try a hardware peripheral that needs no ISR: PCNT for encoder counts, RMT for RC pulse input, LEDC for PWM. Check the API at the pinned framework version (skill `hw-research`).

## Verify
- `make checks` (`test_firmware_tasks.py`: tasks in the doc, ISRs in IRAM).
- `make build`. Then `make compiledb` and the clangd diagnostics of the changed files.
- Read the diff of each changed task. For each critical section, list the code inside it. For each wait, name the task that waits and its limit.
- User-run only: `make flash`, the bench checklist. For a change to `controlTask` or a priority, add to the PR checklist: stop the command stream and see the `FAILSAFE` event within `timeoutMs`.
- Claim a result only with the command output from this session. A check that you did not run is "not run".
