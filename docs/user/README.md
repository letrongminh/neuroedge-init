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
| Sản phẩm làm được gì, trên môi trường nào, và thử từng bước ra sao | [`huong-dan.md`](huong-dan.md) | năng lực theo nhóm (§3–§4) và kịch bản thử từng bước (§5) |
| Trạng thái hiện tại | [`trang-thai.md`](trang-thai.md) | máy sinh từ roadmap §0 |
| Nạp agent của mình lên ESP32-S3-BOX-3 (hoặc QEMU) | [`nap-firmware.md`](nap-firmware.md) | `build --target esp32s3` → `idf.py flash`; nơi duy nhất của thủ tục nạp |
| **Hiểu sản phẩm** | | |
| Yêu cầu `FR-*` / `NFR-*` | [`neuroedge-prd.md`](../../roadmap/neuroedge-prd.md) | sổ quyết định là §15 (mã `Q-N`) |
| Kiến trúc và Phụ lục B (đặc tả gate) | [`neuroedge-proposal.md`](../../roadmap/neuroedge-proposal.md) | |
| Giải mã mã viết tắt (`FR-*`, `Q-N`, `A1`, `CEO-X1`…) | [`thuat-ngu.md`](thuat-ngu.md) | nơi duy nhất |
| Vì sao Giai đoạn 1 đi "wedge `sim` trước" | [`docs/archive/giai-doan-1-wedge-truoc-mcu-sau.md`](../archive/giai-doan-1-wedge-truoc-mcu-sau.md) | lịch sử, đóng băng 2026-09-23 — kế hoạch hiện hành ở roadmap |
| Biên bản các vòng review | [`docs/archive/`](../archive/) | lưu trữ, không quy phạm |
| Dashboard sản phẩm cho CPO (tiến độ, mốc, việc chờ người, quyết định) | [`docs/business/cpo-dashboard.html`](../business/cpo-dashboard.html) | mở bằng trình duyệt; sinh từ roadmap — đừng sửa tay |
| Cổng nhu cầu 2026-10-25 (phỏng vấn, demo, chấm điểm) | [`docs/business/cong-nhu-cau-2026-10-25/`](../business/cong-nhu-cau-2026-10-25/README.md) | tài liệu kinh doanh, Q-20 |
| Kế hoạch: increment I0–I18 (kèm I2a, I2b, I3a, I4a, I5a), việc gì làm khi nào, ngày dự báo | [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md) | roadmap duy nhất (Q-39); bảng increment ở §0.2 |
| Ghi chú thiết kế — thị giác, phủ rộng phần cứng | [`neuroedge-design-phase2.md`](../../roadmap/neuroedge-design-phase2.md) | Khối V1a → P2; không lịch, không trạng thái — increment ở roadmap (I11, I13, I16–I18; thị giác cơ bản V1b đã vào MVP ở I2a, I3a — Q-53) |
| Ghi chú thiết kế — NeuroBrain | [`neuroedge-design-neurobrain.md`](../../roadmap/neuroedge-design-neurobrain.md) | Khối N0 → N7; increment I4a, I5a ở roadmap (Q-55); wireframe ở [`wireframe/`](../../wireframe/README.md) |
| Ghi chú thiết kế — robot phân tầng (FOFOCA) | [`draft-ke-hoach-mo-rong-robot-fofoca.md`](../../roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md) · RFC nháp [`draft-rfc-node-giao-thuc-dieu-phoi.md`](../../roadmap/draft-rfc-node-giao-thuc-dieu-phoi.md) | chặng W0–W4; increment I14 ở roadmap (Q-32), riêng khối W1 ở I2a, I3a (Q-53); RFC node chưa cấp số |
| **Đóng góp** | | |
| Quy ước, quy trình, hoàn thành task | [`CONTRIBUTING.md`](../../CONTRIBUTING.md) | §8 là checklist bắt buộc |
| Đổi `schemas/` (lược đồ đã đóng băng) | [`docs/rfc/README.md`](../rfc/README.md) | quy trình RFC |
| Việc đã xem xét và hoãn | [`TODOS.md`](../../TODOS.md) | mỗi mục kèm mốc kích hoạt |
| Phát hành: tag nội bộ trước I6, PyPI từ I6 | [`docs/release.md`](../release.md) | đẩy tag; công tắc PyPI chỉ bật ở I6 |
| Agent AI đọc gì trước | [`CLAUDE.md`](../../CLAUDE.md) | |
| **Tham chiếu** | | |
| Lược đồ, gate mẫu, vết ghi, bo mạch | `schemas/` · `gates/` · `fixtures/` · `boards/` | artifact máy đọc |
| Tool call, MCP, xác nhận `ask` (Gated Tool Profile) | [`docs/spec/tool_calling.md`](../spec/tool_calling.md) | nơi duy nhất cho tool call |
| Máy trạng thái hội thoại: lượt, cắt lời, wake-word, STT/TTS, STT dự phòng | [`docs/spec/voice_fsm.md`](../spec/voice_fsm.md) | quy phạm cho cả Python lẫn chip |
| Giao diện thiết bị: màn hình, quy tắc ngôn ngữ, ảnh golden | [`docs/spec/ui.md`](../spec/ui.md) | quy tắc ngôn ngữ ở §2 |
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
├── targets/esp32s3/    firmware ESP-IDF (ui/: giao diện LVGL và ảnh golden)
├── pipewire/           cấu hình PipeWire khử vang cho micro/loa trên linux
├── scripts/            công cụ CI (sinh tài liệu, kiểm dung lượng firmware)
└── docs/
    ├── user/           tài liệu cho người dùng  ← bạn đang ở đây
    ├── rfc/            thay đổi lược đồ
    ├── spec/           đặc tả và ràng buộc
    ├── reports/        báo cáo đo
    ├── business/       tài liệu kinh doanh (cổng nhu cầu)
    ├── release.md      quy trình phát hành (tag nội bộ, PyPI từ I6)
    └── archive/        lưu trữ: biên bản review, thiết kế đã đóng băng
```

## Quy ước

- Tiếng Việt; mã, lệnh, đường dẫn giữ nguyên.
- Dẫn mã khi nhắc một sự thật (`TSK-S2-03`, `Q-17`, `RFC-0004`, `FR-GATE-03`,
  `TODOS.md #15`) — không chép lại nội dung.
- Lịch bằng increment (`I3`) hoặc ngày tuyệt đối (`2026-09-28`); không dùng "tuần sau"
  hay nhãn tuần/tháng đánh số (`CONTRIBUTING.md` §8.3).
- `trang-thai.md` do máy sinh: sửa [`neuroedge-roadmap.md`](../../roadmap/neuroedge-roadmap.md)
  §0 rồi chạy `python3 scripts/gen_user_status.py`, **đừng sửa tay**.
