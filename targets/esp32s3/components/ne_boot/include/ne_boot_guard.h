/*
 * Boot guard, ESP-IDF side (Q-79, TSK-I2f-10; decisions in ne_boot_policy.h).
 *
 * main.c calls `ne_boot_guard_begin` right after NVS is up and before anything
 * that could crash: it reads the count, writes this boot's number, prints the
 * `NE_BOOT` marker and says whether to start in safe mode. Once the boot has
 * done all its startup, `ne_boot_guard_stable_after` clears the count after
 * CONFIG_NEUROEDGE_BOOT_GUARD_STABLE_MS. A boot that crashes, hangs in a reset
 * loop or loses power before then keeps its number, so the boot that reaches
 * CONFIG_NEUROEDGE_BOOT_GUARD_MAX starts in safe mode.
 *
 * The count lives in the default NVS partition (namespace `ne_boot`): it is
 * not a secret, and it must work before the owner's secrets are readable.
 */
#ifndef NE_BOOT_GUARD_H
#define NE_BOOT_GUARD_H

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "ne_boot_policy.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Count this boot, print `NE_BOOT ...`, and return the decision. When NVS
 * cannot be written the boot runs normally and says so (`NE_BOOT GUARD_OFF`):
 * a guard that cannot count must not lock the owner out either. */
ne_boot_decision ne_boot_guard_begin(void);

/* The decision `ne_boot_guard_begin` made for this boot. */
ne_boot_decision ne_boot_guard_current(void);

/* Start a low-priority task that clears the count after `stable_ms` and prints
 * `NE_BOOT STABLE`. 0 clears now. */
void ne_boot_guard_stable_after(uint32_t stable_ms);

/* Clear the count now (console `bootguard clear`); prints `NE_BOOT CLEARED`. */
esp_err_t ne_boot_guard_clear(void);

#ifdef __cplusplus
}
#endif

#endif /* NE_BOOT_GUARD_H */
