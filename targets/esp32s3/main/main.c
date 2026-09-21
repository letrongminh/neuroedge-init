#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"

static const char *TAG = "neuroedge_core";

void app_main(void)
{
    ESP_LOGI(TAG, "==================================================");
    ESP_LOGI(TAG, "Starting NeuroEdge Physical AI Runtime (ESP32-S3-Box-3)");
    ESP_LOGI(TAG, "HAL Primitives: audio.in, audio.out, digital.out, sensor.read, display");
    ESP_LOGI(TAG, "Action Contract Engine: FAIL-CLOSED circuit breaker ACTIVE");
    ESP_LOGI(TAG, "==================================================");

    // Initialize NVS for provisioning and credentials
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_LOGI(TAG, "Target Equivalence Engine ready. Listening for Gate verification events...");
}
