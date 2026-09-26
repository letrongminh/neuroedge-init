"""
The device UI's text helpers, compiled and fuzzed on this host (TSK-S4-10).

`targets/esp32s3/ui/src/ne_ui_text.c` handles untrusted agent text for the
panel: it must never read past the input, never write past its buffer and never
let an invalid byte through. The C driver below (no LVGL) is compiled with
AddressSanitizer and UndefinedBehaviorSanitizer and covers the cases the first
implementation got wrong — a string cut off in the middle of a sequence — plus
overlong forms, surrogates, code points above U+10FFFF, NUL in the middle, very
long unbreakable text and a few thousand seeded random byte strings. A missing
C compiler is a failure, not a skip (CONTRIBUTING.md §5).
"""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from .test_c_walker import STRICT, cc

UI = Path(__file__).parent.parent.parent / "targets" / "esp32s3" / "ui"

DRIVER = r"""
#include <stdio.h>
#include <string.h>

#include "ne_ui_text.h"

static int checks;
static int failures;

static void report(const char *label, const char *want, const char *got, size_t got_len)
{
    failures++;
    printf("FAIL %s: want \"%s\" got \"%s\" (%zu bytes)\n", label, want, got, got_len);
}

static void expect(const char *label, const char *text, size_t max_bytes, size_t cap, const char *want)
{
    char out[512];
    size_t n;
    checks++;
    memset(out, 0xA5, sizeof(out));
    n = ne_ui_text_truncate(out, cap, text, max_bytes);
    if (n != strlen(out) || strcmp(out, want) != 0) {
        report(label, want, out, n);
    }
}

static void expect_line(const char *label, const char *text, const char *want)
{
    char out[512];
    size_t n;
    checks++;
    memset(out, 0xA5, sizeof(out));
    n = ne_ui_text_single_line(out, sizeof(out), text, 320);
    if (n != strlen(out) || strcmp(out, want) != 0) {
        report(label, want, out, n);
    }
}

static void expect_sequence(const char *label, const char *text, size_t want)
{
    size_t n = ne_ui_text_sequence(text);
    checks++;
    if (n != want) {
        failures++;
        printf("FAIL %s: sequence want %zu got %zu\n", label, want, n);
    }
}

/* Every byte of the output is part of a valid sequence; NUL ends it. */
static int valid_utf8(const char *text)
{
    size_t i = 0;
    while (text[i] != '\0') {
        size_t n = ne_ui_text_sequence(text + i);
        if (n == 0) {
            return 0;
        }
        i += n;
    }
    return 1;
}

static unsigned long rng_state = 0x9E3779B97F4A7C15ul;

static unsigned next_u32(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return (unsigned)(rng_state >> 16);
}

static void fuzz(unsigned iterations)
{
    static char input[401];
    static char out[512];
    unsigned iter;
    for (iter = 0; iter < iterations; iter++) {
        size_t len = next_u32() % 400u;
        size_t i;
        size_t cap = 5u + next_u32() % 400u;
        size_t max_bytes = next_u32() % (cap + 1u);
        size_t n;
        for (i = 0; i < len; i++) {
            input[i] = (char)(next_u32() & 0xFFu);
        }
        input[len] = '\0';
        memset(out, 0x5A, sizeof(out));
        n = ne_ui_text_truncate(out, cap, input, max_bytes);
        checks++;
        if (n >= cap || strlen(out) != n || !valid_utf8(out)) {
            failures++;
            printf("FAIL fuzz[%u]: n=%zu cap=%zu valid=%d\n", iter, n, cap, valid_utf8(out));
            return;
        }
        memset(out, 0x5A, sizeof(out));
        n = ne_ui_text_single_line(out, cap, input, max_bytes);
        checks++;
        if (n >= cap || strlen(out) != n || !valid_utf8(out)) {
            failures++;
            printf("FAIL fuzz-line[%u]: n=%zu cap=%zu\n", iter, n);
            return;
        }
    }
}

int main(void)
{
    static char long_text[1001];
    static const char nul_middle[] = {'a', 'b', '\0', 'c', 'd', '\0'};

    /* Valid input, whole code points, no surprises. */
    expect("ascii fits", "abc", 320, 400, "abc");
    expect("vietnamese", "bật đèn", 320, 400, "bật đèn");
    expect("four byte", "\xF0\x9F\x98\x80", 320, 400, "\xF0\x9F\x98\x80");
    expect("cut ends with ellipsis", "abcdef", 3, 400, "abc\xE2\x80\xA6");
    expect("cut at a code point", "a\xC3\xA9", 2, 400, "a\xE2\x80\xA6");
    expect("cut mid sequence dropped, not split", "a\xC3\xA9", 3, 400, "a\xC3\xA9");
    expect("exactly max is not cut", "abc", 3, 400, "abc");
    expect("empty stays empty", "", 320, 400, "");
    expect("null text", NULL, 320, 400, "");

    /* A string cut off in the middle of a sequence: the bug ASan reproduced. */
    expect("truncated two byte tail", "c\xE1\xBA\xAFt \xC3", 320, 400, "c\xE1\xBA\xAFt ?");
    expect("truncated four byte tail", "\xF0", 320, 400, "?");
    expect("lone continuation", "\x80", 320, 400, "?");
    expect("overlong two byte", "\xC0\xAF", 320, 400, "??");
    expect("overlong three byte", "\xE0\x80\xAF", 320, 400, "???");
    expect("surrogate", "\xED\xA0\x80", 320, 400, "???");
    expect("above U+10FFFF", "\xF4\x90\x80\x80", 320, 400, "????");
    expect("five byte lead", "\xF8\x88\x80\x80\x80", 320, 400, "?????");
    expect("FF lead", "\xFF", 320, 400, "?");
    expect("C1 lead", "\xC1\xBF", 320, 400, "??");
    expect("valid then truncated", "ok \xE2\x82", 320, 400, "ok ??");

    /* NUL in the middle ends the text: never read past it. */
    expect("nul ends the text", nul_middle, 320, 400, "ab");

    /* Tiny and zero capacities still terminate and never write past cap. */
    expect("cap four", "abcd", 320, 4, "\xE2\x80\xA6");
    expect("cap five empty", "", 320, 5, "");
    expect("max zero", "abc", 0, 400, "\xE2\x80\xA6");

    /* One-line helper: control bytes become spaces, tabs and newlines included. */
    expect_line("newlines and tabs", "a\nb\tc\rd\x7F", "a b c d ");
    expect_line("normal text untouched", "bật đèn 31.5 °C", "bật đèn 31.5 °C");
    expect("newlines survive truncate", "a\nb", 320, 400, "a\nb");

    /* Very long unbreakable text, and the exact boundary. */
    memset(long_text, 'a', 1000);
    long_text[1000] = '\0';
    {
        char out[1100];
        size_t n = ne_ui_text_truncate(out, 400, long_text, 320);
        checks++;
        if (n != 323 || strlen(out) != 323 || out[319] != 'a' || out[320] != '\xE2') {
            failures++;
            printf("FAIL long unbreakable: n=%zu\n", n);
        }
        n = ne_ui_text_truncate(out, sizeof(out), long_text, 1000);
        checks++;
        if (n != 1000 || strlen(out) != 1000) {
            failures++;
            printf("FAIL long fits: n=%zu\n", n);
        }
    }

    /* The decoder's own contract. */
    expect_sequence("seq ascii", "a", 1);
    expect_sequence("seq nul", "", 1);
    expect_sequence("seq two", "\xC3\xA9", 2);
    expect_sequence("seq three", "\xE1\xBA\xAF", 3);
    expect_sequence("seq four", "\xF0\x9F\x98\x80", 4);
    expect_sequence("seq truncated", "\xE1\xBA", 0);
    expect_sequence("seq overlong", "\xC0\xAF", 0);
    expect_sequence("seq lone continuation", "\x80", 0);
    expect_sequence("seq surrogate", "\xED\xA0\x80", 0);
    expect_sequence("seq too high", "\xF4\x90\x80\x80", 0);
    expect_sequence("seq invalid lead", "\xFF", 0);

    fuzz(5000);

    printf("ne_ui_text: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
"""


def test_the_device_ui_text_helpers_survive_hostile_input(tmp_path: Path) -> None:
    driver = tmp_path / "test_ui_text_host.c"
    driver.write_text(DRIVER, encoding="utf-8")
    binary = tmp_path / "test_ui_text_host"
    command = [
        cc(),
        *STRICT[:-1],  # the driver itself is not held to -Wconversion
        "-O1",
        "-g",
        "-fsanitize=address,undefined",
        "-fno-sanitize-recover=all",
        "-fno-omit-frame-pointer",
        "-I",
        str(UI / "src"),
        str(UI / "src" / "ne_ui_text.c"),
        str(driver),
        "-o",
        str(binary),
    ]
    built = subprocess.run(command, capture_output=True, text=True)
    assert built.returncode == 0, textwrap.dedent(built.stderr)
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, f"{run.stdout}{run.stderr}"
    assert "0 failures" in run.stdout
