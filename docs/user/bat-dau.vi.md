# Bắt đầu ở đây

**NeuroEdge: The Physical AI that really does things, safely by design** — AI làm việc thật (rơ-le, van, chốt cửa), và an toàn nhờ chính kiến trúc chứ không nhờ AI ngoan.

Trang này cho người mới: hệ thống gồm những gì, hôm nay chạy được gì, và nên đọc gì tiếp.
Đọc mất năm phút. Các mã như `Q-72` hay `TSK-I2d-25` trong tài liệu khác là mã quyết định và mã
việc; lần đầu đọc thì bỏ qua được.

## 1. Hệ thống trong một hình

```text
  📱 Bạn            🧠 Bộ não                 🛡️ Hộp NeuroEdge              💡 Thiết bị
  nhắn tin  ──►  NeuroClaw: hiểu lời,  ──►  giữ luật: cho làm,      ──►  đèn, cửa, quạt…
                 nhớ, nhắc lịch            hỏi bạn, hay từ chối;
                                           ghi lại mọi quyết định
```

- **Bộ não (NeuroClaw)** nói chuyện với bạn qua Telegram và các kênh chat khác, gọi AI, nhớ việc,
  nhắc lịch. Nó **không** chạm thẳng vào thiết bị: muốn bật đèn, nó phải xin hộp.
- **Hộp NeuroEdge** giữ **luật** (gọi là *gate*). Với mỗi lệnh, luật cho một trong ba kết quả: làm
  ngay; hỏi bạn trước; hoặc từ chối kèm lý do. Mọi quyết định được ghi lại và phát lại được.
- **Thiết bị** là đèn, cửa, cảm biến. Hôm nay phần lớn là thiết bị ảo trên máy tính; bo mạch thật
  chưa về.

Vì sao tách bộ não khỏi hộp: AI có thể hiểu sai hoặc bị lừa. Chatbot nói sai thì bấm hỏi lại; cửa
đã mở sai thì không bấm lại được. Nên AI chỉ được *xin*, còn luật trên hộp mới *quyết*.

## 2. Hai repo

| Repo | Là gì | Viết bằng |
|:---|:---|:---|
| `neuroedge-init` (repo này) | Hộp: luật, trình mô phỏng thiết bị, firmware cho chip ESP32-S3, máy chủ để bộ não gọi vào | Python, C |
| [`letrongminh/neuroclaw`](https://github.com/letrongminh/neuroclaw) | Bộ não: chat, AI, trí nhớ, lịch; có bản phát hành cho Linux, macOS, Windows, Pi, Android, Docker, và bản cho chip ESP32 | Go, C |

Bộ não có thể chạy trên một máy riêng (VPS, Pi, laptop), hoặc chung một chip ESP32-S3 với hộp.
Một bản do NeuroEdge vận hành hộ trên cloud là dự kiến, chưa mở.

## 3. Hôm nay chạy được gì

| Đã chạy | Chưa có |
|:---|:---|
| Luật trên máy tính, với đèn, cửa, cảm biến ảo; xem trên trang web | Bo mạch thật (đang chờ hàng) |
| Cùng luật đó trên Linux (chân GPIO giả lập) và trên chip ESP32-S3 giả lập | Giao việc dài hạn bằng lời ("trông bể cá giúp tôi") |
| Ghi lại và phát lại mọi quyết định | Gói sản phẩm để chia sẻ hay bán (gọi là *Blueprint*) |
| Nhắn Telegram cho NeuroClaw để bật đèn, mở cửa (có hỏi bạn); đã chạy trong bản demo | Gói cài cho người ngoài tự dựng hộp + bộ não (đang làm) |
| NeuroClaw cho chip chạy trên chip giả lập | NeuroEdge Cloud |

Đây chưa phải sản phẩm an toàn có chứng nhận: luật không thay nút dừng khẩn hay khoá phần cứng.

## 4. Bạn muốn làm gì

| Muốn | Đọc |
|:---|:---|
| Thử luật trên laptop trong vài phút | [`python/README.md`](../../python/README.md), rồi [`huong-dan.md`](huong-dan.md) §6 |
| Nhắn tin điều khiển nhà bằng NeuroClaw | [`chat-voi-nha.md`](chat-voi-nha.md) |
| Nạp lên chip ESP32-S3 | [`nap-firmware.md`](nap-firmware.md); bộ não và hộp chung một chip: [`esp32-mot-chip.md`](esp32-mot-chip.md) |
| Hiểu kiến trúc | [`00-overview.md`](../architecture/vi/00-overview.md) |
| Xem tiến độ | [`trang-thai.md`](trang-thai.md) |

## 5. Năm từ cần biết

| Từ | Nghĩa |
|:---|:---|
| **Gate** (luật) | Chính sách an toàn viết bằng YAML; quyết định một lệnh được làm, phải hỏi, hay bị từ chối |
| **Vết ghi** (trace) | Bản ghi mọi quyết định; phát lại được để kiểm tra |
| **`sim`** | Trình mô phỏng thiết bị trên máy tính |
| **Bộ não** | Phần chat và AI; bản dùng là NeuroClaw |
| **MCP** | Cách bộ não (hay Claude Desktop, hay agent khác) gọi vào hộp để xin làm việc |

Mọi từ và mã khác: [`thuat-ngu.md`](thuat-ngu.md).
