/*
 * The boot guard's decisions, without ESP-IDF state (Q-79, TSK-I2f-10). Ported
 * from zclaw main/boot_guard.c (https://github.com/tnm/zclaw, commit e3ad271,
 * MIT, Copyright (c) 2026 Ted Nyman): every boot counts itself in NVS before it
 * does anything else, a boot that stays up long enough clears the count, and a
 * boot that finds the count at the limit starts in safe mode — serial console
 * only, no network, no gate runtime, nothing that could have caused the loop.
 *
 * Changed from zclaw: the count is a u32, not a decimal string; it saturates
 * instead of overflowing; the decision and the marker line are one place, driven
 * on the host (python/tests/test_c_boot_and_config.py).
 */
#ifndef NE_BOOT_POLICY_H
#define NE_BOOT_POLICY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Longest marker line, newline excluded. Buffers are NE_BOOT_LINE_MAX + 1. */
#define NE_BOOT_LINE_MAX 96u

typedef struct {
    uint32_t count;  /* this boot's number since the last stable boot, 1 for the first */
    uint32_t max;    /* the boot that reaches this number starts in safe mode */
    bool safe_mode;
} ne_boot_decision;

/*
 * `persisted` is the count NVS held before this boot (0 when there is none).
 * `max_failures` below 2 is treated as 2: a guard that put every boot, or the
 * first boot after a stable one, in safe mode would lock the owner out.
 */
ne_boot_decision ne_boot_decide(uint32_t persisted, uint32_t max_failures);

/*
 * The boot's marker, at column 0 for the QEMU jobs:
 *   NE_BOOT count=<n> max=<m> mode=normal|safe reason=<reason>
 * `reason` is the reset reason's short name (poweron, sw, panic, wdt, ...);
 * NULL or anything but [a-z_] prints `unknown`. Returns the length written,
 * or -1 when it does not fit `cap`.
 */
int ne_boot_marker(char *out, size_t cap, ne_boot_decision decision, const char *reason);

#ifdef __cplusplus
}
#endif

#endif /* NE_BOOT_POLICY_H */
