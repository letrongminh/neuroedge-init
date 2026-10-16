/*
 * Host harness of ne_hal (TSK-S4-01, DP-B-08), driven by python/tests/test_c_hal.py: every
 * case prints `case<TAB>name<TAB>status<TAB>reason<TAB>levels`, the levels the fake writer holds.
 */
#include <stdio.h>
#include <string.h>

#include "ne_hal.h"

#define PINS 3u

static uint8_t levels[PINS];
static unsigned writes;
static unsigned rng = 7u;

static int fake_write(void *ctx, uint32_t pin, uint8_t level)
{
    (void)ctx;
    levels[pin] = level;
    writes++;
    return 0;
}

static void fill(void *buf, size_t len)
{
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) {
        rng = rng * 1103515245u + 12345u;
        p[i] = (unsigned char)(rng >> 16);
    }
}

/* `why` by address: read after the call it comes from (argument order is unspecified in C). */
static void report(const char *name, ne_hal_status status, const ne_token_reason *why)
{
    printf("case\t%s\t%d\t%s\t%u%u%u\n", name, (int)status, ne_token_reason_name(*why), levels[0],
           levels[1], levels[2]);
}

int main(void)
{
    ne_ledger ledger;
    ne_tree tree;
    ne_token token, other;
    ne_token_reason why;
    const ne_hal hal = {{NULL, fake_write}, &ledger, PINS};

    memset(&tree, 0, sizeof tree);
    tree.p95_latency_ms = 100u;
    static const uint8_t digest[NE_DIGEST_SIZE] = {1};
    tree.gate_digest = digest; /* the ledger copies NE_DIGEST_SIZE bytes from it */
    ne_ledger_init(&ledger, 0x1234u);

    report("no token", ne_hal_on(&hal, NULL, 0u, 10u, &why), &why);
    ne_token_issue(&ledger, &tree, 0x1u, 10u, fill, &token); /* pin 0 only */
    report("another pin", ne_hal_on(&hal, &token, 1u, 11u, &why), &why);
    report("its pin", ne_hal_on(&hal, &token, 0u, 12u, &why), &why);
    report("again", ne_hal_on(&hal, &token, 0u, 13u, &why), &why);
    why = NE_TOKEN_AUTHORIZED;
    report("off, no token", ne_hal_off(&hal, 0u), &why);
    ne_token_issue(&ledger, &tree, 0x4u, 20u, fill, &other); /* pin 2 */
    ne_token_close(&ledger, &other);
    report("closed token", ne_hal_on(&hal, &other, 2u, 21u, &why), &why);
    ne_token_issue(&ledger, &tree, 0x4u, 30u, fill, &other);
    report("expired", ne_hal_on(&hal, &other, 2u, 30u + 301u, &why), &why);
    ne_token_issue(&ledger, &tree, 0x4u, 400u, fill, &other);
    other.nonce[0] ^= 1u;
    report("forged", ne_hal_on(&hal, &other, 2u, 401u, &why), &why);
    report("no such pin", ne_hal_on(&hal, &token, PINS, 402u, &why), &why);
    printf("writes\t%u\n", writes);
    return 0;
}
