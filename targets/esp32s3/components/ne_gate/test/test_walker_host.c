/*
 * Host conformance runner for the C walker (TSK-S4-02, TSK-S4-07).
 *
 *   test_walker_host <tree.netree> <cases.nevc> [<tree> <cases> ...]
 *
 * For each pair: load the tree, run every case through `ne_decide` (with the
 * case's degraded gathering, if any), compare verdict, reason, failing index,
 * answerability, fail mode and confirmed mask with what the Python engine
 * decided (python/tests/test_c_walker.py writes the cases); a case that did not
 * degrade must also be exactly `ne_evaluate`. Then fuzz the tree:
 * every truncation must be refused; single-byte corruption must be refused by
 * the CRC; and structurally mutated trees with a recomputed CRC must either be
 * refused or walk without reading outside the buffer (built with ASan/UBSan).
 * Exit 0 only if every case matches and nothing crashed.
 *
 * The `.nevc` case format is a test fixture, not part of RFC-0003.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ne_walker.h"

#define FACT_SIZE 16u
#define ARG_SIZE 80u
#define TAIL_SIZE 12u

static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static double rdf64(const uint8_t *p) {
    uint64_t bits = (uint64_t)rd32(p) | (uint64_t)rd32(p + 4) << 32;
    double v;
    memcpy(&v, &bits, sizeof v);
    return v;
}

static uint8_t *slurp(const char *path, uint32_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc((size_t)(n > 0 ? n : 1));
    if (!buf || fread(buf, 1, (size_t)n, f) != (size_t)n) {
        fclose(f);
        free(buf);
        return NULL;
    }
    fclose(f);
    *len = (uint32_t)n;
    return buf;
}

static uint32_t xorshift(uint32_t *s) {
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *s = x;
}

static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

/* Walk a (possibly hostile) tree with arbitrary inputs; ASan reports any overread. */
static void exercise(const ne_tree *t, uint32_t *seed) {
    ne_fact facts[NE_MAX_NODES];
    ne_arg_value args[NE_MAX_ARGS];
    static const char text[] = "gi\xe1\xbb\x9bi h\xe1\xba\xa1n";
    for (int round = 0; round < 4; round++) {
        for (uint32_t i = 0; i < NE_MAX_NODES; i++) {
            uint32_t r = xorshift(seed);
            facts[i].present = (uint8_t)(r & 1u);
            facts[i].in_domain = (uint8_t)((r >> 1) & 1u);
            facts[i].index = (uint8_t)((r >> 2) & 0x3Fu);
            facts[i].has_confidence = (uint8_t)((r >> 8) & 1u);
            facts[i].confidence = (double)((r >> 9) & 0x3FFu) / 800.0;
        }
        for (uint32_t i = 0; i < NE_MAX_ARGS; i++) {
            uint32_t r = xorshift(seed);
            args[i].present = (uint8_t)(r & 1u);
            args[i].type = (uint8_t)((r >> 1) & 7u);
            args[i].str = text;
            args[i].str_len = (r >> 4) % (uint32_t)sizeof text;
            args[i].number = (double)((int32_t)(r >> 8) % 200);
        }
        ne_result out;
        if (ne_evaluate(t, facts, args, (int)(xorshift(seed) & 1u), &out) != NE_OK ||
            ne_decide(t, facts, args, (int)(xorshift(seed) & 1u),
                      (ne_degraded)(xorshift(seed) % 3u), &out) != NE_OK) {
            fprintf(stderr, "ne_evaluate / ne_decide refused a loaded tree\n");
            exit(3);
        }
        (void)ne_criterion_name(t, xorshift(seed) % 40u);
        (void)ne_argument_name(t, xorshift(seed) % 20u);
    }
}

static int fuzz(const uint8_t *tree, uint32_t len, const char *name) {
    int bad = 0;
    ne_tree t;
    uint8_t *copy = malloc(len);
    if (!copy) return 1;
    /* 1. Every truncation is refused. */
    for (uint32_t n = 0; n < len; n++) {
        if (ne_tree_load(&t, tree, n) == NE_OK) {
            fprintf(stderr, "%s: a %u-byte truncation loaded\n", name, n);
            bad++;
        }
    }
    /* 2. Any single corrupted byte is refused (CRC, or magic/version first). */
    for (uint32_t i = 0; i < len; i++) {
        memcpy(copy, tree, len);
        copy[i] ^= 0x5Au;
        if (ne_tree_load(&t, copy, len) == NE_OK) {
            fprintf(stderr, "%s: corrupted byte %u loaded\n", name, i);
            bad++;
        }
    }
    /* 3. Hostile structure with a valid CRC: refused, or walked safely. */
    uint32_t seed = 0x9E3779B9u ^ len;
    for (int k = 0; k < 4000; k++) {
        memcpy(copy, tree, len);
        int flips = 1 + (int)(xorshift(&seed) % 4u);
        for (int f = 0; f < flips; f++) {
            uint32_t pos = 40u + xorshift(&seed) % (len - 40u); /* past magic/version/digest */
            if (pos >= 60u && pos < 64u) continue;             /* the CRC itself */
            copy[pos] = (uint8_t)xorshift(&seed);
        }
        put32(copy + 60, ne_crc32(copy, len, 60, 4));
        if (ne_tree_load(&t, copy, len) == NE_OK) exercise(&t, &seed);
    }
    free(copy);
    return bad;
}

static int run_cases(const ne_tree *t, const uint8_t *vec, uint32_t vlen, const char *name) {
    if (vlen < 20u || memcmp(vec, "NEVC", 4) != 0 || rd32(vec + 4) != 2u) {
        fprintf(stderr, "%s: bad case file\n", name);
        return 1;
    }
    uint32_t nodes = rd32(vec + 8), args = rd32(vec + 12), count = rd32(vec + 16);
    if (nodes != t->node_count || args != t->arg_count) {
        fprintf(stderr, "%s: case file is for %u nodes / %u args\n", name, nodes, args);
        return 1;
    }
    uint32_t stride = nodes * FACT_SIZE + args * ARG_SIZE + TAIL_SIZE;
    if (20u + stride * count != vlen) {
        fprintf(stderr, "%s: case file size\n", name);
        return 1;
    }
    int bad = 0;
    ne_fact facts[NE_MAX_NODES];
    ne_arg_value values[NE_MAX_ARGS];
    for (uint32_t c = 0; c < count; c++) {
        const uint8_t *p = vec + 20u + c * stride;
        for (uint32_t i = 0; i < nodes; i++, p += FACT_SIZE) {
            facts[i].present = p[0];
            facts[i].in_domain = p[1];
            facts[i].index = p[2];
            facts[i].has_confidence = p[3];
            facts[i].confidence = rdf64(p + 8);
        }
        for (uint32_t i = 0; i < args; i++, p += ARG_SIZE) {
            values[i].present = p[0];
            values[i].type = p[1];
            values[i].str_len = (uint32_t)(p[2] | p[3] << 8);
            values[i].number = rdf64(p + 8);
            values[i].str = (const char *)(p + 16);
        }
        ne_result out, plain;
        if (ne_decide(t, facts, values, p[0], (ne_degraded)p[6], &out) != NE_OK) {
            fprintf(stderr, "%s case %u: ne_decide failed\n", name, c);
            bad++;
            continue;
        }
        if ((uint8_t)out.verdict != p[1] || (uint8_t)out.reason != p[2] ||
            (uint8_t)out.failed_kind != p[3] || out.failed_index != p[4] ||
            out.answerable != p[5] || out.fail_mode != p[7] || out.confirmed_mask != rd32(p + 8)) {
            fprintf(stderr,
                    "%s case %u (degraded %u): C says verdict=%d reason=%d kind=%d index=%u "
                    "answerable=%u fail_mode=%u confirmed=%x; Python says %u %u %u %u %u %u %x\n",
                    name, c, p[6], out.verdict, out.reason, out.failed_kind, out.failed_index,
                    out.answerable, out.fail_mode, out.confirmed_mask, p[1], p[2], p[3], p[4],
                    p[5], p[7], rd32(p + 8));
            bad++;
        }
        if (p[6] == 0u && (ne_evaluate(t, facts, values, p[0], &plain) != NE_OK ||
                           memcmp(&plain, &out, sizeof out) != 0)) {
            fprintf(stderr, "%s case %u: ne_decide without degradation is not ne_evaluate\n",
                    name, c);
            bad++;
        }
    }
    printf("%s: %u cases, %d mismatches\n", name, count, bad);
    return bad;
}

int main(int argc, char **argv) {
    if (argc < 3 || (argc - 1) % 2 != 0) {
        fprintf(stderr, "usage: %s <tree.netree> <cases.nevc> [...]\n", argv[0]);
        return 2;
    }
    int bad = 0;
    for (int i = 1; i < argc; i += 2) {
        uint32_t tlen = 0, vlen = 0;
        uint8_t *tree = slurp(argv[i], &tlen), *vec = slurp(argv[i + 1], &vlen);
        if (!tree || !vec) {
            fprintf(stderr, "cannot read %s / %s\n", argv[i], argv[i + 1]);
            return 2;
        }
        ne_tree t;
        ne_status status = ne_tree_load(&t, tree, tlen);
        if (status != NE_OK) {
            fprintf(stderr, "%s: load failed (%d)\n", argv[i], status);
            bad++;
        } else {
            bad += run_cases(&t, vec, vlen, argv[i]);
            bad += fuzz(tree, tlen, argv[i]);
        }
        free(tree);
        free(vec);
    }
    printf(bad == 0 ? "ALL OK\n" : "FAILED: %d\n", bad);
    return bad == 0 ? 0 : 1;
}
