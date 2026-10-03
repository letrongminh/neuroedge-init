/*
 * NeuroEdge device UI — C99 on the LVGL API only (TSK-S4-10, FR-HAL-01).
 *
 * The screens of the 320x240 ST7789 panel of the ESP32-S3-BOX-3
 * (boards/esp32s3-box-3.toml). The panel driver and the touch input are
 * TSK-S4-01; this component draws into any `lv_display_t` the caller created,
 * so the same sources build on the host against LVGL for the golden images
 * (targets/esp32s3/ui/host/, scripts/run_ui_golden.sh) and link unchanged into
 * the firmware once the display driver exists.
 *
 * Language. `agent.toml` picks one language per agent and the generated
 * component carries it as `NE_AGENT_LANGUAGE`; the rule is docs/spec/ui.md
 * §Ngôn ngữ. Here that code is a string table and a set of glyphs, or nothing:
 * `ne_ui_init` refuses a language this component does not ship, so a screen is
 * never drawn in a language it cannot spell.
 *
 * Determinism. Rendering reads no clock and no randomness, starts no animation
 * (every animation-capable call passes LV_ANIM_OFF) and scrolls nothing by
 * itself; the same state struct renders the same pixels, which is what makes
 * the golden compare meaningful.
 *
 * Data. Text that comes from the agent — a gate's on_block message, an action
 * name, a reply, a sensor reading — is data, drawn as given. Only the labels
 * below (`ne_ui_strings_t`) are the UI's own and translated.
 */
#ifndef NE_UI_H
#define NE_UI_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "lvgl/lvgl.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The panel this UI is laid out for; the host harness renders exactly this. */
#define NE_UI_WIDTH 320
#define NE_UI_HEIGHT 240

/* Longest agent-provided text drawn on one screen, truncation included. */
#define NE_UI_TEXT_MAX 320u

/* At most this many sensor readings / local commands are drawn. The arrays may
 * be longer; the UI never creates a widget per element an agent declares, so a
 * hostile count cannot exhaust the heap. */
#define NE_UI_MAX_READINGS 4u
#define NE_UI_MAX_COMMANDS 4u

/* The languages the UI ships a string table and font glyphs for (docs/spec/ui.md
 * §Ngôn ngữ). `NE_UI_LANG_NONE` is what an unsupported code resolves to; every
 * show function refuses to draw with it. */
typedef enum {
    NE_UI_LANG_NONE = -1,
    NE_UI_LANG_VI = 0,
    NE_UI_LANG_EN = 1,
} ne_ui_language_t;

/* Why a gate blocked, same vocabulary and values as `ne_reason` in
 * targets/esp32s3/components/ne_gate/include/ne_walker.h (and REASONS in
 * python/neuroedge/engine/firmware.py). A Python pin keeps them equal. */
typedef enum {
    NE_UI_REASON_NONE = 0,
    NE_UI_REASON_CONDITION_NOT_MET = 1,
    NE_UI_REASON_CRITERION_UNAVAILABLE = 2,
    NE_UI_REASON_CONFIDENCE_UNAVAILABLE = 3,
    NE_UI_REASON_ARGUMENT_OUT_OF_RANGE = 4,
    NE_UI_REASON_GATE_UNREACHABLE = 5,
    NE_UI_REASON_BUDGET_EXCEEDED = 6,
    NE_UI_REASON_VALUE_OUT_OF_RANGE = 7,
    NE_UI_REASON_COUNT = 8,
} ne_ui_reason_t;

/* The boot self-test phases (main/gate_selftest.c). */
typedef enum {
    NE_UI_BOOT_RUNNING = 0,
    NE_UI_BOOT_PASSED = 1,
    NE_UI_BOOT_FAILED = 2,
} ne_ui_boot_phase_t;

/* The voice states that have a screen (python/neuroedge/perception/voice_fsm.py:
 * IDLE is `ne_ui_show_idle`; BARGE_IN reaches the screen as a new LISTENING
 * turn, with `interrupted` set). */
typedef enum {
    NE_UI_VOICE_LISTENING = 0,
    NE_UI_VOICE_THINKING = 1,
    NE_UI_VOICE_SPEAKING = 2,
} ne_ui_voice_phase_t;

/* The phases of an OTA update (another worker's task; the UI only draws them). */
typedef enum {
    NE_UI_OTA_CHECKING = 0,
    NE_UI_OTA_DOWNLOADING = 1,
    NE_UI_OTA_VERIFYING = 2,
    NE_UI_OTA_REJECTED = 3,
    NE_UI_OTA_SWITCHING = 4,
    NE_UI_OTA_ROLLED_BACK = 5,
} ne_ui_ota_phase_t;

/*
 * One screen's state. `const char *` fields are agent data, drawn as given and
 * never translated; a NULL one is drawn as an empty line.
 *
 * Agent data is untrusted. The UI copies at most NE_UI_TEXT_MAX bytes of it,
 * turns a byte that is not part of a valid UTF-8 sequence into '?' and never
 * lets a field wrap over another widget: one-line text has its control bytes
 * (an agent newline among them) replaced with spaces, multi-line text goes into
 * a fixed-size clipped box. See docs/spec/ui.md §4. Text should arrive
 * NFC-normalised: NFD Vietnamese has no glyphs in the fonts and draws as boxes.
 */
typedef struct {
    ne_ui_boot_phase_t phase;
    const char *reason; /* NE_UI_BOOT_FAILED: the self-test's own message */
} ne_ui_boot_state_t;

typedef struct {
    const char *agent;  /* [agent] name, as the device knows itself */
    bool network_up;    /* Wi-Fi associated, as the runtime knows it */
} ne_ui_idle_state_t;

typedef struct {
    ne_ui_voice_phase_t phase;
    int level_pct;          /* LISTENING: input level, 0..100 */
    bool interrupted;       /* LISTENING after a barge-in */
    const char *transcript; /* THINKING, SPEAKING: what was heard */
    const char *reply;      /* SPEAKING: what is being said */
} ne_ui_voice_state_t;

typedef struct {
    const char *action;   /* the @action the gate guards */
    const char *message;  /* on_block.message: the agent's question, data */
    const char *fallback; /* on_block.fallback_action, or NULL */
} ne_ui_confirm_state_t;

typedef struct {
    bool allowed;
    ne_ui_reason_t reason; /* NE_UI_REASON_NONE when allowed */
    const char *action;
    const char *detail;    /* the gate's message or the runtime's note, data */
} ne_ui_verdict_state_t;

typedef struct {
    bool stt_down;         /* cloud STT unreachable */
    bool tts_down;         /* cloud TTS unreachable */
    bool system_two_down;  /* System 2 (the model) unreachable */
    const char *const *commands; /* intents the local grammar still runs, data */
    size_t command_count;
} ne_ui_degraded_state_t;

typedef struct {
    const char *name;  /* "temperature", data */
    const char *value; /* "31.5", already formatted by the caller */
    const char *unit;  /* "°C", data */
    const char *band;  /* the band the runtime assigned, data */
} ne_ui_reading_t;

typedef struct {
    const ne_ui_reading_t *readings;
    size_t reading_count;
} ne_ui_sensor_state_t;

typedef struct {
    ne_ui_ota_phase_t phase;
    int progress_pct;    /* CHECKING, DOWNLOADING: 0..100 */
    const char *detail;  /* version, or why an image was rejected, data */
} ne_ui_ota_state_t;

typedef struct {
    const char *reason; /* why the gate runtime stopped, data */
} ne_ui_fatal_state_t;

/* The UI, allocated by the caller (a static in the firmware). */
typedef struct {
    lv_display_t *display;
    lv_obj_t *root;
    ne_ui_language_t language;
} ne_ui_t;

/* Language codes: "vi", "en", or the code of `language`; NE_UI_LANG_NONE has
 * none. `ne_ui_language_from_code` is case-sensitive, like `[agent] language`. */
const char *ne_ui_language_code(ne_ui_language_t language);
ne_ui_language_t ne_ui_language_from_code(const char *code);
bool ne_ui_language_supported(const char *code);

typedef struct ne_ui_strings ne_ui_strings_t;

/* The UI's own labels for `language`; NULL when the UI ships no strings for it. */
const ne_ui_strings_t *ne_ui_strings(ne_ui_language_t language);

/* The label of a reason code, in `language`. */
const char *ne_ui_reason_label(ne_ui_language_t language, ne_ui_reason_t reason);

/*
 * Prepare `ui` to draw on `display` in `language`. False — and no screen may be
 * shown — when the UI ships no strings for that language: the fail-closed path
 * of docs/spec/ui.md §Ngôn ngữ.
 */
bool ne_ui_init(ne_ui_t *ui, lv_display_t *display, ne_ui_language_t language);

/*
 * Draw one screen, replacing the last. A no-op before a successful init.
 *
 * Threading: every show call touches LVGL objects and must run under the LVGL
 * lock (`lv_lock()`/`lv_unlock()` when LV_USE_OS is not LV_OS_NONE; a bare-metal
 * single-task caller needs none). Stack: a call uses about 1 KB for its text
 * buffers (up to three NE_UI_TEXT_MAX + 4 arrays) plus what LVGL allocates while
 * building the widgets, so keep at least 2 KB of task stack free for it.
 */
void ne_ui_show_boot(ne_ui_t *ui, const ne_ui_boot_state_t *state);
void ne_ui_show_idle(ne_ui_t *ui, const ne_ui_idle_state_t *state);
void ne_ui_show_voice(ne_ui_t *ui, const ne_ui_voice_state_t *state);
void ne_ui_show_confirm(ne_ui_t *ui, const ne_ui_confirm_state_t *state);
void ne_ui_show_verdict(ne_ui_t *ui, const ne_ui_verdict_state_t *state);
void ne_ui_show_degraded(ne_ui_t *ui, const ne_ui_degraded_state_t *state);
void ne_ui_show_sensor(ne_ui_t *ui, const ne_ui_sensor_state_t *state);
void ne_ui_show_ota(ne_ui_t *ui, const ne_ui_ota_state_t *state);
void ne_ui_show_fatal(ne_ui_t *ui, const ne_ui_fatal_state_t *state);

#ifdef __cplusplus
}
#endif

#endif /* NE_UI_H */
