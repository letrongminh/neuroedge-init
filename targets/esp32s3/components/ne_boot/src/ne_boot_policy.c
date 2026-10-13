/*
 * The boot guard's decisions (ne_boot_policy.h). Pure C99: compiled on the host
 * with sanitizers by python/tests/test_c_boot_and_config.py. Adapted from zclaw
 * main/boot_guard.c (https://github.com/tnm/zclaw, commit e3ad271, MIT,
 * Copyright (c) 2026 Ted Nyman).
 */
#include "ne_boot_policy.h"

#include <stdio.h>
#include <string.h>

ne_boot_decision ne_boot_decide(uint32_t persisted, uint32_t max_failures)
{
    ne_boot_decision decision;
    decision.max = max_failures < 2u ? 2u : max_failures;
    decision.count = persisted == UINT32_MAX ? UINT32_MAX : persisted + 1u;
    decision.safe_mode = decision.count >= decision.max;
    return decision;
}

static bool reason_is_name(const char *reason)
{
    if (reason == NULL || reason[0] == '\0' || strlen(reason) > 16u) return false;
    for (const char *c = reason; *c != '\0'; c++) {
        if (!((*c >= 'a' && *c <= 'z') || *c == '_')) return false;
    }
    return true;
}

int ne_boot_marker(char *out, size_t cap, ne_boot_decision decision, const char *reason)
{
    if (out == NULL || cap == 0u) return -1;
    const int n = snprintf(out, cap, "NE_BOOT count=%lu max=%lu mode=%s reason=%s",
                           (unsigned long)decision.count, (unsigned long)decision.max,
                           decision.safe_mode ? "safe" : "normal",
                           reason_is_name(reason) ? reason : "unknown");
    if (n < 0 || (size_t)n >= cap) {
        out[0] = '\0';
        return -1;
    }
    return n;
}
