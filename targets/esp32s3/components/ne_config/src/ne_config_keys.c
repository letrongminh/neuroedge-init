/*
 * The owner's settings on the chip (ne_config_keys.h). Pure C99. The key set
 * follows what zclaw keeps in NVS for a standalone Telegram agent (Wi-Fi, bot
 * token, owner id, LLM endpoint and key); its validation rules are NeuroEdge's.
 */
#include "ne_config_keys.h"

#include <stdio.h>
#include <string.h>

static const ne_config_key KEYS[] = {
    {"wifi.ssid", "wifi_ssid", false, NE_CONFIG_CHECK_SSID, 32u, "Wi-Fi network name"},
    {"wifi.pass", "wifi_pass", true, NE_CONFIG_CHECK_WIFI_PASS, 64u, "Wi-Fi password"},
    {"telegram.token", "tg_token", true, NE_CONFIG_CHECK_TG_TOKEN, 96u,
     "bot token from @BotFather"},
    {"telegram.owner", "tg_owner", false, NE_CONFIG_CHECK_TG_OWNER, 20u,
     "the owner's Telegram user id (from @userinfobot)"},
    {"llm.url", "llm_url", false, NE_CONFIG_CHECK_URL, 200u,
     "OpenAI-compatible chat completions endpoint"},
    {"llm.key", "llm_key", true, NE_CONFIG_CHECK_WORD, NE_CONFIG_VALUE_MAX, "LLM API key"},
    {"llm.model", "llm_model", false, NE_CONFIG_CHECK_WORD, 96u, "LLM model name"},
    /* Profile B (DP-B-10): what NeuroClaw-ESP needs besides the above */
    {"llm.fallback_url", "llm_fb_url", false, NE_CONFIG_CHECK_URL, 200u,
     "fallback chat completions endpoint (used when the first fails)"},
    {"llm.fallback_key", "llm_fb_key", true, NE_CONFIG_CHECK_WORD, NE_CONFIG_VALUE_MAX,
     "fallback LLM API key"},
    {"llm.fallback_model", "llm_fb_model", false, NE_CONFIG_CHECK_WORD, 96u,
     "fallback LLM model name"},
    {"search.key", "search_key", true, NE_CONFIG_CHECK_WORD, 128u, "web search API key"},
    {"tz", "tz", false, NE_CONFIG_CHECK_WORD, 64u, "POSIX time zone, e.g. ICT-7"},
};

const ne_config_key *ne_config_keys(size_t *count)
{
    if (count != NULL) *count = sizeof KEYS / sizeof KEYS[0];
    return KEYS;
}

const ne_config_key *ne_config_key_find(const char *name)
{
    if (name == NULL) return NULL;
    for (size_t i = 0; i < sizeof KEYS / sizeof KEYS[0]; i++) {
        if (strcmp(KEYS[i].name, name) == 0) return &KEYS[i];
    }
    return NULL;
}

static bool is_digit(char c)
{
    return c >= '0' && c <= '9';
}

static bool is_token_char(char c)
{
    return is_digit(c) || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_' ||
           c == '-';
}

static bool has_space(const char *value)
{
    return strchr(value, ' ') != NULL;
}

/* <5..15 digits>:<30..80 of [A-Za-z0-9_-]> */
static bool telegram_token_ok(const char *value)
{
    const char *colon = strchr(value, ':');
    if (colon == NULL) return false;
    const size_t id_len = (size_t)(colon - value);
    if (id_len < 5u || id_len > 15u) return false;
    for (const char *c = value; c < colon; c++) {
        if (!is_digit(*c)) return false;
    }
    const size_t secret_len = strlen(colon + 1);
    if (secret_len < 30u || secret_len > 80u) return false;
    for (const char *c = colon + 1; *c != '\0'; c++) {
        if (!is_token_char(*c)) return false;
    }
    return true;
}

static bool owner_ok(const char *value)
{
    if (value[0] == '0') return false;
    for (const char *c = value; *c != '\0'; c++) {
        if (!is_digit(*c)) return false;
    }
    return true;
}

static bool url_ok(const char *value)
{
    const char *host;
    if (strncmp(value, "https://", 8) == 0) {
        host = value + 8;
    } else if (strncmp(value, "http://", 7) == 0) {
        host = value + 7;
    } else {
        return false;
    }
    return host[0] != '\0' && host[0] != '/' && !has_space(value);
}

ne_config_verdict ne_config_check_value(const ne_config_key *key, const char *value)
{
    if (key == NULL) return NE_CONFIG_UNKNOWN_KEY;
    if (value == NULL || value[0] == '\0') return NE_CONFIG_EMPTY;
    const size_t len = strlen(value);
    if (len > key->max_len) return NE_CONFIG_TOO_LONG;
    for (const char *c = value; *c != '\0'; c++) {
        const unsigned char byte = (unsigned char)*c;
        if (byte < 0x20u || byte == 0x7fu) return NE_CONFIG_FORMAT;
    }
    switch (key->check) {
    case NE_CONFIG_CHECK_SSID:
        return NE_CONFIG_OK;
    case NE_CONFIG_CHECK_WIFI_PASS:
        return len < 8u ? NE_CONFIG_TOO_SHORT : NE_CONFIG_OK;
    case NE_CONFIG_CHECK_TG_TOKEN:
        return telegram_token_ok(value) ? NE_CONFIG_OK : NE_CONFIG_FORMAT;
    case NE_CONFIG_CHECK_TG_OWNER:
        return owner_ok(value) ? NE_CONFIG_OK : NE_CONFIG_FORMAT;
    case NE_CONFIG_CHECK_URL:
        return url_ok(value) ? NE_CONFIG_OK : NE_CONFIG_FORMAT;
    case NE_CONFIG_CHECK_WORD:
        return has_space(value) ? NE_CONFIG_FORMAT : NE_CONFIG_OK;
    }
    return NE_CONFIG_FORMAT;
}

const char *ne_config_verdict_name(ne_config_verdict verdict)
{
    switch (verdict) {
    case NE_CONFIG_OK: return "ok";
    case NE_CONFIG_UNKNOWN_KEY: return "unknown_key";
    case NE_CONFIG_EMPTY: return "empty";
    case NE_CONFIG_TOO_SHORT: return "too_short";
    case NE_CONFIG_TOO_LONG: return "too_long";
    case NE_CONFIG_FORMAT: return "format";
    }
    return "format";
}

const char *ne_config_value_risk(const ne_config_key *key, const char *value)
{
    if (key == NULL || value == NULL) return NULL;
    if (key->check == NE_CONFIG_CHECK_URL && strncmp(value, "http://", 7) == 0) {
        return "cleartext_url";
    }
    return NULL;
}

int ne_config_display(const ne_config_key *key, const char *value, char *out, size_t cap)
{
    if (key == NULL || out == NULL || cap == 0u) return -1;
    const char *shown = value == NULL ? "<unset>" : key->secret ? "<secret>" : value;
    const size_t len = strlen(shown);
    if (len >= cap) {
        out[0] = '\0';
        return -1;
    }
    for (size_t i = 0; i < len; i++) {
        const unsigned char byte = (unsigned char)shown[i];
        out[i] = (byte < 0x20u || byte == 0x7fu) ? '?' : shown[i];
    }
    out[len] = '\0';
    return (int)len;
}
