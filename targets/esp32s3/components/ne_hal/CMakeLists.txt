# The device HAL's token door for digital.out (TSK-S4-01, DP-B-08).
idf_component_register(SRCS "src/ne_hal.c"
                       INCLUDE_DIRS "include"
                       REQUIRES ne_gate)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=c99 -Wall -Wextra -Wconversion -Werror)
