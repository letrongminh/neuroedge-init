# Chat với nhà bằng NeuroClaw

Bạn nhắn Telegram (hay kênh chat khác) cho **bộ não**, và bộ não điều khiển thiết bị trong nhà
qua **hộp tại nhà**. Bộ não là [NeuroClaw](https://github.com/letrongminh/neuroclaw), repo riêng,
MIT. Hộp là `neuroedge mcp serve --http` của kho này. Hộp giữ gate: lệnh nào cũng là *yêu cầu*,
gate quyết định, việc cần hỏi chủ nhà thì hỏi trên trang tại nhà.

> Trạng thái: chạy được với `sim` (thiết bị ảo), đã thử trên laptop và trên một máy ảo đóng vai
> cloud. Khoá, token và cấp quyền hôm nay là của bộ script demo, hạn 30 ngày, chưa phải bản cho
> người dùng. NeuroEdge Cloud chưa mở (Q-74). Kiến trúc: [`15-target-architecture.md`](../architecture/vi/15-target-architecture.md) §6.10.

## Chọn cách chạy bộ não

| Cách chạy | Bộ não ở đâu | Đọc |
|:---|:---|:---|
| Tự host | NeuroClaw (Go) trên VPS, board Linux, Pi, máy Mac hay Windows | Mục 1 → 3 dưới đây |
| Một chip | NeuroClaw-ESP chung một ESP32-S3 với gate | [`esp32-mot-chip.md`](esp32-mot-chip.md) (chờ bo) |
| NeuroEdge Cloud | Instance do NeuroEdge vận hành | Chưa có — có điều kiện sau cổng nhu cầu (Q-74) |

## 1. Dựng hộp

Hộp đòi đủ chứng chỉ máy chủ, CA của thiết bị, issuer và khoá ký token; thiếu một thứ là không
mở cổng ([`tool_calling.md`](../spec/tool_calling.md) §8.1). Cách nhanh nhất hôm nay là script
của demo: [`demo/i2f-chat-den-cua/kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md) §0.1.
Nó tạo khoá một lần (`tao-khoa.py`), rồi chạy `neuroedge mcp serve --http --ui --target sim`.
Trang `127.0.0.1:8765` là màn hình tại nhà, nơi bạn duyệt việc cần hỏi chủ nhà.

## 2. Cài NeuroClaw và nối với hộp

- **Cài** theo môi trường: [hướng dẫn cài của NeuroClaw](https://github.com/letrongminh/neuroclaw/blob/main/docs/guides/install.md).
- **Nối với hộp** bằng một máy chủ MCP kiểu `http` có khối `tls` (CA, chứng chỉ và khoá của bộ
  não, token): [NeuroClaw làm bộ não NeuroEdge](https://github.com/letrongminh/neuroclaw/blob/main/docs/guides/neuroedge.md).
- **Hoặc dùng script demo:** `chay-nao.sh` tải bản phát hành NeuroClaw (kiểm checksum), dựng
  `config.json` từ [`demo/i2f-chat-den-cua/neuroclaw/config.json`](../../demo/i2f-chat-den-cua/neuroclaw/config.json)
  và chạy `neuroclaw gateway`; `dung-vps.sh` làm việc đó trên VPS
  ([`kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md) §0.2).

Chỉ chép sang máy bộ não những gì nó cần: CA, chứng chỉ và khoá của bộ não, token. **Không bao giờ**
chép khoá của issuer hay của hộp.

## 3. Chọn bộ não mở hay khoanh vùng

NeuroClaw có đủ năng lực PicoClaw: shell, bus phần cứng, cài skill, lệnh trong cron. Mỗi thứ đang
bật ghi một dòng `NeuroClaw risk=<tên>` lúc khởi động (Q-80).

- **Bộ não chung máy với hộp** mà còn `risk=shell` hay `risk=hardware_bus` thì đi vòng được gate.
  Hãy tắt chúng trong `config.json` (bản của demo đã tắt) hoặc chạy bộ não dưới user riêng không có
  quyền phần cứng (TSK-I2d-24).
- **Bộ não ở máy khác** (VPS, cloud): gate vẫn quyết mọi việc với thiết bị trong nhà; shell chỉ tới
  được chính máy đó.

Vì sao: [`threat_model.md`](../spec/threat_model.md) §2k. Danh sách nhãn: `docs/reference/capabilities.md`
§2 của repo `neuroclaw`.

## 4. Chat

Nhắn bot: "bật đèn phòng khách" chạy ngay; "mở cửa" làm hộp hỏi bạn trên trang tại nhà, và bộ não
báo đang chờ bạn duyệt. Kịch bản đủ sáu màn và kết quả đã chạy:
[`kich-ban.md`](../../demo/i2f-chat-den-cua/kich-ban.md).
