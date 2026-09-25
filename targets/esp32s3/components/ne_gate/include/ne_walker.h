/*
 * NeuroEdge gate walker — C99, no allocation, no globals, no recursion.
 *
 * Reads a decision tree in the `NETR` v1 binary layout (RFC-0003) that
 * `neuroedge build` generates, in place (typically from flash), and decides a
 * gate exactly as the host engine does (python/neuroedge/engine/): the same
 * verdict, the same reason, the same failing criterion — pinned by the truth
 * tables in fixtures/decision_trees/ and python/tests/test_c_walker.py.
 *
 * What stays outside the walker, as on the host: gathering facts within the
 * budget, and the degraded verdicts (gate_unreachable, budget_exceeded) that
 * apply `fail`. The walker decides from the facts it is given.
 */
#ifndef NE_WALKER_H
#define NE_WALKER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NE_LAYOUT_VERSION 1u
#define NE_HEADER_SIZE 64u
#define NE_NODE_SIZE 24u
#define NE_ARG_SIZE 32u
#define NE_ENUM_SIZE 16u
#define NE_MAX_NODES 32u
#define NE_MAX_DOMAIN 32u
#define NE_MAX_ARGS 16u
#define NE_MAX_ENUMS 64u
#define NE_MAX_STRINGS 16384u

/* ne_tree_load() results. */
typedef enum {
    NE_OK = 0,
    NE_ERR_ARGUMENT = 1,   /* NULL pointer */
    NE_ERR_SIZE = 2,       /* shorter than a header, or sizes do not add up */
    NE_ERR_MAGIC = 3,
    NE_ERR_VERSION = 4,    /* a layout this walker does not know */
    NE_ERR_CRC = 5,        /* corrupted in flash or in transit */
    NE_ERR_LIMITS = 6,     /* counts beyond the NE_MAX_* limits */
    NE_ERR_STRUCTURE = 7   /* an offset, index, kind or mask that does not fit */
} ne_status;

typedef enum { NE_ALLOW = 0, NE_BLOCK = 1 } ne_verdict;

/* Same vocabulary as python/neuroedge/engine/verdict.py `Reason`. */
typedef enum {
    NE_REASON_NONE = 0,
    NE_REASON_CONDITION_NOT_MET = 1,
    NE_REASON_CRITERION_UNAVAILABLE = 2,
    NE_REASON_CONFIDENCE_UNAVAILABLE = 3,
    NE_REASON_ARGUMENT_OUT_OF_RANGE = 4
} ne_reason;

typedef enum { NE_FAILED_NONE = 0, NE_FAILED_CRITERION = 1, NE_FAILED_ARGUMENT = 2 } ne_failed_kind;

typedef enum { NE_KIND_BOOL = 0, NE_KIND_LEVEL = 1, NE_KIND_CHOICE = 2 } ne_kind;

typedef enum { NE_ARG_STRING = 0, NE_ARG_INTEGER = 1, NE_ARG_NUMBER = 2, NE_ARG_BOOLEAN = 3 } ne_arg_type;

/* A loaded tree: a view onto the caller's bytes (which must outlive it). */
typedef struct {
    const uint8_t *base;
    uint32_t size;
    uint16_t node_count;
    uint16_t arg_count;
    uint16_t enum_count;
    uint8_t on_block_action; /* 0 deny, 1 escalate, 2 ask, 3 degrade */
    uint8_t fail_open;
    uint32_t p95_latency_ms;
    uint32_t confirm_mask;   /* bit i: criterion i may be stood in for by a person */
    uint32_t strings_size;
    const uint8_t *gate_digest; /* 32 raw bytes */
} ne_tree;

/*
 * One criterion's fact. `present` 0 = no fact; `in_domain` 0 = a value outside
 * the node's domain (or a non-bool for a bool node); `index` = the value's
 * position in the domain. `has_confidence` 0 = no confidence given.
 */
typedef struct {
    uint8_t present;
    uint8_t in_domain;
    uint8_t index;
    uint8_t has_confidence;
    double confidence;
} ne_fact;

/*
 * One argument value, in the tree's argument order. `type` is the value's own
 * JSON type (an integral double is NE_ARG_INTEGER); `str` need not be
 * NUL-terminated.
 */
typedef struct {
    uint8_t present;
    uint8_t type;
    uint32_t str_len;   /* bytes of UTF-8 */
    const char *str;
    double number;      /* numbers; booleans as 0 / 1 */
} ne_arg_value;

typedef struct {
    ne_verdict verdict;
    ne_reason reason;
    ne_failed_kind failed_kind;
    uint8_t failed_index;   /* criterion or argument index */
    uint8_t answerable;     /* BLOCK ask a person's yes would turn into ALLOW (RFC-0006) */
    uint32_t confirmed_mask;/* criteria stood in for on this verdict */
} ne_result;

/* Validate `len` bytes as a NETR v1 tree. Nothing is copied. */
ne_status ne_tree_load(ne_tree *tree, const uint8_t *buf, uint32_t len);

/*
 * Decide the gate. `facts` has `tree->node_count` entries (may be NULL when 0),
 * `args` has `tree->arg_count` entries (may be NULL when 0). `confirmed` is
 * non-zero only after a person answered this gate's ask on the device: the
 * criteria in `confirm_mask` then count as satisfied (RFC-0006).
 * Returns NE_OK, or NE_ERR_ARGUMENT for a NULL tree/out.
 */
ne_status ne_evaluate(const ne_tree *tree, const ne_fact *facts, const ne_arg_value *args,
                      int confirmed, ne_result *out);

/* Name of criterion `i` (NUL-terminated, in the tree), or NULL. For traces. */
const char *ne_criterion_name(const ne_tree *tree, uint32_t i);
/* Name of argument `i`, or NULL. */
const char *ne_argument_name(const ne_tree *tree, uint32_t i);
/* Kind of criterion `i` — NE_KIND_BOOL, NE_KIND_LEVEL, NE_KIND_CHOICE — or -1. For traces. */
int ne_criterion_kind(const ne_tree *tree, uint32_t i);
/* Value `j` of criterion `i`'s domain ("false"/"true" for a bool), or NULL. For traces. */
const char *ne_domain_value(const ne_tree *tree, uint32_t i, uint32_t j);

/* CRC-32 (IEEE 802.3, as zlib) — exposed for tests and OTA tooling. */
uint32_t ne_crc32(const uint8_t *data, uint32_t len, uint32_t skip_from, uint32_t skip_len);

#ifdef __cplusplus
}
#endif

#endif /* NE_WALKER_H */
