# Đợt thử với đối tác — NeuroEdge

> **Lời hứa:** *đặt một gate trước mọi lệnh AI chạm vào thiết bị bạn đang có* — trong ≤ 15 phút, không cần mua phần cứng mới.

NeuroEdge đặt một **gate** (một tệp YAML bạn đọc được) giữa AI và thiết bị: mỗi lệnh phải qua gate, gate **chặn mặc định**, và bạn **mở có chủ ý** từng thứ một. Mọi quyết định được ghi vào một
**vết ghi** bạn đọc và phát lại được. Đợt thử này là bản dành riêng cho một đội đối tác, theo thoả thuận thử nghiệm bằng văn bản; wheel được giao trực tiếp, **không** có trên PyPI hay index nào.

## 1. Bạn cần

- **Python 3.11 trở lên** (`python3 --version`).
- **Một tệp wheel** do chúng tôi gửi, ví dụ `neuroedge-0.1.0-py3-none-any.whl`.
- Một thứ bạn đang có để che: một MCP server (ví dụ Home Assistant), một API HTTP của thiết bị trong nhà, hoặc một agent Python của bạn.

Cài vào một môi trường riêng (đừng cài vào Python hệ thống):

<!-- guide: skip reason="cài wheel thật của đối tác; script partner_guides_check.sh cài wheel vào một venv sạch trước khi chạy các hướng dẫn" -->
```bash
python3 -m venv neuroedge-venv
. neuroedge-venv/bin/activate
pip install './neuroedge-0.1.0-py3-none-any.whl[mcp]'
neuroedge --help
```

`[mcp]` kéo thêm SDK MCP (cần cho `proxy mcp` và cho các ví dụ chạy thử). Có lệnh `neuroedge` là xong bước cài.

## 2. Chọn hướng dẫn

| Bạn muốn che | Đọc | Lệnh chính | Cần |
|:---|:---|:---|:---|
| Home Assistant (hoặc MCP server khác) mà Claude Desktop đang gọi | [`home-assistant-mcp.md`](home-assistant-mcp.md) | `guard init --mcp`, `proxy mcp` | địa chỉ MCP và token của HA |
| Tool call trong **agent Python của bạn** | [`guard-python.md`](guard-python.md) | `neuroedge.guard` | chỉ Python — không cần thiết bị |
| API HTTP của thiết bị trong nhà (Tasmota, Shelly, REST tự viết) | [`proxy-http.md`](proxy-http.md) | `guard init --http`, `proxy http` | địa chỉ API, `curl` |

Mỗi hướng dẫn: ≤ 3 lệnh tới giá trị đầu, cách thấy **BLOCK** rồi **ALLOW** sau khi bạn mở gate có chủ ý, cách đọc vết ghi, cách làm proxy thành đường duy nhất, và các lỗi thường gặp với thông báo thật.
Mọi lệnh trong ba hướng dẫn được chạy tự động từ wheel (`scripts/partner_guides_check.sh`) trên bản giả của Home Assistant và của API thiết bị — tức là lệnh đúng, **không** nghĩa là đã đúng với thiết bị thật của bạn.

## 3. Ba điều cần nhớ

1. **Chặn mặc định.** Gate sinh ra chặn mọi thứ (`BLOCK`, `criterion_unavailable`) cho tới khi bạn sửa nó. Thấy `BLOCK` ngay lần đầu là đúng, không phải hỏng.
2. **Proxy canh con đường đi qua nó.** Ai gọi thẳng thiết bị vẫn không qua gate. `neuroedge plugin doctor` báo những lối vòng nó thấy; đóng chúng là việc của bạn (token, tường lửa).
3. **Vết ghi chứa tham số của lời gọi** (ví dụ tên thiết bị), không băm. Đọc trước khi gửi cho chúng tôi.

## 4. Gửi phản hồi

Dùng [`phan-hoi.md`](phan-hoi.md): chép mẫu, điền (thời gian tới BLOCK đầu, tới ALLOW có chủ ý đầu, lỗi nguyên văn, điều khó hiểu), gửi qua kênh riêng chúng tôi đã mở cho đội bạn.
Muốn gửi vết ghi: gửi tệp `trace-*.json` sau khi bạn đã đọc nó.

## 5. Giới hạn

Đọc [`gioi-han.md`](gioi-han.md) trước khi bắt đầu: đợt thử **chưa** có `esp32s3`, thoại trên chip, NeuroBrain; Home Assistant mới chỉ kiểm trên bản giả; proxy không chặn được lời gọi thẳng; và giấy phép
(PolyForm Noncommercial) chỉ cho đánh giá theo thoả thuận bằng văn bản.
