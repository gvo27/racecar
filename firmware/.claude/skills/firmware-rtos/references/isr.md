# Interrupt handlers (ESP32-S3, Arduino core on ESP-IDF)

Read this file before you add or change an ISR. The firmware has no ISR now. The first candidates are the reserved pins (encoder, IMU interrupt, battery low: `docs/firmware/README.md`).

## Rules
1. Mark the handler `IRAM_ATTR`. An NVS write stops the flash cache, and a handler in flash then crashes the chip. `test_firmware_tasks.py` checks the handlers of `attachInterrupt` and `gpio_isr_handler_add`.
2. A constant table that the handler reads must be in RAM (`DRAM_ATTR`).
3. The handler only records the event:
   - read and clear the hardware status
   - take a time stamp (`esp_timer_get_time()`)
   - increment a 32-bit counter
   - put one item in a queue or a ring buffer with a fixed size
   - notify a task
   The task does all other work.
4. Not in a handler: `Serial`, log calls, `malloc` or `new`, `delay`, I2C, LEDC writes, a loop with a variable bound, protocol parsing, control math.
5. No floating-point math in a handler. ESP-IDF does not support the FPU in an ISR on the Xtensa cores.
6. Use the `FromISR` FreeRTOS calls (`xQueueSendFromISR`, `vTaskNotifyGiveFromISR`). End the handler with `portYIELD_FROM_ISR(woken)`.
7. Shared state: `portENTER_CRITICAL_ISR(&g_mux)` in the handler, `portENTER_CRITICAL(&g_mux)` in the task. The task reads a counter of the handler only under `g_mux`.
8. Keep the handler short: a few microseconds (generic start value, not measured on this car).
9. Write each ISR in `docs/firmware/README.md` ("Tasks and peripherals"): pin, edge, and the task that it notifies.

## Verify
Use the Verify section of `SKILL.md`. For a new ISR, add to the PR bench checklist: run `SAVE` while the interrupt source is active. The chip must not reset.
