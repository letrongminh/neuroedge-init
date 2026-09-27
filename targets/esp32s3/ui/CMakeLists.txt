# The device UI as an ESP-IDF component (TSK-S4-10).
#
# The current firmware does not build this directory: it is not under
# targets/esp32s3/components/ and nothing requires it — wiring the UI into the
# running firmware waits for the display driver (TSK-S4-01). It is registered
# here so that, when that lands, the UI, its strings and its fonts are one
# component the firmware requires:
#
#     idf_component_register(... REQUIRES ne_ui)
#
# and ne_ui needs LVGL ^9.6 (MIT), the same v9.6.0 the host harness pins by
# URL and SHA-256 (host/CMakeLists.txt). The screen code is plain C on the LVGL
# API only: it builds here and on the host from the same sources.
idf_component_register(
    SRCS
        "src/ne_ui.c"
        "src/ne_ui_text.c"
        "src/ne_ui_strings.c"
        "fonts/ne_font_12.c"
        "fonts/ne_font_16.c"
        "fonts/ne_font_22.c"
    INCLUDE_DIRS "include" "fonts"
    REQUIRES lvgl)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=c99 -Wall -Wextra -Werror)
