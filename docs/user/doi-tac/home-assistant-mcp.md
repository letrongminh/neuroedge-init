# Hướng dẫn 1 — Home Assistant qua `neuroedge proxy mcp`

> **Mục tiêu:** đặt một gate trước *mọi lệnh AI gửi tới Home Assistant* (HA) qua tích hợp **MCP Server** của HA — Claude Desktop hay bất
> kỳ MCP client nào nói chuyện với proxy, không với HA. **Thời gian:** ≤ 15 phút từ lúc đã cài wheel.
>
> **Trạng thái kiểm — đọc trước:** hướng dẫn này **chưa kiểm trên Home Assistant thật**. Mọi lệnh bên dưới được script
> [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh) chạy từ wheel trên một **bản giả**
> ([`fixtures/ha_mcp_double/`](../../../fixtures/ha_mcp_double/server.py)) dựng theo tài liệu công khai của tích hợp MCP Server (địa chỉ, token
> `Bearer`, tên tool kiểu `HassTurnOn`). Tên tool, tham số và địa chỉ `/api/mcp` của HA thật có thể khác; chỗ nào khác, đó là phản hồi quý giá —
> gửi theo [mẫu phản hồi](phan-hoi.md). Giới hạn khác: [`gioi-han.md`](gioi-han.md).

## 0. Bạn cần

- Đã cài wheel theo [README](README.md) (`neuroedge --help` chạy được).
- Trong HA: tích hợp **Model Context Protocol Server** đã bật, và nên tạo **một người dùng HA riêng cho proxy** với một *long-lived access token*
  (Hồ sơ → Bảo mật). Token chỉ để trong biến môi trường, **không bao giờ** trong tệp.
- Địa chỉ MCP của HA, ví dụ `http://192.168.1.10:8123/api/mcp` (mạng nhà, http thuần) hay `https://…` nếu bạn có.

Đặt hai biến (`read -s` không in và không lưu token vào lịch sử shell):

<!-- guide: skip reason="đặt biến môi trường: script đã đặt sẵn HA_MCP_URL và HA_AUTH trỏ vào bản giả" -->
```bash
export HA_MCP_URL="http://192.168.1.10:8123/api/mcp"
read -rs HA_TOKEN && export HA_AUTH="Bearer $HA_TOKEN" && unset HA_TOKEN
```

## 1. Ba lệnh tới giá trị đầu

**Lệnh 1 — nối vào HA, liệt kê tool, viết cấu hình và gate.** `--allow-lan-http` chỉ cần khi HA nói http thuần trên mạng nhà; dùng `https://` thì bỏ
nó (lý do và rủi ro: [`gioi-han.md`](gioi-han.md)).

<!-- guide: run expect="tool(s) behind the Guard, all BLOCKED until you open their gate" expect="wrote" -->
```bash
neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --name homeassistant --dir ha
```

Nó viết `ha/guard.toml` và một gate cho **mỗi** tool của HA trong `ha/gates/`. Mỗi gate **chặn mặc định**: nó đòi một dữ kiện (`operator_approved`) mà không ai đặt.
Tool có tham số bắt buộc không phải kiểu đơn giản (chuỗi, số, đúng/sai) không được phơi ra, và lệnh in lý do; tham số tuỳ chọn kiểu danh sách (như `domain` của HA)
bị bỏ, kèm ghi chú. Tên tool trong `guard.toml` là chữ thường (`hassturnon`); tên thật của HA nằm ở `[proxy.mcp.names]`.

**Lệnh 2 — đăng ký proxy vào Claude Desktop** (thay cho `HA` trong cấu hình Claude). Thử ra một tệp tạm trước — lệnh không đụng cấu hình thật:

<!-- guide: run expect="Wrote mcpServers['homeassistant']" expect="Quit Claude Desktop completely" -->
```bash
neuroedge proxy mcp --config ha/guard.toml --desktop-config --write --config-path ./claude_desktop_thu.json
```

Hài lòng thì ghi vào cấu hình thật (lệnh giữ mọi mục khác, và sao lưu tệp cũ thành `.bak-<giờ>`):

<!-- guide: skip reason="ghi vào cấu hình Claude Desktop thật của máy; bước trên đã thử cùng lệnh ra tệp tạm" -->
```bash
neuroedge proxy mcp --config ha/guard.toml --desktop-config --write
```

Claude Desktop chạy proxy với môi trường **tối thiểu**: nó không thấy `HA_AUTH` của shell bạn. Mở tệp cấu hình và thêm khối `env` cho đúng mục `homeassistant`
(lệnh in nhắc điều này và **không** ghi token vào tệp thay bạn):

<!-- guide: skip reason="chỉnh tay cấu hình Claude Desktop" -->
```json
"homeassistant": { "command": "…", "args": ["…"], "env": { "HA_AUTH": "Bearer <token của người dùng HA riêng>" } }
```

Đây là điểm yếu bạn phải biết: token nằm **dạng chữ rõ** trong tệp cấu hình của Claude Desktop trên máy này. Đó là lý do nên dùng người dùng HA riêng với quyền hẹp cho proxy.

**Lệnh 3 — thoát hẳn rồi mở lại Claude Desktop** (không chỉ đóng cửa sổ), rồi hỏi: *"bật đèn phòng khách"*. Claude gọi tool qua proxy và nhận **BLOCK**.

Không có Claude Desktop, hoặc muốn tự chạy thử: lưu máy khách nhỏ này thành `thu.py`. Nó khởi chạy proxy y như Claude Desktop, gọi một tool và in kết quả; tham số đầu là tệp vết ghi.

<!-- guide: run -->
```bash
cat > thu.py <<'PY'
import asyncio, json, os, sys
from mcp import Client, StdioServerParameters

async def main(trace, tool, arguments):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "neuroedge", "proxy", "mcp", "--config", "ha/guard.toml", "--trace-out", trace],
        env={"HA_AUTH": os.environ["HA_AUTH"]},
    )
    async with Client(params) as client:
        result = await client.call_tool(tool, arguments)
        print(json.dumps(result.structured_content or result.content[0].text))

asyncio.run(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3])))
PY
```

## 2. Thấy BLOCK

<!-- guide: run expect='"status": "BLOCK"' expect='"reason": "criterion_unavailable"' expect='"failed_criterion": "operator_approved"' log_lacks="HA_LOG|HassTurnOn" -->
```bash
python thu.py ha/trace-block.json hassturnon '{"name": "Living room lamp"}'
```

`BLOCK` + `criterion_unavailable` nghĩa là gate chạy đúng: nó đòi `operator_approved` mà không ai đặt, nên **không có gì tới HA** (script kiểm cả điều này: HA giả không nhận lời gọi nào).
Đây là kết quả bình thường, không phải lỗi — và là điều bạn muốn khi một AI bị lừa gọi một tool.

## 3. Mở gate có chủ ý rồi thấy ALLOW

Mở gate là việc **bạn làm bằng tay**, từng tool một. Gate của tool `hassturnon` nằm ở `ha/gates/hassturnon@1.0.0.yaml`; đầu tệp có hướng dẫn.
Cách nhanh nhất là xoá tiêu chí `operator_approved` ở hai chỗ (`evaluate:` và `allow_when:`) bằng một lệnh — hoặc sửa bằng trình soạn thảo:

<!-- guide: run -->
```bash
f="ha/gates/hassturnon@1.0.0.yaml"
awk '/^  operator_approved:/ {skip=1; next} skip && /^    / {next} {skip=0; print}' "$f" > "$f.new" && mv "$f.new" "$f"
```

Sau đó gate chỉ còn điều kiện nguồn: `call_source: { in: [mcp] }` — client MCP phía trước proxy được gọi tool này. Kiểm gate vẫn hợp lệ:

<!-- guide: run expect="gate(s) resolved" -->
```bash
neuroedge gate lint ha/gates
```

<!-- guide: run expect="Turned on Living room lamp" log_has="HA_LOG|HassTurnOn" -->
```bash
python thu.py ha/trace-allow.json hassturnon '{"name": "Living room lamp"}'
```

Lần này lời gọi qua gate và **mới** tới HA (script kiểm HA giả nhận đúng một lệnh `HassTurnOn`). Các tool khác vẫn bị chặn — thử `hassturnoff`:

<!-- guide: run expect='"status": "BLOCK"' log_lacks="HA_LOG|HassTurnOff" -->
```bash
python thu.py ha/trace-other.json hassturnoff '{"name": "Living room lamp"}'
```

Mở bao nhiêu tuỳ bạn, nhưng đừng mở theo kiểu "cho mọi MCP client": thêm điều kiện thật vào gate (`neuroedge gate explain`, các gate mẫu ở `gates/`) cho thứ khó hoàn tác như khoá cửa.

## 4. Đọc vết ghi

Mỗi phiên của proxy ghi một vết ghi (`--trace-out`). Thẩm định rồi đọc:

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate ha/trace-allow.json
```

<!-- guide: run expect="gate_evaluation_result" expect="ALLOW" expect="tool_call" -->
```bash
neuroedge trace show ha/trace-allow.json
```

Bạn sẽ thấy `tool_call` (nguồn `mcp`, tên tool, **tham số**), `gate_evaluation_result` (`ALLOW` hay `BLOCK`, và vì sao). Vết ghi **chứa tham số của lời gọi** như client gửi
(ví dụ tên thiết bị), không băm — coi nó là dữ liệu nhà bạn khi gửi cho chúng tôi (xem [`phan-hoi.md`](phan-hoi.md)).

## 5. Làm proxy thành đường duy nhất

Proxy chỉ canh con đường đi **qua nó**. Ai gọi thẳng HA vẫn không qua gate. `plugin doctor` báo những lối vòng nó thấy và nói rõ điều nó **không** kiểm được:

<!-- guide: run exit=1 expect="allow_lan_http đang bật" expect="đích còn tới được mà không qua proxy" expect="không kiểm được: plugin (TSK-I2c-11)" -->
```bash
neuroedge plugin doctor --config ha/guard.toml
```

Mã thoát `1` = có cảnh báo (ở đây luôn có: HA luôn tới được từ máy bạn). Việc cần làm thật, doctor không làm thay:

- **Token là chìa khoá.** Chỉ proxy được cầm token HA (của người dùng HA riêng). Claude Desktop, agent, script khác **không** cầm token đó — chúng chỉ nói chuyện với proxy. Máy khách nào có token HA là một lối vòng.
- **Mạng.** Nếu bạn kiểm soát được, chỉ cho máy chạy proxy (và thiết bị thật sự cần, như app điện thoại của HA) tới cổng HA; doctor không đọc tường lửa và không quét mạng.
- **Các ứng dụng khác trên máy** (Cursor, VS Code, script) có thể có mục MCP trỏ thẳng HA: tự rà.

## 6. Lỗi thường gặp (thông báo thật)

**Thiếu biến môi trường** — quên `export HA_AUTH`:

<!-- guide: run exit=1 expect="environment variable(s) ['HA_AUTH'] named in guard.toml are not set" expect="export HA_AUTH=" -->
```bash
env -u HA_AUTH neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

(Thông báo nói "named in guard.toml" dù lúc `init` chưa có tệp — nghĩa là biến bạn vừa nêu bằng `--header-env`.)

**Token sai hoặc hết hạn** — HA trả 401; proxy không cho biết mã, chỉ nói chung:

<!-- guide: run exit=1 expect="cannot connect to the real MCP server" expect="Server returned an error response" -->
```bash
HA_AUTH="Bearer sai-token" neuroedge guard init --mcp "$HA_MCP_URL" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

Cách tự kiểm: thử cùng token bằng `curl -i -H "Authorization: $HA_AUTH" "$HA_MCP_URL"` — `401` là token.

**http thuần tới máy trong nhà mà chưa bật cờ**:

<!-- guide: run exit=1 expect="plain http to another machine on the LAN sends the calls and the token in clear" expect="allow_lan_http = true" -->
```bash
neuroedge guard init --mcp "http://192.168.1.10:8123/api/mcp" --header-env Authorization=HA_AUTH --dir ha-loi
```

**http thuần tới máy ngoài mạng nhà** — cờ không cứu được, dùng https:

<!-- guide: run exit=1 expect="plain http to a host outside loopback and the home LAN would send the token in clear over the internet" -->
```bash
neuroedge guard init --mcp "http://ha.example.com/api/mcp" --header-env Authorization=HA_AUTH --allow-lan-http --dir ha-loi
```

**Proxy không khởi động khi HA tắt, sai địa chỉ hay thiếu biến** — nó không bao giờ "phục vụ phần còn lại":

<!-- guide: run exit=1 expect="environment variable(s) ['HA_AUTH'] named in guard.toml are not set" -->
```bash
env -u HA_AUTH neuroedge proxy mcp --config ha/guard.toml
```

**Mọi tool đều BLOCK sau khi bạn đã sửa gate** — gate chỉ nạp lúc proxy khởi động: thoát hẳn Claude Desktop (nó giữ tiến trình proxy cũ) rồi mở lại.

**Tên tool trong HA khác** — nếu `guard init` in "NOT exposed" cho tool bạn cần, tool đó có tham số bắt buộc không phải kiểu đơn giản; chưa phơi được ở bản này
(ghi vào phản hồi: tool nào, tham số nào).

## 7. Tiếp theo

Gửi phản hồi theo [`phan-hoi.md`](phan-hoi.md) (thời gian tới BLOCK đầu, tới ALLOW đầu có chủ ý, lỗi nguyên văn). Đã xong với HA? Hai hướng dẫn còn lại:
[`guard-python.md`](guard-python.md) (agent Python của bạn), [`proxy-http.md`](proxy-http.md) (API thiết bị cục bộ kiểu Tasmota).
