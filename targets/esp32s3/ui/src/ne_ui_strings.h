/*
 * Every label the UI writes itself, per language (TSK-S4-10).
 *
 * Agent data — gate messages, action names, replies, readings — never comes
 * through here: it is drawn as given (`ne_ui.h`). The struct is internal to the
 * component; callers get a `const ne_ui_strings_t *` from `ne_ui_strings()` and
 * need only the language code and the reason labels.
 *
 * Adding a language means adding one table here and the glyphs its strings need
 * to fonts/ranges.txt (checked by python/tests/test_ui_assets.py); the rule is
 * docs/spec/ui.md §Ngôn ngữ.
 */
#ifndef NE_UI_STRINGS_H
#define NE_UI_STRINGS_H

#include "ne_ui.h"

#ifdef __cplusplus
extern "C" {
#endif

struct ne_ui_strings {
    ne_ui_language_t language;
    const char *code; /* ISO-639-1, as [agent] language writes it */

    const char *boot_self_test;
    const char *boot_running;
    const char *boot_passed;
    const char *boot_failed;

    const char *idle_hint;
    const char *net_online;
    const char *net_offline;

    const char *listening;
    const char *listening_hint;
    const char *barge_in;
    const char *thinking;
    const char *speaking;
    const char *heard;
    const char *reply;

    const char *confirm_title;
    const char *confirm_yes;
    const char *confirm_no;
    const char *confirm_fallback;

    const char *verdict_allowed;
    const char *verdict_blocked;
    const char *action;
    const char *reason;

    const char *degraded_title;
    const char *degraded_stt;
    const char *degraded_tts;
    const char *degraded_system_two;
    const char *degraded_commands;

    const char *sensor_title;

    const char *ota_title;
    const char *ota_checking;
    const char *ota_downloading;
    const char *ota_verifying;
    const char *ota_rejected;
    const char *ota_switching;
    const char *ota_rolled_back;
    const char *progress;

    const char *fatal_title;
    const char *fatal_hint;

    const char *yes;
    const char *no;

    const char *reason_labels[NE_UI_REASON_COUNT];
};

#ifdef __cplusplus
}
#endif

#endif /* NE_UI_STRINGS_H */
