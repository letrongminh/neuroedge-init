# Bề mặt công khai — API Python (`import neuroedge`) và CLI (`neuroedge`)

**Trạng thái:** chuẩn tắc (TSK-I6-06, Q-63); quy tắc ngừng hỗ trợ (§5), cách đọc `0.x` (§3), `SimSession` công khai (§2.1) và hợp đồng CLI (§6) chốt ở Q-64. PRD §10.3 hứa SemVer cho gói `neuroedge` ("thay đổi bề mặt API công khai hoặc CLI")
nhưng chưa nói cái gì là công khai; tài liệu này nói, cho API Python (§1–§4) và cho CLI (§6).
**Mã nguồn:** `python/neuroedge/__init__.py` (`__all__`) · `python/neuroedge/sim/serve.py` (`serve_mcp`) · `python/neuroedge/cli/main.py` (cây lệnh).
**Test ghim:** `python/tests/test_public_api.py` (API Python) · `python/tests/test_cli_contract.py` (CLI).

Tài liệu này là nơi **duy nhất** định nghĩa điều gì thuộc API Python và CLI công khai, và SemVer hứa gì về chúng.
Tài liệu khác dẫn tới đây, không chép lại (CONTRIBUTING §8.1). Từ khoá **PHẢI**, **KHÔNG ĐƯỢC**,
**NÊN** mang nghĩa như RFC 2119. Danh sách tên nằm ở `neuroedge.__all__`; bảng ở §2 chỉ giải thích
từng nhóm, và test khoá việc mỗi tên đều có mặt ở đó.

## 1. Điều gì là công khai

**Công khai là mọi tên trong `neuroedge.__all__`, và chỉ chúng.** Một dự án tích hợp chỉ cần
`import neuroedge`: dựng HAL, nạp gate, gọi `dispatch`, khởi động MCP server (tiêu chí ra I6 số 9).

| Thuộc bề mặt công khai | Ngoài bề mặt công khai |
|:---|:---|
| Tên trong `__all__`, đọc là `neuroedge.<tên>` | Mọi mô-đun con: `neuroedge.engine`, `neuroedge.hal.sim`, `neuroedge.sim`, `neuroedge.cli`… — dùng được, nhưng **không được hứa** |
| Chữ ký gọi của tên đó: tên tham số, thứ tự, tham số bắt buộc hay không | Tên bắt đầu bằng `_`, mọi thuộc tính hay phương thức không được docstring hoặc đặc tả nói tới |
| Hành vi mà docstring và đặc tả dẫn tới mô tả | Tham số tiêm đối tượng giả khi test (`gpiod`, `sounddevice` của HAL) |
| Lớp lỗi và **mã `NE…`** mà nó ném (PRD Phụ lục B) | Câu chữ của `why` và `how` (được cải thiện; lớp lỗi và mã thì không trôi — CONTRIBUTING §3) |
| Tên và lớp của các lỗi trong `__all__`; ba thuộc tính `where`, `why`, `how` và `code` của `NeuroEdgeError` | Thứ tự khoá, `repr`, hiệu năng, số sự kiện trong vết ghi |

Công khai theo **tên**, không theo **vị trí**: `neuroedge.SimHAL` được hứa; `neuroedge.hal.sim.SimHAL`
vẫn chạy hôm nay nhưng một bản phát hành có thể dời nó. Mã sinh ra bởi `neuroedge new` và các agent
mẫu chỉ import tên công khai ở dạng `from neuroedge import …`.

Hợp đồng dạng tệp **không** thuộc tài liệu này vì có phiên bản riêng: lược đồ gate, vết ghi, `board.v1`,
`tool-call.v1`, `tool-result.v1`, `error.v1` và danh mục mã lỗi `error-codes.v1` (RFC-0015)
(PRD §10.3, `schemas/`, `CONTRIBUTING.md` §3) và bố cục nhị phân `NETR` (RFC-0003, RFC-0009). Dòng
"hoặc CLI" của PRD §10.3 được định nghĩa ở §6.

## 2. Bề mặt hiện tại

| Nhóm | Tên | Dùng để |
|:---|:---|:---|
| Phiên bản | `__version__` | Chuỗi phiên bản của gói |
| HAL | `HardwareAbstractionLayer`, `SimHAL`, `LinuxHAL`, `PinAssertion`, `BoardProfile`, `load_board_by_id`, `digital`, `motion` | Dựng HAL cho `sim` hoặc `linux`, khẳng định trạng thái chân, đọc hồ sơ bo mạch; `digital.out(pin)` là cách thân `@action` điều khiển chân, `digital.input(pin).level()` là cách nó đọc mức một chân đầu vào đã khai (RFC-0007 §3a; không cần token, đọc hỏng ⇒ `PerceptionUnavailableError`). `motion.motor(kênh, speed=…, ramp_ms=…)`, `motion.servo(kênh, target=…)` và `motion.stop(kênh)` điều khiển kênh chuyển động đã khai (RFC-0011 §3b): lệnh chỉ chạy trong thời hạn thuê (lease) của phán quyết, gia hạn bằng một lần qua gate mới, hết hạn ⇒ trạng thái an toàn của kênh; `stop` là lệnh về phía an toàn, không bao giờ bị chặn. `LinuxHAL` cần extra `linux` (`gpiod`) **khi dựng**, không phải khi `import neuroedge` |
| Gate và engine | `ResolvedGate`, `resolve_gate_file`, `resolve_gate_uri`, `GateRegistry`, `ActionContractEngine`, `GateVerdict`, `GateResult`, `Gate`, `Fact`, `Reason` | Nạp và phân giải gate, đăng ký vào engine, đọc phán quyết. `Gate` là bí danh cũ của `GateResult`, giữ vì đã công khai từ 0.1 |
| Cây quyết định | `compile_tree`, `walk`, `TreeResult` | Biên dịch gate đã phân giải thành cây và duyệt nó trên máy tính — hàm thuần, cùng phán quyết với walker trên thiết bị |
| Hành động và tool call | `action`, `spec_of`, `Conversation`, `ActionResult`, `ToolCall`, `ToolResult`, `ToolSet`, `dispatch` | `@action`, `c.do()` qua gate, và đường duy nhất từ một tool call tới chân: `dispatch` (`docs/spec/tool_calling.md` §2) |
| Phiên mô phỏng | `SimSession`, `Turn` | Nạp một agent trên `sim` (hoặc `linux`), cho nó nghe một dòng, khẳng định chân và vết ghi: bộ khung test của mã `neuroedge new`. Chỉ một phần nhỏ được hứa: §2.1 |
| Mô hình | `SystemOne`, `SystemTwo` | Hai tầng mô hình của agent |
| Vết ghi và kiểm thử | `TraceRecorder`, `load_trace`, `validate_trace`, `replay`, `scenario` | Ghi vết (băm lời người dùng theo mặc định, NFR-PRIV-03), thẩm định, replay |
| MCP | `serve_mcp` | Khởi động MCP server qua stdio từ mã Python (§4) |
| Lỗi | `NeuroEdgeError` và các lớp con: `ActionContractViolation`, `TokenReplayError`, `EnvelopeRefusedError` (NE1003, do phong bì ném — RFC-0007), `ToolCallError`, `GateError`, `GateNotFoundError`, `GateSchemaError`, `GateInheritanceError`, `BoardCapabilityError`, `AgentManifestError`, `BuildFailed`, `TraceValidationError`, `SafetyRegressionError`, `ReplayError`, `VerificationError`, `PerceptionUnavailableError` | Mọi lớp lỗi của gói, mã ở PRD Phụ lục B. `ToolCall` dựng với nguồn không hợp lệ ném `ToolCallError` (NE1004), cũng là `ValueError` để mã viết cho 0.1 vẫn chạy. Nguồn hợp lệ là năm tên dựng sẵn, `bridge:<id>` hoặc `mcp:<client>` (văn phạm ở `docs/spec/tool_calling.md` §1; `SOURCES`, `valid_source`, `source_channel` là nội bộ); `dispatch()` ném cùng mã cho một nguồn có không gian tên chưa được đăng ký trong phiên |

Mọi lớp lỗi trong `errors.py` **PHẢI** nằm trong `__all__` (test khoá): người tích hợp bắt lỗi theo lớp,
nên một lớp lỗi không có tên công khai là một lỗi không bắt được.

### 2.1 `SimSession` và `Turn`: chỉ những thành viên này được hứa

`SimSession` là nơi lắp ráp một agent (`docs/architecture/vi/03-component-host-c4l3.md` §2), nên lớp
này lớn và còn đổi. Lời hứa SemVer **chỉ** phủ những thành viên mà mã `neuroedge new` và tài liệu dùng;
mọi thứ khác của `SimSession` và `Turn` nằm ngoài lời hứa (§1), dù không bắt đầu bằng `_`.

| Tên | Được hứa |
|:---|:---|
| `SimSession.load(agent_toml="agent.toml", *, board_id, facts, registry, clock, events, slow, target, target_options)` | Đúng chín tham số này, tên, thứ tự và mặc định; ném `BuildFailed` khi agent không khớp bo mạch, `BoardCapabilityError` khi `linux` không chạy được agent (docstring của `load`) |
| `await session.handle(text)` | Chạy một dòng gõ qua ngữ pháp, `c.do()` và gate; trả một `Turn`. Các tham số từ khoá của `handle` (`heard_after_ms`, `spoken`, `answer_to`) **không** được hứa |
| `session.hal` | HAL của phiên (`session.hal.pin(tên)` khẳng định chân) |
| `session.set_sensor(sensor, value)` | Đặt giá trị cảm biến mô phỏng mà HAL trả về |
| `session.trace()` | Vết ghi `trace.v1` của phiên cho tới lúc này, đã thẩm định |
| `session.events.of_type(loại)` | Các sự kiện đã ghi theo loại |
| `Turn.recognised`, `Turn.allowed` | `recognised`: ngữ pháp nhận ra lệnh; `allowed`: hành động đã chạy vì gate cho phép |
| `Turn.result` | `ActionResult` của hành động, hoặc `None` nếu không có hành động; `result.blocked`, `result.gate` (một `GateResult`) |
| `Turn.reply_source` | Nguồn của câu trả lời: chuỗi hoặc `None` (các giá trị cụ thể không được hứa) |
| `Turn.confirmation` | `None` khi thiết bị không hỏi lại người; khác `None` khi có một câu hỏi chờ trả lời |

Test trong mã `neuroedge new` chỉ dùng các thành viên ở bảng trên (cộng các tệp của chính dự án, như
`agent.toml`); đọc `session.grammar`, `session.sensor_facts` hay `session.gate_facts` là dựa vào nội bộ.

## 3. Chính sách SemVer

Gói `neuroedge` theo [SemVer 2.0.0](https://semver.org/lang/vi/) trên bề mặt ở §1 và hợp đồng CLI ở §6. Với phiên bản
`MAJOR.MINOR.PATCH`:

| Thay đổi | Tăng |
|:---|:---|
| Bỏ hay đổi tên một tên trong `__all__`; đổi chữ ký theo cách làm hỏng lời gọi cũ (bỏ tham số, thêm tham số **bắt buộc**, đổi thứ tự tham số vị trí); đổi lớp lỗi hay mã `NE…` một tình huống ném; đổi hành vi đã mô tả | **MAJOR** |
| Thêm một tên vào `__all__`; thêm tham số **tuỳ chọn** có mặc định giữ hành vi cũ; thêm một lớp lỗi mới | **MINOR** |
| Sửa lỗi mà không đổi điều đã mô tả; cải thiện câu chữ `why`/`how`; thay đổi nội bộ | **PATCH** |

Hai điểm riêng của sản phẩm này:

- **An toàn không bao giờ bị "tương thích" ép lùi.** Một thay đổi làm gate chặn nhiều hơn, hay đóng một
  đường tắt qua gate, được phép ở bản MINOR hay PATCH dù có mã đang chạy nhờ đường đó (bất biến
  `CHANGELOG.md` §3.3 #2: fail-closed). Ghi rõ trong `CHANGELOG.md`.
- **Mỗi thay đổi của `__all__` là một quyết định.** `test_public_api.py` ghim danh sách: thêm hay bỏ
  một tên làm CI đỏ cho tới khi sửa danh sách ghim, bảng §2 và mục `CHANGELOG.md` trong cùng PR.

**Ý nghĩa của `0.x`.** SemVer cho phép bản `0.y.z` đổi bất cứ lúc nào. NeuroEdge **hẹp lại** lời đó:
trong `0.x`, MINOR đóng vai MAJOR — một thay đổi phá vỡ chỉ xảy ra ở bản MINOR (`0.y` → `0.y+1`),
không bao giờ ở bản PATCH, và vẫn đi qua quy tắc §5. Lời hứa đầy đủ ở §3 bắt đầu từ `v1.0`.
*(Q-64.)*

## 4. Khởi động MCP server từ Python

```python
import neuroedge

neuroedge.serve_mcp("agent.toml")            # chặn tới khi client đóng stdin
```

`serve_mcp` làm đúng việc của `neuroedge mcp serve` (không có `--ui`), vì hai nơi dùng chung một vòng
phục vụ (`sim/serve.py::run_stdio`), không phải hai đường mã:

- Mọi `@action` của agent là một tool; mọi `tools/call` đi **một đường** tới phần cứng — kiểm schema,
  `c.do()`, gate, token dùng một lần, HAL (`docs/spec/tool_calling.md` §2). Không có tham số nào để
  tắt gate hay tự khai `call_source`: nguồn của kết nối là `mcp` (§5 của đặc tả đó).
- `trace_out` ghi vết phiên khi thoát; lời người dùng **được băm** trừ khi `raw=True` (khi đó phát một
  `UserWarning` và vết ghi `metadata.anonymized = false`, như `--raw`). Mặc định giữ nguyên NFR-PRIV-03.
- `target="linux"` điều khiển chân thật: tiến trình rời qua phần dọn dẹp khi nhận SIGTERM hay SIGHUP,
  mọi chân về trạng thái tắt (như `mcp serve --target linux`).
- **`serve_mcp` sở hữu tiến trình.** Hai lối ra kết thúc cả tiến trình gọi nó bằng `os._exit`, sau khi
  đã dọn dẹp (ghi vết, thả mọi chân): không client nào gửi `initialize` trong `init_timeout` giây (mặc
  định 30; `0` chờ mãi), và SIGTERM/SIGHUP khi `target="linux"`. Lý do: luồng đọc stdin của MCP SDK
  không huỷ được, nên chỉ thoát tiến trình mới giải phóng được nó. Gọi `serve_mcp` trong một tiến trình
  dành riêng cho nó, không trong tiến trình còn việc khác.
- stdout thuộc về giao thức; mọi thứ cho người đọc đi vào stderr. Thiếu MCP SDK (extra `mcp`) thì
  `serve_mcp` ném `NeuroEdgeError` với cách cài, trước khi dựng gì.

Hàm đồng bộ, tự chạy vòng sự kiện của nó: không gọi trực tiếp từ một coroutine. Người cần giao diện
`--ui` dùng CLI: trang đó không thuộc bề mặt Python công khai.
Tương tự, cửa mạng của MCP server (`neuroedge mcp serve --http`: Streamable HTTP, mTLS, token OAuth 2.1;
`docs/spec/tool_calling.md` §8.1) là việc của CLI, **chưa** thuộc bề mặt Python công khai: `serve_mcp` chỉ
phục vụ qua stdio, và không có tham số nào mở một cổng mạng.

## 5. Quy tắc ngừng hỗ trợ (Q-64)

Bề mặt công khai không biến mất đột ngột:

1. Một tên (hay tham số, hay hành vi) sắp bị bỏ **PHẢI** được đánh dấu *ngừng hỗ trợ* ở một bản
   **MINOR**: nó vẫn chạy y như cũ, nhưng phát `DeprecationWarning` nêu tên thay thế và bản sẽ bỏ nó,
   và `CHANGELOG.md` ghi vào nhóm *Đã đổi*.
2. Nó **PHẢI** còn chạy ít nhất **một bản MINOR đầy đủ** sau bản đánh dấu (bản `1.4` đánh dấu thì `1.5`
   vẫn còn; `2.0` mới được bỏ). Chỉ bản **MAJOR** mới bỏ hẳn.
3. Trong `0.x`: cùng quy tắc, MINOR thay MAJOR (§3) — đánh dấu ở `0.y`, bỏ nhanh nhất ở `0.y+2`.
4. Ngoại lệ duy nhất là lỗ hổng an toàn: bỏ ngay ở bản PATCH, kèm lời giải thích trong changelog.
5. Cảnh báo dùng `warnings.warn(..., DeprecationWarning, stacklevel=2)`, để nó trỏ vào dòng của
   người gọi. Mã trong repo **KHÔNG ĐƯỢC** dựa vào một tên đã đánh dấu.

*Chưa có tên nào bị ngừng hỗ trợ.* Khi có, mục này nhận một bảng: tên, bản đánh dấu, bản bỏ, tên thay thế.

## 6. Hợp đồng CLI

CLI là `neuroedge <lệnh> …` (`python -m neuroedge` như nhau). Cùng chính sách SemVer (§3) và quy tắc
ngừng hỗ trợ (§5, Q-64) như API Python; ở `0.x`, MINOR đóng vai MAJOR.

| Được hứa | Không được hứa |
|:---|:---|
| Tên lệnh và lệnh con (`gate lint`, `mcp serve`…) | Chữ in ra stdout và stderr cho người đọc: câu chữ, màu, thứ tự dòng, bảng, khung |
| Tên cờ và tuỳ chọn (kể cả dạng ngắn `-t`), ý nghĩa của chúng, cờ nhận giá trị hay không, lặp được hay không | Thời gian chạy, độ rộng bảng, khối `Examples:` của `--help` |
| Đối số nào bắt buộc, và thứ tự các đối số vị trí | Đường dẫn mặc định của tệp một lệnh ghi khi không có `--out` |
| **Mã thoát** — bảng ở `CHANGELOG.md` §2.3 (`0` đạt, `1` không đạt, `2` chưa hiện thực), không chép lại ở đây | Nội dung chẩn đoán `why`/`how` (mã `NE…` thì được hứa, §1) |
| Đầu ra máy đọc: `--json`, `--openai`, và các tệp lệnh ghi ra (lược đồ riêng, có phiên bản — `schemas/`, PRD §10.3; không nhắc lại ở đây) | |

**Nhóm lệnh `add` (TSK-I2b-04, FR-DX-08).** Hứa bốn lệnh con `add action`, `add sensor`, `add device`,
`add gate`, mỗi lệnh nhận một tên làm đối số bắt buộc; các cờ `--primitive`, `--pin`, `--channel`,
`--source`, `--label`, `--device`, `--register`, `--width`, `--fact`, `--board` và `--agent` như bản chụp ở
`test_cli_contract.py`. Hợp đồng hành vi: lệnh chỉ chạy trong dự án có `agent.toml`; **không bao giờ ghi đè**
một tệp, một khoá `[gates]`, một tên action hay tên lệnh đã có (từ chối bằng lỗi ba phần, mã thoát `1`, không
ghi gì); kết quả được build thử trên một bản sao trước khi ghi vào dự án. Câu chữ in ra không được hứa.

**Quy tắc phiên bản cho CLI:**

| Thay đổi | Tăng |
|:---|:---|
| Đổi tên hay bỏ một lệnh, cờ hay tuỳ chọn; đổi ý nghĩa của một mã thoát; đổi hình dạng `--json`/`--openai` theo cách làm hỏng bên đọc cũ; biến đối số tuỳ chọn hoặc cờ thành bắt buộc; biến cờ thành tuỳ chọn nhận giá trị | **MAJOR** (ở `0.x`: MINOR) |
| Thêm một lệnh hoặc một cờ **tuỳ chọn**; thêm khoá vào `--json` mà bên đọc cũ bỏ qua được | **MINOR** |
| Một lệnh (hay một `--target`) chuyển từ mã `2` ("chưa hiện thực") sang `0` hoặc `1` | **MINOR**, không phải thay đổi phá vỡ: mã `2` là lời hứa "chưa có", không phải lời hứa "sẽ không bao giờ có" |
| Sửa câu chữ, màu, bảng; sửa lỗi | **PATCH** |

Khi đổi tên hay bỏ, tên cũ **PHẢI** còn chạy như một bí danh ẩn (`hidden=True`) phát cảnh báo ngừng hỗ trợ
trên stderr đúng một bản MINOR đầy đủ (§5). An toàn vẫn được ưu tiên: một lệnh mà hành vi cũ để lọt
điều gate lẽ ra chặn thì sửa ngay, theo ngoại lệ ở §5.

**Cưỡng chế.** `test_cli_contract.py` đọc cây lệnh Typer và so với một bản chụp theo từng dòng một
lệnh: tên đầy đủ, đối số theo thứ tự, cờ (kèm `=` nếu nhận giá trị, `!` nếu bắt buộc). Thêm, bỏ hay đổi một
lệnh hoặc cờ làm CI đỏ cho tới khi bản chụp, mục SemVer ở trên và `CHANGELOG.md` đổi trong cùng PR. Mã thoát
và `--json` được kiểm bởi test của từng lệnh, không phải bản chụp này.
