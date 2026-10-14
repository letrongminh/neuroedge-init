# NeuroEdge

**From an idea to a physical AI product: build it, run it safely, share and sell it.**
Physical AI, under contract — no contract, no action: every command to the hardware passes
the gate.
*Nơi biến ý định thành sản phẩm vật lý có AI — dựng, chạy an toàn, chia sẻ và bán.*

Đó là hướng đi (Q-72); agent vận hành và NeuroEdge Blueprint **chưa có mã**. Cái đã chạy hôm
nay là lớp niềm tin bên dưới. Chatbot trả lời sai thì bấm
*Regenerate*; agent vật lý sai thì chốt cửa đã mở, đèn cầu thang đã tắt — không bấm lại
được. NeuroEdge đặt một **gate** (chính sách an toàn dạng YAML, có phiên bản, kế thừa được)
trước mọi lệnh ra phần cứng. Lời gọi từ LLM hay từ agent khác chỉ là *yêu cầu*: gate quyết
định, mọi phán quyết vào một vết ghi phát lại được. Cùng một gate chạy trên trình mô
phỏng, Linux và ESP32-S3. Hôm nay agent chạy đầy đủ trên trình mô phỏng; trên Linux, chân
GPIO, cảm biến và màn hình đã chạy trên phần cứng ảo, âm thanh chạy từ tệp WAV; trên ESP32-S3, gate của agent
tự kiểm lúc khởi động và cập nhật OTA có ký đã chạy trên QEMU — bo mạch thật chưa về.

> Alpha. NeuroEdge **không** phải chức năng an toàn được chứng nhận (không SIL, không PL): gate
> không thay nút dừng khẩn hay interlock phần cứng. Tiến độ ở
> [trạng thái dự án](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/trang-thai.md).

## Chat với nhà

Bộ não của nhà là [**NeuroClaw**](https://github.com/letrongminh/neuroclaw) (repo riêng, MIT):
bạn nhắn Telegram, nó gọi LLM, nhớ, nhắc lịch, và chạm thiết bị **chỉ** qua bộ tool MCP của hộp
NeuroEdge — gate vẫn quyết từng lệnh, việc cần hỏi thì hỏi chủ nhà. Nó chạy trên Linux, cloud,
Pi, macOS, Windows; bản cho chip (NeuroClaw-ESP) chung một ESP32-S3 với gate, hôm nay trên QEMU. Cách nối:
[chat với nhà](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/chat-voi-nha.md).

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
