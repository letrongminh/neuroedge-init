/*
 * The owner's settings and secrets, ESP-IDF side (ne_config.h). Encrypted-NVS
 * approach from zclaw main/memory.c (https://github.com/tnm/zclaw, commit
 * e3ad271, MIT, Copyright (c) 2026 Ted Nyman): when encryption is configured and
 * fails, refuse rather than fall back to plaintext.
 */
#include "ne_config.h"

#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "esp_partition.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#define NE_CONFIG_PARTITION "ne_config"
#define NE_CONFIG_NAMESPACE "ne_config"

static const char *TAG = "ne_config";
static ne_config_storage s_storage = NE_CONFIG_STORAGE_NONE;

const char *ne_config_storage_name(ne_config_storage storage)
{
    switch (storage) {
    case NE_CONFIG_STORAGE_PLAINTEXT: return "plaintext";
    case NE_CONFIG_STORAGE_ENCRYPTED: return "encrypted";
    case NE_CONFIG_STORAGE_NONE: break;
    }
    return "none";
}

ne_config_storage ne_config_storage_mode(void)
{
    return s_storage;
}

const char *ne_config_storage_risk(void)
{
    return s_storage == NE_CONFIG_STORAGE_PLAINTEXT ? "readable_flash" : NULL;
}

#if CONFIG_NVS_ENCRYPTION
static esp_err_t open_encrypted(void)
{
    nvs_sec_scheme_t *scheme = nvs_flash_get_default_security_scheme();
    if (scheme == NULL) return ESP_ERR_NOT_FOUND;
    nvs_sec_cfg_t cfg;
    esp_err_t err = nvs_flash_read_security_cfg_v2(scheme, &cfg);
    if (err == ESP_ERR_NVS_KEYS_NOT_INITIALIZED) {
        ESP_LOGI(TAG, "generating the NVS encryption keys");
        err = nvs_flash_generate_keys_v2(scheme, &cfg);
    }
    if (err != ESP_OK) return err;
    err = nvs_flash_secure_init_partition(NE_CONFIG_PARTITION, &cfg);
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "erasing the %s partition", NE_CONFIG_PARTITION);
        err = nvs_flash_erase_partition(NE_CONFIG_PARTITION);
        if (err == ESP_OK) err = nvs_flash_secure_init_partition(NE_CONFIG_PARTITION, &cfg);
    }
    return err;
}
#else
static esp_err_t open_plaintext(void)
{
    esp_err_t err = nvs_flash_init_partition(NE_CONFIG_PARTITION);
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "erasing the %s partition", NE_CONFIG_PARTITION);
        err = nvs_flash_erase_partition(NE_CONFIG_PARTITION);
        if (err == ESP_OK) err = nvs_flash_init_partition(NE_CONFIG_PARTITION);
    }
    return err;
}
#endif

esp_err_t ne_config_init(void)
{
    s_storage = NE_CONFIG_STORAGE_NONE;
    if (esp_partition_find_first(ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_NVS,
                                 NE_CONFIG_PARTITION) == NULL) {
        printf("NE_CONFIG STORAGE none reason=no_partition\n");
        fflush(stdout);
        return ESP_ERR_NOT_FOUND;
    }
#if CONFIG_NVS_ENCRYPTION
    const esp_err_t err = open_encrypted();
    if (err == ESP_OK) s_storage = NE_CONFIG_STORAGE_ENCRYPTED;
#else
    const esp_err_t err = open_plaintext();
    if (err == ESP_OK) s_storage = NE_CONFIG_STORAGE_PLAINTEXT;
#endif
    if (err != ESP_OK) {
        printf("NE_CONFIG STORAGE none reason=%s\n", esp_err_to_name(err));
    } else if (ne_config_storage_risk() != NULL) {
        printf("NE_CONFIG STORAGE %s risk=%s\n", ne_config_storage_name(s_storage),
               ne_config_storage_risk());
    } else {
        printf("NE_CONFIG STORAGE %s\n", ne_config_storage_name(s_storage));
    }
    fflush(stdout);
    return err;
}

static esp_err_t open_namespace(nvs_open_mode_t mode, nvs_handle_t *handle)
{
    if (s_storage == NE_CONFIG_STORAGE_NONE) return ESP_ERR_INVALID_STATE;
    return nvs_open_from_partition(NE_CONFIG_PARTITION, NE_CONFIG_NAMESPACE, mode, handle);
}

esp_err_t ne_config_set(const char *name, const char *value, ne_config_verdict *verdict)
{
    const ne_config_key *key = ne_config_key_find(name);
    const ne_config_verdict checked = ne_config_check_value(key, value);
    if (verdict != NULL) *verdict = checked;
    if (checked != NE_CONFIG_OK) return ESP_ERR_INVALID_ARG;
    nvs_handle_t handle;
    esp_err_t err = open_namespace(NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    err = nvs_set_str(handle, key->nvs_key, value);
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

esp_err_t ne_config_get(const char *name, char *out, size_t cap)
{
    const ne_config_key *key = ne_config_key_find(name);
    if (key == NULL) return ESP_ERR_NOT_FOUND;
    if (out == NULL || cap == 0) return ESP_ERR_INVALID_ARG;
    out[0] = '\0';
    nvs_handle_t handle;
    esp_err_t err = open_namespace(NVS_READONLY, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) return ESP_ERR_NVS_NOT_FOUND; /* nothing stored yet */
    if (err != ESP_OK) return err;
    size_t len = cap;
    err = nvs_get_str(handle, key->nvs_key, out, &len);
    nvs_close(handle);
    if (err != ESP_OK) out[0] = '\0';
    return err;
}

bool ne_config_is_set(const char *name)
{
    const ne_config_key *key = ne_config_key_find(name);
    if (key == NULL) return false;
    nvs_handle_t handle;
    if (open_namespace(NVS_READONLY, &handle) != ESP_OK) return false;
    size_t len = 0;
    const esp_err_t err = nvs_get_str(handle, key->nvs_key, NULL, &len);
    nvs_close(handle);
    return err == ESP_OK;
}

esp_err_t ne_config_unset(const char *name)
{
    const ne_config_key *key = ne_config_key_find(name);
    if (key == NULL) return ESP_ERR_NOT_FOUND;
    nvs_handle_t handle;
    esp_err_t err = open_namespace(NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    err = nvs_erase_key(handle, key->nvs_key);
    if (err == ESP_ERR_NVS_NOT_FOUND) err = ESP_OK;
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

esp_err_t ne_config_erase_all(void)
{
    nvs_handle_t handle;
    esp_err_t err = open_namespace(NVS_READWRITE, &handle);
    if (err == ESP_ERR_NVS_NOT_FOUND) return ESP_OK;
    if (err != ESP_OK) return err;
    err = nvs_erase_all(handle);
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}
