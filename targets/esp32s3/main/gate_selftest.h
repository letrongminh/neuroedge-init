/*
 * Boot self-test of the gate runtime (TSK-S4-02, TSK-S4-08, TSK-I3-01).
 *
 * Runs on the agent this image was built for (`ne_agent_linked`, the component
 * components/ne_agent/ that `neuroedge build --target esp32s3` generates):
 *
 *   1. every gate's tree loads from flash (CRC, structure) and is the tree the
 *      host compiled for that gate: same digest, same number of criteria;
 *   2. every check of the agent — facts varied one criterion at a time, a
 *      degraded gathering, a person's confirmation — is decided by the C walker
 *      exactly as the host engine decided it: verdict, reason, failing criterion,
 *      answerable, fail mode, confirmed criteria;
 *   3. every @action's token grants exactly the pins of its action, once each: a
 *      second use is `token_replayed`, a pin outside the action's is
 *      `pin_not_granted`, a tampered token is `unknown_token`; the action table
 *      names a gate and pins the agent has;
 *   4. the ledger fails closed when every slot holds a live token.
 *
 * Pure C99 with no ESP-IDF dependency, so python/tests/ also runs it on the host.
 * With a trace sink, every check is also written as `NE1` trace lines
 * (gate_evaluation_begin, gate_facts, gate_evaluation_result — TSK-S4-09)
 * inside the caller's session; token checks write none.
 */
#ifndef NEUROEDGE_GATE_SELFTEST_H
#define NEUROEDGE_GATE_SELFTEST_H

#include <stddef.h>
#include <stdint.h>

#include "ne_agent.h"
#include "ne_token.h"
#include "ne_trace.h"

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Returns 0 when every check passed. `line` receives the one line the firmware
 * prints on the UART, which the QEMU jobs grep for:
 *   "NE_SELFTEST PASS walker=<n> token=<n>"   n = checks passed
 *   "NE_SELFTEST FAIL <what>"
 * `sink` may be NULL: nothing but `line` is written.
 */
int neuroedge_gate_selftest(const ne_agent *agent, ne_random_fn fill_random, uint32_t boot_id,
                            uint32_t now_ms, char *line, size_t cap, ne_trace_sink *sink);

#ifdef __cplusplus
}
#endif

#endif /* NEUROEDGE_GATE_SELFTEST_H */
