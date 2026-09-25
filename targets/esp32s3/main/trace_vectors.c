/*
 * The canonical traces, replayed on the device — see trace_vectors.h.
 */
#include "trace_vectors.h"

#include <stddef.h>

#include "vectors/canonical_vectors.h"

static uint32_t now(const ne_trace_sink *sink) {
    return sink->now_ms != NULL ? sink->now_ms(sink->ctx) : 0u;
}

/* One recorded gate evaluation: the device decides, and drives only what its token allows. */
static int replay_step(ne_trace_sink *sink, const ne_vector_step *step, ne_ledger *ledger,
                       ne_random_fn fill_random) {
    ne_tree tree;
    ne_result r;
    ne_token token;
    if (step->gate >= NE_VECTOR_GATES) return 1;
    const ne_vector_gate *g = &ne_vector_gates[step->gate];
    if (ne_tree_load(&tree, g->tree, g->tree_size) != NE_OK) return 1;
    ne_trace_put(sink, ne_trace_gate_begin(sink->buf, sink->cap, ne_trace_offset(sink), g->label,
                                           &tree));
    ne_trace_put(sink, ne_trace_gate_facts(sink->buf, sink->cap, ne_trace_offset(sink), &tree,
                                           step->facts, step->sources));
    if (ne_decide(&tree, step->facts, NULL, step->confirmed, (ne_degraded)step->degraded, &r) !=
        NE_OK)
        return 1;
    ne_trace_put(sink, ne_trace_gate_result(sink->buf, sink->cap, ne_trace_offset(sink), g->label,
                                            &tree, step->facts, &r, &g->text));
    if (r.verdict != NE_ALLOW) return 0;

    if (ne_token_issue(ledger, &tree, step->pin_mask, now(sink), fill_random, &token) !=
        NE_TOKEN_OK)
        return 1;
    for (uint32_t c = 0; c < step->command_count; c++) {
        const ne_vector_command *command = &step->commands[c];
        const ne_token_reason why = ne_token_authorize(ledger, &token, command->pin_index, now(sink));
        if (why == NE_TOKEN_AUTHORIZED)
            ne_trace_put(sink, ne_trace_actuator_command(sink->buf, sink->cap, ne_trace_offset(sink),
                                                         command->pin, command->operation,
                                                         command->duration_ms));
        else
            ne_trace_put(sink, ne_trace_actuator_rejected(sink->buf, sink->cap,
                                                          ne_trace_offset(sink), command->pin, why));
    }
    ne_token_close(ledger, &token);
    return 0;
}

int neuroedge_trace_vectors(ne_trace_sink *sink, const ne_device_info *device, ne_ledger *ledger,
                            ne_random_fn fill_random, uint32_t boot_id) {
    int sessions = 0;
    if (sink == NULL || device == NULL || ledger == NULL || fill_random == NULL) return -1;
    for (uint32_t v = 0; v < NE_VECTORS; v++) {
        const ne_vector *vector = &ne_vectors[v];
        ne_device_info info = *device;
        info.agent_version = vector->agent_version;
        info.replay_of = vector->replay_of;
        info.trace_digest = vector->trace_digest;
        if (ne_ledger_init(ledger, boot_id) != NE_TOKEN_OK) return -1;
        ne_trace_open(sink, &info);
        for (uint32_t s = 0; s < vector->step_count; s++)
            if (replay_step(sink, &vector->steps[s], ledger, fill_random) != 0) return -1;
        ne_trace_close(sink);
        sessions++;
    }
    return sessions;
}
