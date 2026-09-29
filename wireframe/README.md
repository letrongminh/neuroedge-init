# wireframe/

Wireframe HTML tham chiếu cho giao diện. Mở trực tiếp bằng trình duyệt; không cần mạng.

**Không phải mã nguồn và không được đóng gói.** Mỗi tệp nhúng một **bản chụp**
`python/neuroedge/viz/assets/ui.css` ở thời điểm vẽ. CSS thật của trang sim vẫn chỉ nằm
ở `python/neuroedge/viz/assets/`. Khi hai nơi lệch nhau, `viz/assets/` đúng.

| Tệp | Nội dung | Kế hoạch |
|:---|:---|:---|
| [`studio-v1.html`](studio-v1.html) | **NeuroEdge Studio.** Wireframe ứng dụng cục bộ tích hợp đầy đủ mọi năng lực trên laptop: phiên trực tiếp, gate, vết ghi, kiểm chứng, thiết bị ESP32-S3, MCP và cấu hình agent (song ngữ VI/EN) | bản duyệt giao diện trước khi viết mã |
| [`lab-monitor-v2.html`](lab-monitor-v2.html) | **Bản tham chiếu.** Panel Lab Monitor trong trang sim, cập nhật theo design review 2026-09-24 | `neuroedge-design-neurobrain.md` §11 (Khối N5b) |
| [`lab-monitor-v1.html`](lab-monitor-v1.html) | Hai biến thể bố cục ban đầu (A: panel trong trang, **đã chọn**; B: tab riêng) | lịch sử, không quy phạm |

Font IBM Plex **chưa** nhúng trong wireframe (chờ TSK-N0-06). Wireframe dùng font hệ thống.
