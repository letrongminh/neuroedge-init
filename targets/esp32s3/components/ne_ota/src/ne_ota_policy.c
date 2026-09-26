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

bool ne_ota_parse_version(const char *text, uint32_t out[3]) {
    if (out == NULL) return false;
    out[0] = out[1] = out[2] = 0u;
    if (empty(text)) return false;
    const char *cursor = text;
    for (int part = 0; part < 3; part++) {
        if (*cursor < '0' || *cursor > '9') return false;
        if (*cursor == '0' && cursor[1] >= '0' && cursor[1] <= '9') return false; /* no 01 */
        uint32_t value = 0u;
        while (*cursor >= '0' && *cursor <= '9') {
            if (value > (0xFFFFFFFFu - (uint32_t)(*cursor - '0')) / 10u) return false;
            value = value * 10u + (uint32_t)(*cursor - '0');
            cursor++;
        }
        out[part] = value;
        if (part < 2) {
            if (*cursor != '.') return false;
            cursor++;
        }
    }
    return *cursor == '\0';
}

int ne_ota_compare_versions(const uint32_t left[3], const uint32_t right[3]) {
    for (int part = 0; part < 3; part++) {
        if (left[part] != right[part]) return left[part] < right[part] ? -1 : 1;
    }
    return 0;
}

ne_ota_decision ne_ota_should_install(const char *running_version, const char *remote_version,
                                      const char *rolled_back_version,
                                      const char *high_water_version) {
    /* An unreadable version on either side decides nothing: refuse, do not guess. */
    if (empty(running_version) || empty(remote_version)) return NE_OTA_SKIP_NO_VERSION;
    uint32_t running[3], remote[3];
    if (!ne_ota_parse_version(running_version, running) ||
        !ne_ota_parse_version(remote_version, remote))
        return NE_OTA_SKIP_BAD_VERSION;
    /* Parse first, compare numbers: "0.3" and "0.3.0" are the same version,
     * and a string compare would let the known-bad one back in. */
    if (ne_ota_compare_versions(running, remote) == 0) return NE_OTA_SKIP_SAME_VERSION;
    if (!empty(rolled_back_version)) {
        uint32_t banned[3];
        if (!ne_ota_parse_version(rolled_back_version, banned)) return NE_OTA_SKIP_BAD_VERSION;
        if (ne_ota_compare_versions(remote, banned) == 0) return NE_OTA_SKIP_ROLLED_BACK;
    }
    if (!empty(high_water_version)) {
        uint32_t mark[3];
        /* A mark that cannot be read refuses everything: a downgrade is worse. */
        if (!ne_ota_parse_version(high_water_version, mark)) return NE_OTA_SKIP_BAD_VERSION;
        if (ne_ota_compare_versions(remote, mark) <= 0) return NE_OTA_SKIP_DOWNGRADE;
    }
    return NE_OTA_INSTALL;
}

bool ne_ota_mark_should_rise(const char *running, const char *mark) {
    uint32_t running_parts[3];
    if (!ne_ota_parse_version(running, running_parts)) return false;
    uint32_t mark_parts[3];
    if (empty(mark)) return true;
    if (!ne_ota_parse_version(mark, mark_parts)) return false;
    return ne_ota_compare_versions(running_parts, mark_parts) > 0;
}

bool ne_ota_resolve_rollback(const char *stored, const char *from_slot, bool slot_valid, char *out,
                             size_t cap) {
    if (out == NULL || cap == 0) return false;
    out[0] = '\0';
    bool use_slot = slot_valid && !empty(from_slot);
    const char *source = use_slot ? from_slot : (!empty(stored) ? stored : NULL);
    if (source == NULL) return false;
    size_t length = strlen(source);
    if (length >= cap) length = cap - 1;
    memcpy(out, source, length);
    out[length] = '\0';
    return true;
}

const char *ne_ota_status_reason(int status) {
    return status >= 300 && status < 400 ? "redirect" : NULL;
}

bool ne_ota_download_timed_out(uint32_t now_ms, uint32_t started_ms, uint32_t last_progress_ms,
                               uint32_t total_ms, uint32_t stall_ms) {
    return (uint32_t)(now_ms - started_ms) >= total_ms ||
           (uint32_t)(now_ms - last_progress_ms) >= stall_ms;
}

const char *ne_ota_decision_reason(ne_ota_decision decision) {
    switch (decision) {
        case NE_OTA_SKIP_SAME_VERSION:
            return "same_version";
        case NE_OTA_SKIP_NO_VERSION:
            return "no_version";
        case NE_OTA_SKIP_ROLLED_BACK:
            return "rolled_back";
        case NE_OTA_SKIP_DOWNGRADE:
            return "downgrade";
        case NE_OTA_SKIP_BAD_VERSION:
            return "bad_version";
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
    /* A query string or fragment may carry a secret of its own: never log it. */
    const char *query = strpbrk(path, "?#");
    const size_t keep = query != NULL ? (size_t)(query - url) : length;

    size_t written = 0;
    for (size_t i = 0; i < keep; i++) {
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

bool ne_ota_marker_erased(char *out, size_t cap, const char *partition) {
    if (partition == NULL) return false;
    return marker(out, cap, "NE_OTA ERASED partition=%s", partition);
}
