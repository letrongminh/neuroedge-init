/*
 * NeuroEdge brain bridge — Profile B (one chip, Q-79, Q-83) — C99, no allocation, no
 * globals, no recursion.
 *
 * NeuroClaw-ESP (the brain) and `ne_gate` (the box) share one ESP32-S3 image. They speak the
 * same contract as over MCP in Profile A, only by function call: the tool list the box would
 * list (`neuroedge mcp serve`, DP-COM-02) and a `tool-result.v1` JSON object for every call
 * (DP-COM-01). docs/spec/deployment_profiles.md, DP-B-02 to DP-B-08, DP-COM-09.
 *
 *   ne_bridge_tool()     the tools: one per @action, name, description, input schema (DP-B-03)
 *   ne_bridge_call()     JSON arguments -> checked against that schema -> ne_arg_value[]
 *                        (DP-B-04); facts from on-chip sources only (DP-B-05); ne_decide;
 *                        an ALLOW runs the action between ne_token_issue and ne_token_close
 *                        (DP-B-08); the result as tool-result.v1 JSON (DP-B-06)
 *   ne_bridge_answer()   the owner's Telegram callback, its user id checked here (DP-B-07)
 *   ne_bridge_answer_button()  the board's button, for the question its screen shows (DP-B-07)
 *
 * What the brain sends is never a fact: `call_source` / `call_channel` are set by the bridge
 * (the brain is a caller like an MCP client: "mcp"), every other criterion is read by the
 * fact source. A question waits in the bridge's own table of NE_BRIDGE_PENDING entries, with
 * the host's TTL max(3 x p95, 10 s), single use; a fifth is BLOCK `budget_exceeded`
 * (DP-COM-09). A "yes" re-reads the facts and decides the stored arguments again with
 * `confirmed` = 1: it stands in for the gate's `confirms` criteria, nothing else.
 *
 * One caller at a time: the brain's task. A button handler posts to that task, or the
 * application holds one lock around every ne_bridge_* call.
 *
 * Where the host is more lenient, the bridge refuses (closed side): arguments longer than
 * NE_BRIDGE_ARGS_MAX, more than NE_BRIDGE_MAX_KEYS keys, a duplicate key, a numeric string
 * that is not a plain decimal. The `nc_gate` adapter for NeuroClaw-ESP is the image's
 * main/brain.c; this component is the part both builds share, and is tested on the host
 * against the box itself (python/tests/test_c_bridge.py).
 */
#ifndef NE_BRAIN_BRIDGE_H
#define NE_BRAIN_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

#include "ne_agent.h"
#include "ne_token.h"
#include "ne_trace.h"
#include "ne_walker.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NE_BRIDGE_CONTRACT "tool-result.v1" /* as _meta["dev.neuroedge/contract"] over MCP */
#define NE_BRIDGE_CALL_SOURCE "mcp"         /* the brain, as the box sees an MCP client */
#define NE_BRIDGE_PENDING 4u                /* DP-COM-09: questions waiting at once */
#define NE_BRIDGE_MIN_TTL_MS 10000u         /* confirmation.py MIN_TTL_MS */
#define NE_BRIDGE_TTL_FACTOR 3u             /* confirmation.py TTL_FACTOR */
#define NE_BRIDGE_ARGS_MAX 256u             /* bytes of one call's arguments JSON */
#define NE_BRIDGE_MAX_KEYS 16u              /* keys of one call's arguments */
#define NE_BRIDGE_KEY_MAX 48u               /* bytes of one argument name */
#ifndef NE_BRIDGE_RESULT_MAX              /* a test builds it smaller to reach the overflow */
#define NE_BRIDGE_RESULT_MAX 1024u          /* bytes of one result, NUL included */
#endif
#define NE_BRIDGE_OWNER_MAX 32u             /* bytes of the owner's Telegram user id */
#define NE_BRIDGE_MAX_FALLBACK 3u           /* conversation.py MAX_FALLBACK_DEPTH */
#define NE_BRIDGE_WHO "the owner, on the board's button or in Telegram; not this caller"

/*
 * On-chip facts (DP-B-05): fill facts[0..count) for `gate` (index `gate_index` of the agent)
 * from HAL inputs, sensors, the clock and the owner's settings, nothing else. The bridge
 * zeroes `facts` first. A value the box itself commanded is not a reading (present 0).
 * Returns how gathering went: NE_DEGRADED_NONE, or why it could not.
 */
typedef struct {
    void *ctx;
    ne_degraded (*read)(void *ctx, const ne_tree *gate, uint32_t gate_index, ne_fact *facts,
                        uint32_t count, uint32_t now_ms);
} ne_fact_source;

/*
 * The device. `run` performs @action `action` (an index of agent->actions) with `args` in its
 * gate's argument order; it moves pins only through ne_hal_on(hal, token, pin, now) (ne_hal.h,
 * which asks ne_token_authorize) and leaves a pin as it is on any refusal (DP-B-08). The bridge
 * closes the token after.
 */
typedef struct {
    void *ctx;
    uint32_t (*now_ms)(void *ctx);
    ne_random_fn fill_random;
    void (*run)(void *ctx, uint32_t action, const ne_arg_value *args, uint32_t arg_count,
                ne_ledger *ledger, const ne_token *token);
} ne_bridge_hal;

typedef enum { NE_BRIDGE_ALLOW = 0, NE_BRIDGE_BLOCK = 1, NE_BRIDGE_REJECTED = 2 } ne_bridge_status;

/* One answer to the brain: `json` is a tool-result.v1 object, NUL-terminated. */
typedef struct {
    ne_bridge_status status;
    uint32_t len;
    char json[NE_BRIDGE_RESULT_MAX];
} ne_bridge_result;

typedef enum {
    NE_PENDING_FREE = 0,
    NE_PENDING_WAITING = 1,
    NE_PENDING_CONFIRMED = 2,
    NE_PENDING_DECLINED = 3,
    NE_PENDING_EXPIRED = 4
} ne_pending_state;

typedef struct {
    uint8_t state;            /* ne_pending_state */
    uint16_t action;          /* index of agent->actions */
    uint32_t number;          /* the id is "confirm_<number>" */
    uint32_t created_ms;
    uint32_t ttl_ms;
    uint8_t digest[NE_DIGEST_SIZE];
    uint32_t args_len;
    char args[NE_BRIDGE_ARGS_MAX]; /* the call's arguments JSON, decided again on "yes" */
} ne_bridge_pending;

/* A span of the arguments JSON: a string's inside (escapes undecoded), or a whole token. */
typedef struct {
    const char *p;
    uint32_t n;
    uint8_t type; /* the JSON type, the bridge's own numbering */
} ne_bridge_span;

/* Static storage (a static in the application): every field is the bridge's own. */
typedef struct {
    const ne_agent *agent;
    ne_ledger *ledger;
    ne_fact_source facts;
    ne_bridge_hal hal;
    char owner[NE_BRIDGE_OWNER_MAX]; /* "" refuses every Telegram answer */
    uint32_t next_number;
    ne_bridge_pending pending[NE_BRIDGE_PENDING];
    /* Scratch for one decision, kept here and not on a task's stack. */
    ne_fact fact_buf[NE_MAX_NODES];
    ne_arg_value arg_buf[NE_MAX_ARGS];
    char text_buf[NE_BRIDGE_ARGS_MAX]; /* decoded argument strings */
    char work[NE_BRIDGE_ARGS_MAX];       /* one string decoded */
    char line[NE_BRIDGE_RESULT_MAX];     /* one problem being worded */
    char problems[NE_BRIDGE_RESULT_MAX]; /* every problem of one call */
    char saved[NE_BRIDGE_ARGS_MAX];      /* a question's arguments, decided again */
    char name[NE_BRIDGE_KEY_MAX + 4u];   /* one argument name decoded */
    char cmp[2][NE_BRIDGE_KEY_MAX + 4u]; /* two names compared */
    int opened;                          /* the question this call opened, or -1 */
    ne_bridge_span keys[NE_BRIDGE_MAX_KEYS];
    ne_bridge_span values[NE_BRIDGE_MAX_KEYS];
    uint32_t key_count;
    ne_trace_sink *trace;             /* NULL: no NE1 lines (ne_bridge_trace) */
    const ne_device_info *trace_info; /* each session's device_info */
} ne_bridge;

/*
 * `owner_id` is `telegram.owner` of ne_config (NULL or "": no Telegram answer is accepted).
 * Every pointer must outlive the bridge. Returns 0, or -1 for a NULL or too long argument.
 */
int ne_bridge_init(ne_bridge *b, const ne_agent *agent, ne_ledger *ledger,
                   const ne_fact_source *facts, const ne_bridge_hal *hal, const char *owner_id);

/* The tools, in the order `neuroedge mcp serve` lists them (by name). */
uint32_t ne_bridge_tool_count(const ne_bridge *b);
/* Tool `i`: its name, description and input schema (compact JSON). Returns 0, or -1. */
int ne_bridge_tool(const ne_bridge *b, uint32_t i, const char **name, const char **description,
                   const char **input_schema);

/* Decide one call. `arguments_json` may be NULL or "" for {}. Always fills `out`. */
void ne_bridge_call(ne_bridge *b, const char *name, const char *arguments_json,
                    ne_bridge_result *out);

/*
 * The owner answered `confirmation_id` in Telegram; `from_id` is the user id Telegram reports
 * for that press. Accepted only when it equals the owner set at init (DP-B-07, C4). A refused
 * answer is REJECTED, a "no" is BLOCK `declined`, a "yes" is the call decided again.
 */
void ne_bridge_answer(ne_bridge *b, const char *confirmation_id, int approve,
                      const char *from_id, ne_bridge_result *out);

/*
 * The board's button answers the question the board shows: `confirmation_id` is the one its
 * screen displayed with the press, never "the latest" (the brain controls what is latest).
 */
void ne_bridge_answer_button(ne_bridge *b, const char *confirmation_id, int approve,
                             ne_bridge_result *out);

/* Questions waiting now (expired ones are not). */
uint32_t ne_bridge_waiting(ne_bridge *b);

/*
 * DP-B-12: from now on every call and answer writes one NE1 session on `sink` (device_info,
 * gate_evaluation_start, gate_facts, gate_evaluation_result per gate decided, trace_end), which
 * `neuroedge record --port` rebuilds and `verify` replays. NULL stops it. `sink` and `info` are
 * the application's and must outlive the bridge.
 */
void ne_bridge_trace(ne_bridge *b, ne_trace_sink *sink, const ne_device_info *info);

/*
 * From the `run` callback: what became of one pin of the action (DP-B-12). Driven:
 * `actuator_command {pin, operation, duration_ms}`; refused by the token: `actuator_rejected`.
 * Nothing when the bridge writes no trace.
 */
void ne_bridge_trace_pin(ne_bridge *b, uint32_t pin, int driven, const char *operation,
                         uint32_t duration_ms, ne_token_reason why);

/*
 * The length of one pulse of `action` (its `ops`, ne_agent.h), for the `run` callback: the
 * op's constant, or its length per unit times the call's value of `op->arg`, in ms. 0 when
 * the op is not a pulse, the argument is absent, or the value is not a positive number below
 * a day.
 */
uint32_t ne_bridge_pulse_ms(const ne_bridge *b, uint32_t action, const ne_agent_pin_op *op,
                            const ne_arg_value *args, uint32_t arg_count);

/*
 * One field of a result, for an adapter that fills its own struct (NeuroClaw-ESP's
 * `nc_tool_result`): `name` at the top (`reason`, `failed_criterion`, `message`, the first of
 * `problems`) or inside `object` (`confirmation`: `id`, `message`, `expires_in_ms`). A string is
 * decoded, a number copied as written. 0 when found and it fits in `cap` with its NUL; else -1
 * and `out` is empty.
 */
int ne_bridge_result_field(const ne_bridge_result *r, const char *object, const char *name,
                           char *out, uint32_t cap);

#ifdef __cplusplus
}
#endif

#endif /* NE_BRAIN_BRIDGE_H */
