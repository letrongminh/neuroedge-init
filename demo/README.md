# Danh mục demo theo increment — NeuroEdge

Thư mục `demo/` tập hợp các kịch bản trình diễn và mã lệnh chuẩn bị cho từng mốc phát triển của dự án NeuroEdge. Theo quyết định Q-49, mỗi increment ra kèm một demo trong `demo/<increment>/`, chạy được bằng lệnh có thật, ghi commit đã chạy lại; quy tắc này được kiểm tra bằng review trước khi hoàn thành một increment. Tài liệu giúp người thuyết trình trình diễn trực tiếp các năng lực hiện có của NeuroEdge cho người ngoài đội ngũ kỹ thuật.

## Các bản demo

| Increment | Thư mục | Trạng thái | Chạy ở đâu | Chạy lại lần cuối |
|:---|:---|:---|:---|:---|
| I1 — **NeuroEdge Studio** (giao diện) | [`i1-studio/`](i1-studio/) | sẵn sàng — bảy màn kiểm trên trình duyệt | local macOS/Linux, `neuroedge studio` | nhánh `studio/integration` (2026-09-29) |
| I1 — terminal | [`i1-sim/`](i1-sim/) | sẵn sàng | local macOS/Linux, không cần phần cứng | `6a69626` (2026-09-29) |
| I3 (phần không cần bo mạch) + OTA của I7 | [`i3-firmware-qemu/`](i3-firmware-qemu/) | sẵn sàng | Docker `espressif/idf:v5.4` (Mac Apple Silicon hoặc Linux) | `6a69626` (2026-09-29) |
| I4 (thoại trên laptop) | [`i4-thoai-laptop/`](i4-thoai-laptop/) | sẵn sàng — đường provider đã chạy thật; micro: chạy thử trên máy trình bày | local macOS, tai nghe, `OPENROUTER_API_KEY` | nhánh `voice/integration` (2026-09-29) |

## Vì sao chạy local, không Docker

Bản demo `sim` chạy trực tiếp trên máy cục bộ (macOS hoặc Linux) thay vì chạy trong container Docker vì trang giao diện trực quan `--ui` chỉ bind vào địa chỉ loopback `127.0.0.1`, đồng thời Docker trên macOS không thể chuyển tiếp trực tiếp micro và loa vào container cho các tác vụ âm thanh. Ngược lại, các demo firmware (như I3) chạy trong Docker với cùng image môi trường của CI (`espressif/idf:v5.4`). Với target `linux`, hệ thống đòi hỏi nhân Linux thật có mô-đun `gpio-sim` (máy ảo Linux), nên phần này được chứng minh qua nhật ký chạy của CI (job `linux-hal`).

## Demo phỏng vấn khách hàng

Ngoài các demo theo từng increment kỹ thuật tại thư mục này, tài liệu kịch bản demo phỏng vấn theo từng phân khúc nhu cầu khách hàng (≤ 5 phút mỗi phân khúc, phục vụ kiểm chứng giả thuyết kinh doanh) được lưu tại [`docs/business/cong-nhu-cau-2026-10-25/demo.md`](../docs/business/cong-nhu-cau-2026-10-25/demo.md).

## Thêm demo cho increment mới

Khi thêm demo cho một increment mới theo quyết định Q-49:
- Đặt tên thư mục con theo quy ước `i<N>-<slug>/` (ví dụ `i1-sim/`, `i3-firmware-qemu/`).
- Tạo tệp `kich-ban.md` gồm lời dẫn của người thuyết trình, khối lệnh gõ có thật và khối đầu ra thực tế trích từ hệ thống (rút gọn bằng ký hiệu `…`).
- Ghi rõ commit git và môi trường đã chạy lại lần cuối ở đầu tệp kịch bản.
- Cập nhật dòng tương ứng trong bảng danh mục demo của tệp này.
