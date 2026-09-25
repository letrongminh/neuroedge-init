/*
 * NeuroEdge trace lines — see ne_trace.h. C99; every write is bounded by the
 * caller's buffer and by NE_TRACE_LINE_MAX. No heap, no static or global
 * state, no recursion.
 */
#include "ne_trace.h"

#include <float.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* --- a bounded JSON writer ---------------------------------------------------------- */

typedef struct {
    char *buf;
    size_t cap;
    size_t len;
    int full; /* the line did not fit: nothing is written */
} writer;

static void w_init(writer *w, char *buf, size_t cap) {
    w->buf = buf;
    w->cap = cap;
    w->len = 0;
    w->full = buf == NULL || cap == 0u;
    if (!w->full) buf[0] = '\0';
}

static void w_bytes(writer *w, const char *s, size_t n) {
    if (w->full) return;
    if (n >= w->cap - w->len || w->len + n > NE_TRACE_LINE_MAX) { /* room for the NUL */
        w->full = 1;
        return;
    }
    memcpy(w->buf + w->len, s, n);
    w->len += n;
    w->buf[w->len] = '\0';
}

static void w_raw(writer *w, const char *s) { w_bytes(w, s, strlen(s)); }

static void w_char(writer *w, char c) { w_bytes(w, &c, 1u); }

/* A JSON string, or null. Bytes >= 0x80 (UTF-8) pass through as they are. */
static void w_str(writer *w, const char *s) {
    const char *hex = "0123456789abcdef";
    if (s == NULL) {
        w_raw(w, "null");
        return;
    }
    w_char(w, '"');
    for (const unsigned char *p = (const unsigned char *)s; *p != 0u && !w->full; p++) {
        if (*p == '"' || *p == '\\') {
            char esc[2] = {'\\', (char)*p};
            w_bytes(w, esc, sizeof esc);
        } else if (*p < 0x20u) {
            char esc[6] = {'\\', 'u', '0', '0', hex[*p >> 4], hex[*p & 15u]};
            w_bytes(w, esc, sizeof esc);
        } else {
            w_char(w, (char)*p);
        }
    }
    w_char(w, '"');
}

static void w_u32(writer *w, uint32_t v) {
    char tmp[12];
    snprintf(tmp, sizeof tmp, "%" PRIu32, v);
    w_raw(w, tmp);
}

/* The shortest decimal that reads back as `d`, as Python's json writes floats. */
static void w_number(writer *w, double d) {
    char tmp[32];
    if (d != d || d > DBL_MAX || d < -DBL_MAX) { /* NaN and infinities are not JSON */
        w_raw(w, "null");
        return;
    }
    for (int precision = 1; precision <= 17; precision++) {
        snprintf(tmp, sizeof tmp, "%.*g", precision, d);
        if (strtod(tmp, NULL) == d) break;
    }
    w_raw(w, tmp);
}

static void w_digest(writer *w, const uint8_t *digest) {
    const char *hex = "0123456789abcdef";
    char text[7 + 2 * NE_DIGEST_SIZE + 1];
    memcpy(text, "sha256:", 7u);
    for (uint32_t i = 0; i < NE_DIGEST_SIZE; i++) {
        text[7u + 2u * i] = hex[digest[i] >> 4];
        text[8u + 2u * i] = hex[digest[i] & 15u];
    }
    text[sizeof text - 1u] = '\0';
    w_str(w, text);
}

/* `"key":`, with the comma an object needs before every key but its first. */
static void w_key(writer *w, int *count, const char *key) {
    if ((*count)++ > 0) w_char(w, ',');
    w_str(w, key);
    w_char(w, ':');
}

static void w_event(writer *w, uint32_t offset_ms, const char *type) {
    w_raw(w, NE_TRACE_PREFIX "{\"offset_ms\":");
    w_u32(w, offset_ms);
    w_raw(w, ",\"type\":");
    w_str(w, type);
    w_raw(w, ",\"data\":{");
}

static int w_done(writer *w) {
    w_raw(w, "}}");
    if (w->full) {
        if (w->buf != NULL && w->cap != 0u) w->buf[0] = '\0';
        return -1;
    }
    return (int)w->len;
}

static int w_refuse(writer *w) {
    if (w->buf != NULL && w->cap != 0u) w->buf[0] = '\0';
    return -1;
}

/* --- vocabulary --------------------------------------------------------------------- */

const char *ne_reason_name(ne_reason reason) {
    switch (reason) {
    case NE_REASON_CONDITION_NOT_MET: return "condition_not_met";
    case NE_REASON_CRITERION_UNAVAILABLE: return "criterion_unavailable";
    case NE_REASON_CONFIDENCE_UNAVAILABLE: return "confidence_unavailable";
    case NE_REASON_ARGUMENT_OUT_OF_RANGE: return "argument_out_of_range";
    case NE_REASON_GATE_UNREACHABLE: return "gate_unreachable";
    case NE_REASON_BUDGET_EXCEEDED: return "budget_exceeded";
    case NE_REASON_NONE:
    default: return NULL;
    }
}

const char *ne_on_block_name(uint32_t action) {
    switch (action) {
    case 0u: return "deny";
    case 1u: return "escalate";
    case 2u: return "ask";
    case 3u: return "degrade";
    default: return NULL;
    }
}

/* A fact's value as JSON, as decision_tree._classify returns it; null if unknown. */
static void w_value(writer *w, const ne_tree *tree, uint32_t i, const ne_fact *fact) {
    const char *value = fact->in_domain ? ne_domain_value(tree, i, fact->index) : NULL;
    if (value == NULL) {
        w_raw(w, "null");
    } else if (ne_criterion_kind(tree, i) == NE_KIND_BOOL) {
        w_raw(w, value); /* "true" / "false" as JSON literals */
    } else {
        w_str(w, value);
    }
}

static int valid_confidence(double c) { return c >= 0.0 && c <= 1.0; } /* false for NaN */

/* The value the host records in `evaluations`: present, in the domain, sane confidence. */
static int evaluated(const ne_tree *tree, uint32_t i, const ne_fact *fact) {
    if (fact == NULL || !fact->present || !fact->in_domain) return 0;
    if (ne_domain_value(tree, i, fact->index) == NULL) return 0;
    return !fact->has_confidence || valid_confidence(fact->confidence);
}

/* --- formatters --------------------------------------------------------------------- */

int ne_trace_device_info(char *buf, size_t cap, const ne_device_info *info) {
    writer w;
    int n = 0;
    char boot[9];
    w_init(&w, buf, cap);
    if (info == NULL) return w_refuse(&w);
    snprintf(boot, sizeof boot, "%08" PRIx32, info->boot_id);
    w_event(&w, 0u, "device_info");
    w_key(&w, &n, "board_id");
    w_str(&w, info->board_id);
    w_key(&w, &n, "agent_version");
    w_str(&w, info->agent_version);
    w_key(&w, &n, "device_id");
    w_str(&w, info->device_id);
    w_key(&w, &n, "boot_id");
    w_str(&w, boot);
    if (info->replay_of != NULL) {
        w_key(&w, &n, "replay_of");
        w_str(&w, info->replay_of);
    }
    if (info->trace_digest != NULL) {
        w_key(&w, &n, "trace_digest");
        w_str(&w, info->trace_digest);
    }
    return w_done(&w);
}

int ne_trace_gate_begin(char *buf, size_t cap, uint32_t offset_ms, const char *gate,
                        const ne_tree *tree) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    if (gate == NULL || tree == NULL || tree->base == NULL) return w_refuse(&w);
    w_event(&w, offset_ms, "gate_evaluation_begin");
    w_key(&w, &n, "gate");
    w_str(&w, gate);
    w_key(&w, &n, "gate_digest");
    w_digest(&w, tree->gate_digest);
    return w_done(&w);
}

int ne_trace_gate_facts(char *buf, size_t cap, uint32_t offset_ms, const ne_tree *tree,
                        const ne_fact *facts, const char *const *sources) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    if (tree == NULL || tree->base == NULL) return w_refuse(&w);
    if (facts == NULL) return 0;
    w_event(&w, offset_ms, "gate_facts");
    for (uint32_t i = 0; i < tree->node_count; i++) {
        const ne_fact *fact = &facts[i];
        if (!fact->present) continue;
        int m = 0;
        w_key(&w, &n, ne_criterion_name(tree, i));
        w_char(&w, '{');
        w_key(&w, &m, "value");
        if (fact->has_confidence && !(fact->confidence == fact->confidence))
            w_raw(&w, "null"); /* NaN confidence: unavailable, as on the device */
        else
            w_value(&w, tree, i, fact);
        w_key(&w, &m, "confidence");
        if (fact->has_confidence)
            w_number(&w, fact->confidence);
        else
            w_raw(&w, "null");
        w_key(&w, &m, "source");
        w_str(&w, sources != NULL && sources[i] != NULL ? sources[i] : "context");
        w_char(&w, '}');
    }
    if (n == 0) {
        w_refuse(&w);
        return 0;
    }
    return w_done(&w);
}

/* The criteria a person stood in for, sorted by name as the host writes them. */
static void w_confirmed(writer *w, const ne_tree *tree, uint32_t mask) {
    const char *previous = NULL;
    int n = 0;
    w_char(w, '[');
    for (uint32_t k = 0; k < tree->node_count; k++) {
        const char *next = NULL;
        for (uint32_t i = 0; i < tree->node_count && i < 32u; i++) {
            if (((mask >> i) & 1u) == 0u) continue;
            const char *name = ne_criterion_name(tree, i);
            if (previous != NULL && strcmp(name, previous) <= 0) continue;
            if (next == NULL || strcmp(name, next) < 0) next = name;
        }
        if (next == NULL) break;
        if (n++ > 0) w_char(w, ',');
        w_str(w, next);
        previous = next;
    }
    w_char(w, ']');
}

int ne_trace_gate_result(char *buf, size_t cap, uint32_t offset_ms, const char *gate,
                         const ne_tree *tree, const ne_fact *facts, const ne_result *result,
                         const ne_on_block_text *text) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    if (gate == NULL || tree == NULL || tree->base == NULL || result == NULL) return w_refuse(&w);
    const int block = result->verdict == NE_BLOCK;
    /* A degraded verdict applies `fail`, not `on_block` (Q-17): closed is a plain deny. */
    const int closed = result->fail_mode == NE_FAIL_MODE_CLOSED;
    const int degraded = result->reason == NE_REASON_GATE_UNREACHABLE ||
                         result->reason == NE_REASON_BUDGET_EXCEEDED;
    const char *action = closed ? "deny" : ne_on_block_name(tree->on_block_action);
    w_event(&w, offset_ms, "gate_evaluation_result");
    w_key(&w, &n, "verdict");
    w_str(&w, block ? "BLOCK" : "ALLOW");
    if (result->fail_mode != NE_FAIL_MODE_NONE) {
        w_key(&w, &n, "fail_mode");
        w_str(&w, closed ? "closed" : "open");
    }
    if (ne_reason_name(result->reason) != NULL) {
        w_key(&w, &n, "reason");
        w_str(&w, ne_reason_name(result->reason));
    }
    /* No evaluations after a degraded gathering; an argument refusal decides before
     * any fact, so the host records them empty. */
    if (!degraded) {
        w_key(&w, &n, "evaluations");
        w_char(&w, '{');
        if (result->failed_kind != NE_FAILED_ARGUMENT) {
            int m = 0;
            for (uint32_t i = 0; facts != NULL && i < tree->node_count; i++) {
                if (!evaluated(tree, i, &facts[i])) continue;
                w_key(&w, &m, ne_criterion_name(tree, i));
                w_value(&w, tree, i, &facts[i]);
            }
        }
        w_char(&w, '}');
    }
    if (block) {
        w_key(&w, &n, "blocked_by");
        w_str(&w, gate);
        w_key(&w, &n, "action");
        w_str(&w, action);
    }
    if (block && !closed) {
        const char *failed = result->failed_kind == NE_FAILED_ARGUMENT
                                 ? ne_argument_name(tree, result->failed_index)
                                 : ne_criterion_name(tree, result->failed_index);
        if (result->failed_kind != NE_FAILED_NONE && failed != NULL) {
            w_key(&w, &n, "failed_criterion");
            w_str(&w, failed);
        }
        if (text != NULL && tree->on_block_action == 1u && text->to != NULL) {
            w_key(&w, &n, "escalated_to");
            w_str(&w, text->to);
        }
        if (text != NULL && (tree->on_block_action == 1u || tree->on_block_action == 2u) &&
            text->message != NULL) {
            w_key(&w, &n, "message");
            w_str(&w, text->message);
        }
        if (text != NULL && tree->on_block_action == 3u && text->fallback_action != NULL) {
            w_key(&w, &n, "fallback_action");
            w_str(&w, text->fallback_action);
        }
    }
    if (result->confirmed_mask != 0u) {
        w_key(&w, &n, "confirmed");
        w_confirmed(&w, tree, result->confirmed_mask);
    }
    return w_done(&w);
}

int ne_trace_actuator_command(char *buf, size_t cap, uint32_t offset_ms, const char *pin,
                              const char *operation, uint32_t duration_ms) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    if (pin == NULL || operation == NULL) return w_refuse(&w);
    w_event(&w, offset_ms, "actuator_command");
    w_key(&w, &n, "pin");
    w_str(&w, pin);
    w_key(&w, &n, "operation");
    w_str(&w, operation);
    w_key(&w, &n, "duration_ms");
    w_u32(&w, duration_ms);
    return w_done(&w);
}

int ne_trace_actuator_rejected(char *buf, size_t cap, uint32_t offset_ms, const char *pin,
                               ne_token_reason reason) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    if (pin == NULL || reason == NE_TOKEN_AUTHORIZED) return w_refuse(&w);
    w_event(&w, offset_ms, "actuator_command_rejected");
    w_key(&w, &n, "pin");
    w_str(&w, pin);
    w_key(&w, &n, "reason");
    w_str(&w, ne_token_reason_name(reason));
    w_key(&w, &n, "code");
    w_str(&w, ne_token_reason_code(reason));
    return w_done(&w);
}

int ne_trace_end(char *buf, size_t cap, uint32_t offset_ms, uint32_t events) {
    writer w;
    int n = 0;
    w_init(&w, buf, cap);
    w_event(&w, offset_ms, "trace_end");
    w_key(&w, &n, "events");
    w_u32(&w, events);
    return w_done(&w);
}

/* --- sink helpers ------------------------------------------------------------------- */

void ne_trace_open(ne_trace_sink *sink, const ne_device_info *info) {
    if (sink == NULL) return;
    sink->t0_ms = sink->now_ms != NULL ? sink->now_ms(sink->ctx) : 0u;
    sink->lines = 0u;
    sink->dropped = 0u;
    ne_trace_put(sink, ne_trace_device_info(sink->buf, sink->cap, info));
}

uint32_t ne_trace_offset(const ne_trace_sink *sink) {
    if (sink == NULL || sink->now_ms == NULL) return 0u;
    return (uint32_t)(sink->now_ms(sink->ctx) - sink->t0_ms);
}

void ne_trace_put(ne_trace_sink *sink, int len) {
    if (sink == NULL || len == 0) return;
    sink->lines++;
    if (len < 0) {
        sink->dropped++;
        return;
    }
    if (sink->emit != NULL) sink->emit(sink->ctx, sink->buf);
}

void ne_trace_close(ne_trace_sink *sink) {
    if (sink == NULL) return;
    const int len = ne_trace_end(sink->buf, sink->cap, ne_trace_offset(sink), sink->lines);
    if (len > 0 && sink->emit != NULL) sink->emit(sink->ctx, sink->buf);
}
