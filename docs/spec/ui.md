# Giao diện thiết bị `esp32s3` — màn hình, ngôn ngữ, ảnh golden

**Trạng thái:** đặc tả quy phạm cho TSK-S4-10 (FR-HAL-01, FR-CI-05, Q-21). Mã:
[`targets/esp32s3/ui/`](../../targets/esp32s3/ui/); chạy: `scripts/run_ui_golden.sh`. Ô `display` của
`esp32s3` trong ma trận phủ là [`simulation_coverage.md`](simulation_coverage.md) §2.

Hai câu tóm cả tài liệu: **giao diện nói ngôn ngữ của agent** (§2), và **chữ của agent là dữ liệu,
chỉ chữ của giao diện mới được dịch** (§3).

## 1. Phạm vi

Panel 320×240 RGB565 (ST7789) của Box-3 (`boards/esp32s3-box-3.toml`). Giao diện là C99 thuần trên
API LVGL v9.6.0 (MIT, `NOTICE` mục C): không header ESP-IDF, nên cùng mã đó build trên host để so
ảnh golden mỗi PR (job `ui-golden`, `.github/workflows/ci-sim-linux.yml`) và link nguyên vẹn vào
firmware khi có driver.

**Ngoài phạm vi:** driver SPI của màn hình và cảm ứng (TSK-S4-01), và việc nối giao diện vào task
firmware đang chạy. Component `targets/esp32s3/ui/CMakeLists.txt` đã đăng ký sẵn cho lúc đó; hôm
nay firmware không build thư mục này.

Vẽ **tất định**: không đọc đồng hồ, không ngẫu nhiên, không tự chạy hoạt ảnh (mọi lời gọi có tham
số hoạt ảnh đều nhận `LV_ANIM_OFF`), không tự cuộn. Cùng một struct trạng thái cho ra cùng điểm ảnh —
đó là điều làm ảnh golden có nghĩa.

## 2. Ngôn ngữ — quy tắc duy nhất

Mỗi agent một ngôn ngữ, chọn theo thứ tự:

| Bước | Nguồn | Kết quả |
|:---:|:---|:---|
| 1 | `[agent] language` trong `agent.toml` (ISO-639-1) | dùng nó |
| 2 | không có ⇒ `[stt] language` | dùng nó |
| 3 | cả hai đều không có | `"vi"` |

Hai trường hợp **build dừng**, không đoán:

- **Hai nguồn khác nhau** (`[agent] language` và `[stt] language` cùng có, khác giá trị): giao diện
  và bộ nhận dạng sẽ nói hai thứ tiếng; thông báo nêu cả hai giá trị và cách sửa.
- **Giao diện không có tiếng đó**: `UI_LANGUAGES` hôm nay là `["vi", "en"]`. Một mã khác (kể cả
  `[stt] language = "ja"`) bị từ chối vì không có bảng chữ **hoặc** không có glyph.

Hiện thực: `python/neuroedge/engine/compiler.py` (`load_agent_manifest` kiểm dạng ISO-639-1 của
`[agent] language`) và `python/neuroedge/engine/firmware.py` (`UI_LANGUAGES`, `ui_language`).
Firmware sinh ra mang kết quả dưới dạng `#define NE_AGENT_LANGUAGE "…"` trong `ne_agent.h`.
`python/tests/test_ui_language.py` kiểm từng nhánh và từng lỗi; `python/tests/test_ui_assets.py`
giữ `UI_LANGUAGES` khớp bảng chữ C.

**Phía C, fail closed.** `ne_ui_language_from_code("…")` trả `NE_UI_LANG_NONE` cho mã lạ, và
`ne_ui_init` trả `false` — không màn hình nào được vẽ — nếu ngôn ngữ không có bảng chữ. Mã hợp lệ:
`ne_ui_language_code`, `ne_ui_language_supported`.

**Thêm một ngôn ngữ** (việc của một PR thường): thêm `ne_ui_strings_<mã>` vào
`targets/esp32s3/ui/src/ne_ui_strings.c`, thêm mã vào `UI_LANGUAGES`, thêm dải glyph cần thiết vào
`targets/esp32s3/ui/fonts/ranges.txt`, chạy `bash scripts/gen_ui_fonts.sh`, rồi
`bash scripts/run_ui_golden.sh --update`. `test_ui_assets.py` sẽ đỏ nếu thiếu một trong các bước.

## 3. Màn hình

Mỗi màn hình một hàm `ne_ui_show_*` trong `ne_ui.h`; struct trạng thái đi kèm là dữ liệu (§ dưới).
Chữ của agent — tên action, thông điệp `on_block`, câu trả lời, số đọc — vẽ **nguyên văn**, không
dịch. Nhãn của giao diện nằm trong `ne_ui_strings.c`, mỗi ngôn ngữ một bảng.

| Hàm | Trạng thái runtime | Vẽ gì |
|:---|:---|:---|
| `ne_ui_show_boot` | self-test gate lúc boot (`main/gate_selftest.c`) | `NE_UI_BOOT_RUNNING` (thanh chạy) · `_PASSED` · `_FAILED` kèm lý do (dữ liệu) |
| `ne_ui_show_idle` | `VoiceState.IDLE` (`perception/voice_fsm.py`) | tên agent, cách bắt đầu nói, mạng lên/xuống |
| `ne_ui_show_voice` | `LISTENING` | mức vào 0..100 |
| `ne_ui_show_voice` | `BARGE_IN` | như `LISTENING` với cờ `interrupted` |
| `ne_ui_show_voice` | `THINKING` | bản chép lời đã nghe |
| `ne_ui_show_voice` | `SPEAKING` | bản chép lời + câu trả lời (wrap, cuộn được) |
| `ne_ui_show_confirm` | `on_block.action = ask` (RFC-0006) | action, thông điệp hỏi (dữ liệu), `fallback_action`, cách trả lời có/không |
| `ne_ui_show_verdict` | phán quyết gate | ALLOW / BLOCK, action, **mã lý do** (bảng dưới), chi tiết (dữ liệu) |
| `ne_ui_show_degraded` | STT/TTS đám mây hoặc System 2 mất | phần nào mất, lệnh cục bộ còn chạy (dữ liệu) |
| `ne_ui_show_sensor` | `sensor.read` | tên, giá trị, đơn vị, dải (dữ liệu) |
| `ne_ui_show_ota` | cập nhật firmware (task OTA) | 6 pha, tiến độ, chi tiết (dữ liệu) |
| `ne_ui_show_fatal` | cổng dừng | lý do (dữ liệu) |

Sáu mã lý do của BLOCK — đúng bảng `ne_reason` của walker (`ne_walker.h`) và `firmware.REASONS`:
`condition_not_met`, `criterion_unavailable`, `confidence_unavailable`, `argument_out_of_range`,
`gate_unreachable`, `budget_exceeded`. Nhãn của chúng ở `ne_ui_strings.c`; `test_ui_assets.py` giữ
enum C và bảng Python khớp nhau. `NE_UI_REASON_NONE` là của ALLOW.

Hàm nhận con trỏ struct; trường `const char *` là dữ liệu, `NULL` vẽ như dòng rỗng. Màn hình không
giữ con trỏ sau khi hàm trả về (LVGL sao chép chữ), nên bên gọi có thể dùng dữ liệu tạm.

## 4. Chữ dài không bao giờ tràn panel

Ba lớp, đều tất định:

1. Chữ dữ liệu dài bị cắt còn `NE_UI_TEXT_MAX` (320) **byte**, cắt tại ranh giới điểm mã UTF-8 và
   thêm `…` khi bị cắt — không bao giờ cắt giữa một ký tự.
2. Nhãn nhiều dòng dùng `LV_LABEL_LONG_MODE_WRAP` với bề rộng cố định; nhãn một dòng dùng
   `LV_LABEL_LONG_MODE_DOTS` (dấu ba chấm của LVGL).
3. Vùng chữ cuộn được (câu trả lời, danh sách lệnh) là container có kích thước cố định; LVGL cắt
   phần thừa — không có đường nào để chữ vẽ ra ngoài panel.

## 5. Phông chữ

Be Vietnam Pro (OFL-1.1 — `LICENSES/OFL-1.1.txt`, `NOTICE` mục A.5) đủ dấu tiếng Việt; phông dựng
sẵn của Montserrat trong LVGL thì không. Ba cỡ, dùng trong màn hình: **12** (nhãn phụ), **16**
(thân), **22** (tiêu đề, số đọc).

`scripts/gen_ui_fonts.sh` tải hai weight nguồn (Regular, SemiBold) theo URL + SHA-256, chạy
`lv_font_conv@1.5.3` qua `npx`, và ghi `targets/esp32s3/ui/fonts/ne_font_{12,16,22}.c`. Mỗi tệp sinh
ra mang ghi nhận tại chỗ: tệp nguồn, SHA-256, giấy phép (CONTRIBUTING.md §4 nghĩa vụ 3). Các dải
glyph nằm ở `fonts/ranges.txt` — một nơi; `test_ui_assets.py` kiểm mọi ký tự trong hai bảng chữ C
nằm trong đó. Đổi bảng chữ hoặc cỡ chữ thì chạy lại script và commit tệp sinh ra.

## 6. Ảnh golden

Host harness `targets/esp32s3/ui/host/` fetch LVGL **v9.6.0** ghim URL + SHA-256 trong CMake; tải
lệch ⇒ CMake dừng. Với mỗi **màn hình × ngôn ngữ × trạng thái đại diện** (ma trận trong
`host/main.c`), harness dựng `lv_test_display` 320×240 rồi so bằng `lv_test_screenshot_compare` với
`targets/esp32s3/ui/golden/<mã>/<ca>.png`.

```bash
bash scripts/run_ui_golden.sh            # kiểm; KHÔNG bao giờ ghi golden
bash scripts/run_ui_golden.sh --update   # dựng lại golden rồi kiểm lại
```

Chế độ kiểm sao golden vào thư mục build rồi chạy ở đó: khác biệt để lại `<ca>_err.png` trong thư
mục build, còn golden đã commit không bị ghi. Thiếu golden, khác một điểm ảnh, harness không dựng
được, hoặc một phép kiểm ngôn ngữ/lý do sai ⇒ thoát khác 0. CI chạy đúng script đó trong container
`espressif/idf:v5.4` — cùng toolchain đã sinh golden (cmake 3.30, gcc 13) — nên nó kiểm byte đã ghim,
không phải một bộ vẽ thứ hai.

## 7. Điều tài liệu này không hứa

- Chân SPI thật, cảm ứng, và giao diện nằm trong task firmware: TSK-S4-01.
- Cập nhật firmware thật: màn hình OTA chỉ vẽ trạng thái; mã OTA là task khác.
- Hoạt ảnh, hiệu ứng chuyển màn hình: cố ý không có (tất định).
- Chữ tiếng Việt ngoài các dải glyph ở `ranges.txt`: thêm dải rồi sinh lại phông (§5).
