# Thuật ngữ và mã định danh

Nơi **duy nhất** giải mã các ký hiệu dùng khắp kho. Mỗi dòng: mã là gì, và nơi
định nghĩa nó — đọc định nghĩa đầy đủ ở đó, tệp này không chép lại.

## 1. Mã tài liệu

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **FR-xxx-nn** | Yêu cầu chức năng, ví dụ `FR-GATE-03` (nhóm `GATE`, số 03) | `neuroedge-prd.md` §4–§8 |
| **NFR-xxx-nn** | Yêu cầu phi chức năng (hiệu năng, bảo mật, độ bền…) | `neuroedge-prd.md` §9 |
| **P0 · P1 · P2** | Độ ưu tiên: P0 bắt buộc để phát hành · P1 trượt được sang bản vá · P2 nếu còn nguồn lực | tệp này |
| **A1–A9 · B1–B5 · C1–C7** | Tiêu chí **nghiệm thu phát hành**: A = v1.0 · B = Developer Beta · C = v1.1 | `neuroedge-prd.md` §11 |
| **TR-1…TR-7** | Tiêu chí ra cấp thực thi của Khối 2 và 3 — **khác** bộ C | `neuroedge-roadmap.md` §8.3 |
| **Q-1…Q-20** | Quyết định kỹ thuật đã chốt hoặc đang mở | `neuroedge-prd.md` §15 — **sổ quyết định duy nhất** |
| **PF-1…PF-4** | Bộ lọc ưu tiên tính năng — **khác** mã rủi ro `R-n` | `neuroedge-proposal.md` §2 |
| **R-1…R-7** | Rủi ro sản phẩm | `neuroedge-prd.md` §13.2 |
| **U1–U5** | Nhóm người dùng (U1 = maker độc lập…) | `neuroedge-prd.md` §2 |
| **J1–J7** | Hành trình người dùng (J1 = "thử agent giọng nói tối nay khi chưa có bo mạch") | `neuroedge-prd.md` §2 |
| **V-G1…V-G5** | Cột mốc xác thực Giai đoạn 2 | `neuroedge-proposal.md` §12.4 |
| **RFC-NNNN** | Đề xuất sửa lược đồ hoặc ngữ nghĩa phân giải gate | `docs/rfc/` |
| **RB-1…RB-4** | Ràng buộc kỹ thuật HAL chuyển cho Sprint 4 (vd RB-3: lệnh chân phải huỷ được) | `docs/spec/hal_mcu_review.md` |
| **TODOS #n** | Việc đã xem xét và hoãn có chủ ý, kèm mốc kích hoạt | `TODOS.md` |
| **§x.y** | Mục trong `neuroedge-proposal.md`. Viết *"§x.y của tài liệu này"* khi là mục nội bộ | tệp này |

## 2. Kế hoạch và con người

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **Khối 1a · 1b · 2 · 3 · 4 · 5** | Khối công việc Giai đoạn 1: 1a lõi + Action CI · 1b vi điều khiển · 2 Fleet OS · 3 các đường ray nền tảng | `neuroedge-roadmap.md` mục lục |
| **Khối V1a · V1b · P1 · P2** | Khối công việc Giai đoạn 2 (thị giác, phủ rộng phần cứng) | `neuroedge-roadmap-phase2.md` |
| **Sprint 1…6** | Các sprint 2 tuần của Khối 1a và 1b | `neuroedge-roadmap.md` §4–§5 |
| **TSK-Sn-mm** | Một task, ví dụ `TSK-S2-03` = Sprint 2, task 03. Giai đoạn 2 dùng `TSK-V…` · `TSK-P…` | bảng task trong roadmap |
| **Tuần N · Tháng N** | Tuần/tháng thứ N **của chương trình**, tính từ Tuần 0 = **2026-09-21**. "Tháng 9" **không** phải tháng 9/2026. Khi tuần và ngày lệch nhau, ngày tuyệt đối đúng | tệp này · lịch ngày tuyệt đối: `neuroedge-prd.md` §15 (Q-19) |
| **V1–V4** | Vai trò trong đội: V1 kỹ sư lõi · V2 kỹ sư nhúng · V3 trải nghiệm lập trình viên · V4 hạ tầng dịch vụ | `neuroedge-roadmap.md` §1.1 |

> ⚠️ **Hai mã trùng chữ, khác nghĩa:**
> - **A1** là tiêu chí nghiệm thu v1.0 trong PRD, **và** là cửa sổ wedge `sim` (2026-09-28 → 10-25) trong
>   design doc Giai đoạn 1; A2 tương tự (cửa sổ `linux` + Action CI). Roadmap viết *"Sprint 2 ≈ A1"*
>   theo nghĩa thứ hai.
> - **V1** là vai trò kỹ sư lõi, **và** là tiền tố Khối V1a/V1b của Giai đoạn 2.

## 3. Mã từ các phiên review

Các mã này chỉ có nghĩa trong biên bản review; nhiều mã đã được giải thành quyết định `Q-N`.

| Mã | Là gì | Định nghĩa ở |
|:---|:---|:---|
| **CEO-X1…X6 · CEO-T1…T4 · CEO-Sn-m** | Phát hiện của review góc nhìn CEO (X = cần người quyết, T = lựa chọn khẩu vị) | `docs/archive/giai-doan-1-review-log.md` |
| **ENG-A1…A3 · ENG-T1…T3 · ENG-Qn** | Phát hiện của review kỹ thuật (A = kiến trúc, T = test, Q = chất lượng mã) | như trên |
| **DX-C1… · DX-Hn · DX-Mn** | Phát hiện của review trải nghiệm lập trình viên (C = critical, H = high, M = medium) | như trên |
| **D6–D11** | Câu hỏi trong phiên /office-hours 2026-09-22 — không có trong kho | `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md` (đầu tệp) |

## 4. Thuật ngữ sản phẩm

| Thuật ngữ | Nghĩa | Đọc thêm |
|:---|:---|:---|
| **Gate** | Chính sách an toàn dạng YAML cho một hành động vật lý: tiêu chí `evaluate`, điều kiện `allow_when`, hành vi khi bị chặn `on_block`, ngân sách `budget` | `neuroedge-proposal.md` Phụ lục B |
| **Phán quyết (verdict)** | Kết quả lượng giá một gate: `ALLOW` hoặc `BLOCK` kèm `reason` | `python/neuroedge/engine/verdict.py` |
| **Kế thừa gate (`extends`)** | Gate con dùng lại gate cha và **chỉ được siết chặt** (năm nguyên tắc B.5) | `neuroedge-proposal.md` Phụ lục B.5 |
| **Fail-closed / fail-open** | Khi không thẩm định được: chặn (mặc định) / cho qua (chỉ khi gate tự khai `fail: open`) | `neuroedge-proposal.md` Phụ lục B.4 |
| **Token phán quyết** | Bằng chứng dùng một lần mà `c.do()` cấp sau một ALLOW; HAL chỉ đổi chân khi có nó | `docs/spec/threat_model.md` |
| **`c.do()` · `c.say()`** | Cổng duy nhất tới thế giới vật lý · lời nói (không qua gate) | `python/neuroedge/actions/` |
| **HAL · 5 nguyên thủy** | Lớp phần cứng: `audio.in`, `audio.out`, `digital.out`, `sensor.read`, `display` | `neuroedge-prd.md` §4.1 (FR-HAL-01) |
| **Target `sim` · `linux` · `esp32s3`** | Môi trường chạy bậc 1: trình mô phỏng · Linux (RPi 5) · vi điều khiển ESP32-S3-Box-3 | `neuroedge-prd.md` §4.2 (FR-TGT) |
| **Bậc target (1 · 2 · 3)** | Mức cam kết chất lượng theo target (Q-13) | `neuroedge-prd.md` §15 |
| **SystemOne · SystemTwo** | Mô hình trả lời có cấu trúc (bool/level/choice) · mô hình sinh văn bản tự do | `neuroedge-proposal.md` §3.6 |
| **Ngữ pháp lệnh cố định** | Fallback khi mất mạng: danh sách câu lệnh → intent, không mạng, tất định (Q-14) | `fixtures/agents/villa-concierge/commands.toml` |
| **Action CI** | Kiểm thử hồi quy hành vi vật lý bằng vết ghi (record / replay / assert) | `neuroedge-proposal.md` §4.7 |
| **Golden Reference** | Vết ghi có quyết định là quyết định kỳ vọng; replay được so với nó theo phán quyết gate + lệnh chân, bỏ qua timing và chữ | `python/neuroedge/testing/golden.py` (FR-CI-04) |
| **gpio-sim** | Mô-đun kernel Linux tạo chip GPIO ảo qua configfs; CI chạy HAL `linux` trên nó, không cần bo mạch | `scripts/setup_gpio_sim.sh` (Q-16) |
| **Vết ghi (trace)** | Tệp JSON `trace.v1` ghi mọi sự kiện một phiên | `schemas/trace.v1.json` |
| **Wedge** | Lát cắt hẹp nhất chứng minh giá trị trước: `sim` trước, vi điều khiển sau | `docs/designs/giai-doan-1-wedge-truoc-mcu-sau.md` |
| **TTFV** | Time-to-first-value — thời gian từ cài đặt tới lần đầu thấy agent chạy (mục tiêu < 10 phút) | `neuroedge-prd.md` §2.3 (hành trình 1) |
| **CR-1.0** | Change Request 2026-09-21: chuyển kiến trúc sang cloud-first, provider-pluggable | `CHANGELOG.md` [0.2.0] |
| **NE1001…NE5001** | Mã lỗi ổn định, mỗi lỗi có 3 phần: ở đâu · vì sao · cách sửa | `neuroedge-prd.md` Phụ lục B |
