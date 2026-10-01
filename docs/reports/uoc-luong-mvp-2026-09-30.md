# Ước lượng lại phạm vi MVP — 2026-09-30

Bằng chứng cho các ngày dự báo của I2a → I8 ở [`roadmap/neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) §0.2
(TSK-I2a-01, luật R5). Phạm vi là MVP của Q-52: I1 → I7, kể cả I2a, I2b, I3a, I4a, I5a. Quyết định:
[`roadmap/neuroedge-prd.md`](../../roadmap/neuroedge-prd.md) §15 (Q-52 → Q-57).

## 1. Dữ liệu tốc độ

Đếm trên bảng task của roadmap ngày 2026-09-30 (ô trạng thái ✅ kèm ngày):

| Ngày hoàn thành | Task |
|:---|---:|
| 2026-09-23 | 22 |
| 2026-09-24 | 11 |
| 2026-09-25 | 8 |
| 2026-09-26 | 13 |
| 2026-09-27 | 1 |
| không ghi ngày | 12 |
| **Tổng** | **67** |

67 task xong trong khoảng 2026-09-21 → 2026-09-29, tức **khoảng 7 task mỗi ngày** cho cả đội. Mọi task đó là
việc trên host (Python, C trên host và QEMU, tài liệu), đặc tả rõ, không chờ phần cứng, không chờ người ngoài.

**Hệ số lập kế hoạch: chia 4**, còn **khoảng 1,75 task mỗi ngày** cho việc trên host của MVP. Lý do:

- task mới lớn hơn (nguyên thủy HAL mới, pipeline thị giác, NeuroBrain) và chạm tầng an toàn;
- mọi mã của nguyên thủy mới chờ RFC được chấp thuận (§2.3 roadmap), nên có hàng đợi review;
- đội chưa làm dạng việc này, nên tốc độ của I0 là cận trên, không phải kỳ vọng.

Việc cần phần cứng và việc cần người ngoài **không** tính bằng tốc độ này: chúng tính bằng ngày phần cứng về
và thời gian thật của phép đo.

## 2. Phân loại 106 task MVP còn mở

Không tính TSK-I2a-01 (task này).

| Increment | Host | Cần phần cứng | Cần người ngoài hoặc bên thứ ba | Tổng |
|:---|---:|---:|---:|---:|
| I1 | — | — | 2 (TSK-I1-02 đo TTFV · TSK-I1-04 micro thật trên máy trình bày) | 2 |
| I2 | — | 1 (TSK-I2-01, Pi 5) | — | 1 |
| I2a | 23 (5 RFC/đặc tả + 18 hiện thực) | 2 (TSK-N3-03 nếu spike trượt · TSK-V1b-05 NPU) | — | 25 |
| I2b | 2 | 2 (TSK-I2b-01, I2b-02: kiểm BOM và sơ đồ đấu dây trên Pi) | — | 4 |
| I3 | — | 8 | — | 8 |
| I3a | — | 7 | — | 7 |
| I4 | — | 2 (TSK-S5-08 Pi + HAT · TSK-S3-13 phần thời gian thực) | 2 (TSK-I4-01 mô hình wake-word có giấy phép · TSK-I4-04 micro thật) | 4 |
| I4a | 33 | — | — | 33 |
| I5 | — | 7 | — | 7 |
| I5a | — | 2 | — | 2 |
| I6 | 1 (TSK-S3-09) | 1 (TSK-I6-03 video trên ba target) | 3 (PyPI, tên miền, kênh cộng đồng) + điều khoản license (`TODOS.md` #44) | 5 |
| I7 | 4 (TSK-S6-07, S6-08, W0-01, I7-01) | 3 (TSK-S6-03, S6-05, S6-06 chạy 24 giờ) | 1 (TSK-I7-02: A1 10 người, A9 bên thứ ba) + A12 (5 người) | 8 |
| **Tổng** | **63** | **35** | **8** | **106** |

## 3. Giả định

| # | Giả định | Nếu sai |
|:---:|:---|:---|
| G1 | Box-3, RPi 5 và bo ESP32-S3 có camera về **trước 2026-11-01**; bo camera được chọn ở TSK-I3a-01 **trước 2026-10-09** để kịp đặt mua | Mọi increment từ I3 dời theo, ngày đổi ngày |
| G2 | Sáu RFC (0007, 0009 → 0013) được kỹ thuật trưởng chấp thuận **trước 2026-10-09**; câu hỏi mở đã quyết (Q-57) | I2a còn khoảng 3 tuần đệm trước khi phụ thuộc I2 (2026-11-29) ràng ngày; quá 2026-10-30 thì I2a dời |
| G3 | Đủ người cho V1 → V7 (Q-52), mỗi làn làm song song | Đọc lại theo roadmap §1.3 |
| G4 | Spike bộ nhớ TSK-S1-10 đạt ngưỡng Q-3 với thoại + bốn gói | Mở `Q-N` lập lại kế hoạch I5, I3a; dời ngày, không cắt (Q-44, Q-52) |
| G5 | `vision.in` chạy được trên bo camera ESP32-S3 trong ngân sách bộ nhớ (TSK-I3a-01) | Áp phương án (b) hoặc (c) của RFC-0013 §9; lập lại kế hoạch I3a |
| G6 | Điều khoản license thương mại (`TODOS.md` #44) có trước I6 | I6 và I7 dời |

## 4. Ngày dự báo

Tính theo làn: làn host dùng tốc độ §1; làn chip bắt đầu khi bo mạch về (G1); ngày của một increment không
sớm hơn ngày của mọi increment nó phụ thuộc (luật R3).

| Increment | Dự báo | Cách tính |
|:---|:---:|:---|
| I1, I2, I3, I4, I5 | giữ nguyên | Phạm vi không đổi; đủ người nên làn chip của I3a không lấy người của I3, I5 |
| **I2a** | **2026-12-06** | 18 task hiện thực sau RFC (G2) ≈ 10 ngày làm việc ở 1,75 task/ngày; phần NPU và ADC trên phần cứng sau 2026-11-01; ràng bởi I2 (2026-11-29) + một tuần tích hợp |
| **I2b** | **2026-12-20** | Hai tuần sau I2a: năm kit kiểm trên Pi, thư viện gate, `neuroedge add` |
| **I3a** | **2027-01-10** | Bốn tuần sau I3 (2026-12-13): HAL C của bốn gói, thị giác trên bo camera, test mất điện giữa lệnh `motion.*` |
| **I4a** | **2027-01-03** | 33 task host, phần lớn làm được trước I2a; ràng bởi I4 (2026-12-13) và TSK-I4a-01 (cần đủ bốn gói của I2a) + ba tuần phủ bốn gói và review bản nháp |
| **I5a** | **2027-01-24** | Hai tuần sau I3a: lab action, gate và phong bì trên chip |
| **I6** | **2027-01-31** | Một tuần sau I5a: PyPI, lược đồ công khai, video trên ba target, license (G6) |
| **I7** | **2027-02-21** | Ba tuần sau I6: A1 (10 người cài từ PyPI), A12 (5 người dựng kit), A9 (bên thứ ba), chạy 24 giờ, Secure Boot |
| **I8** | **2027-03-21** | Bốn tuần Beta sau I7 (§5.4 roadmap) |

**Đường găng:** bo mạch về → TSK-S1-10 → I3 → I3a → I5a → I6 → I7. So với dự báo trước khi mở rộng phạm vi
(v1.0 2027-01-24), v1.0 lùi **bốn tuần**: phần mở rộng trên host chạy song song và nằm ngoài đường găng, còn làn
chip thêm I3a và I5a.

## 5. Khi nào ước lượng lại

- Bất kỳ giả định G1 → G6 nào sai: ước lượng lại trong cùng PR với bằng chứng (R5).
- Ngày 2026-11-01: đối chiếu tốc độ thật của làn host trong tháng 10 với 1,75 task/ngày.
- Khi TSK-S1-10 có số đo và khi TSK-I3a-01 chọn xong bo camera.
