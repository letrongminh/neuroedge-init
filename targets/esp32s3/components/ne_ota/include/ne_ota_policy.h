/*
 * The decisions of the OTA component that carry no ESP-IDF state (FR-OTA-01..04,
 * TSK-S6-01/02/04). `ne_ota.c` reads partitions, the network and the UART; what
 * is decided — install or not, mark valid or roll back, how a URL is shown, how
 * a marker line reads — is here, so the host tests compile and drive it exactly
 * (python/tests/test_c_ota_policy.py), like the walker and the token ledger.
 *
 * Every refusal names its reason; no function guesses on missing input. A URL
 * printed anywhere goes through `ne_ota_sanitize_url`: credentials never reach
 * the UART.
 */
#ifndef NE_OTA_POLICY_H
#define NE_OTA_POLICY_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Longest marker line, newline excluded. Buffers are NE_OTA_LINE_MAX + 1. */
#define NE_OTA_LINE_MAX 512u
/* Longest version an image carries: esp_app_desc_t.version[32], NUL included. */
#define NE_OTA_VERSION_MAX 32u

/*
 * Whether `ne_ota.c` may write the remote image. A missing or empty version on
 * either side is a refusal, not a guess: an update whose effect cannot be told
 * apart from what runs now must not happen.
 */
typedef enum {
    NE_OTA_INSTALL = 0,
    NE_OTA_SKIP_SAME_VERSION, /* the running app is this version already */
    NE_OTA_SKIP_NO_VERSION,   /* the running or the remote version is unreadable */
    NE_OTA_SKIP_ROLLED_BACK,  /* the version the device rolled back from */
} ne_ota_decision;

ne_ota_decision ne_ota_should_install(const char *running_version, const char *remote_version,
                                      const char *rolled_back_version);

/* The reason field of `NE_OTA SKIP`, one word per decision. */
const char *ne_ota_decision_reason(ne_ota_decision decision);

/*
 * What to do with the running image at boot. The rule of FR-OTA-02: an image
 * that boots in PENDING_VERIFY is marked valid only after the gate self-test
 * passed; a failed self-test marks it invalid, and the bootloader then brings
 * back the previous app. Factory images are never marked — they keep working as
 * before OTA existed.
 */
typedef enum {
    NE_OTA_BOOT_NONE = 0,     /* factory, or an image already valid: nothing to mark */
    NE_OTA_BOOT_MARK_VALID,   /* pending verification, self-test passed */
    NE_OTA_BOOT_MARK_INVALID, /* pending verification, self-test failed */
} ne_ota_boot_action;

ne_ota_boot_action ne_ota_boot_action_for(bool is_ota_partition, bool pending_verify,
                                          bool selftest_ok);

/*
 * Copy `url` into `out`, dropping `user:password@` in front of the host, the way
 * `snprintf` returns: the length that would have been written. >= cap means the
 * URL did not fit (truncated); the result is always NUL-terminated when cap > 0.
 */
size_t ne_ota_sanitize_url(const char *url, char *out, size_t cap);

/*
 * One anchored UART line per OTA event, built whole: false when the line does
 * not fit, in which case `out` holds nothing and the caller prints nothing — a
 * half marker must never read as a whole one. `ne_ota_marker_check` sanitizes
 * the URL first.
 */
bool ne_ota_marker_check(char *out, size_t cap, const char *url);
bool ne_ota_marker_downloaded(char *out, size_t cap, unsigned bytes, const char *version);
bool ne_ota_marker_rejected(char *out, size_t cap, const char *reason);
bool ne_ota_marker_switch(char *out, size_t cap, const char *partition);
bool ne_ota_marker_valid(char *out, size_t cap, const char *partition);
bool ne_ota_marker_invalid(char *out, size_t cap, const char *partition);
bool ne_ota_marker_rollback(char *out, size_t cap, const char *from, const char *to);
bool ne_ota_marker_skip(char *out, size_t cap, const char *reason, const char *version);

#ifdef __cplusplus
}
#endif

#endif /* NE_OTA_POLICY_H */
