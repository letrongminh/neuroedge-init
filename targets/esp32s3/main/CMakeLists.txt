idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES esp_system esp_wifi esp_http_client nvs_flash driver esp_timer
)
