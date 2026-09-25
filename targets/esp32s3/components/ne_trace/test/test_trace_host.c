/*
 * Host runner for ne_trace (TSK-S4-09), driven by python/tests/test_c_trace.py.
 *
 * Prints `<case>\t<line>` for every formatter case — the Python test parses each
 * line as JSON and compares it with the event the host would write — then checks
 * in C what only C can: every case at every buffer size from 0 to its length + 1
 * either fits exactly or returns -1 leaving an empty buffer, and the sink counts
 * a line it could not fit. Exit 0 and a last line "ALL OK" when every check held.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "ne_trace.h"

#include "gates/home_voice_indices.h"
#include "gates/light_off.netree.h"
#include "gates/light_on.netree.h"

static int failures = 0;

static void check(int ok, const char *what) {
    if (!ok) {
        printf("FAIL\t%s\n", what);
        failures++;
    }
}

static ne_tree on, off;
static ne_fact facts[NE_LIGHT_OFF_NODES];
static const char *sources[NE_LIGHT_OFF_NODES] = {NULL, "sensor"};
static char long_text[700];

static ne_fact fact(uint8_t index) {
    ne_fact f;
    memset(&f, 0, sizeof f);
    f.present = 1u;
    f.in_domain = 1u;
    f.index = index;
    return f;
}

#define CASES 18

/* Case `which` into (buf, cap); its name in *name. */
static int format(int which, char *buf, size_t cap, const char **name) {
    ne_device_info info = {"esp32s3-box-3", NE_AGENT_VERSION, "qemu", 0xdeadbeefu, NULL, NULL};
    ne_on_block_text text = NE_LIGHT_OFF_ON_BLOCK_TEXT;
    ne_result r;
    memset(&r, 0, sizeof r);
    memset(facts, 0, sizeof facts);
    switch (which) {
    case 0:
        *name = "device_info";
        return ne_trace_device_info(buf, cap, &info);
    case 1:
        *name = "device_info_replay";
        info.replay_of = "happy-path.json";
        info.trace_digest = "sha256:0123";
        return ne_trace_device_info(buf, cap, &info);
    case 2:
        *name = "device_info_escaped";
        info.board_id = "a\"b\\c\x01\x1f d\xc3\xa9";
        return ne_trace_device_info(buf, cap, &info);
    case 3:
        *name = "gate_begin";
        return ne_trace_gate_begin(buf, cap, 7u, NE_LIGHT_OFF_GATE, &off);
    case 4:
        *name = "gate_facts";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_LOCAL_GRAMMAR);
        facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_TRUE);
        facts[NE_LIGHT_OFF_ROOM_EMPTY].has_confidence = 1u;
        facts[NE_LIGHT_OFF_ROOM_EMPTY].confidence = 0.96;
        return ne_trace_gate_facts(buf, cap, 8u, &off, facts, sources);
    case 5:
        *name = "gate_facts_unreadable";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(0u);
        facts[NE_LIGHT_OFF_CALL_SOURCE].in_domain = 0u; /* a value outside the domain */
        facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_FALSE);
        facts[NE_LIGHT_OFF_ROOM_EMPTY].has_confidence = 1u;
        facts[NE_LIGHT_OFF_ROOM_EMPTY].confidence = NAN;
        return ne_trace_gate_facts(buf, cap, 9u, &off, facts, NULL);
    case 6:
        *name = "gate_facts_none";
        return ne_trace_gate_facts(buf, cap, 9u, &off, facts, NULL);
    case 7:
        *name = "result_allow";
        facts[NE_LIGHT_ON_CALL_SOURCE] = fact(NE_LIGHT_ON_CALL_SOURCE_MCP);
        return ne_trace_gate_result(buf, cap, 10u, NE_LIGHT_ON_GATE, &on, facts, &r, NULL);
    case 8:
        *name = "result_block_ask";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_SYSTEM_TWO);
        facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_FALSE);
        r.verdict = NE_BLOCK;
        r.reason = NE_REASON_CONDITION_NOT_MET;
        r.failed_kind = NE_FAILED_CRITERION;
        r.failed_index = NE_LIGHT_OFF_ROOM_EMPTY;
        return ne_trace_gate_result(buf, cap, 11u, NE_LIGHT_OFF_GATE, &off, facts, &r, &text);
    case 9:
        *name = "result_confirmed";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_LOCAL_GRAMMAR);
        facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_FALSE);
        r.confirmed_mask = (1u << NE_LIGHT_OFF_ROOM_EMPTY) | (1u << NE_LIGHT_OFF_CALL_SOURCE);
        return ne_trace_gate_result(buf, cap, 12u, NE_LIGHT_OFF_GATE, &off, facts, &r, &text);
    case 10:
        *name = "result_argument";
        facts[NE_LIGHT_ON_CALL_SOURCE] = fact(NE_LIGHT_ON_CALL_SOURCE_MCP);
        r.verdict = NE_BLOCK;
        r.reason = NE_REASON_ARGUMENT_OUT_OF_RANGE;
        r.failed_kind = NE_FAILED_ARGUMENT;
        return ne_trace_gate_result(buf, cap, 13u, NE_LIGHT_ON_GATE, &on, facts, &r, NULL);
    case 11:
        *name = "actuator_command";
        return ne_trace_actuator_command(buf, cap, 14u, "door_lock", "pulse", 30000u);
    case 12:
        *name = "actuator_rejected";
        return ne_trace_actuator_rejected(buf, cap, 15u, "door_lock", NE_TOKEN_REPLAYED);
    case 13:
        *name = "trace_end";
        return ne_trace_end(buf, cap, 4294967295u, 19u);
    case 14:
        *name = "too_long";
        info.agent_version = long_text;
        return ne_trace_device_info(buf, cap, &info);
    case 15:
        *name = "rejected_authorized";
        return ne_trace_actuator_rejected(buf, cap, 16u, "door_lock", NE_TOKEN_AUTHORIZED);
    case 16:
        *name = "result_closed";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_LOCAL_GRAMMAR);
        r.verdict = NE_BLOCK;
        r.reason = NE_REASON_GATE_UNREACHABLE;
        r.fail_mode = NE_FAIL_MODE_CLOSED;
        return ne_trace_gate_result(buf, cap, 17u, NE_LIGHT_OFF_GATE, &off, facts, &r, &text);
    case 17:
        *name = "result_open";
        facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_LOCAL_GRAMMAR);
        r.reason = NE_REASON_BUDGET_EXCEEDED;
        r.fail_mode = NE_FAIL_MODE_OPEN;
        return ne_trace_gate_result(buf, cap, 18u, NE_LIGHT_OFF_GATE, &off, facts, &r, &text);
    default:
        *name = "?";
        return -1;
    }
}

/* --- a sink that keeps its lines -------------------------------------------------------- */

typedef struct {
    char lines[8][NE_TRACE_LINE_MAX + 1];
    int count;
    uint32_t clock;
} memory;

static void keep(void *ctx, const char *line) {
    memory *m = ctx;
    if (m->count < 8) strcpy(m->lines[m->count++], line);
}

static uint32_t tick(void *ctx) {
    memory *m = ctx;
    return m->clock += 5u;
}

int main(void) {
    static char buf[2048], again[2048];
    const char *name = NULL;

    memset(long_text, 'x', sizeof long_text - 1u);
    long_text[sizeof long_text - 1u] = '\0';
    check(ne_tree_load(&on, ne_tree_light_on, (uint32_t)sizeof ne_tree_light_on) == NE_OK, "load on");
    check(ne_tree_load(&off, ne_tree_light_off, (uint32_t)sizeof ne_tree_light_off) == NE_OK,
          "load off");

    for (int which = 0; which < CASES; which++) {
        const int len = format(which, buf, sizeof buf, &name);
        printf("%s\t%d\t%s\n", name, len, len > 0 ? buf : "");
        if (len <= 0) {
            check(buf[0] == '\0', "a refused line leaves an empty buffer");
            continue;
        }
        check((size_t)len == strlen(buf) && len <= (int)NE_TRACE_LINE_MAX, "length is the line's");
        for (size_t cap = 0; cap <= (size_t)len + 1u; cap++) {
            memset(again, '#', sizeof again);
            const int got = format(which, cap == 0u ? NULL : again, cap, &name);
            if (cap <= (size_t)len) {
                check(got == -1, "a buffer too small is refused");
                check(cap == 0u || again[0] == '\0', "a refused line leaves an empty buffer");
            } else {
                check(got == len && strcmp(again, buf) == 0, "a buffer just large enough fits");
            }
        }
    }

    for (uint32_t i = 0; i <= 7u; i++) {
        const char *reason = ne_reason_name((ne_reason)i);
        printf("reason\t%u\t%s\n", (unsigned)i, reason != NULL ? reason : "-");
    }
    for (uint32_t i = 0; i <= 4u; i++) {
        const char *action = ne_on_block_name(i);
        printf("on_block\t%u\t%s\n", (unsigned)i, action != NULL ? action : "-");
    }
    check(ne_domain_value(&off, NE_LIGHT_OFF_ROOM_EMPTY, 2u) == NULL, "domain value out of range");
    check(ne_domain_value(&off, 9u, 0u) == NULL && ne_criterion_kind(&off, 9u) == -1, "no node 9");

    /* The sink: a line that does not fit is still counted, so trace_end tells the host. */
    static memory m;
    static char line[NE_TRACE_LINE_MAX + 1];
    ne_trace_sink sink = {keep, tick, &m, line, sizeof line, 0, 0, 0};
    const ne_device_info info = {"esp32s3-box-3", NE_AGENT_VERSION, "qemu", 1u, NULL, NULL};
    m.clock = 4294967290u; /* the device clock wraps inside the session */
    ne_trace_open(&sink, &info);
    ne_trace_put(&sink, ne_trace_gate_begin(sink.buf, sink.cap, ne_trace_offset(&sink),
                                            NE_LIGHT_ON_GATE, &on));
    ne_trace_put(&sink, -1);
    ne_trace_put(&sink, 0);
    ne_trace_close(&sink);
    check(sink.lines == 3u && sink.dropped == 1u, "the sink counts a dropped line");
    for (int i = 0; i < m.count; i++) printf("sink\t%d\t%s\n", i, m.lines[i]);

    if (failures == 0)
        printf("ALL OK\n");
    else
        printf("FAILED %d\n", failures);
    return failures == 0 ? 0 : 1;
}
