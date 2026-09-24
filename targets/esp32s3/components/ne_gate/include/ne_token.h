/*
 * NeuroEdge single-use verdict tokens on the device — C99, no allocation, no
 * globals, no recursion.
 *
 * The device form of python/neuroedge/actions/token.py (TSK-S2-05, FR-ACE-02):
 * an ALLOW becomes a token, and a pin moves only on a token this ledger issued,
 * for that pin, once, within its TTL (p95 x 3). The refusal reasons, their
 * NE1001/NE1002 codes and the order they are checked in are the host's, pinned
 * by the differential test python/tests/test_c_token.py.
 *
 * Two differences from the host, both on the closed side:
 *   - the ledger is a fixed array of NE_TOKEN_SLOTS slots, owned by the caller.
 *     `ne_token_issue` reuses a closed or expired slot; when every slot holds a
 *     live token it refuses (NE_TOKEN_ERR_FULL): no token, no action. A token
 *     whose slot was reused is forgotten, and presenting it is `unknown_token`;
 *   - `boot_id` (random at boot) plays `process_instance_id`: a token from
 *     before a restart is `token_expired`.
 *
 * Time is a uint32 millisecond counter that may wrap: expiry is computed as
 * `(uint32_t)(now - issued) > ttl`, which holds across the wrap for any
 * token younger than 2^32 ms (~49 days).
 */
#ifndef NE_TOKEN_H
#define NE_TOKEN_H

#include <stddef.h>
#include <stdint.h>

#include "ne_walker.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NE_TOKEN_SLOTS 4u
#define NE_NONCE_SIZE 16u
#define NE_DIGEST_SIZE 32u
#define NE_TTL_FACTOR 3u
#define NE_MAX_PINS 32u /* pin i is bit i of a token's pin mask */

/* A random source with the shape of ESP-IDF's `esp_fill_random`. */
typedef void (*ne_random_fn)(void *buf, size_t len);

/* What the caller holds and presents. Nonces never belong in a trace. */
typedef struct {
    uint8_t nonce[NE_NONCE_SIZE];
    uint8_t gate_digest[NE_DIGEST_SIZE];
    uint32_t boot_id;
    uint32_t pin_mask;
    uint32_t issued_ms;
    uint32_t ttl_ms;
} ne_token;

typedef enum { NE_SLOT_FREE = 0, NE_SLOT_ISSUED = 1, NE_SLOT_CLOSED = 2 } ne_slot_state;

typedef struct {
    ne_token token;
    uint32_t consumed_mask; /* pins already driven on this token */
    uint8_t state;          /* ne_slot_state */
} ne_token_slot;

/* Caller-allocated (a task's stack or a static in the application). */
typedef struct {
    uint32_t boot_id;
    ne_token_slot slots[NE_TOKEN_SLOTS];
} ne_ledger;

typedef enum {
    NE_TOKEN_OK = 0,
    NE_TOKEN_ERR_ARGUMENT = 1, /* NULL pointer */
    NE_TOKEN_ERR_FULL = 2      /* every slot holds a live token: fail closed */
} ne_token_status;

/* ne_token_authorize() results — python/neuroedge/actions/token.py reasons. */
typedef enum {
    NE_TOKEN_AUTHORIZED = 0,
    NE_TOKEN_NOT_A_TOKEN = 1,     /* NE1001 */
    NE_TOKEN_UNKNOWN_TOKEN = 2,   /* NE1001 */
    NE_TOKEN_PIN_NOT_GRANTED = 3, /* NE1001 */
    NE_TOKEN_REPLAYED = 4,        /* NE1002 */
    NE_TOKEN_EXPIRED = 5          /* NE1002 */
} ne_token_reason;

/* An empty ledger for this boot. `boot_id` should be random (esp_random()). */
ne_token_status ne_ledger_init(ne_ledger *ledger, uint32_t boot_id);

/*
 * Mint a token for an ALLOW of `tree`: a fresh nonce from `fill_random`, the tree's
 * gate_digest, `pin_mask`, issued at `now_ms`, TTL = p95 x 3 (saturating).
 */
ne_token_status ne_token_issue(ne_ledger *ledger, const ne_tree *tree, uint32_t pin_mask,
                               uint32_t now_ms, ne_random_fn fill_random, ne_token *out);

/*
 * May `pin` be driven on `token` now? NE_TOKEN_AUTHORIZED consumes the pin on
 * that token. Any other value is a refusal: the pin must not move.
 */
ne_token_reason ne_token_authorize(ne_ledger *ledger, const ne_token *token, uint32_t pin,
                                   uint32_t now_ms);

/* The action returned: the token is spent for every pin. Unknown tokens are ignored. */
void ne_token_close(ne_ledger *ledger, const ne_token *token);

/* "unknown_token", ... as in the host's `actuator_command_rejected` event. */
const char *ne_token_reason_name(ne_token_reason reason);
/* "NE1001" or "NE1002" for a refusal; "" for NE_TOKEN_AUTHORIZED. */
const char *ne_token_reason_code(ne_token_reason reason);

#ifdef __cplusplus
}
#endif

#endif /* NE_TOKEN_H */
