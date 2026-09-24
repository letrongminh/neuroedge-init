/*
 * Host runner for the C token ledger (TSK-S4-02).
 *
 *   test_token_host <script.txt>
 *
 * Runs the operation scripts that python/tests/test_c_token.py writes, and
 * prints one line per decision, which the test compares with what the host
 * TokenLedger decided. The script is a test fixture, not an interface:
 *
 *   S <start_ms> <boot_id> <seed>   a new script: fresh ledger, clock, random source
 *   I <p95_ms> <pin_mask> <d>       issue (digest byte i = d + 37 i)  -> "I <status>"
 *   A <handle> <pin>                authorize token <handle>          -> "A <reason> <code>"
 *   T <handle> <pin> <field> <k>    authorize a tampered copy         -> "T <reason> <code>"
 *                                   field 0 nonce bit k, 1 digest bit k, 2 mask bit k,
 *                                   3 issued + 1, 4 ttl + 1, 5 boot_id ^ 1
 *   N <pin>                         authorize NULL                    -> "N <reason> <code>"
 *   C <handle>                      close
 *   W <delta_ms>                    advance the clock (uint32, wraps)
 *   R <boot_id>                     restart: a new ledger; old tokens are kept by the caller
 *   E                               end of script                     -> "E"
 *
 * A handle numbers the successful issues of a script from 0.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ne_token.h"

#define MAX_TOKENS 4096

static unsigned long long rng_state; /* the test's random source; the ledger holds none */

static void fill_random(void *buf, size_t len) {
    uint8_t *p = buf;
    for (size_t i = 0; i < len; i++) {
        rng_state ^= rng_state << 13;
        rng_state ^= rng_state >> 7;
        rng_state ^= rng_state << 17;
        p[i] = (uint8_t)(rng_state >> 24);
    }
}

static void print_reason(char op, ne_token_reason r) {
    const char *code = ne_token_reason_code(r);
    printf("%c %d %s\n", op, (int)r, code[0] ? code : "-");
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <script.txt>\n", argv[0]);
        return 2;
    }
    FILE *f = fopen(argv[1], "r");
    if (!f) {
        perror(argv[1]);
        return 2;
    }
    ne_token *tokens = calloc(MAX_TOKENS, sizeof *tokens);
    if (!tokens) return 2;
    ne_ledger ledger;
    ne_tree tree;
    uint8_t digest[NE_DIGEST_SIZE];
    uint32_t now = 0;
    unsigned count = 0;
    char op;
    int bad = 0;
    memset(&tree, 0, sizeof tree);
    ne_ledger_init(&ledger, 0);

    while (fscanf(f, " %c", &op) == 1) {
        unsigned long a = 0, b = 0, c = 0, d = 0;
        switch (op) {
        case 'S':
            if (fscanf(f, "%lu %lu %lu", &a, &b, &c) != 3) bad = 1;
            now = (uint32_t)a;
            ne_ledger_init(&ledger, (uint32_t)b);
            rng_state = (unsigned long long)c * 2654435761ull + 1ull;
            count = 0;
            break;
        case 'I': {
            if (fscanf(f, "%lu %lu %lu", &a, &b, &c) != 3) bad = 1;
            for (uint32_t i = 0; i < NE_DIGEST_SIZE; i++) digest[i] = (uint8_t)(c + 37u * i);
            tree.gate_digest = digest;
            tree.p95_latency_ms = (uint32_t)a;
            ne_token out;
            ne_token_status s = ne_token_issue(&ledger, &tree, (uint32_t)b, now, fill_random, &out);
            if (s == NE_TOKEN_OK) {
                if (count >= MAX_TOKENS) return 2;
                tokens[count++] = out;
            }
            printf("I %d\n", (int)s);
            break;
        }
        case 'A':
            if (fscanf(f, "%lu %lu", &a, &b) != 2 || a >= count) bad = 1;
            else print_reason('A', ne_token_authorize(&ledger, &tokens[a], (uint32_t)b, now));
            break;
        case 'T': {
            if (fscanf(f, "%lu %lu %lu %lu", &a, &b, &c, &d) != 4 || a >= count) {
                bad = 1;
                break;
            }
            ne_token t = tokens[a];
            if (c == 0) t.nonce[(d / 8u) % NE_NONCE_SIZE] ^= (uint8_t)(1u << (d % 8u));
            else if (c == 1) t.gate_digest[(d / 8u) % NE_DIGEST_SIZE] ^= (uint8_t)(1u << (d % 8u));
            else if (c == 2) t.pin_mask ^= 1u << (d % 32u);
            else if (c == 3) t.issued_ms += 1u;
            else if (c == 4) t.ttl_ms += 1u;
            else t.boot_id ^= 1u;
            print_reason('T', ne_token_authorize(&ledger, &t, (uint32_t)b, now));
            break;
        }
        case 'N':
            if (fscanf(f, "%lu", &a) != 1) bad = 1;
            print_reason('N', ne_token_authorize(&ledger, NULL, (uint32_t)a, now));
            break;
        case 'C':
            if (fscanf(f, "%lu", &a) != 1 || a >= count) bad = 1;
            else ne_token_close(&ledger, &tokens[a]);
            break;
        case 'W':
            if (fscanf(f, "%lu", &a) != 1) bad = 1;
            now += (uint32_t)a;
            break;
        case 'R':
            if (fscanf(f, "%lu", &a) != 1) bad = 1;
            ne_ledger_init(&ledger, (uint32_t)a);
            break;
        case 'E':
            printf("E\n");
            break;
        default:
            bad = 1;
        }
        if (bad) {
            fprintf(stderr, "malformed script near op '%c'\n", op);
            return 2;
        }
    }
    fclose(f);
    free(tokens);
    return 0;
}
