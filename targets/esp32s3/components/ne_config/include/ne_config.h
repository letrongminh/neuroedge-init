/*
 * The owner's settings and secrets on the chip (Q-79, TSK-I2f-10): Wi-Fi, the
 * Telegram bot and its owner, the LLM endpoint and key. Keys and value rules in
 * ne_config_keys.h.
 *
 * They live in their own NVS partition, `ne_config` (partitions.csv), apart
 * from the default one that holds the boot count and OTA marks, so a factory
 * reset of the owner's data never touches those.
 *
 *   - Built with CONFIG_NVS_ENCRYPTION (sdkconfig.secure: flash encryption on):
 *     the partition is encrypted with keys from the `nvs_keys` partition. If
 *     that fails, nothing is stored at all — never a silent plaintext fallback.
 *   - Otherwise (a development board, QEMU): plaintext, and the firmware says
 *     so on every boot and every write (`risk=readable_flash`): anyone holding
 *     the board can read the token and keys from flash. A label, not a refusal
 *     (Q-73); the owner chooses when to burn the eFuses.
 *
 * Approach from zclaw main/memory.c (https://github.com/tnm/zclaw, commit
 * e3ad271, MIT, Copyright (c) 2026 Ted Nyman), which refuses the same fallback.
 */
#ifndef NE_CONFIG_H
#define NE_CONFIG_H

#include <stdbool.h>
#include <stddef.h>

#include "esp_err.h"
#include "ne_config_keys.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    NE_CONFIG_STORAGE_NONE = 0, /* nothing can be stored or read */
    NE_CONFIG_STORAGE_PLAINTEXT,
    NE_CONFIG_STORAGE_ENCRYPTED,
} ne_config_storage;

/* Open the partition and print `NE_CONFIG STORAGE <mode> [risk=|reason=]`. */
esp_err_t ne_config_init(void);

ne_config_storage ne_config_storage_mode(void);

/* `none`, `plaintext`, `encrypted`. */
const char *ne_config_storage_name(ne_config_storage storage);

/* `readable_flash` when the storage is plaintext, NULL otherwise. */
const char *ne_config_storage_risk(void);

/*
 * Store `value` under the key named `name` after ne_config_check_value; the
 * verdict goes to `*verdict` (ESP_ERR_INVALID_ARG when it is not OK).
 */
esp_err_t ne_config_set(const char *name, const char *value, ne_config_verdict *verdict);

/* The stored value; ESP_ERR_NVS_NOT_FOUND when unset, ESP_ERR_NOT_FOUND for an
 * unknown key. For the firmware's own use: the console never prints a secret. */
esp_err_t ne_config_get(const char *name, char *out, size_t cap);

bool ne_config_is_set(const char *name);

esp_err_t ne_config_unset(const char *name);

/* Erase every setting (console `factory-reset`). */
esp_err_t ne_config_erase_all(void);

#ifdef __cplusplus
}
#endif

#endif /* NE_CONFIG_H */
