# ne_config — the owner's settings and secrets on the chip (Q-79, TSK-I2f-10).
# src/ne_config_keys.c (which keys exist, what a value must look like, how one
# is shown) is pure C99 and compiles on the host
# (python/tests/test_c_boot_and_config.py); src/ne_config.c owns the `ne_config`
# NVS partition, encrypted when flash encryption is on. Approach from zclaw
# main/memory.c (MIT; NOTICE §A).
idf_component_register(
    SRCS
        "src/ne_config.c"
        "src/ne_config_keys.c"
    INCLUDE_DIRS
        "include"
    REQUIRES
        nvs_flash
        esp_partition
)

set_source_files_properties(src/ne_config_keys.c PROPERTIES COMPILE_OPTIONS "-std=c99")
target_compile_options(${COMPONENT_LIB} PRIVATE -Wall -Wextra -Wconversion -Werror)
