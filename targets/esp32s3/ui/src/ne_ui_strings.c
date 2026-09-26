/*
 * The UI's own labels, Vietnamese and English (TSK-S4-10).
 *
 * Vietnamese carries full diacritics: fonts/ne_font_*.c are generated from Be
 * Vietnam Pro with the ranges in fonts/ranges.txt, and
 * python/tests/test_ui_assets.py checks every character here is inside them.
 * A string that is agent data does not belong in this file — it is drawn as the
 * agent wrote it.
 */

#include "ne_ui_strings.h"

#include <stddef.h>
#include <string.h>

static const ne_ui_strings_t ne_ui_strings_vi = {
    .language = NE_UI_LANG_VI,
    .code = "vi",

    .boot_self_test = "Tự kiểm tra cổng",
    .boot_running = "Đang chạy…",
    .boot_passed = "Đã đạt",
    .boot_failed = "Thất bại",

    .idle_hint = "Nói từ đánh thức để bắt đầu",
    .net_online = "Mạng: đã kết nối",
    .net_offline = "Mạng: mất kết nối",

    .listening = "Đang nghe",
    .listening_hint = "Nói câu lệnh của bạn",
    .barge_in = "Bị ngắt lời",
    .thinking = "Đang suy nghĩ",
    .speaking = "Đang trả lời",
    .heard = "Đã nghe",
    .reply = "Trả lời",

    .confirm_title = "Cần bạn xác nhận",
    .confirm_yes = "Trả lời “có”",
    .confirm_no = "Trả lời “không”",
    .confirm_fallback = "Nếu bạn không trả lời",

    .verdict_allowed = "Được phép",
    .verdict_blocked = "Bị chặn",
    .action = "Hành động",
    .reason = "Lý do",

    .degraded_title = "Chế độ suy giảm",
    .degraded_stt = "Không có STT đám mây",
    .degraded_tts = "Không có TTS đám mây",
    .degraded_system_two = "Không có System 2",
    .degraded_commands = "Lệnh cục bộ vẫn chạy",

    .sensor_title = "Cảm biến",

    .ota_title = "Cập nhật firmware",
    .ota_checking = "Đang kiểm tra bản mới",
    .ota_downloading = "Đang tải về",
    .ota_verifying = "Đang kiểm chữ ký",
    .ota_rejected = "Bản cập nhật bị từ chối",
    .ota_switching = "Đang chuyển sang bản mới",
    .ota_rolled_back = "Đã quay về bản cũ",
    .progress = "Tiến độ",

    .fatal_title = "Cổng đã dừng",
    .fatal_hint = "Khởi động lại thiết bị",

    .reason_labels =
        {
            [NE_UI_REASON_NONE] = "",
            [NE_UI_REASON_CONDITION_NOT_MET] = "Điều kiện chưa đạt",
            [NE_UI_REASON_CRITERION_UNAVAILABLE] = "Thiếu dữ kiện bắt buộc",
            [NE_UI_REASON_CONFIDENCE_UNAVAILABLE] = "Độ tin cậy dưới ngưỡng",
            [NE_UI_REASON_ARGUMENT_OUT_OF_RANGE] = "Tham số ngoài khoảng cho phép",
            [NE_UI_REASON_GATE_UNREACHABLE] = "Không tới được cổng",
            [NE_UI_REASON_BUDGET_EXCEEDED] = "Cổng vượt ngân sách thời gian",
        },
};

static const ne_ui_strings_t ne_ui_strings_en = {
    .language = NE_UI_LANG_EN,
    .code = "en",

    .boot_self_test = "Gate self-test",
    .boot_running = "Running…",
    .boot_passed = "Passed",
    .boot_failed = "Failed",

    .idle_hint = "Say the wake word to start",
    .net_online = "Network: connected",
    .net_offline = "Network: offline",

    .listening = "Listening",
    .listening_hint = "Say your command",
    .barge_in = "Interrupted",
    .thinking = "Thinking",
    .speaking = "Speaking",
    .heard = "Heard",
    .reply = "Reply",

    .confirm_title = "Confirm the action",
    .confirm_yes = "Answer “yes”",
    .confirm_no = "Answer “no”",
    .confirm_fallback = "If you do not answer",

    .verdict_allowed = "Allowed",
    .verdict_blocked = "Blocked",
    .action = "Action",
    .reason = "Reason",

    .degraded_title = "Degraded mode",
    .degraded_stt = "Cloud STT unavailable",
    .degraded_tts = "Cloud TTS unavailable",
    .degraded_system_two = "System 2 unavailable",
    .degraded_commands = "Local commands still work",

    .sensor_title = "Sensors",

    .ota_title = "Firmware update",
    .ota_checking = "Checking for an update",
    .ota_downloading = "Downloading",
    .ota_verifying = "Verifying the signature",
    .ota_rejected = "Update rejected",
    .ota_switching = "Switching to the new image",
    .ota_rolled_back = "Rolled back",
    .progress = "Progress",

    .fatal_title = "Gate runtime stopped",
    .fatal_hint = "Restart the device",

    .reason_labels =
        {
            [NE_UI_REASON_NONE] = "",
            [NE_UI_REASON_CONDITION_NOT_MET] = "The condition was not met",
            [NE_UI_REASON_CRITERION_UNAVAILABLE] = "A required fact was unavailable",
            [NE_UI_REASON_CONFIDENCE_UNAVAILABLE] = "Confidence below the required floor",
            [NE_UI_REASON_ARGUMENT_OUT_OF_RANGE] = "An argument was outside its allowed range",
            [NE_UI_REASON_GATE_UNREACHABLE] = "The gate could not be reached",
            [NE_UI_REASON_BUDGET_EXCEEDED] = "The gate ran out of its time budget",
        },
};

/* The one list of shipped languages: code, strings and enum value together. */
static const ne_ui_strings_t *const ne_ui_shipped[] = {
    &ne_ui_strings_vi,
    &ne_ui_strings_en,
};

const ne_ui_strings_t *ne_ui_strings(ne_ui_language_t language)
{
    size_t i;
    for (i = 0; i < sizeof(ne_ui_shipped) / sizeof(ne_ui_shipped[0]); i++) {
        if (ne_ui_shipped[i]->language == language) {
            return ne_ui_shipped[i];
        }
    }
    return NULL;
}

const char *ne_ui_language_code(ne_ui_language_t language)
{
    const ne_ui_strings_t *strings = ne_ui_strings(language);
    return strings == NULL ? NULL : strings->code;
}

ne_ui_language_t ne_ui_language_from_code(const char *code)
{
    size_t i;
    if (code == NULL) {
        return NE_UI_LANG_NONE;
    }
    for (i = 0; i < sizeof(ne_ui_shipped) / sizeof(ne_ui_shipped[0]); i++) {
        if (strcmp(code, ne_ui_shipped[i]->code) == 0) {
            return ne_ui_shipped[i]->language;
        }
    }
    return NE_UI_LANG_NONE;
}

bool ne_ui_language_supported(const char *code)
{
    return ne_ui_language_from_code(code) != NE_UI_LANG_NONE;
}

const char *ne_ui_reason_label(ne_ui_language_t language, ne_ui_reason_t reason)
{
    const ne_ui_strings_t *strings = ne_ui_strings(language);
    if (strings == NULL || reason < 0 || reason >= NE_UI_REASON_COUNT) {
        return "";
    }
    return strings->reason_labels[reason];
}
