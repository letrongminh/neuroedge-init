/*
 * NeuroEdge trace lines on the UART — C99, no allocation, no globals, no recursion.
 *
 * The device writes each trace event as one line, `NE1 ` and then one
 * `trace.v1` event as JSON: {"offset_ms":..,"type":..,"data":{..}}, the same
 * event names and fields the host writes (docs/spec/simulation_coverage.md §3,
 * §4; TSK-S4-09). The host (`neuroedge record --target esp32s3 --port`, module
 * python/neuroedge/testing/uart.py) keeps these lines, drops every other log
 * line, and rebuilds a trace file that `trace validate` and `replay` accept.
 *
 * A session is framed: `device_info` first (offset 0), `trace_end {events: N}`
 * last, N = the lines of the session before it — including any this device
 * could not fit — so the host notices a lost line instead of reading a shorter
 * trace as the truth.
 *
 * Every formatter writes one whole line into the caller's buffer and returns
 * its length; 0 when there is nothing to write; -1 when the line does not fit
 * in `cap` (the buffer then holds no line). Nonces never belong in a trace.
 */
#ifndef NE_TRACE_H
#define NE_TRACE_H

#include <stddef.h>
#include <stdint.h>

#include "ne_token.h"
#include "ne_walker.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NE_TRACE_PREFIX "NE1 "
/* Longest line, prefix included, newline excluded. Buffers are NE_TRACE_LINE_MAX + 1. */
#define NE_TRACE_LINE_MAX 512u

typedef struct {
    const char *board_id;      /* "esp32s3-box-3" */
    const char *agent_version; /* "home-voice@0.1.0" */
    const char *device_id;     /* "qemu", or "esp32s3-<mac>" on the board */
    uint32_t boot_id;          /* random at boot; the host names the session after it */
    const char *replay_of;     /* NULL, or the canonical trace this session replays */
    const char *trace_digest;  /* NULL, or "sha256:<hex>" of that trace */
} ne_device_info;

/* What NETR v1 does not carry about `on_block`; NULL where the gate has none. */
typedef struct {
    const char *to;              /* escalate */
    const char *message;         /* escalate, ask */
    const char *fallback_action; /* degrade */
} ne_on_block_text;

/*
 * Where lines go. `emit` writes one line (no newline) to the UART; `now_ms`
 * is the device clock; `buf` is the application's line buffer, at least
 * NE_TRACE_LINE_MAX + 1 bytes (a static in the application, or a task's stack).
 * The sink helpers number the lines of one session and compute `offset_ms`.
 */
typedef struct {
    void (*emit)(void *ctx, const char *line);
    uint32_t (*now_ms)(void *ctx);
    void *ctx;
    char *buf;
    size_t cap;
    uint32_t t0_ms;
    uint32_t lines;   /* lines of the session so far, dropped ones included */
    uint32_t dropped; /* lines that did not fit */
} ne_trace_sink;

/* --- formatters ---------------------------------------------------------------------- */

int ne_trace_device_info(char *buf, size_t cap, const ne_device_info *info);

/* {gate, gate_digest}: `gate` is the compiled label, "light_on@1.0.0". */
int ne_trace_gate_begin(char *buf, size_t cap, uint32_t offset_ms, const char *gate,
                        const ne_tree *tree);

/*
 * {criterion: {value, confidence, source}} for every present fact — the inputs
 * of the verdict, which a replay feeds back in. `sources` has one entry per
 * node, or is NULL: every fact is "context". A value outside the domain is
 * written as null (it reads as unavailable, on the host as here). 0 when no
 * fact is present, as the host writes no `gate_facts` then.
 */
int ne_trace_gate_facts(char *buf, size_t cap, uint32_t offset_ms, const ne_tree *tree,
                        const ne_fact *facts, const char *const *sources);

/*
 * The verdict with the keys of the host's `GateResult.to_event_data()`:
 * verdict, reason, evaluations, blocked_by + action on a BLOCK, failed_criterion,
 * the `on_block` texts, confirmed. `text` may be NULL.
 */
int ne_trace_gate_result(char *buf, size_t cap, uint32_t offset_ms, const char *gate,
                         const ne_tree *tree, const ne_fact *facts, const ne_result *result,
                         const ne_on_block_text *text);

/* {pin, operation, duration_ms}: what the device drove, after the token allowed it. */
int ne_trace_actuator_command(char *buf, size_t cap, uint32_t offset_ms, const char *pin,
                              const char *operation, uint32_t duration_ms);

/* {pin, reason, code}: the token ledger refused the pin (NE1001 / NE1002). */
int ne_trace_actuator_rejected(char *buf, size_t cap, uint32_t offset_ms, const char *pin,
                               ne_token_reason reason);

int ne_trace_end(char *buf, size_t cap, uint32_t offset_ms, uint32_t events);

/* "condition_not_met", ... as python/neuroedge/engine/verdict.py `Reason`; NULL for none. */
const char *ne_reason_name(ne_reason reason);
/* "deny", "escalate", "ask", "degrade"; NULL when out of range. */
const char *ne_on_block_name(uint32_t action);

/* --- sink helpers -------------------------------------------------------------------- */

/* Start a session: resets the counters, then writes `device_info` at offset 0. */
void ne_trace_open(ne_trace_sink *sink, const ne_device_info *info);
/* Milliseconds since `ne_trace_open`, wrap-safe. */
uint32_t ne_trace_offset(const ne_trace_sink *sink);
/* Count the line a formatter just wrote into `sink->buf` and write it: `len` > 0
 * writes, -1 counts it as dropped, 0 is nothing. */
void ne_trace_put(ne_trace_sink *sink, int len);
/* End the session with `trace_end {events: lines so far}`. */
void ne_trace_close(ne_trace_sink *sink);

#ifdef __cplusplus
}
#endif

#endif /* NE_TRACE_H */
