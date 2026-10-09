# Lõi an toàn dùng độc lập và Extension SDK — `neuroedge.guard`, `neuroedge.sdk`

**Trạng thái:** chuẩn tắc cho phần đã hiện thực (TSK-I2c-07, TSK-I2c-14, TSK-I2c-16 phần lõi); phần còn lại ghi rõ "chưa có". Nền: [RFC-0016](../rfc/0016-loi-tach-duoc-va-extension-sdk.md)
(§3b, §3c, §3d, §3e, §3g), [RFC-0017](../rfc/0017-nguon-goi-theo-khong-gian-ten.md) (nguồn `bridge:<id>`), [RFC-0018](../rfc/0018-co-cau-chap-hanh-tu-xa.md) (cơ cấu chấp hành từ xa).
**Mã nguồn:** `python/neuroedge/guard.py`, `python/neuroedge/sdk/__init__.py`, `python/neuroedge/sim/hal_build.py`, `python/neuroedge/plugins/` (bộ nạp, khai báo `[actuators]`, `conformance`), `python/neuroedge/hal/remote.py`.
**Test ghim:** `python/tests/test_guard.py`, `python/tests/test_sdk_api.py`, `python/tests/test_plugins.py`, `python/tests/test_remote_actuator*.py`, `python/tests/test_conformance.py`.
Tài liệu này là nơi **duy nhất** định nghĩa cú pháp `guard.toml` và văn phạm `drive`; chỗ khác dẫn tới đây. Mức hứa của hai mô-đun: `python_api.md` §1.

## 1. `neuroedge.guard`

Một chương trình bất kỳ (proxy MCP, cầu nối, node ROS) có gate → token → phong bì → vết ghi mà không cần `agent.toml`, `@action` hay `SimSession`.
Ví dụ chạy được: [`examples/guard/`](../../examples/guard/) (`guard.toml` + `run.py`; `test_the_guard_example_runs_and_writes_a_valid_trace`).

```python
from neuroedge.guard import Guard
from neuroedge.sdk import ToolRequest

async with Guard.load("guard.toml") as guard:      # thoát ⇒ thả chân, như SimSession.close()
    bridge = guard.dispatcher("ros_node")           # đăng ký `bridge:ros_node`; không nêu nguồn khác được
    guard.set_fact("badge_ok", True)                # ngữ cảnh gate của chương trình chủ, như `c.facts`
    outcome = await bridge.dispatch(ToolRequest("lamp_on", {"seconds": 3}))
    outcome.status, outcome.content                 # "ALLOW" | "BLOCK" | "REJECTED"; `ToolResult.content()`
    trace = guard.trace()                           # trace.v1 đã thẩm định
```

- **Một đường tới chân.** `Guard` dựng `ActionContractEngine`, sổ token, HAL cùng phong bì của bo (hàm dựng chung với `SimSession`: `sim/hal_build.py`) và một
  `Conversation` nội bộ **có sổ action riêng** (không đụng `REGISTRY` toàn cục của `@action`), rồi gọi đúng `dispatch()` (`tool_calling.md` §2).
  Mỗi `Tool` là một `ActionSpec` khai bằng dữ liệu; `threat_model.md` §1–§2b áp nguyên.
- **ALLOW là phán quyết; nếu `Tool` có thân thì là một lần chạy dưới token.** Thân là `run` (hàm Python, đồng bộ hay `async`, nhận tham số đã kiểm, đã điền mặc định) **hoặc**
  `drive` (§3), không cả hai; không có thân thì ALLOW chỉ là phán quyết. Chân chỉ nhúc nhích trong thân, dưới token một lần và phong bì của bo; thân không động tới được chân không khai ở `requires`.
- **Gate phân giải lúc nạp.** Mỗi `Tool` có một gate (đường dẫn tệp hoặc `neuroedge://…`) được phân giải đủ (kế thừa, đủ bất biến `CHANGELOG.md` §3.3 #1) **trước** khi dựng HAL; gate không
  phân giải được ⇒ không nạp, chưa chân nào bị giữ. Gate biến mất lúc chạy ⇒ `BLOCK`, `gate_not_found`. Không có công tắc fail-open, không nhận `ResolvedGate` dựng tay.
- **Nguồn và id.** Người gọi **không** nêu `source`: `guard.dispatcher(id)` (mẫu `[a-z][a-z0-9_]{0,31}`) đăng ký `bridge:<id>` bằng `Conversation.register_source` (RFC-0017 §3b); id sai văn phạm
  hoặc trùng ⇒ `ToolCallError` (NE1004). `ToolRequest` không có trường `source`, và `Dispatcher.dispatch` từ chối một `ToolCall`. Nguồn `test` chỉ qua `Guard(..., testing=True).testing_dispatcher()`.
  Gate đọc nguồn qua `call_source` / `call_channel` (`tool_calling.md` §5).
- **Tuần tự hoá.** Mọi `Dispatcher.dispatch` của một `Guard` chạy dưới **một** `asyncio.Lock`. Không phải vì nguồn: `call_source` thuộc về từng lời gọi (`Conversation.do_with`) nên hai lời gọi chồng nhau
  không thấy nguồn của nhau (`test_two_concurrent_dispatches_never_share_a_call_source`). Mà vì vết ghi: hai lời gọi đang chạy xen kẽ sự kiện, một lệnh chân sau phán quyết của A rơi sau yêu cầu của B, và replay đọc vết ghi
  như một chuỗi bước (`test_concurrent_dispatches_are_recorded_one_after_another_and_replay`). Hệ quả cần biết: một thân `run` chậm (chuyển tiếp qua mạng) giữ các bridge khác đợi.
- **Vết ghi và replay.** `guard.trace()` = `EventLog.to_trace()` + `validate_trace`; `metadata.agent_version = "guard:<name>@<phiên bản neuroedge>"`, `board_id = "none"` khi không có bo.
  `TracePlayer(trace, guard="guard.toml")` replay vết đó bằng bảng `Tool` (không cho cả `agent=` lẫn `guard=`): `test_a_guard_trace_replays_to_the_same_verdicts`.
  Thân `run` bằng mã Python không nằm trong `guard.toml`, nên replay chạy thân `drive` và chỉ phán quyết cho phần còn lại.
- **Một Guard một tiến trình**, sổ token trong bộ nhớ (RFC-0016 §3b mục 7). Không có bo ⇒ không HAL: `Tool` có `requires` bị từ chối lúc nạp (`BoardCapabilityError`), và thân gọi `digital.out` bị từ chối.
- **Cố ý không làm:** không sandbox và không chặn mạng (canh con đường đi qua nó, không ngăn ai gọi thẳng đích); không `agent.toml`, ngữ pháp, mô hình, thoại, UI, MCP server; không đường xác nhận
  bằng người (`on_block: ask` hiện ra là `BLOCK` kèm câu hỏi trong `outcome.content`); không chống mã cùng tiến trình (`threat_model.md` §3). `Guard` không nằm trong `neuroedge.__all__`.

Hàm khởi tạo `Guard(tools, *, name, board, target, registry_root, base, events, testing, hal_options, source, actuators, plugins)`: `board` là id của một bo (hoặc `None`); `target` là `sim` hoặc `linux`, mặc định theo bo
(`esp32s3` không có Guard Python — MCU dùng `ne_gate` + `NETR`). Gate nằm ở từng `Tool`, nên hàm không có tham số `gates=` riêng của RFC-0016 §3b (ví dụ ở đó); gate `fallback_action` là một `Tool` khác.
`actuators` là các `ActuatorDeclaration` dựng bằng mã và `plugins` là danh sách bản phân phối bật cho chúng (như `[plugins] enable`): chúng đi qua **cùng** `check_actuators` với khai báo trong tệp (§7), trước khi chân nào bị giữ.

## 2. `neuroedge.sdk`

Phần mà `guard` và plugin cơ cấu chấp hành cần của Extension SDK:

| Tên | Là gì |
|:---|:---|
| `ToolRequest(name, arguments={}, id="")` | `tool-call.v1#/$defs/request`: **không có `source`**; bất biến |
| `Outcome(status, content)` | Dữ liệu thuần: `status` và `ToolResult.content()` (hợp lệ theo `tool-result.v1`), không mang giá trị mà thân action trả về |
| `SDK_VERSION = (1, 0)` | Bộ `(MAJOR, MINOR)` riêng, không phải `__version__` của gói |
| `Actuator` | Protocol của plugin nhóm `neuroedge.actuators`; chữ ký là của RFC-0018 §3c (nguồn duy nhất), SDK chỉ xuất lại: `safe_off_level`, `readback`, `tolerance_ms`, `command_timeout_ms`, `max_lease_ms`, `apply(command)`, `safe_off()`, `read_state()`, `probe()` |
| `Command(id, operation, duration_ms=None, lease_ms=None)` | Lệnh HAL giao cho plugin sau khi đã cho qua: `operation` là `"on"` hoặc `"renew"`; `duration_ms` luôn có ở L2, `lease_ms` ở L3; là **khoảng**, không bao giờ là mốc. `id` duy nhất cho mỗi lệnh (thiết bị nhận ra lệnh trùng, gia hạn đến muộn) |
| `DeviceDouble` | Protocol của bản giả thiết bị mà `probe()` trả: `state()`, `cut_link()`, `heal_link()`, `advance(ms)` |
| `ActuatorError` và `NotSent`, `Rejected`, `Ambiguous`, `ReadFailed` | Plugin tự phân loại lỗi gửi (chắc chắn chưa tới · bị từ chối rõ · không biết đã tới hay chưa) và lỗi đọc; không phải mã `NE…` |

`__all__` của nó là `["SDK_VERSION", "Actuator", "ActuatorError", "Ambiguous", "Command", "DeviceDouble", "NotSent", "Outcome", "ReadFailed", "Rejected", "ToolRequest"]`; không tên HAL, không `Guard`, không `Conversation`, không tên nào của `neuroedge.__all__` (`test_the_sdk_exports_no_hal_name_and_no_name_of_all`), và chỉ import `errors` của lõi.
Plugin khai `sdk_requires = (MAJOR, MINOR)` ở mô-đun của entry point (§6). **Chưa có (TSK-I2c-11/12):** `Protocol` cho bridge, fact source, exporter; bộ nạp và tuân thủ cho các loại đó. Cam kết ổn định đầy đủ: RFC-0016 §3e.

## 3. `guard.toml`

Tập con của `agent.toml`. Khoá lạ, trường mang tên bí mật viết thẳng (`api_key`, `token`, …; chỉ tên biến môi trường `*_env`) và mọi thứ chưa hiện thực ⇒ `AgentManifestError` (NE3002), ba phần,
**không bao giờ bỏ qua lặng lẽ** — thứ chưa có thì lỗi nêu tên task sẽ làm nó.

```toml
[guard]
name  = "door-proxy"              # bắt buộc; ⇒ metadata.agent_version = "guard:door-proxy@<version>"
board = "sim-default"             # id một bo của boards/; vắng ⇒ không HAL, chỉ phán quyết

[registry]
roots = ["gates"]                 # một thư mục (tương đối so với guard.toml) cho `neuroedge://`; nhiều gốc: TSK-I2c-08

[tools.lamp_on]                   # tên: [a-z][a-z0-9_]{0,63}
gate     = "gates/lamp_on@1.0.0.yaml"          # tệp (tương đối so với guard.toml) hoặc neuroedge://…
requires = ["digital.out:porch_light"]         # chỉ `digital.out:<chân>`; cần board; chân phải có trên board
drive    = [{ pin = "porch_light", operation = "pulse", seconds_from = "seconds" }]

[tools.lamp_on.parameters.seconds]             # tham số không khai ⇒ REJECTED
type    = "integer"               # string | integer | number | boolean
default = 5                       # tuỳ chọn, đúng kiểu; có mặc định ⇒ tham số tuỳ chọn
```

| Bảng | Khoá | Ghi chú |
|:---|:---|:---|
| `[guard]` | `name`, `board` | `board` là đường dẫn hay `pkg:…` ⇒ từ chối, nêu TSK-I2c-08 |
| `[registry]` | `roots` | hơn một gốc ⇒ từ chối, nêu TSK-I2c-08 |
| `[tools.<tên>]` | `gate`, `requires`, `drive`, `parameters` | |
| `[tools.<tên>.parameters.<p>]` | `type`, `default`, `description`, `required` | giới hạn giá trị là của `arguments` trong gate (RFC-0005), không ở đây. Không có `default` và không có `required = false` ⇒ tham số bắt buộc; `required = false` không `default` ⇒ tham số tuỳ chọn mà `run` không nhận nếu người gọi không đưa |
| `[proxy.mcp]` | `command` hoặc `url`, `env_from`, `headers_env`, `names` | chỉ do `proxy mcp` và `plugin doctor` đọc (§4); `Guard` bỏ qua |
| `[proxy.http]` | `upstream`, `listen`, `id`, `headers_env`, `[[routes]]` (`method`, `path`, `tool`) | chỉ do `proxy http` và `plugin doctor` đọc (§5); đúng một trong `[proxy.mcp]` / `[proxy.http]` mỗi tệp |
| `[plugins]` | `enable`, `config` | §6; chỉ loại actuator nạp được, bản phân phối mang loại khác ⇒ từ chối, nêu TSK-I2c-11 |
| `[actuators.<tên>]` | `plugin`, `safe_off`, `reversible`, `envelope`, `config` | §7; cùng khai báo và cùng hàm kiểm với `agent.toml`. Tool tới nó bằng `requires = ["digital.out:<tên>"]`: chiều "khai mà không ai dùng" của luật hai chiều xét trên `requires` của các tool |
| `[external]` | — | từ chối, nêu TSK-I2c-09 |

### Văn phạm `drive`

`drive` là danh sách bước, chạy lần lượt trong thân của tool, dưới token. Mỗi bước là một bảng:

| Khoá | Ý nghĩa |
|:---|:---|
| `pin` | tên chân; **phải** có trong `requires` (`digital.out:<pin>`) |
| `operation` | `on`, `off` hoặc `pulse` |
| `seconds_from` | chỉ với `pulse`, **bắt buộc** ở đó: tên một tham số đã khai, kiểu `integer` hoặc `number`; độ dài xung (giây) lấy từ tham số này |

Guard dựng bước thành `digital.out(pin).on()`, `.off()` hay `.pulse(seconds=<tham số>)`. Giá trị ngoài giới hạn là việc của gate (`argument_out_of_range`) và của phong bì của bo.
Không có gì khác trong `drive`: cơ cấu từ xa là chân `digital.out` có tên (§7), nên `{ pin = "garden_valve", operation = "pulse", … }` tới nó qua cùng đường. Muốn thân tuỳ ý, dùng `Tool(run=…)` trong Python.

## 4. `neuroedge proxy mcp` — một máy chủ MCP có sẵn đứng sau NeuroEdge (TSK-I2c-14, FR-EXT-06)

Ba lệnh trên máy sạch: `pip install 'neuroedge[mcp]'`, rồi `neuroedge guard init --mcp "<lệnh hoặc https://…>"`, rồi `neuroedge proxy mcp`
(`test_three_commands_put_a_server_behind_the_proxy`, qua một MCP client thật). Mọi `tools/call` đi qua `Guard` (gate → token → phong bì → vết ghi) và
chỉ được **chuyển tiếp tới máy chủ thật bên trong `run` của tool**, tức là sau ALLOW: không có đoạn "nếu ALLOW thì chuyển tiếp" nào để viết sai.

### 4.1 Bảng `[proxy.mcp]`

```toml
[proxy.mcp]
command  = ["python", "my_server.py"]       # stdio; HOẶC  url = "https://ha.local/mcp"  (Streamable HTTP) — đúng một trong hai
env_from = ["HA_TOKEN"]                      # (stdio) tên biến môi trường chuyển cho tiến trình con — chỉ TÊN
headers_env = { Authorization = "HA_TOKEN" } # (url) tên header → TÊN biến môi trường; không bao giờ giá trị
[proxy.mcp.names]                            # tên tool của guard → tên tool của máy chủ thật, khi khác nhau
get_state = "get-state"                      # tên tool của guard là [a-z][a-z0-9_]{0,63}; MCP cho phép `-`, `.`, chữ hoa
```

Giá trị bí mật viết thẳng bị từ chối (NE3002) và không bao giờ được in lại: khoá mang tên bí mật, đối số `command` giống khoá API, URL có thông tin đăng nhập hay tham số truy vấn mang tên bí mật,
giá trị `headers_env` không phải tên biến. `http://` chỉ nhận cho `localhost`/`127.0.0.1`/`::1` (token không đi rõ ràng qua mạng) — trừ khi bật `allow_lan_http` (§4.1a). Biến môi trường được nêu mà vắng trong shell ⇒ không kết nối.
### 4.1a `allow_lan_http` — http thuần tới thiết bị trên mạng nhà (và cho cả `proxy http`, §5.1)

Thiết bị thật (Home Assistant `http://192.168.1.10:8123/api/mcp`, Tasmota, Shelly) thường chỉ nói http thuần trên LAN. Khoá `allow_lan_http = true` ở `[proxy.mcp]` (cần `url`) và `[proxy.http]` là **lối vào có chủ ý**, mặc định tắt (tắt ⇒ hành vi không đổi: http chỉ tới loopback).
Khi bật, http thuần chỉ được nhận cho `host` là:

- literal IP riêng/link-local/loopback: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `127.0.0.0/8`; IPv6 `fc00::/7`, `fe80::/10`, `::1`;
- hoặc tên `*.local`, `*.lan`, `*.home.arpa` (có ít nhất một nhãn trước hậu tố).

**Mọi host khác vẫn bị từ chối dù bật cờ:** tên hay địa chỉ công khai, dải CGNAT `100.64.0.0/10` (cố ý từ chối), IPv6 documentation/`fec0::/10`, địa chỉ IPv4-mapped IPv6, tên trần (`homeassistant`) — token không bao giờ đi rõ ràng qua internet
(`test_any_other_host_stays_refused_even_with_the_flag`). Thông tin đăng nhập trong URL vẫn bị từ chối. `listen` của `proxy http` vẫn chỉ loopback (cờ này không đụng tới front).
`guard init --mcp|--http … --allow-lan-http` ghi khoá kèm chú thích; `plugin doctor` in **CẢNH BÁO** khi khoá bật: lời gọi và token đi bằng http thuần trên LAN, ai nghe được mạng nhà đọc và chép được token.
Nếu thiết bị hỗ trợ https thì dùng https; cờ này là cái giá của một thiết bị không có.

Tool của proxy không giữ chân (`requires`, `drive` bị từ chối): nó chuyển tiếp một lời gọi.

### 4.2 `guard init --mcp`

`neuroedge guard init --mcp <lệnh|url> [--dir DIR] [--name TÊN] [--env-from TÊN]… [--header-env HEADER=BIẾN]…` kết nối như một MCP client, liệt kê tool của máy chủ, rồi viết `guard.toml` và một gate cho mỗi tool ở `gates/`:

- **Gate sinh ra chặn mặc định.** Gate khai `call_source` với `options` tường minh (nguồn của client phía trước proxy là `mcp`) **và** một tiêu chí không ai đặt (`operator_approved`, `allow_when: operator_approved: true`)
  nên tool `BLOCK` với `criterion_unavailable` cho tới khi người vận hành sửa gate **có chủ ý**; đầu mỗi tệp ghi cách mở (`test_a_generated_gate_blocks_until_the_operator_opens_it`).
- **Tham số.** Thuộc tính vô hướng của `inputSchema` (`string`, `integer`, `number`, `boolean`; kể cả `Optional[…]`) thành `[tools.X.parameters]`; có mặc định thì ghi `default`, tuỳ chọn không mặc định thì `required = false`.
  Tool có tham số **bắt buộc** không phải vô hướng **không được phơi ra**: ghi thành một khối chú thích có lý do và in ở stderr (`test_a_tool_with_a_required_object_parameter_is_not_exposed`); tham số tuỳ chọn không phải vô hướng bị bỏ, có ghi chú.
- Tên tool của máy chủ không hợp lệ cho guard (`get-state`) được đổi (`get_state`) và ghi vào `[proxy.mcp.names]`. Đối số của `--mcp` là tệp có thật thì được viết đường dẫn tuyệt đối.
- **Không bao giờ ghi đè**: nếu bất kỳ tệp nào sẽ viết đã có ⇒ lỗi ba phần, không ghi gì cả (`test_guard_init_never_overwrites_a_file`). Các tệp sinh ra được nạp thử (`Guard.load`, phân giải gate) trong bản sao **trước khi** ghi, nên `guard init` không bao giờ để lại cấu hình không nạp được.

### 4.3 `proxy mcp`

`neuroedge proxy mcp [--config guard.toml] [--trace-out PATH]` phục vụ **chỉ qua stdio** (`--http` là TSK-I2c-15, chưa có) đúng các tool của `guard.toml`, mô tả lấy từ máy chủ thật. Khi khởi động nó kết nối tới máy chủ thật và kiểm từng tool của guard:
tool phải có mặt ở đó (theo `[proxy.mcp.names]`), mỗi tham số khai phải có cùng kiểu, và mọi tham số bắt buộc của máy chủ thật phải được khai. **Thiếu một tool, lệch lược đồ hay không kết nối được ⇒ không khởi động** (mã thoát 1, lỗi ba phần), không bao giờ "phục vụ phần còn lại".

- **Nguồn.** Lời gọi giữ nguồn của client phía trước, `mcp`, qua đường nội bộ `Guard._dispatch_front` (RFC-0016 §3b mục 4): không `Dispatcher` nào chạm tới, nên một bridge chỉ có thể là `bridge:<id>` (`test_a_bridge_cannot_obtain_the_front_source`).
- **Kết quả.** ALLOW ⇒ nguyên văn kết quả của máy chủ thật. BLOCK ⇒ phán quyết (JSON, `isError` = false); REJECTED ⇒ phán quyết, `isError` = true — như `mcp serve`.
- **Máy chủ thật hỏng sau ALLOW** ⇒ kết quả lỗi (`status = ALLOW`, `isError` = true, "was not retried"); **không bao giờ thử lại**, vì lời gọi có thể đã xảy ra (`test_an_upstream_error_after_allow_is_an_error_result_not_a_retry`).
- **Vết ghi.** `--trace-out` ghi `guard.trace()` khi thoát (kể cả SIGTERM); `metadata.proxy = {kind, upstream}` — không có đối số lệnh hay URL truy vấn. Vết có **đối số của lời gọi** như nhận từ client (không băm): coi nó như dữ liệu của máy chủ thật. Replay: `TracePlayer(trace, guard="guard.toml")`, không bao giờ chạm máy chủ thật (`test_the_proxy_trace_validates_and_replays`).
- **Claude Desktop.** `neuroedge proxy mcp --desktop-config [--write] [--config-path P] [--name N]` in (hay ghi, kèm bản sao lưu, đúng một mục `mcpServers`) lối vào để Desktop chạy proxy. Desktop khởi chạy với môi trường tối thiểu: các biến trong `env_from`/`headers_env` phải được thêm vào khối `env` của mục đó **bằng tay** (lệnh nhắc, và không ghi bí mật vào tệp).
- Chưa có: front qua mạng (cho MCP: TSK-I2c-15 chỉ làm `proxy http` cho API HTTP, §5), `--init-timeout` như `mcp serve`, gate đọc dữ kiện của chính máy chủ thật.

### 4.4 `plugin doctor` — "proxy là đường duy nhất" chỉ kiểm được một phần

`neuroedge plugin doctor [--config guard.toml] [--json]` (RFC-0016 §3d mục 6, §5 rủi ro 3, 8). Nó **cảnh báo** những gì nó thấy và **nói rõ** những gì nó không kiểm được; không bao giờ in một chữ "OK" trơn:

| Kiểm | Kết quả |
|:---|:---|
| `url`: thử nối TCP thẳng tới đích (2 giây) | nối được ⇒ **CẢNH BÁO** "đích còn tới được mà không qua proxy"; không nối được ⇒ "không kiểm được" (máy khác chưa biết) |
| stdio: đọc cấu hình Claude Desktop (`mcp_desktop.default_config_path`) | mục khác (không phải proxy) khởi chạy cùng lệnh ⇒ **CẢNH BÁO**; không đọc được cấu hình ⇒ "không kiểm được"; luôn kèm "không kiểm được: ứng dụng khác (Cursor, VS Code, shell…)" |
| mỗi tool: gate có đọc `call_source` hoặc `call_channel` không | không ⇒ **CẢNH BÁO** (RFC-0016 §5 rủi ro 8) |
| plugin | nạp các bản phân phối của `[plugins] enable` như Guard: nạp hỏng ⇒ **CẢNH BÁO**; cài editable ⇒ **CẢNH BÁO** (không băm tệp, không huy hiệu); còn lại ghi chú bản phân phối, phiên bản, `files_sha256`. Luôn kèm "không kiểm được: plugin (TSK-I2c-11) loại …": loại khác actuator, và mức tự tắt (chỉ `conformance` chứng minh, trên bản giả) |

Mã thoát: `1` nếu có ít nhất một cảnh báo, `0` nếu không (các dòng "không kiểm được" không đổi mã thoát — chúng không phải bằng chứng). `0` **không** nghĩa là proxy là đường duy nhất: nó chỉ nghĩa là doctor không thấy lối vòng.
Tin đúng hơn: đặt máy chủ thật sau tường lửa/ACL để chỉ proxy tới được; doctor không làm việc đó.

## 5. `neuroedge proxy http` — một API HTTP cục bộ có sẵn đứng sau NeuroEdge (TSK-I2c-15, FR-EXT-06)

Cho API web của Tasmota/Shelly/ESPHome, một dịch vụ REST tự viết, REST của Home Assistant. Mỗi **route khai báo** là một tool của `Guard`; request chỉ được chuyển tới API thật **bên trong `run` của tool**, tức là sau ALLOW; mọi thứ
không khai báo bị từ chối bằng 404 và không bao giờ được chuyển tiếp. Hình dạng và độ chặt như `proxy mcp` (§4): `guard init --http` → sửa gate có chủ ý → `proxy http`.

### 5.1 Bảng `[proxy.http]`

```toml
[proxy.http]
upstream = "http://127.0.0.1:8080"   # http chỉ tới loopback (hoặc LAN với allow_lan_http, §4.1a); https tới đâu cũng được; không thông tin đăng nhập/truy vấn/fragment
allow_lan_http = false               # mặc định tắt; true: nhận http thuần tới IP riêng / *.local / *.lan / *.home.arpa (§4.1a)
listen   = "127.0.0.1:8787"          # CHỈ loopback (127.0.0.0/8, ::1, localhost): front không có xác thực ở bản này
id       = "http"                    # id bridge ⇒ nguồn `bridge:http`
headers_env = { Authorization = "DEVICE_TOKEN" }   # tên header → TÊN biến môi trường; không bao giờ giá trị

[[proxy.http.routes]]
method = "POST"                      # GET | POST | PUT | PATCH | DELETE
path   = "/cm/{cmd}"                 # `{tham_số}` là cả một đoạn; không `..`, không `%`, không query
tool   = "post_cm_cmd"               # một [tools.<tên>] của cùng tệp
```

Kiểm lúc nạp (NE3002, ba phần): địa chỉ `listen` không phải loopback; `upstream` http tới máy khác; bí mật viết thẳng (khoá mang tên bí mật, giá trị `headers_env` không phải tên biến — không bao giờ in lại);
route trùng (không kể tên tham số); tool không có; mỗi `{tham_số}` phải là tham số mà tool khai (nếu không mọi request sẽ `REJECTED`); tool không có route nào; cả `[proxy.mcp]` lẫn `[proxy.http]`.
Không kết nối được tới `upstream` hoặc biến môi trường vắng ⇒ không khởi động.

### 5.2 Nguồn là `bridge:<id>`

HTTP không có nguồn dựng sẵn (thêm một giá trị `enum` là RFC, `schemas/`), nên front này là **một bridge của lõi**: nó gọi `guard.dispatcher(id)` và mọi lời gọi có nguồn `bridge:<id>` (mặc định `bridge:http`, RFC-0017 §3b).
Gate **phải liệt kê nó**: gate chỉ liệt kê `mcp` chặn nó (`criterion_unavailable`, HTTP 403) — `test_the_proxy_dispatches_as_a_bridge_and_a_gate_listing_only_mcp_blocks_it`. Gate sinh ra liệt kê đúng `bridge:<id>` của tệp.

### 5.3 Request → tool

- **Tham số của tool:** tham số đường dẫn, tham số query và các **vô hướng cấp cao nhất** của body JSON. Kiểm bằng lược đồ của `Guard`: tham số không khai ⇒ `REJECTED` (400).
- **400 và không dispatch:** body không phải JSON, không phải đối tượng, giá trị lồng/`null`, khoá JSON lặp, tham số lặp (trong query, hoặc giữa đường dẫn/query/body), đoạn đường dẫn rỗng hoặc không an toàn (`%2f`, `%5c`, `%00`, `//`, `.`/`..` sau khi giải mã).
- **Chuyển tiếp nguyên văn:** method, đường dẫn, query và body **như đã nhận** (không dựng lại) tới `upstream`, kèm header cấu hình. Bỏ header hop-by-hop (và header nêu trong `Connection`), `Host` (đặt lại), `Content-Length` (tính lại),
  `Expect`; **`Authorization` và `Cookie` của client không bao giờ được chuyển** — header cấu hình ở `headers_env` thay chỗ.
- **Trả lời:** ALLOW ⇒ status, header (trừ hop-by-hop) và body của upstream; BLOCK ⇒ **403** + phán quyết JSON; `REJECTED` ⇒ **400** + phán quyết; route không khai báo ⇒ **404** (nêu chỉ route khai báo mới qua, không chuyển gì);
  body > 1 MiB ⇒ **413** (không đọc); `Transfer-Encoding` ⇒ 411; upstream hỏng sau ALLOW ⇒ **502** + phán quyết + vấn đề, **không bao giờ thử lại**; mỗi request tới upstream có thời hạn 30 giây.
- Mỗi kết nối một request (`Connection: close`); `dispatch` tuần tự dưới khoá của `Guard`.

### 5.4 Lệnh

- `neuroedge guard init --http <upstream> --route "METHOD /đường/{tham_số}" [--route …] [--dir DIR] [--name TÊN] [--header-env HEADER=BIẾN]`: viết `guard.toml` và một gate **chặn mặc định** cho mỗi route (cùng khuôn `operator_approved` như `guard init --mcp`;
  `call_source` có `bridge:http` trong `options` và `allow_when` chỉ nhận nó); tham số đường dẫn khai kiểu `string`; query/body muốn nhận phải tự khai thêm; không bao giờ ghi đè (`test_guard_init_http_never_overwrites_a_file`).
  `--mcp` và `--http` loại trừ nhau; `--route` chỉ đi với `--http`.
- `neuroedge proxy http [--config guard.toml] [--trace-out PATH]`: phục vụ **chỉ trên loopback** tới khi SIGINT/SIGTERM, rồi ghi vết (`metadata.proxy = {kind: "http", upstream}`); replay bằng `TracePlayer(trace, guard=…)` không chạm upstream.
- `neuroedge plugin doctor` (cùng lệnh với §4.4): với `[proxy.http]`, **API còn tới được trực tiếp ⇒ CẢNH BÁO** — với API cục bộ thì luôn như vậy; người vận hành phải đặt API của thiết bị sau tường lửa/ACL hoặc chỉ nhận từ máy proxy. Doctor không quét mạng
  nên nói "không kiểm được" cho máy/ứng dụng khác; gate không đọc `call_source` ⇒ CẢNH BÁO; plugin: "không kiểm được". Mã thoát như §4.4.
- **Chưa có:** TLS và xác thực ở front (vì vậy chỉ loopback), websocket, body streaming, `--init-timeout`.

## 6. Plugin: bật, nạp, nguồn gốc (RFC-0016 §3d; phần actuator của TSK-I2c-11)

Mã: `neuroedge/plugins/__init__.py`. Sáu nhóm entry point (`neuroedge.bridges`, `neuroedge.fact_sources`, `neuroedge.actuators`, `neuroedge.boards`, `neuroedge.templates`,
`neuroedge.exporters`); **chỉ `neuroedge.actuators` được nạp** ở bản này.

- **Phát hiện không import.** `neuroedge plugin list [--json]` đọc `importlib.metadata` — loại, tên entry point, bản phân phối, phiên bản — không import gói nào (`test_listing_plugins_imports_nothing`).
- **Bật trong tệp được commit, không ở dòng lệnh.** `[plugins] enable = ["neuroedge-ha", "neuroedge-ros2==0.4.1"]` trong `agent.toml` hoặc `guard.toml`: tên bản phân phối (so khớp theo PEP 503), tuỳ chọn ghim `==phiên bản`.
  Cài bằng `pip` không bật gì; **không cờ CLI nào** bật plugin. `[plugins.config.<entry point>]` là cấu hình chung của entry point đó, gộp **dưới** `[actuators.<tên>.config]` khi dựng; cùng luật bí mật với `[external]`: trường mang tên bí mật viết thẳng ⇒ NE3002, `*_env` chỉ là tên biến (không bao giờ in lại giá trị).
- **Hỏng ⇒ không khởi động.** Chưa cài · không import được · `sdk_requires` không tương thích (cùng MAJOR, MINOR đã cài ≥ MINOR đòi; thiếu ⇒ không tương thích) · ghim phiên bản lệch · hai bản phân phối đã bật cùng một tên entry point ·
  tên entry point ngoài `[a-z][a-z0-9_]{0,31}` · nhà máy không nhận đúng **một** đối số (`config`) · bản phân phối đã bật không có entry point NeuroEdge nào · có entry point loại chưa hiện thực (nêu TSK-I2c-11) ·
  `[plugins.config.X]` cho một entry point không bản phân phối đã bật nào cấp ⇒ `AgentManifestError` (NE3002), ba phần, trước khi chân nào bị giữ và trước lượt gate đầu.
  `neuroedge build` báo cùng lỗi (gom vào `BuildFailed`).
- **Nguồn gốc.** Mỗi entry point đã nạp: một dòng trên stderr lúc khởi động, một mục trong `metadata.plugins` của **mọi** vết ghi của phiên/Guard và một sự kiện `plugin_loaded`, cùng dữ liệu
  `{kind, name, distribution, version, files_sha256}` — `files_sha256` = `sha256:` của danh sách (đường dẫn, sha256 của byte trên đĩa) các tệp của gói entry point trong `dist.files`, không đọc từ `RECORD`.
  Bản cài editable (`direct_url.json` có `dir_info.editable`) không có `files_sha256` mà có `editable: true`. Không plugin nào bật ⇒ không có khoá `metadata.plugins` (vết ghi chuẩn mực không đổi).

## 7. Cơ cấu chấp hành từ xa (RFC-0018; TSK-I2c-16 phần lõi)

Ngữ nghĩa và lý do: [RFC-0018](../rfc/0018-co-cau-chap-hanh-tu-xa.md) §3b–§3i (đã chấp thuận; hằng ở §9.5). Ở đây chỉ ghi điều mã làm, và những chỗ RFC để mở mà mã đã chọn.

**Khai báo** (`agent.toml` hoặc `guard.toml`, hay `ActuatorDeclaration` bằng mã):

```toml
[requires]
"digital.out" = { pins = ["garden_valve"] }      # tên cơ cấu từ xa nằm cạnh chân của bo

[plugins]
enable = ["neuroedge-ref-actuators"]

[actuators.garden_valve]
plugin     = "ref_l2"          # tên entry point của một bản phân phối đã bật
safe_off   = "L2"              # mức người triển khai dựa vào; bắt buộc
reversible = false             # vắng ⇒ false (không hoàn tác)
[actuators.garden_valve.envelope]   # bốn khoá của board.v1 #/$defs/envelope, bắt buộc đủ
window_s = 3600
max_on_ms_per_window = 1800000
min_interval_ms = 2000
max_continuous_ms = 600000
[actuators.garden_valve.config]     # chuyển (chỉ đọc) cho factory của plugin; không bí mật viết thẳng
token_env = "NE_VALVE_TOKEN"
```

**Một hàm kiểm** — `check_actuators` (`neuroedge.guard`), qua `plugins.actuators.remote_setup` cho tệp — chạy ở `neuroedge build` (`engine/compiler.py`), ở `SimSession.load` và ở `Guard`; mọi luật ở bảng §3b,
D5 (§3f) và §3k của RFC; danh sách từng luật kèm mã lỗi là corpus `fixtures/actuators/` (`expected_errors.yaml`, khép kín hai chiều). Cảnh báo, không chặn: mức `L0`; module `@action` import
`httpx`, `requests`, `aiohttp`, `urllib.request` hoặc `socket` (in ở `neuroedge build`, `BuildReport.warnings`).

**Đường tới thiết bị.** `digital_out` của `SimHAL` và `LinuxHAL` rẽ ở đầu hàm vào `HardwareAbstractionLayer._remote_out`: `require_pin → chốt trạng thái → phong bì → authorize → record → apply`
(`test_the_order_is_require_pin_state_guard_envelope_authorize_record_apply`). Chỉ `on`, `off`, `pulse`; `after_ms` (lệnh hẹn) bị từ chối (`BoardCapabilityError`). Chỉ HAL giữ plugin;
HAL nhận lớp `Command` và bốn lỗi của SDK qua `hal.remote.Vocabulary` (HAL vẫn là lá, không import `sdk`). Lỗi gửi `NotSent`/`Rejected` ⇒ hoàn phần giữ trước, ném `BoardCapabilityError`;
`Ambiguous` (hay lỗi lạ của plugin, hay quá `command_timeout_ms`) ⇒ giữ phần giữ trước, `uncertain`, ném `BoardCapabilityError`. `off` không bao giờ ném.

**Chỗ RFC để mở, mã chọn (fail-closed):**

| Điều | Mã làm | Vì sao |
|:---|:---|:---|
| Mức điều khiển thời gian khi `safe_off` khai thấp hơn `safe_off_level` của plugin | HAL dùng **mức của plugin** (giao thức thiết bị nói): L2 luôn gửi `duration_ms`, L3 luôn thuê | Bảo đảm của thiết bị không bao giờ bị bỏ; D5 vẫn xét mức khai |
| L0 | HAL vẫn gửi `off` của nó ở `D` (như L1) | Nợ tắt là của nó; không gì cấm phía an toàn |
| Đọc lại trước mỗi lệnh bật | Có `readback`: mỗi `on`/`pulse` đọc trạng thái ngay trước chốt | Chốt cần mốc ≤ `max_state_age_ms` |
| Đọc thấy `on` khi không nợ gì | `already_on`, kể cả khi đang `uncertain`; không gửi `off` | §3g: không tắt thứ nó không bật |
| Không có `readback` | `off` được ghi nhận (ack) là xác nhận tắt; sau khởi động phải có một `off` được ack trước lệnh bật đầu | §3g "off là lần off được xác nhận gần nhất" |
| Bản ghi trạng thái | `<thư mục phong bì>/<tên>.remote.json` `{version, name, off_owed, quarantined}`, ghi trước lệnh; thiếu mà không `envelope_init` (linux), hay hỏng ⇒ `quarantined` | Cùng luật bản ghi phong bì (RFC-0007 §3d) |
| Gỡ `quarantined` | Người vận hành sửa bản ghi (`"quarantined": null`) hoặc gọi `FileRemoteStore(<thư mục>).clear("<tên>")`, rồi khởi động lại (⇒ `uncertain` tới lần đọc `off` tươi) | Không có đường tự gỡ |
| Replay | Không dựng plugin; mỗi lần bật nhận đúng quyết định của chốt trạng thái lúc ghi (`script_remote_state`), hết dữ liệu ⇒ `actuator_state_unknown`; phong bì quyết lại trên dòng thời gian đã ghi, kết thúc ở hạn `D` như mọi chân khi replay | `remote_*` chỉ là thông tin (§3i) |
| Đọc lại thành dữ kiện cho gate (§3e đoạn cuối) | **Chưa có** (cần TSK-I2c-09): không nguồn nào cấp, gate đòi nó thấy dữ kiện vắng ⇒ `BLOCK` | `test_uncertain_and_quarantined_are_absent_facts_so_a_gate_blocks` |
| `pwm`, `motion` lên tên cơ cấu từ xa; `esp32s3` | NE3001 ở build; lúc chạy `pwm` ⇒ `BoardCapabilityError` | RFC-0018 §3a, §9.4 |

`sim` luôn lái `DeviceDouble` của plugin (`probe()` gọi khi dựng HAL, trước mọi I/O; thiếu `probe()` ⇒ không chạy trên `sim`); đồng hồ của bản giả đi theo đồng hồ phiên. Sự kiện vết ghi:
`simulation_coverage.md` §3; lint `remote_command_sent` (NE4001): `python/neuroedge/trace.py::lint_remote`.

Plugin tham chiếu (Apache-2.0, `fixtures/compliance/actuators/valid/neuroedge-ref-actuators/`): bốn entry point `ref_l0` … `ref_l3`, giao thức đồ chơi qua TCP tới một thiết bị không có, chỉ dùng qua bản giả.
Adapter Home Assistant là phần B của TSK-I2c-16, chưa có.

## 8. `neuroedge conformance` — loại actuator (RFC-0016 §3g, RFC-0018 §3e; phần của TSK-I2c-12)

`neuroedge conformance <bản phân phối> [--kind actuator] [--json]` nạp **chỉ** bản phân phối đó (gõ tên là hành vi bật tường minh) và kiểm từng entry point của nó. Mã: `neuroedge/plugins/conformance.py`.
Phép kiểm động chạy bản giả của plugin **qua mã HAL thật** (`hal/remote.py`) trên đồng hồ ảo; factory được gọi với `conformance_config` của mô-đun (một `Mapping`, vắng ⇒ `{}`).

| Phép kiểm | Đạt khi |
|:---|:---|
| `plugin.loads` | import được; factory nhận đúng một đối số; trả một `Actuator` đủ thuộc tính và phương thức, trong giới hạn §9.5 của RFC-0018 |
| `plugin.sdk_range` | `sdk_requires` tương thích `SDK_VERSION` |
| `plugin.name_pattern` | tên entry point khớp `[a-z][a-z0-9_]{0,31}` |
| `actuator.level_proven` | vector của mức khai: L0 — `on` không mang thời hạn; L1 — đứt liên lạc ngay trước hạn ⇒ HAL không tin là đã tắt, gửi lại mỗi `OFF_RETRY_MS`, liên lạc lại thì tắt và xác nhận; L2 — (a) `duration_ms ≤ D` ở mọi `on`, (b) đứt sau khi giao ⇒ tắt trước `D + tolerance_ms`, (c) đứt trước khi giao ⇒ không bật quá `D`; L3 — (a) runtime đóng băng ⇒ tắt ≤ `lease_ms + tolerance_ms` sau lần gia hạn cuối, (b) gia hạn trùng/đến muộn không đẩy quá `start + D + tolerance_ms`, (c) `lease_ms ≤ max_lease_ms` |
| `actuator.off_is_idempotent` | `safe_off()` hai lần (đang tắt, rồi sau một `on`) không lỗi |
| `actuator.off_is_unconditional` | HAL có sổ token từ chối mọi thứ vẫn tắt được thiết bị |
| `actuator.builds_without_io` | factory chạy khi `socket` bị chặn, không thử mở kết nối nào |
| `actuator.classifies_errors` | đứt liên lạc: `apply`/`safe_off` ném `NotSent`, `Rejected` hoặc `Ambiguous`; `read_state` ném `ReadFailed` |
| `actuator.receives_no_handles` | factory nhận đúng `config`; driver không giữ đối tượng nào của lõi (ngoài `neuroedge.sdk`/`errors`) |

Kết quả `pass` · `fail` · `unverifiable` (không `probe()`: bốn phép kiểm động). Không nạp được ⇒ mọi phép kiểm `actuator.*` là `fail`. Mã thoát: §6 của `python_api.md`.
Báo cáo `--json`: `{distribution, version, files_sha256, editable, sdk, core, checker, results: [{entry_point, check, result, detail}], unimplemented, problem, badge_eligible, exit_code}` —
`badge_eligible` chỉ đúng khi mọi phép kiểm `pass`, không editable và có `files_sha256` (huy hiệu là TSK-I2c-18); chưa vào `schemas/` (RFC-0016 §3g).
Corpus `fixtures/compliance/actuators/{valid,invalid}/` + `expected_results.yaml`: mỗi phép kiểm có ít nhất một phản chứng mà nó bắt (`test_every_check_of_every_kind_catches_a_counter_example`).
P1 chứng minh cách plugin dựng lệnh với giao thức thiết bị trên bản giả, **không** chứng minh phần sụn thật tôn trọng lệnh (RFC-0018 §3e).
