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
 * workstation and the firmware only walks it (components/ne_gate). The agent
 * is one generated component, components/ne_agent/ (`neuroedge build --target
 * esp32s3`, TSK-I3-01; the one checked in here is the home-voice sample's).
 * Before any network comes up, a boot self-test decides the agent's checks with
 * the walker and runs each action's token through the single-use ledger, and
 * prints one line the QEMU jobs grep for (TSK-S4-02, TSK-S4-08). A failed
 * self-test stops here: no gate runtime, no action.
 *
 * The self-test's gate evaluations also go out as `NE1` trace lines, framed as
 * one session (components/ne_trace, TSK-S4-09). Then the device replays the
 * canonical traces, one session each (trace_vectors.c): its own verdicts and
 * token decisions on the recorded inputs, which `neuroedge verify --targets
 * esp32s3 --port <uart>` compares with the golden references. `NE_TRACE DONE`
 * follows the last session, so a reader knows the device has nothing more to say;
 * the line before it is the free heap at that point (NEUROEDGE_HEAP_JSON, TSK-S4-11).
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
#include "memory_probe.h"
#include "ne_agent.h"
#include "ne_trace.h"
#include "trace_vectors.h"

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

/* The application's trace line buffer and vector ledger: statics here, never in the components. */
static char s_trace_line[NE_TRACE_LINE_MAX + 1];
static ne_ledger s_vector_ledger;

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
static bool run_gate_selftest(ne_trace_sink *sink, const ne_device_info *info)
{
    char line[96];
    ne_trace_open(sink, info);
    const int failed = neuroedge_gate_selftest(&ne_agent_linked, esp_fill_random, info->boot_id,
                                               uptime_ms(NULL), line, sizeof line, sink);
    ne_trace_close(sink);
    printf("%s\n", line);
    fflush(stdout);
    return failed == 0;
}

void app_main(void)
{
    ESP_LOGI(TAG, "==================================================");
    ESP_LOGI(TAG, "NeuroEdge memory feasibility spike (TSK-S1-10)");
    ESP_LOGI(TAG, "Board: ESP32-S3-BOX-3 · reference board fixed by Q-1/Q-2");
    ESP_LOGI(TAG, "Agent: %s · %u gate(s), %u action(s), %u pin(s)", ne_agent_linked.version,
             (unsigned)ne_agent_linked.gate_count, (unsigned)ne_agent_linked.action_count,
             (unsigned)ne_agent_linked.pin_count);
    ESP_LOGI(TAG, "==================================================");

    neuroedge_memory_probe(NEUROEDGE_CP_BOOT, "boot");

    init_nvs();
    neuroedge_memory_probe(NEUROEDGE_CP_NVS_READY, "nvs_ready");

    char id[24];
    device_id(id, sizeof id);
    ne_trace_sink sink = {uart_line, uptime_ms, NULL, s_trace_line, sizeof s_trace_line, 0, 0, 0};
    const ne_device_info info = {NE_AGENT_BOARD, NE_AGENT_VERSION, id, esp_random(), NULL, NULL};
    if (!run_gate_selftest(&sink, &info)) {
        ESP_LOGE(TAG, "gate self-test failed: the gate runtime is not trusted, stopping");
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(10000));
        }
    }
    int sessions = 1;
#ifdef CONFIG_NEUROEDGE_REPLAY_VECTORS
    const int replayed = neuroedge_trace_vectors(&sink, &info, &s_vector_ledger, esp_fill_random,
                                                 info.boot_id);
    if (replayed < 0) ESP_LOGE(TAG, "replaying the canonical traces failed");
    sessions += replayed > 0 ? replayed : 0;
#endif
    /* Before NE_TRACE DONE, which a reader stops at: the free heap once the gate runtime is
     * up, before the network and the audio stack (TSK-S4-11). A floor, not the Q-3 figure. */
    neuroedge_memory_report_heap_json("gate_runtime_ready");
    printf("NE_TRACE DONE sessions=%d\n", sessions);
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
