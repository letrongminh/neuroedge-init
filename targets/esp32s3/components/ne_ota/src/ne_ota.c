/*
 * The OTA component's ESP-IDF side: partitions, the network, esp_https_ota
 * (ne_ota.h holds the order main.c uses). What is decided without ESP-IDF —
 * install or not, mark valid or roll back, marker text, URL sanitising — lives
 * in ne_ota_policy.c and is driven on the host.
 *
 * A failed update never switches: `esp_https_ota_finish` verifies the image
 * (including the RSA signature, CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT)
 * before `esp_ota_set_boot_partition` runs, and every error path aborts the
 * esp_https_ota handle or lets it free itself (begin does on failure). The
 * only reboot this component asks for is after a complete, verified image was
 * made the boot partition.
 */
#include "ne_ota.h"

#include <stdio.h>
#include <string.h>

/* Everything the boot path uses is included outside the OTA guard: the marks
 * and the rollback state are read and written on every boot, OTA or not
 * (test_ota_includes.py keeps this from regressing). */
#include "esp_app_desc.h"
#include "esp_err.h"
#include "esp_image_format.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_system.h"
#include "nvs.h"
#include "sdkconfig.h"

#if CONFIG_NEUROEDGE_OTA
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#if CONFIG_MBEDTLS_CERTIFICATE_BUNDLE
#include "esp_crt_bundle.h"
#endif
#endif

#if CONFIG_NEUROEDGE_OTA && CONFIG_NEUROEDGE_OTA_ETH
#include "esp_eth.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_eth_mac_openeth.h"
#include "freertos/event_groups.h"
#endif

/*
 * The update URL, the high-water mark and the rolled-back version live in one
 * NVS namespace (docs/user/nap-firmware.md). Turning OTA on without the two
 * guarantees it is built around — every image verified, every new image
 * verified by its own self-test before it may stay — would be a downgrade
 * attack with extra steps, so it is a build error, not a default.
 */
#if CONFIG_NEUROEDGE_OTA && !(CONFIG_SECURE_SIGNED_ON_UPDATE && CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE)
#error "NEUROEDGE_OTA requires signature verification on update and app rollback: build with sdkconfig.ota (CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y, CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y)"
#endif

static const char *TAG = "ne_ota";

#define NE_OTA_NVS_NAMESPACE "ne_ota"
#define NE_OTA_NVS_URL "url"      /* string; an empty value disables OTA */
#define NE_OTA_NVS_BEST "best"    /* string; newest version confirmed by its self-test */
#define NE_OTA_NVS_ROLLBACK "rollback" /* string; the version last rolled back from */

static bool s_pending_verify;                /* this image booted awaiting verification */
static bool s_is_ota;                        /* running from an OTA slot (not factory) */
static char s_running_partition[16];         /* "factory", "ota_0", "ota_1" */
static char s_high_water[NE_OTA_VERSION_MAX]; /* newest confirmed version, or empty */
static bool s_high_water_unknown;            /* a mark exists but cannot be read */
static char s_running_version[NE_OTA_VERSION_MAX];
static char s_rolled_back_version[NE_OTA_VERSION_MAX]; /* empty: no aborted slot */
static bool s_rolled_back_unknown;           /* aborted slot exists, its version unreadable */

static void emit(const char *line) {
    printf("%s\n", line);
    fflush(stdout);
}

static void copy_bounded(char *out, size_t cap, const char *text) {
    if (out == NULL || cap == 0) return;
    if (text == NULL) {
        out[0] = '\0';
        return;
    }
    size_t length = strlen(text);
    if (length >= cap) length = cap - 1;
    memcpy(out, text, length);
    out[length] = '\0';
}

/* One string from NVS: false when absent; *unreadable when present but not a
 * readable string (wrong type, too long, a corrupt page) — the caller then
 * refuses, not guesses. Only ESP_ERR_NVS_NOT_FOUND means absent: reading a
 * damaged namespace as "no mark" would silently drop downgrade protection. */
static bool nvs_read(const char *key, char *out, size_t cap, bool *unreadable) {
    *unreadable = false;
    out[0] = '\0';
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NE_OTA_NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        if (err != ESP_ERR_NVS_NOT_FOUND) *unreadable = true;
        return false;
    }
    size_t length = cap;
    err = nvs_get_str(handle, key, out, &length);
    nvs_close(handle);
    if (err == ESP_OK) return true;
    if (err != ESP_ERR_NVS_NOT_FOUND) *unreadable = true;
    return false;
}

/* Best-effort: a mark that cannot be written only loses future protection. */
static void nvs_write(const char *key, const char *value) {
    nvs_handle_t handle;
    if (nvs_open(NE_OTA_NVS_NAMESPACE, NVS_READWRITE, &handle) != ESP_OK) {
        ESP_LOGE(TAG, "cannot open NVS to record %s", key);
        return;
    }
    const esp_err_t err = nvs_set_str(handle, key, value);
    if (err == ESP_OK) {
        const esp_err_t commit = nvs_commit(handle);
        if (commit != ESP_OK) ESP_LOGE(TAG, "NVS commit of %s: %s", key, esp_err_to_name(commit));
    } else {
        ESP_LOGE(TAG, "NVS write of %s: %s", key, esp_err_to_name(err));
    }
    nvs_close(handle);
}

/* Whether the slot's bytes are a complete image (structure and, with
 * signature-on-update, its signature) — the aborted state alone only says the
 * image was selected once; the descriptor of a half-written one lies. */
static bool slot_holds_valid_image(const esp_partition_t *partition) {
    if (partition == NULL) return false;
    esp_image_metadata_t metadata;
    const esp_partition_pos_t pos = {.offset = partition->address, .size = partition->size};
    return esp_image_verify(ESP_IMAGE_VERIFY_SILENT, &pos, &metadata) == ESP_OK;
}

/*
 * The slot that was abandoned, read from otadata alone.
 *
 * `esp_ota_get_last_invalid_partition()` validates the image first, and a
 * corrupt image — a common reason a slot was abandoned at all — then reads as
 * "no rollback happened", which would let the device re-install the very
 * version it rolled back from. The state is the fact; the bytes need not be
 * readable for the device to know it must not go back there.
 */
static const esp_partition_t *aborted_partition(const esp_partition_t *running) {
    const esp_partition_t *found = NULL;
    for (int subtype = ESP_PARTITION_SUBTYPE_APP_OTA_0; subtype < ESP_PARTITION_SUBTYPE_APP_OTA_MAX;
         subtype++) {
        const esp_partition_t *candidate = esp_partition_find_first(
            ESP_PARTITION_TYPE_APP, (esp_partition_subtype_t)subtype, NULL);
        if (candidate == NULL) continue;
        if (running != NULL && candidate->address == running->address) continue;
        esp_ota_img_states_t state;
        const esp_err_t state_err = esp_ota_get_state_partition(candidate, &state);
        if (state_err == ESP_ERR_NOT_FOUND) continue; /* no otadata entry: fine */
        if (state_err != ESP_OK) {
            /* Not knowing this slot's state is not "it is fine": without it the
             * device cannot tell which version it must not go back to, so no
             * update is allowed this boot (NE_OTA SKIP reason=rolled_back). */
            s_rolled_back_unknown = true;
            continue;
        }
        if (state != ESP_OTA_IMG_INVALID && state != ESP_OTA_IMG_ABORTED) continue;
        if (found != NULL) {
            /* Two abandoned slots: no single version to blame. */
            s_rolled_back_unknown = true;
            continue;
        }
        found = candidate;
    }
    return found;
}

void ne_ota_boot(void) {
    s_pending_verify = false;
    s_rolled_back_unknown = false;
    s_high_water_unknown = false;
    s_is_ota = false;
    s_running_partition[0] = '\0';
    s_running_version[0] = '\0';
    s_rolled_back_version[0] = '\0';
    s_high_water[0] = '\0';

    const esp_partition_t *running = esp_ota_get_running_partition();
    if (running == NULL) return; /* unreachable: an app is running */
    copy_bounded(s_running_partition, sizeof s_running_partition, running->label);
    s_is_ota = running->subtype != ESP_PARTITION_SUBTYPE_APP_FACTORY;

    if (s_is_ota) {
        esp_ota_img_states_t state;
        if (esp_ota_get_state_partition(running, &state) == ESP_OK) {
            s_pending_verify = state == ESP_OTA_IMG_PENDING_VERIFY || state == ESP_OTA_IMG_NEW;
        }
    }

    const esp_app_desc_t *desc = esp_app_get_description();
    if (desc != NULL) copy_bounded(s_running_version, sizeof s_running_version, desc->version);

    /* The high-water mark: what must be beaten to be installed at all. */
    bool unreadable = false;
    if (nvs_read(NE_OTA_NVS_BEST, s_high_water, sizeof s_high_water, &unreadable)) {
        uint32_t mark[3];
        if (!ne_ota_parse_version(s_high_water, mark)) s_high_water_unknown = true;
    } else if (unreadable) {
        s_high_water_unknown = true;
        s_high_water[0] = '\0';
    }

    /*
     * Repair the mark from the running image. A confirmed image records its
     * version when it is confirmed, but that NVS write can fail or lose power
     * before it commits: without this repair the device could later accept an
     * image below the version it is already running. Only a mark that is
     * absent or readable-but-lower may rise — an unreadable one could have
     * been higher, and lowering it is the downgrade it exists to stop.
     */
    if (!s_pending_verify && !s_high_water_unknown &&
        ne_ota_mark_should_rise(s_running_version, s_high_water)) {
        nvs_write(NE_OTA_NVS_BEST, s_running_version);
        copy_bounded(s_high_water, sizeof s_high_water, s_running_version);
    }

    /* The version the device last rolled back from: the slot's own descriptor
     * when it can be read, else the value recorded when the rollback was first
     * seen — an interrupted later write over that slot must not block every
     * future update. */
    const esp_partition_t *invalid = aborted_partition(running);
    if (invalid == NULL) return;
    char from_slot[NE_OTA_VERSION_MAX] = {0};
    esp_app_desc_t broken;
    bool slot_valid = false;
    if (slot_holds_valid_image(invalid) &&
        esp_ota_get_partition_description(invalid, &broken) == ESP_OK) {
        copy_bounded(from_slot, sizeof from_slot, broken.version);
        slot_valid = true;
    }
    char stored[NE_OTA_VERSION_MAX] = {0};
    bool stored_unreadable = false;
    nvs_read(NE_OTA_NVS_ROLLBACK, stored, sizeof stored, &stored_unreadable);
    if (ne_ota_resolve_rollback(stored, from_slot, slot_valid, s_rolled_back_version,
                                sizeof s_rolled_back_version)) {
        /* The record may only be replaced by a complete, valid image: a
         * truncated write over the slot still answers with a descriptor, and
         * it must not un-ban the version that actually bootlooped. */
        if (slot_valid && strcmp(stored, from_slot) != 0)
            nvs_write(NE_OTA_NVS_ROLLBACK, from_slot);
    } else {
        s_rolled_back_unknown = true;
    }
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_rollback(line, sizeof line, invalid->label, running->label)) emit(line);
}

void ne_ota_boot_confirmed(void) {
    if (ne_ota_boot_action_for(s_is_ota, s_pending_verify, true) != NE_OTA_BOOT_MARK_VALID) return;
    const esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err != ESP_OK) {
        /* No VALID marker: a boot that could not be confirmed must not read as
         * one. Fail closed — if a rollback is possible, reboot and let the
         * bootloader take this image back to the previous one; only when no
         * rollback exists is a self-test-passing image better than none. */
        ESP_LOGE(TAG, "could not mark %s valid: %s", s_running_partition, esp_err_to_name(err));
        if (esp_ota_check_rollback_is_possible()) {
            ESP_LOGE(TAG, "rolling back instead of running unconfirmed");
            esp_restart();
        }
        return;
    }
    s_pending_verify = false;
    /* The mark rises only here: a version counts once its self-test passed
     * (and from a running confirmed image at boot — see ne_ota_boot). */
    if (ne_ota_mark_should_rise(s_running_version, s_high_water)) {
        nvs_write(NE_OTA_NVS_BEST, s_running_version);
        copy_bounded(s_high_water, sizeof s_high_water, s_running_version);
        s_high_water_unknown = false; /* written: the same boot need not refuse */
    }
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_valid(line, sizeof line, s_running_partition)) emit(line);
}

void ne_ota_boot_rejected(void) {
    if (ne_ota_boot_action_for(s_is_ota, s_pending_verify, false) != NE_OTA_BOOT_MARK_INVALID)
        return; /* factory: the caller stops the gate runtime itself */
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_invalid(line, sizeof line, s_running_partition)) emit(line);
    ESP_LOGE(TAG, "self-test failed on a pending image: marking %s invalid and rolling back",
             s_running_partition);
    const esp_err_t err = esp_ota_mark_app_invalid_rollback_and_reboot();
    /* Only a failure returns. The caller must then stop the gate runtime. */
    ESP_LOGE(TAG, "could not mark %s invalid (%s): rollback needs a reboot that did not "
                  "happen; stopping instead of running an unverified image",
             s_running_partition, esp_err_to_name(err));
}

#if CONFIG_NEUROEDGE_OTA

/*
 * The URL: NVS (provisioning) overrides the Kconfig value. 1 when set, 0 when
 * absent (fall back to Kconfig) or empty in Kconfig (OTA off), -1 when the NVS
 * value exists but cannot be used — an empty NVS url disables OTA rather than
 * resurrecting the Kconfig one, and a wrong-typed or over-long value is
 * refused, never guessed at.
 */
static int configured_url(char *out, size_t cap) {
    bool unreadable = false;
    char stored[NE_OTA_LINE_MAX + 1] = {0};
    if (nvs_read(NE_OTA_NVS_URL, stored, sizeof stored, &unreadable)) {
        if (stored[0] == '\0') {
            out[0] = '\0';
            return 0; /* provisioned off */
        }
        size_t length = strlen(stored);
        if (length + 1u > cap) return -1;
        memcpy(out, stored, length + 1u);
        return 1;
    }
    if (unreadable) return -1;
    const char *fallback = CONFIG_NEUROEDGE_OTA_URL;
    const size_t length = strlen(fallback);
    if (length + 1u > cap) return -1;
    if (length > 0u) memcpy(out, fallback, length + 1u);
    else out[0] = '\0';
    return length > 0u ? 1 : 0;
}

/* An image that failed verification must never be bootable: erase the written
 * slot's first sector so a later fallback cannot even start it. */
static void erase_slot(const char *reason, const esp_partition_t *target) {
    if (target == NULL) return;
    const esp_err_t err = esp_partition_erase_range(target, 0, target->erase_size);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "could not erase %s after %s: %s", target->label, reason,
                 esp_err_to_name(err));
        return;
    }
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_erased(line, sizeof line, target->label)) emit(line);
}

static void reject(const char *reason) {
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_rejected(line, sizeof line, reason)) {
        emit(line);
    } else {
        ESP_LOGE(TAG, "update refused (%s) and the REJECTED marker did not fit", reason);
    }
}

/* A refusal and the cleanup that must follow it, in one place: an image that
 * failed verification must never be bootable, and the order (REJECTED, then
 * ERASED) is part of what the scripts read. */
static void refuse(const char *reason, const esp_partition_t *target) {
    reject(reason);
    erase_slot(reason, target);
}

#if CONFIG_NEUROEDGE_OTA_ETH
#define NE_OTA_IP_BIT BIT0

static EventGroupHandle_t s_ip_event;

static void on_eth_got_ip(void *arg, esp_event_base_t base, int32_t id, void *data) {
    (void)arg;
    (void)base;
    (void)id;
    (void)data;
    xEventGroupSetBits(s_ip_event, NE_OTA_IP_BIT);
}

/*
 * QEMU's open_eth (sdkconfig.qemu_ota). On the board the Wi-Fi stack main.c
 * brings up is used instead; this path is never compiled into a board layer.
 */
static bool eth_up(void) {
    esp_err_t err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "esp_netif_init: %s", esp_err_to_name(err));
        return false;
    }
    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "esp_event_loop_create_default: %s", esp_err_to_name(err));
        return false;
    }
    esp_netif_t *netif = esp_netif_new(&(esp_netif_config_t)ESP_NETIF_DEFAULT_ETH());
    if (netif == NULL) {
        ESP_LOGE(TAG, "esp_netif_new(ETH) returned NULL");
        return false;
    }
    eth_mac_config_t mac_config = ETH_MAC_DEFAULT_CONFIG();
    eth_phy_config_t phy_config = ETH_PHY_DEFAULT_CONFIG();
    esp_eth_mac_t *mac = esp_eth_mac_new_openeth(&mac_config);
    esp_eth_phy_t *phy = esp_eth_phy_new_dp83848(&phy_config);
    if (mac == NULL || phy == NULL) {
        ESP_LOGE(TAG, "open_eth MAC/PHY: %s (is CONFIG_ETH_USE_OPENETH on?)",
                 mac == NULL ? "no MAC" : "no PHY");
        if (mac != NULL) mac->del(mac);
        if (phy != NULL) phy->del(phy);
        esp_netif_destroy(netif);
        return false;
    }
    esp_eth_handle_t handle = NULL;
    err = esp_eth_driver_install(&(esp_eth_config_t)ETH_DEFAULT_CONFIG(mac, phy), &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_eth_driver_install: %s", esp_err_to_name(err));
        mac->del(mac);
        phy->del(phy);
        esp_netif_destroy(netif);
        return false;
    }
    esp_eth_netif_glue_handle_t glue = esp_eth_new_netif_glue(handle);
    if (glue == NULL) {
        ESP_LOGE(TAG, "esp_eth_new_netif_glue returned NULL");
        esp_eth_driver_uninstall(handle);
        esp_netif_destroy(netif);
        return false;
    }
    err = esp_netif_attach(netif, glue);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_netif_attach: %s", esp_err_to_name(err));
        esp_eth_del_netif_glue(glue);
        esp_eth_driver_uninstall(handle);
        esp_netif_destroy(netif);
        return false;
    }

    s_ip_event = xEventGroupCreate();
    if (s_ip_event == NULL) {
        ESP_LOGE(TAG, "xEventGroupCreate returned NULL");
        esp_eth_del_netif_glue(glue);
        esp_eth_driver_uninstall(handle);
        esp_netif_destroy(netif);
        return false;
    }
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_ETH_GOT_IP, on_eth_got_ip, NULL));
    err = esp_eth_start(handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_eth_start: %s", esp_err_to_name(err));
        esp_event_handler_unregister(IP_EVENT, IP_EVENT_ETH_GOT_IP, on_eth_got_ip);
        vEventGroupDelete(s_ip_event);
        s_ip_event = NULL;
        esp_eth_del_netif_glue(glue);
        esp_eth_driver_uninstall(handle);
        esp_netif_destroy(netif);
        return false;
    }
    const EventBits_t bits = xEventGroupWaitBits(s_ip_event, NE_OTA_IP_BIT, pdFALSE, pdTRUE,
                                                 pdMS_TO_TICKS(15000));
    esp_event_handler_unregister(IP_EVENT, IP_EVENT_ETH_GOT_IP, on_eth_got_ip);
    vEventGroupDelete(s_ip_event);
    s_ip_event = NULL;
    if ((bits & NE_OTA_IP_BIT) == 0) {
        ESP_LOGE(TAG, "no DHCP address within 15 s");
        return false;
    }
    return true;
}
#endif /* CONFIG_NEUROEDGE_OTA_ETH */

void ne_ota_run(void) {
    char line[NE_OTA_LINE_MAX + 1];
    char url[NE_OTA_LINE_MAX + 1];
    const int url_state = configured_url(url, sizeof url);
    if (url_state < 0) {
        reject("nvs");
        return;
    }
    if (url_state == 0) return; /* absent and unset, or provisioned empty: OTA off */

    /* Both facts a decision needs must be readable: the version the device
     * rolled back from, and the mark it must beat. Blocking is the only safe
     * answer when either is unknown. */
    if (s_rolled_back_unknown) {
        if (ne_ota_marker_skip(line, sizeof line, "rolled_back", "?")) emit(line);
        return;
    }
    if (s_high_water_unknown) {
        reject("nvs");
        return;
    }
    /* A URL too long to report is a URL the operator cannot see; refuse it. */
    if (!ne_ota_marker_check(line, sizeof line, url)) {
        reject("url");
        return;
    }
    emit(line);

#if CONFIG_NEUROEDGE_OTA_ETH
    if (!eth_up()) {
        reject("network");
        return;
    }
#endif

    const esp_partition_t *target = esp_ota_get_next_update_partition(NULL);
    if (target == NULL) {
        reject("no_partition");
        return;
    }

    esp_http_client_config_t http = {
        .url = url,
        .timeout_ms = CONFIG_NEUROEDGE_OTA_HTTP_TIMEOUT_MS,
        .keep_alive_enable = false,
        /* A redirect is a second server the signature does not cover being
         * trusted by name; refuse it (checked below). */
        .disable_auto_redirect = true,
#if CONFIG_MBEDTLS_CERTIFICATE_BUNDLE
        /* HTTPS validates the server against the CA bundle; plain HTTP needs
         * none of this — the signature is the integrity check either way. */
        .crt_bundle_attach = esp_crt_bundle_attach,
#endif
    };
    esp_https_ota_config_t config = {
        .http_config = &http,
    };
    esp_https_ota_handle_t handle = NULL;
    esp_err_t err = esp_https_ota_begin(&config, &handle);
    if (err != ESP_OK) {
        /* begin frees its own handle on failure: nothing to abort here */
        ESP_LOGE(TAG, "esp_https_ota_begin: %s", esp_err_to_name(err));
        reject("http");
        return;
    }

    const int status = esp_https_ota_get_status_code(handle);
    const char *status_reason = ne_ota_status_reason(status);
    if (status_reason != NULL) {
        ESP_LOGE(TAG, "HTTP status %d refused (%s)", status, status_reason);
        esp_https_ota_abort(handle);
        reject(status_reason);
        return;
    }

    esp_app_desc_t remote;
    memset(&remote, 0, sizeof remote);
    err = esp_https_ota_get_img_desc(handle, &remote);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "no app descriptor at the URL: %s", esp_err_to_name(err));
        esp_https_ota_abort(handle);
        reject("descriptor");
        return;
    }

    const ne_ota_decision decision = ne_ota_should_install(
        s_running_version, remote.version, s_rolled_back_version, s_high_water);
    if (decision != NE_OTA_INSTALL) {
        esp_https_ota_abort(handle);
        if (ne_ota_marker_skip(line, sizeof line, ne_ota_decision_reason(decision), remote.version))
            emit(line);
        return;
    }

    /* A stalled server must not hang the gate runtime forever: a total
     * deadline and a no-progress limit, both checked between reads. */
    const uint32_t started_ms = (uint32_t)(esp_timer_get_time() / 1000);
    uint32_t last_progress_ms = started_ms;
    int last_read = -1;
    while ((err = esp_https_ota_perform(handle)) == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
        const int read = esp_https_ota_get_image_len_read(handle);
        const uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);
        if (read != last_read) {
            last_read = read;
            last_progress_ms = now_ms;
        }
        if (ne_ota_download_timed_out(now_ms, started_ms, last_progress_ms,
                                      CONFIG_NEUROEDGE_OTA_DOWNLOAD_TIMEOUT_MS,
                                      CONFIG_NEUROEDGE_OTA_STALL_TIMEOUT_MS)) {
            ESP_LOGE(TAG, "download stalled after %d bytes", read);
            esp_https_ota_abort(handle);
            refuse("timeout", target);
            return;
        }
    }
    if (err != ESP_OK) {
        esp_https_ota_abort(handle);
        if (err == ESP_ERR_OTA_VALIDATE_FAILED) {
            refuse("signature", target);
        } else {
            /* Bytes may already be in the slot; leave nothing bootable. */
            refuse("download", target);
        }
        return;
    }
    if (!esp_https_ota_is_complete_data_received(handle)) {
        esp_https_ota_abort(handle);
        refuse("incomplete", target);
        return;
    }
    const int read = esp_https_ota_get_image_len_read(handle);
    const unsigned bytes = read > 0 ? (unsigned)read : 0u;

    err = esp_https_ota_finish(handle); /* verifies (signature included), then sets boot */
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota_finish: %s", esp_err_to_name(err));
        if (err == ESP_ERR_OTA_VALIDATE_FAILED) {
            reject("signature");
            erase_slot("signature", target);
        } else {
            erase_slot("verify", target);
            reject("verify");
        }
        return;
    }

    if (ne_ota_marker_downloaded(line, sizeof line, bytes, remote.version)) emit(line);
    if (ne_ota_marker_switch(line, sizeof line, target->label)) emit(line);
    ESP_LOGI(TAG, "rebooting into %s (version %s)", target->label, remote.version);
    vTaskDelay(pdMS_TO_TICKS(100)); /* let the UART drain before the reset */
    esp_restart();
}

#else /* !CONFIG_NEUROEDGE_OTA */

void ne_ota_run(void) {
    /* OTA is not compiled in (CONFIG_NEUROEDGE_OTA=n): an unsigned developer
     * build that cannot fetch, and so cannot accept, anything. */
}

#endif /* CONFIG_NEUROEDGE_OTA */
