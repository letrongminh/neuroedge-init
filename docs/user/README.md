# NeuroEdge — tài liệu cho người dùng

NeuroEdge là nền tảng **Action Contract** cho thiết bị vật lý: mọi hành động ra
phần cứng đi qua một *gate* đã đóng băng lược đồ, chạy được ở các môi trường
ngang hàng (`sim`, `linux`, `esp32s3`) mà không rẽ nhánh logic theo target.

Mỗi sự thật trong kho có **đúng một nơi** (`CONTRIBUTING.md` §8.1). Bản đồ này
trả lời câu *"cần biết X thì đọc tệp nào"* — các tệp khác dẫn mã, không chép lại.

## Đọc gì theo nhu cầu

| Bạn cần | Đọc | Ghi chú |
|:---|:---|:---|
| **Chạy thử** | | |
| Cài đặt và chạy test | [`python/README.md`](../../python/README.md) | venv + `pip install -e '.[dev]'` |
| Toàn bộ lệnh CLI và đầu ra kỳ vọng | [`CHANGELOG.md`](../../CHANGELOG.md) §2 | nguồn duy nhất cho cú pháp lệnh |
| Hôm nay dùng được gì | [`huong-dan.md`](huong-dan.md) | hướng dẫn sử dụng cho maker |
| Trạng thái hiện tại | [`trang-thai.md`](trang-thai.md) | máy sinh từ roadmap §0 |
| **Hiểu sản phẩm** | | |
| Yêu cầu `FR-*` / `NFR-*` | [`neuroedge-prd.md`](../../neuroedge-prd.md) | sổ quyết định là §15 (mã `Q-N`) |
| Kiến trúc và Phụ lục B (đặc tả gate) | [`neuroedge-proposal.md`](../../neuroedge-proposal.md) | |
| Giải mã mã viết tắt (`FR-*`, `Q-N`, `A1`, `CEO-X1`…) | [`thuat-ngu.md`](thuat-ngu.md) | nơi duy nhất |
| Vì sao Giai đoạn 1 đi "wedge `sim` trước" | [`docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`](../archive/giai-doan-1-wedge-truoc-mcu-sau.md) | lịch sử, đóng băng 2026-09-23 — kế hoạch hiện hành ở roadmap |
| Biên bản các vòng review | [`docs/archive/`](../archive/) | lưu trữ, không quy phạm |
| Dashboard sản phẩm cho CPO (tiến độ, mốc, việc chờ người, quyết định) | [`docs/business/cpo-dashboard.html`](../business/cpo-dashboard.html) | mở bằng trình duyệt; sinh từ roadmap — đừng sửa tay |
| Cổng nhu cầu 2026-10-25 (phỏng vấn, demo, chấm điểm) | [`docs/business/cong-nhu-cau-2026-10-25/`](../business/cong-nhu-cau-2026-10-25/README.md) | tài liệu kinh doanh, Q-20 |
| Kế hoạch Giai đoạn 2 | [`neuroedge-roadmap-phase2.md`](../../neuroedge-roadmap-phase2.md) | Khối V1a → P2 |
| Kế hoạch Giai đoạn 1.5 — NeuroBrain | [`neuroedge-roadmap-phase1-5.md`](../../neuroedge-roadmap-phase1-5.md) | Khối N0 → N7, bản nháp chờ `Q-N`; wireframe ở [`wireframe/`](../../wireframe/README.md) |
| Mở rộng cho robot phân tầng (FOFOCA) | [`draft-ke-hoach-mo-rong-robot-fofoca.md`](../../draft-ke-hoach-mo-rong-robot-fofoca.md) · RFC nháp [`draft-rfc-node-giao-thuc-dieu-phoi.md`](../../draft-rfc-node-giao-thuc-dieu-phoi.md) | chặng W0–W4, bản nháp chờ `Q-N` — chưa phải quyết định |
| **Đóng góp** | | |
| Quy ước, quy trình, hoàn thành task | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | §8 là checklist bắt buộc |
| Đổi `schemas/` (lược đồ đã đóng băng) | [`docs/rfc/README.md`](../rfc/README.md) | quy trình RFC |
| Việc đã xem xét và hoãn | [`TODOS.md`](../../TODOS.md) | mỗi mục kèm mốc kích hoạt |
| Phát hành lên PyPI / TestPyPI | [`docs/release.md`](../release.md) | bật công tắc, đẩy tag |
| Agent AI đọc gì trước | [`CLAUDE.md`](../../CLAUDE.md) | |
| **Tham chiếu** | | |
| Lược đồ, gate mẫu, vết ghi, bo mạch | `schemas/` · `gates/` · `fixtures/` · `boards/` | artifact máy đọc |
| Tool call, MCP, xác nhận `ask` (Gated Tool Profile) | [`docs/spec/tool_calling.md`](../spec/tool_calling.md) | nơi duy nhất cho tool call |
| Đường tắt qua gate đã chặn, và điều ngoài phạm vi | [`docs/spec/threat_model.md`](../spec/threat_model.md) | kèm tên test |
| Mỗi nguyên thủy HAL × target: chạy bằng gì, kiểm ở đâu | [`docs/spec/simulation_coverage.md`](../spec/simulation_coverage.md) | Q-21, Q-22 |
| Ràng buộc MCU cho HAL | [`docs/spec/hal_mcu_review.md`](../spec/hal_mcu_review.md) | RB-1…RB-4 |
| Số đo bộ nhớ trên `esp32s3` | [`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md) | TSK-S1-10 |

## Bố cục kho

```text
neuroedge-init/
├── schemas/            lược đồ đóng băng (chỉ RFC mới sửa được)
├── gates/              gate mẫu phân giải được
├── boards/             khai báo năng lực bo mạch (TOML)
├── fixtures/           vết ghi chuẩn mực + corpus phản chứng
├── python/             SDK: hal/ · engine/ · cli/ · tests/
├── targets/esp32s3/    firmware ESP-IDF
├── scripts/            công cụ CI (sinh tài liệu, kiểm dung lượng firmware)
└── docs/
    ├── user/           tài liệu cho người dùng  ← bạn đang ở đây
    ├── rfc/            thay đổi lược đồ
    ├── spec/           đặc tả và ràng buộc
    ├── reports/        báo cáo đo
    ├── business/       tài liệu kinh doanh (cổng nhu cầu)
    ├── release.md      quy trình phát hành PyPI
    └── archive/        lưu trữ: biên bản review, thiết kế đã đóng băng
```

## Quy ước

- Tiếng Việt; mã, lệnh, đường dẫn giữ nguyên.
- Dẫn mã khi nhắc một sự thật (`TSK-S2-03`, `Q-17`, `RFC-0004`, `FR-GATE-03`,
  `TODOS.md #15`) — không chép lại nội dung.
- Ngày tuyệt đối (`2026-09-28`), không dùng "tuần sau".
- `trang-thai.md` do máy sinh: sửa [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md)
  §0 rồi chạy `python3 scripts/gen_user_status.py`, **đừng sửa tay**.
