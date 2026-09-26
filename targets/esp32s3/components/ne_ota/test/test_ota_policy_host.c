/*
 * Host conformance runner for the OTA decisions (TSK-S6-01/02/04).
 *
 * Drives every branch of ne_ota_policy.c: the install/refuse decision table
 * (including unreadable versions and the version the device rolled back from),
 * the boot action that ties marking valid to the gate self-test, URL
 * sanitisation (credentials never reach the UART) and the anchored markers,
 * line for line. Exit 0 only when every check passed; the Python test
 * (python/tests/test_c_ota_policy.py) compiles and runs this.
 */
#include <stdio.h>
#include <string.h>

#include "ne_ota_policy.h"

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

static int check_install(void) {
    CHECK(ne_ota_should_install("0.1.0", "0.2.0", NULL) == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.1.0", NULL) == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "0.0.9", NULL) == NE_OTA_INSTALL); /* downgrade: allowed */
    CHECK(ne_ota_should_install(NULL, "0.2.0", NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", NULL, NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("", "0.2.0", NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "", NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "0.2.0", "") == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.3.0", "0.3.0") == NE_OTA_SKIP_ROLLED_BACK);
    CHECK(ne_ota_should_install("0.1.0", "0.3.1", "0.3.0") == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.1.0", "0.3.0") == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "0.2.0", NULL) == NE_OTA_INSTALL);

    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_SAME_VERSION), "same_version") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_NO_VERSION), "no_version") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_ROLLED_BACK), "rolled_back") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_INSTALL), "install") == 0);
    return 0;
}

static int check_boot_action(void) {
    for (int ota = 0; ota < 2; ota++) {
        for (int pending = 0; pending < 2; pending++) {
            for (int ok = 0; ok < 2; ok++) {
                const ne_ota_boot_action action =
                    ne_ota_boot_action_for(ota != 0, pending != 0, ok != 0);
                ne_ota_boot_action expected = NE_OTA_BOOT_NONE;
                if (ota && pending) expected = ok ? NE_OTA_BOOT_MARK_VALID : NE_OTA_BOOT_MARK_INVALID;
                CHECK(action == expected);
            }
        }
    }
    return 0;
}

static int check_sanitize(void) {
    char out[128];

    CHECK(ne_ota_sanitize_url("http://alice:secret@example.com/fw.bin", out, sizeof out) == 25);
    CHECK(strcmp(out, "http://example.com/fw.bin") == 0);
    CHECK(ne_ota_sanitize_url("https://token@host:8080/a/b.bin", out, sizeof out) == 25);
    CHECK(strcmp(out, "https://host:8080/a/b.bin") == 0);
    CHECK(ne_ota_sanitize_url("http://host/a@b.bin", out, sizeof out) == 19);
    CHECK(strcmp(out, "http://host/a@b.bin") == 0);
    CHECK(ne_ota_sanitize_url("http://a@b@host/x", out, sizeof out) == 13);
    CHECK(strcmp(out, "http://host/x") == 0);
    CHECK(ne_ota_sanitize_url("http://user@host", out, sizeof out) == 11);
    CHECK(strcmp(out, "http://host") == 0);
    CHECK(ne_ota_sanitize_url("host/path", out, sizeof out) == 9);
    CHECK(strcmp(out, "host/path") == 0);
    CHECK(ne_ota_sanitize_url("http://example.com/fw.bin", out, 8) == 25);
    CHECK(strcmp(out, "http://") == 0); /* truncated, still NUL-terminated */
    CHECK(ne_ota_sanitize_url(NULL, out, sizeof out) == 0);
    CHECK(out[0] == '\0');
    CHECK(ne_ota_sanitize_url("http://host/x", NULL, 0) == 13); /* no buffer: no write */
    return 0;
}

static int check_markers(void) {
    char line[NE_OTA_LINE_MAX + 1];

    CHECK(ne_ota_marker_check(line, sizeof line, "http://alice:secret@example.com/fw.bin"));
    CHECK(strcmp(line, "NE_OTA CHECK url=http://example.com/fw.bin") == 0);
    CHECK(ne_ota_marker_downloaded(line, sizeof line, 1234u, "0.2.0"));
    CHECK(strcmp(line, "NE_OTA DOWNLOADED bytes=1234 version=0.2.0") == 0);
    CHECK(ne_ota_marker_rejected(line, sizeof line, "signature"));
    CHECK(strcmp(line, "NE_OTA REJECTED reason=signature") == 0);
    CHECK(ne_ota_marker_switch(line, sizeof line, "ota_1"));
    CHECK(strcmp(line, "NE_OTA SWITCH partition=ota_1") == 0);
    CHECK(ne_ota_marker_valid(line, sizeof line, "ota_0"));
    CHECK(strcmp(line, "NE_OTA VALID partition=ota_0") == 0);
    CHECK(ne_ota_marker_invalid(line, sizeof line, "ota_1"));
    CHECK(strcmp(line, "NE_OTA INVALID partition=ota_1") == 0);
    CHECK(ne_ota_marker_rollback(line, sizeof line, "ota_1", "ota_0"));
    CHECK(strcmp(line, "NE_OTA ROLLBACK from=ota_1 to=ota_0") == 0);
    CHECK(ne_ota_marker_skip(line, sizeof line, "rolled_back", "0.3.0"));
    CHECK(strcmp(line, "NE_OTA SKIP reason=rolled_back version=0.3.0") == 0);

    /* Exactly fitting is a whole line; one byte less is no line at all. */
    const char *exact = "NE_OTA SWITCH partition=ota_1";
    CHECK(ne_ota_marker_switch(line, strlen(exact) + 1, "ota_1"));
    CHECK(strcmp(line, exact) == 0);
    line[0] = 'x';
    CHECK(!ne_ota_marker_switch(line, strlen(exact), "ota_1"));
    CHECK(line[0] == '\0');

    CHECK(!ne_ota_marker_rejected(line, sizeof line, NULL));
    CHECK(!ne_ota_marker_switch(line, sizeof line, NULL));
    CHECK(!ne_ota_marker_valid(line, sizeof line, NULL));
    CHECK(!ne_ota_marker_invalid(line, sizeof line, NULL));
    CHECK(!ne_ota_marker_rollback(line, sizeof line, NULL, "ota_0"));
    CHECK(!ne_ota_marker_skip(line, sizeof line, "version", NULL));
    CHECK(!ne_ota_marker_downloaded(line, sizeof line, 1u, NULL));
    CHECK(!ne_ota_marker_check(line, sizeof line, NULL));

    /* A URL the marker cannot carry whole refuses the marker, not truncates it. */
    char long_url[600];
    memset(long_url, 'a', sizeof long_url - 1);
    long_url[0] = 'h';
    long_url[1] = 't';
    long_url[2] = 't';
    long_url[3] = 'p';
    long_url[4] = ':';
    long_url[5] = '/';
    long_url[6] = '/';
    long_url[sizeof long_url - 1] = '\0';
    line[0] = 'x';
    CHECK(!ne_ota_marker_check(line, sizeof line, long_url));
    CHECK(line[0] == '\0');
    return 0;
}

int main(void) {
    if (check_install() != 0) return 1;
    if (check_boot_action() != 0) return 1;
    if (check_sanitize() != 0) return 1;
    if (check_markers() != 0) return 1;
    printf("NE_OTA_POLICY OK checks=%u\n", s_checks);
    return 0;
}
