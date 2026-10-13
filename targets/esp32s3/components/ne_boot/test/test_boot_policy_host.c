/*
 * Host conformance runner for the boot guard's decisions (Q-79, TSK-I2f-10).
 *
 * The count, the safe-mode threshold (and its floor of 2, so the owner is never
 * locked out), saturation, and the marker line. Exit 0 only when every check
 * passed; python/tests/test_c_boot_and_config.py compiles and runs this.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ne_boot_policy.h"

static unsigned s_checks;

static int fail(const char *what, int line) {
    fprintf(stderr, "FAIL line %d: %s\n", line, what);
    return 1;
}

#define CHECK(cond)                     \
    do {                                \
        s_checks++;                     \
        if (!(cond)) return fail(#cond, __LINE__); \
    } while (0)

static int check_decide(void) {
    /* zclaw's MAX_BOOT_FAILURES = 4: three boots that never stay up, the fourth is safe. */
    for (uint32_t persisted = 0; persisted < 3u; persisted++) {
        const ne_boot_decision d = ne_boot_decide(persisted, 4u);
        CHECK(d.count == persisted + 1u);
        CHECK(d.max == 4u);
        CHECK(!d.safe_mode);
    }
    CHECK(ne_boot_decide(3u, 4u).safe_mode);
    CHECK(ne_boot_decide(3u, 4u).count == 4u);
    CHECK(ne_boot_decide(10u, 4u).safe_mode); /* stays safe until the count is cleared */
    /* The first boot after a stable one is never safe, whatever the limit says. */
    CHECK(!ne_boot_decide(0u, 0u).safe_mode);
    CHECK(!ne_boot_decide(0u, 1u).safe_mode);
    CHECK(ne_boot_decide(0u, 1u).max == 2u);
    CHECK(ne_boot_decide(1u, 1u).safe_mode);
    CHECK(!ne_boot_decide(0u, 2u).safe_mode);
    CHECK(ne_boot_decide(1u, 2u).safe_mode);
    /* Saturates instead of wrapping back to a normal boot. */
    CHECK(ne_boot_decide(UINT32_MAX, 4u).count == UINT32_MAX);
    CHECK(ne_boot_decide(UINT32_MAX, 4u).safe_mode);
    CHECK(ne_boot_decide(UINT32_MAX - 1u, 4u).count == UINT32_MAX);
    CHECK(ne_boot_decide(18u, 20u).safe_mode == false);
    CHECK(ne_boot_decide(19u, 20u).safe_mode);
    return 0;
}

static int check_marker(void) {
    char line[NE_BOOT_LINE_MAX + 1];
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), "poweron") > 0);
    CHECK(strcmp(line, "NE_BOOT count=1 max=4 mode=normal reason=poweron") == 0);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(3u, 4u), "task_wdt") > 0);
    CHECK(strcmp(line, "NE_BOOT count=4 max=4 mode=safe reason=task_wdt") == 0);
    /* A reason that is not a plain name never reaches the line. */
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), NULL) > 0);
    CHECK(strcmp(line, "NE_BOOT count=1 max=4 mode=normal reason=unknown") == 0);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), "") > 0);
    CHECK(strstr(line, "reason=unknown") != NULL);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), "sw\nNE_SELFTEST PASS") > 0);
    CHECK(strcmp(line, "NE_BOOT count=1 max=4 mode=normal reason=unknown") == 0);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), "PANIC") > 0);
    CHECK(strstr(line, "reason=unknown") != NULL);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(0u, 4u), "a_very_long_reason_name") > 0);
    CHECK(strstr(line, "reason=unknown") != NULL);
    CHECK(ne_boot_marker(line, sizeof line, ne_boot_decide(UINT32_MAX, 20u), "brownout") > 0);
    CHECK(strcmp(line, "NE_BOOT count=4294967295 max=20 mode=safe reason=brownout") == 0);
    /* Too small a buffer: -1 and an empty string, never a cut line. */
    char small[16];
    small[0] = 'x';
    CHECK(ne_boot_marker(small, sizeof small, ne_boot_decide(0u, 4u), "sw") == -1);
    CHECK(small[0] == '\0');
    CHECK(ne_boot_marker(NULL, 10u, ne_boot_decide(0u, 4u), "sw") == -1);
    CHECK(ne_boot_marker(line, 0u, ne_boot_decide(0u, 4u), "sw") == -1);
    return 0;
}

int main(void) {
    if (check_decide() != 0) return 1;
    if (check_marker() != 0) return 1;
    printf("NE_BOOT_POLICY OK checks=%u\n", s_checks);
    return 0;
}
