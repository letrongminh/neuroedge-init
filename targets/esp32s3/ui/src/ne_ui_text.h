/*
 * Text handling of the device UI (TSK-S4-10) — C99, no LVGL, no allocation.
 *
 * Kept apart from ne_ui.c so it can be compiled and fuzzed on the host without
 * LVGL (python/tests/test_ui_text.py builds it with ASan+UBSan). Agent data is
 * untrusted: it comes from a model, a person or a gate message, and the panel
 * must never read past it, split a character in half or draw control bytes.
 *
 * Rules, in one place:
 *  - a sequence is copied only when it is complete and valid: a proper lead
 *    byte with continuation bytes, no overlong form, no surrogate, no code
 *    point above U+10FFFF. A NUL byte always ends the text;
 *  - any byte that is not part of a valid sequence becomes one '?' (ASCII, so
 *    it has a glyph in every font), then the scan moves one byte on;
 *  - nothing is read past the first NUL, and nothing is written past `cap`;
 *  - when the rest did not fit, the copy ends with U+2026 (…) so a cut is
 *    visible rather than implied.
 */
#ifndef NE_UI_TEXT_H
#define NE_UI_TEXT_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * The length in bytes of the valid UTF-8 sequence at `text`, 1…4; 0 when the
 * byte is not a valid lead byte or the sequence is truncated, overlong, a
 * surrogate or beyond U+10FFFF. `text` must be NUL-terminated; the scan stops
 * at the NUL and never reads past it.
 */
size_t ne_ui_text_sequence(const char *text);

/*
 * Copy `text` into `out` (which holds `cap` bytes), at most `max_bytes` bytes
 * of whole code points; invalid bytes become '?' as above, and a cut ends with
 * U+2026. Always NUL-terminates and never writes more than `cap` bytes.
 * Returns the number of bytes written, the ellipsis included, the NUL not.
 */
size_t ne_ui_text_truncate(char *out, size_t cap, const char *text, size_t max_bytes);

/*
 * `ne_ui_text_truncate`, then every remaining C0 control byte (0x00–0x1F and
 * 0x7F) becomes a space: for labels a screen keeps on one line, where an agent
 * newline would otherwise break the layout. Returns the same as truncate.
 */
size_t ne_ui_text_single_line(char *out, size_t cap, const char *text, size_t max_bytes);

#ifdef __cplusplus
}
#endif

#endif /* NE_UI_TEXT_H */
