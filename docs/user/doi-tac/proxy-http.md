# Hướng dẫn 3 — API thiết bị cục bộ qua `neuroedge proxy http`

> **Mục tiêu:** đặt một gate trước API HTTP của một thiết bị trong nhà (kiểu Tasmota, Shelly, ESPHome, hay một dịch vụ REST bạn tự viết). Mỗi route bạn **khai** là
> một tool có gate; request chỉ được chuyển tới thiết bị **sau khi gate cho phép**; route không khai bị từ chối bằng 404 và không bao giờ tới thiết bị. **Thời gian:** ≤ 15 phút từ lúc đã cài wheel.
>
> Trạng thái kiểm: các lệnh dưới được [`scripts/partner_guides_check.sh`](../../../scripts/partner_guides_check.sh) chạy từ wheel trên một **bản giả** của API thiết bị
> ([`fixtures/http_upstream/`](../../../fixtures/http_upstream/server.py)): `GET /cm?cmnd=…` kiểu Tasmota và `POST /api/{lệnh}` kiểu REST. **Chưa kiểm trên thiết bị thật**:
> thiết bị của bạn có thể cần xác thực hay định dạng mà bản giả không có — hãy ghi vào [phản hồi](phan-hoi.md). Giới hạn: [`gioi-han.md`](gioi-han.md).

## 0. Bạn cần

- Đã cài wheel theo [README](README.md); `curl` (có sẵn trên macOS và Linux).
- Địa chỉ API của thiết bị, ví dụ `http://192.168.1.50` (Tasmota). Thiết bị nói http thuần trên mạng nhà thì cần cờ `--allow-lan-http` ở lệnh 1 (rủi ro: [`gioi-han.md`](gioi-han.md)).
- Cổng `8787` trên máy này còn trống (mặc định của proxy; đổi ở `listen` trong `guard.toml`).

<!-- guide: skip reason="đặt biến môi trường: script đã đặt sẵn DEVICE_URL trỏ vào bản giả" -->
```bash
export DEVICE_URL="http://192.168.1.50"
```

## 1. Lệnh tới giá trị đầu

**Lệnh 1 — khai route.** Mỗi `--route "PHƯƠNG-THỨC /đường/{tham_số}"` là một tool; lệnh viết `guard.toml` và một gate **chặn mặc định** cho mỗi route.
Ví dụ cho Tasmota (`GET /cm?cmnd=Power On`) và một API kiểu REST (`POST /api/{lệnh}`):

<!-- guide: run expect="2 tool(s) behind the Guard, all BLOCKED until you open their gate" expect="get_cm" expect="post_api_cmd" -->
```bash
neuroedge guard init --http "$DEVICE_URL" --route "GET /cm" --route "POST /api/{cmd}" --allow-lan-http --name plug --dir plug
```

Tham số của đường dẫn (`{cmd}`) được khai tự động. **Query và body thì bạn phải tự khai**, từng cái một — tham số không khai bị từ chối (400). Tasmota nhận lệnh ở query `cmnd`,
nên khai nó; còn API REST nhận số trong body JSON:

<!-- guide: run -->
```bash
cat >> plug/guard.toml <<'TOML'

[tools.get_cm.parameters.cmnd]
type = "string"

[tools.post_api_cmd.parameters.value]
type = "integer"
required = false
TOML
```

**Lệnh 2 — chạy proxy** (giữ cửa sổ này mở; **Ctrl-C** để dừng, proxy ghi vết ghi khi thoát):

<!-- guide: run bg=proxy wait="127.0.0.1:8787" -->
```bash
neuroedge proxy http --config plug/guard.toml --trace-out plug/trace-1.json
```

Proxy chỉ nghe ở `127.0.0.1` (không nghe địa chỉ nào khác: nó chưa có xác thực ở phía trước). Từ giờ ứng dụng/agent của bạn gọi `http://127.0.0.1:8787` thay cho `$DEVICE_URL`.

**Lệnh 3 — một request thử** (cửa sổ khác). Bật thiết bị qua proxy:

<!-- guide: run expect="HTTP 403" expect='"status": "BLOCK"' expect='"reason": "criterion_unavailable"' expect='"failed_criterion": "operator_approved"' log_lacks="DEVICE_LOG|Power" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

## 2. Thấy BLOCK

`HTTP 403` với `BLOCK` + `criterion_unavailable`: gate chạy đúng. Nó đòi `operator_approved` mà không ai đặt, nên **thiết bị không nhận gì** (script kiểm: nhật ký của thiết bị giả không có lệnh nào).
Mã HTTP của proxy: **403** = gate chặn; **400** = request sai (tham số không khai, JSON hỏng, tham số lặp) và không tới gate hay thiết bị; **404** = route không khai báo; **413** = body > 1 MiB;
**502** = gate cho phép nhưng thiết bị hỏng — và proxy **không thử lại** (lời gọi có thể đã xảy ra).

Một route không khai báo thì không bao giờ qua, dù gate nào:

<!-- guide: run expect="HTTP 404" expect="only declared routes pass" expect="nothing was forwarded" log_lacks="DEVICE_LOG|admin" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8787/admin
```

## 3. Mở gate có chủ ý rồi thấy ALLOW

Dừng proxy trước (gate chỉ được nạp lúc khởi động):

<!-- guide: stop=proxy -->
```text
Ctrl-C ở cửa sổ đang chạy `neuroedge proxy http`
```

Mở gate của route `GET /cm` — `plug/gates/get_cm@1.0.0.yaml`, đầu tệp có hướng dẫn. Cách nhanh nhất là xoá tiêu chí `operator_approved` ở hai chỗ, hoặc sửa bằng trình soạn thảo:

<!-- guide: run -->
```bash
f="plug/gates/get_cm@1.0.0.yaml"
awk '/^  operator_approved:/ {skip=1; next} skip && /^    / {next} {skip=0; print}' "$f" > "$f.new" && mv "$f.new" "$f"
```

**Nguồn là `bridge:http`, không phải `mcp`.** HTTP không có nguồn dựng sẵn (thêm một nguồn là đổi lược đồ, cần RFC), nên proxy chạy như một *bridge của lõi*: mọi request của nó
có `call_source = bridge:http`. Gate **phải liệt kê nó** — gate chỉ liệt kê `mcp` chặn mọi request HTTP. Gate sinh ra đã làm đúng việc này:

<!-- guide: run expect='in: ["bridge:http"]' -->
```bash
grep -n 'bridge:http' plug/gates/get_cm@1.0.0.yaml
```

Chạy lại proxy rồi gọi lại:

<!-- guide: run bg=proxy wait="127.0.0.1:8787" -->
```bash
neuroedge proxy http --config plug/guard.toml --trace-out plug/trace-2.json
```

<!-- guide: run expect="HTTP 200" expect='"POWER": "ON"' log_has="DEVICE_LOG|/cm?cmnd=Power%20On" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

Lần này request qua gate và **mới** tới thiết bị, nguyên văn (cùng method, đường dẫn và query như bạn gửi). Route kia vẫn bị chặn:

<!-- guide: run expect="HTTP 403" log_lacks="DEVICE_LOG|/api/" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{"value": 1}' http://127.0.0.1:8787/api/relay
```

Tham số lạ hay lặp là lỗi của request, bị từ chối trước khi tới thiết bị:

<!-- guide: run expect="HTTP 400" expect="unknown argument 'x'" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power&x=1"
```

<!-- guide: run expect="HTTP 400" expect="a query parameter is given twice" -->
```bash
curl -s -w '\nHTTP %{http_code}\n' "http://127.0.0.1:8787/cm?cmnd=Power&cmnd=Power"
```

Thông tin đăng nhập của client **không bao giờ** được chuyển cho thiết bị (proxy chỉ gửi header bạn khai ở `headers_env`):

<!-- guide: run expect="HTTP 200" log_lacks="DEVICE_LOG|Bearer cua-client" -->
```bash
CLIENT_AUTH='Bearer cua-client'
curl -s -w '\nHTTP %{http_code}\n' -H "Authorization: $CLIENT_AUTH" "http://127.0.0.1:8787/cm?cmnd=Power%20On"
```

Thiết bị cần mật khẩu qua header (ví dụ `Authorization`)? Khai tên header và **tên biến môi trường** chứa giá trị — không bao giờ giá trị — rồi `export` biến đó:

<!-- guide: skip reason="ví dụ cấu hình; thiết bị giả không đòi xác thực" -->
```toml
[proxy.http]
headers_env = { Authorization = "DEVICE_AUTH" }
```

## 4. Đọc vết ghi

<!-- guide: stop=proxy -->
```text
Ctrl-C ở cửa sổ đang chạy `neuroedge proxy http` — proxy ghi vết ghi khi thoát
```

<!-- guide: run expect="VALID" -->
```bash
neuroedge trace validate plug/trace-2.json
```

<!-- guide: run expect="gate_evaluation_result" expect="bridge:http" expect="tool_call" -->
```bash
neuroedge trace show plug/trace-2.json
```

Mỗi request tới được gate là một `tool_call` với nguồn `bridge:http` và **tham số** (đường dẫn, query, scalar của body) — không băm. Request bị 400/404 chặn từ đầu thì không có `tool_call`
(chưa tới gate). Coi vết ghi là dữ liệu nhà bạn khi gửi cho chúng tôi ([`phan-hoi.md`](phan-hoi.md)).

## 5. Làm proxy thành đường duy nhất

Proxy canh con đường đi **qua nó**; thiết bị vẫn nghe ở địa chỉ gốc. `plugin doctor` thử nối thẳng tới thiết bị và nói rõ điều nó không kiểm được:

<!-- guide: run exit=1 expect="đích còn tới được mà không qua proxy" expect="tường lửa" expect="allow_lan_http đang bật" expect="không kiểm được: plugin (TSK-I2c-11)" -->
```bash
neuroedge plugin doctor --config plug/guard.toml
```

Với một API cục bộ, doctor **luôn** cảnh báo (mã thoát `1`): thiết bị luôn tới được từ máy bạn. Việc thật sự phải làm là của bạn, chúng tôi không làm thay:

- Đặt API của thiết bị sau tường lửa/ACL của router, hoặc cấu hình thiết bị chỉ nhận từ địa chỉ của máy chạy proxy. Ứng dụng/agent nào còn tới được `http://192.168.1.50` là lối vòng.
- Đừng bind proxy ra ngoài loopback để "tiện": nó không có xác thực phía trước và sẽ từ chối khởi động nếu `listen` không phải loopback.
- Thiết bị có token/mật khẩu: chỉ proxy được biết nó.

## 6. Lỗi thường gặp (thông báo thật)

**`listen` không phải loopback**:

<!-- guide: run exit=1 expect="the proxy listens on loopback only" expect="use 127.0.0.1" -->
```bash
sed 's/127.0.0.1:8787/0.0.0.0:8787/' plug/guard.toml > plug/loi-listen.toml && neuroedge proxy http --config plug/loi-listen.toml
```

**Thiết bị tắt hoặc sai địa chỉ** — proxy không khởi động:

<!-- guide: run exit=1 expect="cannot reach the real API" -->
```bash
sed 's#^upstream = .*#upstream = "http://127.0.0.1:9"#' plug/guard.toml > plug/loi-tat.toml && neuroedge proxy http --config plug/loi-tat.toml
```

**http thuần tới thiết bị trong nhà mà chưa bật cờ**:

<!-- guide: run exit=1 expect="plain http to another machine on the LAN sends the calls and the token in clear" expect="allow_lan_http = true" -->
```bash
neuroedge guard init --http "http://192.168.1.50" --route "GET /cm" --dir plug-loi
```

**http thuần tới địa chỉ ngoài mạng nhà** — cờ không cứu được:

<!-- guide: run exit=1 expect="plain http to a host outside loopback and the home LAN would send the token in clear over the internet" -->
```bash
neuroedge guard init --http "http://thiet-bi.example.com" --route "GET /cm" --allow-lan-http --dir plug-loi
```

**Đường dẫn hay phương thức sai ở `--route`**:

<!-- guide: run exit=1 expect="not `METHOD /path`" -->
```bash
neuroedge guard init --http "http://127.0.0.1:1" --route "cm" --dir plug-loi
```

**Mọi request đều 403 sau khi bạn đã sửa gate** — gate chỉ nạp lúc proxy khởi động: dừng và chạy lại proxy. Nếu vẫn 403, xem `reason` trong phản hồi: `criterion_unavailable` là dữ kiện không ai đặt,
`condition_not_met` là điều kiện của gate không thoả; và kiểm gate có liệt kê `bridge:http` (xem §3).

**`Address already in use` khi chạy proxy** — cổng `8787` đang có tiến trình khác dùng. Đổi `listen = "127.0.0.1:8787"` trong `plug/guard.toml` sang cổng trống, hoặc tắt tiến trình kia.
(Ở bản này lỗi này hiện thành một traceback dài thay vì một thông báo ngắn; chúng tôi đã ghi nhận.)

## 7. Tiếp theo

Gửi phản hồi theo [`phan-hoi.md`](phan-hoi.md). Hai hướng dẫn kia: [`home-assistant-mcp.md`](home-assistant-mcp.md), [`guard-python.md`](guard-python.md).
