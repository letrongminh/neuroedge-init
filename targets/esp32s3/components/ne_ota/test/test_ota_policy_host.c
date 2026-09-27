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
    CHECK(ne_ota_should_install("0.1.0", "0.2.0", NULL, NULL) == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.1.0", NULL, NULL) == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install(NULL, "0.2.0", NULL, NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", NULL, NULL, NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("", "0.2.0", NULL, NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "", NULL, NULL) == NE_OTA_SKIP_NO_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "0.2.0", "", "") == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.3.0", "0.3.0", NULL) == NE_OTA_SKIP_ROLLED_BACK);
    CHECK(ne_ota_should_install("0.1.0", "0.3.1", "0.3.0", NULL) == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.1.0", "0.1.0", "0.3.0", NULL) == NE_OTA_SKIP_SAME_VERSION);
    /* A version that does not parse decides nothing: refuse, do not guess. */
    CHECK(ne_ota_should_install("0.1.0", "banana", NULL, NULL) == NE_OTA_SKIP_BAD_VERSION);
    CHECK(ne_ota_should_install("v0.1.0", "0.2.0", NULL, NULL) == NE_OTA_SKIP_BAD_VERSION);
    CHECK(ne_ota_should_install("0.1.0", "1.2.3.4", NULL, NULL) == NE_OTA_SKIP_BAD_VERSION);
    /* The high-water mark: anything not newer is refused; an unreadable mark
     * refuses everything (a downgrade is the worse failure). */
    CHECK(ne_ota_should_install("0.2.0", "0.3.0", NULL, "0.2.0") == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.2.0", "0.2.0", NULL, "0.2.0") == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install("0.3.0", "0.2.0", NULL, "0.2.0") == NE_OTA_SKIP_DOWNGRADE);
    CHECK(ne_ota_should_install("0.3.0", "0.3.0", NULL, "0.3.0") == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install("0.3.0", "0.3.0", NULL, "0.4.0") == NE_OTA_SKIP_SAME_VERSION);
    CHECK(ne_ota_should_install("0.3.0", "0.2.0", NULL, "") == NE_OTA_INSTALL);
    CHECK(ne_ota_should_install("0.3.0", "0.2.0", NULL, "nonsense") == NE_OTA_SKIP_BAD_VERSION);
    CHECK(ne_ota_should_install("0.3.0", "0.3.1", "0.3.1", "0.3.1") == NE_OTA_SKIP_ROLLED_BACK);
    /* Versions are compared as parsed triples, never as strings; and a
     * version that does not parse is refused, not compared loosely — "0.3"
     * is not "0.3.0" here, it is unusable. */
    CHECK(ne_ota_should_install("0.2.0", "0.3", "0.3.0", NULL) == NE_OTA_SKIP_BAD_VERSION);
    CHECK(ne_ota_should_install("0.3", "0.3.0", NULL, NULL) == NE_OTA_SKIP_BAD_VERSION);
    CHECK(ne_ota_should_install("0.2.0", "0.3.0", "0.3", NULL) == NE_OTA_SKIP_BAD_VERSION);

    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_SAME_VERSION), "same_version") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_NO_VERSION), "no_version") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_ROLLED_BACK), "rolled_back") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_DOWNGRADE), "downgrade") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_SKIP_BAD_VERSION), "bad_version") == 0);
    CHECK(strcmp(ne_ota_decision_reason(NE_OTA_INSTALL), "install") == 0);
    return 0;
}

static int check_versions(void) {
    uint32_t parts[3];
    CHECK(ne_ota_parse_version("1.2.3", parts) && parts[0] == 1 && parts[1] == 2 && parts[2] == 3);
    CHECK(ne_ota_parse_version("0.0.0", parts) && parts[0] == 0 && parts[1] == 0 && parts[2] == 0);
    CHECK(ne_ota_parse_version("10.20.30", parts) && parts[0] == 10);
    CHECK(ne_ota_parse_version("4294967295.0.1", parts) && parts[0] == 4294967295u);
    /* Exactly three parts, no leading zeros: the same rule as _RELEASE in
     * python/neuroedge/engine/firmware.py (test_ota_version_host.c pins both). */
    CHECK(!ne_ota_parse_version("", parts));
    CHECK(!ne_ota_parse_version(NULL, parts));
    CHECK(!ne_ota_parse_version("1", parts));
    CHECK(!ne_ota_parse_version("1.2", parts));
    CHECK(!ne_ota_parse_version("1.2.3.4", parts));
    CHECK(!ne_ota_parse_version("01.002.0003", parts));
    CHECK(!ne_ota_parse_version("1.02.3", parts));
    CHECK(!ne_ota_parse_version("1.2.03", parts));
    CHECK(!ne_ota_parse_version("00.1.2", parts));
    CHECK(!ne_ota_parse_version("1..2", parts));
    CHECK(!ne_ota_parse_version("1.2.", parts));
    CHECK(!ne_ota_parse_version(".1.2", parts));
    CHECK(!ne_ota_parse_version("a.b.c", parts));
    CHECK(!ne_ota_parse_version("1.2.x", parts));
    CHECK(!ne_ota_parse_version("1.-2", parts));
    CHECK(!ne_ota_parse_version("1.2. 3", parts));
    CHECK(!ne_ota_parse_version("4294967296.0.0", parts));
    CHECK(!ne_ota_parse_version("999999999999.0.0", parts));

    const uint32_t one[3] = {1, 2, 3}, two[3] = {1, 2, 3}, three[3] = {1, 2, 4};
    CHECK(ne_ota_compare_versions(one, two) == 0);
    CHECK(ne_ota_compare_versions(one, three) == -1);
    CHECK(ne_ota_compare_versions(three, two) == 1);

    /* The mark rises only from a parsable running version; an unreadable mark
     * is never repaired (it may have been higher). */
    CHECK(ne_ota_mark_should_rise("0.2.0", NULL));
    CHECK(ne_ota_mark_should_rise("0.2.0", ""));
    CHECK(ne_ota_mark_should_rise("0.2.0", "0.1.0"));
    CHECK(!ne_ota_mark_should_rise("0.2.0", "0.2.0"));
    CHECK(!ne_ota_mark_should_rise("0.2.0", "0.3.0"));
    CHECK(!ne_ota_mark_should_rise("0.2.0", "garbage"));
    CHECK(!ne_ota_mark_should_rise("garbage", NULL));

    /* A redirect is refused, whichever 3xx code it is; 2xx/4xx are not. */
    CHECK(strcmp(ne_ota_status_reason(301), "redirect") == 0);
    CHECK(strcmp(ne_ota_status_reason(302), "redirect") == 0);
    CHECK(strcmp(ne_ota_status_reason(308), "redirect") == 0);
    CHECK(ne_ota_status_reason(200) == NULL);
    CHECK(ne_ota_status_reason(204) == NULL);
    CHECK(ne_ota_status_reason(404) == NULL);
    CHECK(ne_ota_status_reason(0) == NULL);
    CHECK(ne_ota_status_reason(-1) == NULL);

    char out[NE_OTA_VERSION_MAX];
    /* A complete slot image wins; a corrupt one (slot_valid false) must not
     * overwrite the recorded version that bootlooped. */
    CHECK(ne_ota_resolve_rollback("0.3.0", "0.4.0", true, out, sizeof out) &&
          strcmp(out, "0.4.0") == 0);
    CHECK(ne_ota_resolve_rollback("0.3.0", "0.4.0", false, out, sizeof out) &&
          strcmp(out, "0.3.0") == 0);
    CHECK(ne_ota_resolve_rollback("0.3.0", NULL, false, out, sizeof out) &&
          strcmp(out, "0.3.0") == 0);
    CHECK(ne_ota_resolve_rollback("0.3.0", "", true, out, sizeof out) &&
          strcmp(out, "0.3.0") == 0);
    out[0] = 'x';
    CHECK(!ne_ota_resolve_rollback("", NULL, false, out, sizeof out));
    CHECK(out[0] == '\0');
    CHECK(!ne_ota_resolve_rollback(NULL, NULL, false, out, sizeof out));
    CHECK(!ne_ota_resolve_rollback(NULL, NULL, false, NULL, 0));
    CHECK(!ne_ota_resolve_rollback(NULL, NULL, true, out, sizeof out));

    /* The total deadline and the no-progress limit, wrapping at 2^32 ms. */
    CHECK(!ne_ota_download_timed_out(1000u, 0u, 900u, 300000u, 30000u));
    CHECK(ne_ota_download_timed_out(300000u, 0u, 299000u, 300000u, 30000u));
    CHECK(ne_ota_download_timed_out(31000u, 0u, 1000u, 300000u, 30000u));
    CHECK(!ne_ota_download_timed_out(100u, 0xFFFFFF00u, 90u, 300000u, 30000u)); /* wrapped */
    CHECK(ne_ota_download_timed_out(0xFFFFFF00u, 1u, 0u, 300000u, 30000u));
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
    /* A query string or fragment may carry a secret: never printed. */
    CHECK(ne_ota_sanitize_url("http://alice:secret@host:80/fw.bin?a=b#c", out, sizeof out) == 21);
    CHECK(strcmp(out, "http://host:80/fw.bin") == 0);
    CHECK(ne_ota_sanitize_url("http://host/fw.bin?token=secret", out, sizeof out) == 18);
    CHECK(strcmp(out, "http://host/fw.bin") == 0);
    CHECK(ne_ota_sanitize_url("http://host/fw.bin#frag", out, sizeof out) == 18);
    CHECK(strcmp(out, "http://host/fw.bin") == 0);
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
    CHECK(ne_ota_marker_erased(line, sizeof line, "ota_1"));
    CHECK(strcmp(line, "NE_OTA ERASED partition=ota_1") == 0);

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
    CHECK(!ne_ota_marker_erased(line, sizeof line, NULL));
    CHECK(!ne_ota_marker_erased(line, 8, "ota_1"));

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
    if (check_versions() != 0) return 1;
    if (check_boot_action() != 0) return 1;
    if (check_sanitize() != 0) return 1;
    if (check_markers() != 0) return 1;
    printf("NE_OTA_POLICY OK checks=%u\n", s_checks);
    return 0;
}
