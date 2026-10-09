# Lõi an toàn dùng độc lập và Extension SDK — `neuroedge.guard`, `neuroedge.sdk`

**Trạng thái:** chuẩn tắc cho phần đã hiện thực (TSK-I2c-07); phần còn lại ghi rõ "chưa có". Nền: [RFC-0016](../rfc/0016-loi-tach-duoc-va-extension-sdk.md)
(§3b, §3c, §3e), [RFC-0017](../rfc/0017-nguon-goi-theo-khong-gian-ten.md) (nguồn `bridge:<id>`).
**Mã nguồn:** `python/neuroedge/guard.py`, `python/neuroedge/sdk/__init__.py`, `python/neuroedge/sim/hal_build.py`.
**Test ghim:** `python/tests/test_guard.py`, `python/tests/test_sdk_api.py`.
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

Hàm khởi tạo `Guard(tools, *, name, board, target, registry_root, base, events, testing, hal_options)`: `board` là id của một bo (hoặc `None`); `target` là `sim` hoặc `linux`, mặc định theo bo
(`esp32s3` không có Guard Python — MCU dùng `ne_gate` + `NETR`). Gate nằm ở từng `Tool`, nên hàm không có tham số `gates=` riêng của RFC-0016 §3b (ví dụ ở đó); gate `fallback_action` là một `Tool` khác.

## 2. `neuroedge.sdk`

Phần tối thiểu mà `guard` cần của Extension SDK (TSK-I2c-11 làm phần còn lại):

| Tên | Là gì |
|:---|:---|
| `ToolRequest(name, arguments={}, id="")` | `tool-call.v1#/$defs/request`: **không có `source`**; bất biến |
| `Outcome(status, content)` | Dữ liệu thuần: `status` và `ToolResult.content()` (hợp lệ theo `tool-result.v1`), không mang giá trị mà thân action trả về |
| `SDK_VERSION = (1, 0)` | Bộ `(MAJOR, MINOR)` riêng, không phải `__version__` của gói |

`__all__` của nó là `["SDK_VERSION", "Outcome", "ToolRequest"]`; không tên HAL, không `Guard`, không `Conversation`, không tên nào của `neuroedge.__all__` (`test_the_sdk_exports_no_hal_name_and_no_name_of_all`).
**Chưa có (TSK-I2c-11/12):** `Protocol` cho bridge, fact source, actuator, exporter; bộ nạp entry point và `plugin list|doctor`; `sdk_requires`; bộ test tuân thủ. Cam kết ổn định đầy đủ: RFC-0016 §3e.

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
| `[tools.<tên>.parameters.<p>]` | `type`, `default`, `description` | giới hạn giá trị là của `arguments` trong gate (RFC-0005), không ở đây |
| `[plugins]` | `enable`, `config` | khác rỗng ⇒ từ chối, nêu TSK-I2c-11 |
| `[external]` | — | từ chối, nêu TSK-I2c-09 |
| `[actuators]` | — | từ chối, nêu TSK-I2c-16 |

### Văn phạm `drive`

`drive` là danh sách bước, chạy lần lượt trong thân của tool, dưới token. Mỗi bước là một bảng:

| Khoá | Ý nghĩa |
|:---|:---|
| `pin` | tên chân; **phải** có trong `requires` (`digital.out:<pin>`) |
| `operation` | `on`, `off` hoặc `pulse` |
| `seconds_from` | chỉ với `pulse`, **bắt buộc** ở đó: tên một tham số đã khai, kiểu `integer` hoặc `number`; độ dài xung (giây) lấy từ tham số này |

Guard dựng bước thành `digital.out(pin).on()`, `.off()` hay `.pulse(seconds=<tham số>)`. Giá trị ngoài giới hạn là việc của gate (`argument_out_of_range`) và của phong bì của bo.
Không có gì khác trong `drive`: cơ cấu từ xa là chân `digital.out` có tên (RFC-0018, TSK-I2c-16 — chưa có). Muốn thân tuỳ ý, dùng `Tool(run=…)` trong Python.
