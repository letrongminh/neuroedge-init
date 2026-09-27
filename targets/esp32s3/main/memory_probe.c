/*
 * NeuroEdge memory feasibility probe — TSK-S1-10.
 *
 * See memory_probe.h for what is measured and why. Nothing here allocates on
 * the heap: a probe that perturbed the quantity it measures would be useless,
 * and the samples array is static for the same reason.
 */
#include "memory_probe.h"

#include <inttypes.h>
#include <stdio.h>

#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_system.h"
#include "sdkconfig.h"

static const char *TAG = "neuroedge_mem";

static neuroedge_memory_sample_t s_samples[NEUROEDGE_CP_COUNT];

void neuroedge_memory_probe(neuroedge_checkpoint_t cp, const char *label)
{
    if (cp >= NEUROEDGE_CP_COUNT) {
        return;
    }

    neuroedge_memory_sample_t *sample = &s_samples[cp];
    sample->label = label;

    sample->internal_free    = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    sample->internal_largest = heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
    sample->internal_min_ever = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);

    sample->psram_free    = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    sample->psram_largest = heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM);
    sample->psram_present = (sample->psram_free > 0);

    sample->recorded = true;

    ESP_LOGI(TAG, "[%s] internal free %u B (largest %u B) | PSRAM free %u B (largest %u B)",
             label,
             (unsigned) sample->internal_free,
             (unsigned) sample->internal_largest,
             (unsigned) sample->psram_free,
             (unsigned) sample->psram_largest);
}

void neuroedge_memory_report(void)
{
    ESP_LOGI(TAG, "================ NeuroEdge memory probe (Q-3) ================");
    ESP_LOGI(TAG, "%-16s %12s %12s %12s %12s", "checkpoint",
             "int free", "int largest", "psram free", "psram large");

    for (int i = 0; i < NEUROEDGE_CP_COUNT; ++i) {
        const neuroedge_memory_sample_t *s = &s_samples[i];
        if (!s->recorded) {
            ESP_LOGW(TAG, "%-16s %12s %12s %12s %12s",
                     s->label ? s->label : "(checkpoint)",
                     "not", "reached", "-", "-");
            continue;
        }
        ESP_LOGI(TAG, "%-16s %12u %12u %12u %12u",
                 s->label,
                 (unsigned) s->internal_free,
                 (unsigned) s->internal_largest,
                 (unsigned) s->psram_free,
                 (unsigned) s->psram_largest);
    }

    ESP_LOGI(TAG, "Q-3 budget: internal SRAM >= %u B | PSRAM >= %u B | firmware <= %u B",
             (unsigned) NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES,
             (unsigned) NEUROEDGE_Q3_MIN_PSRAM_BYTES,
             (unsigned) NEUROEDGE_Q3_MAX_FIRMWARE_BYTES);
    ESP_LOGI(TAG, "Firmware size is a build-time figure; nightly CI reads it from the .bin.");
    ESP_LOGI(TAG, "==============================================================");
}

void neuroedge_memory_report_json(void)
{
    const neuroedge_memory_sample_t *final = &s_samples[NEUROEDGE_CP_AUDIO_READY];

    /* printf, not ESP_LOGI: the log prefix would have to be stripped before
     * the line could be parsed, and CI should not have to guess the format. */
    printf("NEUROEDGE_MEMORY_JSON {"
           "\"schema\":\"neuroedge.memory_spike/v1\","
           "\"board\":\"esp32s3-box-3\","
           "\"idf_version\":\"%s\","
           "\"audio_checkpoint_reached\":%s,"
           "\"internal_free_bytes\":%u,"
           "\"internal_largest_block_bytes\":%u,"
           "\"internal_min_ever_bytes\":%u,"
           "\"psram_free_bytes\":%u,"
           "\"psram_largest_block_bytes\":%u,"
           "\"q3_min_internal_sram_bytes\":%u,"
           "\"q3_min_psram_bytes\":%u,"
           "\"q3_max_firmware_bytes\":%u,"
           "\"meets_q3_runtime_budget\":%s"
           "}\n",
           esp_get_idf_version(),
           final->recorded ? "true" : "false",
           (unsigned) final->internal_free,
           (unsigned) final->internal_largest,
           (unsigned) final->internal_min_ever,
           (unsigned) final->psram_free,
           (unsigned) final->psram_largest,
           (unsigned) NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES,
           (unsigned) NEUROEDGE_Q3_MIN_PSRAM_BYTES,
           (unsigned) NEUROEDGE_Q3_MAX_FIRMWARE_BYTES,
           neuroedge_memory_meets_q3_budget() ? "true" : "false");
}

void neuroedge_memory_report_heap_json(const char *label)
{
#ifdef CONFIG_NEUROEDGE_QEMU
    const char *qemu = "true";
#else
    const char *qemu = "false";
#endif
    /* printf, not ESP_LOGI, for the same reason as NEUROEDGE_MEMORY_JSON. */
    printf("NEUROEDGE_HEAP_JSON {"
           "\"schema\":\"neuroedge.heap/v1\","
           "\"checkpoint\":\"%s\","
           "\"idf_version\":\"%s\","
           "\"qemu\":%s,"
           "\"internal_free_bytes\":%u,"
           "\"internal_largest_block_bytes\":%u,"
           "\"internal_min_ever_bytes\":%u,"
           "\"psram_free_bytes\":%u,"
           "\"q3_min_internal_sram_bytes\":%u"
           "}\n",
           label != NULL ? label : "",
           esp_get_idf_version(),
           qemu,
           (unsigned) heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
           (unsigned) heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL),
           (unsigned) heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL),
           (unsigned) heap_caps_get_free_size(MALLOC_CAP_SPIRAM),
           (unsigned) NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES);
    fflush(stdout);
}

bool neuroedge_memory_meets_q3_budget(void)
{
    const neuroedge_memory_sample_t *final = &s_samples[NEUROEDGE_CP_AUDIO_READY];

    if (!final->recorded) {
        /* The audio stack is what the spike exists to measure. Reporting a pass
         * from the pre-audio baseline would answer a different question, and
         * R-1 is rated High precisely because that answer looks reassuring. */
        ESP_LOGE(TAG, "Q-3 VERDICT: INCONCLUSIVE — the audio checkpoint was never reached.");
        ESP_LOGE(TAG, "Load AEC + VAD + Opus before calling this; the baseline is not the budget.");
        return false;
    }

    const bool sram_ok  = final->internal_free >= NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES;
    const bool psram_ok = final->psram_free >= NEUROEDGE_Q3_MIN_PSRAM_BYTES;

    ESP_LOGI(TAG, "Q-3 internal SRAM: %u B vs >= %u B -> %s",
             (unsigned) final->internal_free,
             (unsigned) NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES,
             sram_ok ? "PASS" : "FAIL");
    ESP_LOGI(TAG, "Q-3 PSRAM:         %u B vs >= %u B -> %s",
             (unsigned) final->psram_free,
             (unsigned) NEUROEDGE_Q3_MIN_PSRAM_BYTES,
             psram_ok ? "PASS" : "FAIL");

    if (!sram_ok || !psram_ok) {
        /* Q-44: voice on the chip is required for v1.0, so a miss is not a
         * scope cut: it opens a Q-N to re-plan I5 at once (TSK-S1-10). */
        ESP_LOGE(TAG, "Q-3 VERDICT: FAIL — open a Q-N to re-plan I5 now (Q-44).");
        return false;
    }

    ESP_LOGI(TAG, "Q-3 VERDICT: PASS on the runtime budget (firmware size checked at build).");
    return true;
}
