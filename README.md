# NeuroEdge

**Physical AI, under contract.** No contract, no action: every command to the hardware
passes the gate — CI-tested, write once, run anywhere.
*Hợp đồng vào Physical AI — không hợp đồng, không hành động.*

Chatbot trả lời sai thì bấm
*Regenerate*; agent vật lý sai thì chốt cửa đã mở, đèn cầu thang đã tắt — không bấm lại
được. NeuroEdge đặt một **gate** (chính sách an toàn dạng YAML, có phiên bản, kế thừa được)
trước mọi lệnh ra phần cứng. Lời gọi từ LLM hay từ agent khác chỉ là *yêu cầu*: gate quyết
định, mọi phán quyết vào một vết ghi phát lại được. Cùng một gate chạy trên trình mô
phỏng, Linux và ESP32-S3 — hôm nay agent chạy đầy đủ trên trình mô phỏng; Linux mới
phát lại vết ghi, ESP32-S3 mới chạy logic gate.

> Alpha. Tiến độ ở
> [trạng thái dự án](https://github.com/letrongminh/neuroedge-init/blob/main/docs/user/trang-thai.md).

## Bắt đầu nhanh (Python 3.11+)

```bash
pip install 'neuroedge[mcp]'    # muốn trả lời bằng LLM thật: 'neuroedge[mcp,cloud]'
neuroedge new my-home --template home-voice
neuroedge mcp desktop-config --agent my-home/agent.toml --ui --write
```

Thoát hẳn Claude Desktop rồi mở lại, nhờ nó *"bật đèn"*: đèn ảo sáng và phán
quyết của gate hiện ngay ở http://127.0.0.1:8765 (cổng bận thì URL thật nằm trong log
MCP của Desktop). Không dùng Claude Desktop thì `cd my-home && neuroedge run --ui` — gõ
lệnh, xem cùng trang đó. Không cần mạng, không cần khoá API.

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
  · [mọi lệnh và đầu ra kỳ vọng](https://github.com/letrongminh/neuroedge-init/blob/main/CHANGELOG.md#2-cách-vận-hành)
- [Gọi tool qua gate và MCP](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/tool_calling.md)
  · [mô hình mối đe doạ](https://github.com/letrongminh/neuroedge-init/blob/main/docs/spec/threat_model.md)
- [Kiến trúc](https://github.com/letrongminh/neuroedge-init/blob/main/neuroedge-proposal.md)
  · [đóng góp](https://github.com/letrongminh/neuroedge-init/blob/main/CONTRIBUTING.md)
  · [giấy phép MIT](https://github.com/letrongminh/neuroedge-init/blob/main/LICENSE)
