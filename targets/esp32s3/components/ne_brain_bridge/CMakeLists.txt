# The brain bridge of Profile B (Q-83, TSK-I2f-12): NeuroClaw-ESP calls ne_gate through it.
idf_component_register(SRCS "src/ne_brain_bridge.c"
                       INCLUDE_DIRS "include"
                       REQUIRES ne_gate ne_agent ne_trace)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=c99 -Wall -Wextra -Wconversion -Werror)
