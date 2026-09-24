/*
 * Boot self-test of the gate runtime — see gate_selftest.h.
 *
 * The expected verdicts are the host engine's for the same gates
 * (fixtures/agents/home-voice/gates/): light_on admits the dispatcher's
 * sources and refuses `test`; light_off also needs room_empty, and on a BLOCK
 * asks a person, whose "có" stands in for room_empty only (RFC-0006).
 */
#include "gate_selftest.h"

#include <stdio.h>
#include <string.h>

#include "ne_walker.h"
#include "gates/home_voice_indices.h"
#include "gates/light_off.netree.h"
#include "gates/light_on.netree.h"

#define ASK 2u

static ne_fact fact(uint8_t index) {
    ne_fact f;
    memset(&f, 0, sizeof f);
    f.present = 1u;
    f.in_domain = 1u;
    f.index = index;
    return f;
}

static int decided(const ne_tree *tree, const ne_fact *facts, int confirmed, ne_verdict verdict,
                   ne_reason reason, uint8_t failed_index, ne_result *out) {
    if (ne_evaluate(tree, facts, NULL, confirmed, out) != NE_OK) return 0;
    if (out->verdict != verdict || out->reason != reason) return 0;
    return verdict == NE_ALLOW || out->failed_index == failed_index;
}

static int fail(char *line, size_t cap, const char *what) {
    snprintf(line, cap, "NE_SELFTEST FAIL %s", what);
    return 1;
}

int neuroedge_gate_selftest(ne_random_fn fill_random, uint32_t boot_id, uint32_t now_ms,
                            char *line, size_t cap) {
    ne_tree on, off;
    ne_result r;
    ne_fact facts[NE_LIGHT_OFF_NODES];
    unsigned walker = 0, token = 0;

    if (line == NULL || cap == 0) return 1;
    if (ne_tree_load(&on, ne_tree_light_on, (uint32_t)sizeof ne_tree_light_on) != NE_OK)
        return fail(line, cap, "load light_on");
    if (ne_tree_load(&off, ne_tree_light_off, (uint32_t)sizeof ne_tree_light_off) != NE_OK)
        return fail(line, cap, "load light_off");
    if (on.node_count != NE_LIGHT_ON_NODES || off.node_count != NE_LIGHT_OFF_NODES)
        return fail(line, cap, "node count");

    /* light_on: the fixed grammar may switch the light on; a `test` caller may not. */
    facts[NE_LIGHT_ON_CALL_SOURCE] = fact(NE_LIGHT_ON_CALL_SOURCE_LOCAL_GRAMMAR);
    if (!decided(&on, facts, 0, NE_ALLOW, NE_REASON_NONE, 0, &r))
        return fail(line, cap, "light_on local_grammar ALLOW");
    walker++;
    facts[NE_LIGHT_ON_CALL_SOURCE] = fact(NE_LIGHT_ON_CALL_SOURCE_TEST);
    if (!decided(&on, facts, 0, NE_BLOCK, NE_REASON_CONDITION_NOT_MET, NE_LIGHT_ON_CALL_SOURCE, &r))
        return fail(line, cap, "light_on test BLOCK");
    walker++;

    /* light_off: room empty => ALLOW. */
    facts[NE_LIGHT_OFF_CALL_SOURCE] = fact(NE_LIGHT_OFF_CALL_SOURCE_LOCAL_GRAMMAR);
    facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_TRUE);
    if (!decided(&off, facts, 0, NE_ALLOW, NE_REASON_NONE, 0, &r))
        return fail(line, cap, "light_off room_empty ALLOW");
    walker++;

    /* Someone in the room => BLOCK on room_empty, and a person may be asked. */
    facts[NE_LIGHT_OFF_ROOM_EMPTY] = fact(NE_LIGHT_OFF_ROOM_EMPTY_FALSE);
    if (!decided(&off, facts, 0, NE_BLOCK, NE_REASON_CONDITION_NOT_MET, NE_LIGHT_OFF_ROOM_EMPTY,
                 &r) ||
        off.on_block_action != ASK || !r.answerable)
        return fail(line, cap, "light_off occupied BLOCK ask");
    walker++;

    /* The person's "có" stands in for room_empty (RFC-0006). */
    if (!decided(&off, facts, 1, NE_ALLOW, NE_REASON_NONE, 0, &r) ||
        r.confirmed_mask != (1u << NE_LIGHT_OFF_ROOM_EMPTY))
        return fail(line, cap, "light_off confirmed ALLOW");
    walker++;

    /* No motion reading => BLOCK: a missing fact never reads as "empty". */
    memset(&facts[NE_LIGHT_OFF_ROOM_EMPTY], 0, sizeof facts[0]);
    if (!decided(&off, facts, 0, NE_BLOCK, NE_REASON_CRITERION_UNAVAILABLE,
                 NE_LIGHT_OFF_ROOM_EMPTY, &r))
        return fail(line, cap, "light_off missing fact BLOCK");
    walker++;

    /* A token for porch_light: once, then token_replayed. */
    ne_ledger ledger;
    ne_token t, spare;
    const uint32_t pin = NE_PIN_PORCH_LIGHT, mask = 1u << NE_PIN_PORCH_LIGHT;
    if (ne_ledger_init(&ledger, boot_id) != NE_TOKEN_OK ||
        ne_token_issue(&ledger, &off, mask, now_ms, fill_random, &t) != NE_TOKEN_OK)
        return fail(line, cap, "token issue");
    token++;
    if (ne_token_authorize(&ledger, &t, pin, now_ms) != NE_TOKEN_AUTHORIZED)
        return fail(line, cap, "token first use");
    token++;
    if (ne_token_authorize(&ledger, &t, pin, now_ms) != NE_TOKEN_REPLAYED)
        return fail(line, cap, "token second use not token_replayed");
    token++;
    if (ne_token_authorize(&ledger, &t, pin + 1u, now_ms) != NE_TOKEN_PIN_NOT_GRANTED)
        return fail(line, cap, "token other pin not pin_not_granted");
    token++;
    spare = t;
    spare.nonce[0] ^= 1u;
    if (ne_token_authorize(&ledger, &spare, pin, now_ms) != NE_TOKEN_UNKNOWN_TOKEN)
        return fail(line, cap, "tampered token not unknown_token");
    token++;

    /* Closed slots are reused; four live tokens fill the ledger, and it fails closed. */
    ne_token_close(&ledger, &t);
    for (uint32_t i = 0; i < NE_TOKEN_SLOTS; i++)
        if (ne_token_issue(&ledger, &on, mask, now_ms, fill_random, &spare) != NE_TOKEN_OK)
            return fail(line, cap, "token slot not reused");
    if (ne_token_issue(&ledger, &on, mask, now_ms, fill_random, &spare) != NE_TOKEN_ERR_FULL)
        return fail(line, cap, "full ledger did not fail closed");
    token++;

    snprintf(line, cap, "NE_SELFTEST PASS walker=%u token=%u", walker, token);
    return 0;
}
