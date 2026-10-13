# ne_console — the serial console (Q-79, TSK-I2f-10): esp_console REPL after
# MimiClaw's template, commands after zclaw's local admin (both MIT; NOTICE §A).
idf_component_register(
    SRCS
        "src/ne_console.c"
    INCLUDE_DIRS
        "include"
    REQUIRES
        console
        esp_driver_uart
        esp_system
        ne_boot
        ne_config
        nvs_flash
)

target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Werror)
