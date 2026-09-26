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

#include "esp_app_desc.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "sdkconfig.h"

#if CONFIG_NEUROEDGE_OTA
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs.h"
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

static const char *TAG = "ne_ota";

/* NVS override for the update URL: namespace ne_ota, key url (docs/user/nap-firmware.md). */
#define NE_OTA_NVS_NAMESPACE "ne_ota"
#define NE_OTA_NVS_KEY "url"

static bool s_pending_verify;                /* this image booted awaiting verification */
static char s_running_partition[16];         /* "factory", "ota_0", "ota_1" */
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
        if (esp_ota_get_state_partition(candidate, &state) != ESP_OK) continue;
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
    s_running_partition[0] = '\0';
    s_running_version[0] = '\0';
    s_rolled_back_version[0] = '\0';

    const esp_partition_t *running = esp_ota_get_running_partition();
    if (running == NULL) return; /* unreachable: an app is running */
    copy_bounded(s_running_partition, sizeof s_running_partition, running->label);

    if (running->subtype != ESP_PARTITION_SUBTYPE_APP_FACTORY) {
        esp_ota_img_states_t state;
        if (esp_ota_get_state_partition(running, &state) == ESP_OK) {
            s_pending_verify = state == ESP_OTA_IMG_PENDING_VERIFY || state == ESP_OTA_IMG_NEW;
        }
    }

    const esp_app_desc_t *desc = esp_app_get_description();
    if (desc != NULL) copy_bounded(s_running_version, sizeof s_running_version, desc->version);

    const esp_partition_t *invalid = aborted_partition(running);
    if (invalid == NULL) return;
    esp_app_desc_t broken;
    if (esp_ota_get_partition_description(invalid, &broken) == ESP_OK) {
        copy_bounded(s_rolled_back_version, sizeof s_rolled_back_version, broken.version);
    } else {
        s_rolled_back_unknown = true;
    }
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_rollback(line, sizeof line, invalid->label, running->label)) emit(line);
}

void ne_ota_boot_confirmed(void) {
    if (!s_pending_verify) return; /* factory, or already valid: nothing to mark */
    const esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err != ESP_OK) {
        /* No VALID marker: a boot that could not be confirmed must not read as one. */
        ESP_LOGE(TAG, "could not mark %s valid: %s", s_running_partition, esp_err_to_name(err));
        return;
    }
    s_pending_verify = false;
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_valid(line, sizeof line, s_running_partition)) emit(line);
}

void ne_ota_boot_rejected(void) {
    if (!s_pending_verify) return; /* factory: the caller stops the gate runtime itself */
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

/* The URL: NVS (provisioning) overrides the Kconfig value; empty disables OTA. */
static bool configured_url(char *out, size_t cap) {
    size_t length = cap;
    nvs_handle_t handle;
    if (nvs_open(NE_OTA_NVS_NAMESPACE, NVS_READONLY, &handle) == ESP_OK) {
        const esp_err_t err = nvs_get_str(handle, NE_OTA_NVS_KEY, out, &length);
        nvs_close(handle);
        if (err == ESP_OK && length > 1u) return true; /* length includes the NUL */
    }
    const char *fallback = CONFIG_NEUROEDGE_OTA_URL;
    length = strlen(fallback);
    if (length + 1u > cap) return false;
    if (length > 0u) memcpy(out, fallback, length + 1u);
    else out[0] = '\0';
    return length > 0u;
}

static void reject(const char *reason) {
    char line[NE_OTA_LINE_MAX + 1];
    if (ne_ota_marker_rejected(line, sizeof line, reason)) {
        emit(line);
    } else {
        ESP_LOGE(TAG, "update refused (%s) and the REJECTED marker did not fit", reason);
    }
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
    if (!configured_url(url, sizeof url)) return; /* empty: OTA is off (the default) */

    /* An aborted slot whose version cannot be read blocks every update rather
     * than re-installing the image that just failed. */
    if (s_rolled_back_unknown) {
        if (ne_ota_marker_skip(line, sizeof line, "rolled_back", "?")) emit(line);
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

    esp_app_desc_t remote;
    memset(&remote, 0, sizeof remote);
    err = esp_https_ota_get_img_desc(handle, &remote);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "no app descriptor at the URL: %s", esp_err_to_name(err));
        esp_https_ota_abort(handle);
        reject("descriptor");
        return;
    }

    const ne_ota_decision decision =
        ne_ota_should_install(s_running_version, remote.version, s_rolled_back_version);
    if (decision != NE_OTA_INSTALL) {
        esp_https_ota_abort(handle);
        if (ne_ota_marker_skip(line, sizeof line, ne_ota_decision_reason(decision), remote.version))
            emit(line);
        return;
    }

    while ((err = esp_https_ota_perform(handle)) == ESP_ERR_HTTPS_OTA_IN_PROGRESS) {
    }
    if (err != ESP_OK) {
        esp_https_ota_abort(handle);
        reject(err == ESP_ERR_OTA_VALIDATE_FAILED ? "signature" : "download");
        return;
    }
    if (!esp_https_ota_is_complete_data_received(handle)) {
        esp_https_ota_abort(handle);
        reject("incomplete");
        return;
    }
    const int read = esp_https_ota_get_image_len_read(handle);
    const unsigned bytes = read > 0 ? (unsigned)read : 0u;

    err = esp_https_ota_finish(handle); /* verifies (signature included), then sets boot */
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_https_ota_finish: %s", esp_err_to_name(err));
        reject(err == ESP_ERR_OTA_VALIDATE_FAILED ? "signature" : "verify");
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
