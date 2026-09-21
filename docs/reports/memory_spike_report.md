# Báo cáo Spike khả thi bộ nhớ — ESP32-S3-BOX-3

| | |
|:---|:---|
| **Mã task** | TSK-S1-10 (đo) · TSK-S2-10 (kết luận phạm vi) |
| **Yêu cầu** | NFR-RES-01, NFR-RES-02 |
| **Quyết định đối chiếu** | Q-3 |
| **Rủi ro liên quan** | R-1 (phạm vi Khối 1b vượt hạn do tối ưu bộ nhớ) — mức **Cao** |
| **Người thực hiện** | V2 — Kỹ sư nhúng |
| **Trạng thái** | 🟡 **Khung đo đã xong · CHƯA CÓ SỐ ĐO THỰC** |
| **Cập nhật lần cuối** | 2026-09-21 |

> **Trạng thái trung thực của báo cáo này.** Khung đo (`targets/esp32s3/main/memory_probe.c`)
> đã viết xong và đã nối vào `app_main`. Chưa có một con số đo thực nào, vì
> chưa chạy trên bo mạch vật lý. Roadmap §4.1 yêu cầu kết quả spike là **một
> con số, không phải một nhận định** — nên mọi ô "Giá trị đo" dưới đây để
> trống, và `neuroedge_memory_meets_q3_budget()` trả về `false` /
> `INCONCLUSIVE` cho tới khi checkpoint `audio_ready` được lấy thật.

---

## 1. Ngưỡng đối chiếu (đã chốt tại Q-3)

| Chỉ tiêu | Ngưỡng Q-3 | Giá trị đo | Kết luận |
|:---|:---:|:---:|:---:|
| SRAM nội cho ứng dụng | **≥ 120 KB** (122 880 B) | *chưa đo* | ⏳ |
| PSRAM cho ứng dụng | **≥ 2 MB** (2 097 152 B) | *chưa đo* | ⏳ |
| Dung lượng firmware | **≤ 3,5 MB** (3 670 016 B) | *chưa đo* | ⏳ |

Ba ngưỡng này được ghim thành hằng số trong
[`targets/esp32s3/main/memory_probe.h`](../../targets/esp32s3/main/memory_probe.h)
(`NEUROEDGE_Q3_*`). **Không sửa hằng số để một lần chạy đạt ngưỡng** — đổi
ngưỡng là quyết định roadmap, không phải thay đổi mã nguồn.

Ngưỡng firmware 3,5 MB xuất phát từ bảng phân vùng: flash 16 MB chia hai khe
A/B mỗi khe `0x380000` = 3 670 016 B (xem
[`targets/esp32s3/partitions.csv`](../../targets/esp32s3/partitions.csv)).
Vượt ngưỡng này thì OTA A/B không nạp được, đây là ràng buộc cứng chứ không
phải mục tiêu tối ưu.

## 2. Các mốc đo (checkpoint)

Bộ đo lấy mẫu tại bốn mốc, theo đúng thứ tự. Mỗi mốc là một thời điểm mà một
phân hệ *không thể loại bỏ* đã chiếm bộ nhớ; phần còn lại mới là phần runtime
tác tử thực sự được dùng.

| # | Checkpoint | Nội dung đã nạp | SRAM nội còn trống | PSRAM còn trống |
|:---:|:---|:---|:---:|:---:|
| 1 | `boot` | Chỉ FreeRTOS + IDF | *chưa đo* | *chưa đo* |
| 2 | `nvs_ready` | + NVS (cấp phép, thông tin đăng nhập) | *chưa đo* | *chưa đo* |
| 3 | `network_ready` | + ngăn xếp TCP/IP và Wi-Fi | *chưa đo* | *chưa đo* |
| 4 | `audio_ready` | **+ AEC + VAD + Opus + ring buffer** | *chưa đo* | *chưa đo* |

**Mốc 4 là mốc quyết định.** Ba mốc đầu chỉ cho biết sàn; đối chiếu Q-3 bằng
số của mốc 1–3 sẽ trả lời một câu hỏi khác và cho một kết quả trông có vẻ an
tâm — đúng kiểu thất bại mà R-1 cảnh báo. Vì vậy hàm đối chiếu báo
`INCONCLUSIVE` khi mốc 4 chưa được lấy.

## 3. Việc còn lại để có số đo

| # | Việc | Phụ thuộc |
|:---:|:---|:---|
| 1 | Có bo mạch ESP32-S3-BOX-3 vật lý | Đặt hàng — chưa xong |
| 2 | Vendoring `esp-sr` (AEC/AFE + VAD) và `opus`, kèm rà soát giấy phép §3.9 | Ma trận giấy phép (`NOTICE`) |
| 3 | Nạp AEC 16 kHz 2 kênh (ES7210), VAD, Opus encoder 16 kHz mono, ring buffer PSRAM | Việc 1 và 2 |
| 4 | Gọi `neuroedge_memory_probe(NEUROEDGE_CP_AUDIO_READY, "audio_ready")` | Việc 3 |
| 5 | Điền bảng §1 và §2, chốt kết luận §5 | Việc 4 |

Vị trí chèn đã đánh dấu sẵn bằng `TODO(TSK-S1-10, V2)` trong
[`targets/esp32s3/main/main.c`](../../targets/esp32s3/main/main.c).

## 4. Cách thu số đo

```bash
cd targets/esp32s3
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

Bảng đọc được in ra với tag `neuroedge_mem`. Ngoài bảng cho người đọc, firmware
in thêm **một dòng máy đọc được** để không ai phải chép tay số liệu:

```
NEUROEDGE_MEMORY_JSON {"schema":"neuroedge.memory_spike/v1","board":"esp32s3-box-3", ...}
```

Workflow [`nightly-hardware.yml`](../../.github/workflows/nightly-hardware.yml)
grep đúng tiền tố này, lưu payload thành artifact, và kiểm tra dung lượng
firmware bằng
[`scripts/check_firmware_size.py`](../../scripts/check_firmware_size.py).

## 5. Kết luận và hệ quả phạm vi

> **Chưa thể kết luận.** Mục này chỉ được điền sau khi có số đo tại mốc
> `audio_ready`.

Quy tắc quyết định đã chốt trước khi đo, để kết quả không bị giải thích lại
theo hướng có lợi:

| Kết quả đo | Hành động bắt buộc |
|:---|:---|
| Đạt cả ba ngưỡng Q-3 | Giữ nguyên phạm vi Khối 1b. Ghi số đo làm đường cơ sở cho Tiêu chí 4 của Sprint 5 (bộ nhớ còn lại sau 4 giờ chạy) |
| Trượt bất kỳ **một** ngưỡng | **Kích hoạt bậc 5 của thang cắt phạm vi (§9) ngay**, không chờ Tuần 9: `esp32s3` chỉ chạy gate và GPIO, runtime thoại đẩy sang sau Beta |

Roadmap §4.1 nói rõ: *"Không đạt ngưỡng nào thì kích hoạt bậc 5 của thang cắt
phạm vi (§9) ngay, không chờ Tuần 9."* Giá trị của việc chạy spike ở Tuần 2 là
còn đủ thời gian để đổi phạm vi; hoãn quyết định sẽ xóa sạch giá trị đó.

## 6. Ảnh hưởng tới Tiêu chí ra Sprint 1

Tiêu chí 3 của Sprint 1 — *"Báo cáo spike bộ nhớ có số liệu đo thực, đối chiếu
trực tiếp với ngưỡng Q-3"* — **chưa thỏa mãn** và không thể thỏa mãn bằng công
việc trên máy tính. Đây là hạng mục duy nhất của Sprint 1 bị chặn bởi phần
cứng vật lý.
