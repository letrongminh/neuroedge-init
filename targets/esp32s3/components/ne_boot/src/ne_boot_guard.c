/*
 * Boot guard, ESP-IDF side (ne_boot_guard.h). Adapted from zclaw main/main.c and
 * main/boot_guard.c (https://github.com/tnm/zclaw, commit e3ad271, MIT,
 * Copyright (c) 2026 Ted Nyman).
 */
#include "ne_boot_guard.h"

#include <stdio.h>

#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs.h"
#include "sdkconfig.h"

#define NE_BOOT_NAMESPACE "ne_boot"
#define NE_BOOT_KEY "count"

static const char *TAG = "ne_boot";
static ne_boot_decision s_decision = {1u, 2u, false};

static const char *reset_reason_name(esp_reset_reason_t reason)
{
    switch (reason) {
    case ESP_RST_POWERON: return "poweron";
    case ESP_RST_EXT: return "ext";
    case ESP_RST_SW: return "sw";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "int_wdt";
    case ESP_RST_TASK_WDT: return "task_wdt";
    case ESP_RST_WDT: return "wdt";
    case ESP_RST_DEEPSLEEP: return "deepsleep";
    case ESP_RST_BROWNOUT: return "brownout";
    case ESP_RST_SDIO: return "sdio";
    case ESP_RST_USB: return "usb";
    case ESP_RST_JTAG: return "jtag";
    default: return "unknown";
    }
}

static esp_err_t write_count(uint32_t count)
{
    nvs_handle_t handle;
    esp_err_t err = nvs_open(NE_BOOT_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    err = nvs_set_u32(handle, NE_BOOT_KEY, count);
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err;
}

ne_boot_decision ne_boot_guard_begin(void)
{
    uint32_t persisted = 0;
    nvs_handle_t handle;
    if (nvs_open(NE_BOOT_NAMESPACE, NVS_READONLY, &handle) == ESP_OK) {
        if (nvs_get_u32(handle, NE_BOOT_KEY, &persisted) != ESP_OK) persisted = 0;
        nvs_close(handle);
    }
    s_decision = ne_boot_decide(persisted, (uint32_t)CONFIG_NEUROEDGE_BOOT_GUARD_MAX);

    const esp_err_t err = write_count(s_decision.count);
    if (err != ESP_OK) {
        /* A count that cannot be kept cannot prove a loop: run normally. */
        ESP_LOGE(TAG, "cannot persist the boot count: %s", esp_err_to_name(err));
        s_decision.safe_mode = false;
        printf("NE_BOOT GUARD_OFF error=%s\n", esp_err_to_name(err));
    }
    char line[NE_BOOT_LINE_MAX + 1];
    if (ne_boot_marker(line, sizeof line, s_decision, reset_reason_name(esp_reset_reason())) > 0) {
        printf("%s\n", line);
    }
    fflush(stdout);
    return s_decision;
}

ne_boot_decision ne_boot_guard_current(void)
{
    return s_decision;
}

esp_err_t ne_boot_guard_clear(void)
{
    const esp_err_t err = write_count(0);
    if (err == ESP_OK) {
        printf("NE_BOOT CLEARED\n");
    } else {
        printf("NE_BOOT CLEAR_FAILED error=%s\n", esp_err_to_name(err));
    }
    fflush(stdout);
    return err;
}

static void mark_stable(uint32_t stable_ms)
{
    if (write_count(0) == ESP_OK) {
        printf("NE_BOOT STABLE after_ms=%lu\n", (unsigned long)stable_ms);
    } else {
        ESP_LOGE(TAG, "cannot clear the boot count");
    }
    fflush(stdout);
}

static void stable_task(void *arg)
{
    const uint32_t stable_ms = (uint32_t)(uintptr_t)arg;
    vTaskDelay(pdMS_TO_TICKS(stable_ms));
    mark_stable(stable_ms);
    vTaskDelete(NULL);
}

void ne_boot_guard_stable_after(uint32_t stable_ms)
{
    if (stable_ms == 0) {
        mark_stable(0);
        return;
    }
    if (xTaskCreate(stable_task, "ne_boot_ok", 2560, (void *)(uintptr_t)stable_ms, 1, NULL) !=
        pdPASS) {
        ESP_LOGE(TAG, "cannot start the boot-stable task; the count stays");
    }
}
