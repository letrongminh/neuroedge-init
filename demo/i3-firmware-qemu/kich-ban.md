Chạy lại lần cuối: 2026-09-29, macOS (Apple Silicon), Docker `espressif/idf:v5.4`, `main` `6a69626` — `ui`, `boot`, `agent`, `ota` đều kết thúc bằng ✓.

# Kịch bản demo firmware không cần bo mạch (I3 + OTA)

> **Mục tiêu:** Giúp người trình bày (presenter) có thể demo đầy đủ phía vi điều khiển ESP32-S3 của NeuroEdge mà không cần cắm bo mạch vật lý: từ giao diện thiết bị (LVGL golden images), firmware boot trên Espressif QEMU và tự kiểm tra gate (gate self-test), thiết bị replay các vết ghi chuẩn mực với cùng phán quyết như trên máy tính (`verify --targets esp32s3`), đóng gói agent của chính người dùng thành firmware, cho đến cập nhật OTA phân vùng A/B có ký số và tự động rollback khi lỗi — toàn bộ diễn ra trong Docker với cùng image và các bước chuẩn tắc như CI.

---

## 0. Chuẩn bị

Trước buổi demo, người trình bày chuẩn bị máy tính (macOS Apple Silicon hoặc Linux):

1. **Docker Desktop đang chạy:** Đảm bảo daemon Docker hoạt động bình thường (`docker info`).
2. **Kéo sẵn ảnh Docker ESP-IDF:** Chạy lệnh sau một lần duy nhất trước buổi demo:
   ```bash
   docker pull espressif/idf:v5.4
   ```
3. **Thời gian chạy:**
   - Đo ngày 2026-09-29: lần đầu `ui` + `boot` mất khoảng 3,5 phút (biên dịch ESP-IDF từ đầu). Các lần sau nhanh hơn nhờ volume ccache `neuroedge-ccache` và venv `neuroedge-demo-venv`. `ota` build bốn ảnh firmware nên lâu nhất — **chạy trước buổi demo**, lúc trình bày chỉ mở log.
   - Dòng `E (…) octal_psram: PSRAM ID read error` trong log là bình thường: QEMU không mô phỏng PSRAM.
4. **Nguyên tắc môi trường:**
   - Script chạy từ thư mục gốc của kho: `./demo/i3-firmware-qemu/run.sh <lệnh>`.
   - Toàn bộ các bước biên dịch, mô phỏng QEMU và kiểm tra chạy trong container `espressif/idf:v5.4` không có quyền `--privileged`.
   - Không ghi tệp ra ngoài các đường dẫn được `.gitignore` của kho và các Docker volume đã cấu hình.

---

## 1. Màn 1 — Giao diện trên thiết bị, tiếng Việt

### Nói
"NeuroEdge hỗ trợ giao diện đồ họa trực tiếp trên màn hình 320×240 của thiết bị bằng tiếng Việt chuẩn có dấu (phông Be Vietnam Pro) và tiếng Anh tùy theo cấu hình của agent. Toàn bộ mã giao diện được viết bằng C99 thuần túy trên thư viện đồ họa mở LVGL v9.6.0. Cùng một mã nguồn C này vừa được biên dịch vào firmware chạy trên chip thật, vừa được biên dịch trên máy tính để so sánh ảnh golden mỗi lần có Pull Request (job CI `ui-golden`). Nhờ đó, chúng ta kiểm soát từng điểm ảnh (pixel-for-pixel) của 66 trạng thái màn hình, đảm bảo chữ của agent dù dài hay có ký tự đặc biệt cũng không bao giờ làm tràn panel hay vỡ bố cục."

### Gõ
```bash
./demo/i3-firmware-qemu/run.sh ui
```

### Thấy
- Công cụ so sánh 66 ảnh màn hình (33 ảnh tiếng Việt + 33 ảnh tiếng Anh) qua `scripts/run_ui_golden.sh` trong container `espressif/idf:v5.4`.
- Thông báo đối chiếu thành công: `ui-golden: 66/66 passed` rồi `ui-golden: every screen matches its golden`.
- Dòng kết thúc:
  ```text
  ✓ ui: 66 ảnh golden khớp hoàn toàn (vi và en)
  ```
- Bảng minh họa 8 màn hình tiêu biểu bằng tiếng Việt:

| Màn hình | Tên tệp | Ý nghĩa | Ảnh minh họa |
|:---|:---|:---|:---:|
| Khởi động đạt | `boot_passed.png` | Self-test gate đạt lúc boot | ![`boot_passed`](../../targets/esp32s3/ui/golden/vi/boot_passed.png) |
| Lắng nghe | `voice_listening.png` | Mức âm thanh đầu vào | ![`voice_listening`](../../targets/esp32s3/ui/golden/vi/voice_listening.png) |
| Phản hồi giọng nói | `voice_speaking.png` | Bản chép lời và câu trả lời | ![`voice_speaking`](../../targets/esp32s3/ui/golden/vi/voice_speaking.png) |
| Hỏi xác nhận | `confirm.png` | `on_block: ask` theo RFC-0006 | ![`confirm`](../../targets/esp32s3/ui/golden/vi/confirm.png) |
| Cho phép (ALLOW) | `verdict_allow.png` | Gate duyệt lệnh thành công | ![`verdict_allow`](../../targets/esp32s3/ui/golden/vi/verdict_allow.png) |
| Chặn lệnh (BLOCK) | `verdict_block_condition_not_met.png` | Gate chặn kèm mã lý do | ![`verdict_block_condition_not_met`](../../targets/esp32s3/ui/golden/vi/verdict_block_condition_not_met.png) |
| Cảm biến | `sensor.png` | Đọc nhiệt độ, độ ẩm, tiếp điểm cửa | ![`sensor`](../../targets/esp32s3/ui/golden/vi/sensor.png) |
| Xác minh OTA | `ota_verifying.png` | Đang kiểm tra chữ ký RSA-3072 | ![`ota_verifying`](../../targets/esp32s3/ui/golden/vi/ota_verifying.png) |

*(Xem toàn bộ 33 ảnh tiếng Việt tại thư mục [`targets/esp32s3/ui/golden/vi/`](../../targets/esp32s3/ui/golden/vi/) và 33 ảnh tiếng Anh tại [`targets/esp32s3/ui/golden/en/`](../../targets/esp32s3/ui/golden/en/)).*

### Điểm nhấn
- **Giao diện nói ngôn ngữ của agent:** Ngôn ngữ được chọn tự động từ `[agent] language` trong `agent.toml` (mặc định `"vi"` nếu không khai báo), chi tiết tại [`docs/spec/ui.md`](../../docs/spec/ui.md) §2.
- **Tất định tuyệt đối:** Không hiệu ứng ngẫu nhiên, không cuộn tự do khi vẽ ảnh mẫu. Chữ dài luôn được cắt ở ranh giới điểm mã UTF-8 kèm dấu `…`, không bao giờ đè lên nhãn khác.

---

## 2. Màn 2 — Con chip boot và tự kiểm gate

### Nói
"Bây giờ chúng ta khởi động firmware cơ sở trên trình giả lập Espressif QEMU. Lúc khởi động, chip chạy một thủ tục self-test gate: walker C và sổ token dùng một lần trên chip sẽ kiểm tra lại toàn bộ cây quyết định NETR lưu trong flash và các phép thử của agent. Nếu phán quyết của chip sai lệch dù chỉ một điều kiện so với engine phía host, firmware sẽ lập tức báo `NE_SELFTEST FAIL` và dừng hoạt động (fail-closed). Sau khi self-test đạt, con chip phát lại (replay) 3 vết ghi chuẩn mực của hệ thống ra UART. Lệnh `neuroedge verify --targets esp32s3` đọc luồng UART này và chứng minh phán quyết của chip trùng khớp 100% với golden reference."

### Gõ
```bash
./demo/i3-firmware-qemu/run.sh boot
```

### Thấy
Người trình bày chỉ cho người xem các mốc in ra ở cột 0 trên log UART:
1. Dòng tự kiểm tra gate thành công:
   ```text
   NE_SELFTEST PASS walker=26 token=11
   ```
2. Các dòng phát lại vết ghi chuẩn mực dưới dạng cấu trúc JSON `NE1 `:
   ```text
   NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu",…
   ```
3. Dòng thông báo hoàn tất các phiên vết ghi:
   ```text
   NE_TRACE DONE sessions=4
   ```
4. Kết quả xác minh tương đương target của CLI:
   ```text
   ✓ VALID /tmp/demo-boot-traces/sess_…00.json — 78 event(s), target esp32s3
   │ Passed: all 3 gate(s) resolve, all 3 canonical trace(s) validate, every tool │
   ```
5. Dòng kết thúc:
   ```text
   ✓ boot: firmware boot thành công trên QEMU, self-test đạt và verify khớp 3 vết ghi chuẩn mực
   ```

### Điểm nhấn
- **Walker C duyệt cây NETR:** Không dùng bộ thông dịch CEL nặng nề trên vi điều khiển; cây quyết định nhị phân được duyệt nhanh gọn bằng C99 thuần (bất biến 5 trong [`CHANGELOG.md`](../../CHANGELOG.md) §3.3).
- **Target Equivalence:** Phán quyết của chip ảo trên QEMU tương đương hoàn toàn với engine trên máy chủ/máy trạm.

---

## 3. Màn 3 — Agent của chính bạn thành firmware

### Nói
"Một lập trình viên không chuyên về nhúng hoàn toàn có thể đưa agent của mình lên chip ESP32-S3. Chỉ bằng một lệnh `neuroedge build --target esp32s3 --board esp32s3-box-3`, hệ thống sẽ tự động chuyển đổi khai báo agent thành một dự án ESP-IDF tiêu chuẩn: biên dịch các gate thành cây NETR, sinh component `ne_agent.c` chứa các kiểm tra self-test kèm phán quyết đã tính trước, và liên kết mã nguồn firmware. Bây giờ chúng ta sẽ tạo một agent mới từ đầu, sinh firmware, boot trên QEMU và chứng kiến gate của chính agent đó vượt qua self-test trên chip."

### Gõ
```bash
./demo/i3-firmware-qemu/run.sh agent
```

### Thấy
- Các giai đoạn được thực hiện tự động trong scratch directory:
  1. Tạo agent: `neuroedge new demo-agent`
  2. Sinh mã firmware: `neuroedge build --target esp32s3 --board esp32s3-box-3`
  3. Biên dịch dự án ESP-IDF sinh ra với cấu hình `sdkconfig.qemu`
  4. Boot firmware của agent trên QEMU
  5. Đọc dòng phán quyết self-test ở cột 0:
     ```text
     NE_SELFTEST PASS walker=8 token=6
     ```
  6. Ghi vết `neuroedge record` và thẩm định phiên `neuroedge trace validate`
- Dòng kết thúc:
  ```text
  ✓ agent: agent demo-agent được sinh firmware, boot trên QEMU và vượt qua self-test
  ```

### Điểm nhấn
- **Cùng một agent, đa nền tảng:** Cùng một mã nguồn agent có thể chạy mô phỏng (`sim`), chạy trên Linux (`linux`), hoặc sinh thành firmware C (`esp32s3`).
- **Từ chối lúc build nếu không tương thích:** Nếu agent đòi hỏi chân GPIO hoặc năng lực mà bo mạch không hỗ trợ (FR-HAL-04), lệnh `build` sẽ từ chối ngay với mã lỗi 1 và không ghi bất kỳ tệp nào ra đĩa ([`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §3).

---

## 4. Màn 4 — Cập nhật OTA có ký, tự quay về khi hỏng

### Nói
"Cơ chế cập nhật qua mạng (OTA) của NeuroEdge được xây dựng theo tiêu chuẩn an toàn công nghiệp: hai phân vùng A/B, bắt buộc xác minh chữ ký RSA-3072 trước khi cho phép chuyển khe khởi động, và tự động rollback nếu bản cập nhật bị lỗi hoặc trượt self-test gate. Không cần dịch vụ đám mây trung gian: thiết bị kéo bản cập nhật trực tiếp từ một HTTP endpoint. Trình giả lập QEMU sẽ thực thi toàn bộ kịch bản 7 pha (a đến g) để chứng minh mọi tình huống an toàn."

### Gõ
```bash
./demo/i3-firmware-qemu/run.sh ota
```

### Thấy
Quá trình chạy kịch bản `scripts/qemu_ota.sh` trải qua đủ 7 pha:
- **Pha a:** Bản factory 0.1.0 khởi động, self-test đạt, máy chủ đang chạy cùng phiên bản nên bỏ qua (`NE_OTA SKIP reason=same_version version=0.1.0`) — không bao giờ mất khe đang chạy.
- **Pha b:** Bản 0.2.0 ký đúng khóa được tải về, xác minh chữ ký, chuyển khe khởi động (`SWITCH partition=ota_0`) và được đánh dấu hợp lệ (`NE_OTA VALID`) sau khi vượt qua self-test của chính nó (mốc nước cao NVS nâng lên 0.2.0).
- **Pha c:** Bản cập nhật ký bằng khóa lạ (khác với khóa của bản đang chạy) bị từ chối trước khi khởi động (`NE_OTA REJECTED reason=signature`): không đổi khe, không reboot, thiết bị ở lại bản 0.2.0 và khe vừa ghi bị xóa sector đầu (`NE_OTA ERASED`).
- **Pha d:** Bản ký đúng nhưng bị lỗi hỏng (resets/crashes trước khi kịp xác nhận) (`NE_OTA TEST BOOTLOOP`) được bootloader tự động quay về (`NE_OTA ROLLBACK from=ota_1 to=ota_0`); thiết bị khởi động lại vào 0.2.0 và không tải lại bản đã hỏng (`NE_OTA SKIP reason=rolled_back version=0.3.0`).
- **Pha e:** Bản cập nhật có gate self-test thất bại tự đánh dấu hỏng (`NE_OTA INVALID partition=ota_1`) và reboot; bootloader tự quay về bản trước (`NE_OTA ROLLBACK from=ota_1 to=ota_0`), rồi bỏ qua bản đó (`NE_OTA SKIP reason=rolled_back version=0.3.1`).
- **Pha f:** Bản cập nhật không có chữ ký (không có signature block) bị từ chối (`NE_OTA REJECTED reason=signature`) và khe vừa ghi bị xóa (`NE_OTA ERASED`).
- **Pha g:** Bản ký đúng nhưng có số phiên bản thấp hơn (0.1.0 so với mốc 0.2.0) bị từ chối vì hạ cấp (`NE_OTA SKIP reason=downgrade version=0.1.0`) bởi mốc nước cao trong NVS.
- Tổng kết của script: `OTA on QEMU: all phases passed`.
- Dòng kết thúc:
  ```text
  ✓ ota: toàn bộ các pha cập nhật OTA và rollback (a–g) đạt yêu cầu trên QEMU
  ```

### Điểm nhấn
- **Self-test trước khi Valid:** Bản mới tải về chỉ được coi là hợp lệ sau khi tự kiểm tra gate thành công trên chip.
- **Không bao giờ bị 'cục gạch' (bricked):** Mọi sự cố từ sai khóa, hỏng mã nguồn cho tới trượt self-test đều được bootloader và chính sách phân vùng tự động khôi phục về khe hoạt động gần nhất.

---

## 5. Những điều không được nói trong demo

Khi trình bày với đối tác, khách hàng hoặc trong phỏng vấn nhu cầu, người trình bày cần tuân thủ nghiêm ngặt danh mục "Không được nói" tại [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../../docs/business/cong-nhu-cau-2026-10-25/demo.md) §0.1 và danh mục giới hạn tại [`CHANGELOG.md`](../../CHANGELOG.md) §3.7. Cụ thể, không được nói hoặc khẳng định ba điều sau đây:

1. **Không nói là chân GPIO đã điều khiển thiết bị thật:** Hiện tại HAL trên vi điều khiển là TSK-S4-01; mô phỏng QEMU chỉ chứng minh logic phân vùng flash, walker C, sổ token và chữ ký (Nguồn: [`docs/spec/simulation_coverage.md`](../../docs/spec/simulation_coverage.md) §4, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §1).
2. **Không nói là Box-3 đã kết nối Wi-Fi thật ngoài đời:** QEMU kết nối mạng bằng card mạng ảo `open_eth`; trên bo mạch ESP32-S3-BOX-3 thật, Wi-Fi mới dừng ở mức khởi tạo giao diện STA mà chưa gọi kết nối và chưa có provisioning cấu hình mạng (Nguồn: [`docs/spec/simulation_coverage.md`](../../docs/spec/simulation_coverage.md) §4.1, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §6.5, `TODOS.md` #50).
3. **Không nói là đã có Secure Boot phần cứng hay eFuse anti-rollback:** Khóa công khai xác minh nằm trong ảnh firmware đang chạy (TSK-S6-05); người có cáp nạp trực tiếp vẫn có thể thay firmware hoặc đổi khóa; việc chặn hạ cấp hiện tại là bằng phần mềm dựa vào mốc nước cao trong NVS (Nguồn: TSK-S6-05, [`docs/user/nap-firmware.md`](../../docs/user/nap-firmware.md) §1, §6).
