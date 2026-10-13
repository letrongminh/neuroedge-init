# ne_boot — boot guard (Q-79, TSK-I2f-10), ported from zclaw (MIT; NOTICE §A).
# src/ne_boot_policy.c is pure C99 and compiles on the host
# (python/tests/test_c_boot_and_config.py); src/ne_boot_guard.c owns NVS and the
# stable-boot task.
idf_component_register(
    SRCS
        "src/ne_boot_guard.c"
        "src/ne_boot_policy.c"
    INCLUDE_DIRS
        "include"
    REQUIRES
        nvs_flash
        esp_system
)

set_source_files_properties(src/ne_boot_policy.c PROPERTIES COMPILE_OPTIONS "-std=c99")
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Wconversion -Werror)
