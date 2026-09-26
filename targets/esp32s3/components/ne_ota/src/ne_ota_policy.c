/*
 * Decisions of the OTA component — see ne_ota_policy.h. C99, no ESP-IDF, no
 * allocation, no globals: the host tests drive every branch.
 */
#include "ne_ota_policy.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static bool empty(const char *text) {
    return text == NULL || text[0] == '\0';
}

static bool same(const char *left, const char *right) {
    return left != NULL && right != NULL && strcmp(left, right) == 0;
}

ne_ota_decision ne_ota_should_install(const char *running_version, const char *remote_version,
                                      const char *rolled_back_version) {
    /* An unreadable version on either side decides nothing: refuse, do not guess. */
    if (empty(running_version) || empty(remote_version)) return NE_OTA_SKIP_NO_VERSION;
    if (same(running_version, remote_version)) return NE_OTA_SKIP_SAME_VERSION;
    if (!empty(rolled_back_version) && same(remote_version, rolled_back_version))
        return NE_OTA_SKIP_ROLLED_BACK;
    return NE_OTA_INSTALL;
}

const char *ne_ota_decision_reason(ne_ota_decision decision) {
    switch (decision) {
        case NE_OTA_SKIP_SAME_VERSION:
            return "same_version";
        case NE_OTA_SKIP_NO_VERSION:
            return "no_version";
        case NE_OTA_SKIP_ROLLED_BACK:
            return "rolled_back";
        case NE_OTA_INSTALL:
            break;
    }
    return "install";
}

ne_ota_boot_action ne_ota_boot_action_for(bool is_ota_partition, bool pending_verify,
                                          bool selftest_ok) {
    if (!is_ota_partition || !pending_verify) return NE_OTA_BOOT_NONE;
    return selftest_ok ? NE_OTA_BOOT_MARK_VALID : NE_OTA_BOOT_MARK_INVALID;
}

size_t ne_ota_sanitize_url(const char *url, char *out, size_t cap) {
    if (cap > 0) out[0] = '\0';
    if (url == NULL) return 0;

    const size_t length = strlen(url);
    /* Drop everything between the scheme and the '@' that ends the userinfo: the
     * last '@' before the path starts, so an '@' inside the path stays. */
    const char *scheme = strstr(url, "://");
    const char *authority = scheme != NULL ? scheme + 3 : url;
    const char *path = authority;
    while (*path != '\0' && *path != '/' && *path != '?' && *path != '#') path++;
    const char *at = NULL;
    for (const char *cursor = authority; cursor < path; cursor++) {
        if (*cursor == '@') at = cursor;
    }
    const size_t drop_from = at != NULL ? (size_t)(authority - url) : 0u;
    const size_t drop_to = at != NULL ? (size_t)(at + 1 - url) : 0u;

    size_t written = 0;
    for (size_t i = 0; i < length; i++) {
        if (i >= drop_from && i < drop_to) continue;
        if (written + 1 < cap) out[written] = url[i];
        written++;
    }
    if (cap > 0) out[written < cap ? written : cap - 1] = '\0';
    return written;
}

/* One whole line or nothing: a truncated marker must never read as a whole one. */
static bool marker(char *out, size_t cap, const char *format, ...) {
    if (out == NULL || cap == 0) return false;
    out[0] = '\0';
    va_list args;
    va_start(args, format);
    const int written = vsnprintf(out, cap, format, args);
    va_end(args);
    if (written < 0 || (size_t)written >= cap) {
        out[0] = '\0';
        return false;
    }
    return true;
}

bool ne_ota_marker_check(char *out, size_t cap, const char *url) {
    char safe[NE_OTA_LINE_MAX + 1];
    if (out == NULL || cap == 0) return false;
    out[0] = '\0';
    if (url == NULL || ne_ota_sanitize_url(url, safe, sizeof safe) >= sizeof safe) return false;
    return marker(out, cap, "NE_OTA CHECK url=%s", safe);
}

bool ne_ota_marker_downloaded(char *out, size_t cap, unsigned bytes, const char *version) {
    if (version == NULL) return false;
    return marker(out, cap, "NE_OTA DOWNLOADED bytes=%u version=%s", bytes, version);
}

bool ne_ota_marker_rejected(char *out, size_t cap, const char *reason) {
    if (reason == NULL) return false;
    return marker(out, cap, "NE_OTA REJECTED reason=%s", reason);
}

bool ne_ota_marker_switch(char *out, size_t cap, const char *partition) {
    if (partition == NULL) return false;
    return marker(out, cap, "NE_OTA SWITCH partition=%s", partition);
}

bool ne_ota_marker_valid(char *out, size_t cap, const char *partition) {
    if (partition == NULL) return false;
    return marker(out, cap, "NE_OTA VALID partition=%s", partition);
}

bool ne_ota_marker_invalid(char *out, size_t cap, const char *partition) {
    if (partition == NULL) return false;
    return marker(out, cap, "NE_OTA INVALID partition=%s", partition);
}

bool ne_ota_marker_rollback(char *out, size_t cap, const char *from, const char *to) {
    if (from == NULL || to == NULL) return false;
    return marker(out, cap, "NE_OTA ROLLBACK from=%s to=%s", from, to);
}

bool ne_ota_marker_skip(char *out, size_t cap, const char *reason, const char *version) {
    if (reason == NULL || version == NULL) return false;
    return marker(out, cap, "NE_OTA SKIP reason=%s version=%s", reason, version);
}
