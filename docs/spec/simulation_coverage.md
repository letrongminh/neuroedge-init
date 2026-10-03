# Phủ mô phỏng — 5 nguyên thủy × 3 target bậc 1

**Trạng thái:** đặc tả quy phạm, đi kèm Q-21 và Q-22 (*đã chốt*) — PRD §15. Tài liệu này nói **cái gì**
chạy và kiểm từng ô; ô nào đã xong là trạng thái của task tương ứng trong `neuroedge-roadmap.md`.
Công cụ và giấy phép: proposal Phụ lục H.4. Chiến lược theo tầng: proposal §3.2.

Tài liệu này trả lời một câu hỏi: **với mỗi nguyên thủy HAL trên mỗi target, cái gì chạy nó,
cái gì kiểm nó, và cái gì chưa kiểm được.** Mỗi ô của bảng ở §2 có một task chịu trách nhiệm;
ô nào chưa có task là một lỗ hổng.

## 1. "Phủ trọn vẹn" nghĩa là gì

Không bộ mô phỏng nào giả lập được âm học phòng, timing I2S hay áp lực bộ nhớ của ESP32-S3. Vì
vậy "trọn vẹn" không có nghĩa là mọi thứ chạy không cần phần cứng. Một ô được coi là **phủ** khi
đủ bốn điều:

1. **Backend chạy được** trên target đó, đúng hợp đồng HAL (FR-TGT-01/02/03).
2. **Sự kiện vết ghi chuẩn** cho mọi lần gọi (§3), để phiên được `record` và `replay`.
3. **Kiểm tự động** ở ít nhất một tầng: mỗi PR (không cần phần cứng), QEMU hằng đêm, hoặc bo
   mạch thật hằng đêm (TSK-S4-05).
4. **Ranh giới ghi rõ**: phần tầng đó không kiểm được được nêu ở cột "Chỉ phần cứng" và có một
   kiểm thử trên bo mạch.

## 2. Ma trận phủ

"PR" = chạy trên runner GitHub mỗi PR, không cần phần cứng. Trạng thái (xong / một phần / chưa)
không ghi ở đây: đọc task ở cột cuối trong bảng task của roadmap (`CONTRIBUTING.md` §8.1).

### `sim` — `sim-default` (mirror ESP32-S3-BOX-3, bất biến 7)

| Nguyên thủy | Backend | Kiểm ở | Task |
|:---|:---|:---|:---|
| `digital.out` | `SimHAL`, token dùng một lần; phong bì theo chân trong bộ nhớ, đồng hồ của phiên, chân tự về tắt tại hạn (ảo: `sim` không có hẹn giờ) — cùng số của bo mạch nó soi (bất biến 7) | PR | TSK-S2-01, S2-05, N2-01, N2-02 |
| `digital.out` — PWM *(chỉ bo mạch khai `digital_out.pwm`, vd. `sim-rpi5`)* | Thao tác `pwm` (`frequency_hz`, `duty`, `duration_ms` — cả ba bắt buộc) và `off`; `on`/`pulse` trên kênh PWM bị từ chối. Cùng giới hạn bo mạch, phong bì và lượng tử hoá `duty` về 0 như `linux`; `enable_pin` là của HAL (`pwm_enabled()`); `state()` trả `commanded`, hoặc `measured` từ `SimHAL.set_feedback()` khi bo mạch khai `feedback.pins` (REPL `:feedback`) | PR (`tests/test_pwm.py`) | TSK-W1-01 |
| `audio.in` | Gõ chữ → ngữ pháp lệnh (Q-15) · tệp WAV PCM 16-bit mono đúng `sample_rate_hz` của bo mạch (`--voice-file`; bo mạch không lấy mẫu lại nên `sim` cũng không) → khung 20 ms → VAD năng lượng → STT provider `[stt]` (`hal/audio.py`, `perception/voice_session.py`) | PR (gõ chữ, tệp WAV sinh trong test, provider giả) | WAV: TSK-S3-13 |
| `audio.out` | Chữ sẽ nói (`tts_stream_start`): câu trả lời knowledge base (RAG qua System 2, cục bộ khi mất mạng), lời hỏi lại của `on_block: ask` · âm thanh TTS provider `[tts]` lấy mẫu lại về `sample_rate_hz` của bo mạch, đặt trên dòng thời gian ảo, cắt khi bị nói chen, ghi ra WAV (`--voice-out`) | PR (provider giả) | chữ: TSK-S2-11 · WAV: TSK-S3-13 |
| `sensor.read` | Giá trị kịch bản: `[sim.sensors]` trong `agent.toml`, `:sensor` trong REPL và UI; dữ kiện gate từ cảm biến: `[sim.sensor_facts]`; `sensor.read()` trong `@action` | PR | TSK-S3-23 |
| `display` | Khung chữ hoặc điểm ảnh RGB565/RGB888 trong bộ nhớ, kiểm độ phân giải; digest SHA-256; `display.show()` trong `@action` | PR | TSK-S3-23 |
| `i2c` *(chỉ bo mạch khai `i2c`, vd. `sim-rpi5`)* | Giá trị kịch bản `SimHAL.set_i2c()` / dãy `script_i2c()` (replay), qua đúng allow-list của `linux`; không quét bus, không bịa số đọc — chưa đặt giá trị ⇒ `PerceptionUnavailableError` (NE5001); `i2c.read()` trong `@action` | PR | TSK-I2a-03 |
| *Trực quan* | Terminal · `trace view` HTML tĩnh · `run --ui` và `mcp serve --ui` web cục bộ (FR-TGT-06) | PR | TSK-S3-22, S2-09, S3-27 |

**Dữ kiện gate từ cảm biến — `[sim.sensor_facts]`.** Mỗi dòng `tiêu_chí = { sensor = "…", <luật> }`
tính một dữ kiện gate từ số đọc, như nhau trên `sim` (giá trị kịch bản) và `linux` (số đọc kernel).
Mỗi cảm biến được đọc **một lần mỗi lần tính dữ kiện gate** (`gate_facts`: các tool call của một lượt
lệnh, một câu trả lời xác nhận, một tool call qua MCP), nên hai dữ kiện của cùng một cảm biến không bao
giờ tính trên hai số đọc khác nhau. Hiện thực: `SensorFact` và `SimSession.gate_facts` trong
`python/neuroedge/sim/session.py`.

| Luật | Dữ kiện | Ví dụ |
|:---|:---|:---|
| *(không có)* | Chính số đọc | `door_closed = { sensor = "door_contact" }` |
| `equals` | `bool`: số đọc bằng giá trị — giá trị là bool, chữ hoặc số hữu hạn | `room_empty = { sensor = "motion", equals = false }` |
| `gte` / `lte` (một hoặc cả hai) | `bool`: số đọc ≥ / ≤ ngưỡng — **tính cả ngưỡng** | `too_hot = { sensor = "temperature", gte = 30 }` |
| `bands` | `level`: dải chứa số đọc | `heat_level = { sensor = "temperature", bands = { low = -40, normal = 25, high = 40, critical = 55 } }` |

Kiểm khi nạp phiên — sai ⇒ lỗi ba phần (`AgentManifestError`, cảm biến bo mạch không có ⇒
`BoardCapabilityError`), **trước khi** xin line GPIO nào:

- Mỗi dòng **một** luật: `bands`, `equals`, `gte`/`lte` không đi chung. Ngưỡng là số hữu hạn (không
  phải bool, NaN, inf). Cảm biến phải là cảm biến bo mạch khai.
- Luật số (`gte`, `lte`, `bands`) cần đơn vị khai ở `[sim.sensors]`
  (`temperature = { value = 45, unit = "C" }`), để `linux` từ chối số đọc khác đơn vị thay vì đem so
  với ngưỡng (luật `linux` dưới đây).
- `bands`: mỗi mục là `mức = ngưỡng dưới`, ngưỡng **tăng ngặt** theo thứ tự viết. Một dải bắt đầu
  **tại** ngưỡng của nó và dừng ngay dưới ngưỡng của mục kế tiếp; dải cuối không có cận trên. Ví dụ
  trên: 24,999 → `low`, 25 → `normal`, 54,999 → `high`, 55 → `critical`. Phải có ít nhất một gate
  đọc tiêu chí đó; mọi gate đọc nó khai kiểu `level`, và với từng gate: mức là mức gate khai ở
  `evaluate.<tiêu_chí>.levels`, viết **đúng thứ tự** đó, và **mục cuối là mức cao nhất** của gate —
  chỉ được bỏ mức thấp hoặc mức giữa, để số đọc cao tới đâu cũng không dừng dưới mức trên cùng.
- Trên cảm biến có `bands`, `gte` phải **trùng một ngưỡng** của các `bands` đó (dữ kiện bool là
  "từ dải này trở lên", không lệch khỏi dải ở số đọc nào); `lte` bị từ chối, vì ngưỡng thuộc dải
  phía trên nên `lte` sẽ lệch đúng tại ngưỡng.
- Tiêu chí do cảm biến quyết không được có giá trị cố định ở `[sim.facts]` (hay `SimSession.load(facts=)`):
  giá trị đó không bao giờ được đọc. `:set` trong REPL và trang `--ui` từ chối nó và chỉ sang `:sensor`.

Lúc chạy — fail-closed, không đoán:

- Một số đọc **không lấy được** (cờ lỗi, NaN hay tệp hỏng trên `linux`, thiết bị biến mất, `sim` chưa có
  giá trị), hoặc bị **một luật bất kỳ của cảm biến đó** từ chối — luật số trên số đọc không phải số hữu
  hạn (chữ, bool, NaN, inf), `bands` trên số đọc dưới ngưỡng đầu tiên (đầu dò hở/chập), `equals` trên số
  đọc khác kiểu (`0` không phải `false`), chính số đọc khi nó rỗng hay không hữu hạn — thì **mọi** dữ kiện
  của cảm biến đó trong lần tính ấy là **chưa xác định** (`null` trong `gate_facts`), và phiên ghi
  `sensor_unavailable` (§3). Gate đọc chúng chặn với `criterion_unavailable`; vì cả tiêu chí phủ quyết
  (`heat_critical`) cũng chưa xác định, một lời "có" không đủ nên thiết bị **không hỏi**. Gate không đọc
  dữ kiện nào của cảm biến đó quyết như thường (`vent_on` của `factory-monitor` vẫn chạy).
- Câu trả lời xác nhận tính lại dữ kiện: hỏi lúc 45 °C, cảm biến hỏng trước lời "có" ⇒ vẫn chặn.
- Replay dùng lại `gate_facts` đã ghi, nên không tính lại được dữ kiện cảm biến. Vết ghi mang digest
  của `[sim.sensor_facts]` (`metadata.sensor_facts_digest`); luật đổi sau khi ghi thì `replay` cảnh báo
  (sự kiện `sensor_facts_changed` trong vết ghi phát lại) — phán quyết khi đó không kiểm luật mới, cần
  ghi lại phiên. Đây là cảnh báo, không phải khác biệt quyết định: mã thoát không đổi.

**Dữ kiện gate từ kênh ADC — `[sim.analog_facts]`** (`analog.in`, TSK-I2a-04; bo mạch khai kênh:
`sim-rpi5`, `linux-rpi5`). `tiêu_chí = { channel = "adc0" }` nối một tiêu chí `numeric` của gate với một kênh
`analog.in` (RFC-0007 §3c, RFC-0009 §3f); `[requires]` khai `"analog.in" = { channels = ["adc0"] }`. Giá trị
trên `sim` là `[sim.analog] adc0 = 1.25` (đơn vị của kênh), đổi bằng `:analog adc0 1.5` / `:analogs` trong
REPL và `:analog` trên trang `--ui`; trên `linux` là số đọc kernel (bên dưới). Mỗi kênh được đọc **một lần
mỗi lần tính dữ kiện gate**; số đọc vào gate là `Fact` kèm **mốc đọc** `read_ms` lấy trên đồng hồ của phiên
**trước** lần đọc HAL, và engine tính `age_ms` (Q-62; vết ghi `gate_facts` ghi `read_offset_ms`,
`eval_offset_ms`, `age_ms`). Kiểm lúc `neuroedge build` — sai ⇒ `BoardCapabilityError` (NE3001): kênh phải
do bo mạch khai **và** do `[requires]` liệt kê; mọi gate đọc tiêu chí đó khai nó `numeric`, cùng `unit` với
kênh, và `[min, max]` của kênh nằm trong `range` của tiêu chí. Tiêu chí `numeric` nằm trong
`on_block.confirms` bị `gate lint` từ chối với **mọi** tiêu chí số (`GateSchemaError`, NE2002), nên một kênh
ADC không bao giờ được người dùng xác nhận thay. Tiêu chí do kênh quyết không được có giá trị cố định ở
`[sim.facts]`, cũng không nằm đồng thời ở `[sim.sensor_facts]`; `:set` từ chối nó và chỉ sang `:analog`.
Lúc chạy — fail-closed: số đọc hỏng — chưa đặt giá trị trên `sim`; trên `linux` thiết bị mất, tệp mất hay
chứa rác, cờ `*_fault`, khác đơn vị; hoặc giá trị không hữu hạn hay **ngoài `[min, max]` của kênh** (không bao
giờ cắt về biên) — là `PerceptionUnavailableError` (NE5001) ⇒ dữ kiện chưa xác định ⇒ BLOCK
`criterion_unavailable`. Mỗi lần đọc, kể cả lần hỏng, ghi sự kiện `analog_in` (§3). Replay dùng lại
`gate_facts` đã ghi (giá trị lẫn tuổi), không đọc kênh nào; vì vậy không tính lại được dữ kiện, và đổi
`[sim.analog_facts]` sau khi ghi **không** được cảnh báo như `[sim.sensor_facts]` (chưa có digest).

**PWM và kênh phản hồi (RFC-0010, TSK-W1-01).** PWM là một khối của `digital.out`, không phải nguyên thủy
riêng: agent khai `"digital.out" = { pins = ["fan"], pwm = ["fan"] }` (mỗi kênh `pwm` phải do bo mạch khai ở
`digital_out.pwm.pins` **và** nằm trong `pins`; kiểm lúc `neuroedge build`, `BoardCapabilityError` nếu không) và
gọi `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)` — `ms` bắt buộc, không có giá trị mặc định
hay "chạy mãi". Thứ tự xử lý: `require_pin` → **giới hạn bo mạch** (`on`/`pulse` trên kênh PWM, `pwm` trên chân
thường, thiếu `duration_ms`, `frequency_hz` ngoài dải, `duty` ngoài `[0, max_duty]` ⇒ `BoardCapabilityError`) →
phong bì (giữ trước `duration_ms`, **cả** thời gian `duty > 0` được tính, `duration_ms` > `max_continuous_ms` ⇒
`EnvelopeRefusedError` lý do `max_continuous_ms`, không cắt ngắn) → `authorize` → ghi. `duty` được lượng tử hoá về
0 theo `resolution_bits` nên không bao giờ vượt `max_duty`; một `duty` lượng tử về 0 là trạng thái an toàn: chạy
như `off` (không token, không qua phong bì, `actuator_command` `off` kèm `cause: duty_zero`). `off`, hết hạn,
`close()` và mất giám sát thả `enable_pin` rồi `duty = 0`, không bao giờ bị chặn. Gate giới hạn `duty`,
`frequency_hz`, `duration_ms` bằng khối `arguments` sẵn có (RFC-0005): vượt ⇒ BLOCK `argument_out_of_range`; tool
call thiếu tham số ⇒ `REJECTED`. `gate.v1` không đổi.

`digital.out("fan").state()` (HAL: `pin_state()`) trả `duty` và `frequency_hz` kèm `source`: `measured` khi chân
nằm trong `digital_out.feedback.pins` và đọc lại từ phần cứng (trên `linux`: thanh ghi của bộ điều khiển PWM, đọc
lại từ sysfs — không phải bộ nhớ của HAL), còn lại `commanded`. Đọc lại hỏng (tệp mất, rác, thanh ghi mâu thuẫn,
`duty` quá `max_duty` hay tần số ngoài dải của bo mạch) là `PerceptionUnavailableError` (NE5001), không bao giờ
trả `commanded` thay. Mỗi lần đọc ghi sự kiện `pin_state` (§3); replay nạp lại cả `source`. **Dữ kiện cho gate:**
`[sim.feedback_facts]` — `tiêu_chí = { pin = "fan", quantity = "duty" | "frequency_hz" }` nối một tiêu chí `numeric` với
một đại lượng của `state()`; thang cố định theo bo mạch (`duty`: `unit: ratio`, `[0, max_duty]`; `frequency_hz`:
`unit: Hz`, dải tần số của kênh) và `neuroedge build` kiểm `unit` trùng và thang nằm trong `range` của tiêu chí
(`BoardCapabilityError`). Mỗi kênh được đọc **một lần mỗi lần tính dữ kiện gate** và dữ kiện mang mốc đọc `read_ms`
như `analog.in`. **Chỉ `measured` tới gate**: giá trị `commanded`, một lần đọc hỏng hay một đại lượng không có giá
trị lúc đó (tần số của kênh đang tắt) làm dữ kiện chưa xác định ⇒ BLOCK `criterion_unavailable`. Bo mạch tham chiếu
(`sim-rpi5`, `linux-rpi5`) **chưa khai `feedback`** (bằng chứng phần cứng thật là việc của nightly Pi 5 và của người
dựng giàn), nên `fan` ở đó đọc `commanded` và tiêu chí nối với nó không bao giờ quyết được; test dùng một bo mạch
có `feedback`. `:feedback fan duty=0.3 | fail <lý do> | clear` đặt số đọc lại giả lập trên `sim` (REPL và `--ui`).
Trên `linux` kênh kernel nằm ở `NEUROEDGE_LINUX_PWM='fan=pwmchip0/2'` (hoặc `LinuxHAL(pwm_channels=…)`), không bao
giờ đoán; session chỉ chuẩn bị kênh mà `[requires]` `pwm` liệt kê (`needs["pwm"]`): kernel thiếu chip/kênh ⇒
`BoardCapabilityError` lúc nạp agent, không lùi về PWM phần mềm; đồng bộ với `preflight(pwm=…)`.

### `digital.in` — `sim-rpi5` và `linux-rpi5` (RFC-0007 §3a, TSK-I2a-02)

`digital.in` là nguyên thủy mở rộng (RFC-0013): chỉ bo mạch khai `[capabilities.digital_in]` mới có —
`sim-default` không có, nên agent dùng nó build với `--board sim-rpi5`.

| Target | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `sim` | `SimHAL.set_digital_in()` — mức khởi đầu `[sim.inputs]`, đổi bằng `:input <chân> <true\|false>` trong REPL và trang `--ui` (sự kiện `digital_in_set`); chân chưa đặt mức ⇒ lần đọc hỏng, không phải một mức | PR | — | TSK-I2a-02 |
| `linux` | `LinuxHAL` qua libgpiod v2: line tìm theo **tên** như chân ra, xin làm **đầu vào** (không bao giờ ghi, không đặt bias hay cạnh), giữ tới `close()`; phiên xin mọi line agent đọc ngay khi dựng, line đọc lần đầu muộn hơn thì xin lúc đó | PR — fake gpiod (`tests/test_digital_in_linux.py`) · `gpio-sim` (`tests_linux/test_gpio_sim.py`; mức đặt qua `sim_gpioN/pull`) | Điện áp, nhiễu, bias thật của mạch | TSK-I2a-02 |

**Dữ kiện gate từ chân đầu vào — `[sim.digital_facts]`.** RFC-0007 không nói tiêu chí gate nối với chân
nào; cách nối nhỏ nhất hợp với RFC là theo khuôn `[sim.sensor_facts]`: `tiêu_chí = { pin = "…" }` là chính
mức đọc (cao = `true`), `{ pin = "…", equals = false }` là "chân ở mức thấp". Giống `sensor_facts`, bảng nằm
trong `[sim]` nhưng cũng dùng trên `linux`. Mỗi chân được đọc **một lần mỗi lần tính dữ kiện gate**, ngay
trước lúc gate lượng giá (không dùng giá trị đệm).

Kiểm lúc `neuroedge build` và nạp phiên — sai ⇒ lỗi ba phần, **trước khi** xin line nào:

- Chân phải là chân `digital_in.pins` của bo mạch **và** nằm trong `"digital.in" = { pins = [...] }` của
  `[requires]` (`@action(requires="digital.in:<chân>")` cũng phải là chân `[requires]` khai); chân không khai ⇒
  `BoardCapabilityError` (NE3001).
- Tiêu chí phải do ít nhất một gate đánh giá, và mọi gate đánh giá nó khai kiểu `bool` — mức logic là dữ
  kiện `bool` (không `numeric`, `level`, `choice`).
- Một tiêu chí một nguồn: không đồng thời ở `[sim.sensor_facts]`; không có giá trị cố định ở `[sim.facts]`;
  `:set` từ chối và chỉ sang `:input`.

Tuổi và fail-closed (RFC-0007 §3a, §3e, §9 mục 11):

- Dữ kiện mang **mốc đọc** HAL (`read_ms`, trên đồng hồ của `EventLog`, lấy **trước** lần đọc). Engine tính
  `age_ms` lúc lượng giá, như tiêu chí `numeric` (RFC-0009 §3c); `gate_facts` ghi `read_offset_ms`,
  `eval_offset_ms`, `age_ms`, `source: "digital.in"`. `replay` chỉ tin một tuổi vết ghi giải thích được.
- Tiêu chí `bool` không có `max_age_ms`, nên trần là hằng `DIGITAL_IN_MAX_AGE_MS = 100` trong
  `engine/verdict.py`: không cấu hình, gate và agent không nới được. `age_ms` âm, vượt trần, hoặc không có
  mốc đọc dùng được ⇒ `criterion_unavailable`. Trần bắt đường đọc treo; đầu vào kẹt mức ở phần cứng không
  bị bắt bằng tuổi, nên gate quan trọng cần thêm một tiêu chí độc lập.
- Lần đọc hỏng (không tìm thấy line, không xin được, `get_value` lỗi, chip mất, `sim` chưa đặt mức) ⇒
  `PerceptionUnavailableError` (NE5001) ⇒ dữ kiện `digital.in` **không có giá trị** ⇒ BLOCK
  `criterion_unavailable`, **kể cả gate `fail: open`** (`known_failure` không bỏ qua dữ kiện `digital.in`
  mất, như số đọc `numeric` mất). Mức không bao giờ được đoán.
- Đọc trong thân `@action`: `digital.input("<chân>").level()` (không cần token, đọc không di chuyển gì);
  mỗi lần đọc là một sự kiện `digital_in` mà `replay` cấp lại theo thứ tự, lần đọc hỏng được cấp lại thành
  lần đọc hỏng, đọc quá số lần đã ghi cũng là đọc hỏng — không bao giờ lặp mức cuối.
- `replay` không bao giờ chạm line của máy: `LinuxHAL(replay=True)` không xin line nào.

### `motion.*` — `sim-rpi5` và `linux-rpi5` (RFC-0011, TSK-I2a-05)

`motion.*` là nguyên thủy mở rộng (RFC-0013): chỉ bo mạch khai `[capabilities.motion]` mới có — `sim-default`
không có, nên agent dùng nó build với `--board sim-rpi5`. `[requires]` khai `"motion" = { channels = [...] }`
và mỗi kênh phải là kênh `motor` hoặc `servo` bo mạch khai (NE3001 lúc build). API trong thân `@action`:
`motion.motor(kênh, speed=, ramp_ms=)`, `motion.servo(kênh, target=, speed_max=)`, `motion.stop(kênh)`.

| Target | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `sim` | `SimActuator` — mô hình có ramp trên đồng hồ ảo: tốc độ motor đi tới giá trị lệnh trong `ramp_ms`, dừng là tức thì; servo đi tới đích với tốc độ `speed_max`, `hold` giữ nguyên vị trí và còn cấp điện. Hiện trong REPL (`:motion`: kênh, chế độ, setpoint, lease còn lại, tốc độ/vị trí) và trang `--ui` (từ sự kiện `motion_command`, `motion_safe`) | PR (`tests/test_motion.py`) | — | TSK-I2a-05 |
| `linux` | PWM phần cứng qua sysfs — **cùng bộ ghi `SysfsPwm` của `hal/pwm.py`** mà các kênh PWM của `digital.out` (RFC-0010) dùng (`check`, `apply_ns`, `set_duty_ns`, `off`; một kênh kernel `pwmchipN/M` chỉ có một chủ: nối trùng giữa kênh `motion` và chân PWM `digital.out` bị từ chối khi dựng HAL) — `hal/motion_pwm.py` chỉ là chính sách chuyển động (motor 20 kHz, duty = tốc độ; servo xung 1000–2000 µs trong chu kỳ 20 ms trải trên dải đích) + **đường enable** của driver. Kênh nào nối với `pwmchipN/M` nào là dây nối của máy, không phải của bo mạch: `NEUROEDGE_LINUX_MOTION=wheel_left=pwmchip0/0;gripper=pwmchip0/1` hoặc `LinuxHAL(motion_sources=…)`; kênh chưa nối bị từ chối khi dựng HAL, không đoán. Đường enable do HAL quản và **tiến trình giám sát giữ** (hạn = hết lease + 250 ms), PWM ghi **trước** khi đường enable lên, và về 0 ngay khi HAL khởi động (kernel giữ duty cuối của PWM) | PR — gpiod giả + cây sysfs PWM giả + một tiến trình giám sát thật trên `tests/fake_gpiod` (`tests/test_motion_linux.py`); `gpio-sim` cho đường enable, SIGSTOP và SIGKILL của runtime (`tests_linux/test_gpio_motion.py`, PWM vẫn là cây giả) | Motor, servo, driver thật cắt điện khi enable xuống, PWM của RP1, nút dừng khẩn (Q-38), test mất điện giữa lệnh (RFC-0011 §3f, giai đoạn B) | TSK-I2a-05 |

**Lease và lần chạy.** Token phán quyết của một `action` có `requires="motion:<kênh>"` mang một **lease** cho mỗi
kênh: `lease_ms` của kênh (200 nếu bo mạch không khai; trần 500), tính từ phán quyết, dùng cho **đúng một lệnh**,
không phụ thuộc `TTL_FACTOR`. Lease không gia hạn được bằng cách nào khác ngoài một lần qua gate mới (lệnh
mới, lượng giá lại đầy đủ); lời gọi bị BLOCK không gia hạn mà còn đưa kênh về trạng thái an toàn ngay.
**Lần chạy** là chuỗi lease liên tiếp trên một kênh (lease mới đến trước khi lease cũ hết): phong bì giữ trước
`max_continuous_ms` **một lần lúc bắt đầu** lần chạy, kiểm `min_interval_ms` **chỉ lúc đó**, ghi bền một lần
(không ghi mỗi lần gia hạn), và hoàn phần dư khi lần chạy kết thúc. Mọi kiểm theo thứ tự
`kênh đúng loại → giới hạn bo mạch → phong bì → bằng chứng (lease) → lái → ghi vết`; nếu bằng chứng hỏng thì
phần phong bì đã giữ được hoàn trả hết.

**Trạng thái an toàn** (`stop` nếu không khai; `hold` chỉ cho servo khai `holds_position` + `max_hold_ms`) được
gửi, **không qua phong bì, không cần token, không chờ ramp**, khi: lease hết (`lease_expired`), hết
`max_continuous_ms`, hết `max_hold_ms` (`hold` ⇒ `stop`), cắt lời (`barge_in`, `VoiceStateMachine` gọi
`motion_barge_in` ở bước 1 của `docs/spec/voice_fsm.md` §5.2, cùng tick với sự kiện kích), BLOCK (`block`),
`motion.stop` (`stop`), `hal.close()` (`close`), tiến trình giám sát thả đường enable (`supervisor_heartbeat`,
`supervisor_deadline`), PWM không ghi được (`actuator_fault`). Mọi nguyên nhân sau `close`, `max_*`, `supervisor_*`,
`actuator_fault` dừng hẳn kể cả khi kênh khai `hold`. Mỗi lần ghi `motion_safe` kèm nguyên nhân; kênh đã ở trạng
thái đó không sinh sự kiện.

Giới hạn theo hai nơi, **chặt hơn thắng**: bo mạch (`speed_max`, `ramp_min_ms`, dải đích — HAL từ chối bằng
`BoardCapabilityError`) và gate (`arguments` của RFC-0005, `BLOCK argument_out_of_range` trước mọi dữ kiện).
Chiều quay: `board.v1` chưa cho kênh motor khai đường chiều, nên `direction = "reverse"` bị từ chối trên **mọi**
target (sim không giàu hơn bo mạch); cần RFC để mở.

### `linux` — `linux-rpi5`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | `LinuxHAL` qua libgpiod v2; phong bì theo chân với hẹn giờ tự tắt thật và tệp trạng thái bền theo bo mạch; tiến trình giám sát giữ line của chân cơ cấu (mặc định bật, `hal/supervisor.py`) | PR — gpio-sim, và SIGSTOP runtime trên gpio-sim (`tests_linux/test_gpio_envelope.py`) | Điện áp, timing | TSK-S3-05, N2-01, N2-02 |
| `digital.out` — PWM *(chỉ bo mạch khai `digital_out.pwm`, vd. `linux-rpi5`)* | **Chỉ PWM phần cứng của kernel** qua `/sys/class/pwm/pwmchipN/pwmM/{period,duty_cycle,enable}` — `hal/pwm.py`; không bit-bang. `enable_pin` là line gpiod của HAL, do tiến trình giám sát giữ cùng hạn của phong bì: nâng sau khi bộ điều khiển đã lập trình, hạ **trước** khi tắt bộ điều khiển | PR — cây sysfs giả + gpiod giả + giám sát giả (`tests/test_hal_linux_pwm.py`); gpio-sim cho line `enable` và SIGSTOP (`tests_linux/test_gpio_pwm.py`). **Không có chip PWM mô phỏng trên runner** (gpio-sim chỉ có line; kernel azure không có `pwm-sim`) nên bộ điều khiển thật chỉ kiểm trên nightly Pi 5 | Xung thật, tải, readback thật | TSK-W1-01 |
| `audio.in` | **Backend tệp**: WAV (`--voice-file`) ở mọi rate 8–96 kHz, 1–2 kênh → mono ở rate bo mạch (`hal/audio.py`, `open_audio_file`) · **Backend sống**: `sounddevice` (PortAudio) đọc nút `neuroedge.ec.source` của `module-echo-cancel` (Q-22) | PR — backend tệp trên fake gpiod + `sounddevice` giả; `tests_linux/test_audio_file.py` trên gpio-sim (**runner không có `snd-aloop`**, nên backend sống chỉ chạy trên máy) | Micro, AEC, âm học — RPi 5 + HAT I2S, `snd-aloop` trên Pi | TSK-S5-08 |
| `audio.out` | **Backend tệp**: dòng thời gian `Speaker` ghi WAV ở rate bo mạch (`--voice-out`) · **Backend sống**: `sounddevice` phát vào nút `neuroedge.ec.sink` (tín hiệu tham chiếu của AEC) | PR — như trên | Loa, âm lượng | TSK-S5-08 |
| `sensor.read` | sysfs **hwmon** và **IIO** (`/sys/class/hwmon/*/temp1_input`, `/sys/bus/iio/devices/iio:device*/in_*`) — `hal/sysfs.py` | PR — `i2c-stub` + driver `lm75` → hwmon (`scripts/setup_i2c_stub.sh`, `tests_linux/`); IIO trên cây sysfs giả (`tests/test_hal_linux_io.py`) | Cảm biến thật; IIO chỉ trên Pi (`CONFIG_IIO` tắt trên runner) | TSK-S5-09 |
| `analog.in` | sysfs **hwmon** (`inN_input`, mV → V theo `HWMON_UNITS`) và IIO, kênh tìm bằng **nguồn** `NEUROEDGE_LINUX_ANALOG='adc0=hwmon:ads7828/in0'` / `LinuxHAL(analog_sources=…)` (như `sensor.read`, `board.v1` chưa có khoá nối kênh với thiết bị) hoặc bằng nhãn `inN_label`; đổi sang đơn vị khai của kênh, từ chối ngoài `[min, max]` như lỗi đọc — `hal/analog.py`, `hal/linux.py` | PR — cây sysfs giả (`tests/test_hal_linux_analog.py`); `i2c-stub` + driver `ads7828` → hwmon, mã `0x800` → 1249 mV, gate quyết trên số đọc, replay (`scripts/setup_i2c_stub.sh`, `tests_linux/test_analog_in.py`) | ADC thật trên Pi 5 (spike TSK-N3-03 chỉ chứng minh `i2c-stub` + hwmon, RFC-0007 §3c đòi bằng chứng hằng đêm trên phần cứng trước tiêu chí ra I2a) | TSK-I2a-04 |
| `display` | Kiểm và ghi khung bằng đúng mã của `sim` (`make_frame`), rồi → `/dev/fb*` trên Pi, hoặc chỉ trong bộ nhớ — `hal/framebuffer.py` | PR — khung trong bộ nhớ + digest; `/dev/fbN` của `vfb`, hoặc `vkms` trên kernel azure (`scripts/setup_vfb.sh`) | Panel HDMI/DSI | TSK-S5-09 |
| `i2c` *(chỉ bo mạch khai `i2c`, vd. `linux-rpi5`)* | `/dev/i2c-N` qua ioctl `I2C_SMBUS` (chỉ `fcntl` + `ctypes`, không thêm phụ thuộc) — `hal/i2c_bus.py`, API agent `hal/i2c.py` | PR — transport trên `ioctl` giả, chính sách trên bus giả ghi mọi giao dịch (`tests/test_hal_i2c.py`); `i2c-stub` với `ina219` (0x40), `ads7828` (0x4a), `lm75` (0x48) (`scripts/setup_i2c_stub.sh`, `tests_linux/test_i2c_read.py`) | Chip thật, pull-up, timeout thật | TSK-I2a-03 |

**Phong bì an toàn trên `sim` và `linux`** (RFC-0007 §3d, TSK-N2-01, TSK-N2-02; hiện thực `python/neuroedge/hal/envelope.py`).
Bốn số của mỗi chân cơ cấu lấy từ `board.v1`; `sim-*` có đúng số của bo mạch nó soi, không giàu hơn.

- **Giữ trước nguyên tử.** Mỗi lệnh `on` hoặc `pulse` giữ trước đúng thời gian chân sẽ bật: `min(thời hạn, max_continuous_ms)`,
  hoặc `max_continuous_ms` khi lệnh không có hạn. Kiểm và giữ là một bước dưới khoá theo chân; hai lệnh đồng
  thời không cùng qua ngân sách còn lại. Tắt sớm hoàn phần chưa dùng; `authorize` thất bại hoàn 100% và không tiêu token.
- **Chân đang bật từ chối lệnh bật thứ hai** (`already_on`): không có "bật lại để kéo dài". `min_interval_ms` tính từ lúc lần bật
  trước **kết thúc**. Lệnh `off` và mọi lệnh về phía an toàn không bao giờ bị chặn, không cần token (`threat_model.md` §1).
- **Đồng hồ.** `sim`: đồng hồ của phiên (`EventLog.clock`), chân tự về tắt tại hạn mà không cần hẹn giờ (xử lý lười ở lệnh kế
  tiếp và ở `run_due()`); `linux`: hẹn giờ thật ở `LinuxHAL`, và phong bì coi chân còn bật cho tới khi HAL xác nhận đã thả line.
  Replay quyết định theo mốc đã ghi của từng lệnh (`ReplayClock`), nên bản ghi phát lại cho cùng quyết định ở mọi tốc độ.
- **Sống qua khởi động lại (`linux`).** Thời gian bật được ghi **trước** khi bật, một tệp JSON mỗi chân
  (`{"version": 1, "name": <chân>, "on_ms": [...]}`) trong **một thư mục theo bo mạch**: `$NEUROEDGE_LINUX_ENVELOPE_STATE`, mặc định
  `$XDG_STATE_HOME/neuroedge/envelope/<board id>` (`~/.local/state/…`). Theo bo mạch vì chân thuộc về giàn thiết bị, không thuộc về agent:
  hai agent trên cùng bo mạch dùng chung một cửa sổ. Sau khởi động, mọi lần bật đã ghi chiếm ngân sách tới `window_s`, và mỗi chân chờ
  `min_interval_ms` trước lần bật đầu. Tệp thiếu, hỏng hoặc không ghi được ⇒ coi cả cửa sổ đã dùng hết (`window_unreadable`). Giàn
  mới khai tệp trống bằng `NEUROEDGE_LINUX_ENVELOPE_INIT=1` (hoặc `envelope_init` ở `target_options`); cờ này chỉ tạo tệp **chưa có**,
  không bao giờ ghi đè tệp có sẵn. `sim` giữ cùng luật trong bộ nhớ, không có tệp và không có lần khởi động lại.
- **Giám sát ngoài tiến trình (`linux`) — mặc định BẬT.** Line của mọi chân có phong bì do một tiến trình riêng giữ
  (`hal/supervisor.py`; phiên riêng nên SIGSTOP gửi cho nhóm tiến trình của runtime không dừng nó). Runtime ra lệnh qua
  ống và gửi nhịp tim; mất nhịp quá `heartbeat_timeout_ms` (mặc định 1000 ms) khi có line đang bật, quá hạn (thời gian
  giữ trước + 250 ms), hoặc ống đóng (runtime chết) ⇒ giám sát thả line. Runtime nhận biết ở tin nhắn kế tiếp và ghi
  `actuator_command` `off` kèm `cause`. **Fail-closed:** tiến trình giám sát không khởi động được, hoặc mất liên lạc giữa
  phiên ⇒ mọi lệnh bật chân có phong bì bị từ chối (`envelope_refused`, `reason: supervisor_unavailable`, trước `authorize`
  nên không tiêu token) còn `off` luôn chạy; không bao giờ "chạy tiếp không giám sát". Tắt có chủ ý chỉ dành cho test và gỡ
  lỗi: `LinuxHAL(supervise=False)` hoặc `NEUROEDGE_LINUX_SUPERVISE=0`; replay không giám sát. Trạng thái (`on` · `off` ·
  `failed`) ghi ở `metadata.supervision` của vết ghi phiên, và `failed` kèm sự kiện `supervision_unavailable {reason}`, để
  hậu kiểm thấy phiên đã chạy mà không có lớp bảo vệ này. Các test phiên dùng `gpiod` giả trong tiến trình nên tắt tường minh;
  `tests_linux/` giữ mặc định (bật, gpiod thật)

**Cảm biến trên `linux` tìm theo tên, không theo số thứ tự** (`hwmon3`, `iio:device0` đổi theo thứ
tự probe), như chân GPIO tìm theo tên line: kênh có nhãn trùng tên cảm biến của bo mạch, hoặc một
**nguồn** đặt theo máy — `LinuxHAL(sensor_sources=…)` hoặc biến môi trường `NEUROEDGE_LINUX_SENSORS`.
Cú pháp nguồn và bảng đơn vị: `python/neuroedge/hal/sysfs.py`. Nguồn không nằm trong `boards/*.toml`
(`board.v1` chưa có trường cho nó — khai bus I2C trong bo mạch là RFC-0007); khoá của nó phải là cảm
biến bo mạch khai. Luật an toàn:

- Mỗi lần đọc đi tới kernel; không nguồn, hai nguồn, tệp không đọc được, giá trị không phải số hữu
  hạn, cờ `*_fault`, hay loại kênh không rõ đơn vị ⇒ `BoardCapabilityError`, không bao giờ trả giá
  trị mặc định. "Tới kernel" không có nghĩa là mới hơn chu kỳ cập nhật của driver (lm75 ≈ 1,5 s).
- Agent khai đơn vị cho cảm biến (`[sim.sensors] temperature = { value = …, unit = "C" }`) thì số đọc
  của kernel khác đơn vị đó bị từ chối, không đem so với ngưỡng viết cho đơn vị kia. Dữ kiện gate tính
  từ số đọc kernel bằng đúng luật `[sim.sensor_facts]` của `sim` (trên), gồm `bands`.
- Replay chỉ dùng giá trị đã ghi: cảm biến vết ghi không có số đọc thì báo lỗi, không đọc kernel; khung
  hình vẽ trong bộ nhớ.
- `door_contact` và `motion` của `linux-rpi5` là đầu vào GPIO, không phải hwmon/IIO: chưa đọc được trên
  `linux`, agent cần chúng bị từ chối trước khi xin line.

**I2C chỉ đọc** (RFC-0007 §3b, TSK-I2a-03). API không có hàm ghi dữ liệu: lần ghi duy nhất là con trỏ
thanh ghi, và chỉ tới thanh ghi nằm trong `readable_registers` của thiết bị trong allow-list của bo
mạch, ngay trước một lần đọc repeated-start (SMBus *read byte/word data*, `width` 1 hoặc 2 byte; số 16
bit trả theo thứ tự trên dây, byte đầu là byte cao). Thiết bị không khai `readable_registers` chỉ nhận
receive-byte. Mọi kiểm tra của bo mạch (bus, thiết bị — tên hoặc địa chỉ —, thanh ghi) chạy **trước**
khi chọn nút hay gửi giao dịch; địa chỉ ngoài allow-list chỉ được liệt kê bởi `i2c_scan` (đọc từng
địa chỉ `0x03..0x77` bằng read-byte, không bao giờ quick-write) và mọi lần đọc tới nó bị từ chối. NACK,
timeout hay giá trị không phải số byte đã xin: thử lại **một lần**, rồi `i2c_read` ghi `reason` thay cho
`value` và lỗi `PerceptionUnavailableError` (NE5001) bay lên; bản ghi tự ghi (replay) không thử lại.
`i2c` **không** vào gate như một tiêu chí: RFC-0007 chỉ cho `digital.in` và `analog.in` vào gate; agent
đọc I2C trong thân `@action`. Nút của từng bus bo mạch là của máy, không nằm trong `boards/*.toml`:
`LinuxHAL(i2c_nodes={"i2c1": "/dev/i2c-1"})` hoặc `NEUROEDGE_LINUX_I2C='i2c1=/dev/i2c-1'`, không đoán
(số adapter đổi theo bo mạch và lần khởi động). Địa chỉ được ép (`I2C_SLAVE_FORCE`) vì chip đã có driver
hwmon (`ads7828`, `lm75`) sẽ trả EBUSY cho yêu cầu thường. Agent khai trong `[requires]`:
`"i2c" = { devices = ["i2c1/ina219"] }` — mỗi `bus/thiết bị` phải nằm trong allow-list của bo mạch (kiểm
lúc build, `BoardCapabilityError`), và `@action(requires="i2c:i2c1/ina219")` phải được `[requires]` khai.

**Giá trị I2C trên `sim` — `[sim.i2c."bus/thiết_bị"]`** (TSK-I2a-03, gói cảm biến). I2C không vào gate, nên
bảng này không phải dữ kiện: nó đặt thứ `i2c.read()` trong thân `@action` nhận được trên `sim`, như
`SimHAL.set_i2c()`. Mỗi dòng là `"0x02" = 24000` (một byte) hoặc `"0x02" = { value = 24000, width = 2 }`
(thanh ghi 16 bit, giá trị theo thứ tự trên dây). `neuroedge build` kiểm: thanh ghi phải nằm trong
`readable_registers` của thiết bị trong allow-list của bo mạch (`BoardCapabilityError`), thiết bị phải do
`[requires]` `i2c` liệt kê, giá trị phải vừa `width`. Trên `linux` chip trả lời và bảng không được dùng.

**Agent mẫu của gói cảm biến — `fixtures/agents/rail-gate`** (I2a tiêu chí ra 3). Một cổng chạy bằng ắc quy:
`rail_open_gate` mở khi công tắc hành trình báo cổng ở điểm dừng đóng (`digital.in`, dữ kiện `bool`) và điện
áp nguồn trên kênh ADC từ 1,2 V (`analog.in`, tiêu chí `numeric` với đơn vị, thang và `max_age_ms` khoá ở
gate); `rail_report` đọc điện áp bus của `ina219` qua I2C trong thân action rồi hiện lên màn hình. Build trên
`sim-rpi5` và `linux-rpi5`; `sim-default` và Box-3 từ chối nó, nêu từng nguyên thủy thiếu. Corpus
`fixtures/traces/sensor-pack/` (cho phép; chặn vì rail sụt và vì cổng lệch điểm dừng; chặn
`criterion_unavailable` vì ADC ngoài thang, số đọc ADC cũ 501 ms và chân hành trình chưa có mức) do
`scripts/gen_sensor_pack_traces.py` sinh, phát lại bằng `neuroedge verify` trên **mọi bo mạch khai đủ ba
nguyên thủy** (`sim-rpi5`, `linux-rpi5`). Bo mạch thiếu một nguyên thủy bỏ qua corpus (ô `—`), không tính là
đạt; corpus đếm riêng với các vết ghi chuẩn mực ("extension replays compared"), và `verify` thất bại nếu không
bo mạch nào phát lại được nó. Kiểm: `tests/test_sensor_pack_sample.py`, `tests/test_sensor_pack_linux.py` (phiên
`linux` trên gpiod, sysfs và i2c-dev giả), `tests_linux/test_rail_gate.py` (gpio-sim + `i2c-stub`).

**Âm thanh chọn rõ, không đoán** (TSK-S5-08): hai backend, không bao giờ đoán.

- **Backend tệp** là mặc định của `--voice-file` (và của replay): WAV đọc cả tệp, 16-bit PCM,
  1–2 kênh, rate 8–96 kHz, đưa về **mono ở `audio_in.sample_rate_hz` của bo mạch** bằng đúng
  phép trộn kênh và lấy mẫu lại mà một câu TTS nhận (`to_mono`, `resample`); **không mở micro**.
  `--voice-out` ghi dòng thời gian `Speaker` ở rate `audio_out` — bo mạch mới là bên lấy mẫu lại,
  `sim` thì không (bất biến 7). Tệp sai định dạng, quá dài (> 600 s), thiếu tệp ⇒ lỗi ba phần,
  không có sự kiện nào được ghi.
- **Backend sống** qua `sounddevice` (PortAudio, extra `neuroedge[audio]`): chỉ được nạp khi
  `LinuxHAL(audio="live")` hoặc `NEUROEDGE_LINUX_AUDIO=live`; mặc định đọc/ghi đúng hai nút
  AEC của §6.1 — `audio.in` đọc `neuroedge.ec.source` (đã khử vang), `audio.out` phát vào
  `neuroedge.ec.sink` (tham chiếu). Đổi nút bằng `NEUROEDGE_LINUX_AUDIO_IN` /
  `NEUROEDGE_LINUX_AUDIO_OUT`. Thiếu thiết bị, thiết bị biến mất giữa phiên, hay thiết bị từ
  chối rate/kênh/16-bit của bo mạch ⇒ lỗi ba phần; **im lặng không bao giờ được đọc như đầu vào**.
- Replay không mở thiết bị nào (backend tệp), như `display` vẽ trong bộ nhớ. Phiên thoại thời
  gian thực (micro/loa thật chạy song song provider) vẫn là `TODOS.md` #45; ở đây là nguyên thủy
  HAL mà phiên đó sẽ dùng. Vì chưa có phiên thật điều khiển nó, **đầu vào sống chưa được kiểm trên
  phần cứng**: một lần tràn bộ đệm (thiết bị bỏ mất âm thanh) ghi `audio_in_overflow` rồi dừng
  phiên — không có dòng thời gian co lại trong im lặng.
- Khi backend sống được chọn, `LinuxHAL` **mở và kiểm cả hai thiết bị trong `preflight`, trước khi
  xin line GPIO nào** (Q-16): thiếu micro/loa ⇒ lỗi ba phần, chưa giữ chân nào. `--voice-file` luôn
  ép backend tệp, nên `NEUROEDGE_LINUX_AUDIO=live` không bao giờ khiến một phiên WAV mở thiết bị.

**Màn hình chọn rõ, không đoán:** `LinuxHAL(display="memory" | "/dev/fbN")` hoặc
`NEUROEDGE_LINUX_DISPLAY`; không chọn thì `display` báo lỗi. Framebuffer đọc bố cục điểm ảnh từ
kernel (ioctl `FBIOGET_*SCREENINFO`: 16/24/32 bit, vị trí màu; chế độ grayscale/FOURCC/`msb_right` bị
từ chối), ghi từng hàng từ góc trên trái, mở thiết bị mỗi khung rồi đóng ngay; khung chữ bị từ chối
(không có font — `memory` nhận). Phiên tương tác (`run`, `record`, `mcp serve --target linux`) kiểm
mọi cảm biến agent và `[sim.sensor_facts]` cần, và backend màn hình nếu agent cần `display`, **trước
khi** xin line GPIO nào.

### Nguyên thủy mở rộng `vision.in` — `sim-rpi5` và `linux-rpi5`

| Nguyên thủy | Backend | Kiểm ở | Task |
|:---|:---|:---|:---|
| `vision.in` trên `sim` (`sim-rpi5`) | Camera ảo phát lại chuỗi khung đã ghi (`[sim.vision]`) trên đồng hồ phiên, đúng chế độ bo mạch khai, hàng đợi kiểu driver, hết chuỗi ⇒ mất camera; nhãn do mô hình `replay` cấp ([`camera.md`](camera.md) §4) | PR (`tests/test_virtual_camera.py`, `tests/test_vision_camera.py`) | TSK-V1b-02 |
| `vision.in` trên `linux` (`linux-rpi5`) | Node V4L2 do máy chọn (`NEUROEDGE_LINUX_CAMERA`), Python thuần, đúng chế độ khai ([`camera.md`](camera.md) §5) | PR với driver giả (`tests/test_v4l2.py`); job `linux-hal` với `vivid` (`scripts/setup_vivid.sh`, `tests_linux/test_camera_v4l2.py`) | TSK-V1b-01 |
| Corpus `vision.in` | `fixtures/traces/vision/` replay trên mọi bo khai `vision.in` ([`camera.md`](camera.md) §8) | PR · `neuroedge verify` | TSK-V1b-02 |

`sim-default` (soi Box-3) không có camera: agent đòi `vision.in` bị từ chối lúc build. Chỉ phần cứng: độ trễ thật của driver CSI/USB, nhiễu và phơi sáng;
tương đương suy luận giữa target (`tolerance`): TSK-V1b-04.

### `esp32s3` — `esp32s3-box-3`

| Nguyên thủy | Backend | Kiểm ở | Chỉ phần cứng | Task |
|:---|:---|:---|:---|:---|
| `digital.out` | ESP-IDF `gpio` sau walker cây `NETR` và sổ token C | PR — walker và sổ token C biên dịch trên host (bảng sự thật, ASan/UBSan) · QEMU (`firmware-qemu`, mỗi PR đụng `targets/**` và hằng đêm) — self-test gate lúc boot, cả firmware sinh cho một agent mới (`agent-firmware`); lệnh chân qua UART (QEMU không có GPIO matrix) | Chân thật | walker, sổ token, self-test: TSK-S4-02, S4-07, S4-08 · firmware của agent: I3-01 · chân: S4-01 · UART: S4-09 |
| `audio.in` | I2S ES7210 + ESP-SR AFE (AEC, VAD) — driver từ XiaoZhi | **Không** — QEMU không có I2S; ESP-SR là thư viện Xtensa dựng sẵn, không chạy trên host | Toàn bộ | TSK-S5-01, S5-02 |
| `audio.out` | I2S ES8311 | Không | Toàn bộ | TSK-S5-02 |
| `sensor.read` | Driver I2C của ESP-IDF | QEMU — driver giả qua cùng giao diện HAL (QEMU không có I2C) | Bus I2C, cảm biến | TSK-S4-03 |
| `display` | `esp_lcd` + LVGL | PR — **cùng mã giao diện LVGL** build trên host với màn hình test LVGL, so ảnh golden ([`ui.md`](ui.md): màn hình, quy tắc ngôn ngữ, cách dựng golden) · QEMU — `esp_lcd_qemu_rgb` | Đường SPI tới ILI9342C/ST7789 | TSK-S4-10 |

Mỗi ô có task. Ba ô chỉ kiểm được trên bo mạch (`audio.in`, `audio.out` của `esp32s3`, và
phần âm học của `linux`); chúng nằm ở nightly TSK-S4-05 và tiêu chí của I5 (roadmap §4.6) và I7 (roadmap §4.8).

## 3. Sự kiện vết ghi theo nguyên thủy

Lược đồ `trace.v1` để `type` tự do và `data` là object, nên thêm loại sự kiện **không cần RFC**.
Tên và trường dưới đây là quy phạm; mọi target phát cùng tên. Sự kiện nào đã được phát trên target
nào đi theo ô tương ứng ở §2. Cột "Vai trò khi replay" nói phần nào vào **so khớp quyết định**
(phán quyết gate + lệnh chân, như `replay` và `verify` so) — các cấp đảm bảo L1–L3 của Action CI
định nghĩa ở `neuroedge-prd.md` FR-CI-LVL.

| Nguyên thủy | Sự kiện | `data` | Vai trò khi replay |
|:---|:---|:---|:---|
| `audio.in` | `text_input` · `audio_in_vad_start` · `audio_in_segment` · `audio_in_overflow` | `{text}` · `{energy_db}` · `{sha256, duration_ms, sample_rate_hz}` · `{}` | **Đầu vào.** Replay bắt đầu từ kết quả nhận thức đã ghi (`intent_extracted`), không chạy lại âm thanh. `audio_in_overflow`: thiết bị sống bỏ mất âm thanh đã thu (người đọc theo không kịp) — phiên **dừng** thay vì đưa tiếp một dòng thời gian đã co lại trong im lặng (Q-21) |
| `audio.out` | `tts_stream_start` · `tts_stream_end` · `knowledge_retrieved` | `{text}` · `{duration_ms, sha256?, reason?}` (`reason`: `docs/spec/voice_fsm.md` §8) · `{entries: [{id, score}]}` | **Đầu ra** — chữ không vào so khớp quyết định; `knowledge_retrieved` cho biết câu trả lời dựa trên tri thức nào |
| `digital.out` | `actuator_command` · `actuator_aborted` | `{pin, operation, duration_ms, frequency_hz?, duty?, cause?}` · `{pin, reason}` — `frequency_hz` và `duty` (đã lượng tử hoá) chỉ có ở `operation: pwm` (RFC-0010), và vào `safety_view` của golden; `cause` chỉ có khi **HAL** tự đưa chân về an toàn, không phải lệnh của agent: `max_continuous_ms` (phong bì cắt một lệnh không có hạn hoặc hạn dài hơn trần) · `duty_zero` (lệnh `pwm` có `duty` lượng tử về 0 chạy như `off`) · `supervisor_heartbeat` · `supervisor_deadline` (tiến trình giám sát thả line, §2 phần `linux`). Lệnh kết thúc bằng `duration_ms` của chính nó không sinh sự kiện thứ hai | **Quyết định** — so golden ở mọi lần `replay` / `verify` |
| `digital.out` (PWM) | `pin_state` · `feedback_set` | `{pin, source, duty?, frequency_hz?, use?}` hoặc `{pin, reason, use?}` khi đọc lại hỏng · `{pin, duty?, frequency_hz?, fail?, clear?}` | **Đầu vào** (RFC-0010 §3b, §9.4) — mỗi lần `state()` một sự kiện (`use: fact` khi đọc để tính dữ kiện gate); `source` là `measured` hoặc `commanded`, `frequency_hz` vắng khi kênh tắt. Đọc lại hỏng ghi `reason` (NE5001), không bao giờ ghi giá trị `commanded` thay. Replay cấp lại đúng `source` và giá trị đã ghi; lần đọc `use: fact` không cấp lại vì kết quả đã ở `gate_facts`. `feedback_set`: người dùng đổi số đọc lại của kênh trong REPL/UI (chỉ `sim`) |
| `digital.out` (phong bì) | `envelope_refused` | `{pin, operation, reason, limit_ms?, used_ms?, requested_ms?, wait_ms?, remaining_ms?}` — `reason`: `window_budget` (`limit_ms` = `max_on_ms_per_window`, `used_ms` đã giữ trong cửa sổ, `requested_ms` phần xin thêm) · `min_interval_ms` (`limit_ms`, `wait_ms` còn phải chờ) · `already_on` (chân đang bật hoặc có lệnh chờ bật; `remaining_ms` tới hạn của lệnh đang giữ) · `window_unreadable` (bản ghi on-time thiếu, hỏng hoặc không ghi được) · `supervisor_unavailable` (`linux`: tiến trình giám sát không chạy, §2 phần `linux`) · `max_continuous_ms` (dành cho `pwm`, RFC-0010 §3d: lệnh có `duration_ms` vượt trần bị từ chối hẳn, `limit_ms` = trần, `requested_ms` = phần xin; `digital.out` thì tự tắt tại trần, không từ chối) | **Quyết định** — phong bì từ chối lệnh bật trước `authorize` (RFC-0007 §3d, `EnvelopeRefusedError` NE1003); không có `actuator_command` đi kèm và token không bị tiêu. Lệnh về phía an toàn không bao giờ sinh sự kiện này. So golden cùng `actuator_command` (`safety_view`: `{pin, operation, refused}`). Replay quyết định theo **mốc đã ghi** của lệnh (`ReplayClock`): lệnh bị từ chối trong bản ghi phải bị từ chối lại với cùng `pin`, `operation`, `reason`, và lệnh được phép không được bị từ chối — lệch là `Divergence` |
| `digital.out` (phong bì, khởi động lại) | `envelope_restored` | `{boot_ms, pins: {<chân>: {carried_ms: [số ms…]} hoặc {unreadable: lý do}}}` — `boot_ms` là mốc khởi động trên trục thời gian của vết ghi; chỉ ghi khi phiên `linux` bắt đầu với bản ghi on-time của lần chạy trước (một giàn mới khai `NEUROEDGE_LINUX_ENVELOPE_INIT=1` không có sự kiện này) | **Đầu vào của replay** — replay không đọc tệp trạng thái của máy: nó gieo phong bì từ sự kiện này (mỗi `carried_ms` giữ ngân sách tới `window_s` sau `boot_ms`, chân chờ `min_interval_ms` từ `boot_ms`), nên một lệnh bị từ chối vì on-time mang từ phiên trước vẫn bị từ chối lại với cùng `reason`. Gieo ít hơn đã ghi (vết ghi bị sửa) ⇒ lệnh không còn bị từ chối ⇒ `Divergence`; mục không đọc được ⇒ coi cả cửa sổ đã dùng hết. Vết ghi không có sự kiện này (mọi vết ghi chuẩn mực) replay từ trạng thái rỗng |
| `digital.in` | `digital_in` · `digital_in_set` | `{pin, value, use?}` hoặc `{pin, reason, use?}` (lần đọc hỏng, không có `value`) · `{pin, value}` | **Đầu vào** (RFC-0007 §3a) — replay cấp lại các lần đọc trong thân `@action` theo thứ tự, lần đọc hỏng thành lần đọc hỏng. Lần đọc `use: fact` (tính dữ kiện gate) không cấp lại vì kết quả đã ở `gate_facts`, nơi ghi **mốc đọc và tuổi**: `read_offset_ms`, `eval_offset_ms`, `age_ms`, `source: "digital.in"`; replay tính lại `age_ms` rồi so, và `age_ms < 0` hoặc vượt `DIGITAL_IN_MAX_AGE_MS` ⇒ BLOCK `criterion_unavailable`. Mốc đọc của sự kiện là `offset_ms` của chính nó. `digital_in_set` ghi việc người dùng đổi mức trong REPL/UI (`:input`) |
| `motion.*` | `motion_command` · `motion_safe` | `{channel, kind, speed, direction, ramp_ms, lease_ms, run}` (motor) hoặc `{channel, kind, target, speed_max?, lease_ms, run}` (servo), `run` ∈ {`new`, `renewed`} · `{channel, state, cause}`, `state` ∈ {`stop`, `hold`} | **Quyết định** (RFC-0011) — so golden: `replay` chạy lại action trên đồng hồ ghi, nên lease hết hạn, phong bì và cắt lời cho cùng chuỗi `motion_command`/`motion_safe` (trừ `motion_safe` nguyên nhân `close`: hết phiên, không phải quyết định). Phong bì từ chối một lần chạy ghi `envelope_refused` với `pin` là **tên kênh**; lease dùng lại hoặc hết hạn ghi `actuator_command_rejected {pin: kênh, reason: lease_used \| lease_expired, code}` |
| `i2c` | `i2c_read` | `{bus, device, address, register?, value?, reason?}` — `register` chỉ có ở lần đọc thanh ghi | **Đầu vào** (RFC-0007 §3b) — `sim` chỉ phát lại giá trị đã ghi, không quét bus. Mỗi lần đọc ghi một sự kiện; bus NACK hay timeout ghi `reason` thay cho `value` (`PerceptionUnavailableError` NE5001). Không có sự kiện ghi dữ liệu: API không có đường ghi |
| `analog.in` | `analog_in` · `analog_set` | `{channel, value, unit, use?, non_finite?}` hoặc `{channel, error, use?}` khi lần đọc hỏng · `{channel, value, non_finite?}` | **Đầu vào** (RFC-0007 §3c) — mỗi lần đọc một sự kiện (`use: fact` khi đọc để tính dữ kiện gate); giá trị ngoài `[min, max]` của kênh, mất thiết bị, rác là lỗi đọc (`error`, `PerceptionUnavailableError` NE5001), không bị cắt. Mốc đọc `read_offset_ms` và `age_ms` nằm ở `gate_facts` của lần lượng giá (RFC-0009 §3c): replay cấp lại đúng `value` và tuổi đã ghi, `age_ms < 0` hay quá `max_age_ms` ⇒ BLOCK `criterion_unavailable`. `analog_set`: người dùng đổi giá trị kênh trong REPL/UI (chỉ `sim`) |
| `sensor.read` | `sensor_read` · `sensor_set` · `sensor_unavailable` | `{sensor, value, unit?, use?, non_finite?}` · `{sensor, value, non_finite?}` · `{sensor, reason}` | **Đầu vào** — replay cấp lại đúng giá trị đã ghi; lần đọc `use: fact` (tính dữ kiện gate) không cấp lại vì kết quả đã ở `gate_facts`. `sensor_set` ghi việc người dùng đổi giá trị trong REPL/UI. `sensor_unavailable`: một lần tính dữ kiện gate không lấy được số đọc, hoặc một luật của cảm biến từ chối nó (§2), nên mọi dữ kiện của cảm biến đó là `null`; chỉ để đọc, replay dùng `gate_facts` |
| `display` | `display_frame` | `{width, height, format, sha256, text?}` (`text` khi `format = "text"`) | **Đầu ra** — so digest khi golden có ghi, không chặn tương đương quyết định |
| `vision.in` | `vision_fact` | `{fact, kind, label, zone, min_frames, value, values, unavailable?, age_ms, max_frame_age_ms, present_score_floor, model: {name, sha256}, frames: [{frame_seq, vision_ref: {sha256, size}, captured_ms, labels, rejected?}]}` — mỗi dữ kiện thị giác của một phán quyết, trước `gate_evaluation_begin`; chi tiết và lint ở [`vision.md`](vision.md) §5 | **Đầu vào nhận thức.** Replay **tính lại** dữ kiện từ nhãn đã ghi, không gọi mô hình và không cần khung hình; sự kiện không khớp nhãn của nó ⇒ dữ kiện chưa quyết ⇒ BLOCK `criterion_unavailable`. Không ảnh thô: `vision_ref` là danh tính |
| `vision.in` | `camera_unavailable` | `{reason}` — camera không giao được ở lần lượng giá này; cửa sổ bị xoá | **Đầu vào nhận thức** ([`camera.md`](camera.md) §7). Replay bỏ qua: phán quyết `criterion_unavailable` đi cùng được tính lại từ `vision_fact` chưa quyết |

Chế độ ẩn danh (FR-TRC-07) băm `text`; `audio_in_segment`, `display_frame` và `vision_fact` vốn chỉ mang digest hoặc nhãn, không mang ảnh.

**Không có NaN hay vô cực trong JSON.** JSON không có các số đó (`NaN` trần làm `JSON.parse` của trình
duyệt dừng, và trang `--ui` dừng theo). Số đọc không hữu hạn ghi thành chuỗi `"nan"`, `"inf"`, `"-inf"`
kèm `non_finite: true`, và replay đọc lại thành số thực. Mọi sự kiện khác, siêu dữ liệu, trang `--ui` và
`trace view` cũng không bao giờ mang số không hữu hạn (`json_safe` trong `python/neuroedge/trace.py`);
`trace validate` từ chối tệp có `NaN`/`Infinity` trần. Siêu dữ liệu `sensor_facts_digest` và sự kiện
`sensor_facts_changed` (chỉ ở vết ghi phát lại): §2, luật `[sim.sensor_facts]`.

Sự kiện ngoài nguyên thủy (tool call, xác nhận, MCP host, `system_two_*`, đo lượt `turn_latency` /
`session_summary`) ở danh mục duy nhất `docs/spec/tool_calling.md` §7; sự kiện của máy trạng thái hội thoại (`voice_state_changed`,
`wake_word_detected`, `audio_in_vad_end`, `stt_result`, `stt_unavailable`, `stt_fallback`) ở `docs/spec/voice_fsm.md` §8. Replay bỏ qua `system_two_call`: System 2 không đổi phán quyết, nên
phiên ghi online replay được mà không cần model hay key.

## 4. Vết ghi từ `esp32s3` về máy tính

Firmware ghi mỗi sự kiện thành **một dòng trên UART0 / USB-CDC**: tiền tố `NE1 ` rồi đúng một sự
kiện `trace.v1`, cùng tên và trường ở §3 và ở `docs/spec/tool_calling.md` §7. Đây là đặc tả của
TSK-S4-09 (trạng thái ở roadmap); định dạng C ở `targets/esp32s3/components/ne_trace/`, bộ đọc ở
`python/neuroedge/testing/uart.py`.

```text
I (312) boot: ESP-IDF v5.4 2nd stage bootloader           ← log thường: bỏ qua
NE1 {"offset_ms":0,"type":"device_info","data":{"board_id":"esp32s3-box-3","agent_version":"home-voice@0.1.0","device_id":"qemu","boot_id":"9f2c01aa"}}
NE1 {"offset_ms":3,"type":"gate_evaluation_begin","data":{"gate":"light_on@1.0.0","gate_digest":"sha256:4cc8…"}}
NE1 {"offset_ms":6,"type":"gate_facts","data":{"call_source":{"value":"local_grammar","confidence":null,"source":"context"}}}
NE1 {"offset_ms":9,"type":"gate_evaluation_result","data":{"verdict":"ALLOW","evaluations":{"call_source":"local_grammar"}}}
NE1 {"offset_ms":57,"type":"trace_end","data":{"events":4}}
NE_SELFTEST PASS walker=<n> token=<n>
NE_TRACE DONE sessions=1
```

**Dòng.** `NE1 ` ở cột 0, rồi một object JSON có đúng ba khoá `offset_ms` (số nguyên ≥ 0, đồng hồ
thiết bị tính từ `device_info`), `type`, `data` — không khoá nào khác (lược đồ cấm). UTF-8, tối đa
**512 byte** kể cả tiền tố, kết thúc bằng `\n` (host nhận cả `\r\n`). Chuỗi escape theo JSON. Dòng
không vừa thì thiết bị **không** ghi nửa dòng: nó bỏ dòng và vẫn đếm (xem `trace_end`). Nonce của
token không bao giờ có trong dòng nào.

**Khung phiên.** Mỗi phiên mở bằng `device_info` ở `offset_ms` 0 và đóng bằng `trace_end`; sau phiên
cuối, thiết bị in `NE_TRACE DONE sessions=<n>` — dòng log thường, không phải sự kiện — để người đọc
biết nó không còn gì để nói.

| Sự kiện | `data` | Ý nghĩa |
|:---|:---|:---|
| `device_info` | `{board_id, agent_version, device_id, boot_id, replay_of?, trace_digest?}` | Thiết bị tự khai. `device_id = "qemu"` khi build với `sdkconfig.qemu` (`CONFIG_NEUROEDGE_QEMU`), còn trên chip là `esp32s3-<MAC>` — bằng chứng giả lập không bao giờ đọc thành bằng chứng bo mạch. `boot_id` là 8 chữ số hex ngẫu nhiên mỗi lần khởi động. `replay_of` / `trace_digest`: phiên replay một vết ghi chuẩn mực |
| `trace_end` | `{events}` | Số dòng của phiên trước nó, kể cả `device_info` và kể cả dòng thiết bị không ghi được. Host đếm lệch ⇒ lỗi |

**Firmware chỉ ghi cái nó tự tính.** Hôm nay: `gate_evaluation_begin {gate, gate_digest}`, `gate_facts`
(đầu vào của phán quyết, như host), `gate_evaluation_result` với đúng khoá của host
(`GateResult.to_event_data()`). Hai chỗ chưa như host, đều đọc lại được đúng khi replay: giá trị ngoài
miền, và độ tin cậy NaN, ghi là `null` (thiết bị chỉ biết "không đọc được"). Nhãn gate
(`light_on@1.0.0`) và chữ `on_block` (`to`, `message`, `fallback_action`) nay có trong `NETR` v2 (`ne_gate_name`…), nhưng bảng vẫn đi
kèm firmware cho tới khi `ne_trace` đọc từ cây, sinh từ cùng gate đã phân giải (component `ne_agent` của `neuroedge build --target esp32s3`,
TSK-I3-01; `scripts/gen_firmware_vectors.py`). Phiên self-test là các phép kiểm của agent đã link, mỗi phép
kiểm một lần đánh giá gate, cùng dữ kiện và phán quyết engine host đã tính lúc build; không có lệnh chân; lệnh chân chỉ có trong phiên
replay dưới đây, và chưa có `actuator_aborted`: chưa có HAL firmware (TSK-S4-01).

**Tiêu chí số trong `gate_facts` và quy tắc phát lại (RFC-0009 §4, §5).** Mỗi dữ kiện `numeric` mang thêm ba khoá nguyên trên trục thời gian của vết ghi: `read_offset_ms` (mốc HAL đọc cảm biến), `eval_offset_ms` (mốc bắt đầu lượng giá gate) và `age_ms` (tuổi số đọc, `eval_offset_ms - read_offset_ms`, có thể âm nếu vi phạm nhân quả). Khi phát lại (`replay`), player tính lại tuổi `eval_offset_ms - read_offset_ms` và so sánh với `age_ms` đã ghi; nếu lệch (vết ghi bị sửa đổi), replay cảnh báo và duyệt lại cây với tuổi vừa tính lại. Mục `numeric` thiếu một trong ba khoá luôn được coi là `criterion_unavailable`, không bao giờ được coi là đạt.

**Host.** `neuroedge record --target esp32s3 --port <nguồn>` giữ các dòng `NE1 `, bỏ mọi dòng khác
(kể cả `NE1001…`, `NE_SELFTEST`, `NEUROEDGE_MEMORY_JSON`), kiểm khung, rồi ghi **mỗi phiên một tệp**
qua `TraceRecorder` (TSK-S3-01), thẩm định trước khi ghi. Sự kiện là của thiết bị, nguyên văn và đúng
`offset_ms`. Host chỉ dựng `metadata`:

- `session_id = sess_<boot_id><số thứ tự phiên trong lần khởi động>`;
- `target = esp32s3`;
- `board_id`, `agent_version`, `device_id` lấy từ `device_info`;
- `timestamp_utc` là giờ host đọc được `device_info` — với tệp log là giờ đọc tệp, không phải giờ
  chạy.

Dòng `NE1` hỏng, khoá thừa, `trace_end` đếm lệch, phiên chưa đóng khi nguồn hết, hoặc phiên mới mở
khi phiên cũ chưa đóng (thiết bị khởi động lại) ⇒ `TraceValidationError` (NE4001) nêu `nguồn:dòng`.
Không bao giờ đọc một vết ghi ngắn hơn như thể nó là sự thật.

| `--port` | Nguồn | Dừng khi |
|:---|:---|:---|
| đường dẫn tệp, hoặc `file:<đường dẫn>` | log QEMU `-serial file:uart.log`, hoặc bản chụp đã lưu | `NE_TRACE DONE` hoặc hết tệp |
| `tcp://host:port` | QEMU `-serial tcp::5555,server` (QEMU chờ người đọc rồi mới boot, không mất dòng đầu) | `NE_TRACE DONE` hoặc `--timeout` |
| `/dev/tty…`, `COMn`, URL pyserial (`loop://`, `rfc2217://`…) | bo mạch, qua extra `neuroedge[serial]` | `NE_TRACE DONE` hoặc `--timeout` |

`--baud` mặc định 921600 (PRD Phụ lục D.2); USB-CDC bỏ qua baud.

**Thiết bị replay vết ghi chuẩn mực.** Sau self-test, firmware replay từng vết ghi ở
`fixtures/traces/` (`main/trace_vectors.c`, `CONFIG_NEUROEDGE_REPLAY_VECTORS`), mỗi vết ghi một phiên
có `replay_of` và `trace_digest` (digest JCS của tệp). Mỗi bước nhận đúng đầu vào mà `replay` cấp lại
cho engine host — dữ kiện đã ghi, lần thu thập suy giảm đã ghi, xác nhận của người —, sinh vào
`main/vectors/` bằng `scripts/gen_firmware_vectors.py`. Phần còn lại là của thiết bị:

| Trong phiên replay | Ai tính |
|:---|:---|
| Phán quyết, lý do, `fail_mode` (kể cả `gate_unreachable` / `budget_exceeded` theo `fail` của gate) | Thiết bị — walker C `ne_decide`, cùng ngữ nghĩa `engine/gate.py` (TSK-S4-07 kiểm trên mọi gate) |
| Có phát lệnh chân không, và chân nào | Thiết bị — sổ token C: token cấp cho chân của action, `ne_token_authorize` cho từng lệnh |
| `operation`, `duration_ms` của lệnh | **Host** — bảng hành động: chạy @action một lần trên `SimHAL` sau engine luôn-ALLOW, lúc sinh vector |

`actuator_command` trong phiên replay nghĩa là sổ token cho phép chân đó; **không chân GPIO nào
động**. Cách action thật sự chạy trên MCU thay bảng hành động ở TSK-S4-01. Script từ chối, không
đoán, những gì firmware chưa replay được: tham số có giới hạn, `degrade` + `fallback_action`, số đọc
cảm biến, độ tin cậy không phải số.

`neuroedge verify --targets esp32s3 --port <nguồn>` đọc các phiên đó và, cho mỗi vết ghi chuẩn mực, so
phiên có `replay_of` tương ứng với chính vết ghi đó làm golden — như `sim` và `linux` (TSK-S3-04;
lệch ⇒ NE4002). Trước khi so, nó từ chối (NE4003, "firmware cũ") phiên có `trace_digest` khác tệp
trong checkout, hoặc `gate_digest` khác gate checkout biên dịch ra: đó sẽ là kết quả về một thứ khác.
Phép kiểm `gate_digest` là của RFC-0008 (ba vết ghi chuẩn mực mang nó trong
`gate_evaluation_begin`): host `verify` cưỡng chế nó trên mọi target, còn `replay` trên vết ghi của
người dùng chỉ cảnh báo, vì gate có thể được siết có chủ ý — luật chi tiết ở
[`10-target-equivalence.md`](../architecture/vi/10-target-equivalence.md) §5.
Thiếu `--port` ⇒ mã 1; thiếu phiên cho một vết ghi ⇒ ✗. Kết quả in rõ phần nào do thiết bị tính.

Firmware trên QEMU chạy mỗi PR đụng `targets/**` hoặc `fixtures/traces/`, và job `uart-trace` của
`firmware-qemu.yml` chạy `record` rồi `verify --targets esp32s3` trên log UART của nó. Bo mạch, replay
một vết ghi tuỳ ý trên thiết bị (gửi dữ kiện xuống) và so timing là phần còn lại của TSK-S4-04;
`replay --target esp32s3` vẫn thoát mã 2.

### 4.1 OTA trên QEMU (TSK-S6-01/02/04, FR-OTA-01…04)

`scripts/qemu_ota.sh` (job `ota-rollback`) dựng các ảnh factory, bản mới, sai khóa, không ký và ảnh hỏng (pha a–g),
ký bằng khóa RSA-3072 dùng-một-lần, phục vụ qua HTTP và đọc UART. Phiên bản trong app descriptor —
thứ OTA so sánh — của một project người dùng build đến từ `version.txt` do `neuroedge build
--target esp32s3` ghi (`[agent] version`; cách đặt và tăng: `docs/user/nap-firmware.md` §6.6);
kịch bản QEMU ghi đè `PROJECT_VER` để dựng ảnh mới 0.2.0. QEMU **chứng minh**:

- khe A/B: ảnh factory vẫn chạy, bản mới được nạp rồi khởi động, và một lần cập nhật hỏng không
  làm mất khe đang chạy;
- chữ ký: ảnh sai khóa bị `NE_OTA REJECTED reason=signature`, không có `SWITCH`, thiết bị ở lại
  bản cũ, khe vừa ghi bị xoá (`NE_OTA ERASED`); ảnh không ký bị từ chối như vậy; đây là cùng
  đường xác minh `esp_ota_end` mà bo mạch dùng;
- xác nhận sau self-test: ảnh mới chỉ `NE_OTA VALID` sau khi self-test gate đạt;
- rollback cục bộ: ảnh hỏng (tự reset trước khi kịp xác nhận, hoặc self-test hỏng ⇒
  `NE_OTA INVALID`) bị bootloader quay về ảnh trước ở lần khởi động kế tiếp, và phiên bản vừa bị
  quay về bị chặn (`NE_OTA SKIP reason=rolled_back`). Quyết định nạp hay không là hàm C thuần
  `ne_ota_should_install` (`ne_ota_policy.c`) — QEMU chạy đúng bản bo mạch chạy, gồm cả từ chối hạ
  cấp theo mốc nước cao phiên bản trong NVS (pha g: ảnh ký đúng nhưng thấp hơn mốc ⇒
  `SKIP reason=downgrade`). Mốc đó chỉ là bảo vệ bằng phần mềm; quá hạn chót, lỗi tải, chuyển hướng, phiên
  bản không đọc được và việc nâng lại mốc lúc khởi động chỉ được kiểm bằng test host
  (`test_ota_policy_host.c`), không có pha QEMU.

QEMU **không** chứng minh được, chỉ bo mạch mới có:

- Wi-Fi và mạng thật: QEMU không có Wi-Fi (Q-21), nên kịch bản dùng NIC `open_eth` (slirp). Trên
  Box-3, `main.c` (`init_network_stack`) mới chỉ dựng STA (`esp_wifi_set_mode(WIFI_MODE_STA)` +
  `esp_wifi_start()`) mà **chưa** gọi `esp_wifi_connect()` và chưa có provisioning: hôm nay chỉ
  đường `open_eth` của QEMU chạy được.
- Mất điện giữa lúc ghi hoặc giữa lúc đánh dấu hợp lệ; điện áp, thời gian ghi flash. Ảnh **treo**
  trước self-test cũng thuộc nhóm này: task watchdog không panic theo mặc định
  (`CONFIG_ESP_TASK_WDT_PANIC=n`), nên máy không tự reset — rollback chỉ ở lần khởi động sau.
- Bootloader: OTA không bao giờ ghi nó (`esp_https_ota` chỉ đổi khe app), nên bản có rollback phải
  nạp **một lần bằng cáp**; QEMU không kiểm việc nạp đó.
- Cấu hình thiếu: OTA chỉ được biên dịch khi bật đủ chữ ký-trên-cập-nhật và rollback (Kconfig từ
  chối `CONFIG_NEUROEDGE_OTA` nếu thiếu); QEMU chỉ chạy lớp `sdkconfig.ota` đầy đủ, không chứng
  minh gì về một build thiếu.
- Secure Boot / khóa trong eFuse (TSK-S6-05, ngoài phạm vi đợt này): khóa xác minh nằm trong ảnh
  đang chạy, nên người có cáp vẫn đổi được firmware; eFuse anti-rollback đi cùng Secure Boot.
- Hai giới hạn của chính QEMU 9.0, kịch bản phải né: bộ mô hình flash hỏng trạng thái khi reset
  nóng ngay sau các lần ghi flash của một lần cập nhật, và trình xử lý panic treo thay vì in rồi
  reset. Vì vậy script chạy **mỗi lần khởi động trong một tiến trình QEMU riêng** (dừng ngay sau
  dòng `rst:` của thiết bị) và ảnh hỏng dùng reset (`esp_restart`) chứ không panic; trên bo mạch
  cùng logic otadata đó chạy trong một lần cập nhật duy nhất.

## 5. Trực quan hoá

Năm bề mặt, cùng một bộ thành phần SVG tự vẽ (chốt cửa, đèn, relay, đồng hồ cảm biến, khung màn
hình). Không phụ thuộc CDN: `sim` phải chạy không mạng (FR-DX-02).

| Bề mặt | Dùng khi | Đáp ứng | Task |
|:---|:---|:---|:---|
| Terminal (`run`, `replay`, `gate explain`) | Hằng ngày, CI | Có | TSK-S3-06, S3-18 |
| `neuroedge trace view <tệp>` → một tệp HTML tĩnh | Xem lại, gửi đồng nghiệp, debug sự cố | Dòng thời gian, phán quyết + lý do, chân, cảm biến, khung màn hình; mở không cần server | TSK-S3-22 |
| `neuroedge run --ui` → trang web cục bộ, cập nhật trực tiếp | Demo, hành trình 10 phút | FR-TGT-06: trạng thái chân ảo theo thời gian thực; gõ lệnh, đặt cảm biến, nút xác nhận `ask` | TSK-S2-09, S3-26 |
| `neuroedge mcp serve --ui` → cùng trang, cho phiên MCP | Claude Desktop hoặc agent khác gọi thiết bị, người xem và can thiệp trên trang | Như trên, trong **cùng phiên** với client MCP (`tool_calling.md` §8) | TSK-S3-27 |
| `neuroedge trace export --format chrome` → Perfetto | Phân tích timing | Mở trong Perfetto UI (Apache-2.0) | TSK-S3-22 |

Wokwi Elements (MIT) có thể thay phần hiển thị đèn, servo, relay, màn hình `ili9341` nếu đóng gói
kèm (không tải CDN); không có sẵn chốt cửa.

## 6. Ba thiết bị chạy cùng agent mẫu

FR-TGT-02 và FR-TGT-03 đòi **agent mẫu chạy thật** trên RPi 5 và Box-3. Agent mẫu
`villa-concierge` khai `audio.in aec = true`, và `linux-rpi5` khai `aec = false`, nên `build
--target linux` từ chối nó — agent mẫu chỉ phủ 2/3 thiết bị. **Q-22 (đã chốt, phương án A)** đóng
khoảng này bằng AEC phần mềm của PipeWire: TSK-S5-08 đã giao backend sống, cấu hình drop-in và
đường tệp WAV; `linux-rpi5` **vẫn giữ `aec = false`** cho tới khi nightly trên Pi đạt hai phép đo
§6.2, nên `build` tiếp tục từ chối agent cần AEC — không có đường nào để khai một năng lực chưa
đo. Kịch bản tương đương ba thiết bị dùng agent chỉ cần `digital.out` (mẫu `minimal` của
`neuroedge new`) hoặc agent cần âm thanh không AEC (`--voice-file` trên `linux`).

### 6.1 Cách nối

`libpipewire-module-echo-cancel` tạo bốn nút (tài liệu PipeWire, `page_module_echo_cancel`):

```text
micro ─► capture ─►┌─────────────┐─► source   ─► LinuxHAL.audio_in   (đã khử vang)
                   │ echo-cancel │
LinuxHAL.audio_out ─► sink ─────►└─────────────┘─► playback ─► loa
```

`audio.out` **phải** phát vào nút `sink`: đó là tín hiệu tham chiếu được trừ khỏi micro. Phát
thẳng ra loa thì AEC không có gì để trừ. Cách khác là `monitor.mode = true`, lấy tham chiếu từ
monitor của sink mặc định — dùng khi một tiến trình khác cũng phát ra loa.

Cấu hình TSK-S5-08 giao kèm ở `pipewire/neuroedge-echo-cancel.conf` (trong wheel:
`neuroedge/_data/pipewire/`, tìm bằng `neuroedge.paths.echo_cancel_conf()`), **sao chép** vào
`~/.config/pipewire/pipewire.conf.d/` (người dùng) hoặc `/etc/pipewire/pipewire.conf.d/` (hệ
thống), rồi `systemctl restart --user pipewire.service`: `LinuxHAL` đọc/ghi hai nút
`neuroedge.ec.source` / `neuroedge.ec.sink` ở đây khi backend sống được chọn:

```text
# neuroedge-echo-cancel.conf — bản giao kèm, dùng được ngay
context.modules = [
{   name = libpipewire-module-echo-cancel
    args = {
        library.name = "aec/libspa-aec-webrtc"
        node.description = "NeuroEdge Echo Cancel"
        capture.props  = { node.name = "neuroedge.ec.capture" }
        # target.object = "<tên nút micro HAT I2S, từ `pw-cli ls Node`>"   ← dòng DUY NHẤT phải sửa
        source.props   = { node.name = "neuroedge.ec.source" }      # audio.in đọc ở đây
        sink.props     = { node.name = "neuroedge.ec.sink" }        # audio.out phát vào đây
        playback.props = { node.name = "neuroedge.ec.playback"
                           node.autoconnect = true }
    }
}
]
```

Bản giao kèm **không có placeholder**: không đặt `target.object`, module lấy micro nguồn mặc định
của hệ thống. Muốn ghim micro HAT, bỏ chú thích và sửa **đúng một dòng** `target.object` bằng tên
nút `pw-cli ls Node` in ra (mẫu lấy từ cấu hình tham khảo, gist `fathonix/05de5398…`).

**PortAudio nhìn thấy gì — chưa kiểm trên phần cứng.** `audio.in`/`audio.out` sống đọc/ghi thiết bị
qua `sounddevice` → PortAudio, mà host API mặc định trên Linux là **ALSA**: nó liệt kê các PCM ALSA,
còn `neuroedge.ec.source` / `neuroedge.ec.sink` là **tên nút PipeWire**. Hai tên đó chỉ tới được
PortAudio khi có lớp nối: plugin `pipewire-alsa` (thường có sẵn cùng PipeWire) phơi nút ra ALSA, và
cách chắc chắn là thêm một alias PCM trong `~/.asoundrc` / `/etc/asound.conf` trỏ tới nút, hoặc
truyền đúng tên/ chỉ số thiết bị mà `python -c "import sounddevice; print(sounddevice.query_devices())"`
in ra trên chính máy đó (qua `NEUROEDGE_LINUX_AUDIO_IN`/`_OUT`). **Chưa có bước nào ở đây được kiểm
trên Pi** — việc chọn tên/alias là phần của nightly TSK-S4-05; lỗi "no input/output device named …"
của `LinuxHAL` luôn chỉ người đọc về mục này.

### 6.2 Khi nào `linux-rpi5` được khai `aec = true`

Chỉ khi nightly trên RPi 5 (TSK-S4-05) đạt cả hai, trên cùng HAT và loa của bo tham chiếu:

1. **Không tự nghe mình:** phát 20 lần một câu TTS cố định qua `audio.out` khi không ai nói —
   VAD trên `audio.in` không kích hoạt lần nào (0/20).
2. **Mức khử vang:** ERLE (năng lượng micro thô so với sau khử vang, cùng đoạn phát) ≥ 20 dB.

Chưa đạt thì `aec = false` giữ nguyên và `build` tiếp tục từ chối agent cần AEC — không có đường
nào để khai một năng lực chưa đo. Runner CI không có âm thanh (`CONFIG_SOUND` tắt), nên
hai phép đo này chỉ chạy trên Pi.

## 7. Điều tài liệu này không hứa

- Tương đương **timing** giữa target (TSK-S4-04 mới so quyết định).
- Chất lượng âm thanh, AEC, VAD dưới âm học thật — chỉ đo trên thiết bị (A6, I7 — roadmap §4.8).
- Target bậc 2–3 (`jetson`, `stm32`, `rp2350`) — RFC-0002.
