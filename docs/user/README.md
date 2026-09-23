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
| Yêu cầu `FR-*` / `NFR-*` | [`neuroedge-prd.md`](../../neuroedge-prd.md) | sổ quyết định là §15 (`Q-1`…`Q-20`) |
| Kiến trúc và Phụ lục B (đặc tả gate) | [`neuroedge-proposal.md`](../../neuroedge-proposal.md) | |
| Giải mã mã viết tắt (`FR-*`, `Q-N`, `A1`, `CEO-X1`…) | [`thuat-ngu.md`](thuat-ngu.md) | nơi duy nhất |
| Thiết kế Giai đoạn 1 | [`docs/designs/`](../designs/) | *vì sao* của wedge `sim` |
| Biên bản các vòng review | [`docs/archive/`](../archive/) | lưu trữ, không quy phạm |
| Kế hoạch Giai đoạn 2 | [`neuroedge-roadmap-phase2.md`](../../neuroedge-roadmap-phase2.md) | Khối V1a → P2 |
| **Đóng góp** | | |
| Quy ước, quy trình, hoàn thành task | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | §8 là checklist bắt buộc |
| Đổi `schemas/` (lược đồ đã đóng băng) | [`docs/rfc/README.md`](../rfc/README.md) | quy trình RFC |
| Việc đã xem xét và hoãn | [`TODOS.md`](../../TODOS.md) | mỗi mục kèm mốc kích hoạt |
| Agent AI đọc gì trước | [`CLAUDE.md`](../../CLAUDE.md) | |
| **Tham chiếu** | | |
| Lược đồ, gate mẫu, vết ghi, bo mạch | `schemas/` · `gates/` · `fixtures/` · `boards/` | artifact máy đọc |
| Ràng buộc MCU cho HAL | [`docs/spec/hal_mcu_review.md`](../spec/hal_mcu_review.md) | RB-1…RB-4 |
| Số đo bộ nhớ trên `esp32s3` | [`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md) | chờ bo mạch — chưa có số |

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
    ├── designs/        thiết kế
    └── archive/        biên bản review đã khép
```

## Quy ước

- Tiếng Việt; mã, lệnh, đường dẫn giữ nguyên.
- Dẫn mã khi nhắc một sự thật (`TSK-S2-03`, `Q-17`, `RFC-0004`, `FR-GATE-03`,
  `TODOS.md #15`) — không chép lại nội dung.
- Ngày tuyệt đối (`2026-09-28`), không dùng "tuần sau".
- `trang-thai.md` do máy sinh: sửa [`neuroedge-roadmap.md`](../../neuroedge-roadmap.md)
  §0 rồi chạy `python3 scripts/gen_user_status.py`, **đừng sửa tay**.
