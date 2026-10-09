# RFC-0018: Cơ cấu chấp hành từ xa và mức tự tắt

| | |
|:---|:---|
| **Mã RFC** | 0018 |
| **Tiêu đề** | Cơ cấu chấp hành từ xa (Home Assistant, ESPHome, Matter…) là một loại cơ cấu của HAL do plugin `neuroedge.actuators` cung cấp: khai ở `agent.toml`, chỉ lái được qua `_admit` (phong bì → token → vết ghi), khai một **mức tự tắt** L0–L3 kèm cách chứng minh; mất liên lạc ⇒ trạng thái không chắc ⇒ từ chối lệnh bật; hành động không hoàn tác cần ≥ L2 |
| **Hợp đồng bị ảnh hưởng** | `agent.toml` *(khối `[actuators.<tên>]` mới; ngoài `schemas/`, kiểm ở `neuroedge build` và lúc nạp, như `[external]` của RFC-0014)* · hợp đồng an toàn của điểm cắm `neuroedge.actuators` *(Protocol `Actuator` đầy đủ chữ ký ở §3c, mức tự tắt ở §3d)* · đường HAL `_admit` *(thêm một chốt trạng thái cho cơ cấu từ xa trước phong bì, §3g)* · `docs/spec/threat_model.md` §1–§2 *(thêm luật và hàng)* · PRD Phụ lục B *(nới nguyên nhân NE1003, NE3001, NE3002; không mã mới)* · quy ước sự kiện vết ghi *(không đổi `trace.v1`)* · corpus mới `fixtures/actuators/` · **không** đụng `board.v1` *(phương án có đụng: §6, §9 câu 1)*, `gate.v1`, ngữ nghĩa phân giải, `NETR`, sổ token, `digests.lock`, ba vết ghi chuẩn mực |
| **Yêu cầu PRD liên quan** | FR-EXT-02, FR-EXT-03, FR-EXT-07, FR-HAL-01, FR-HAL-05, FR-ACE-02, NFR-SEC-10 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-10-04 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-04) — kỹ thuật trưởng ký trên PR #99; quyết định cho câu hỏi mở ở §9 (Q-68) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (thêm luật lên đường tới cơ cấu chấp hành; mở một loại cơ cấu mà bảo đảm tự tắt nằm ở thiết bị ngoài tầm kiểm của lõi) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3. Thiết kế này **không** chạm hàng nào của bảng đó (không sửa `schemas/`, ngữ nghĩa phân giải, ba vết ghi chuẩn mực, `digests.lock`, `NETR`);
> RFC vẫn bắt buộc vì Q-67 quyết định 5 đòi, vì nó thêm luật lên "đường hợp lệ duy nhất" của `threat_model.md` §1, và vì nó định phần an toàn của điểm cắm mà `neuroedge.sdk` sẽ đóng băng (FR-EXT-09).
> Nếu §9 câu 1 chọn khai ở `board.v1` thì RFC này chạm hàng đầu của §3 (sửa `schemas/board.v1.json`). Task: **TSK-I2c-04** (RFC này), **TSK-I2c-16** (hiện thực và adapter Home Assistant đầu tiên); phụ thuộc
> TSK-I2c-09 (dữ kiện đọc lại), TSK-I2c-11 (bộ nạp plugin), TSK-I2c-12 (bộ test tuân thủ). Quyết định nền: `neuroedge-prd.md` §15 **Q-67** (quyết định 5: cơ cấu từ xa có mức tự tắt, mức "không tự tắt" cấm cho hành động không hoàn tác),
> **Q-62** (lệnh về phía an toàn không bao giờ bị chặn; tự tắt bắt buộc; phong bì ghi bền; giám sát ngoài tiến trình), **Q-65** (RFC-0014: dữ kiện số, tuổi do bộ nhận đo, vắng ⇒ BLOCK), Q-57 (an toàn cao nhất), Q-53, Q-38.
> Đóng phần thiết kế của `TODOS.md` #55. Liên quan: RFC-0016 *Lõi an toàn dùng độc lập và Extension SDK* (bộ nạp, bật plugin, khung tuân thủ; chữ ký `Actuator` do RFC này chốt ở §3c), RFC-0017 *Nguồn gọi theo không gian tên và danh tính client* (không đổi bởi RFC này: lệnh tới cơ cấu từ xa không mang `source` riêng, nó đi sau phán quyết của gate như mọi lệnh tới chân).

## 1. Vấn đề

Hôm nay một hành động vật lý tới Home Assistant, ESPHome hay Matter chỉ có một đường mà `docs/spec/tool_calling.md` §10 quy tắc 2 cho phép: bọc thành `@action` có gate, và **thân hàm** gọi MCP hay HTTP của hệ đó. Gate quyết định *trước* thân hàm — và chỉ có vậy. Khoảng hở nằm ở chỗ token, phong bì và tự tắt chỉ canh một loại đích là chân của bo mạch:

1. **Token.** `Conversation._do` cấp token rồi chạy `spec.fn(**kwargs)` dưới `digital.grant` (`python/neuroedge/actions/conversation.py:210–224`). Token chỉ có nghĩa khi có ai gọi `TokenLedger.authorize` (`actions/token.py:116`), và chỉ có hai nơi gọi: `HardwareAbstractionLayer._admit` (`hal/__init__.py:270`) và `MotionController._command` (`hal/motion_core.py:474`). Một `httpx.post(...)` trong thân hàm không đi qua HAL nên không chạm sổ token.
2. **Phong bì và tự tắt.** `SafetyEnvelope.reserve` chỉ được gọi từ `_admit` (`hal/__init__.py:259`) và `_command` của motion (`hal/motion_core.py:463`). Hẹn giờ tự tắt là `HardwareAbstractionLayer._auto_off` (`:215`) và `LinuxHAL._arm` (`hal/linux.py:863`), đều theo chân của bo. Tiến trình giám sát chỉ giữ **line gpiod** (`hal/linux.py:451–466`; `hal/supervisor.py:4–20`): nó không với tới một thiết bị ở xa.
3. **Vết ghi.** `actuator_command` do HAL phát (`hal/sim.py:443`, `hal/linux.py:753`). Lệnh gửi từ thân hàm không để lại vết ghi nào về hiệu ứng, càng không về trạng thái thật của thiết bị.

| Đích | Gate | Token | Phong bì | Tự tắt / giám sát | Vết ghi hiệu ứng |
|:---|:---:|:---:|:---:|:---:|:---:|
| Chân `digital.out` của bo | có | có (`_admit`) | có | có (`_auto_off`, giám sát) | `actuator_command` |
| HTTP tới Home Assistant trong thân `@action` | có (chỉ cổng vào) | **không** | **không** | **không** | **không** |

Hệ quả: "đường hợp lệ duy nhất" (`threat_model.md` §1) đúng cho chân, **chưa đúng** cho thiết bị ở xa. Hàng `Tool bên ngoài có hiệu ứng vật lý` ở §2b chỉ nói hiệu ứng *phải* là `@action`, không nói thân hàm *được làm gì*.
`TODOS.md` #55 hoãn đúng vì thế: thiết bị ở xa không bảo đảm được "tự tắt" (Q-62). Q-67 quyết định 5 mở lại có điều kiện: cho phép, nhưng mỗi cơ cấu từ xa khai một mức tự tắt và mức "không tự tắt" bị cấm cho hành động không hoàn tác.

## 2. Vì sao cơ chế hiện tại không giải quyết được

- `board.v1` đóng: `capabilities` và `digital_out` đều `additionalProperties: false` (`schemas/board.v1.json`), không có chỗ khai một thực thể ở xa; và bo mạch khai **phần cứng**, không khai đồng cấp phần mềm hay cấu hình triển khai (cùng lập luận RFC-0014 §6). Bo tham chiếu dùng chung cho mọi triển khai, trong khi URL và thực thể Home Assistant là của từng nhà.
- Tập nguyên thủy đóng có chủ ý (FR-HAL-01), và nguyên thủy mở rộng phải có trên cả ba target (Q-53; cùng lập luận RFC-0014 §6); `esp32s3` không có bộ nạp plugin. Một nguyên thủy `remote.out` mới vừa vi phạm hai điều đó, vừa tách API khỏi `digital.out` nên mọi `@action`, gate, `commands.toml` hiện có không dùng lại được (§6).
- HAL chọn backend bằng `if target == "linux"` (`sim/session.py:917–942`), không có registry; RFC-0016 mở điểm cắm, nhưng không nói điểm cắm **cơ cấu** phải làm gì để giữ lời hứa an toàn. Đó là việc của RFC này.
- Các mảnh đã đủ dùng lại: phong bì khoá theo **tên** (`SafetyEnvelope.__init__(limits: Mapping[str, EnvelopeLimits])`, `hal/envelope.py:272–294`; `reserve(..., primitive=...)`, `:394–403`); token khoá theo tên chân từ `requires="digital.out:<tên>"` (`actions/spec.py:63–64`); `ended(at=…)` (`hal/envelope.py:539`) cho một lần bật kết thúc ở một thời điểm đã biết; `Actuator` Protocol của motion (`hal/motion_core.py:149`) là tiền lệ một backend cắm được. Thiếu: một **khai báo**, một **hợp đồng cho driver**, một **mô hình bảo đảm tự tắt** kiểm được, và một **mô hình trạng thái không chắc**.

## 3. Thay đổi đề xuất

### 3a. Phạm vi và ranh giới

Một **cơ cấu từ xa** là một thực thể mà NeuroEdge điều khiển qua một đường không nằm trong bo (hub, mạng, bus ngoài), do một plugin nhóm `neuroedge.actuators` (RFC-0016) lái.
Với agent, nó là **một chân `digital.out` có tên** — `digital.out("porch_light").pulse(seconds=…)` — nên `@action`, gate, `commands.toml` và bộ kiểm tool không đổi. Các giới hạn bản này, mỗi giới hạn có lý do:

| Giới hạn | Lý do |
|:---|:---|
| Chỉ `on`, `off`, `pulse`; **không** `pwm`, `motion.*`, độ sáng, mức tương tự | Mỗi thứ cần một hợp đồng "bị chặn bởi gì khi mất liên lạc" riêng (§9 câu 4); ghép vào đây làm mức tự tắt mất nghĩa chính xác |
| Chỉ target `sim` và `linux`; `esp32s3` ⇒ `neuroedge build` từ chối (`BoardCapabilityError`, NE3001) | Không có bộ nạp plugin trên MCU; cùng lập luận RFC-0014 §3i. Đường qua gateway thuộc I14 |
| `sim` luôn dùng **bản giả thiết bị** (double) của plugin, không bao giờ chạm thiết bị thật | Một phiên mô phỏng không được lái một cái van thật; thử trên thiết bị thật là target `linux` |
| NeuroEdge **không** là bộ điều khiển duy nhất của thiết bị | Người, automation của hub, công tắc tường cùng đổi trạng thái; NeuroEdge chỉ bảo đảm điều **nó** bật (§3g, "nợ tắt") |
| Plugin là mã người vận hành tin, chạy trong tiến trình (NFR-SEC-10, `threat_model.md` §3) | RFC này chặn **nhầm lẫn và treo**, không chặn plugin cố ý phá |

### 3b. Khai báo: `[actuators.<tên>]` ở `agent.toml`; `board.v1` không đổi

```toml
[requires]
"digital.out" = { pins = ["porch_light"] }     # tên cơ cấu từ xa nằm cạnh chân của bo (nếu có)

[actuators.porch_light]
plugin     = "home_assistant"       # tên entry point nhóm neuroedge.actuators; gói phải nằm trong [plugins] enable (RFC-0016 §3d)
safe_off   = "L1"                   # mức người triển khai dựa vào: L0 | L1 | L2 | L3. Không khai ⇒ build từ chối
reversible = true                   # không khai ⇒ false (không hoàn tác), §3f
[actuators.porch_light.envelope]    # bốn khoá của RFC-0007 §3d, bắt buộc đủ
window_s = 3600
max_on_ms_per_window = 1800000
min_interval_ms = 2000
max_continuous_ms = 600000
[actuators.porch_light.config]      # chuyển nguyên cho factory của plugin (§3c); dựng không I/O
url = "http://homeassistant.local:8123"
entity_id = "switch.porch_light"
token_env = "NE_HA_TOKEN"           # tên biến môi trường, không bao giờ là giá trị
```

| Luật (`AgentManifestError`, NE3002, gom vào `BuildFailed`, NE3003) | Lý do |
|:---|:---|
| Tên theo `^[a-z][a-z0-9_]{0,31}$`; không trùng chân, `enable_pin`, kênh `motion` của bo, hay cơ cấu khác | Một tên chỉ một đích; tên trùng chân của bo sẽ lái nhầm chân thật |
| `plugin`, `safe_off`, `envelope` (đủ bốn khoá, đúng `$defs/envelope` của `schemas/board.v1.json`, dùng lại định nghĩa) bắt buộc; `reversible` là `bool`, mặc định `false` | Mọi cơ cấu từ xa là cơ cấu chấp hành có phong bì (RFC-0007 §3d: mặc định là cơ cấu chấp hành); không khai ⇒ coi là xấu nhất |
| **Hai chiều:** mỗi `[actuators.X]` phải có trong `[requires] "digital.out".pins`; chiều ngược lại (tên không thuộc bo mà không có `[actuators.X]`) là NE3001 sẵn có của `check_capabilities` | Không khai thừa, không để một chân treo (cùng khuôn RFC-0014 §3c) |
| Khoá lạ; trường tên bí mật (`token`, `key`, `secret`, `password`) viết thẳng; `*_env` sai tên biến | Dùng lại `refuse_unknown`, `secret_fields`, `ENV_NAME` của `models/providers/common.py:38,91,117`; `agent.toml` được commit |

Các luật liên quan tới plugin (`safe_off` vượt `safe_off_level`, `readback`, `esp32s3`) là NE3001 ở §3f. Khai báo là **một cấu trúc dữ liệu có một hàm kiểm duy nhất**: `agent.toml` chỉ là một nguồn của nó; nguồn nào khác dựng nó từ mã (ví dụ API `neuroedge.guard` của RFC-0016) **phải** gọi cùng hàm lúc nạp.
Luật không vì thế bị bỏ qua khi không có `agent.toml`. Tên công khai của cấu trúc và hàm kiểm do TSK-I2c-16 quyết, ghim ở `docs/spec/python_api.md` và `tests/test_public_api.py` (như RFC-0014 §3g).

**Vì sao `agent.toml` mà không phải `board.v1`:** URL, thực thể, mức tự tắt và độ không hoàn tác là của *triển khai*, không phải của phần cứng; sửa `board.v1` là sửa lược đồ đóng băng (RFC-0015) và buộc bo tham chiếu mang cấu hình riêng của từng nhà. Cái giá: phong bì của cơ cấu từ xa nằm ở `agent.toml` chứ không ở bo như RFC-0007. Nó vẫn **độc lập với gate và với mã hành động** — thứ RFC-0007 §3d cần ("giới hạn phần cứng phải đứng được cả khi gate viết lỏng"); nó không độc lập với người viết `agent.toml`, mà người đó cũng là người cắm plugin. Quyết định thuộc §9 câu 1.

### 3c. Một đường duy nhất: `_admit`; Protocol `Actuator`

Cơ cấu từ xa đi **đúng** đường của chân, theo đúng thứ tự `require_pin → chốt trạng thái (§3g) → phong bì → authorize → record → driver`:

- `digital_out` của `sim` (`hal/sim.py:402`) và `linux` (`hal/linux.py:691`) rẽ ở đầu hàm: tên thuộc cơ cấu từ xa ⇒ gọi một hàm **dùng chung** của lớp cơ sở (không rẽ `if target` thêm), đi qua `_admit` (`hal/__init__.py:231`), rồi mới tới plugin. `require_pin` nhận tên cơ cấu từ xa như chân của bo; `esp32s3` không có đường này.
- **Plugin không có handle.** Lõi dựng plugin từ khai báo; chỉ HAL giữ tham chiếu và gọi `apply`/`safe_off`/`read_state` của nó, `apply` chỉ sau `_admit`. Plugin không nhận HAL, sổ token hay phong bì; mã agent không nhận plugin (không có `digital.out` nào trả plugin). Điều này kiểm được bằng cấu trúc (§7), và là lời hứa của FR-EXT-03: *actuator chỉ được HAL lái sau token và phong bì*.
- **Token không đổi.** Lệnh bật tiêu token của chân đó đúng một lần (`token.py:160–177`); `off` không cần token (RFC-0007 §3d). `ActionSpec.pins` đã lấy tên từ `requires="digital.out:<tên>"` (`actions/spec.py:63`), nên không cần thay `VerdictToken`.
- **Lệnh về phía an toàn.** `off` tới cơ cấu từ xa luôn được **thử**, không qua phong bì, không cần token, không chờ `min_interval_ms` (ngoại lệ duy nhất của `threat_model.md` §1, nay phủ thêm đích này). Chốt trạng thái §3g chỉ chặn lệnh *bật*.

**Protocol `Actuator` — nguồn duy nhất của chữ ký** (`neuroedge.sdk` chỉ xuất lại; RFC-0016 dẫn về đây). Giá trị entry point là `module:factory(config: Mapping[str, Any]) -> Actuator`, gọi một lần, **không I/O**; `config` sai ⇒ `ValueError(lý do)` và lõi đổi thành NE3002 ba phần. Mọi phương thức **đồng bộ**, chặn không quá `command_timeout_ms`, và HAL có thể gọi từ luồng hẹn giờ của nó ⇒ plugin tự bảo đảm an toàn luồng.

| Thành viên | Chữ ký | I/O | Ý nghĩa |
|:---|:---|:---:|:---|
| `safe_off_level` · `readback` | `Literal["L0","L1","L2","L3"]` · `Literal["push","poll","none"]` | không | Mức cao nhất chứng minh được **cho `config` đó** (§3d); cách đọc lại (§3e). Khai ngay lúc dựng |
| `tolerance_ms` · `command_timeout_ms` · `max_lease_ms` | `int ≥ 0` · `int > 0` · `int \| None` | không | Độ lệch tối đa hạn ↔ lúc thiết bị tắt; hạn chờ một lệnh; trần lease (`None` ngoài L3) (§3d) |
| `apply` | `apply(command: Command) -> None`, `Command(id: str, operation: "on" \| "renew", duration_ms: int \| None, lease_ms: int \| None)` | có | Chỉ HAL gọi, sau `_admit`. L2: `duration_ms` luôn có; L3: `lease_ms`, `renew` = gia hạn; L0/L1: không có. Trả về = hub/thiết bị **đã nhận**, không phải đã bật. Lỗi: `NotSent` · `Rejected` · `Ambiguous` |
| `safe_off` | `safe_off() -> None` | có | Lệnh về phía an toàn: **không token, không phong bì**, chạy cả khi sổ token từ chối mọi thứ, **lặp lại được** (đã tắt thì không lỗi). Cùng ba lỗi |
| `read_state` | `read_state() -> tuple[bool, int]` = `(đang_bật, observed_age_ms ≥ 0)` | `poll`: có | `push`: trả giá trị mới nhất đang giữ. Tuổi chỉ **cộng thêm**, bộ nhận đo mốc (RFC-0014 §3f). Không gọi khi `readback = none`. Lỗi: `ReadFailed` |
| `probe` | `probe() -> DeviceDouble` | không | Bản giả thiết bị trên đồng hồ ảo, đi qua **đúng** đường mã của ba phương thức trên; có `state() -> bool`, `cut_link()`, `heal_link()`, `advance(ms: int)` (§3e) |
| Lỗi | `NotSent` (chắc chắn chưa tới thiết bị) · `Rejected` (hub từ chối rõ ràng) · `Ambiguous` (hết giờ hay đứt sau khi gửi) · `ReadFailed` | | Lớp con của `ActuatorError` trong `neuroedge.sdk`; không phải mã `NE…`, không thêm mã (§3k) |

**Điều RFC này không làm được, nói thẳng:** thân `@action` vẫn gọi được SDK tuỳ ý trong Python (cùng loại mã có quyền ngang runtime, `threat_model.md` §3). RFC làm đường đúng **rẻ hơn** đường sai (khai ba mục TOML thay vì tự viết client) và thêm một cảnh báo ở `build`: module chứa `@action` mà nhập một client mạng phổ biến (`httpx`, `requests`, `aiohttp`, `urllib.request`, `socket`) ⇒ in cảnh báo (không chặn; heuristic, không đầy đủ) nhắc dùng cơ cấu từ xa. Cảnh báo này không phải chặn lối tắt (§5, rủi ro 5).

### 3d. Mức tự tắt

Mức là lời hứa về **ai** làm cơ cấu về `off` khi NeuroEdge không còn giúp được. Thứ tự L0 < L1 < L2 < L3; `D = min(thời hạn lệnh, max_continuous_ms)` (như RFC-0007 §3d; `on()` không thời hạn lấy `max_continuous_ms`).

| Mức | Ai giữ hẹn giờ | `on` mang theo | Bảo đảm **kiểm được** | Mất liên lạc / NeuroEdge treo |
|:---|:---|:---|:---|:---|
| **L0** `none` | Không ai | Không có thời hạn | Không có. HAL chỉ bảo đảm không bật chồng (`already_on`) cho tới khi *xác nhận* tắt, và phong bì đếm thời gian bật thật tới lúc đó | Thiết bị giữ trạng thái vô hạn |
| **L1** `host` | Tiến trình NeuroEdge (như `LinuxHAL._arm`) | Không có thời hạn; HAL hẹn `off` tại `D` | Nếu runtime sống **và** liên lạc thông: `off` được *gửi* trong ≤ `D + OFF_SLACK_MS`, gửi lại mỗi `OFF_RETRY_MS` tới khi xác nhận. Đây là bảo đảm về **nỗ lực**, không về hiệu ứng | Không bảo đảm gì: thiết bị có thể bật vô hạn |
| **L2** `device_timer` | **Thiết bị** | `on` kèm `duration_ms = D`, **không bao giờ vắng** | Sau khi thiết bị nhận lệnh, nó tự về `off` sau ≤ `D + tolerance_ms` mà không cần thông điệp nào nữa | Giữ nguyên: dù NeuroEdge treo, chết hay mạng đứt |
| **L3** `device_lease` | **Thiết bị** (thuê) | `on` kèm `lease_ms`; HAL gia hạn mỗi `lease_ms / 3` và **ngừng gia hạn** tại `start + D − lease_ms` (`D ≤ lease_ms`: một lease dài `D`, không gia hạn) | Thiết bị về `off` ≤ `lease_ms + tolerance_ms` sau lần gia hạn cuối nó nhận được ⇒ hạn tuyệt đối `start + D + tolerance_ms` | Runtime treo ⇒ gia hạn ngừng ⇒ tắt, không cần thông điệp "tắt" nào |

- L2 và L3 **không bỏ** L1: HAL vẫn gửi `off` sau hạn (§3g), nhưng như lớp dự phòng *sau* bảo đảm của thiết bị, nên bảo đảm được thử mỗi lần chạy (§3e).
- Gia hạn lease của L3 **không** là gia hạn thẩm quyền của RFC-0011 §3c: nó không bao giờ vượt `D` mà phong bì đã giữ trước. Muốn bật lâu hơn phải qua gate lần nữa, mà `already_on` chặn tới khi lần chạy kết thúc.
- `safe_off` ở `agent.toml` là mức người triển khai **dựa vào**, và không được vượt `safe_off_level` của plugin (§3c); vượt ⇒ NE3001, nên một bản plugin lỡ hạ mức làm build đỏ chứ không hạ lặng lẽ. Mức **không bao giờ được đoán hay nâng lúc chạy** (cùng tinh thần Q-35: không khai thì xấu nhất). `tolerance_ms` là độ lệch tối đa giữa hạn tính từ lúc HAL gửi và lúc thiết bị thật sự tắt (hẹn giờ thiết bị, độ trễ giao lệnh — gồm `command_timeout_ms` — và độ trễ đọc lại).
- Hằng `OFF_SLACK_MS`, `OFF_RETRY_MS`, `max_state_age_ms` chốt ở §9 câu 5 (Q-68).

### 3e. Một mức được chứng minh thế nào

Hai chứng cứ, bổ sung nhau. `neuroedge build` **không** chạy P1 (nó là điều kiện huy hiệu của RFC-0016, và người vận hành chọn plugin); build chỉ kiểm khai báo. P2 chạy ở runtime, mỗi lệnh.

**P1 — bộ test tuân thủ với bản giả thiết bị** (`neuroedge conformance`, TSK-I2c-12; vector ở `fixtures/compliance/actuators/`). Plugin kèm một **double** của thiết bị, dựng ở `probe()` (§3c) và chạy trên đồng hồ ảo; thiếu `probe()` ⇒ `unverifiable`, không huy hiệu (RFC-0016). Phép kiểm `actuator.level_proven` chạy vector của mức plugin khai (`safe_off_level`) **và** phải bắt được double nói dối (mỗi phép kiểm có một ca phản chứng):

| Mức | Vector (double ngắt liên lạc / đóng băng runtime) | Ca phản chứng phải bị bắt |
|:---|:---|:---|
| L0 | Plugin không khai mức nào cao hơn thực có; `on` không mang thời hạn | Plugin khai L2 mà `on` không mang `duration_ms` |
| L1 | Ngắt liên lạc đúng lúc hạn ⇒ HAL **không** tuyên bố đã tắt, vào `uncertain`, gửi lại mỗi `OFF_RETRY_MS` | Plugin báo "đã tắt" khi chưa nhận được xác nhận |
| L2 | (a) `on` luôn mang `duration_ms ≤ D`; (b) ngắt liên lạc ngay sau khi giao lệnh ⇒ tới `D + tolerance_ms` double ở `off`; (c) ngắt trước khi giao ⇒ double không bật quá `D` | Double **bỏ qua** hẹn giờ ⇒ vector (b) đỏ |
| L3 | (a) đóng băng runtime (không thông điệp) ⇒ `off` ≤ `lease_ms + tolerance_ms`; (b) gia hạn trùng hoặc đảo thứ tự không đẩy hạn quá `start + D + tolerance_ms`; (c) `lease_ms` không vượt trần plugin khai | Double bỏ qua lease ⇒ (a) đỏ |
| Mọi mức | `off_is_idempotent` (gọi `safe_off` ≥ 2 lần); `off_is_unconditional` (chạy khi sổ token từ chối mọi thứ); `builds_without_io` (chốt chặn `socket`); `classifies_errors` (`NotSent` / `Rejected` / `Ambiguous`, §3g); `receives_no_handles` (không nhận HAL, sổ token, phong bì — kiểm chữ ký dựng) | `safe_off` đòi token; plugin giữ tham chiếu tới HAL |

P1 chứng minh **cách plugin dựng lệnh** đúng với giao thức thiết bị; nó **không** chứng minh phần sụn thật tôn trọng lệnh.

**P2 — đọc lại trạng thái thành dữ kiện, mỗi lần chạy.** Với L2 và L3, HAL **không gửi `off` của mình trước** `hạn + tolerance_ms` (L2) hay `start + D + tolerance_ms` (L3); tại đó nó đọc lại trạng thái: đã `off` ⇒ thiết bị tự tắt đúng mức đã khai (bằng chứng, ghi `remote_state`); vẫn `on` ⇒ thiết bị **vi phạm mức nó khai**: HAL gửi `off` (về phía an toàn), vào `quarantined`, ghi `remote_level_violated`. Mỗi lệnh vì thế là một phép thử của mức, miễn phí, không cần thao tác thủ công; chỗ hở tối đa là `tolerance_ms` cộng một lần gửi lại. Không đọc lại được (`readback = none`) thì không có P2: HAL gửi `off` ở hạn như L1 và **mức L2/L3 chỉ còn dựa vào P1** ⇒ cấm cho không hoàn tác (§3f).

Trạng thái đọc lại là dữ kiện theo RFC-0014: số `0`/`1` với `range: { min: 0, max: 1 }`, mốc đọc do **bộ nhận** đo trên trục của phiên (plugin chỉ cộng thêm `observed_age_ms ≥ 0`, không tự khai tuổi). Plugin chạy trong tiến trình nên không qua ổ cắm và không cần xác thực nguồn của RFC-0014 §3d; mọi luật tuổi và *vắng ⇒ BLOCK* của §3f–§3i của RFC đó áp nguyên.
Cơ cấu có `readback` còn là một fact source trong tiến trình (TSK-I2c-09) với một dữ kiện 0/1, để gate muốn dùng thì khai `external_source` như thường. `uncertain` và `quarantined` **không bao giờ** thành giá trị: chúng là dữ kiện *vắng* ⇒ `criterion_unavailable` ⇒ BLOCK.

### 3f. Luật D5: cấm "không tự tắt" cho hành động không hoàn tác

**Định nghĩa.** `reversible = true` là lời khai của người triển khai rằng *để cơ cấu bật cho tới khi có người nhận ra thì không gây hại* (nhiệt, nước, điện, cơ khí, an ninh, liều) *và `off` trả đúng trạng thái cũ* — "hoàn tác được và rủi ro thấp" là **một** khai báo. Mọi thứ khác, kể cả không khai, là **không hoàn tác**.
Một `@action` là không hoàn tác nếu `requires` của nó có một cơ cấu từ xa không hoàn tác. Lớp được khai **một lần, ở cơ cấu**, không ở từng `@action` (§6).

| `reversible` | Mức tối thiểu | Điều kiện thêm | Vi phạm |
|:---|:---|:---|:---|
| `true` | L0 trở lên (L0 in cảnh báo ở build) | — | — |
| `false` (mặc định) | **L2** (FR-EXT-07: thiết bị tự tắt được dù mất liên lạc) | `readback ≠ none` (nếu không, P2 không có, §3e) | `safe_off` thấp hơn ⇒ **NE3002**; `safe_off_level` của plugin thấp hơn mức đó hoặc `readback = none` ⇒ **NE3001** |

Lỗi ba phần, ví dụ:

```
NE3002 AgentManifestError
  where: agent.toml -> [actuators.garage_valve] safe_off
  why:   the actuator is irreversible (reversible is not true) and declares safe_off = "L1": this runtime sends the off, so a lost link or a frozen runtime leaves the valve open
  how:   use a plugin and device kind that reach L2 or L3 and set safe_off to it, or — only if leaving it on harms nothing — set reversible = true (RFC-0018 §3f)
```

Kiểm ở **hai chỗ**: `neuroedge build` (`engine/compiler.py`, cạnh `check_motion_leases`) và lúc nạp (cùng hàm kiểm của §3b), để không đường nào vào HAL mà bỏ qua luật. NE3001 cũng áp khi `[actuators]` có mặt với `--target esp32s3`.

### 3g. Trạng thái, mất liên lạc và chốt trước phong bì

HAL giữ cho mỗi cơ cấu từ xa một trạng thái **của HAL** (không phải của thiết bị): `off` (đã xác nhận), `on` (có lệnh bật của NeuroEdge đang sống), `uncertain`, `quarantined`.

- **Chốt bật.** Lệnh `on`/`pulse` chỉ qua khi trạng thái là `off` với mốc đọc không cũ hơn `max_state_age_ms` (không có `readback`: xem dưới). Ngược lại ⇒ `EnvelopeRefusedError` (NE1003) **trước phong bì và `authorize`** (như `supervisor_unavailable`, `hal/linux.py:720–734`): không giữ trước, không tiêu token, ghi `envelope_refused` với `reason` mới
  `actuator_state_unknown` (`uncertain`, hoặc mốc quá cũ), `actuator_quarantined` hoặc `already_on` (đọc lại thấy `on` mà NeuroEdge không bật: không bật chồng lên điều của bộ điều khiển khác).
- **Vào `uncertain`:** lệnh gửi hết `command_timeout_ms`; mất kênh đọc lại; mốc đọc quá cũ; khởi động lại (không còn tri thức nào). **Ra khỏi `uncertain`:** **chỉ** bằng một lần đọc lại `off` có mốc tươi *sau* khi liên lạc trở lại — không bằng hẹn giờ, không bằng "đợi đủ lâu", vì hẹn giờ không biết thiết bị đang ra sao.
  Không có `readback` (thiết bị chỉ ghi; chỉ được với `reversible = true`, §3f): `off` là lần `off` được xác nhận gần nhất, không có hạn tuổi. Đọc lại báo `on` ngoài dự kiến (lệnh đến muộn) ⇒ HAL gửi `off` ngay.
- **Nợ tắt.** HAL chỉ gửi `off` khi còn *nợ tắt*: một lệnh bật **của NeuroEdge** chưa được xác nhận tắt. Nó không bao giờ tắt thiết bị mà nó không bật, và **không** gửi `off` khi khởi động trừ khi bản ghi ghi bền (§3h, thêm cờ `off_owed`) còn nợ ở L0/L1. `off` (qua `safe_off()`) luôn được thử (cả ở `close()`), gửi lại mỗi `OFF_RETRY_MS`, không bao giờ bị từ chối, không cần token; thất bại **không** ném lỗi cho gọi `off` (lệnh về phía an toàn không được nằm sau một ngoại lệ) mà ghi `remote_command_failed`.
- **Lỗi gửi do plugin phân loại (§3c), HAL không đoán.** `NotSent` và `Rejected` ⇒ hoàn lại phần giữ trước (`envelope.refund`) và trạng thái giữ nguyên. `Ambiguous` ⇒ **không hoàn**, vào `uncertain`, phần giữ trước ở lại: lệnh có thể đã tới (cùng nguyên tắc "phía an toàn của việc không biết", `hal/linux.py:772–774`, `:821`).
  Lệnh *bật* không bao giờ được tự gửi lại (lặp một lệnh không có khoá chống lặp là bật hai lần); chỉ `off` được gửi lại.
- **`quarantined`** (thiết bị vi phạm mức đã khai, §3e): từ chối mọi lệnh bật tới khi người vận hành gỡ bằng thao tác tường minh trên bản ghi trạng thái (cùng chỗ với bản ghi phong bì, RFC-0007 §3d); không có đường tự gỡ. Bản ghi không đọc được ⇒ coi là `quarantined`.

### 3h. Phong bì và giám sát

Cùng bốn khoá và cùng `SafetyEnvelope` (khoá theo tên), cùng thứ tự `_admit`; `envelope.py` chỉ đổi một chỗ: cơ cấu từ xa luôn do **HAL** kết thúc (`virtual = False` theo tên, cả trên `sim`), để hai target cho cùng kết quả.

| Khoá | Ý nghĩa với cơ cấu từ xa |
|:---|:---|
| `max_continuous_ms` | Trần của `D` (L2 gửi `duration_ms = D`; L1 hẹn `off` tại `D`; L3 ngừng gia hạn ở `start + D − lease_ms`). Trần vật lý là `D + tolerance_ms` — phần dư là sai số plugin khai, **được tính vào cửa sổ**; `neuroedge build` đòi `max_continuous_ms > tolerance_ms` (NE3001) |
| `max_on_ms_per_window` | Thời gian giữ trước là `D`; HAL gọi `ended(at=…)` tại **lúc nó biết** cơ cấu đã tắt (đọc lại), hay tại hạn bảo đảm (`hạn + tolerance_ms`) với L2/L3 khi không có `readback` — không sớm hơn. L0 và `uncertain`: lần bật vẫn *đang đếm* (`_settle`, `hal/envelope.py:610–611`: bật quá hạn ⇒ khoảng kéo dài tới bây giờ) — chỉ có thể từ chối nhiều hơn, không bao giờ ít |
| `min_interval_ms` | Tính từ lúc lần bật trước *kết thúc* theo nghĩa trên; chỉ áp cho lệnh bật |
| `window_s` | Như RFC-0007 |

- **Ghi bền write-ahead** như RFC-0007 §3d (`FileEnvelopeStore`, theo tên cơ cấu); sau khởi động mọi cơ cấu từ xa là `uncertain` cho tới lần đọc lại đầu, kể cả khi bản ghi sạch.
- **Giám sát ngoài tiến trình (RFC-0007 §3d, Q-62) không áp được:** tiến trình giám sát chỉ giữ line gpiod (`hal/linux.py:451–466`); tên cơ cấu từ xa **không** thuộc `_supervised`, nên `supervisor_unavailable` không áp cho nó. Cái thay thế theo mức: **L0, L1 — không có gì ngoài tiến trình** (hẹn giờ L1 chết cùng runtime; đó là lý do L1 không đủ cho không hoàn tác);
  **L2 — hẹn giờ ở thiết bị**; **L3 — lease ở thiết bị, và nhịp tim chính là gia hạn** (runtime treo ⇒ gia hạn ngừng). P1 chứng minh trường hợp "runtime đóng băng" ở double (§3e).

### 3i. Vết ghi và replay

`trace.v1` không đổi (`type` mở, `data` tự do); sự kiện thêm vào `docs/spec/simulation_coverage.md` §3 khi hiện thực:

| Sự kiện | Dữ liệu |
|:---|:---|
| `actuator_command` *(sẵn có, **không đổi hình dạng**)* | `{pin, operation, duration_ms}` — phát lúc lệnh được nhận như mọi chân; `testing/player.py:173` vẫn nhận ra mốc lệnh |
| `remote_command_sent` | `{actuator, command_id, operation, duration_ms?, lease_ms?, level, plugin}` |
| `remote_command_acked` · `remote_command_failed` | `{actuator, command_id, latency_ms}` · `{actuator, command_id, kind}`, `kind` ∈ `not_sent` · `ambiguous` · `rejected` |
| `remote_state` | `{actuator, state, via, read_offset_ms}`, `state` ∈ `on` · `off`, `via` ∈ `push` · `poll`; tuổi do bộ nhận đo |
| `remote_state_unknown` · `remote_state_confirmed` | `{actuator, why, since_offset_ms}`, `why` ∈ `command_timeout` · `link_lost` · `stale` · `restart` · `readback_failed` · `{actuator, state, unknown_ms}` |
| `remote_level_violated` | `{actuator, level, expected_off_ms, observed}` |

Lint ngữ nghĩa ở `python/neuroedge/trace.py` (như `lint_vision`; vi phạm ⇒ `TraceValidationError`, NE4001): `remote_command_sent` với `operation ≠ off` mà không có `actuator_command` cùng chân ngay trước nó trong cùng bước — tức một lệnh bật tới thiết bị ở xa không có dấu vết đã qua đường §3c — là vết ghi sai.
**Replay chỉ dùng điều đã ghi:** `ReplaySession` không dựng plugin, không đọc biến môi trường chứa khoá, không mở kết nối (có test chặn `socket`); HAL replay nhận trạng thái từ `remote_state` đã ghi (`script_remote_state`, theo mẫu `script_digital_in` / `script_pin_state`, `hal/__init__.py:552`, `:626`), nên một lệnh bật bị `actuator_state_unknown` lúc ghi bị từ chối y như vậy lúc phát lại. Sự kiện `remote_*` là thông tin, không vào so khớp phán quyết. Ba vết ghi chuẩn mực không có cơ cấu từ xa nên không đổi.

### 3j. Adapter đầu tiên: Home Assistant (TSK-I2c-16)

**Điều Home Assistant cung cấp** (đọc từ tài liệu `home-assistant.io` và `developers.home-assistant.io` ngày 2026-10-04; điều chưa đọc được ghi "chưa kiểm"):

| Điều | Chi tiết |
|:---|:---|
| REST | Mọi lời gọi kèm `Authorization: Bearer <Long-Lived Access Token>`; `GET /api/states/<entity_id>` trả trạng thái hiện tại; `POST /api/services/<domain>/<service>` trả "danh sách trạng thái đã đổi **trong lúc** dịch vụ chạy" — **không** phải bảo đảm về hiệu ứng ở thiết bị; mã 200/201 và 400/401/404/405; hạn chờ API: chưa kiểm |
| WebSocket | Bắt tay `auth_required` → `auth` (`access_token`) → `auth_ok` / `auth_invalid`; lệnh `call_service`, `subscribe_events` (lọc `event_type`), `get_states`; `ping`/`pong` kiểm kết nối. Tên sự kiện đổi trạng thái của thực thể: chưa kiểm ở trang đã đọc |
| Dịch vụ `switch` | `switch.turn_on`, `switch.turn_off`, `switch.toggle`; tài liệu **không** nêu tham số thời hạn hay hẹn giờ tự tắt |
| `script` | Có hành động `delay` và chế độ `single`/`restart`/…; hẹn giờ này chạy **trong Home Assistant**, không ở thiết bị; hành vi khi HA khởi động lại: chưa kiểm |
| Thiết bị nền | Matter: lệnh `OnWithTimedOff` (0x42) mang `OnTime` (đơn vị 1/10 giây), thuộc tính năng Lighting (LT) của cụm On/Off nên không phải mọi thiết bị có — nguồn là tài liệu tham chiếu cụm của bên thứ ba, **chưa kiểm** với đặc tả Matter. ESPHome: `api.reboot_timeout` (mặc định 15 phút) khởi động lại khi "no client connects to the API" — không gắn với gia hạn của NeuroEdge nên **không** phải lease của ta; hành động `on_turn_on` có `delay` có chạy trên thiết bị hay không: chưa kiểm |

**Mức Home Assistant đạt.** Qua `switch.turn_on` / `switch.turn_off` chung, plugin `home_assistant` khai **L1** cho mọi thực thể: lệnh bật không mang thời hạn (dịch vụ `switch` không có tham số đó) và hẹn giờ là của NeuroEdge. Một `script` có `delay` là hẹn giờ ở hub: sống sót khi NeuroEdge treo nhưng không khi hub chết hay hub mất liên lạc với thiết bị — **không phải L2** (L2 đòi hẹn giờ ở thiết bị), và không được tính cho D5.
L2/L3 chỉ đạt được với một loại thiết bị mà bản thân giao thức của nó mang thời hạn hay lease (ví dụ Matter `OnWithTimedOff`, một dịch vụ ESPHome tự có hẹn giờ trong firmware — cả hai chưa kiểm), qua một nhánh adapter riêng **có vector P1 riêng**; adapter bản đầu không khai chúng. Hệ quả: với Home Assistant, **hành động không hoàn tác bị build từ chối** (NE3002; NE3001 nếu khai L2) — đúng lời hứa FR-EXT-07, không phải lỗi.

Hiện thực: lái bằng REST (`POST /api/services/...`) hoặc WebSocket (`call_service`); đọc lại bằng `GET /api/states/<id>` định kỳ (`poll`) hay `subscribe_events` (`push`); `token_env` như §3b; lời gọi dịch vụ trả 200 **không** làm trạng thái thành `off` — chỉ đọc lại. Trạng thái Home Assistant báo là **niềm tin của hub** về thiết bị (có thể là lạc quan, chưa kiểm), nên `readback` của plugin này không bắt được thiết bị nói dối tới hub (§5, rủi ro 2).
Kiểm bằng **bản giả của Home Assistant** (REST và WebSocket tối thiểu) chạy qua vector L0–L1 của §3e; chạy trên một Home Assistant thật là bước của người (roadmap TSK-I2c-16). Chiều ngược — Home Assistant gọi NeuroEdge — là MCP có xác thực đã có (Q-58), không thuộc RFC này.

### 3k. Mã lỗi

Không thêm mã. NE1003 `EnvelopeRefusedError` thêm `reason`: `actuator_state_unknown`, `actuator_quarantined` (và dùng `already_on` có sẵn); NE3001 `BoardCapabilityError`: `safe_off` vượt `safe_off_level` của plugin, `readback = none` cho không hoàn tác, `max_continuous_ms ≤ tolerance_ms`, `[actuators]` với `esp32s3`, `pwm` hay `motion` tới tên cơ cấu từ xa; NE3002 `AgentManifestError`: §3b và vi phạm D5 (§3f); NE4001 `TraceValidationError`: lint §3i.
`reason` không nằm trong `schemas/error-codes.v1.json` (chỉ `fields: ["reason"]`), nên chỉ sửa lời ở PRD Phụ lục B và docstring `EnvelopeRefusedError` (`errors.py:76`).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — `[actuators]` là khối tuỳ chọn; không `agent.toml`, bo, gate hay vết ghi nào của kho có nó. `board.v1` không đổi |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có, đúng một loại: `agent.toml` có `[actuators.<tên>]` đúng §3b. `agent.toml` không có lược đồ trong `schemas/`. *Bản `neuroedge` cũ đọc nó bỏ qua khối lạ, nhưng tên cơ cấu không có trên bo nên `[requires]` bị từ chối (NE3001)* — fail-closed, không phải vỡ tương thích |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không. `trace.v1` không đổi (`type` mở); `board.v1` không đổi; `error-codes.v1` không đổi |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — không chạm `gate.v1` |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — không có cơ cấu từ xa; `actuator_command` giữ nguyên hình dạng |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không — `esp32s3` không có cơ cấu từ xa (NE3001) |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không — `@action` và tool giữ nguyên; thêm corpus `fixtures/actuators/` (hợp lệ/không hợp lệ + `expected_errors.yaml`, khép kín hai chiều; thêm dòng vào bảng `CONTRIBUTING.md` §3) |
| Mã lỗi (PRD Phụ lục B) | Không mã mới; nới nguyên nhân NE1003, NE3001, NE3002 (§3k) |
| API Python công khai | Tên công khai mới (khai báo, hàm kiểm, hợp đồng driver) vào `neuroedge.sdk` theo RFC-0016, ghim ở `docs/spec/python_api.md` và `tests/test_public_api.py`; không đổi `neuroedge.__all__` hiện có |
| Bất biến `sim` không giàu hơn bo (`CHANGELOG.md` §3.3 #7) | Không áp: cơ cấu từ xa không phải năng lực bo; nhưng double của `sim` không được hứa mức cao hơn `safe_off_level` của plugin (P1) |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn, không đường mới tới cơ cấu:** cơ cấu từ xa chỉ tới được qua `_admit` (§3c); plugin không có handle; phong bì chỉ biết từ chối; token không đổi. `gate.v1` và năm nguyên tắc kế thừa không đổi.
- **Fail-closed mọi hướng (`CHANGELOG.md` §3.3 #2):** không khai `reversible` ⇒ không hoàn tác; không khai `safe_off` ⇒ build từ chối; không `readback` ⇒ cấm không hoàn tác; trạng thái không chắc ⇒ từ chối bật; lỗi gửi mơ hồ ⇒ không hoàn phần giữ trước; bản ghi hỏng ⇒ coi là `quarantined`; thiết bị vi phạm mức ⇒ cách ly. Chỗ duy nhất "nới" là `off`.
- **Lệnh về phía an toàn không bao giờ bị chặn (Q-62):** `off` tới cơ cấu từ xa luôn được thử, không phong bì, không token. Chốt §3g chỉ từ chối lệnh *bật*. Ngoại lệ duy nhất của `threat_model.md` §1 phủ thêm đích này, **không** thêm ngoại lệ nào khác (không có cờ `[lab]` hay thao tác thử bỏ qua gate).
- **Không phải an toàn chức năng được chứng nhận (Q-38, `threat_model.md` §3b):** một cơ cấu từ xa không bao giờ là nút dừng khẩn; thiết bị gây hại được cho người vẫn cần ngắt phần cứng không qua phần mềm.
- **Rủi ro còn lại — không loại được ở lõi:**
  1. **Phân vùng mạng.** L0/L1: cơ cấu có thể bật vô hạn — vì thế cấm cho không hoàn tác và `uncertain` chặn bật tiếp. L2/L3: tắt trong `D + tolerance_ms` nhờ thiết bị; NeuroEdge không biết trạng thái cho tới khi liên lạc trở lại.
  2. **Phần sụn nói dối hoặc hub tin sai.** `readback` là lời của chính thiết bị (hay của hub, với Home Assistant). P2 bắt được thiết bị *mâu thuẫn* với mức nó khai; không bắt được thiết bị báo `off` khi vẫn đang chạy. Giảm bằng: cơ cấu không hoàn tác có ngắt phần cứng độc lập; gate ghép thêm một tiêu chí do lõi tin cậy (RFC-0014 §5 rủi ro 1).
  3. **Đồng hồ.** Mọi thời hạn gửi đi là **khoảng** (`duration_ms`, `lease_ms`), không bao giờ mốc tuyệt đối: lõi không phụ thuộc đồng hồ thiết bị hay đồng hồ treo tường; sai số hẹn giờ thiết bị nằm trong `tolerance_ms` (plugin khai, P1 kiểm trên double — **không** kiểm được trên thiết bị thật). Lệnh bị kẹt rồi giao muộn: bị chặn bởi `command_timeout_ms`, và nếu vẫn tới, lần đọc lại thấy `on` ngoài dự kiến ⇒ `off` (§3g).
  4. **Bộ điều khiển khác.** Người, automation của hub hay công tắc tường đổi trạng thái thiết bị; NeuroEdge chỉ chịu trách nhiệm điều nó bật, không tắt thứ nó không bật.
  5. **Thân `@action` đi vòng.** Python không chặn được một client mạng gọi thẳng trong thân hàm; cảnh báo ở build (§3c) chỉ là heuristic. Kẻ cùng quyền với runtime ngoài phạm vi (`threat_model.md` §3).
  6. **`reversible = true` khai sai.** Đó là lời khai không kiểm bằng máy được; mặc định `false`, lời khai nằm trong `agent.toml` được commit và vết ghi của phiên mang mức đã khai.
  7. **Plugin xấu hoặc có lỗi** chạy trong tiến trình (NFR-SEC-10): P1 chỉ bắt lỗi dựng lệnh, không bắt mã độc, và build không kiểm P1 — một plugin chưa tuân thủ vẫn nạp được nếu người vận hành bật nó (nguồn gốc vào vết ghi, RFC-0016 §3d).
- Cần kỹ thuật trưởng duyệt vì RFC thêm luật lên đường tới cơ cấu chấp hành.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Giữ nguyên: lệnh từ xa là thân `@action` thường | §1: không token, không phong bì, không tự tắt, không vết ghi hiệu ứng; đúng điều `TODOS.md` #55 hoãn |
| Đòi **L3 ở mọi nơi** | Thiết bị phổ thông (đèn, ổ cắm qua hub) không đạt; luật không ai đáp ứng được sẽ bị đi vòng bằng đường thân hàm tệ hơn. D5 chỉ cấm "không tự tắt" cho không hoàn tác |
| Nguyên thủy mới `remote.out` ở HAL | FR-HAL-01 đóng tập; Q-53 đòi ba target; tách API khỏi `digital.out` nên `@action`, gate, `commands.toml` không dùng lại; RFC-0014 §6 đã bác lập luận tương tự cho `external.in` |
| Khai ở `board.v1` (`capabilities.remote_out`) | Sửa lược đồ đóng băng; bo là phần cứng, không phải cấu hình triển khai; bo tham chiếu dùng chung nên không giữ URL/thực thể được; bo cộng đồng (RFC-0002, `--board <đường dẫn>`) tự chứng nhận nên mang số an toàn do chính tác giả nó khai. Giữ ở §9 câu 1 |
| Khai không hoàn tác **theo `@action`** (tham số decorator) | Hai action lái cùng một cơ cấu với lớp khác nhau thì lớp yếu thắng; khai nằm trong mã mà build không thể kiểm đủ; lớp là tính chất của cơ cấu |
| Khai mức tự tắt hay độ hoàn tác **trong gate** | `gate.v1` không biết nó gắn vào cơ cấu nào (RFC-0014 §9.8); đổi `gate.v1` và digest |
| Tin mức đã khai, không cần bằng chứng | Mức thành nhãn; plugin hay người triển khai khai cao hơn thực có. Cần P1 (dựng lệnh) và P2 (đọc lại mỗi lần chạy) |
| Mở rộng tiến trình giám sát để gửi lệnh `off` dựng sẵn khi mất nhịp tim ("L1 có giám sát") | Giám sát nhỏ có chủ ý (chỉ gpiod, `supervisor.py:4–20`); nhét client HTTP/TLS và khoá vào đó phá lý do tồn tại; và vẫn không phải bảo đảm phía thiết bị. Có thể là RFC sau nếu cần |
| Hoàn phần giữ trước khi gửi lỗi bất kỳ | Lỗi mơ hồ có thể đã giao lệnh; hoàn lại cho phép lần bật thứ hai chạy chồng khi lần đầu còn sống |
| Coi HTTP 200 của hub là "đã tắt/đã bật" | Tài liệu REST: phản hồi là các trạng thái đổi *trong lúc* chạy dịch vụ, không phải hiệu ứng ở thiết bị |
| `uncertain` tự hết sau một khoảng thời gian | Hẹn giờ không biết thiết bị ra sao; chỉ lần đọc lại tươi mới biết |
| Gửi `off` tới mọi cơ cấu khi khởi động | Sẽ tắt thứ người hay bộ điều khiển khác đã bật; chỉ trả "nợ tắt" của chính mình |
| Plugin tự dò hay nâng mức lúc chạy | Mức được khai và chứng minh, không đoán (Q-35: không khai thì xấu nhất) |
| `sim` nối thiết bị thật bằng cờ | Một phiên mô phỏng không được lái van thật; thử thật là `linux` hoặc bước của người |

## 7. Bằng chứng kiểm chứng

Mọi dòng là **việc phải có khi hiện thực** (TSK-I2c-16); chưa tick vì RFC này chưa có mã. Mọi corpus khép kín hai chiều (`CONTRIBUTING.md` §3).

- [x] **Corpus khai báo** (`fixtures/actuators/{valid,invalid}/` + `expected_errors.yaml`): khai báo hợp lệ cho từng mức; không khai `safe_off`, mức lạ, thiếu khoá phong bì, tên trùng chân của bo, thiếu chiều nào của §3b, khoá lạ, bí mật viết thẳng ⇒ NE3002; `safe_off` vượt `safe_off_level`, `readback = none` cho không hoàn tác, `max_continuous_ms ≤ tolerance_ms`, `esp32s3`, `pwm`/`motion` lên tên từ xa ⇒ NE3001
- [x] **Luật D5** (`python/tests/test_remote_actuator_build.py`): `test_an_irreversible_actuator_below_l2_is_refused_at_build`, `test_the_same_declaration_is_refused_at_load_without_agent_toml`, `test_reversible_is_false_when_not_declared`, `test_l0_builds_only_for_a_reversible_actuator_and_warns`, `test_an_irreversible_actuator_without_readback_is_refused`, `test_the_home_assistant_plugin_cannot_declare_an_irreversible_actuator`
- [x] **Chỉ có một đường** (`python/tests/test_remote_actuator.py`): `test_no_path_reaches_a_remote_actuator_without_a_valid_token`, `test_a_remote_actuator_plugin_receives_no_hal_no_ledger_and_no_envelope`, `test_the_order_is_require_pin_state_guard_envelope_authorize_record_apply`, `test_a_refused_remote_on_spends_no_token_and_holds_no_envelope`, `test_off_to_a_remote_actuator_needs_no_token_and_is_never_refused`
- [x] **Trạng thái và mất liên lạc:** `test_an_ambiguous_send_failure_holds_the_reservation_and_marks_the_actuator_uncertain`, `test_a_not_sent_failure_refunds_the_reservation`, `test_an_uncertain_actuator_refuses_on_but_still_sends_off`, `test_uncertain_ends_only_on_a_fresh_off_readback_never_on_a_timer`, `test_a_reading_of_on_nobody_commanded_is_already_on_not_a_command_to_turn_off`, `test_the_hal_turns_off_only_what_it_turned_on`, `test_a_restart_leaves_every_remote_actuator_uncertain`, `test_a_late_delivered_on_is_seen_by_readback_and_turned_off`
- [x] **Phong bì** (`python/tests/test_remote_actuator_envelope.py`): `test_the_remote_envelope_keys_have_the_meaning_of_rfc_0007`, `test_the_window_counts_until_the_hal_knows_the_actuator_is_off`, `test_the_physical_ceiling_is_max_continuous_plus_tolerance_and_is_counted`, `test_sim_and_linux_end_a_remote_on_the_same_way`, `test_the_remote_on_time_is_written_before_the_command_is_sent`, `test_a_corrupt_record_makes_a_remote_actuator_quarantined`
- [x] **Mức tự tắt trên double** (`fixtures/compliance/actuators/` + `neuroedge conformance`): phép kiểm `actuator.level_proven` cho L0–L3 của §3e, mỗi vector một ca phản chứng (`test_a_double_that_ignores_the_timer_fails_l2`, `test_a_double_that_ignores_the_lease_fails_l3`, `test_a_plugin_claiming_l2_without_duration_fails_l0_check`); `test_l2_sends_a_duration_on_every_on_never_none`, `test_l3_stops_renewing_before_the_ceiling_and_a_frozen_runtime_loses_the_device`
- [x] **P2:** `test_a_device_that_turns_itself_off_is_recorded_as_evidence`, `test_a_device_still_on_after_its_guarantee_is_commanded_off_and_quarantined`, `test_a_quarantined_actuator_refuses_every_on_until_the_record_is_cleared`, `test_uncertain_and_quarantined_are_absent_facts_so_a_gate_blocks`, `test_the_state_fact_age_is_measured_by_the_receiver`
- [x] **Vết ghi và replay:** `test_every_remote_command_sent_follows_an_actuator_command` (lint ⇒ NE4001 khi thiếu), `test_replay_never_builds_the_plugin_opens_a_socket_or_reads_the_key`, `test_replay_refuses_the_same_on_it_refused_when_recorded`, `test_the_canonical_traces_do_not_change`
- [x] **Home Assistant** (bản giả HA, `tests/`): `test_the_home_assistant_plugin_passes_the_l0_and_l1_vectors`, `test_a_200_from_a_service_call_is_not_a_confirmed_state`, `test_the_plugin_declares_l1_for_a_switch_and_nothing_higher`, `test_the_websocket_dropping_makes_the_actuator_uncertain`
- [x] **Ranh giới:** `test_esp32s3_refuses_an_agent_with_remote_actuators`, `test_build_warns_on_a_network_client_import_in_an_action_module`, `test_sim_never_uses_the_real_plugin`
- [x] **Hợp đồng công khai:** `tests/test_public_api.py` ghim tên mới, `test_the_actuator_protocol_signature_is_pinned` (chữ ký §3c, bốn lớp lỗi); `docs/spec/python_api.md` cập nhật
- [x] `neuroedge gate lint` và `neuroedge verify` xanh; `pytest -q` 0 failed, 0 skipped

## 8. Việc phải làm khi chấp thuận

- [x] `engine/compiler.py`: đọc `[actuators]`, kiểm §3b và D5 (§3f), nối vào `check_capabilities` (tên cơ cấu là chân khai được), cảnh báo import client mạng; cùng hàm kiểm dùng lúc nạp (TSK-I2c-16)
- [x] `hal/__init__.py` và mô-đun mới `hal/remote.py`: đường dùng chung §3c, trạng thái §3g, hẹn giờ `off`/gia hạn lease; `hal/sim.py`, `hal/linux.py` rẽ ở đầu `digital_out`; `script_remote_state`; `hal/envelope.py`: kết thúc theo tên do HAL (`virtual = False`) và gộp giới hạn của cơ cấu từ xa vào `SafetyEnvelope`; `sim/session.py` (`:917–942`, `_linux_envelope` `:645`): nối plugin (`linux`) hoặc double (`sim`), từ chối `esp32s3`
- [x] `python/neuroedge/trace.py`: lint §3i; `testing/player.py`: replay không chạm plugin
- [x] `Actuator` Protocol, `Command`, `DeviceDouble`, `ActuatorError` và bốn lớp lỗi vào `neuroedge.sdk` (TSK-I2c-11); bộ test tuân thủ cho loại `neuroedge.actuators` (TSK-I2c-12), double của Home Assistant và plugin `home_assistant` (TSK-I2c-16), dữ kiện đọc lại qua fact source trong tiến trình (TSK-I2c-09)
- [x] `docs/spec/threat_model.md`: §1 thêm cơ cấu từ xa vào "đường hợp lệ duy nhất" và vào ngoại lệ lệnh về phía an toàn; §2 thêm hàng cho từng đường tắt của §3g (bật khi `uncertain`, hoàn nhầm phần giữ trước, tắt thứ không bật); §5 thêm rủi ro 1–7. `docs/spec/tool_calling.md` §10 quy tắc 2: nói thêm "hoặc là cơ cấu từ xa" cho hiệu ứng vật lý
- [x] `docs/spec/simulation_coverage.md` §3: sáu sự kiện §3i; `docs/user/thuat-ngu.md`: mức tự tắt L0–L3, cơ cấu từ xa, nợ tắt, không hoàn tác
- [x] `neuroedge-prd.md`: Phụ lục B (nới nguyên nhân NE1003, NE3001, NE3002); FR-EXT-07 giữ nguyên lời; quyết định mới ở §9 cấp `Q-N` ở §15
- [x] `CONTRIBUTING.md` §3: thêm corpus `fixtures/actuators/` vào bảng "Thêm một fixture phản chứng"; `neuroedge-roadmap.md`: TSK-I2c-04 xong; `TODOS.md` #55: phần thiết kế đóng, phần Zenoh/kênh không tin cậy giữ lại
- [ ] `docs/rfc/README.md` (dòng RFC-0018) và `CHANGELOG.md` `[Chưa phát hành]`

## 9. Quyết định cho các câu hỏi mở (Q-68, 2026-10-04)

Q-67 chưa quyết các điểm dưới đây; RFC viết theo khuyến nghị. Kỹ thuật trưởng **chấp nhận khuyến nghị của mọi câu dưới đây**, theo nguyên tắc an toàn cao nhất của Q-57; mỗi khuyến nghị là quyết định (Q-68, 2026-10-04). Mục này là hồ sơ quyết định: §3–§8 lệch với nó thì sửa §3–§8.

1. **Khai cơ cấu từ xa ở `agent.toml` hay ở `board.v1`?** *Khuyến nghị: `agent.toml`* (§3b): cấu hình triển khai không thuộc phần cứng, và không sửa lược đồ đóng băng. Đánh đổi: phong bì nằm ở tệp của người triển khai, không ở hồ sơ bo. Chọn `board.v1` thì phải sửa `schemas/board.v1.json` (RFC, hàng đầu `CONTRIBUTING.md` §3), thêm khoá `capabilities` mới và quyết cách bo `sim-*` soi nó (bất biến #7).
2. **Đọc lại bắt buộc cho hành động không hoàn tác?** FR-EXT-07 đã đòi mức thiết bị tự tắt được (L2/L3); RFC này thêm `readback ≠ none`, vì không có nó P2 không tồn tại và mức chỉ còn là lời của plugin. *Khuyến nghị: bắt buộc.* Đánh đổi: một số thiết bị chỉ ghi, không đọc được, sẽ không dùng được cho không hoàn tác.
3. **Adapter Home Assistant đặt ở đâu** (roadmap TSK-I2c-16: "plugin trong `python/neuroedge/` hoặc kho riêng")? *Khuyến nghị: kho riêng, giấy phép do tác giả chọn (nên Apache-2.0)* (Q-67 quyết định 8) — nó là phép thử rằng SDK đủ cho bên thứ ba, nên không được dùng đường riêng nào của lõi; ngược lại, đặt trong lõi buộc nó vào PolyForm Noncommercial (Q-45) và buộc đội lõi bảo trì một tích hợp nó không sở hữu.
4. **`pwm`, độ sáng, `motion.*` cho cơ cấu từ xa** (đèn điều sáng của Home Assistant, servo từ xa): mỗi thứ cần định nghĩa "bị chặn bởi gì khi mất liên lạc" riêng. *Khuyến nghị: hoãn, RFC riêng khi có nhu cầu đo được*; bản này cấm bằng NE3001 để không ai dùng tạm mà không có bảo đảm.
5. **Các hằng của §3d, §3g** — `OFF_SLACK_MS`, `OFF_RETRY_MS`, `max_state_age_ms`, trần `command_timeout_ms` và `tolerance_ms` mà plugin được khai. *Khuyến nghị: kỹ thuật trưởng chốt khi duyệt, như RFC-0014 §9 câu 10*; đổi một hằng về sau là sửa đặc tả, nới giới hạn an toàn thì cần RFC. **Đã chốt (Q-68):** `OFF_SLACK_MS` = 100 ms · `OFF_RETRY_MS` = 500 ms · `max_state_age_ms` = 2000 ms · plugin khai `command_timeout_ms` ≤ 5000 ms · plugin khai `tolerance_ms` ≤ 2000 ms (vượt ⇒ NE3002). Đây là giá trị thận trọng chọn khi chưa có thiết bị thật; thu hẹp theo số đo của TSK-I2c-16.
6. **Cảnh báo import client mạng trong module `@action`** (§3c): *cảnh báo, không chặn* (khuyến nghị). Chặn sẽ sinh dương tính giả (mã đọc dữ liệu qua HTTP là hợp lệ) và vẫn không đầy đủ; nó chỉ là một lời nhắc, không phải rào chắn.
