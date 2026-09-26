/*
 * Text handling of the device UI — the rules are in ne_ui_text.h.
 *
 * The decoder validates continuation bytes before accepting a length, so a
 * string that ends in a cut-off sequence cannot walk past its NUL. A byte that
 * is not part of a valid sequence becomes '?'; because a substitution is one
 * byte for one byte, the bytes copied from `text` are always its first `used`
 * bytes, and one memcpy per whole sequence is enough.
 */

#include "ne_ui_text.h"

#include <string.h>

size_t ne_ui_text_sequence(const char *text)
{
    const unsigned char *s = (const unsigned char *)text;
    unsigned char c = s[0];

    if (c < 0x80u) {
        return 1; /* ASCII, NUL included: the caller treats NUL as the end */
    }
    if (c >= 0xC2u && c <= 0xDFu) {
        return (s[1] & 0xC0u) == 0x80u ? 2u : 0u;
    }
    if (c >= 0xE0u && c <= 0xEFu) {
        /* A NUL fails the continuation test, so the scan stops there. */
        if ((s[1] & 0xC0u) != 0x80u || (s[2] & 0xC0u) != 0x80u) {
            return 0;
        }
        if (c == 0xE0u && s[1] < 0xA0u) {
            return 0; /* overlong */
        }
        if (c == 0xEDu && s[1] > 0x9Fu) {
            return 0; /* U+D800…U+DFFF, a surrogate */
        }
        return 3;
    }
    if (c >= 0xF0u && c <= 0xF4u) {
        if ((s[1] & 0xC0u) != 0x80u || (s[2] & 0xC0u) != 0x80u || (s[3] & 0xC0u) != 0x80u) {
            return 0;
        }
        if (c == 0xF0u && s[1] < 0x90u) {
            return 0; /* overlong */
        }
        if (c == 0xF4u && s[1] > 0x8Fu) {
            return 0; /* above U+10FFFF */
        }
        return 4;
    }
    return 0; /* 0x80…0xC1 (continuation or overlong lead), 0xF5…0xFF */
}

static size_t copy(char *out, size_t cap, const char *text, size_t max_bytes, int single_line)
{
    static const char ellipsis[] = "\xE2\x80\xA6";
    size_t used = 0;
    size_t written = 0;
    size_t limit;

    if (cap == 0) {
        return 0;
    }
    if (text == NULL || cap < sizeof(ellipsis)) {
        out[0] = '\0';
        return 0;
    }
    limit = cap - sizeof(ellipsis); /* the ellipsis, its three bytes and the NUL, fits below it */
    if (max_bytes < limit) {
        limit = max_bytes;
    }
    while (used < limit && text[used] != '\0') {
        size_t length = ne_ui_text_sequence(text + used);
        if (length == 0) {
            out[written] = '?';
            written += 1;
            used += 1;
            continue;
        }
        if (used + length > limit) {
            break; /* no room for this whole code point */
        }
        memcpy(out + written, text + used, length);
        written += length;
        used += length;
    }
    if (single_line) {
        size_t i;
        for (i = 0; i < written; i++) {
            unsigned char byte = (unsigned char)out[i];
            if (byte < 0x20u || byte == 0x7Fu) {
                out[i] = ' ';
            }
        }
    }
    if (text[used] == '\0') {
        out[written] = '\0';
        return written;
    }
    memcpy(out + written, ellipsis, sizeof(ellipsis));
    return written + sizeof(ellipsis) - 1u;
}

size_t ne_ui_text_truncate(char *out, size_t cap, const char *text, size_t max_bytes)
{
    return copy(out, cap, text, max_bytes, 0);
}

size_t ne_ui_text_single_line(char *out, size_t cap, const char *text, size_t max_bytes)
{
    return copy(out, cap, text, max_bytes, 1);
}
