/*
 * NeuroEdge brain bridge — see ne_brain_bridge.h. C99, no allocation, no globals, no recursion.
 *
 * Wording and order follow the box, so one brain reads both profiles the same way:
 *   problems      python/neuroedge/actions/tools.py check_arguments, dispatch
 *   fields        python/neuroedge/actions/tools.py _verdict_fields
 *   questions     python/neuroedge/actions/confirmation.py
 *   fallback      python/neuroedge/actions/conversation.py _fallback
 * python/tests/test_c_bridge.py runs the same calls through the box and through this file.
 */
#include "ne_brain_bridge.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* JSON types of a span. */
enum { J_BAD = 0, J_STRING, J_NUMBER, J_TRUE, J_FALSE, J_NULL, J_OBJECT, J_ARRAY };

/* Schema kinds: the ne_arg_type of the value the kind admits, or none. */
#define KIND_NONE (-1)
#define ARG_OTHER 7u /* no JSON type the walker knows: every limit refuses it */

/* --- reading JSON ------------------------------------------------------------------------ */

typedef struct {
    const char *p;
    const char *end;
    int first;
} reader;

static void ws(reader *r)
{
    while (r->p < r->end && (*r->p == ' ' || *r->p == '\t' || *r->p == '\n' || *r->p == '\r')) {
        r->p++;
    }
}

static int hex4(const char *p, const char *end, uint32_t *out)
{
    uint32_t v = 0;
    for (int i = 0; i < 4; i++) {
        if (p + i >= end) return -1;
        char c = p[i];
        uint32_t d;
        if (c >= '0' && c <= '9') d = (uint32_t)(c - '0');
        else if (c >= 'a' && c <= 'f') d = (uint32_t)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') d = (uint32_t)(c - 'A' + 10);
        else return -1;
        v = (v << 4) | d;
    }
    *out = v;
    return 0;
}

/* At '"': the string's inside, escapes checked, not decoded. */
static int read_string(reader *r, ne_bridge_span *s)
{
    if (r->p >= r->end || *r->p != '"') return -1;
    const char *start = ++r->p;
    while (r->p < r->end) {
        unsigned char c = (unsigned char)*r->p;
        if (c == '"') {
            s->p = start;
            s->n = (uint32_t)(r->p - start);
            s->type = J_STRING;
            r->p++;
            return 0;
        }
        if (c < 0x20u) return -1;
        if (c == '\\') {
            r->p++;
            if (r->p >= r->end) return -1;
            char e = *r->p;
            if (e == 'u') {
                uint32_t v;
                if (hex4(r->p + 1, r->end, &v) != 0) return -1;
                r->p += 4;
            } else if (!strchr("\"\\/bfnrt", e) || e == '\0') {
                return -1;
            }
        }
        r->p++;
    }
    return -1;
}

static int digits(reader *r)
{
    const char *start = r->p;
    while (r->p < r->end && *r->p >= '0' && *r->p <= '9') r->p++;
    return r->p > start ? 0 : -1;
}

static int read_number(reader *r, ne_bridge_span *s)
{
    const char *start = r->p;
    if (r->p < r->end && *r->p == '-') r->p++;
    if (r->p < r->end && *r->p == '0') {
        r->p++;
    } else if (digits(r) != 0) {
        return -1;
    }
    if (r->p < r->end && *r->p == '.') {
        r->p++;
        if (digits(r) != 0) return -1;
    }
    if (r->p < r->end && (*r->p == 'e' || *r->p == 'E')) {
        r->p++;
        if (r->p < r->end && (*r->p == '+' || *r->p == '-')) r->p++;
        if (digits(r) != 0) return -1;
    }
    s->p = start;
    s->n = (uint32_t)(r->p - start);
    s->type = J_NUMBER;
    return 0;
}

static int literal(reader *r, const char *word, uint8_t type, ne_bridge_span *s)
{
    size_t n = strlen(word);
    if ((size_t)(r->end - r->p) < n || memcmp(r->p, word, n) != 0) return -1;
    s->p = r->p;
    s->n = (uint32_t)n;
    s->type = type;
    r->p += n;
    return 0;
}

/* Any value; a container is skipped whole (its brackets balanced, its strings checked). */
static int read_value(reader *r, ne_bridge_span *s)
{
    ws(r);
    if (r->p >= r->end) return -1;
    char c = *r->p;
    if (c == '"') return read_string(r, s);
    if (c == '-' || (c >= '0' && c <= '9')) return read_number(r, s);
    if (c == 't') return literal(r, "true", J_TRUE, s);
    if (c == 'f') return literal(r, "false", J_FALSE, s);
    if (c == 'n') return literal(r, "null", J_NULL, s);
    if (c != '{' && c != '[') return -1;
    const char *start = r->p;
    uint32_t depth = 0;
    while (r->p < r->end) {
        char d = *r->p;
        if (d == '"') {
            ne_bridge_span skipped;
            if (read_string(r, &skipped) != 0) return -1;
            continue;
        }
        if (d == '{' || d == '[') {
            depth++;
        } else if (d == '}' || d == ']') {
            if (depth == 0) return -1;
            depth--;
            if (depth == 0) {
                r->p++;
                s->p = start;
                s->n = (uint32_t)(r->p - start);
                s->type = c == '{' ? J_OBJECT : J_ARRAY;
                return 0;
            }
        }
        r->p++;
    }
    return -1;
}

/* Iterate the members of the object (or items of the array) `container` spans. */
static int open_container(reader *r, const ne_bridge_span *container)
{
    r->p = container->p + 1;
    r->end = container->p + container->n - 1;
    r->first = 1;
    return 0;
}

/* 1 = a member, 0 = the end, -1 = not JSON. `key` NULL for an array. */
static int next_item(reader *r, ne_bridge_span *key, ne_bridge_span *value)
{
    ws(r);
    if (r->p >= r->end) return 0;
    if (!r->first) {
        if (*r->p != ',') return -1;
        r->p++;
        ws(r);
    }
    r->first = 0;
    if (key != NULL) {
        if (read_string(r, key) != 0) return -1;
        ws(r);
        if (r->p >= r->end || *r->p != ':') return -1;
        r->p++;
    }
    return read_value(r, value) == 0 ? 1 : -1;
}

static void put_utf8(char *out, uint32_t *n, uint32_t cp)
{
    if (cp < 0x80u) {
        out[(*n)++] = (char)cp;
    } else if (cp < 0x800u) {
        out[(*n)++] = (char)(0xC0u | (cp >> 6));
        out[(*n)++] = (char)(0x80u | (cp & 0x3Fu));
    } else if (cp < 0x10000u) {
        out[(*n)++] = (char)(0xE0u | (cp >> 12));
        out[(*n)++] = (char)(0x80u | ((cp >> 6) & 0x3Fu));
        out[(*n)++] = (char)(0x80u | (cp & 0x3Fu));
    } else {
        out[(*n)++] = (char)(0xF0u | (cp >> 18));
        out[(*n)++] = (char)(0x80u | ((cp >> 12) & 0x3Fu));
        out[(*n)++] = (char)(0x80u | ((cp >> 6) & 0x3Fu));
        out[(*n)++] = (char)(0x80u | (cp & 0x3Fu));
    }
}

/* A string span decoded into `out` (no NUL). -1 when it does not fit. */
static int decode(const ne_bridge_span *s, char *out, uint32_t cap, uint32_t *len)
{
    uint32_t n = 0;
    const char *p = s->p;
    const char *end = s->p + s->n;
    while (p < end) {
        if (n + 4u > cap) return -1;
        if (*p != '\\') {
            out[n++] = *p++;
            continue;
        }
        p++;
        char e = *p++;
        switch (e) {
        case 'b': out[n++] = '\b'; break;
        case 'f': out[n++] = '\f'; break;
        case 'n': out[n++] = '\n'; break;
        case 'r': out[n++] = '\r'; break;
        case 't': out[n++] = '\t'; break;
        case 'u': {
            uint32_t cp;
            if (hex4(p, end, &cp) != 0) return -1;
            p += 4;
            if (cp >= 0xD800u && cp < 0xDC00u && end - p >= 6 && p[0] == '\\' && p[1] == 'u') {
                uint32_t lo;
                if (hex4(p + 2, end, &lo) == 0 && lo >= 0xDC00u && lo < 0xE000u) {
                    cp = 0x10000u + ((cp - 0xD800u) << 10) + (lo - 0xDC00u);
                    p += 6;
                }
            }
            put_utf8(out, &n, cp);
            break;
        }
        default: out[n++] = e; break; /* " \ / */
        }
    }
    *len = n;
    return 0;
}

/* Does the string span equal `text`? Decoded into `scratch` of NE_BRIDGE_KEY_MAX. */
static int span_is(const ne_bridge_span *s, const char *text)
{
    char scratch[NE_BRIDGE_KEY_MAX + 4u];
    uint32_t n;
    if (s->type != J_STRING || decode(s, scratch, sizeof scratch, &n) != 0) return 0;
    return strlen(text) == n && memcmp(scratch, text, n) == 0;
}

/* The member `name` of the object `object`; 0 when found. */
static int member(const ne_bridge_span *object, const char *name, ne_bridge_span *out)
{
    reader r;
    ne_bridge_span key, value;
    if (object->type != J_OBJECT) return -1;
    open_container(&r, object);
    while (next_item(&r, &key, &value) == 1) {
        if (span_is(&key, name)) {
            *out = value;
            return 0;
        }
    }
    return -1;
}

static int whole(const char *text, ne_bridge_span *out)
{
    reader r = {text, text + strlen(text), 1};
    if (read_value(&r, out) != 0) return -1;
    ws(&r);
    return r.p == r.end ? 0 : -1;
}

/* --- writing ---------------------------------------------------------------------------- */

typedef struct {
    char *buf;
    uint32_t cap; /* NUL included */
    uint32_t len;
    int over;
} writer;

static void raw(writer *w, const char *s, uint32_t n)
{
    if (w->over || w->len + n + 1u > w->cap) {
        w->over = 1;
        return;
    }
    memcpy(w->buf + w->len, s, n);
    w->len += n;
    w->buf[w->len] = '\0';
}

static void text(writer *w, const char *s) { raw(w, s, (uint32_t)strlen(s)); }

static void number(writer *w, uint32_t v)
{
    char tmp[12];
    int n = snprintf(tmp, sizeof tmp, "%lu", (unsigned long)v);
    raw(w, tmp, (uint32_t)n);
}

/* A JSON string of `n` UTF-8 bytes. */
static void quoted(writer *w, const char *s, uint32_t n)
{
    raw(w, "\"", 1);
    for (uint32_t i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == '"' || c == '\\') {
            char esc[2] = {'\\', (char)c};
            raw(w, esc, 2);
        } else if (c < 0x20u) {
            char esc[7];
            int k = snprintf(esc, sizeof esc, "\\u%04x", (unsigned)c);
            raw(w, esc, (uint32_t)k);
        } else {
            raw(w, (const char *)&s[i], 1);
        }
    }
    raw(w, "\"", 1);
}

static void quoted_text(writer *w, const char *s) { quoted(w, s, s ? (uint32_t)strlen(s) : 0u); }

/* Python's repr() of a str, as in the box's problems (C1 controls escaped, other text kept). */
static void repr(writer *w, const char *s, uint32_t n)
{
    int single = 0, dbl = 0;
    for (uint32_t i = 0; i < n; i++) {
        single |= s[i] == '\'';
        dbl |= s[i] == '"';
    }
    char q = (single && !dbl) ? '"' : '\'';
    raw(w, &q, 1);
    for (uint32_t i = 0; i < n; i++) {
        unsigned char c = (unsigned char)s[i];
        char esc[5];
        if (c == '\\' || c == (unsigned char)q) {
            esc[0] = '\\';
            esc[1] = (char)c;
            raw(w, esc, 2);
        } else if (c == '\n') {
            raw(w, "\\n", 2);
        } else if (c == '\r') {
            raw(w, "\\r", 2);
        } else if (c == '\t') {
            raw(w, "\\t", 2);
        } else if (c < 0x20u || c == 0x7Fu) {
            int k = snprintf(esc, sizeof esc, "\\x%02x", (unsigned)c);
            raw(w, esc, (uint32_t)k);
        } else if (c == 0xC2u && i + 1 < n && (unsigned char)s[i + 1] < 0xA1u) {
            /* U+0080..U+00A0: not printable for Python, written \x80..\xa0 */
            int k = snprintf(esc, sizeof esc, "\\x%02x", (unsigned)(unsigned char)s[i + 1]);
            raw(w, esc, (uint32_t)k);
            i++;
        } else {
            raw(w, (const char *)&s[i], 1);
        }
    }
    raw(w, &q, 1);
}

/* Python's repr() of a float: the shortest digits that read back, fixed for 1e-4 <= |x| < 1e16. */
static void repr_float(writer *w, double x)
{
    char tmp[40];
    if (x != x) {
        text(w, "nan");
        return;
    }
    if (x > 1.7976931348623157e308 || x < -1.7976931348623157e308) {
        text(w, x > 0 ? "inf" : "-inf");
        return;
    }
    int p = 1;
    for (; p <= 17; p++) {
        snprintf(tmp, sizeof tmp, "%.*e", p - 1, x);
        if (strtod(tmp, NULL) == x) break;
    }
    /* tmp is d.ddde±XX: split digits and exponent. */
    char dig[20];
    uint32_t nd = 0;
    const char *c = tmp;
    int neg = 0;
    if (*c == '-') {
        neg = 1;
        c++;
    }
    for (; *c && *c != 'e'; c++) {
        if (*c >= '0' && *c <= '9' && nd < sizeof dig) dig[nd++] = *c;
    }
    long exp10 = *c == 'e' ? strtol(c + 1, NULL, 10) : 0;
    while (nd > 1 && dig[nd - 1] == '0') nd--;
    if (neg) raw(w, "-", 1);
    if (exp10 >= -4 && exp10 < 16) {
        if (exp10 < 0) {
            raw(w, "0.", 2);
            for (long i = -1; i > exp10; i--) raw(w, "0", 1);
            raw(w, dig, nd);
        } else {
            uint32_t intpart = (uint32_t)exp10 + 1u;
            for (uint32_t i = 0; i < intpart; i++) raw(w, i < nd ? &dig[i] : "0", 1);
            raw(w, ".", 1);
            if (nd > intpart) raw(w, &dig[intpart], nd - intpart);
            else raw(w, "0", 1);
        }
        return;
    }
    raw(w, dig, 1);
    if (nd > 1) {
        raw(w, ".", 1);
        raw(w, &dig[1], nd - 1);
    }
    int k = snprintf(tmp, sizeof tmp, "e%c%02ld", exp10 < 0 ? '-' : '+', exp10 < 0 ? -exp10 : exp10);
    raw(w, tmp, (uint32_t)k);
}

/* Python's repr() of a JSON value as json.loads gives it (containers as their JSON text). */
static void repr_value(ne_bridge *b, writer *w, const ne_bridge_span *v)
{
    char *scratch = b->work;
    const uint32_t cap = sizeof b->work;
    uint32_t n;
    switch (v->type) {
    case J_STRING:
        if (decode(v, scratch, cap, &n) == 0) repr(w, scratch, n);
        return;
    case J_TRUE: text(w, "True"); return;
    case J_FALSE: text(w, "False"); return;
    case J_NULL: text(w, "None"); return;
    case J_NUMBER: {
        int integral = 1;
        for (uint32_t i = 0; i < v->n; i++) integral &= v->p[i] != '.' && v->p[i] != 'e' && v->p[i] != 'E';
        if (integral) {
            if (v->n == 2 && v->p[0] == '-' && v->p[1] == '0') text(w, "0");
            else raw(w, v->p, v->n);
            return;
        }
        if (v->n >= cap) return;
        memcpy(scratch, v->p, v->n);
        scratch[v->n] = '\0';
        repr_float(w, strtod(scratch, NULL));
        return;
    }
    default: raw(w, v->p, v->n); return;
    }
}

/* --- the agent ----------------------------------------------------------------------------- */

/* Fixed-width rows, not pointers: no relocation, so .rodata even in a PIE (no static RAM). */
static const char REASONS[][24] = {
    "",
    "condition_not_met",
    "criterion_unavailable",
    "confidence_unavailable",
    "argument_out_of_range",
    "gate_unreachable",
    "budget_exceeded",
    "value_out_of_range",
};
static const char ON_BLOCK[][9] = {"deny", "escalate", "ask", "degrade"};

static int find_action(const ne_agent *agent, const char *name)
{
    for (uint32_t i = 0; i < agent->action_count; i++) {
        if (strcmp(agent->actions[i].name, name) == 0) return (int)i;
    }
    return -1;
}

static uint32_t ttl_of(const ne_tree *tree)
{
    uint32_t p95 = tree->p95_latency_ms;
    uint32_t ttl = p95 > UINT32_MAX / NE_BRIDGE_TTL_FACTOR ? UINT32_MAX : p95 * NE_BRIDGE_TTL_FACTOR;
    return ttl < NE_BRIDGE_MIN_TTL_MS ? NE_BRIDGE_MIN_TTL_MS : ttl;
}

/* Mark questions past their TTL, as `_expire_due` does. */
static void expire_due(ne_bridge *b, uint32_t now)
{
    for (uint32_t i = 0; i < NE_BRIDGE_PENDING; i++) {
        ne_bridge_pending *q = &b->pending[i];
        if (q->state == NE_PENDING_WAITING && (uint32_t)(now - q->created_ms) > q->ttl_ms) {
            q->state = NE_PENDING_EXPIRED;
        }
    }
}

uint32_t ne_bridge_waiting(ne_bridge *b)
{
    uint32_t n = 0;
    if (b == NULL) return 0;
    expire_due(b, b->hal.now_ms(b->hal.ctx));
    for (uint32_t i = 0; i < NE_BRIDGE_PENDING; i++) n += b->pending[i].state == NE_PENDING_WAITING;
    return n;
}

int ne_bridge_init(ne_bridge *b, const ne_agent *agent, ne_ledger *ledger,
                   const ne_fact_source *facts, const ne_bridge_hal *hal, const char *owner_id)
{
    if (b == NULL || agent == NULL || ledger == NULL || facts == NULL || hal == NULL ||
        hal->now_ms == NULL || hal->fill_random == NULL || hal->run == NULL) {
        return -1;
    }
    size_t owner = owner_id ? strlen(owner_id) : 0u;
    if (owner >= NE_BRIDGE_OWNER_MAX) return -1;
    memset(b, 0, sizeof *b);
    b->agent = agent;
    b->ledger = ledger;
    b->facts = *facts;
    b->hal = *hal;
    if (owner) memcpy(b->owner, owner_id, owner);
    b->next_number = 1;
    b->opened = -1;
    return 0;
}

void ne_bridge_trace(ne_bridge *b, ne_trace_sink *sink, const ne_device_info *info)
{
    if (b == NULL) return;
    b->trace = info != NULL ? sink : NULL;
    b->trace_info = info;
}

void ne_bridge_trace_pin(ne_bridge *b, uint32_t pin, int driven, const char *operation,
                         uint32_t duration_ms, ne_token_reason why)
{
    if (b == NULL || b->trace == NULL || pin >= b->agent->pin_count) return;
    ne_trace_sink *t = b->trace;
    const char *name = b->agent->pins[pin];
    if (driven) {
        ne_trace_put(t, ne_trace_actuator_command(t->buf, t->cap, ne_trace_offset(t), name,
                                                  operation ? operation : "on", duration_ms));
    } else {
        ne_trace_put(t, ne_trace_actuator_rejected(t->buf, t->cap, ne_trace_offset(t), name, why));
    }
}

uint32_t ne_bridge_pulse_ms(const ne_bridge *b, uint32_t action, const ne_agent_pin_op *op,
                            const ne_arg_value *args, uint32_t arg_count)
{
    if (b == NULL || op == NULL || op->op != NE_AGENT_OP_PULSE || action >= b->agent->action_count) {
        return 0u;
    }
    if (op->arg == NULL) return op->ms;
    const ne_agent_gate *g = &b->agent->gates[b->agent->actions[action].gate];
    ne_tree tree;
    if (args == NULL || ne_tree_load(&tree, g->tree, g->tree_size) != NE_OK) return 0u;
    for (uint32_t i = 0; i < arg_count && i < tree.arg_count; i++) {
        const char *name = ne_argument_name(&tree, i);
        if (name == NULL || strcmp(name, op->arg) != 0) continue;
        if (!args[i].present || args[i].type == NE_ARG_STRING) return 0u;
        const double ms = args[i].number * (double)op->ms;
        return ms > 0.0 && ms < 86400000.0 ? (uint32_t)ms : 0u;
    }
    return 0u;
}

uint32_t ne_bridge_tool_count(const ne_bridge *b) { return b ? b->agent->action_count : 0u; }

int ne_bridge_tool(const ne_bridge *b, uint32_t i, const char **name, const char **description,
                   const char **input_schema)
{
    if (b == NULL || i >= b->agent->action_count) return -1;
    if (name) *name = b->agent->actions[i].name;
    if (description) *description = b->agent->actions[i].description;
    if (input_schema) *input_schema = b->agent->actions[i].input_schema;
    return 0;
}

/* --- arguments (DP-B-04) ------------------------------------------------------------------- */

static int kind_of(const ne_bridge_span *prop)
{
    ne_bridge_span type;
    if (member(prop, "type", &type) != 0) return KIND_NONE;
    if (span_is(&type, "string")) return NE_ARG_STRING;
    if (span_is(&type, "integer")) return NE_ARG_INTEGER;
    if (span_is(&type, "number")) return NE_ARG_NUMBER;
    if (span_is(&type, "boolean")) return NE_ARG_BOOLEAN;
    return KIND_NONE;
}

/* Python's float.is_integer(), with no libm and no out-of-range cast. */
static int integral(double x)
{
    if (x != x) return 0;
    if (x > 9007199254740992.0 || x < -9007199254740992.0) return x - x == 0.0; /* inf: no */
    return x == (double)(int64_t)x;
}

/* A plain decimal, as the box's int()/float() read a numeric string (closed side). */
static int decimal(const char *s, uint32_t n, int integer, double *out)
{
    char tmp[64];
    uint32_t i = 0, d = 0;
    if (n == 0 || n >= sizeof tmp) return -1;
    if (s[i] == '+' || s[i] == '-') i++;
    for (; i < n && s[i] >= '0' && s[i] <= '9'; i++) d++;
    if (!integer) {
        if (i < n && s[i] == '.') {
            i++;
            for (; i < n && s[i] >= '0' && s[i] <= '9'; i++) d++;
        }
        if (d && i < n && (s[i] == 'e' || s[i] == 'E')) {
            uint32_t e = 0;
            i++;
            if (i < n && (s[i] == '+' || s[i] == '-')) i++;
            for (; i < n && s[i] >= '0' && s[i] <= '9'; i++) e++;
            if (!e) return -1;
        }
    }
    if (!d || i != n) return -1;
    memcpy(tmp, s, n);
    tmp[n] = '\0';
    *out = strtod(tmp, NULL);
    return 0;
}

/*
 * `_coerce`: the value as the gate sees it under `kind`, or -1 (a problem). A string goes
 * into b->text_buf at *used.
 */
static int coerce(ne_bridge *b, const ne_bridge_span *v, int kind, ne_arg_value *out, uint32_t *used)
{
    char *scratch = b->work;
    uint32_t n = 0;
    memset(out, 0, sizeof *out);
    out->present = 1;
    if (v->type == J_STRING) {
        if (decode(v, scratch, sizeof b->work, &n) != 0) return -1;
    }
    if (kind == KIND_NONE || kind == NE_ARG_STRING) {
        if (v->type == J_STRING) {
            if (*used + n > sizeof b->text_buf) return -1;
            memcpy(b->text_buf + *used, scratch, n);
            out->type = NE_ARG_STRING;
            out->str = b->text_buf + *used;
            out->str_len = n;
            *used += n;
            return 0;
        }
        if (kind == NE_ARG_STRING) return -1;
        if (v->type == J_TRUE || v->type == J_FALSE) {
            out->type = NE_ARG_BOOLEAN;
            out->number = v->type == J_TRUE ? 1.0 : 0.0;
            return 0;
        }
        if (v->type == J_NUMBER && decimal(v->p, v->n, 0, &out->number) == 0) {
            out->type = integral(out->number) ? NE_ARG_INTEGER : NE_ARG_NUMBER;
            return 0;
        }
        out->type = ARG_OTHER;
        return 0;
    }
    if (kind == NE_ARG_BOOLEAN) {
        if (v->type == J_TRUE || v->type == J_FALSE) {
            out->type = NE_ARG_BOOLEAN;
            out->number = v->type == J_TRUE ? 1.0 : 0.0;
            return 0;
        }
        if (v->type == J_STRING && (n == 4u || n == 5u)) {
            char low[5];
            for (uint32_t i = 0; i < n; i++) {
                char c = scratch[i];
                low[i] = (c >= 'A' && c <= 'Z') ? (char)(c - 'A' + 'a') : c;
            }
            if (n == 4u && memcmp(low, "true", 4) == 0) {
                out->type = NE_ARG_BOOLEAN;
                out->number = 1.0;
                return 0;
            }
            if (n == 5u && memcmp(low, "false", 5) == 0) {
                out->type = NE_ARG_BOOLEAN;
                out->number = 0.0;
                return 0;
            }
        }
        return -1;
    }
    /* integer or number */
    double x;
    if (v->type == J_NUMBER) {
        if (decimal(v->p, v->n, 0, &x) != 0) return -1;
        if (kind == NE_ARG_INTEGER && !integral(x)) return -1;
    } else if (v->type == J_STRING) {
        if (decimal(scratch, n, kind == NE_ARG_INTEGER, &x) != 0) return -1;
    } else {
        return -1;
    }
    out->number = x;
    out->type = (kind == NE_ARG_INTEGER || integral(x)) ? NE_ARG_INTEGER : NE_ARG_NUMBER;
    return 0;
}

static int key_index(const ne_bridge *b, const char *name)
{
    for (uint32_t i = 0; i < b->key_count; i++) {
        if (span_is(&b->keys[i], name)) return (int)i;
    }
    return -1;
}

/* Byte order of two string spans, decoded (Python sorts str by code point: UTF-8 bytes agree). */
static int span_cmp(ne_bridge *b, const ne_bridge_span *a, const ne_bridge_span *c)
{
    char *x = b->cmp[0], *y = b->cmp[1];
    uint32_t nx = 0, ny = 0;
    (void)decode(a, x, NE_BRIDGE_KEY_MAX + 4u, &nx);
    (void)decode(c, y, NE_BRIDGE_KEY_MAX + 4u, &ny);
    uint32_t m = nx < ny ? nx : ny;
    int r = memcmp(x, y, m);
    if (r != 0) return r;
    return nx < ny ? -1 : (nx > ny ? 1 : 0);
}

static void repr_span(ne_bridge *b, writer *w, const ne_bridge_span *s)
{
    uint32_t n = 0;
    if (decode(s, b->work, sizeof b->work, &n) == 0) repr(w, b->work, n);
}

/* `sorted(properties)` as Python prints a list of str. */
static void sorted_names(ne_bridge *b, writer *w, const ne_bridge_span *props)
{
    reader r;
    ne_bridge_span key, value, last = {NULL, 0, J_BAD};
    int any = 0;
    raw(w, "[", 1);
    for (;;) {
        ne_bridge_span best = {NULL, 0, J_BAD};
        open_container(&r, props);
        while (next_item(&r, &key, &value) == 1) {
            if (last.type == J_STRING && span_cmp(b, &key, &last) <= 0) continue;
            if (best.type != J_STRING || span_cmp(b, &key, &best) < 0) best = key;
        }
        if (best.type != J_STRING) break;
        if (any) raw(w, ", ", 2);
        repr_span(b, w, &best);
        any = 1;
        last = best;
    }
    raw(w, "]", 1);
}

/* One more problem, as a JSON string, into the array body `w`. */
static void problem(writer *w, int *count, const char *line, uint32_t n)
{
    if (*count) raw(w, ",", 1);
    quoted(w, line, n);
    (*count)++;
}

static void problem_text(writer *w, int *count, const char *line)
{
    problem(w, count, line, (uint32_t)strlen(line));
}

/*
 * check_arguments: the problems of `args` (an object span) against the action's schema, in
 * the box's order, as a JSON array body into `w`; 0 when there are none. The keys are left
 * in b->keys / b->values.
 */
static int check_arguments(ne_bridge *b, uint32_t action, const ne_bridge_span *args, writer *w)
{
    const ne_agent_action *a = &b->agent->actions[action];
    ne_bridge_span schema, props, required, key, value;
    reader r;
    int count = 0;
    writer p = {b->line, sizeof b->line, 0, 0};

    b->key_count = 0;
    if (whole(a->input_schema, &schema) != 0 || member(&schema, "properties", &props) != 0) {
        problem_text(w, &count, "the tool's schema is not valid JSON");
        return count;
    }
    open_container(&r, args);
    int status;
    while ((status = next_item(&r, &key, &value)) == 1) {
        if (b->key_count == NE_BRIDGE_MAX_KEYS || key.n >= NE_BRIDGE_KEY_MAX) {
            problem_text(w, &count, "more than 16 arguments, or an argument name of 48 bytes or more");
            return count;
        }
        for (uint32_t i = 0; i < b->key_count; i++) {
            if (span_cmp(b, &b->keys[i], &key) == 0) {
                problem_text(w, &count, "an argument is given twice");
                return count;
            }
        }
        uint32_t n = 0;
        if (decode(&key, b->name, NE_BRIDGE_KEY_MAX + 3u, &n) != 0 || memchr(b->name, 0, n)) {
            problem_text(w, &count, "an argument name is not plain text");
            return count;
        }
        b->keys[b->key_count] = key;
        b->values[b->key_count] = value;
        b->key_count++;
    }
    if (status != 0) {
        problem_text(w, &count, "the arguments are not valid JSON");
        return count;
    }
    /* unknown keys, sorted */
    ne_bridge_span last = {NULL, 0, J_BAD};
    for (;;) {
        int best = -1;
        for (uint32_t i = 0; i < b->key_count; i++) {
            ne_bridge_span found;
            char *name = b->name;
            uint32_t n = 0;
            (void)decode(&b->keys[i], name, NE_BRIDGE_KEY_MAX + 3u, &n);
            name[n] = '\0';
            if (member(&props, name, &found) == 0) continue;
            if (last.type == J_STRING && span_cmp(b, &b->keys[i], &last) <= 0) continue;
            if (best < 0 || span_cmp(b, &b->keys[i], &b->keys[best]) < 0) best = (int)i;
        }
        if (best < 0) break;
        last = b->keys[best];
        p.len = 0;
        p.over = 0;
        text(&p, "unknown argument ");
        repr_span(b, &p, &b->keys[best]);
        text(&p, "; ");
        text(&p, a->name);
        text(&p, " takes ");
        sorted_names(b, &p, &props);
        problem(w, &count, b->line, p.len);
    }
    /* missing required, in the schema's order */
    if (member(&schema, "required", &required) == 0 && required.type == J_ARRAY) {
        open_container(&r, &required);
        while (next_item(&r, NULL, &value) == 1) {
            char *name = b->name;
            uint32_t n = 0;
            if (value.type != J_STRING || decode(&value, name, NE_BRIDGE_KEY_MAX + 3u, &n) != 0) continue;
            name[n] = '\0';
            if (key_index(b, name) >= 0) continue;
            p.len = 0;
            p.over = 0;
            text(&p, "missing required argument ");
            repr(&p, name, n);
            problem(w, &count, b->line, p.len);
        }
    }
    /* types, in the call's order */
    uint32_t used = 0;
    for (uint32_t i = 0; i < b->key_count; i++) {
        char *name = b->name;
        uint32_t n = 0;
        ne_bridge_span prop;
        ne_arg_value coerced;
        (void)decode(&b->keys[i], name, NE_BRIDGE_KEY_MAX + 3u, &n);
        name[n] = '\0';
        if (member(&props, name, &prop) != 0) continue;
        int kind = kind_of(&prop);
        if (coerce(b, &b->values[i], kind, &coerced, &used) == 0) continue;
        p.len = 0;
        p.over = 0;
        text(&p, "argument ");
        repr(&p, name, n);
        text(&p, " must be ");
        text(&p, kind == NE_ARG_STRING    ? "string"
                 : kind == NE_ARG_INTEGER ? "integer"
                 : kind == NE_ARG_NUMBER  ? "number"
                                          : "boolean");
        text(&p, ", got ");
        repr_value(b, &p, &b->values[i]);
        problem(w, &count, b->line, p.len);
    }
    return count;
}

/* The gate's arguments, in the tree's order: the call's, or the schema's default (`_effective`). */
static void gate_arguments(ne_bridge *b, uint32_t action, const ne_tree *tree)
{
    const ne_agent_action *a = &b->agent->actions[action];
    ne_bridge_span schema, props, prop, def;
    uint32_t used = 0;
    int have = whole(a->input_schema, &schema) == 0 && member(&schema, "properties", &props) == 0;
    for (uint32_t i = 0; i < tree->arg_count && i < NE_MAX_ARGS; i++) {
        ne_arg_value *v = &b->arg_buf[i];
        const char *name = ne_argument_name(tree, i);
        memset(v, 0, sizeof *v);
        if (name == NULL) continue;
        int kind = KIND_NONE;
        if (have && member(&props, name, &prop) == 0) kind = kind_of(&prop);
        int k = key_index(b, name);
        if (k >= 0) {
            if (coerce(b, &b->values[k], kind, v, &used) != 0) memset(v, 0, sizeof *v);
        } else if (have && member(&props, name, &prop) == 0 && member(&prop, "default", &def) == 0) {
            if (coerce(b, &def, kind, v, &used) != 0) memset(v, 0, sizeof *v);
        }
    }
}

/* --- facts (DP-B-05) ---------------------------------------------------------------------- */

/* `call_source` and `call_channel` are the bridge's: the brain calls as an MCP client does. */
static void set_caller(const ne_tree *tree, ne_fact *f, uint32_t i)
{
    memset(f, 0, sizeof *f);
    f->present = 1;
    int kind = ne_criterion_kind(tree, i);
    if (kind != NE_KIND_LEVEL && kind != NE_KIND_CHOICE) return; /* in_domain 0 */
    for (uint32_t j = 0; j < NE_MAX_DOMAIN; j++) {
        const char *value = ne_domain_value(tree, i, j);
        if (value == NULL) break;
        if (strcmp(value, NE_BRIDGE_CALL_SOURCE) == 0) {
            f->in_domain = 1;
            f->index = (uint8_t)j;
            return;
        }
    }
}

static ne_degraded read_facts(ne_bridge *b, const ne_tree *tree, uint32_t gate, uint32_t now)
{
    uint32_t count = tree->node_count;
    ne_degraded degraded = NE_DEGRADED_NONE;
    memset(b->fact_buf, 0, sizeof b->fact_buf);
    if (b->facts.read != NULL) degraded = b->facts.read(b->facts.ctx, tree, gate, b->fact_buf, count, now);
    for (uint32_t i = 0; i < count; i++) {
        const char *name = ne_criterion_name(tree, i);
        if (name && (strcmp(name, "call_source") == 0 || strcmp(name, "call_channel") == 0)) {
            set_caller(tree, &b->fact_buf[i], i);
        }
    }
    return degraded;
}

/* --- deciding ----------------------------------------------------------------------------- */

static int open_question(ne_bridge *b, uint32_t action, const ne_tree *tree, const char *args,
                         uint32_t args_len, uint32_t now)
{
    expire_due(b, now);
    uint32_t waiting = 0;
    int slot = -1;
    for (uint32_t i = 0; i < NE_BRIDGE_PENDING; i++) {
        if (b->pending[i].state == NE_PENDING_WAITING) waiting++;
        else if (slot < 0) slot = (int)i;
    }
    if (waiting >= NE_BRIDGE_PENDING || slot < 0) return -1; /* DP-COM-09 */
    b->opened = slot;
    ne_bridge_pending *q = &b->pending[slot];
    memset(q, 0, sizeof *q);
    q->state = NE_PENDING_WAITING;
    q->action = (uint16_t)action;
    q->number = b->next_number++;
    q->created_ms = now;
    q->ttl_ms = ttl_of(tree);
    memcpy(q->digest, tree->gate_digest, NE_DIGEST_SIZE);
    q->args_len = args_len;
    if (args_len) memcpy(q->args, args, args_len);
    return slot;
}

static int takes_no_arguments(const ne_agent_action *a)
{
    ne_bridge_span schema, required;
    if (whole(a->input_schema, &schema) != 0) return 0;
    if (member(&schema, "required", &required) != 0) return 1;
    return required.n <= 2u; /* "[]" */
}

/* `action_requested` {action, gate, arguments}: what a replay re-runs (trace.v1, the host's). */
static void trace_request(ne_bridge *b, const ne_agent_action *a, const ne_agent_gate *g,
                          const char *args, uint32_t args_len)
{
    ne_trace_sink *t = b->trace;
    const uint32_t cap = t->cap < NE_TRACE_LINE_MAX + 1u ? (uint32_t)t->cap : NE_TRACE_LINE_MAX + 1u;
    writer w = {t->buf, cap, 0, 0};
    uint32_t gate_len = 0;
    while (g->label[gate_len] && g->label[gate_len] != '@') gate_len++;
    text(&w, NE_TRACE_PREFIX "{\"offset_ms\":");
    number(&w, ne_trace_offset(t));
    text(&w, ",\"type\":\"action_requested\",\"data\":{\"action\":");
    quoted_text(&w, a->name);
    text(&w, ",\"gate\":");
    quoted(&w, g->label, gate_len);
    text(&w, ",\"arguments\":");
    if (args_len) {
        /* compact: whitespace outside strings dropped, so a pretty-printed call is one line */
        int in_string = 0, escaped = 0;
        for (uint32_t i = 0; i < args_len; i++) {
            const char ch = args[i];
            if (!in_string && (ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r')) continue;
            if (in_string && !escaped && ch == '"') in_string = 0;
            else if (!in_string && ch == '"') in_string = 1;
            escaped = in_string && !escaped && ch == '\\';
            raw(&w, &ch, 1u);
        }
    } else {
        text(&w, "{}");
    }
    text(&w, "}}");
    ne_trace_put(t, w.over ? -1 : (int)w.len);
}

/*
 * Decide `action` with `args` (an object span of a validated call) and act on it, writing its
 * result object into `w`, then its `on_block: degrade` fallbacks nested in it as the box does.
 * Returns the status of the outermost result.
 */
static ne_bridge_status decide_steps(ne_bridge *b, uint32_t action, const char *args,
                                     uint32_t args_len, int confirmed, writer *w)
{
    uint32_t visited[NE_BRIDGE_MAX_FALLBACK + 1u];
    uint32_t depth = 0;
    ne_bridge_status top = NE_BRIDGE_BLOCK;
    for (;;) {
        const ne_agent_action *a = &b->agent->actions[action];
        const ne_agent_gate *g = &b->agent->gates[a->gate];
        ne_tree tree;
        ne_result res;
        uint32_t now = b->hal.now_ms(b->hal.ctx);
        visited[depth] = action;
        text(w, "{\"tool\":");
        quoted_text(w, a->name);
        if (ne_tree_load(&tree, g->tree, g->tree_size) != NE_OK) {
            text(w, ",\"status\":\"BLOCK\",\"gate\":");
            quoted_text(w, g->label);
            text(w, ",\"reason\":\"gate_not_found\",\"on_block\":\"deny\"");
            if (depth == 0) top = NE_BRIDGE_BLOCK;
            break;
        }
        /* the call's keys, again: a fallback has none */
        ne_bridge_span obj = {"{}", 2, J_OBJECT};
        if (args_len) {
            obj.p = args;
            obj.n = args_len;
        }
        b->key_count = 0;
        if (depth == 0 && args_len) {
            reader r;
            ne_bridge_span key, value;
            open_container(&r, &obj);
            while (b->key_count < NE_BRIDGE_MAX_KEYS && next_item(&r, &key, &value) == 1) {
                b->keys[b->key_count] = key;
                b->values[b->key_count] = value;
                b->key_count++;
            }
        }
        if (b->trace != NULL) trace_request(b, a, g, depth == 0 ? args : NULL, depth == 0 ? args_len : 0u);
        gate_arguments(b, action, &tree);
        ne_degraded degraded = read_facts(b, &tree, a->gate, now);
        ne_decide(&tree, b->fact_buf, b->arg_buf, depth == 0 ? confirmed : 0, degraded, &res);
        if (b->trace != NULL) {
            ne_trace_sink *t = b->trace;
            ne_trace_put(t, ne_trace_gate_begin(t->buf, t->cap, ne_trace_offset(t), g->label, &tree));
            ne_trace_put(t, ne_trace_gate_facts(t->buf, t->cap, ne_trace_offset(t), &tree,
                                                b->fact_buf, NULL));
            ne_trace_put(t, ne_trace_gate_result(t->buf, t->cap, ne_trace_offset(t), g->label,
                                                 &tree, b->fact_buf, &res, &g->text));
        }
        if (res.verdict == NE_ALLOW) {
            ne_token token;
            if (ne_token_issue(b->ledger, &tree, a->pin_mask, now, b->hal.fill_random, &token) !=
                NE_TOKEN_OK) {
                /* every slot holds a live token: no token, no action (ne_token.h) */
                text(w, ",\"status\":\"BLOCK\",\"gate\":");
                quoted_text(w, g->label);
                text(w, ",\"reason\":\"budget_exceeded\",\"on_block\":\"deny\"");
                if (depth == 0) top = NE_BRIDGE_BLOCK;
                break;
            }
            b->hal.run(b->hal.ctx, action, b->arg_buf, tree.arg_count, b->ledger, &token);
            ne_token_close(b->ledger, &token);
            text(w, ",\"status\":\"ALLOW\"");
            if (depth == 0) top = NE_BRIDGE_ALLOW;
            break;
        }
        int degraded_verdict = res.fail_mode != NE_FAIL_MODE_NONE;
        uint8_t on_block = degraded_verdict ? 0u : tree.on_block_action;
        int asks = on_block == 2u && res.answerable && !(depth == 0 && confirmed);
        int full = 0;
        int slot = -1;
        if (asks) {
            slot = open_question(b, action, &tree, depth == 0 ? args : NULL, depth == 0 ? args_len : 0u, now);
            full = slot < 0;
        }
        text(w, ",\"status\":\"BLOCK\",\"gate\":");
        quoted_text(w, g->label);
        if (full) {
            text(w, ",\"reason\":\"budget_exceeded\"");
        } else if (res.reason != NE_REASON_NONE && (uint32_t)res.reason < sizeof REASONS / sizeof REASONS[0]) {
            text(w, ",\"reason\":\"");
            text(w, REASONS[res.reason]);
            text(w, "\"");
        }
        if (res.failed_kind == NE_FAILED_CRITERION || res.failed_kind == NE_FAILED_ARGUMENT) {
            const char *failed = res.failed_kind == NE_FAILED_CRITERION
                                     ? ne_criterion_name(&tree, res.failed_index)
                                     : ne_argument_name(&tree, res.failed_index);
            if (failed) {
                text(w, ",\"failed_criterion\":");
                quoted_text(w, failed);
            }
        }
        text(w, ",\"on_block\":\"");
        text(w, ON_BLOCK[on_block < 4u ? on_block : 0u]);
        text(w, "\"");
        if ((on_block == 1u || on_block == 2u) && g->text.message) {
            text(w, ",\"message\":");
            quoted_text(w, g->text.message);
        }
        if (on_block == 1u && g->text.to) {
            text(w, ",\"escalated_to\":");
            quoted_text(w, g->text.to);
        }
        if (slot >= 0) {
            const ne_bridge_pending *q = &b->pending[slot];
            text(w, ",\"confirmation\":{\"id\":\"confirm_");
            number(w, q->number);
            text(w, "\",\"message\":");
            quoted_text(w, g->text.message ? g->text.message : "");
            text(w, ",\"expires_in_ms\":");
            number(w, q->ttl_ms);
            text(w, ",\"who\":");
            quoted_text(w, NE_BRIDGE_WHO);
            text(w, "}");
        }
        if (depth == 0) top = NE_BRIDGE_BLOCK;
        if (on_block != 3u || g->text.fallback_action == NULL) break;
        /* `_fallback`: a registered @action, not visited, within the depth, with no arguments */
        int next = find_action(b->agent, g->text.fallback_action);
        int ok = next >= 0 && depth + 1u < NE_BRIDGE_MAX_FALLBACK + 1u &&
                 takes_no_arguments(&b->agent->actions[next]);
        for (uint32_t i = 0; ok && i <= depth; i++) ok = visited[i] != (uint32_t)next;
        if (!ok) break;
        text(w, ",\"fallback\":");
        action = (uint32_t)next;
        args = NULL;
        args_len = 0;
        depth++;
    }
    for (uint32_t i = 0; i <= depth; i++) text(w, "}");
    return top;
}

/* One NE1 session around one decision, when the application asked for traces (DP-B-12). */
static ne_bridge_status decide(ne_bridge *b, uint32_t action, const char *args, uint32_t args_len,
                               int confirmed, writer *w)
{
    if (b->trace != NULL) ne_trace_open(b->trace, b->trace_info);
    const ne_bridge_status status = decide_steps(b, action, args, args_len, confirmed, w);
    if (b->trace != NULL) ne_trace_close(b->trace);
    return status;
}

/* --- results ------------------------------------------------------------------------------- */

static void finish(ne_bridge *b, ne_bridge_result *out, writer *w, ne_bridge_status status,
                   const char *tool)
{
    out->status = status;
    if (!w->over) {
        out->len = w->len;
        return;
    }
    if (b != NULL && b->opened >= 0) {
        /* the brain cannot be told about it: the question must not wait to be answered */
        b->pending[b->opened].state = NE_PENDING_DECLINED;
        b->opened = -1;
    }
    /* Too long to tell in full: the status stands, the details do not fit (closed side). */
    writer m = {out->json, sizeof out->json, 0, 0};
    text(&m, "{\"tool\":");
    uint32_t n = 0;
    while (n < 64u && tool[n]) n++; /* strnlen is not C99 */
    quoted(&m, tool, n);
    if (status == NE_BRIDGE_ALLOW) {
        text(&m, ",\"status\":\"ALLOW\"}");
    } else {
        text(&m, ",\"status\":\"REJECTED\",\"problems\":[\"the result does not fit in "
                 "NE_BRIDGE_RESULT_MAX\"]}");
        out->status = NE_BRIDGE_REJECTED;
    }
    out->len = m.len;
}

static void rejected(ne_bridge_result *out, const char *tool, const char *problem)
{
    writer w = {out->json, sizeof out->json, 0, 0};
    text(&w, "{\"tool\":");
    quoted_text(&w, tool);
    text(&w, ",\"status\":\"REJECTED\",\"problems\":[");
    quoted_text(&w, problem);
    text(&w, "]}");
    finish(NULL, out, &w, NE_BRIDGE_REJECTED, tool);
}

void ne_bridge_call(ne_bridge *b, const char *name, const char *arguments_json,
                    ne_bridge_result *out)
{
    if (out == NULL) return;
    memset(out, 0, sizeof *out);
    if (b == NULL) {
        rejected(out, "", "no bridge");
        return;
    }
    const char *tool = name ? name : "";
    writer w = {out->json, sizeof out->json, 0, 0};
    b->opened = -1;
    int action = find_action(b->agent, tool);
    if (action < 0) {
        writer p = {b->line, sizeof b->line, 0, 0};
        text(&p, "no tool named ");
        repr(&p, tool, (uint32_t)strlen(tool));
        text(&p, "; the agent has [");
        for (uint32_t i = 0; i < b->agent->action_count; i++) {
            if (i) text(&p, ", ");
            repr(&p, b->agent->actions[i].name, (uint32_t)strlen(b->agent->actions[i].name));
        }
        text(&p, "]");
        text(&w, "{\"tool\":");
        quoted_text(&w, tool);
        text(&w, ",\"status\":\"REJECTED\",\"problems\":[");
        quoted(&w, b->line, p.len);
        if (p.over) w.over = 1;
        text(&w, "]}");
        finish(b, out, &w, NE_BRIDGE_REJECTED, tool);
        return;
    }
    const char *args = arguments_json ? arguments_json : "";
    size_t args_len = strlen(args);
    ne_bridge_span obj = {"{}", 2, J_OBJECT};
    if (args_len >= NE_BRIDGE_ARGS_MAX) {
        rejected(out, tool, "the arguments are longer than NE_BRIDGE_ARGS_MAX bytes");
        return;
    }
    if (args_len && (whole(args, &obj) != 0 || obj.type != J_OBJECT)) {
        rejected(out, tool, "the arguments are not a JSON object");
        return;
    }
    writer p = {b->problems, sizeof b->problems, 0, 0};
    if (check_arguments(b, (uint32_t)action, &obj, &p) > 0 || p.over) {
        text(&w, "{\"tool\":");
        quoted_text(&w, tool);
        text(&w, ",\"status\":\"REJECTED\",\"problems\":[");
        raw(&w, b->problems, p.len);
        if (p.over) w.over = 1;
        text(&w, "]}");
        finish(b, out, &w, NE_BRIDGE_REJECTED, tool);
        return;
    }
    ne_bridge_status status =
        decide(b, (uint32_t)action, args_len ? obj.p : NULL, args_len ? obj.n : 0u, 0, &w);
    finish(b, out, &w, status, tool);
}

static const char STATES[][10] = {"free", "pending", "confirmed", "declined", "expired"};

static void answer(ne_bridge *b, int slot, int approve, ne_bridge_result *out)
{
    ne_bridge_pending *q = &b->pending[slot];
    const ne_agent_action *a = &b->agent->actions[q->action];
    const ne_agent_gate *g = &b->agent->gates[a->gate];
    writer w = {out->json, sizeof out->json, 0, 0};
    b->opened = -1;
    if (q->state != NE_PENDING_WAITING) {
        writer p = {b->line, sizeof b->line, 0, 0};
        text(&p, "the question is already ");
        text(&p, STATES[q->state < 5u ? q->state : 0u]);
        rejected(out, a->name, b->line);
        return;
    }
    if (memcmp(q->digest, g->digest, NE_DIGEST_SIZE) != 0) {
        q->state = NE_PENDING_EXPIRED;
        rejected(out, a->name, "the gate changed since the question was asked");
        return;
    }
    if (!approve) {
        q->state = NE_PENDING_DECLINED;
        text(&w, "{\"tool\":");
        quoted_text(&w, a->name);
        text(&w, ",\"status\":\"BLOCK\",\"gate\":");
        quoted_text(&w, g->label);
        text(&w, ",\"reason\":\"declined\",\"on_block\":\"ask\",\"message\":\"the owner said no\"}");
        finish(b, out, &w, NE_BRIDGE_BLOCK, a->name);
        return;
    }
    q->state = NE_PENDING_CONFIRMED; /* single use: spent even if the gate then blocks again */
    uint32_t n = q->args_len;
    memcpy(b->saved, q->args, n); /* the slot may be reused by a question the action asks */
    ne_bridge_span obj = {"{}", 2, J_OBJECT};
    if (n) {
        obj.p = b->saved;
        obj.n = n;
    }
    writer p = {b->problems, sizeof b->problems, 0, 0};
    if (check_arguments(b, q->action, &obj, &p) > 0) {
        rejected(out, a->name, "the stored arguments no longer fit the tool");
        return;
    }
    ne_bridge_status status = decide(b, q->action, n ? b->saved : NULL, n, 1, &w);
    finish(b, out, &w, status, a->name);
}

static int slot_of(ne_bridge *b, const char *id)
{
    if (id == NULL || strncmp(id, "confirm_", 8) != 0 || id[8] == '\0') return -1;
    uint32_t number = 0;
    for (const char *c = id + 8; *c; c++) {
        if (*c < '0' || *c > '9' || number > 400000000u) return -1;
        number = number * 10u + (uint32_t)(*c - '0');
    }
    for (uint32_t i = 0; i < NE_BRIDGE_PENDING; i++) {
        if (b->pending[i].state != NE_PENDING_FREE && b->pending[i].number == number) return (int)i;
    }
    return -1;
}

void ne_bridge_answer(ne_bridge *b, const char *confirmation_id, int approve,
                      const char *from_id, ne_bridge_result *out)
{
    if (out == NULL) return;
    memset(out, 0, sizeof *out);
    if (b == NULL) {
        rejected(out, "", "no bridge");
        return;
    }
    expire_due(b, b->hal.now_ms(b->hal.ctx));
    /* the sender first, as `_check` does: who may answer is decided before what, and a
       stranger learns nothing about which questions exist */
    if (b->owner[0] == '\0' || from_id == NULL || strcmp(from_id, b->owner) != 0) {
        rejected(out, "", "only the owner may answer, on the board's button or in Telegram; "
                          "this sender may not");
        return;
    }
    int slot = slot_of(b, confirmation_id);
    const char *tool = slot >= 0 ? b->agent->actions[b->pending[slot].action].name : "";
    if (slot < 0) {
        rejected(out, tool, "no such question");
        return;
    }
    answer(b, slot, approve, out);
}

void ne_bridge_answer_button(ne_bridge *b, const char *confirmation_id, int approve,
                             ne_bridge_result *out)
{
    if (out == NULL) return;
    memset(out, 0, sizeof *out);
    if (b == NULL) {
        rejected(out, "", "no bridge");
        return;
    }
    expire_due(b, b->hal.now_ms(b->hal.ctx));
    /* the question the board shows, by its id: a press means that question, never "the
       latest", which the brain controls by asking again */
    int slot = slot_of(b, confirmation_id);
    if (slot < 0) {
        rejected(out, "", "no such question");
        return;
    }
    answer(b, slot, approve, out);
}

/* --- reading a result back (the nc_gate adapter, DP-B-06) --------------------------------- */

int ne_bridge_result_field(const ne_bridge_result *r, const char *object, const char *name,
                           char *out, uint32_t cap)
{
    ne_bridge_span top, inner, value;
    uint32_t n = 0;
    if (out == NULL || cap == 0u) return -1;
    out[0] = '\0';
    if (r == NULL || name == NULL || whole(r->json, &top) != 0) return -1;
    if (object != NULL) {
        if (member(&top, object, &inner) != 0) return -1;
        top = inner;
    }
    if (member(&top, name, &value) != 0) return -1;
    if (value.type == J_ARRAY) { /* `problems`: the first one */
        reader list;
        ne_bridge_span first;
        open_container(&list, &value);
        if (next_item(&list, NULL, &first) != 1) return -1;
        value = first;
    }
    if (value.type == J_STRING) {
        if (decode(&value, out, cap - 1u, &n) != 0) {
            out[0] = '\0';
            return -1;
        }
    } else if (value.type == J_NUMBER) {
        if (value.n >= cap) return -1;
        memcpy(out, value.p, value.n);
        n = value.n;
    } else {
        return -1;
    }
    out[n] = '\0';
    return 0;
}

