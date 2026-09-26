/*
 * The golden runner of the device UI (TSK-S4-10).
 *
 * For every screen x language x representative state it renders the state with
 * `lv_test_display_create()` (320x240, the Box-3 panel) and compares the screen
 * with the committed PNG under golden/<language>/<case>.png via
 * `lv_test_screenshot_compare()` (LVGL v9.6.0, src/debugging/test/).
 *
 * Normal mode never writes a golden: a missing reference and a difference both
 * fail, differences leave <case>_err.png next to the reference copy for
 * inspection, and the exit status is non-zero if anything failed. Update mode
 * (NE_UI_UPDATE_GOLDEN=1, scripts/run_ui_golden.sh --update) creates missing
 * references instead. The run happens with the working directory that holds
 * ./golden; scripts/run_ui_golden.sh arranges it.
 *
 * The data below is sample data, the kind of thing the runtime draws as given:
 * gate messages, action names, replies, readings. Only the labels around it are
 * the UI's, from ne_ui_strings.c.
 */

#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include "lvgl/lvgl.h"

#include "ne_ui.h"

/* LVGL's FS layer wants a drive letter; 'A' is the working directory (lv_conf.h). */
#define GOLDEN_DIR "A:golden"

typedef void (*case_fn)(ne_ui_t *ui, ne_ui_language_t language);

typedef struct {
    const char *name; /* also the golden file name, without .png */
    case_fn show;
} ui_case;

static const char *pick(ne_ui_language_t language, const char *vi, const char *en)
{
    return language == NE_UI_LANG_EN ? en : vi;
}

/* -- boot --------------------------------------------------------------------------------- */

static void case_boot_running(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_boot_state_t state = {NE_UI_BOOT_RUNNING, NULL};
    (void)language;
    ne_ui_show_boot(ui, &state);
}

static void case_boot_passed(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_boot_state_t state = {NE_UI_BOOT_PASSED, NULL};
    (void)language;
    ne_ui_show_boot(ui, &state);
}

static void case_boot_failed(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_boot_state_t state = {
        NE_UI_BOOT_FAILED,
        pick(language, "Cổng light_off@1.0.0 không nạp được: CRC sai",
             "Gate light_off@1.0.0 would not load: bad CRC"),
    };
    ne_ui_show_boot(ui, &state);
}

/* -- idle and the voice states -------------------------------------------------------------- */

static void case_voice_idle(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_idle_state_t state = {"home-voice", true};
    (void)language;
    ne_ui_show_idle(ui, &state);
}

static void case_voice_idle_offline(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_idle_state_t state = {"home-voice", false};
    (void)language;
    ne_ui_show_idle(ui, &state);
}

static void case_voice_listening(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_voice_state_t state = {NE_UI_VOICE_LISTENING, 64, false, NULL, NULL};
    (void)language;
    ne_ui_show_voice(ui, &state);
}

static void case_voice_barge_in(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_voice_state_t state = {NE_UI_VOICE_LISTENING, 72, true, NULL, NULL};
    (void)language;
    ne_ui_show_voice(ui, &state);
}

static void case_voice_thinking(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_voice_state_t state = {
        NE_UI_VOICE_THINKING, 0, false,
        pick(language, "bật đèn ngoài hiên", "turn on the porch light"), NULL};
    ne_ui_show_voice(ui, &state);
}

static void case_voice_speaking(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_voice_state_t state = {
        NE_UI_VOICE_SPEAKING,
        0,
        false,
        pick(language, "bật đèn ngoài hiên", "turn on the porch light"),
        pick(language,
             "Đã bật đèn ngoài hiên. Bạn còn cần gì nữa không? Mình có thể đọc tin tức, "
             "kiểm tra nhiệt độ trong phòng hoặc tắt đèn nếu không còn ai ở đó.",
             "The porch light is on. Anything else? I can read the news, check the room "
             "temperature, or turn the light off again if nobody is there."),
    };
    ne_ui_show_voice(ui, &state);
}

/* Longer than NE_UI_TEXT_MAX: the screen must cut whole code points and end with
 * an ellipsis, not wrap a split character. */
static void case_voice_speaking_long(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_voice_state_t state = {
        NE_UI_VOICE_SPEAKING,
        0,
        false,
        pick(language, "bật đèn ngoài hiên", "turn on the porch light"),
        pick(language,
             "Đã bật đèn ngoài hiên. Bạn còn cần gì nữa không? Mình có thể đọc tin tức, "
             "kiểm tra nhiệt độ trong phòng, xem độ ẩm, kiểm tra cửa ra vào, hoặc tắt đèn "
             "nếu không còn ai ở đó. Nếu bạn muốn nghe tin mới nhất thì mình cần mạng; khi "
             "mất mạng mình chỉ nói được các câu trả lời cục bộ và điều khiển đèn trong nhà "
             "thôi. Bạn cứ nói khi nào cần nhé — mình luôn ở đây, và mọi lệnh bật tắt đèn "
             "đều đi qua một cổng kiểm tra an toàn trước khi chân GPIO nào đó động.",
             "The porch light is on. Anything else? I can read the news, check the room "
             "temperature, look at the humidity, test the door contact, or turn the light "
             "off again if nobody is there. The latest news needs the network; when the "
             "network is down I can still answer from the local knowledge base and switch "
             "the lights in the house. Just say the word — and every light command goes "
             "through a safety gate before any GPIO pin moves at all."),
    };
    ne_ui_show_voice(ui, &state);
}

/* -- confirm and verdict -------------------------------------------------------------------- */

static void case_confirm(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_confirm_state_t state = {
        "light_off",
        pick(language, "Vẫn còn người trong phòng — bạn chắc muốn tắt đèn?",
             "Someone is still in the room — do you really want to turn the light off?"),
        NULL,
    };
    ne_ui_show_confirm(ui, &state);
}

static void case_verdict_allow(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_verdict_state_t state = {true, NE_UI_REASON_NONE, "light_on", NULL};
    (void)language;
    ne_ui_show_verdict(ui, &state);
}

static void verdict_block(ne_ui_t *ui, ne_ui_language_t language, ne_ui_reason_t reason,
                          const char *vi, const char *en)
{
    const ne_ui_verdict_state_t state = {false, reason, "light_off", pick(language, vi, en)};
    ne_ui_show_verdict(ui, &state);
}

static void case_verdict_block_condition_not_met(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_CONDITION_NOT_MET,
                  "room_empty = false: vẫn còn người trong phòng",
                  "room_empty = false: someone is still in the room");
}

static void case_verdict_block_criterion_unavailable(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_CRITERION_UNAVAILABLE,
                  "Cảm biến chuyển động không trả lời trong hạn",
                  "The motion sensor did not answer in time");
}

static void case_verdict_block_confidence_unavailable(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_CONFIDENCE_UNAVAILABLE,
                  "room_empty@0.82 dưới ngưỡng 0.90",
                  "room_empty@0.82 below the 0.90 floor");
}

static void case_verdict_block_argument_out_of_range(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_ARGUMENT_OUT_OF_RANGE,
                  "brightness = 120, ngoài khoảng 0..100", "brightness = 120, outside 0..100");
}

static void case_verdict_block_gate_unreachable(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_GATE_UNREACHABLE,
                  "Nguồn dữ kiện ngoại tuyến; cổng fail closed",
                  "The fact source is offline; the gate fails closed");
}

static void case_verdict_block_budget_exceeded(ne_ui_t *ui, ne_ui_language_t language)
{
    verdict_block(ui, language, NE_UI_REASON_BUDGET_EXCEEDED, "Thu thập dữ kiện 150 ms > ngân sách 120 ms",
                  "Gathering facts took 150 ms, over the 120 ms budget");
}

/* -- degraded, sensors, OTA, fatal ----------------------------------------------------------- */

static void case_degraded(ne_ui_t *ui, ne_ui_language_t language)
{
    static const char *const vi[] = {"bật đèn", "tắt đèn", "đọc tin tức"};
    static const char *const en[] = {"turn on the light", "turn off the light", "read the news"};
    const ne_ui_degraded_state_t state = {
        true, true, true, language == NE_UI_LANG_EN ? en : vi, 3};
    ne_ui_show_degraded(ui, &state);
}

static void case_sensor(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_reading_t readings[] = {
        {"temperature", "31.5", "°C", pick(language, "nóng", "warm")},
        {"humidity", "68", "%", pick(language, "bình thường", "normal")},
        {"door_contact", pick(language, "đóng", "closed"), NULL, NULL},
    };
    const ne_ui_sensor_state_t state = {readings, 3};
    ne_ui_show_sensor(ui, &state);
}

static void case_ota_checking(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {NE_UI_OTA_CHECKING, 0, NULL};
    (void)language;
    ne_ui_show_ota(ui, &state);
}

static void case_ota_downloading(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {NE_UI_OTA_DOWNLOADING, 42, "v1.1.0 (1.2 / 2.9 MB)"};
    (void)language;
    ne_ui_show_ota(ui, &state);
}

static void case_ota_verifying(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {NE_UI_OTA_VERIFYING, 100, "v1.1.0"};
    (void)language;
    ne_ui_show_ota(ui, &state);
}

static void case_ota_rejected(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {
        NE_UI_OTA_REJECTED, 0,
        pick(language, "Chữ ký không hợp lệ — ảnh bị bỏ, bản cũ vẫn chạy",
             "Bad signature — the image was discarded, the old one still runs")};
    ne_ui_show_ota(ui, &state);
}

static void case_ota_switching(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {
        NE_UI_OTA_SWITCHING, 100,
        pick(language, "Khởi động lại vào khe B", "Restarting into slot B")};
    ne_ui_show_ota(ui, &state);
}

static void case_ota_rolled_back(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_ota_state_t state = {
        NE_UI_OTA_ROLLED_BACK, 100,
        pick(language, "Bản mới không khởi động được — đã quay về v1.0.3",
             "The new image did not boot — back on v1.0.3")};
    ne_ui_show_ota(ui, &state);
}

static void case_fatal(ne_ui_t *ui, ne_ui_language_t language)
{
    const ne_ui_fatal_state_t state = {
        pick(language, "Tự kiểm tra gate thất bại: walker và engine host bất đồng ở check 12",
             "Gate self-test failed: the walker and the host engine disagreed at check 12")};
    ne_ui_show_fatal(ui, &state);
}

/* -- the matrix ----------------------------------------------------------------------------- */

static const ui_case CASES[] = {
    {"boot_running", case_boot_running},
    {"boot_passed", case_boot_passed},
    {"boot_failed", case_boot_failed},
    {"voice_idle", case_voice_idle},
    {"voice_idle_offline", case_voice_idle_offline},
    {"voice_listening", case_voice_listening},
    {"voice_barge_in", case_voice_barge_in},
    {"voice_thinking", case_voice_thinking},
    {"voice_speaking", case_voice_speaking},
    {"voice_speaking_long", case_voice_speaking_long},
    {"confirm", case_confirm},
    {"verdict_allow", case_verdict_allow},
    {"verdict_block_condition_not_met", case_verdict_block_condition_not_met},
    {"verdict_block_criterion_unavailable", case_verdict_block_criterion_unavailable},
    {"verdict_block_confidence_unavailable", case_verdict_block_confidence_unavailable},
    {"verdict_block_argument_out_of_range", case_verdict_block_argument_out_of_range},
    {"verdict_block_gate_unreachable", case_verdict_block_gate_unreachable},
    {"verdict_block_budget_exceeded", case_verdict_block_budget_exceeded},
    {"degraded", case_degraded},
    {"sensor", case_sensor},
    {"ota_checking", case_ota_checking},
    {"ota_downloading", case_ota_downloading},
    {"ota_verifying", case_ota_verifying},
    {"ota_rejected", case_ota_rejected},
    {"ota_switching", case_ota_switching},
    {"ota_rolled_back", case_ota_rolled_back},
    {"fatal", case_fatal},
};

/*
 * What a golden run cannot see: the language map and the reason labels. Checked
 * here so a broken one fails the same run, not a screen that happens to pass.
 */
static int self_checks(void)
{
    static const struct {
        const char *code;
        ne_ui_language_t language;
    } codes[] = {
        {"vi", NE_UI_LANG_VI},
        {"en", NE_UI_LANG_EN},
        {"fr", NE_UI_LANG_NONE},
        {"", NE_UI_LANG_NONE},
        {"VI", NE_UI_LANG_NONE},
        {"vietnamese", NE_UI_LANG_NONE},
        {"vi ", NE_UI_LANG_NONE},
    };
    size_t i;
    int bad = 0;

    for (i = 0; i < sizeof(codes) / sizeof(codes[0]); i++) {
        ne_ui_language_t got = ne_ui_language_from_code(codes[i].code);
        if (got != codes[i].language) {
            printf("FAIL language_from_code(%s) = %d, expected %d\n", codes[i].code, (int)got,
                   (int)codes[i].language);
            bad++;
        }
        if (ne_ui_language_supported(codes[i].code) != (codes[i].language != NE_UI_LANG_NONE)) {
            printf("FAIL language_supported(%s)\n", codes[i].code);
            bad++;
        }
    }
    for (i = 0; i < sizeof(codes) / sizeof(codes[0]); i++) {
        const char *code = ne_ui_language_code(codes[i].language);
        if (codes[i].language == NE_UI_LANG_NONE ? code != NULL
                                                 : strcmp(code, codes[i].code) != 0) {
            printf("FAIL language_code(%d)\n", (int)codes[i].language);
            bad++;
        }
    }
    for (i = 0; i < 2; i++) {
        ne_ui_language_t language = i == 0 ? NE_UI_LANG_VI : NE_UI_LANG_EN;
        int reason;
        if (ne_ui_reason_label(language, NE_UI_REASON_NONE)[0] != '\0') {
            printf("FAIL reason NONE has a label\n");
            bad++;
        }
        for (reason = NE_UI_REASON_CONDITION_NOT_MET; reason < NE_UI_REASON_COUNT; reason++) {
            if (ne_ui_reason_label(language, (ne_ui_reason_t)reason)[0] == '\0') {
                printf("FAIL reason %d has no label in language %d\n", reason, (int)language);
                bad++;
            }
        }
    }
    return bad;
}

int main(void)
{
    static const ne_ui_language_t languages[] = {NE_UI_LANG_VI, NE_UI_LANG_EN};
    lv_display_t *display;
    ne_ui_t ui;
    size_t i;
    size_t c;
    int total = 0;
    int failed = 0;

    if (self_checks() != 0) {
        printf("ui-golden: self-checks failed\n");
        return 1;
    }

    lv_init();
    display = lv_test_display_create(NE_UI_WIDTH, NE_UI_HEIGHT);
    if (display == NULL) {
        printf("FAIL lv_test_display_create(%d, %d)\n", NE_UI_WIDTH, NE_UI_HEIGHT);
        return 1;
    }

    for (i = 0; i < sizeof(languages) / sizeof(languages[0]); i++) {
        ne_ui_language_t language = languages[i];
        const char *code = ne_ui_language_code(language);
        if (!ne_ui_init(&ui, display, language)) {
            printf("FAIL ne_ui_init(%s)\n", code);
            failed++;
            continue;
        }
        for (c = 0; c < sizeof(CASES) / sizeof(CASES[0]); c++) {
            char path[128];
            lv_test_screenshot_result_t result;
            snprintf(path, sizeof(path), GOLDEN_DIR "/%s/%s.png", code, CASES[c].name);
            CASES[c].show(&ui, language);
            result = lv_test_screenshot_compare(path);
            total++;
            if (result == LV_TEST_SCREENSHOT_RESULT_PASSED) {
                printf("ok   %s\n", path);
            } else if (result == LV_TEST_SCREENSHOT_RESULT_NO_REFERENCE_IMAGE) {
                printf("FAIL %s: no golden (run scripts/run_ui_golden.sh --update)\n", path);
                failed++;
            } else {
                printf("FAIL %s: differs from the golden\n", path);
                failed++;
            }
        }
    }
    printf("ui-golden: %d/%d passed\n", total - failed, total);
    return failed == 0 ? 0 : 1;
}
