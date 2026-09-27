/*
 * The screens (TSK-S4-10). Deterministic: no clock, no randomness, no animation
 * (every animation-capable call passes LV_ANIM_OFF) and no automatic scrolling,
 * so the same state renders the same pixels. Agent data is drawn as given, with
 * two rules that keep it on the panel (docs/spec/ui.md §4):
 *
 *  - a single-line label gets one line: `lv_label_set_max_lines(…, 1)`, a fixed
 *    one-line height and DOTS ellipsis, and its text goes through
 *    ne_ui_text_single_line(), so an agent newline cannot break the layout;
 *  - multi-line agent data goes into a fixed-size clipped box (like the reply),
 *    which scrolls at run time and never grows over its neighbours.
 */

#include "ne_ui.h"

#include "ne_fonts.h"
#include "ne_ui_strings.h"
#include "ne_ui_text.h"

#define MARGIN 16
#define CONTENT_W (NE_UI_WIDTH - 2 * MARGIN)
#define TITLE_Y 12
#define BODY_Y 56

/* The palette: one dark surface, one text colour, one per signal. */
#define C_BG 0x0B0F14u
#define C_SURFACE 0x161D26u
#define C_TEXT 0xE6EDF3u
#define C_MUTED 0x93A1B1u
#define C_ALLOW 0x3FB950u
#define C_BLOCK 0xF85149u
#define C_WARN 0xD29922u
#define C_INFO 0x58A6FFu

static int pct(int value)
{
    if (value < 0) {
        return 0;
    }
    return value > 100 ? 100 : value;
}

/*
 * A label. `wrap` labels are for fixed-size boxes and may grow in height inside
 * one; every other label is exactly one line with a DOTS ellipsis.
 */
static lv_obj_t *add_label(lv_obj_t *parent, const char *text, const lv_font_t *font,
                           uint32_t color, int32_t width, bool wrap)
{
    lv_obj_t *label = lv_label_create(parent);
    lv_label_set_text(label, text == NULL ? "" : text);
    lv_obj_set_style_text_font(label, font, 0);
    lv_obj_set_style_text_color(label, lv_color_hex(color), 0);
    lv_obj_set_style_text_line_space(label, 2, 0);
    if (width > 0) {
        lv_obj_set_width(label, width);
    }
    if (wrap) {
        lv_label_set_long_mode(label, LV_LABEL_LONG_MODE_WRAP);
    } else {
        /* One line, always: without the one-line height, LVGL 9.6's DOTS mode
         * wraps instead of ellipsizing (docs/spec/ui.md §4). */
        lv_label_set_long_mode(label, LV_LABEL_LONG_MODE_DOTS);
        lv_label_set_max_lines(label, 1);
        lv_obj_set_height(label, font->line_height);
    }
    return label;
}

/* A label with its own background: a one-line chip whose size follows its text,
 * capped at `max_width` so a wide glyph run cannot push it off the panel (LVGL
 * then ellipsizes inside the cap). */
static lv_obj_t *add_badge(lv_obj_t *parent, const char *text, int32_t x, int32_t y,
                           const lv_font_t *font, uint32_t bg, uint32_t fg, int32_t max_width)
{
    lv_obj_t *label = add_label(parent, text, font, fg, 0, false);
    lv_obj_set_style_bg_color(label, lv_color_hex(bg), 0);
    lv_obj_set_style_bg_opa(label, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(label, 6, 0);
    lv_obj_set_style_pad_hor(label, 10, 0);
    lv_obj_set_style_pad_ver(label, 4, 0);
    /* Height = one line + the padding: leave it at one line and the padded
     * content area is shorter, which makes LVGL's DOTS replace bytes of the
     * text ("…" or "Z") with dots and corrupt a multi-byte string. */
    lv_obj_set_height(label, font->line_height + 8);
    if (max_width > 0) {
        lv_obj_set_style_max_width(label, max_width, 0);
    }
    lv_obj_set_pos(label, x, y);
    return label;
}

static lv_obj_t *add_bar(lv_obj_t *parent, int32_t value, int32_t x, int32_t y, uint32_t color)
{
    lv_obj_t *bar = lv_bar_create(parent);
    lv_obj_set_pos(bar, x, y);
    lv_obj_set_size(bar, CONTENT_W, 12);
    lv_bar_set_range(bar, 0, 100);
    lv_bar_set_value(bar, pct(value), LV_ANIM_OFF);
    lv_obj_set_style_bg_color(bar, lv_color_hex(C_SURFACE), 0);
    lv_obj_set_style_bg_opa(bar, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(bar, 0, 0);
    lv_obj_set_style_radius(bar, 6, 0);
    lv_obj_set_style_bg_color(bar, lv_color_hex(color), LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(bar, LV_OPA_COVER, LV_PART_INDICATOR);
    lv_obj_set_style_radius(bar, 6, LV_PART_INDICATOR);
    return bar;
}

/* A fixed-size container the runtime may scroll; it clips, so text can never
 * leave the panel. Multi-line agent data always goes in one. */
static lv_obj_t *add_scroll_box(lv_obj_t *parent, int32_t x, int32_t y, int32_t w, int32_t h)
{
    lv_obj_t *box = lv_obj_create(parent);
    lv_obj_remove_style_all(box);
    lv_obj_set_pos(box, x, y);
    lv_obj_set_size(box, w, h);
    lv_obj_set_style_bg_opa(box, LV_OPA_TRANSP, 0);
    lv_obj_set_scroll_elastic(box, false);
    lv_obj_set_scroll_dir(box, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(box, LV_SCROLLBAR_MODE_OFF);
    return box;
}

/* A clipped, scrollable region holding one wrapping label. */
static lv_obj_t *add_text_box(lv_obj_t *parent, int32_t x, int32_t y, int32_t w, int32_t h,
                              const char *text, const lv_font_t *font, uint32_t color)
{
    lv_obj_t *box = add_scroll_box(parent, x, y, w, h);
    lv_obj_t *label = add_label(box, text, font, color, w, true);
    lv_obj_set_pos(label, 0, 0);
    return box;
}

static void add_title(ne_ui_t *ui, const char *text, uint32_t color)
{
    lv_obj_t *label = add_label(ui->root, text, &ne_font_22, color, CONTENT_W, false);
    lv_obj_set_pos(label, MARGIN, TITLE_Y);
}

static bool ready(ne_ui_t *ui)
{
    if (ui == NULL || ui->root == NULL || ne_ui_strings(ui->language) == NULL) {
        return false;
    }
    lv_obj_clean(ui->root);
    return true;
}

/* -- screens ------------------------------------------------------------------------------ */

void ne_ui_show_boot(ne_ui_t *ui, const ne_ui_boot_state_t *state)
{
    const ne_ui_strings_t *s;
    const char *phase;
    uint32_t color;
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    switch (state->phase) {
    case NE_UI_BOOT_PASSED:
        phase = s->boot_passed;
        color = C_ALLOW;
        break;
    case NE_UI_BOOT_FAILED:
        phase = s->boot_failed;
        color = C_BLOCK;
        break;
    case NE_UI_BOOT_RUNNING:
    default:
        phase = s->boot_running;
        color = C_INFO;
        break;
    }
    add_title(ui, s->boot_self_test, C_TEXT);
    lv_obj_set_pos(add_label(ui->root, phase, &ne_font_22, color, CONTENT_W, false), MARGIN, 52);
    add_bar(ui->root,
            state->phase == NE_UI_BOOT_RUNNING ? 60
            : state->phase == NE_UI_BOOT_PASSED ? 100
                                                : 0,
            MARGIN, 96, color);
    if (state->phase == NE_UI_BOOT_FAILED && state->reason != NULL) {
        char text[NE_UI_TEXT_MAX + 4];
        ne_ui_text_truncate(text, sizeof(text), state->reason, NE_UI_TEXT_MAX);
        add_text_box(ui->root, MARGIN, 120, CONTENT_W, 112, text, &ne_font_16, C_MUTED);
    }
}

void ne_ui_show_idle(ne_ui_t *ui, const ne_ui_idle_state_t *state)
{
    const ne_ui_strings_t *s;
    char agent[NE_UI_TEXT_MAX + 4];
    lv_obj_t *dot;
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    ne_ui_text_single_line(agent, sizeof(agent), state->agent, 24);
    add_title(ui, agent, C_TEXT);
    lv_obj_set_pos(add_label(ui->root, s->idle_hint, &ne_font_16, C_MUTED, CONTENT_W, true), MARGIN,
                   BODY_Y);
    dot = lv_obj_create(ui->root);
    lv_obj_remove_style_all(dot);
    lv_obj_set_size(dot, 12, 12);
    lv_obj_set_pos(dot, MARGIN, 130);
    lv_obj_set_style_radius(dot, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_bg_color(dot, lv_color_hex(state->network_up ? C_ALLOW : C_MUTED), 0);
    lv_obj_set_style_bg_opa(dot, LV_OPA_COVER, 0);
    lv_obj_set_pos(
        add_label(ui->root, state->network_up ? s->net_online : s->net_offline, &ne_font_16,
                  state->network_up ? C_TEXT : C_MUTED, CONTENT_W - 24, false),
        MARGIN + 22, 126);
}

void ne_ui_show_voice(ne_ui_t *ui, const ne_ui_voice_state_t *state)
{
    const ne_ui_strings_t *s;
    char transcript[NE_UI_TEXT_MAX + 4]; /* the thinking box: wrap, newlines kept */
    char preview[NE_UI_TEXT_MAX + 4];    /* the speaking heard row: one line, cut */
    char reply[NE_UI_TEXT_MAX + 4];
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    ne_ui_text_truncate(transcript, sizeof(transcript), state->transcript, NE_UI_TEXT_MAX);
    ne_ui_text_single_line(preview, sizeof(preview), state->transcript, 40);
    ne_ui_text_truncate(reply, sizeof(reply), state->reply, NE_UI_TEXT_MAX);
    switch (state->phase) {
    case NE_UI_VOICE_THINKING:
        add_title(ui, s->thinking, C_INFO);
        lv_obj_set_pos(add_label(ui->root, s->heard, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       50);
        add_text_box(ui->root, MARGIN, 74, CONTENT_W, 158, transcript, &ne_font_16, C_TEXT);
        break;
    case NE_UI_VOICE_SPEAKING:
        add_title(ui, s->speaking, C_ALLOW);
        lv_obj_set_pos(add_label(ui->root, s->heard, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       50);
        lv_obj_set_pos(add_label(ui->root, preview, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       72);
        lv_obj_set_pos(add_label(ui->root, s->reply, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       94);
        add_text_box(ui->root, MARGIN, 116, CONTENT_W, 104, reply, &ne_font_16, C_TEXT);
        break;
    case NE_UI_VOICE_LISTENING:
    default:
        add_title(ui, s->listening, C_INFO);
        if (state->interrupted) {
            add_badge(ui->root, s->barge_in, NE_UI_WIDTH - MARGIN - 110, BODY_Y - 4, &ne_font_12,
                      C_SURFACE, C_WARN, 110);
        }
        add_bar(ui->root, state->level_pct, MARGIN, BODY_Y + 54, C_INFO);
        lv_obj_set_pos(add_label(ui->root, s->listening_hint, &ne_font_16, C_MUTED, CONTENT_W, false),
                       MARGIN, BODY_Y + 84);
        break;
    }
}

void ne_ui_show_confirm(ne_ui_t *ui, const ne_ui_confirm_state_t *state)
{
    const ne_ui_strings_t *s;
    char action[NE_UI_TEXT_MAX + 4];
    char message[NE_UI_TEXT_MAX + 4];
    char fallback[NE_UI_TEXT_MAX + 4];
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    /* 20 bytes plus the ellipsis keeps the chip inside the panel: the cap only
     * bites on a name far longer than any real @action, and its … stays visible. */
    ne_ui_text_single_line(action, sizeof(action), state->action, 20);
    ne_ui_text_truncate(message, sizeof(message), state->message, NE_UI_TEXT_MAX);
    ne_ui_text_single_line(fallback, sizeof(fallback), state->fallback, 40);
    add_title(ui, s->confirm_title, C_WARN);
    add_badge(ui->root, action, MARGIN, 50, &ne_font_16, C_SURFACE, C_TEXT, CONTENT_W);
    add_text_box(ui->root, MARGIN, 86, CONTENT_W, 70, message, &ne_font_16, C_TEXT);
    if (state->fallback != NULL) {
        lv_obj_t *label = add_label(ui->root, s->confirm_fallback, &ne_font_12, C_MUTED, CONTENT_W,
                                    false);
        lv_obj_set_pos(label, MARGIN, 158);
        lv_obj_set_pos(add_label(ui->root, fallback, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       179);
    }
    /* The chips are the two spoken answers: no separate hint line to collide with. */
    add_badge(ui->root, s->confirm_yes, MARGIN, 201, &ne_font_16, C_ALLOW, C_BG, 124);
    add_badge(ui->root, s->confirm_no, MARGIN + 132, 201, &ne_font_16, C_BLOCK, C_BG, 148);
}

void ne_ui_show_verdict(ne_ui_t *ui, const ne_ui_verdict_state_t *state)
{
    const ne_ui_strings_t *s;
    char action[NE_UI_TEXT_MAX + 4];
    char detail[NE_UI_TEXT_MAX + 4];
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    ne_ui_text_single_line(action, sizeof(action), state->action, 30);
    ne_ui_text_truncate(detail, sizeof(detail), state->detail, NE_UI_TEXT_MAX);
    add_title(ui, state->allowed ? s->verdict_allowed : s->verdict_blocked,
              state->allowed ? C_ALLOW : C_BLOCK);
    lv_obj_set_pos(add_label(ui->root, s->action, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                   50);
    lv_obj_set_pos(add_label(ui->root, action, &ne_font_16, C_TEXT, CONTENT_W, false), MARGIN, 72);
    if (!state->allowed) {
        lv_obj_set_pos(add_label(ui->root, s->reason, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN,
                       102);
        add_text_box(ui->root, MARGIN, 124, CONTENT_W, 40,
                     ne_ui_reason_label(ui->language, state->reason), &ne_font_16, C_WARN);
    }
    if (state->detail != NULL) {
        add_text_box(ui->root, MARGIN, 167, CONTENT_W, 61, detail, &ne_font_12, C_MUTED);
    }
}

void ne_ui_show_degraded(ne_ui_t *ui, const ne_ui_degraded_state_t *state)
{
    const ne_ui_strings_t *s;
    lv_obj_t *box;
    int32_t y = 50;
    size_t i;
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    add_title(ui, s->degraded_title, C_WARN);
    if (state->stt_down) {
        lv_obj_set_pos(add_label(ui->root, s->degraded_stt, &ne_font_16, C_TEXT, CONTENT_W, false),
                       MARGIN + 14, y);
        y += 26;
    }
    if (state->tts_down) {
        lv_obj_set_pos(add_label(ui->root, s->degraded_tts, &ne_font_16, C_TEXT, CONTENT_W, false),
                       MARGIN + 14, y);
        y += 26;
    }
    if (state->system_two_down) {
        lv_obj_set_pos(add_label(ui->root, s->degraded_system_two, &ne_font_16, C_TEXT, CONTENT_W,
                                 false),
                       MARGIN + 14, y);
        y += 26;
    }
    lv_obj_set_pos(add_label(ui->root, s->degraded_commands, &ne_font_12, C_MUTED, CONTENT_W, false),
                   MARGIN, 132);
    /* Up to NE_UI_MAX_COMMANDS one-line lines in a scroll region: a long name is
     * elided at the panel width, the rest scrolls, nothing grows a widget per
     * command however many an agent declares. */
    box = add_scroll_box(ui->root, MARGIN, 155, CONTENT_W, 69);
    for (i = 0; state->commands != NULL && i < state->command_count && i < NE_UI_MAX_COMMANDS; i++) {
        char command[NE_UI_TEXT_MAX + 4];
        lv_obj_t *line;
        ne_ui_text_single_line(command, sizeof(command), state->commands[i], 40);
        line = add_label(box, command, &ne_font_12, C_TEXT, CONTENT_W, false);
        lv_obj_set_pos(line, 0, (int32_t)i * 20);
    }
}

void ne_ui_show_sensor(ne_ui_t *ui, const ne_ui_sensor_state_t *state)
{
    const ne_ui_strings_t *s;
    size_t i;
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    add_title(ui, s->sensor_title, C_TEXT);
    for (i = 0; state->readings != NULL && i < state->reading_count && i < NE_UI_MAX_READINGS; i++) {
        const ne_ui_reading_t *reading = &state->readings[i];
        char name[NE_UI_TEXT_MAX + 4];
        char value[NE_UI_TEXT_MAX + 4];
        char unit[64];
        char band[64];
        lv_obj_t *value_label;
        int32_t y = 48 + (int32_t)i * 48;
        ne_ui_text_single_line(name, sizeof(name), reading->name, 40);
        ne_ui_text_single_line(value, sizeof(value), reading->value, 12);
        ne_ui_text_single_line(unit, sizeof(unit), reading->unit, 6);
        ne_ui_text_single_line(band, sizeof(band), reading->band, 20);
        lv_obj_set_pos(add_label(ui->root, name, &ne_font_12, C_MUTED, CONTENT_W, false), MARGIN, y);
        /* Value, unit and band share the row: each has a cap so a long one
         * ellipsizes instead of running into the next. */
        value_label = add_label(ui->root, value, &ne_font_16, C_TEXT, 0, false);
        lv_obj_set_style_max_width(value_label, 100, 0);
        lv_obj_set_pos(value_label, MARGIN, y + 20);
        if (reading->unit != NULL) {
            lv_obj_t *unit_label = add_label(ui->root, unit, &ne_font_12, C_MUTED, 0, false);
            lv_obj_set_style_max_width(unit_label, 40, 0);
            lv_obj_align_to(unit_label, value_label, LV_ALIGN_OUT_RIGHT_MID, 6, 0);
        }
        if (reading->band != NULL) {
            lv_obj_t *badge = add_badge(ui->root, band, 0, 0, &ne_font_12, C_SURFACE, C_TEXT, 140);
            /* Right-aligned: a long band name grows left, never past the edge. */
            lv_obj_align(badge, LV_ALIGN_TOP_RIGHT, -MARGIN, y + 20);
        }
    }
}

void ne_ui_show_ota(ne_ui_t *ui, const ne_ui_ota_state_t *state)
{
    const ne_ui_strings_t *s;
    const char *phase;
    uint32_t color;
    char detail[NE_UI_TEXT_MAX + 4];
    bool with_bar;
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    switch (state->phase) {
    case NE_UI_OTA_DOWNLOADING:
        phase = s->ota_downloading;
        color = C_INFO;
        break;
    case NE_UI_OTA_VERIFYING:
        phase = s->ota_verifying;
        color = C_INFO;
        break;
    case NE_UI_OTA_REJECTED:
        phase = s->ota_rejected;
        color = C_BLOCK;
        break;
    case NE_UI_OTA_SWITCHING:
        phase = s->ota_switching;
        color = C_INFO;
        break;
    case NE_UI_OTA_ROLLED_BACK:
        phase = s->ota_rolled_back;
        color = C_WARN;
        break;
    case NE_UI_OTA_CHECKING:
    default:
        phase = s->ota_checking;
        color = C_INFO;
        break;
    }
    with_bar = state->phase == NE_UI_OTA_CHECKING || state->phase == NE_UI_OTA_DOWNLOADING;
    ne_ui_text_truncate(detail, sizeof(detail), state->detail, NE_UI_TEXT_MAX);
    add_title(ui, s->ota_title, C_TEXT);
    lv_obj_set_pos(add_label(ui->root, phase, &ne_font_22, color, CONTENT_W, false), MARGIN, BODY_Y);
    if (with_bar) {
        add_bar(ui->root, state->progress_pct, MARGIN, BODY_Y + 44, color);
        lv_obj_set_pos(add_label(ui->root, s->progress, &ne_font_12, C_MUTED, CONTENT_W, false),
                       MARGIN, BODY_Y + 64);
    }
    if (state->detail != NULL) {
        add_text_box(ui->root, MARGIN, BODY_Y + 90, CONTENT_W, 76, detail, &ne_font_16, C_MUTED);
    }
}

void ne_ui_show_fatal(ne_ui_t *ui, const ne_ui_fatal_state_t *state)
{
    const ne_ui_strings_t *s;
    char reason[NE_UI_TEXT_MAX + 4];
    if (!ready(ui) || state == NULL) {
        return;
    }
    s = ne_ui_strings(ui->language);
    ne_ui_text_truncate(reason, sizeof(reason), state->reason, NE_UI_TEXT_MAX);
    add_title(ui, s->fatal_title, C_BLOCK);
    add_text_box(ui->root, MARGIN, 54, CONTENT_W, 124, reason, &ne_font_16, C_TEXT);
    lv_obj_set_pos(add_label(ui->root, s->fatal_hint, &ne_font_16, C_MUTED, CONTENT_W, false), MARGIN,
                   196);
}

/* -- lifecycle ---------------------------------------------------------------------------- */

bool ne_ui_init(ne_ui_t *ui, lv_display_t *display, ne_ui_language_t language)
{
    if (ui == NULL) {
        return false;
    }
    ui->display = NULL;
    ui->root = NULL;
    ui->language = NE_UI_LANG_NONE;
    if (display == NULL || ne_ui_strings(language) == NULL) {
        return false; /* no strings for that language: nothing is ever drawn */
    }
    ui->display = display;
    ui->language = language;
    lv_obj_clean(lv_display_get_screen_active(display)); /* one root, whatever ran before */
    ui->root = lv_obj_create(lv_display_get_screen_active(display));
    lv_obj_remove_style_all(ui->root);
    lv_obj_set_size(ui->root, lv_display_get_horizontal_resolution(display),
                    lv_display_get_vertical_resolution(display));
    lv_obj_set_style_bg_color(ui->root, lv_color_hex(C_BG), 0);
    lv_obj_set_style_bg_opa(ui->root, LV_OPA_COVER, 0);
    lv_obj_set_scrollable(ui->root, false);
    return true;
}
