# Rà soát thiết kế HAL dưới ràng buộc vi điều khiển

| | |
|:---|:---|
| **Mã task** | TSK-S1-11 |
| **Người thực hiện** | V2 — Kỹ sư nhúng (bán thời gian tới Tuần 6) |
| **Đầu vào** | `schemas/board.v1.json`, `python/neuroedge/hal/board.py`, `boards/*.toml` |
| **Trạng thái** | ✅ Rà soát xong · các kết luận đã hiện thực hóa trong mã |

## 0. Vì sao rà soát này phải xảy ra ở Sprint 1 *(bối cảnh lúc rà soát)*

Roadmap §1.2 nêu thẳng: *"Một HAL thiết kế mà không có tiếng nói của kỹ sư nhúng
sẽ phải viết lại ở Tuần 6."* Tài liệu này là tiếng nói đó, đặt trước khi có bất
kỳ hiện thực HAL nào (`sim` ở Sprint 2, `linux` ở Sprint 3, `esp32s3` ở Sprint
4) — vì sau đó thì mọi kết luận đây đều trở thành việc viết lại.

Ràng buộc nền: ESP32-S3-WROOM-1-N16R8 có **512 KB SRAM nội**, trong đó Q-3 chỉ
dành **≥ 120 KB** cho ứng dụng sau khi trừ ngăn xếp mạng và hệ điều hành. Mọi
quyết định thiết kế dưới đây đo bằng thước đó.

---

## 1. Năm kết luận rà soát

### KL-1 — Tập nguyên thủy phải đóng, và nó đang đóng

`audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` — đúng năm, cố
định bởi FR-HAL-01.

**Vì sao quan trọng trên MCU:** tập đóng cho phép bảng năng lực phía thiết bị là
một **mảng tĩnh định kích thước lúc biên dịch**. Nếu tập nguyên thủy mở rộng
được lúc chạy, firmware sẽ cần cấp phát động trong HAL — thứ không được phép
trong đường dẫn âm thanh, vì phân mảnh heap sau nhiều giờ chạy là một trong hai
nguyên nhân hàng đầu gây rớt khung âm thanh.

**Đã hiện thực:** `PRIMITIVES` trong `python/neuroedge/hal/board.py` là một
`tuple`, và mọi tên nguyên thủy lạ bị từ chối ngay tại `_normalise()` với thông
báo nêu rõ tập hợp lệ. Kiểm chứng: `test_unknown_primitive_is_refused`.

### KL-2 — Mã tác tử phải đánh địa chỉ chân theo TÊN, không theo số

Tác tử viết `c.do("door_lock")`, không viết `gpio_set_level(11, 1)`. Bo mạch sở
hữu phép ánh xạ `door_lock → GPIO 11` qua `[capabilities.digital_out].pins`.

**Vì sao quan trọng:** đây là điều kiện cần của tương đương target. `sim` không
có GPIO 11; `linux-rpi5` có GPIO 11 nhưng nối vào thứ khác. Một tác tử ghim số
chân sẽ không thể chạy trên ba target, và tương đương target chính là luận điểm
sản phẩm.

**Đã hiện thực:** `boards/*.toml` khai báo cùng một tập tên chân trên cả ba
target. Kiểm chứng: `test_all_three_targets_share_the_same_named_pins`.

### KL-3 — `sim` không được giàu năng lực hơn bo mạch tham chiếu

**Rủi ro đã chặn:** nếu `sim` khai báo 4 kênh âm thanh vào hoặc 48 kHz trong khi
Box-3 chỉ có 2 kênh 16 kHz, lập trình viên sẽ viết tác tử chạy tốt trong mô
phỏng rồi thất bại lúc `neuroedge build` — hoặc tệ hơn, thất bại lúc chạy trên
thiết bị. Khi đó lời hứa "TTFV dưới 10 phút không cần mua phần cứng" (A1) trở
thành một cái bẫy: nó rút ngắn 10 phút đầu và thêm vào hai ngày gỡ lỗi.

**Đã hiện thực:** `boards/sim-default.toml` sao đúng tham số của Box-3 —
16 kHz, AEC, VAD, cùng tập chân, cùng tập cảm biến. Kiểm chứng:
`test_sim_offers_no_pin_the_reference_board_lacks`,
`test_sim_offers_no_sensor_the_reference_board_lacks`,
`test_sim_audio_matches_the_reference_sample_rate`.

*Ngoại lệ có chủ ý:* `display` của `linux-rpi5` là 800×480 còn Box-3 là 320×240.
Chấp nhận được vì `display` không nằm trong miền quyết định an toàn — không có
phán quyết gate nào phụ thuộc kích thước màn hình. Ràng buộc parity chỉ áp cho
`sim` so với bo mạch tham chiếu, không áp giữa hai target phần cứng thật.

### KL-4 — Khai báo bo mạch là DỮ LIỆU, không phải MÃ

Thêm một bo mạch = thêm một tệp TOML. Không thêm một dòng Python.

**Vì sao quan trọng:** nếu profile bo mạch là mã Python, nó có thể chứa hành vi
mà bản dựng MCU không có (và không thể có). Khi đó "bo mạch đã khai báo năng
lực này" sẽ mang nghĩa khác nhau giữa host và thiết bị — đúng tại tầng mà đối
chiếu năng lực hai chiều phải đáng tin.

**Đã hiện thực:** `boards/` chỉ chứa TOML, được thẩm định bằng
`schemas/board.v1.json`. Tên tệp trùng `id` để tra cứu không bị lệch. Kiểm
chứng: `test_profile_filename_matches_its_declared_id`,
`test_profile_validates_against_board_schema`.

### KL-5 — Trên MCU không có evaluator CEL, không có parser JSON

Đây là hệ quả trực tiếp của **Q-9 phương án A** (và Q-23 về định dạng) và là kết luận
có ảnh hưởng lớn nhất tới thiết kế HAL. Thiết bị **có** lượng giá gate — bằng một walker
duyệt cây đã biên dịch sẵn (TSK-S4-02) — nhưng mọi phần phân tích và biên dịch ở máy tính.

| Chạy trên máy tính | Chạy trên thiết bị |
|:---|:---|
| Phân giải `extends` (5 nguyên tắc B.5) | — |
| Phân tích cú pháp CEL | — |
| Biên dịch sang cây quyết định, mã hoá bố cục nhị phân `NETR` v1 (Q-23, RFC-0003) | Walker C99 duyệt cây `NETR` tại chỗ trong flash |
| Chuẩn tắc hóa RFC 8785, băm | Kiểm magic, phiên bản bố cục, CRC của cây trước khi dùng |
| Ký số gate (Khối 3, Gate Registry) | Đối soát chữ ký — cũng thuộc Khối 3, chưa có |

**Ngân sách phía thiết bị:** walker không cấp phát heap, không dùng RAM tĩnh, không đệ
quy, không phân tích cú pháp, không máy ảo CEL; stack ≤ 512 byte
(`targets/esp32s3/components/ne_gate/src/ne_walker.c`,
`test_the_walker_uses_no_static_ram_and_a_small_stack`).

*Ghi chú 2026-09-24:* bản rà soát đầu (Sprint 1) viết KL-5 là "không có gate engine nào
chạy trên MCU" và dự kiến "cây quyết định JSON" + "một hàm C khoảng 100 dòng"; Q-23 và
RFC-0003 thay bằng bố cục nhị phân. Ý của kết luận — thiết bị không phân tích, chỉ duyệt
— giữ nguyên. Model bo mạch trong
`board.py` **chỉ đọc trên máy tính** — đó là lý do nó được phép dùng Pydantic,
`jsonschema`, `tomllib` mà không tạo ra nợ kỹ thuật nào cho firmware.

**Điều bị cấm:** nhúng `cel-python` hoặc bất kỳ trình lượng giá biểu thức nào
vào firmware. Roadmap §3.8 đã bác bỏ tường minh phương án B (evaluator CEL rút
gọn bằng C) vì nó tạo ra một hiện thực thứ hai cần giữ đồng bộ ở đúng tầng an
toàn.

---

## 2. Bốn ràng buộc chuyển tiếp sang Sprint 4

Các mệnh đề dưới đây là hợp đồng mà `hal/esp32s3` phải thỏa, ghi ở đây để
Sprint 4 không phải suy luận lại:

| # | Ràng buộc | Lý do |
|:---:|:---|:---|
| RB-1 | Không `malloc` trong đường dẫn âm thanh sau khi khởi tạo xong | Phân mảnh heap sau nhiều giờ chạy gây rớt khung; Tiêu chí 4 Sprint 5 đo bộ nhớ còn lại sau 4 giờ |
| RB-2 | Đệm âm thanh cấp phát tĩnh trong PSRAM, đặt tên và đo được | Q-3 dành ≥ 2 MB PSRAM cho ring buffer, VAD và wake-word; không đo được thì không đối chiếu được |
| RB-3 | `digital.out` phải hủy được lệnh đang chờ trong ≤ 1 khung âm thanh | Hợp đồng thu hồi lệnh vật lý ([`voice_fsm.md`](voice_fsm.md) §5): cắt lời phải hủy xung chốt cửa đang chờ, ghi `ACTUATOR_ABORTED_BY_BARGE_IN` |
| RB-4 | Bảng năng lực là `const` trong flash, không phải cấu trúc dựng lúc chạy | Tiết kiệm SRAM và loại bỏ khả năng năng lực bị sửa lúc chạy — một đường tắt vòng qua gate (A3) |

**RB-3 là ràng buộc khó nhất.** Nó nói rằng `digital_out` không thể là một lời
gọi chặn (blocking). Chữ ký hiện tại trong
`python/neuroedge/hal/__init__.py` nhận `duration_ms` và ghi nhận trạng thái
chân ngay — đủ cho `sim`, nhưng hiện thực `esp32s3` sẽ cần một handle hủy được.
Ghi nhận là **nợ thiết kế đã biết**, phải giải quyết tại TSK-S4-01 cùng lúc với
hợp đồng thu hồi lệnh, chứ không phải sau.

## 3. Điều rà soát này KHÔNG kết luận

Rà soát này nói về *hình dạng thiết kế*, không nói về *khả thi bộ nhớ*. Câu hỏi
"AEC + VAD + Opus có vừa 120 KB SRAM và 2 MB PSRAM không" chỉ trả lời được bằng
số đo trên bo mạch thật — đó là TSK-S1-10, và trạng thái của nó ở
[`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md):
**chưa có số đo**.

Hai hạng mục độc lập với nhau: thiết kế HAL có thể đúng trong khi ngân sách bộ
nhớ vẫn trượt — khi đó lập lại kế hoạch I5 theo Q-44, không cắt thoại.
