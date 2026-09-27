/*
 * NeuroEdge memory feasibility probe — TSK-S1-10.
 *
 * The memory spike has to produce a NUMBER, not an opinion (roadmap §4.4, I3).
 * This header defines the measurement so the same checkpoints are taken on
 * every run, by every engineer, and so nightly CI can diff them over time.
 *
 * Thresholds are fixed by decision Q-3 and must not be edited to make a run
 * pass; changing them is a roadmap decision, not a code change.
 */
#pragma once

#include <stdbool.h>
#include <stddef.h>

/* Decision Q-3 — the budget the spike is measured against. */
#define NEUROEDGE_Q3_MIN_INTERNAL_SRAM_BYTES (120 * 1024)   /* >= 120 KB for the app   */
#define NEUROEDGE_Q3_MIN_PSRAM_BYTES         (2 * 1024 * 1024) /* >= 2 MB for audio     */
#define NEUROEDGE_Q3_MAX_FIRMWARE_BYTES      (3670016)       /* <= 3.5 MB per A/B slot  */

/* Checkpoints, taken in this order. Each one is a point at which memory has
 * been consumed by a subsystem we cannot remove, so the remainder is what the
 * agent runtime actually gets to use. */
typedef enum {
    NEUROEDGE_CP_BOOT = 0,        /* immediately in app_main                         */
    NEUROEDGE_CP_NVS_READY,       /* after NVS init (provisioning + credentials)     */
    NEUROEDGE_CP_NETWORK_READY,   /* after the TCP/IP + Wi-Fi stack is up            */
    NEUROEDGE_CP_AUDIO_READY,     /* after AEC + VAD + Opus are loaded — the spike   */
    NEUROEDGE_CP_COUNT
} neuroedge_checkpoint_t;

typedef struct {
    const char *label;
    size_t internal_free;         /* MALLOC_CAP_INTERNAL free bytes                  */
    size_t internal_largest;      /* largest contiguous internal block               */
    size_t internal_min_ever;     /* internal low-water mark since boot              */
    size_t psram_free;            /* MALLOC_CAP_SPIRAM free bytes                    */
    size_t psram_largest;         /* largest contiguous PSRAM block                  */
    bool   psram_present;         /* false when PSRAM failed to initialise           */
    bool   recorded;              /* false when the checkpoint was never reached     */
} neuroedge_memory_sample_t;

/* Take one sample and store it under `cp`. Safe to call before PSRAM init. */
void neuroedge_memory_probe(neuroedge_checkpoint_t cp, const char *label);

/* Human-readable table of every recorded checkpoint. */
void neuroedge_memory_report(void);

/*
 * One machine-readable line per run, prefixed NEUROEDGE_MEMORY_JSON:
 * nightly CI greps for that prefix and appends the payload to the spike
 * report, so the measurement is captured without a human transcribing it.
 */
void neuroedge_memory_report_json(void);

/*
 * One machine-readable line of the free heap right now, prefixed
 * NEUROEDGE_HEAP_JSON (schema neuroedge.heap/v1, TSK-S4-11). The QEMU jobs parse
 * it (scripts/check_firmware_size.py --heap-log): internal SRAM free at `label`
 * must already clear the Q-3 floor, since the network and the audio stack only
 * take more. It is a floor check, never the Q-3 verdict: QEMU has no PSRAM, no
 * Wi-Fi and no I2S, so the verdict stays with neuroedge_memory_meets_q3_budget().
 */
void neuroedge_memory_report_heap_json(const char *label);

/*
 * Compare the final checkpoint against Q-3. Returns true only when every
 * runtime threshold is met. Fails loudly when the audio checkpoint was never
 * reached, because an unmeasured budget must never read as a pass.
 */
bool neuroedge_memory_meets_q3_budget(void);
