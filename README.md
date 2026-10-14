# NeuroEdge

**From an idea to a physical AI product: build it, run it safely, share and sell it.**
Physical AI, under contract — no contract, no action: every command to the hardware passes
the gate.
*Nơi biến ý định thành sản phẩm vật lý có AI — dựng, chạy an toàn, chia sẻ và bán.*

NeuroEdge là **hộp giữ luật** đứng giữa AI và thiết bị. AI chỉ được *xin* làm một việc; luật
trên hộp (gọi là *gate*) quyết định: làm ngay, hỏi bạn trước, hay từ chối kèm lý do — và ghi lại
mọi quyết định để phát lại được. Lý do: chatbot nói sai thì bấm hỏi lại, còn cửa đã mở sai thì
không bấm lại được.

```text
📱 Bạn nhắn tin ──► 🧠 NeuroClaw (bộ não) ──► 🛡️ Hộp NeuroEdge (luật) ──► 💡 Đèn, cửa, cảm biến
```

Bộ não là **NeuroClaw**, repo riêng `letrongminh/neuroclaw` (MIT): chat qua Telegram, gọi AI, nhớ,
nhắc lịch, và chạm thiết bị **chỉ** qua hộp. Nó chạy trên Linux, cloud, Pi, macOS, Windows, hoặc
chung một chip ESP32-S3 với hộp.

**Hôm nay chạy được:** luật trên máy tính với thiết bị ảo, trên Linux với chân GPIO giả lập, trên
chip ESP32-S3 giả lập (QEMU); nhắn Telegram cho NeuroClaw để bật đèn, mở cửa có hỏi chủ nhà — đã
chạy trong bản demo. **Chưa có:** bo mạch thật, giao việc dài hạn bằng lời, gói chia sẻ hay bán
(*Blueprint*).

**Người mới đọc trước:** [Bắt đầu ở đây](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/bat-dau.md) (5 phút) · nối bộ não với hộp:
[chat với nhà](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/chat-voi-nha.md).

> Alpha. NeuroEdge **không** phải chức năng an toàn được chứng nhận (không SIL, không PL): gate
> không thay nút dừng khẩn hay interlock phần cứng. Tiến độ ở
> [trạng thái dự án](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/trang-thai.md).

## Bắt đầu nhanh (Python 3.11+)

Chưa phát hành lên PyPI: trước bản công khai, cài từ mã nguồn theo
[`python/README.md`](https://github.com/letrongminh/neuroedge-init/blob/main/python/README.md), rồi chạy hai
lệnh sau.

```bash
pip install neuroedge    # qua Claude Desktop hoặc LLM thật: 'neuroedge[mcp,cloud]'
neuroedge new my-home --template home-voice
neuroedge run --agent my-home/agent.toml -c "bật đèn"
```

Không cần mạng, không cần khoá API, không cần tài khoản: câu *"bật đèn"* đi qua ngữ pháp
lệnh cục bộ, gate `light_on` cho ALLOW và đèn ảo `porch_light` bật. Gõ tiếp nhiều lệnh và
xem phán quyết trên trang cục bộ: `cd my-home && neuroedge run --ui`.

Muốn nhờ Claude Desktop *"bật đèn"*: `pip install 'neuroedge[mcp]'`, rồi
`neuroedge mcp desktop-config --agent my-home/agent.toml --ui --write`, thoát hẳn Claude
Desktop rồi mở lại — phán quyết hiện ở http://127.0.0.1:8765 (cổng bận thì URL thật nằm
trong log MCP của Desktop).

## Gate trông thế nào

```yaml
name:    unlock_door
version: 1.2.0
extends: neuroedge://gates/hospitality/base-access@1.0.0   # chỉ được siết chặt gate cha

allow_when:
  room_matches: true
  risk_level:   { lte: low }        # cha cho tới medium — con siết xuống low

on_block: { action: escalate, to: human_receptionist }
budget:   { p95_latency_ms: 120, fail: closed }   # không thẩm định kịp ⇒ CHẶN
```

Không đường nào tới chân GPIO bỏ qua gate.

## Đọc tiếp

- [Hướng dẫn người dùng](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/README.md)
  · [năm kit phần cứng](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/kit-phan-cung.md)
  · [mọi lệnh và đầu ra kỳ vọng](https://github.com/letrongminh/neuroedge-init/blob/main/CHANGELOG.md#2-cách-vận-hành)
- [Gọi tool qua gate và MCP](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/tool_calling.md)
  · [mô hình mối đe doạ](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/threat_model.md)
- [Kiến trúc](https://github.com/letrongminh/neuroedge-init/blob/main/docs/architecture/README.md)
  · [đóng góp](https://github.com/letrongminh/neuroedge-init/blob/main/CONTRIBUTING.md)
  · [giấy phép](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSING.md)

## Giấy phép

Mã theo [PolyForm Noncommercial 1.0.0](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSE):
dùng miễn phí cho mục đích phi thương mại; **dùng thương mại cần license thương mại**. Lược đồ,
đặc tả và bộ kiểm tuân thủ theo
[Apache-2.0](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSES/Apache-2.0.txt), để ai
cũng hiện thực được chuẩn. Phạm vi từng phần:
[`LICENSING.md`](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSING.md).
