# NeuroEdge trace lines on the UART as an ESP-IDF component (TSK-S4-09).
# Portable C99, like ne_gate: the same source builds on the host (see Makefile)
# and on the ESP32-S3. Formatting only — the application's sink writes the line.
idf_component_register(SRCS "src/ne_trace.c"
                       INCLUDE_DIRS "include"
                       REQUIRES ne_gate)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=c99 -Wall -Wextra -Wconversion -Werror)
