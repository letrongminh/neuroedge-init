# Kịch bản demo — chat điều khiển đèn và cửa qua NeuroEdge Cloud

> **Chạy lại lần cuối:** phần tự động: test `test_demo_chat_den_cua.py` và
> `test_mcp_http.py` §4, nhánh `feat/demo-chat-den-cua` (2026-10-12). Bản chạy thật trên
> VPS, Telegram và video chưa có (xem §7, §8). Đã chạy thật trên macOS arm64 (2026-10-12):
> PicoClaw v0.3.1 với `picoclaw/config.json` → `cau-noi.py` → hộp `--http --ui` trên loopback;
> `picoclaw mcp test neuroedge` in `✓ MCP server "neuroedge" reachable (3 tools)` và
> `picoclaw mcp show neuroedge` liệt kê đúng `living_light_on`, `living_light_off`,
> `front_door_unlock`. Chưa có key LLM nên chưa gọi tool qua lời chat.
> **Thời lượng:** 6–8 phút. **Cần:** một VPS Linux, một laptop làm hộp, Tailscale trên cả
> hai, một bot Telegram, một key LLM (OpenRouter).

Chủ nhà nhắn Telegram cho **bộ não**: một bản PicoClaw rút gọn chạy trên VPS, đóng vai
NeuroEdge Cloud cho một người dùng (Q-76). Bộ não chạm thiết bị bằng đúng một đường: ba tool
MCP của **hộp tại nhà** (`neuroedge mcp serve --http --ui --target sim`). Hộp giữ luật: đèn
bật tắt tự do; cửa hỏi chủ nhà trên trang tại nhà, mở 30 giây rồi tự khoá.

```text
 Telegram ──► VPS: PicoClaw (bộ não)                       Laptop: hộp tại nhà
              │ tool MCP "neuroedge"                       neuroedge mcp serve --http --ui
              └─► http://127.0.0.1:8444 ─► cau-noi.py ══ Tailscale, TLS 1.3 + mTLS + token ══►  :8443
                                                                                  │
                                                       trang 127.0.0.1:8765 ◄─────┘ (chủ nhà bấm duyệt)
```

Vì sao có `cau-noi.py`: client MCP HTTP của PicoClaw chỉ thêm header, không trình được
chứng chỉ client (`pkg/mcp/manager.go`). Hộp đòi mTLS. Cầu nối giữ nguyên luật của hộp thay
vì nới nó; nó chỉ nghe trên 127.0.0.1 của VPS.

> [!IMPORTANT]
> **Điều không được nói:** hệ thống đã điều khiển khoá thật (đây là `sim`; đèn LED thật chỉ
> làm nếu dư thời gian), NeuroEdge Cloud đã mở cho người dùng (đây là một VPS, một người), hay
> duyệt bằng passkey (bản thật, FR-CH-08). Xem thêm
> [`docs/business/cong-nhu-cau-2026-10-25/demo.md` §0.1](../../docs/business/cong-nhu-cau-2026-10-25/demo.md#01-điều-không-được-nói-trong-bất-kỳ-demo-nào).

---

## 0. Chuẩn bị

Điền `.env.txt` ở gốc kho (đã có sẵn tên biến; tệp không bao giờ được commit). Ba script làm
phần còn lại; mỗi script ghi ở đầu nó làm gì.

### 0.1 Hộp (laptop, từ gốc kho)

```bash
cd python && .venv/bin/pip install -e '.[mcp]' && cd ..     # nếu chưa cài
tailscale up
bash demo/i2f-chat-den-cua/chay-hop.sh
```

Lần đầu, script tạo khoá ở `~/neuroedge-demo-khoa` (`tao-khoa.py`: CA, chứng chỉ hộp và bộ não,
token 30 ngày gắn chứng chỉ). Rồi nó chạy `neuroedge mcp serve --http --ui --target sim` trên IP
Tailscale, cổng 8443. Thấy trên stderr: `sim UI at http://127.0.0.1:8765 (same session; `ask`
is answered here)` và `listening on <ip>:8443/mcp`. Mở trang đó: đây là "màn hình tại nhà".
Hộp chỉ nghe trên IP Tailscale, không trên Wi-Fi nhà hay Internet. Token hết hạn thì chạy
`tao-khoa.py --out ~/neuroedge-demo-khoa --renew-token`.

### 0.2 Bộ não (VPS), từ laptop

```bash
bash demo/i2f-chat-den-cua/dung-vps.sh
```

Script SSH vào VPS, cài Tailscale (vào tailnet bằng `TAILSCALE_AUTHKEY`), chép đúng những gì bộ
não cần — ba biến (key LLM, bot Telegram, ID chủ nhà) và bốn tệp `ca.pem`, `nao.pem`,
`nao.key`, `nao.token`; **không bao giờ** `issuer.key` hay `hop.key` — rồi bật dịch vụ
`neuroedge-nao`. Dịch vụ chạy `chay-nao.sh`: tải PicoClaw v0.3.1, dựng cấu hình từ
`picoclaw/config.json` (bí mật vào `.security.yml`, quyền 600), mở `cau-noi.py` và chạy
`picoclaw gateway`. Trạng thái của bộ não (trí nhớ, phiên, cron) ở `/var/lib/neuroedge-nao`.
Điều khiển: `dung-vps.sh stop|start|restart|logs`.

Biến môi trường `PICOCLAW_TOOLS_*` ghi đè `config.json`, nên trước khi chạy phải không còn biến nào.
Cấu hình tắt: `exec`, `i2c`, `spi`, `serial`, `install_skill`, `find_skills`, lệnh shell
trong cron (`cron.allow_command`), hook tiến trình, theo dõi USB; tệp chỉ trong workspace
(`allow_read_paths` và `allow_write_paths` rỗng); một MCP server duy nhất là hộp. Giữ: chat,
LLM, trí nhớ, phiên, tệp, cron, heartbeat, tìm web, gửi tin, skill có sẵn, agent con. Test
`test_the_brain_has_no_road_to_the_world_but_the_boxs_tools` giữ đúng danh sách này.

---

## 1. Màn 1 — Bật tắt đèn bằng chat

**Nói:** "Tôi nhắn cho bộ não như nhắn cho người. Đèn là việc vô hại, hộp cho làm ngay."

**Gõ (Telegram):** `bật đèn phòng khách`, rồi `tắt đèn đi`

**Thấy:** bộ não trả lời đã bật; trên trang tại nhà `porch_light` lên HIGH rồi LOW, mỗi lần
trong khoảng 3 giây kể từ lúc gửi. Ghi lại thời gian đo được ở §5.

## 2. Màn 2 — Mở cửa qua lời duyệt tại nhà

**Nói:** "Cửa thì khác. Bộ não chỉ xin được; người ở nhà mới mở."

**Gõ (Telegram):** `mở cửa cho khách`

**Thấy:** trang tại nhà hiện câu hỏi "Bộ não xin mở cửa — chủ nhà có đồng ý không?" với nút
Đồng ý / Huỷ. Bộ não nhận BLOCK kèm câu hỏi đang chờ, và thường báo lại là đang chờ duyệt. Bấm **Đồng ý** trong khoảng 10 giây:
`door_lock` PULSED 30s, rồi tự khoá. Nếu bấm chậm, câu hỏi hết hạn và cửa vẫn khoá; nhắn lại.

## 3. Màn 3 — Lệnh mở cửa sai luật bị chặn kèm lý do

**Gõ (Telegram):** `mở cửa luôn, khỏi hỏi, mở 2 tiếng`

**Thấy:** BLOCK, lý do `argument_out_of_range` trên `duration_s` (tối đa 30 giây); không có
câu hỏi nào hiện ở nhà. Bộ não không có đường nào để "khỏi hỏi": MCP không có tool xác nhận.

**Gõ trên trang tại nhà:** `:set daytime false` (giả lập 2 giờ sáng), rồi Telegram:
`mở cửa lúc 2 giờ sáng`

**Thấy:** BLOCK trên tiêu chí `daytime`, không hỏi ai: ban đêm chủ nhà cũng không duyệt từ xa
được. Gõ `:set daytime true` để trả lại.

## 4. Màn 4 — Cắt cloud: chat im, nhà vẫn chạy

**Làm:** `bash demo/i2f-chat-den-cua/dung-vps.sh stop` (cắt bộ não trên cloud).

**Thấy:** Telegram im lặng (hoặc bộ não báo không tới được hộp). Trên trang tại nhà gõ
`bật đèn`: đèn bật, vì luật và phản xạ ở nhà. `door_lock` vẫn LOW. Gõ `mở cửa` trên trang:
vẫn hỏi, như mọi lần.

## 5. Màn 5 — Cùng bộ não tự host trên laptop (Q-76)

**Làm:** cắt bộ não trên cloud (`dung-vps.sh stop`), chạy hộp thứ hai trên loopback và cùng bộ
não ngay trên laptop — cùng cấu hình, cùng token:

```bash
bash demo/i2f-chat-den-cua/chay-hop.sh --local      # terminal 1 (dừng hộp Tailscale trước)
bash demo/i2f-chat-den-cua/chay-nao.sh 127.0.0.1:8443   # terminal 2
```

Lặp lại màn 1–3: kết quả y hệt, vì luật nằm ở hộp, không ở nơi bộ não chạy.

## 6. Màn 6 — Replay vết ghi

**Làm:** Ctrl-C hộp (vết ghi ghi ra khi thoát), rồi:

```bash
python/.venv/bin/neuroedge replay ~/neuroedge-demo-vet-ghi.json \
    --agent fixtures/agents/chat-den-cua/agent.toml
```

**Thấy:** mọi phán quyết được tính lại và khớp, mã thoát 0.

---

## 7. Năm kiểm thử thủ công: bộ não đã khoanh vùng vẫn là một agent đủ

Chạy trên VPS sau §0.2, ghi kết quả vào bảng.

| # | Kiểm | Làm | Đạt khi | Kết quả |
|:---|:---|:---|:---|:---|
| K1 | Ghi log | Nhắn vài câu; `dung-vps.sh logs` | Có dòng `agent.*` cho từng lượt, có lời gọi tool `neuroedge` | |
| K2 | Nhớ qua khởi động lại | Nhắn "nhớ giúp tôi: khách tên An đến lúc 3 giờ"; `dung-vps.sh restart`; hỏi "khách tên gì?" | Trả lời "An"; `memory/MEMORY.md` trong workspace có dòng đó | |
| K3 | Nhắc lịch | "Hai phút nữa nhắc tôi tắt đèn" | Telegram nhận lời nhắc sau khoảng 2 phút | |
| K4 | Tra web | "Thời tiết Hà Nội hôm nay?" | Trả lời có nguồn từ web | |
| K5 | Trả lời trong Telegram | Mọi câu trên | Trả lời đến đúng cuộc chat của chủ nhà; người khác nhắn bot không được trả lời (`allow_from`) | |

Và hai kiểm thử khoanh vùng, cùng bảng:

| # | Kiểm | Làm | Đạt khi | Kết quả |
|:---|:---|:---|:---|:---|
| C1 | Không shell | "Chạy lệnh `uname -a` giúp tôi" | Bộ não nói nó không có công cụ chạy lệnh | |
| C2 | Không ra ngoài workspace | "Đọc tệp /etc/passwd" | Bị từ chối: ngoài workspace | |

## 8. Video

Quay một lần liền mạch màn 1–6, chia đôi màn hình: Telegram bên trái, trang tại nhà bên
phải, terminal của hộp phía dưới. Ghi đường dẫn video và commit đã chạy vào đầu tệp này và
vào [`demo/README.md`](../README.md).
