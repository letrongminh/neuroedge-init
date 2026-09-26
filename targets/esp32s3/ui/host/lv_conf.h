/**
 * @file lv_conf.h
 * LVGL v9.6.0 configuration of the device UI host harness (TSK-S4-10).
 *
 * Only the options this harness changes; every other option keeps the default
 * of lv_conf_internal.h. The panel is RGB565 like the Box-3;
 * the test display itself renders into XRGB8888 for the PNG compare, as
 * lv_test_display_create() does.
 *
 * NE_UI_UPDATE_GOLDEN=1 (scripts/run_ui_golden.sh --update) lets the compare
 * write a missing reference; the normal build never writes a golden, it fails
 * on a missing or different one.
 */
#ifndef LV_CONF_H
#define LV_CONF_H

/* The Box-3 panel (boards/esp32s3-box-3.toml: rgb565). */
#define LV_COLOR_FORMAT_DEFAULT LV_COLOR_FORMAT_RGB565

/* libc on the host: screenshot compare allocates a 320x240x4 buffer per shot,
 * more than LVGL's built-in pool. (The firmware has its own lv_conf.h.) */
#define LV_USE_STDLIB_MALLOC LV_STDLIB_CLIB
#define LV_USE_STDLIB_STRING LV_STDLIB_CLIB
#define LV_USE_STDLIB_SPRINTF LV_STDLIB_CLIB

/* Argument checks logged to stdout, so a failing compare says where and what. */
#define LV_USE_LOG 1
#define LV_LOG_LEVEL LV_LOG_LEVEL_WARN
#define LV_LOG_PRINTF 1

/* Golden images: lv_test_screenshot_compare() reads and writes PNG through
 * lodepng, whose file access goes through LVGL's FS layer: drive 'A' is the
 * working directory, so the golden path is "A:golden/<language>/<case>.png". */
#define LV_USE_LODEPNG 1
#define LV_USE_FS_STDIO 1
#define LV_FS_STDIO_LETTER 'A'
#define LV_FS_STDIO_PATH ""
#define LV_FS_STDIO_CACHE_SIZE 0

/* The generated fonts are compressed (lv_font_conv --force-fast-kern-format). */
#define LV_USE_FONT_COMPRESSED 1

#define LV_USE_TEST 1
#define LV_USE_TEST_SCREENSHOT_COMPARE 1

#if defined(NE_UI_UPDATE_GOLDEN) && NE_UI_UPDATE_GOLDEN
#define LV_TEST_SCREENSHOT_CREATE_REFERENCE_IMAGE 1
#else
#define LV_TEST_SCREENSHOT_CREATE_REFERENCE_IMAGE 0
#endif

#endif /* LV_CONF_H */
