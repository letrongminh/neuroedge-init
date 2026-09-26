# The host harness of the device UI (TSK-S4-10, FR-CI-05).
#
# Builds targets/esp32s3/ui/ against LVGL v9.6.0 pinned by URL and SHA-256, with
# LV_USE_TEST and PNG output, and runs the golden compare for every screen and
# language. The LVGL test tools are LVGL's own (src/debugging/test/); the UI
# sources are the ones the firmware will link, unchanged.
#
#     cmake -S targets/esp32s3/ui/host -B <build> [-DNE_UI_UPDATE_GOLDEN=ON]
#     cmake --build <build>
#     <build>/ne_ui_golden            # run with the golden dir as ./golden
#
# scripts/run_ui_golden.sh is the only intended entry point: it pins the
# checksum, prepares ./golden, and picks cmake or the idf container.
cmake_minimum_required(VERSION 3.24)
project(ne_ui_host C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

option(NE_UI_UPDATE_GOLDEN
       "Write goldens instead of comparing them (scripts/run_ui_golden.sh --update)" OFF)
if(NE_UI_UPDATE_GOLDEN)
    # Directory scope, so lv_conf.h sees it when LVGL itself is compiled:
    # LV_TEST_SCREENSHOT_CREATE_REFERENCE_IMAGE is baked into lvgl, not main.c.
    add_compile_definitions(NE_UI_UPDATE_GOLDEN=1)
endif()

include(FetchContent)
FetchContent_Declare(
    lvgl
    URL https://github.com/lvgl/lvgl/archive/refs/tags/v9.6.0.tar.gz
    URL_HASH SHA256=b20ee3acc1bba13c62d854f9ebd62e4c51e0b443b1e0225892e86442defa84df
    DOWNLOAD_EXTRACT_TIMESTAMP OFF)
# Parts of the LVGL tree this harness does not build (the library still
# compiles their translation units to empty objects).
set(CONFIG_LV_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_BUILD_DEMOS OFF CACHE BOOL "" FORCE)
set(CONFIG_LV_USE_THORVG OFF CACHE BOOL "" FORCE)
set(LV_BUILD_CONF_PATH "${CMAKE_CURRENT_SOURCE_DIR}/lv_conf.h" CACHE PATH "" FORCE)
FetchContent_MakeAvailable(lvgl)

add_executable(
    ne_ui_golden
    main.c
    ../src/ne_ui.c
    ../src/ne_ui_strings.c
    ../fonts/ne_font_12.c
    ../fonts/ne_font_16.c
    ../fonts/ne_font_22.c)
target_include_directories(ne_ui_golden PRIVATE ../include ../src ../fonts ..)
target_compile_options(ne_ui_golden PRIVATE -Wall -Wextra -Werror)
target_link_libraries(ne_ui_golden PRIVATE lvgl)
