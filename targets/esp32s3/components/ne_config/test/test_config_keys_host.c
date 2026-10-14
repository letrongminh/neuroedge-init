/*
 * Host conformance runner for the owner's settings (Q-79, TSK-I2f-10): the key
 * table, every value rule, the risk label, and how a value is shown — a secret
 * never, in part or in length. Exit 0 only when every check passed;
 * python/tests/test_c_boot_and_config.py compiles and runs this.
 */
#include <stdio.h>
#include <string.h>

#include "ne_config_keys.h"

static unsigned s_checks;

static int fail(const char *what, int line) {
    fprintf(stderr, "FAIL line %d: %s\n", line, what);
    return 1;
}

#define CHECK(cond)                     \
    do {                                \
        s_checks++;                     \
        if (!(cond)) return fail(#cond, __LINE__); \
    } while (0)

#define TOKEN "7000000001:AAQemuOnlyNotARealTokenxxxxxxxxxxxx"

static ne_config_verdict check(const char *name, const char *value) {
    return ne_config_check_value(ne_config_key_find(name), value);
}

static int check_table(void) {
    size_t count = 0;
    const ne_config_key *keys = ne_config_keys(&count);
    CHECK(count == 12u);
    for (size_t i = 0; i < count; i++) {
        CHECK(strlen(keys[i].nvs_key) <= 15u); /* NVS key limit */
        CHECK(keys[i].max_len <= NE_CONFIG_VALUE_MAX);
        CHECK(ne_config_key_find(keys[i].name) == &keys[i]);
        for (size_t j = i + 1; j < count; j++) {
            CHECK(strcmp(keys[i].name, keys[j].name) != 0);
            CHECK(strcmp(keys[i].nvs_key, keys[j].nvs_key) != 0);
        }
    }
    /* Exactly these are secrets. */
    CHECK(ne_config_key_find("wifi.pass")->secret);
    CHECK(ne_config_key_find("telegram.token")->secret);
    CHECK(ne_config_key_find("llm.key")->secret);
    CHECK(!ne_config_key_find("wifi.ssid")->secret);
    CHECK(!ne_config_key_find("telegram.owner")->secret);
    CHECK(!ne_config_key_find("llm.url")->secret);
    CHECK(!ne_config_key_find("llm.model")->secret);
    CHECK(ne_config_key_find("llm.fallback_key")->secret);
    CHECK(ne_config_key_find("search.key")->secret);
    CHECK(!ne_config_key_find("llm.fallback_url")->secret);
    CHECK(!ne_config_key_find("tz")->secret);
    CHECK(ne_config_key_find("telegram") == NULL);
    CHECK(ne_config_key_find("TELEGRAM.TOKEN") == NULL);
    CHECK(ne_config_key_find(NULL) == NULL);
    CHECK(ne_config_check_value(NULL, "x") == NE_CONFIG_UNKNOWN_KEY);
    return 0;
}

static int check_values(void) {
    /* Every key: empty is refused, control bytes are refused. */
    size_t count = 0;
    const ne_config_key *keys = ne_config_keys(&count);
    for (size_t i = 0; i < count; i++) {
        CHECK(ne_config_check_value(&keys[i], NULL) == NE_CONFIG_EMPTY);
        CHECK(ne_config_check_value(&keys[i], "") == NE_CONFIG_EMPTY);
        CHECK(ne_config_check_value(&keys[i], "abc\ndef12345") == NE_CONFIG_FORMAT);
        CHECK(ne_config_check_value(&keys[i], "abc\x7f" "def12345") == NE_CONFIG_FORMAT);
    }
    CHECK(check("wifi.ssid", "Nha Minh 5G") == NE_CONFIG_OK);
    CHECK(check("wifi.ssid", "123456789012345678901234567890123") == NE_CONFIG_TOO_LONG);
    CHECK(check("wifi.pass", "1234567") == NE_CONFIG_TOO_SHORT);
    CHECK(check("wifi.pass", "12345678") == NE_CONFIG_OK);
    CHECK(check("wifi.pass", "pass with spaces") == NE_CONFIG_OK);

    CHECK(check("telegram.token", TOKEN) == NE_CONFIG_OK);
    CHECK(check("telegram.token", "7000000001AAQemuOnlyNotARealTokenxxxxxxxxxxxx") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.token", "1234:AAQemuOnlyNotARealTokenxxxxxxxxxxxx") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.token", "70000x0001:AAQemuOnlyNotARealTokenxxxxxxxxxxxx") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.token", "7000000001:short") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.token", "7000000001:AAQemuOnlyNotARealToken xxxxxxxxxxxx") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.token", "7000000001:AAQemuOnlyNotARealToken:xxxxxxxxxxxx") == NE_CONFIG_FORMAT);

    CHECK(check("telegram.owner", "123456789") == NE_CONFIG_OK);
    CHECK(check("telegram.owner", "12ab") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.owner", "0123") == NE_CONFIG_FORMAT);
    CHECK(check("telegram.owner", "-100123") == NE_CONFIG_FORMAT); /* a group, not a person */
    CHECK(check("telegram.owner", "123456789012345678901") == NE_CONFIG_TOO_LONG);

    CHECK(check("llm.url", "https://openrouter.ai/api/v1/chat/completions") == NE_CONFIG_OK);
    CHECK(check("llm.url", "http://10.0.2.2:11434/v1/chat/completions") == NE_CONFIG_OK);
    CHECK(check("llm.url", "ftp://example.com") == NE_CONFIG_FORMAT);
    CHECK(check("llm.url", "https://") == NE_CONFIG_FORMAT);
    CHECK(check("llm.url", "https:///path") == NE_CONFIG_FORMAT);
    CHECK(check("llm.url", "https://a b") == NE_CONFIG_FORMAT);
    CHECK(check("llm.url", "openrouter.ai") == NE_CONFIG_FORMAT);

    CHECK(check("llm.key", "sk-or-v1-abc") == NE_CONFIG_OK);
    CHECK(check("llm.key", "sk or") == NE_CONFIG_FORMAT);
    CHECK(check("llm.model", "openai/gpt-4o-mini") == NE_CONFIG_OK);
    char too_long[NE_CONFIG_VALUE_MAX + 2];
    memset(too_long, 'k', sizeof too_long - 1);
    too_long[sizeof too_long - 1] = '\0';
    CHECK(check("llm.key", too_long) == NE_CONFIG_TOO_LONG);
    too_long[NE_CONFIG_VALUE_MAX] = '\0';
    CHECK(check("llm.key", too_long) == NE_CONFIG_OK);

    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_OK), "ok") == 0);
    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_UNKNOWN_KEY), "unknown_key") == 0);
    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_EMPTY), "empty") == 0);
    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_TOO_SHORT), "too_short") == 0);
    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_TOO_LONG), "too_long") == 0);
    CHECK(strcmp(ne_config_verdict_name(NE_CONFIG_FORMAT), "format") == 0);
    return 0;
}

static int check_risk(void) {
    const ne_config_key *url = ne_config_key_find("llm.url");
    CHECK(strcmp(ne_config_value_risk(url, "http://10.0.2.2/v1"), "cleartext_url") == 0);
    CHECK(ne_config_value_risk(url, "https://openrouter.ai/api/v1") == NULL);
    CHECK(ne_config_value_risk(ne_config_key_find("llm.model"), "http://x") == NULL);
    CHECK(ne_config_value_risk(NULL, "http://x") == NULL);
    CHECK(ne_config_value_risk(url, NULL) == NULL);
    return 0;
}

static int check_display(void) {
    char out[NE_CONFIG_VALUE_MAX + 1];
    const ne_config_key *token = ne_config_key_find("telegram.token");
    CHECK(ne_config_display(token, TOKEN, out, sizeof out) > 0);
    CHECK(strcmp(out, "<secret>") == 0);
    CHECK(strstr(out, "7000") == NULL);
    /* The same text for any secret value: no length, no prefix. */
    CHECK(ne_config_display(ne_config_key_find("llm.key"), "k", out, sizeof out) > 0);
    CHECK(strcmp(out, "<secret>") == 0);
    CHECK(ne_config_display(ne_config_key_find("wifi.pass"), "12345678", out, sizeof out) > 0);
    CHECK(strcmp(out, "<secret>") == 0);
    CHECK(ne_config_display(token, NULL, out, sizeof out) > 0);
    CHECK(strcmp(out, "<unset>") == 0);
    const ne_config_key *owner = ne_config_key_find("telegram.owner");
    CHECK(ne_config_display(owner, "123456789", out, sizeof out) == 9);
    CHECK(strcmp(out, "123456789") == 0);
    /* A stored value with a control byte (an older firmware) cannot move the cursor. */
    CHECK(ne_config_display(ne_config_key_find("wifi.ssid"), "a\x1b[2Jb", out, sizeof out) > 0);
    CHECK(strcmp(out, "a?[2Jb") == 0);
    char small[4];
    small[0] = 'x';
    CHECK(ne_config_display(token, TOKEN, small, sizeof small) == -1);
    CHECK(small[0] == '\0');
    CHECK(ne_config_display(NULL, "x", out, sizeof out) == -1);
    CHECK(ne_config_display(owner, "1", NULL, 4u) == -1);
    return 0;
}

int main(void) {
    if (check_table() != 0) return 1;
    if (check_values() != 0) return 1;
    if (check_risk() != 0) return 1;
    if (check_display() != 0) return 1;
    printf("NE_CONFIG_KEYS OK checks=%u\n", s_checks);
    return 0;
}
