# RFC-0011: Nguyên thủy `motion.*` — lease token, trạng thái an toàn theo cơ cấu

| | |
|:---|:---|
| **Mã RFC** | 0011 |
| **Tiêu đề** | `motion.*` (motor/servo), token thuê có hạn, trạng thái an toàn khai theo cơ cấu, phong bì mở rộng |
| **Hợp đồng bị ảnh hưởng** | `board.v1` · bố cục `NETR` *(chung một lần tăng phiên bản với RFC-0009)* · token `TokenLedger`/`ne_token.c` · kiểm mới ở `neuroedge build` (`p95_latency_ms ≤ lease_ms / 2`, NE3001) · **không** đụng `gate.v1` hay ngữ nghĩa phân giải (`gate lint`) |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-05, FR-PER-02, FR-ACE-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (§9, Q-57) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm token, bố cục `NETR`, chuyển động vật lý) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`, đổi bố cục `NETR` (RFC-0003).
> Task: TSK-W1-03 (thiết kế, RFC này), TSK-W1-04 (hiện thực `motion.*`), TSK-I2a-05 (hiện thực trên bo mạch
> tham chiếu). Quyết định nền: `neuroedge-prd.md` §15 Q-32 (`motion.*` là nguyên thủy riêng), Q-35 (trạng
> thái an toàn khai theo cơ cấu, không khai thì dừng), Q-37 (token thuê có hạn ~200 ms), Q-38 (robot di
> động cần nút dừng khẩn phần cứng), Q-52, Q-53, Q-55. `analog.in` **không** thuộc RFC này (đã chuyển sang
> [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) theo Q-53).

## 1. Vấn đề

Robot cần chuyển động có tham số: tốc độ, góc, thời lượng, ramp. `digital.out` không diễn đạt được (RFC-0010 mới có PWM cho tải đơn giản), và mô hình token hiện tại không hợp với chuyển động liên tục:

- `VerdictToken` (`python/neuroedge/actions/token.py`) mang **tập chân** (`pins: frozenset[str]`), dùng **một lần mỗi chân**, sống `ttl_ms = p95_ms * TTL_FACTOR`, và đóng khi `c.do()` trả về. Không có kênh, không có biên độ, không có "hết hạn thì cơ cấu về đâu".
- Một xung chốt cửa chạy hết là đúng (`docs/spec/voice_fsm.md` §5.3); một motor đang quay khi người dùng hét "dừng" thì **không** được chạy tiếp. Hôm nay không có cách phân biệt (`TODOS.md` #39).
- Test crash-safe cho chuyển động không thể chạy trên QEMU: QEMU không giả lập GPIO (`TODOS.md` #21).

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/board.v1.json` không có nguyên thủy chuyển động, không có trường *trạng thái an toàn* theo cơ cấu (Q-35 đòi RFC cho trường này).
- `gate.v1` không nhận trường lạ (RFC-0005 §2 đã nêu); cờ "vẫn cắt khi đã chạy" theo #39 nếu đặt ở gate là đổi `gate.v1`.
- Token một-lần-mỗi-chân không diễn đạt được *"cho phép quay ở tốc độ ≤ X trên kênh này trong 200 ms nữa"*.
- Bố cục `NETR` v1 (RFC-0003) không mang nhãn gate hay chữ `on_block` (`TODOS.md` #36).

## 3. Thay đổi đề xuất

### 3a. Bo mạch khai kênh chuyển động

Hai hình dạng năng lực riêng, `motor` và `servo` (§9.4), mỗi kênh một bản ghi:

```toml
[capabilities.motion]
motor = [
  { name = "wheel_left", speed_max = 0.6, ramp_min_ms = 200, enable_pin = "motor_en",
    safe_state = "stop", lease_ms = 200 },
]
servo = [
  { name = "gripper", target_min = 0, target_max = 90, unit = "deg", enable_pin = "servo_en",
    safe_state = "hold", holds_position = true, max_hold_ms = 2000, lease_ms = 200 },
]
```

- **`safe_state` ∈ {`stop`, `hold`}**, **không khai ⇒ `stop`** (Q-35, fail-closed). `hold` chỉ hợp lệ khi kênh khai `holds_position = true` kèm `max_hold_ms`; hết `max_hold_ms` thì về `stop`. Không có `home` hay trạng thái nào tự di chuyển (§9.3). Trong tập đó, trạng thái an toàn là quyết định của từng cơ cấu (Q-35).
- **`lease_ms`** mặc định 200, trần 500; lược đồ từ chối giá trị ≤ 0 hoặc > 500 (§9.2).
- **`enable_pin`** bắt buộc, cùng luật PWM ([RFC-0010](0010-pwm-trong-digital-out.md) §9.2): một line `digital.out` có điện trở kéo xuống trên mạch, nên tiến trình chết thì driver bị ngắt (§9.5).
- Phong bì của kênh dùng khoá chung của [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5 (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`), bắt buộc theo luật của mục đó cho mọi chân nối cơ cấu chấp hành.

### 3b. API và phong bì

Tách đôi (§9.4): `motion.motor(channel, speed, direction, ramp_ms)` và `motion.servo(channel, target, speed_max)`. Gọi `motion.servo` lên kênh `motor` (và ngược lại) bị từ chối như kênh lạ. Cả hai đi qua cùng đường HAL: `require_channel → giới hạn bo mạch → envelope → authorize → record`. Phong bì của RFC-0007 áp theo kênh: tốc độ tối đa, **thời gian chạy liên tục tối đa** (`max_continuous_ms`) và tần suất lệnh; tích luỹ ở HAL, không ở gate (bất biến số 4).

Giới hạn ở hai nơi, **cả hai cùng cưỡng chế, giới hạn chặt hơn thắng** (§9.5):

- **Bo mạch:** giới hạn phần cứng của kênh (khai ở `board.v1`) sinh thành bảng firmware, kiểm lúc boot; self-test hỏng ⇒ từ chối mọi lệnh `motion.*`.
- **Gate:** giới hạn tham số (tốc độ, đích) là `arguments` của gate như RFC-0005, nằm trong `NETR`; walker C đã đọc được.

### 3c. Token thuê có hạn (Q-37)

Một **lease** mang: kênh, biên độ tối đa (tốc độ, góc), thời hạn `lease_ms` của kênh (mặc định 200, trần 500 khai ở bo mạch). `gate.v1` **không** mang `lease_ms`, nên gate không có đường nào nâng lease quá giá trị bo mạch; vế "gate chỉ được hạ" của §9.2 không có trường gate ở RFC này — cho gate hạ lease là đổi `gate.v1`, cần RFC riêng. Gia hạn **chỉ** bằng một lời gọi mới qua gate, lượng giá lại đầy đủ; không còn lệnh ⇒ lease hết hạn ⇒ cơ cấu về `safe_state`. Lease tách khỏi `TTL_FACTOR` của token phán quyết (§9.2).

`budget.p95_latency_ms` của gate phải ≤ `lease_ms / 2`, không thì **`neuroedge build`** từ chối (`BoardCapabilityError`, NE3001). Chỉ lúc build mới có cả gate lẫn `lease_ms` của bo mạch; `gate lint` và ngữ nghĩa phân giải không đổi (§9.2).

Thay đổi: `VerdictToken`, `TokenLedger.issue/authorize` (host) và `ne_token.c`/`ne_token.h` (thiết bị) cùng đổi; lease không dùng lại được khi hết hạn hay sai kênh. Gate vẫn thuần: đếm hạn ở HAL/runtime.

### 3d. Cắt lời (barge-in) — đóng `TODOS.md` #39 cho chuyển động

Với `motion.*`: cắt lời, BLOCK hay mất liên lạc ⇒ **gửi ngay lệnh `safe_state`** và ngừng gia hạn lease; không có cờ nào cho chuyển động "chạy tiếp khi đã giao" (§9.1). Lệnh dừng tức thì là lớp chính; lease hết hạn là lớp dự phòng (mất liên lạc mà không phía nào kịp gửi lệnh vẫn dẫn tới `safe_state`, như `cmd_vel` timeout của ROS). **Không thêm cờ vào `gate.v1`.** Xung `digital.out` (chốt cửa) giữ luật "chạy hết" của `docs/spec/voice_fsm.md` §5.3; nếu về sau có cơ cấu `digital.out` cần "cắt cả khi đã chạy", #39 vẫn là mục hoãn cho phần đó.

### 3e. `NETR` (`TODOS.md` #36)

Bản thân `motion.*` **không** cần nút mới: giới hạn tốc độ/đích dùng bảng tham số RFC-0005. Bảng giới hạn phần cứng của §3b là bảng firmware sinh từ `board.v1`, **không** thuộc `NETR`. Lần tăng `layout_version` là chung với [RFC-0009](0009-tieu-chi-so-numeric.md) và mang nhãn gate + chữ `on_block` (#36) để chỉ bump một lần. Bố cục byte ghim ở PR thứ hai.

### 3f. Kiểm thử trên bo mạch thật và an toàn cơ khí

Bo mạch mang `motion` (§9.6): `linux-rpi5` (PWM phần cứng + driver có `enable_pin`) và `esp32s3-box-3` (LEDC qua chân dock, xác minh ở TSK-I3a-01; nếu dock không đủ chân thì bo camera của RFC-0013 mang); `sim-rpi5` và `sim-default` soi theo. Test crash-safe (SIGKILL/crash tiến trình, rút mạng, watchdog, mất điện giữa lệnh) **chạy trên cả hai bo thật** (TSK-W1-04, TSK-I2a-05), không QEMU/Wokwi (#21). Robot di động bắt buộc nút dừng khẩn phần cứng cắt nguồn motor không qua phần mềm (Q-38).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — khối `motion` là tuỳ chọn. Trong khối, `enable_pin` bắt buộc và `safe_state` chỉ nhận `stop`/`hold` (§3a) |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `motion` đúng hình dạng (cùng điểm siết chặt khoá `capabilities` chưa từng có nghĩa như RFC-0007 §4) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `board.v1`. **Có** cho `NETR` (`layout_version` 2, chung với RFC-0009 và #36) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — `gate.v1`, `gate lint` và ngữ nghĩa phân giải không đổi. Kiểm `p95_latency_ms ≤ lease_ms / 2` là kiểm mới của `neuroedge build` trên cặp gate + bo mạch; chỉ chạm agent dùng `motion.*`, chưa có |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không; sự kiện `motion.*` mới (kể cả lệnh `safe_state`) đặt cạnh `actuator_command`/`actuator_aborted` (`docs/spec/simulation_coverage.md` §3) |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | **Có** (§3e), và `ne_token.c`. Firmware thêm bảng giới hạn kênh sinh từ `board.v1` và self-test lúc boot (§3b), ngoài `NETR` |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca `motion.motor`/`motion.servo` mới. Token `digital.out` giữ ngữ nghĩa một-lần |
| Danh mục mã lỗi (`neuroedge-prd.md` Phụ lục B) | Không thêm lớp hay mã mới. Dòng `BoardCapabilityError` (NE3001) mở rộng nguyên nhân: gate có `p95_latency_ms > lease_ms / 2` của kênh chuyển động mà agent dùng |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1`, ngữ nghĩa phân giải, năm nguyên tắc không đổi. Mọi lệnh chuyển động vẫn đi qua gate; lease chỉ **rút ngắn** thời gian một phán quyết còn hiệu lực, và mỗi lần gia hạn là một lần lượng giá lại đầy đủ.
- **Fail-closed sâu hơn:** không khai `safe_state` ⇒ `stop`; cắt lời, BLOCK, mất liên lạc ⇒ gửi ngay `safe_state`; lease hết hạn ⇒ `safe_state`; `hold` quá `max_hold_ms` ⇒ `stop`; không trạng thái an toàn nào tự di chuyển; kênh lạ, sai loại kênh, biên độ vượt lease, lease đã hết ⇒ từ chối, không dùng lại; self-test giới hạn hỏng lúc boot ⇒ từ chối mọi lệnh `motion.*`.
- **Hai lớp giới hạn độc lập:** gate lỏng không vượt được bảng giới hạn phần cứng, bo mạch khai sai không vượt được gate; giới hạn chặt hơn thắng.
- **Lease không thay thế crash-safe:** khi tiến trình bị SIGKILL, không phần mềm nào gửi được `safe_state`. Chỉ có phần cứng (`enable_pin` kéo xuống, watchdog, giới hạn dòng, nút dừng khẩn) — nên test trên bo mạch thật là điều kiện chấp nhận, không phải tuỳ chọn. Hệ quả: khi crash, `enable_pin` ngắt driver bất kể `safe_state` khai `hold`.
- **NeuroEdge không phải chức năng an toàn được chứng nhận** (Q-38): RFC này không tuyên bố SIL/PL. Robot di động cần nút dừng khẩn phần cứng ngoài phạm vi phần mềm.
- **Rủi ro thay đổi token:** `ne_token.c` là mã thiết bị; đổi ngữ nghĩa một-lần sang lease có thể tạo đường phát lại. Bắt buộc fuzz và test đột biến như RFC-0003 §7.
- **Gate 10–20 lần/giây** cho robot di động (Q-34): gia hạn phải tới trước khi lease hết, nên `neuroedge build` đòi `p95_latency_ms ≤ lease_ms / 2` (§3c).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Nhồi motor vào `digital.out` | Q-32: hợp đồng rõ hơn khi nguyên thủy riêng; `digital.out` không có kênh/ramp/lease |
| Một API chung `motion.drive(...)` cho motor và servo | Giới hạn của hai loại khác nhau về bản chất; gộp làm một thì ràng buộc lỏng (§9.4) |
| Token một lần dài hơn (TTL lớn), hoặc lease suy từ `TTL_FACTOR` | Cơ cấu chạy đến hết TTL sau khi mất liên lạc; chính điều Q-37 muốn tránh. Lease có mặc định và trần riêng (§9.2) |
| Cắt lời chỉ thôi gia hạn, chờ lease tự hết | Motor vẫn quay tới `lease_ms` sau khi người dùng phản đối; lệnh `safe_state` tức thì là lớp chính (§9.1) |
| Cờ "vẫn cắt khi đã chạy" trong `gate.v1` (#39) | Đổi `gate.v1`, kéo theo ngữ nghĩa kế thừa; lệnh `safe_state` tức thì cộng lease đạt kết quả đó cho chuyển động mà không đổi gate |
| `safe_state` mở rộng (`release`, `finish_pulse`, `home`…) | Khi mất giám sát, không cơ cấu nào được tự chuyển động; chỉ `stop`/`hold` (§9.3). Chạy hết xung là luật của `digital.out`, không của `motion.*` |
| Kiểm `p95_latency_ms ≤ lease_ms / 2` ở `gate lint` | Gate không mang `lease_ms`; thêm trường là đổi `gate.v1`. Chỉ `build` có đủ cả hai (§9.2) |
| Gate đếm thời gian chạy tích luỹ | Phá tính thuần (bất biến số 4) |
| Tách `NETR` v2 riêng cho mỗi RFC | Nhiều lần bump; firmware phải theo từng bản (§3e) |

## 7. Bằng chứng kiểm chứng

- [ ] Profile `boards/` khai `motion` trên `linux-rpi5`, `esp32s3-box-3` (hoặc bo camera theo RFC-0013), soi ở `sim-rpi5`, `sim-default` (§9.6). Phản chứng: `safe_state` ngoài {`stop`, `hold`} (`home`, `release`); `hold` thiếu `holds_position = true` hoặc `max_hold_ms`; thiếu `enable_pin`; `lease_ms` ≤ 0 hoặc > 500; khoá servo trên bản ghi `motor` và ngược lại; `speed_max` ngoài (0, 1]
- [ ] Test host — lease (§9.2): thiếu `lease_ms` ⇒ 200; lease hết hạn ⇒ `safe_state` và sự kiện có thể replay; lease sai kênh/hết hạn bị từ chối; không có đường gia hạn nào ngoài lời gọi mới qua gate (lời gọi bị BLOCK không gia hạn); đổi `TTL_FACTOR` không đổi lease
- [ ] Test host — cắt lời (§9.1): cắt lời, BLOCK, mất liên lạc ⇒ lệnh `safe_state` ghi ở cùng tick đồng hồ ảo với sự kiện kích, **trước** khi lease hết, và không gia hạn nữa; xung `digital.out` đã giao vẫn chạy hết (`voice_fsm.md` §5.3)
- [ ] Test host — `safe_state` (§9.3): không khai ⇒ `stop`; `hold` hết `max_hold_ms` ⇒ `stop`
- [ ] Test host — API (§9.4): `motion.motor` lên kênh `servo` và ngược lại bị từ chối; ca mới ở `fixtures/tool_calls/`, khép kín hai chiều trong `expected_results.yaml`
- [ ] Test giới hạn (§9.5): gate lỏng hơn bo mạch ⇒ giới hạn bo mạch thắng; bo mạch lỏng hơn gate ⇒ gate thắng; self-test lúc boot hỏng ⇒ mọi lệnh `motion.*` bị từ chối
- [ ] Test `neuroedge build` (§9.2): gate có `p95_latency_ms > lease_ms / 2` ⇒ `BoardCapabilityError` (NE3001), không sinh firmware; đúng ngưỡng thì qua. `neuroedge gate lint` không đổi kết quả trên cùng gate
- [ ] Walker C/`ne_token.c` khớp `TokenLedger` host (mở rộng `python/tests/test_c_token.py`), fuzz ASan/UBSan
- [ ] **Test crash-safe trên cả hai bo thật** (§9.6): kill -9 tiến trình, rút WiFi, treo firmware, mất điện giữa lệnh ⇒ cơ cấu về `safe_state` hoặc bị `enable_pin` ngắt; kết quả đo đính kèm PR
- [ ] `sim` mô hình lease bằng đồng hồ ảo, không giàu hơn bo mạch tham chiếu; `neuroedge verify` và `neuroedge gate lint` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json` (`motion.motor`, `motion.servo`, `safe_state`, `lease_ms`, `enable_pin`, `holds_position`, `max_hold_ms`); ghim bố cục `NETR` v2 cùng RFC-0009 và `TODOS.md` #36 (đóng #36; đóng #39 cho `motion.*`, giữ hoãn phần `digital.out`)
- [ ] Sửa `docs/spec/voice_fsm.md` §5: §5.3 có ngoại lệ cho `motion.*` (cắt lời ⇒ gửi ngay `safe_state`); dừng do mất liên lạc là một lần dừng kiểu tắt máy — TSK-W1-04
- [ ] `neuroedge-prd.md` FR-HAL-01 và dòng `BoardCapabilityError` (NE3001) ở Phụ lục B (§4); quyết định mới cấp `Q-N`; `neuroedge-roadmap.md` (TSK-W1-03, TSK-W1-04, TSK-I2a-05)
- [ ] `python/neuroedge/actions/token.py`, `python/neuroedge/hal/`, kiểm `p95_latency_ms ≤ lease_ms / 2` trong `neuroedge build`, `ne_token.c`, walker C, bảng giới hạn firmware và self-test lúc boot
- [ ] Fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã gộp** vào §3–§8; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Cắt lời (`TODOS.md` #39).** Với `motion.*`: cắt lời, BLOCK hay mất liên lạc ⇒ **gửi ngay lệnh `safe_state`** và ngừng gia hạn lease; không có cờ nào cho phép chuyển động "chạy tiếp khi đã giao". Xung `digital.out` giữ luật hiện hành (`docs/spec/voice_fsm.md` §5.3). *Vì sao:* motor đang quay khi người dùng phản đối là nguy hiểm; lease là lớp dự phòng, lệnh dừng tức thì là lớp chính. Đóng #39 cho chuyển động.
2. **Lease.** `lease_ms` mặc định 200, trần 500 (trần khai ở bo mạch, gate chỉ được hạ). Gia hạn chỉ bằng một lời gọi mới qua gate, lượng giá lại đầy đủ. `budget.p95_latency_ms` của gate phải ≤ `lease_ms / 2`, không thì `neuroedge build` từ chối (`BoardCapabilityError`, NE3001): chỉ lúc build mới có cả gate lẫn `lease_ms` của bo mạch — gate không mang `lease_ms` nên `gate lint` không kiểm được. Lease tách khỏi `TTL_FACTOR` của token phán quyết. *Vì sao:* gia hạn phải kịp tới trước khi lease hết, và mỗi lần gia hạn là một lần gate được hỏi lại.
3. **`safe_state` ∈ {`stop`, `hold`}**, mặc định `stop`. `hold` chỉ khai được khi bo mạch khai kênh đó `holds_position = true` kèm `max_hold_ms`; hết `max_hold_ms` thì về `stop`. Không có `home` hay trạng thái nào tự di chuyển. *Vì sao:* khi mất giám sát, không cơ cấu nào được tự chuyển động.
4. **API tách đôi:** `motion.motor` (tốc độ, chiều, ramp) và `motion.servo` (góc đích, tốc độ tối đa), hai hình dạng năng lực riêng. *Vì sao:* giới hạn của hai loại khác nhau về bản chất; gộp làm một thì ràng buộc lỏng.
5. **Nơi giữ giới hạn.** Giới hạn phần cứng của kênh (khai ở `board.v1`) sinh thành bảng firmware, kiểm lúc boot (self-test hỏng ⇒ từ chối mọi lệnh `motion.*`); ràng buộc của gate nằm trong `NETR`. Cả hai cùng cưỡng chế, giới hạn chặt hơn thắng. Kênh chuyển động cũng bắt buộc `enable_pin` như PWM (RFC-0010 §9). *Vì sao:* gate lỏng không vượt được phần cứng, phần cứng khai sai không vượt được gate.
6. **Bo mạch mang `motion`:** `linux-rpi5` (PWM phần cứng + driver có `enable_pin`) và `esp32s3-box-3` (LEDC qua chân dock, xác minh ở TSK-I3a-01; nếu dock không đủ chân thì bo camera của RFC-0013 mang); `sim-rpi5` và `sim-default` soi theo. Test mất điện giữa lệnh chạy trên cả hai bo thật (TSK-W1-04).
