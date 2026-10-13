/*
 * The owner's settings on the chip: which keys exist, what a value must look
 * like, and how one is shown (Q-79, TSK-I2f-10). No ESP-IDF state: compiled on
 * the host by python/tests/test_c_boot_and_config.py.
 *
 * A secret is never shown, in part or in length: `config get` prints `<secret>`
 * and nothing in the firmware prints the value itself. The console reads a
 * secret at a hidden prompt, never from the command line, so it is not echoed
 * to the UART or kept in the line history either (ne_console.c).
 */
#ifndef NE_CONFIG_KEYS_H
#define NE_CONFIG_KEYS_H

#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Longest value of any key, NUL excluded. Buffers are NE_CONFIG_VALUE_MAX + 1. */
#define NE_CONFIG_VALUE_MAX 256u

typedef enum {
    NE_CONFIG_CHECK_SSID,      /* 1..32 bytes */
    NE_CONFIG_CHECK_WIFI_PASS, /* 8..64 bytes (WPA2 passphrase or 64 hex) */
    NE_CONFIG_CHECK_TG_TOKEN,  /* <bot id>:<secret>, as BotFather gives it */
    NE_CONFIG_CHECK_TG_OWNER,  /* a Telegram user id: digits, no leading zero */
    NE_CONFIG_CHECK_URL,       /* http:// or https://, a host, no spaces */
    NE_CONFIG_CHECK_WORD,      /* 1..max bytes, no spaces */
} ne_config_check;

typedef struct {
    const char *name;    /* what the owner types: `telegram.token` */
    const char *nvs_key; /* at most 15 characters */
    bool secret;
    ne_config_check check;
    size_t max_len;
    const char *help;
} ne_config_key;

typedef enum {
    NE_CONFIG_OK = 0,
    NE_CONFIG_UNKNOWN_KEY,
    NE_CONFIG_EMPTY,
    NE_CONFIG_TOO_SHORT,
    NE_CONFIG_TOO_LONG,
    NE_CONFIG_FORMAT,
} ne_config_verdict;

/* Every key, in the order `config list` shows them; `count` gets how many. */
const ne_config_key *ne_config_keys(size_t *count);

/* The key named `name`, or NULL. */
const ne_config_key *ne_config_key_find(const char *name);

/* Whether `value` may be stored under `key`. No value has a control byte. */
ne_config_verdict ne_config_check_value(const ne_config_key *key, const char *value);

/* `ok`, `unknown_key`, `empty`, `too_short`, `too_long`, `format`. */
const char *ne_config_verdict_name(ne_config_verdict verdict);

/*
 * A risk the owner chose and should see (Q-73: a label, not a refusal), or
 * NULL: `cleartext_url` for an http:// URL, which carries the LLM key
 * unencrypted.
 */
const char *ne_config_value_risk(const ne_config_key *key, const char *value);

/*
 * How `config get` shows a value: `<unset>` when `value` is NULL, `<secret>`
 * for a set secret, the text otherwise (any control byte as `?`). Returns the
 * length written, or -1 when it does not fit `cap`.
 */
int ne_config_display(const ne_config_key *key, const char *value, char *out, size_t cap);

#ifdef __cplusplus
}
#endif

#endif /* NE_CONFIG_KEYS_H */
