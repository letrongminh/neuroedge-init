/*
 * The canonical traces, replayed on the device (TSK-S4-09).
 *
 * For each trace in fixtures/traces/ (generated into vectors/ by
 * scripts/gen_firmware_vectors.py) the firmware writes one `NE1` session whose
 * `device_info` names the trace it replays (`replay_of`, `trace_digest`). Each
 * step gets exactly the inputs `neuroedge replay` feeds the host engine — the
 * recorded facts, the recorded degraded gathering, a person's confirmation —
 * and computes the rest itself: the verdict (`ne_decide`), the token (the C
 * ledger), and whether each command of the action's table is driven. No GPIO
 * moves: a replayed `actuator_command` says the ledger allowed that pin.
 * `neuroedge verify --targets esp32s3 --port <uart>` compares the sessions with
 * the canonical traces as golden references.
 *
 * Pure C99 with no ESP-IDF dependency, so python/tests/test_trace_vectors.py
 * also runs it on the host.
 */
#ifndef NEUROEDGE_TRACE_VECTORS_H
#define NEUROEDGE_TRACE_VECTORS_H

#include <stdint.h>

#include "ne_token.h"
#include "ne_trace.h"
#include "ne_walker.h"

#ifdef __cplusplus
extern "C" {
#endif

/* One pin command of an action, as the host's action table records it. */
typedef struct {
    const char *pin;
    uint8_t pin_index; /* bit of the token's pin mask */
    const char *operation;
    uint32_t duration_ms;
} ne_vector_command;

/* A gate as the vectors hold it: the tree in flash, its label and on_block texts. */
typedef struct {
    const char *label;
    const uint8_t *tree;
    uint32_t tree_size;
    ne_on_block_text text;
} ne_vector_gate;

typedef struct {
    uint8_t gate;               /* index into the vectors' gates */
    uint8_t degraded;           /* ne_degraded, as recorded */
    uint8_t confirmed;          /* a person's "có" was recorded (RFC-0006) */
    const ne_fact *facts;       /* one per node */
    const char *const *sources; /* one per node */
    uint32_t pin_mask;          /* the action's pins: what its token may drive */
    const ne_vector_command *commands;
    uint8_t command_count;
} ne_vector_step;

typedef struct {
    const char *replay_of;    /* "happy-path.json" */
    const char *trace_digest; /* "sha256:…" of that trace */
    const char *agent_version;
    const ne_vector_step *steps;
    uint8_t step_count;
} ne_vector;

/*
 * Replay every vector as one session on `sink`, `device` giving board and
 * device id. `ledger` is the caller's (re-initialised for each vector, with
 * `boot_id`). Returns the number of sessions written, or -1 when a vector could
 * not be replayed — its session is then left without `trace_end`, which the
 * host reports instead of reading a shorter trace.
 */
int neuroedge_trace_vectors(ne_trace_sink *sink, const ne_device_info *device, ne_ledger *ledger,
                            ne_random_fn fill_random, uint32_t boot_id);

#ifdef __cplusplus
}
#endif

#endif /* NEUROEDGE_TRACE_VECTORS_H */
