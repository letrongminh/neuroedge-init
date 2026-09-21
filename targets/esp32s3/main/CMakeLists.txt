idf_component_register(
    SRCS
        "main.c"
        "memory_probe.c"
    INCLUDE_DIRS "."
    REQUIRES
        esp_system
        esp_wifi
        esp_netif
        esp_event
        esp_http_client
        nvs_flash
        driver
        esp_timer
        heap
)
