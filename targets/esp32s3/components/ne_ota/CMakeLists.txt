# ne_ota — A/B firmware update (FR-OTA-01..04, TSK-S6-01/02/04).
# src/ne_ota_policy.c is pure C99 and compiles on the host (python/tests/
# test_c_ota_policy.py); src/ne_ota.c owns the ESP-IDF side and always links, so
# a factory image still reports and marks rollback state. The HTTP(S) and
# Ethernet code sits behind CONFIG_NEUROEDGE_OTA(_ETH): the components are
# always in the requirement list — the dependency checker reads it before
# sdkconfig exists, so it cannot be conditional — but nothing of them links
# into an image whose code never calls them.
idf_component_register(
    SRCS
        "src/ne_ota.c"
        "src/ne_ota_policy.c"
    INCLUDE_DIRS
        "include"
    REQUIRES
        app_update
        nvs_flash
        esp_app_format
        esp_partition
        esp_https_ota
        esp_http_client
        esp_eth
        esp_netif
        esp_event
        esp_timer
        mbedtls
)

# The IDF headers are not strict-C99 clean (static assertions, compound
# literals), so only the policy file gets -std=c99; both get the warnings.
set_source_files_properties(src/ne_ota_policy.c PROPERTIES COMPILE_OPTIONS "-std=c99")
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Wconversion -Werror)
