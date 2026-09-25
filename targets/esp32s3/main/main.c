/*
 * NeuroEdge runtime entry point — ESP32-S3-BOX-3.
 *
 * Sprint 1 scope is the memory feasibility spike (TSK-S1-10), so what runs
 * here is the probe harness: bring up the subsystems whose footprint the agent
 * runtime cannot avoid, sampling free memory at each step, then report against
 * the Q-3 budget.
 *
 * Per decision Q-9 (option A) the device never evaluates CEL: `neuroedge
 * build` compiles gates into a flat decision tree (NETR v1, RFC-0003) on the
 * workstation and the firmware only walks it (components/ne_gate). Before any
 * network comes up, a boot self-test runs the walker and the single-use token
 * ledger on the home-voice gates linked into flash, and prints one line the
 * QEMU job greps for (TSK-S4-02, TSK-S4-08). A failed self-test stops here:
 * no gate runtime, no action.
 *
 * The self-test's gate evaluations also go out as `NE1` trace lines, framed as
 * one session (components/ne_trace, TSK-S4-09); `NE_TRACE DONE` follows the
 * last session, so a reader knows the device has nothing more to say.
 * `neuroedge record --target esp32s3 --port <uart>` turns them into trace files.
 *
 * CONFIG_NEUROEDGE_SKIP_NETWORK (sdkconfig.qemu) leaves the Wi-Fi stack out:
 * QEMU does not emulate it.
 */
#include <stdio.h>
#include <string.h>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"

#include "gate_selftest.h"
#include "gates/home_voice_indices.h"
#include "memory_probe.h"
#include "ne_trace.h"

/* The reference board, fixed by Q-1/Q-2; the only board this image is built for. */
#define NEUROEDGE_BOARD_ID "esp32s3-box-3"

static const char *TAG = "neuroedge_core";

/* One trace line to the UART: printf, not ESP_LOGI, so the line has no log prefix. */
static void uart_line(void *ctx, const char *line)
{
    (void)ctx;
    printf("%s\n", line);
}

static uint32_t uptime_ms(void *ctx)
{
    (void)ctx;
    return (uint32_t)(esp_timer_get_time() / 1000);
}

/* The application's trace line buffer: a static here, never in the components. */
static char s_trace_line[NE_TRACE_LINE_MAX + 1];

/* "qemu" under sdkconfig.qemu, so emulated evidence never reads as the board's. */
static void device_id(char *out, size_t cap)
{
#ifdef CONFIG_NEUROEDGE_QEMU
    snprintf(out, cap, "qemu");
#else
    uint8_t mac[6] = {0};
    esp_efuse_mac_get_default(mac);
    snprintf(out, cap, "esp32s3-%02x%02x%02x%02x%02x%02x", mac[0], mac[1], mac[2], mac[3],
             mac[4], mac[5]);
#endif
}

static void init_nvs(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
}

/*
 * Bring up the network stack without associating to an AP.
 *
 * The footprint that matters for Q-3 is the static cost of the TCP/IP and
 * Wi-Fi stacks, which is incurred at init. Measuring before init would
 * overstate the memory available to the agent by tens of kilobytes, and
 * overstating it is the failure mode R-1 warns about.
 */
#ifndef CONFIG_NEUROEDGE_SKIP_NETWORK
static void init_network_stack(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&config));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
}
#endif

/*
 * Walker + token ledger on the gates in flash, traced as one session. The
 * result line goes to the UART as is, after the session.
 */
static bool run_gate_selftest(uint32_t boot_id)
{
    char line[96];
    char id[24];
    ne_trace_sink sink = {uart_line, uptime_ms, NULL, s_trace_line, sizeof s_trace_line, 0, 0, 0};
    device_id(id, sizeof id);
    const ne_device_info info = {NEUROEDGE_BOARD_ID, NE_AGENT_VERSION, id, boot_id, NULL, NULL};

    ne_trace_open(&sink, &info);
    const int failed = neuroedge_gate_selftest(esp_fill_random, boot_id, uptime_ms(NULL), line,
                                               sizeof line, &sink);
    ne_trace_close(&sink);
    printf("%s\n", line);
    fflush(stdout);
    return failed == 0;
}

void app_main(void)
{
    ESP_LOGI(TAG, "==================================================");
    ESP_LOGI(TAG, "NeuroEdge memory feasibility spike (TSK-S1-10)");
    ESP_LOGI(TAG, "Board: ESP32-S3-BOX-3 · reference board fixed by Q-1/Q-2");
    ESP_LOGI(TAG, "==================================================");

    neuroedge_memory_probe(NEUROEDGE_CP_BOOT, "boot");

    init_nvs();
    neuroedge_memory_probe(NEUROEDGE_CP_NVS_READY, "nvs_ready");

    const uint32_t boot_id = esp_random();
    if (!run_gate_selftest(boot_id)) {
        ESP_LOGE(TAG, "gate self-test failed: the gate runtime is not trusted, stopping");
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(10000));
        }
    }
    printf("NE_TRACE DONE sessions=1\n");
    fflush(stdout);

#ifdef CONFIG_NEUROEDGE_SKIP_NETWORK
    ESP_LOGW(TAG, "network skipped (CONFIG_NEUROEDGE_SKIP_NETWORK): network_ready not measured");
#else
    init_network_stack();
    neuroedge_memory_probe(NEUROEDGE_CP_NETWORK_READY, "network_ready");
#endif

    /*
     * TODO(TSK-S1-10, V2): load the audio stack and take the AUDIO_READY
     * checkpoint. This is the measurement the spike exists to produce:
     *
     *   1. esp-sr AEC (AFE) instance, 16 kHz, two mic channels (ES7210)
     *   2. VAD instance
     *   3. Opus encoder, 16 kHz mono, plus the PSRAM ring buffer
     *   4. neuroedge_memory_probe(NEUROEDGE_CP_AUDIO_READY, "audio_ready");
     *
     * Until that checkpoint is taken, neuroedge_memory_meets_q3_budget()
     * deliberately reports INCONCLUSIVE rather than passing on the baseline.
     * The components need vendoring and a licence review first (§3.9); the
     * checkpoints above the audio line are already real measurements and are
     * useful on their own as the floor the audio stack has to fit inside.
     */

    neuroedge_memory_report();
    neuroedge_memory_report_json();

    const bool within_budget = neuroedge_memory_meets_q3_budget();
    ESP_LOGI(TAG, "Spike complete. Q-3 runtime budget met: %s",
             within_budget ? "yes" : "NO / inconclusive");

    /* Idle rather than return: returning from app_main tears down the task and
     * the serial monitor would lose the report on some IDF versions. */
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}
