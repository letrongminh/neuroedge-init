/*
 * NeuroEdge single-use verdict tokens — see ne_token.h. C99; no heap, no static
 * or global state, no recursion. The ledger is the caller's memory.
 */
#include "ne_token.h"

#include <string.h>

/* OR of the byte differences: no early exit, so the time taken does not depend on
 * where two nonces first differ. */
static uint32_t diff_bytes(const uint8_t *a, const uint8_t *b, uint32_t n) {
    uint32_t d = 0u;
    for (uint32_t i = 0; i < n; i++) d |= (uint32_t)(a[i] ^ b[i]);
    return d;
}

/* Zero iff every field of the two tokens is equal (the host's `!= signature`). */
static uint32_t diff_token(const ne_token *a, const ne_token *b) {
    return diff_bytes(a->nonce, b->nonce, NE_NONCE_SIZE) |
           diff_bytes(a->gate_digest, b->gate_digest, NE_DIGEST_SIZE) |
           (a->boot_id ^ b->boot_id) | (a->pin_mask ^ b->pin_mask) |
           (a->issued_ms ^ b->issued_ms) | (a->ttl_ms ^ b->ttl_ms);
}

/* The slot that issued exactly this token, or -1. Every slot is compared. */
static int find_slot(const ne_ledger *ledger, const ne_token *token) {
    int found = -1;
    for (uint32_t i = 0; i < NE_TOKEN_SLOTS; i++) {
        const ne_token_slot *slot = &ledger->slots[i];
        uint32_t same = diff_token(&slot->token, token) == 0u;
        if (same && slot->state != NE_SLOT_FREE) found = (int)i;
    }
    return found;
}

/* Wrap-safe: the unsigned difference is the age for any token younger than 2^32 ms. */
static int expired(const ne_token *token, uint32_t now_ms) {
    return (uint32_t)(now_ms - token->issued_ms) > token->ttl_ms;
}

static uint32_t ttl_of(uint32_t p95_ms) {
    return p95_ms > UINT32_MAX / NE_TTL_FACTOR ? UINT32_MAX : p95_ms * NE_TTL_FACTOR;
}

ne_token_status ne_ledger_init(ne_ledger *ledger, uint32_t boot_id) {
    if (ledger == NULL) return NE_TOKEN_ERR_ARGUMENT;
    memset(ledger, 0, sizeof *ledger);
    ledger->boot_id = boot_id;
    return NE_TOKEN_OK;
}

ne_token_status ne_token_issue(ne_ledger *ledger, const ne_tree *tree, uint32_t pin_mask,
                               uint32_t now_ms, ne_random_fn fill_random, ne_token *out) {
    if (out != NULL) memset(out, 0, sizeof *out);
    if (ledger == NULL || tree == NULL || tree->gate_digest == NULL || fill_random == NULL ||
        out == NULL)
        return NE_TOKEN_ERR_ARGUMENT;

    /* A free slot, or one whose token can no longer authorise anything. */
    ne_token_slot *slot = NULL;
    for (uint32_t i = 0; i < NE_TOKEN_SLOTS && slot == NULL; i++) {
        ne_token_slot *candidate = &ledger->slots[i];
        if (candidate->state != NE_SLOT_ISSUED || expired(&candidate->token, now_ms))
            slot = candidate;
    }
    if (slot == NULL) return NE_TOKEN_ERR_FULL; /* no token, no action */

    ne_token token;
    fill_random(token.nonce, NE_NONCE_SIZE);
    memcpy(token.gate_digest, tree->gate_digest, NE_DIGEST_SIZE);
    token.boot_id = ledger->boot_id;
    token.pin_mask = pin_mask;
    token.issued_ms = now_ms;
    token.ttl_ms = ttl_of(tree->p95_latency_ms);

    slot->token = token;
    slot->consumed_mask = 0u;
    slot->state = NE_SLOT_ISSUED;
    *out = token;
    return NE_TOKEN_OK;
}

ne_token_reason ne_token_authorize(ne_ledger *ledger, const ne_token *token, uint32_t pin,
                                   uint32_t now_ms) {
    /* The host's order: python/neuroedge/actions/token.py `authorize`. */
    if (ledger == NULL || token == NULL) return NE_TOKEN_NOT_A_TOKEN;
    if (token->boot_id != ledger->boot_id) return NE_TOKEN_EXPIRED; /* minted before a restart */
    int index = find_slot(ledger, token);
    if (index < 0) return NE_TOKEN_UNKNOWN_TOKEN;
    ne_token_slot *slot = &ledger->slots[index];
    if (pin >= NE_MAX_PINS || (token->pin_mask & (1u << pin)) == 0u)
        return NE_TOKEN_PIN_NOT_GRANTED;
    if (slot->state == NE_SLOT_CLOSED || (slot->consumed_mask & (1u << pin)) != 0u)
        return NE_TOKEN_REPLAYED;
    if (expired(token, now_ms)) return NE_TOKEN_EXPIRED;
    slot->consumed_mask |= 1u << pin;
    return NE_TOKEN_AUTHORIZED;
}

void ne_token_close(ne_ledger *ledger, const ne_token *token) {
    if (ledger == NULL || token == NULL || token->boot_id != ledger->boot_id) return;
    int index = find_slot(ledger, token);
    if (index >= 0) ledger->slots[index].state = NE_SLOT_CLOSED;
}

const char *ne_token_reason_name(ne_token_reason reason) {
    if (reason == NE_TOKEN_AUTHORIZED) return "authorized";
    if (reason == NE_TOKEN_NOT_A_TOKEN) return "not_a_token";
    if (reason == NE_TOKEN_UNKNOWN_TOKEN) return "unknown_token";
    if (reason == NE_TOKEN_PIN_NOT_GRANTED) return "pin_not_granted";
    if (reason == NE_TOKEN_REPLAYED) return "token_replayed";
    if (reason == NE_TOKEN_EXPIRED) return "token_expired";
    return "unknown_reason";
}

const char *ne_token_reason_code(ne_token_reason reason) {
    if (reason == NE_TOKEN_AUTHORIZED) return "";
    if (reason == NE_TOKEN_REPLAYED || reason == NE_TOKEN_EXPIRED) return "NE1002";
    return "NE1001";
}
