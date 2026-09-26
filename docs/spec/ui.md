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

**Không chép giao diện vào project sinh ra** (`neuroedge build --target esp32s3`): project chỉ mang
thứ nó gọi, và hôm nay chưa ai gọi giao diện. Chép vào sẽ kéo cả LVGL và phông vào mọi firmware mà
không đổi một hành vi nào, còn `SOURCES` của bộ sinh và `hatch_build.py` phải khớp nhau
(`tests/test_packaging.py`). Việc chép cùng driver màn hình là một bước có chủ đích ở TSK-S4-01.
Thứ firmware mang từ bây giờ là **ngôn ngữ** (§2): `NE_AGENT_LANGUAGE` trong `ne_agent.h`.

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

Hai lỗi **chặn build**, ở hai tầng khác nhau:

- **Dạng và xung đột — mọi target.** `[agent] language` phải là ISO-639-1 đúng **hai** chữ thường
  (`vi`, `en`); `vie`, `VI` bị từ chối. `[agent] language` và `[stt] language` cùng có mà khác nhau
  thì `load_agent_manifest` dừng — kể cả `sim`/`linux`: một vết ghi của phiên mà bộ nhận dạng nghe
  một thứ tiếng còn màn hình hiện thứ khác không phải vết ghi của cùng agent. Thông báo in giá trị
  nguyên văn (`!r`).
- **Bộ chữ và glyph — chỉ nơi có giao diện.** `--target esp32s3` từ chối mã mà `UI_LANGUAGES`
  hôm nay (`["vi", "en"]`) không có (kể cả `[stt] language = "ja"`): không bảng chữ **hoặc** không
  glyph. `sim`/`linux` không có màn hình nên không kiểm phần này.

Hiện thực: `python/neuroedge/engine/compiler.py` (`load_agent_manifest`, `resolve_agent_language`)
và `python/neuroedge/engine/firmware.py` (`UI_LANGUAGES`, `ui_language`). Firmware sinh ra mang kết
quả dưới dạng `#define NE_AGENT_LANGUAGE "…"` trong `ne_agent.h`.
`python/tests/test_ui_language.py` kiểm từng nhánh, từng lỗi và cả `sim`/`linux`;
`python/tests/test_ui_assets.py` giữ `UI_LANGUAGES`, bảng chữ và **cmap của phông sinh ra** khớp nhau.

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

## 4. Chữ dài và chữ bẩn không bao giờ tràn panel

Chữ của agent là dữ liệu không tin cậy — một model, một người, một thông điệp gate viết ra. Bốn
luật, hiện thực ở `ne_ui_text.c` và `ne_ui.c`, đều tất định:

1. **Cắt theo ngân sách của ô.** Mặc định `NE_UI_TEXT_MAX` (320) byte; vài ô ngắn hơn (tên action
   trên chip 20, tên cảm biến 64, giá trị 32, đơn vị 12, dải 20). Cắt tại ranh giới điểm mã UTF-8,
   thêm `…` khi bị cắt — không bao giờ cắt giữa một ký tự. Chip còn có `max_width` làm lưới an toàn
   cho glyph rộng.
2. **Byte không hợp lệ thành `?`.** Thiếu byte nối, dạng overlong, surrogate, trên U+10FFFF: mỗi
   byte hỏng một `?`. Hàm không bao giờ đọc quá NUL đầu tiên, kể cả khi chuỗi kết thúc giữa một
   chuỗi nhiều byte. `python/tests/test_ui_text.py` build driver C với ASan+UBSan và chạy vài nghìn
   chuỗi byte ngẫu nhiên cùng các ca thủ công (đuôi cụt, `\xF0`, overlong, surrogate, NUL giữa).
3. **Nhãn một dòng giữ đúng một dòng.** Xuống dòng và ký tự điều khiển trong dữ liệu thành khoảng
   trắng (`ne_ui_text_single_line`), nhãn nhận `lv_label_set_max_lines(…, 1)`, chiều cao đúng một
   dòng và `LV_LABEL_LONG_MODE_DOTS`. Không có bước này, LVGL 9.6 **tự xuống dòng** (DOTS chỉ cắt
   khi chiều cao cố định) và chữ của agent đè lên nhãn bên dưới.
4. **Chữ nhiều dòng chỉ nằm trong hộp cuộn kích thước cố định** (thông điệp hỏi, câu trả lời, bản
   chép lời, lý do và chi tiết verdict, lý do boot/fatal, chi tiết OTA). Hộp cắt phần thừa và cuộn
   được lúc chạy, nhưng không bao giờ cao lên đè lên widget khác. Số phần tử vẽ ra có trần:
   `NE_UI_MAX_READINGS` và `NE_UI_MAX_COMMANDS` — mảng dài hơn vẫn an toàn.

Chữ nên tới giao diện ở dạng **NFC**: tiếng Việt NFD (ký tự tổ hợp rời) không có glyph trong phông
và vẽ thành ô vuông; chuẩn hoá trước khi gọi `ne_ui_show_*` là việc của bên gọi.

## 5. Phông chữ

Be Vietnam Pro (OFL-1.1 — `LICENSES/OFL-1.1.txt`, `NOTICE` mục A.5) đủ dấu tiếng Việt; phông dựng
sẵn của Montserrat trong LVGL thì không. Ba cỡ, dùng trong màn hình: **12** (nhãn phụ), **16**
(thân), **22** (tiêu đề, số đọc).

`scripts/gen_ui_fonts.sh` tải hai weight nguồn (Regular, SemiBold) theo URL + SHA-256, chạy
`lv_font_conv@1.5.3` qua `npx`, và ghi `targets/esp32s3/ui/fonts/ne_font_{12,16,22}.c`. Mỗi tệp sinh
ra mang ghi nhận tại chỗ: tệp nguồn, SHA-256, giấy phép (CONTRIBUTING.md §4 nghĩa vụ 3). Các dải
glyph nằm ở `fonts/ranges.txt` — một nơi, gồm cả `₫` (U+20AB) để một chuỗi giá sau này không phải
sinh lại phông; `test_ui_assets.py` kiểm mọi ký tự trong hai bảng chữ C nằm trong **cmap của từng
phông sinh ra**, không chỉ trong `ranges.txt`.

Phông bị nén RLE: thiếu `LV_USE_FONT_COMPRESSED 1` thì LVGL chỉ ghi log rồi vẽ glyph trắng, nên
`fonts/ne_fonts.h` có `#error` chặn build. Mỗi tệp sinh ra là một **Modified Version** theo OFL 1.1
(không phải bản thân font software); Be Vietnam Pro **không** khai Reserved Font Name nên tên
`ne_font_*` hợp lệ. Ảnh firmware link phông này là phân phối font software: ảnh đó phải mang dòng
copyright và văn bản OFL (`LICENSES/OFL-1.1.txt`) — chi tiết ở `NOTICE` mục A.5.

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
