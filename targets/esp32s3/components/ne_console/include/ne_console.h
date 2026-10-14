/*
 * Serial console (Q-79, TSK-I2f-10): the owner's way in with a USB cable, in
 * normal and in safe mode. REPL on esp_console + linenoise, after the template
 * in MimiClaw main/cli/serial_cli.c (https://github.com/memovai/mimiclaw, commit
 * dcc1c8c, MIT); the command set follows zclaw's local admin commands (commit
 * e3ad271, MIT).
 *
 * Commands: status, config list|get|set|unset, bootguard [clear], reboot,
 * factory-reset confirm, help. None of them moves a pin or calls a tool: the
 * only way to a device stays the gate (Q-79).
 *
 * A secret is typed at a hidden prompt (`config set telegram.token`, then the
 * value), never on the command line: no echo to the UART, never in the line
 * history. `config get` shows a secret as `<secret>`.
 *
 * Lines a test reads start at column 0: `NE_CONSOLE READY mode=...`,
 * `NE_CONFIG SET|UNSET|REFUSED|FAILED key=...`, `NE_STATUS ...`.
 */
#ifndef NE_CONSOLE_H
#define NE_CONSOLE_H

#include <stdbool.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Take over the console UART and start the REPL task. */
esp_err_t ne_console_start(bool safe_mode);

/*
 * Before ne_console_start: more commands on this one console (Profile B, DP-B-11: the brain
 * registers its own, `neuroclaw_console_register`), called once esp_console is initialised.
 */
void ne_console_add_commands(esp_err_t (*register_more)(void));

/* Before ne_console_start: a risk label `status` prints too (`single_chip`, DP-B-14). Up to 4. */
void ne_console_add_risk(const char *label);

#ifdef __cplusplus
}
#endif

#endif /* NE_CONSOLE_H */
