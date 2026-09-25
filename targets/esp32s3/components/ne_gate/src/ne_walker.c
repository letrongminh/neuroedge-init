/*
 * NeuroEdge gate walker — see ne_walker.h. C99; every read is bounds-checked
 * and assembled byte by byte, so the layout is independent of the CPU's
 * endianness and alignment. No heap, no static or global state, no recursion.
 */
#include "ne_walker.h"

#include <string.h>

/* --- little-endian readers ------------------------------------------------------ */

static uint16_t rd16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1] << 8); }

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static double rdf64(const uint8_t *p) {
    uint64_t bits = (uint64_t)rd32(p) | (uint64_t)rd32(p + 4) << 32;
    double value;
    memcpy(&value, &bits, sizeof value); /* IEEE 754 binary64, as on host and ESP32-S3 */
    return value;
}

static int is_nan(double x) { return x != x; }

/* --- layout ------------------------------------------------------------------------ */

#define H_MAGIC 0
#define H_VERSION 4
#define H_HEADER_SIZE 6
#define H_DIGEST 8
#define H_NODE_COUNT 40
#define H_ARG_COUNT 42
#define H_ENUM_COUNT 44
#define H_ACTION 46
#define H_FAIL_OPEN 47
#define H_P95 48
#define H_CONFIRM_MASK 52
#define H_STRINGS_SIZE 56
#define H_CRC 60

#define N_KIND 0
#define N_DOMAIN_SIZE 1
#define N_NAME 2
#define N_ADMITTED 4
#define N_FLOOR 8
#define N_DOMAIN_OFF 16

#define A_NAME 0
#define A_TYPE 2
#define A_FLAGS 3
#define A_ENUM_FIRST 4
#define A_ENUM_COUNT 6
#define A_MAX_LENGTH 8
#define A_MINIMUM 16
#define A_MAXIMUM 24

#define E_NUMBER 0
#define E_STR_OFF 8
#define E_STR_LEN 12

#define F_MIN 1u
#define F_MAX 2u
#define F_ENUM 4u
#define F_MAX_LENGTH 8u

#define KIND_BOOL 0u
#define ACTION_ASK 2u

static const uint8_t *node_at(const ne_tree *t, uint32_t i) {
    return t->base + NE_HEADER_SIZE + i * NE_NODE_SIZE;
}

static const uint8_t *arg_at(const ne_tree *t, uint32_t i) {
    return t->base + NE_HEADER_SIZE + (uint32_t)t->node_count * NE_NODE_SIZE + i * NE_ARG_SIZE;
}

static const uint8_t *enum_at(const ne_tree *t, uint32_t i) {
    return t->base + NE_HEADER_SIZE + (uint32_t)t->node_count * NE_NODE_SIZE +
           (uint32_t)t->arg_count * NE_ARG_SIZE + i * NE_ENUM_SIZE;
}

static const uint8_t *strings_of(const ne_tree *t) {
    return enum_at(t, t->enum_count);
}

/* --- CRC-32 (bitwise: no table, no rodata) -------------------------------------------- */

uint32_t ne_crc32(const uint8_t *data, uint32_t len, uint32_t skip_from, uint32_t skip_len) {
    uint32_t crc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < len; i++) {
        uint8_t byte = (i >= skip_from && i - skip_from < skip_len) ? 0u : data[i];
        crc ^= byte;
        for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

/* --- load ------------------------------------------------------------------------- */

/* The offset of the NUL ending the string at `off`, or -1 if it runs off the table. */
static int32_t string_end(const uint8_t *strings, uint32_t size, uint32_t off) {
    for (uint32_t i = off; i < size; i++)
        if (strings[i] == 0) return (int32_t)i;
    return -1;
}

ne_status ne_tree_load(ne_tree *tree, const uint8_t *buf, uint32_t len) {
    if (tree == NULL || buf == NULL) return NE_ERR_ARGUMENT;
    memset(tree, 0, sizeof *tree);
    if (len < NE_HEADER_SIZE) return NE_ERR_SIZE;
    if (memcmp(buf + H_MAGIC, "NETR", 4) != 0) return NE_ERR_MAGIC;
    if (rd16(buf + H_VERSION) != NE_LAYOUT_VERSION || rd16(buf + H_HEADER_SIZE) != NE_HEADER_SIZE)
        return NE_ERR_VERSION;

    uint32_t nodes = rd16(buf + H_NODE_COUNT), args = rd16(buf + H_ARG_COUNT);
    uint32_t enums = rd16(buf + H_ENUM_COUNT), strings_size = rd32(buf + H_STRINGS_SIZE);
    if (nodes == 0 || nodes > NE_MAX_NODES || args > NE_MAX_ARGS || enums > NE_MAX_ENUMS ||
        strings_size > NE_MAX_STRINGS)
        return NE_ERR_LIMITS;
    uint32_t expected = NE_HEADER_SIZE + nodes * NE_NODE_SIZE + args * NE_ARG_SIZE +
                        enums * NE_ENUM_SIZE + strings_size;
    if (expected != len) return NE_ERR_SIZE;
    if (ne_crc32(buf, len, H_CRC, 4) != rd32(buf + H_CRC)) return NE_ERR_CRC;

    ne_tree t;
    memset(&t, 0, sizeof t);
    t.base = buf;
    t.size = len;
    t.node_count = (uint16_t)nodes;
    t.arg_count = (uint16_t)args;
    t.enum_count = (uint16_t)enums;
    t.on_block_action = buf[H_ACTION];
    t.fail_open = buf[H_FAIL_OPEN];
    t.p95_latency_ms = rd32(buf + H_P95);
    t.confirm_mask = rd32(buf + H_CONFIRM_MASK);
    t.strings_size = strings_size;
    t.gate_digest = buf + H_DIGEST;

    if (t.on_block_action > 3u || t.fail_open > 1u || t.p95_latency_ms == 0u) return NE_ERR_STRUCTURE;
    if (nodes < 32u && (t.confirm_mask >> nodes) != 0u) return NE_ERR_STRUCTURE;
    if (t.confirm_mask != 0u && t.on_block_action != ACTION_ASK) return NE_ERR_STRUCTURE;

    const uint8_t *strings = strings_of(&t);
    if (strings_size == 0u || strings[strings_size - 1u] != 0u) return NE_ERR_STRUCTURE;

    for (uint32_t i = 0; i < nodes; i++) {
        const uint8_t *n = node_at(&t, i);
        uint32_t kind = n[N_KIND], size = n[N_DOMAIN_SIZE];
        uint32_t admitted = rd32(n + N_ADMITTED);
        double floor = rdf64(n + N_FLOOR);
        if (kind > 2u || size == 0u || size > NE_MAX_DOMAIN) return NE_ERR_STRUCTURE;
        if (kind == KIND_BOOL && size != 2u) return NE_ERR_STRUCTURE;
        if (size < 32u && (admitted >> size) != 0u) return NE_ERR_STRUCTURE;
        if (is_nan(floor) || floor < 0.0 || floor > 1.0) return NE_ERR_STRUCTURE;
        if (rd16(n + N_NAME) >= strings_size) return NE_ERR_STRUCTURE;
        uint32_t off = rd16(n + N_DOMAIN_OFF);
        for (uint32_t v = 0; v < size; v++) { /* the domain's strings are consecutive */
            if (off >= strings_size) return NE_ERR_STRUCTURE;
            int32_t end = string_end(strings, strings_size, off);
            if (end < 0) return NE_ERR_STRUCTURE;
            off = (uint32_t)end + 1u;
        }
    }
    for (uint32_t i = 0; i < args; i++) {
        const uint8_t *a = arg_at(&t, i);
        uint32_t type = a[A_TYPE], flags = a[A_FLAGS];
        uint32_t first = rd16(a + A_ENUM_FIRST), count = rd16(a + A_ENUM_COUNT);
        if (type > 3u || flags > 15u || rd16(a + A_NAME) >= strings_size) return NE_ERR_STRUCTURE;
        if (first + count > enums) return NE_ERR_STRUCTURE;
        if (((flags & F_ENUM) != 0u) != (count != 0u)) return NE_ERR_STRUCTURE;
        if (is_nan(rdf64(a + A_MINIMUM)) || is_nan(rdf64(a + A_MAXIMUM))) return NE_ERR_STRUCTURE;
        for (uint32_t e = first; e < first + count; e++) {
            const uint8_t *en = enum_at(&t, e);
            if (type == NE_ARG_STRING) {
                uint32_t so = rd32(en + E_STR_OFF), sl = rd32(en + E_STR_LEN);
                if (so >= strings_size || sl >= strings_size - so) return NE_ERR_STRUCTURE;
            }
        }
    }
    *tree = t;
    return NE_OK;
}

/* --- names (for traces) ----------------------------------------------------------- */

const char *ne_criterion_name(const ne_tree *tree, uint32_t i) {
    if (tree == NULL || tree->base == NULL || i >= tree->node_count) return NULL;
    return (const char *)strings_of(tree) + rd16(node_at(tree, i) + N_NAME);
}

const char *ne_argument_name(const ne_tree *tree, uint32_t i) {
    if (tree == NULL || tree->base == NULL || i >= tree->arg_count) return NULL;
    return (const char *)strings_of(tree) + rd16(arg_at(tree, i) + A_NAME);
}

int ne_criterion_kind(const ne_tree *tree, uint32_t i) {
    if (tree == NULL || tree->base == NULL || i >= tree->node_count) return -1;
    return node_at(tree, i)[N_KIND];
}

const char *ne_domain_value(const ne_tree *tree, uint32_t i, uint32_t j) {
    if (tree == NULL || tree->base == NULL || i >= tree->node_count) return NULL;
    const uint8_t *node = node_at(tree, i);
    if (j >= node[N_DOMAIN_SIZE]) return NULL;
    /* ne_tree_load checked that the domain's strings are consecutive and terminated. */
    const uint8_t *strings = strings_of(tree);
    uint32_t off = rd16(node + N_DOMAIN_OFF);
    for (uint32_t v = 0; v < j; v++) off = (uint32_t)string_end(strings, tree->strings_size, off) + 1u;
    return (const char *)strings + off;
}

/* --- deciding ---------------------------------------------------------------------- */

static int valid_confidence(double c) { return c >= 0.0 && c <= 1.0; } /* false for NaN */

/* decision_tree._classify: NE_REASON_NONE when the fact satisfies the node. */
static ne_reason classify(const uint8_t *node, const ne_fact *fact) {
    if (fact == NULL || !fact->present) return NE_REASON_CRITERION_UNAVAILABLE;
    if (!fact->in_domain || fact->index >= node[N_DOMAIN_SIZE]) return NE_REASON_CRITERION_UNAVAILABLE;
    if (fact->has_confidence && !valid_confidence(fact->confidence))
        return NE_REASON_CRITERION_UNAVAILABLE;
    double floor = rdf64(node + N_FLOOR);
    if (floor > 0.0 && !fact->has_confidence) return NE_REASON_CONFIDENCE_UNAVAILABLE;
    uint32_t admitted = rd32(node + N_ADMITTED);
    if (((admitted >> fact->index) & 1u) == 0u || (floor > 0.0 && fact->confidence < floor))
        return NE_REASON_CONDITION_NOT_MET;
    return NE_REASON_NONE;
}

/* decision_tree.walk: the first failing criterion not in `waived`. */
static ne_reason walk(const ne_tree *t, const ne_fact *facts, uint32_t waived, uint8_t *failed) {
    for (uint32_t i = 0; i < t->node_count; i++) {
        ne_reason r = classify(node_at(t, i), facts != NULL ? &facts[i] : NULL);
        if (r != NE_REASON_NONE && ((waived >> i) & 1u) == 0u) {
            *failed = (uint8_t)i;
            return r;
        }
    }
    return NE_REASON_NONE;
}

/* UTF-8 code points, as Python's len(str). */
static uint32_t code_points(const char *s, uint32_t len) {
    uint32_t n = 0;
    for (uint32_t i = 0; i < len; i++)
        if (((uint8_t)s[i] & 0xC0u) != 0x80u) n++;
    return n;
}

/* engine/arguments.py `_is`. */
static int fits_type(uint32_t kind, const ne_arg_value *v) {
    switch (kind) {
    case NE_ARG_BOOLEAN: return v->type == NE_ARG_BOOLEAN;
    case NE_ARG_INTEGER: return v->type == NE_ARG_INTEGER;
    case NE_ARG_NUMBER: return v->type == NE_ARG_INTEGER || v->type == NE_ARG_NUMBER;
    default: return v->type == NE_ARG_STRING;
    }
}

/* engine/arguments.py `check`: 1 when argument `i` is outside its limit. */
static int argument_fails(const ne_tree *t, uint32_t i, const ne_arg_value *v) {
    const uint8_t *a = arg_at(t, i);
    uint32_t kind = a[A_TYPE], flags = a[A_FLAGS];
    if (v == NULL || !v->present) return 1;
    if (!fits_type(kind, v)) return 1;
    if (kind == NE_ARG_STRING && v->str == NULL && v->str_len != 0u) return 1;
    if (flags & F_ENUM) {
        int found = 0;
        uint32_t first = rd16(a + A_ENUM_FIRST), count = rd16(a + A_ENUM_COUNT);
        for (uint32_t e = first; e < first + count && !found; e++) {
            const uint8_t *en = enum_at(t, e);
            if (kind == NE_ARG_STRING) {
                uint32_t so = rd32(en + E_STR_OFF), sl = rd32(en + E_STR_LEN);
                found = sl == v->str_len && (sl == 0u || memcmp(strings_of(t) + so, v->str, sl) == 0);
            } else {
                found = rdf64(en + E_NUMBER) == v->number;
            }
        }
        if (!found) return 1;
    }
    if ((flags & F_MIN) && v->number < rdf64(a + A_MINIMUM)) return 1;
    if ((flags & F_MAX) && v->number > rdf64(a + A_MAXIMUM)) return 1;
    if ((flags & F_MAX_LENGTH) && code_points(v->str, v->str_len) > rd32(a + A_MAX_LENGTH)) return 1;
    return 0;
}

ne_status ne_evaluate(const ne_tree *tree, const ne_fact *facts, const ne_arg_value *args,
                      int confirmed, ne_result *out) {
    if (tree == NULL || tree->base == NULL || out == NULL) return NE_ERR_ARGUMENT;
    memset(out, 0, sizeof *out);

    /* RFC-0005: argument limits first — deterministic, before any criterion. */
    for (uint32_t i = 0; i < tree->arg_count; i++) {
        if (argument_fails(tree, i, args != NULL ? &args[i] : NULL)) {
            out->verdict = NE_BLOCK;
            out->reason = NE_REASON_ARGUMENT_OUT_OF_RANGE;
            out->failed_kind = NE_FAILED_ARGUMENT;
            out->failed_index = (uint8_t)i;
            return NE_OK;
        }
    }

    /* RFC-0006: what a person may stand in for, only for an `ask` gate. */
    uint32_t confirmable = tree->on_block_action == ACTION_ASK ? tree->confirm_mask : 0u;
    uint32_t waived = confirmed ? confirmable : 0u;
    uint8_t failed = 0;
    ne_reason reason = walk(tree, facts, waived, &failed);
    if (reason == NE_REASON_NONE) {
        out->verdict = NE_ALLOW;
        out->confirmed_mask = waived;
        return NE_OK;
    }
    out->verdict = NE_BLOCK;
    out->reason = reason;
    out->failed_kind = NE_FAILED_CRITERION;
    out->failed_index = failed;
    /* A question is offered only if a person's yes would be enough. */
    if (!confirmed && confirmable != 0u) {
        uint8_t ignored = 0;
        out->answerable = walk(tree, facts, confirmable, &ignored) == NE_REASON_NONE;
    }
    return NE_OK;
}

/* decision_tree.known_failure: the first criterion not waived whose fact is present and fails. */
static ne_reason known_failure(const ne_tree *t, const ne_fact *facts, uint32_t waived,
                               uint8_t *failed) {
    for (uint32_t i = 0; i < t->node_count; i++) {
        if (((waived >> i) & 1u) != 0u || facts == NULL || !facts[i].present) continue;
        ne_reason r = classify(node_at(t, i), &facts[i]);
        if (r != NE_REASON_NONE) {
            *failed = (uint8_t)i;
            return r;
        }
    }
    return NE_REASON_NONE;
}

ne_status ne_decide(const ne_tree *tree, const ne_fact *facts, const ne_arg_value *args,
                    int confirmed, ne_degraded degraded, ne_result *out) {
    if (degraded != NE_DEGRADED_NONE && degraded != NE_DEGRADED_UNREACHABLE &&
        degraded != NE_DEGRADED_BUDGET)
        return NE_ERR_ARGUMENT;
    ne_status status = ne_evaluate(tree, facts, args, confirmed, out);
    if (status != NE_OK || degraded == NE_DEGRADED_NONE) return status;
    /* RFC-0005: the limits decided before any source was asked. */
    if (out->reason == NE_REASON_ARGUMENT_OUT_OF_RANGE) return NE_OK;

    const ne_reason why =
        degraded == NE_DEGRADED_BUDGET ? NE_REASON_BUDGET_EXCEEDED : NE_REASON_GATE_UNREACHABLE;
    uint32_t confirmable = tree->on_block_action == ACTION_ASK ? tree->confirm_mask : 0u;
    uint32_t waived = confirmed ? confirmable : 0u;
    memset(out, 0, sizeof *out);
    if (tree->fail_open) {
        uint8_t failed = 0;
        ne_reason known = known_failure(tree, facts, waived, &failed);
        if (known != NE_REASON_NONE) { /* on_block, and no question: a person cannot answer it */
            out->verdict = NE_BLOCK;
            out->reason = known;
            out->failed_kind = NE_FAILED_CRITERION;
            out->failed_index = failed;
            return NE_OK;
        }
        out->verdict = NE_ALLOW;
        out->reason = why;
        out->fail_mode = NE_FAIL_MODE_OPEN;
        return NE_OK;
    }
    out->verdict = NE_BLOCK;
    out->reason = why;
    out->fail_mode = NE_FAIL_MODE_CLOSED;
    return NE_OK;
}
