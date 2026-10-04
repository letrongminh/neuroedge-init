# RFC-0011: Nguyên thủy `motion.*` — lease token, trạng thái an toàn theo cơ cấu

| | |
|:---|:---|
| **Mã RFC** | 0011 |
| **Tiêu đề** | `motion.*` (motor/servo), token thuê có hạn, trạng thái an toàn khai theo cơ cấu, phong bì mở rộng |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khối `capabilities.motion` và `envelope` theo kênh)* · token `TokenLedger`/`ne_token.c` · kiểm mới ở `neuroedge build` (`p95_latency_ms ≤ lease_ms / 2`, NE3001) · **không** thêm trường vào `NETR` (`NETR` v2 do RFC-0009 / TSK-W1-02 mang) · **không** đụng `gate.v1` hay ngữ nghĩa phân giải (`gate lint`) |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-05, FR-PER-02, FR-ACE-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-01) — kỹ thuật trưởng ký trên PR #78; sửa theo review 2026-10-01 (§9, Q-62); hiện thực trong PR thứ hai |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm token, chuyển động vật lý) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json` và sổ token C (`ne_token.c`). Bố cục `NETR` v2 do RFC-0009 (TSK-W1-02) mang.
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

[capabilities.motion.envelope.wheel_left]
window_s = 60
max_on_ms_per_window = 30000
min_interval_ms = 2000
max_continuous_ms = 10000

[capabilities.motion.envelope.gripper]
window_s = 60
max_on_ms_per_window = 10000
min_interval_ms = 1000
max_continuous_ms = 3000
```

- **`safe_state` ∈ {`stop`, `hold`}**, **không khai ⇒ `stop`** (Q-35, fail-closed). `hold` chỉ hợp lệ khi kênh khai `holds_position = true` kèm `max_hold_ms`; hết `max_hold_ms` thì về `stop`. Không có `home` hay trạng thái nào tự di chuyển (§9.3). Trong tập đó, trạng thái an toàn là quyết định của từng cơ cấu (Q-35).
- **`lease_ms`** mặc định 200, trần 500; lược đồ từ chối giá trị ≤ 0 hoặc > 500 (§9.2).
- **`enable_pin`** bắt buộc, cùng luật PWM ([RFC-0010](0010-pwm-trong-digital-out.md) §9.2): một line `digital.out` có điện trở kéo xuống trên mạch, nên tiến trình chết thì driver bị ngắt (§9.5).
- **Phong bì của kênh:** Khai tại `[capabilities.motion.envelope.<kênh>]` với các khoá chung của [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5 (`window_s`, `max_on_ms_per_window`, `min_interval_ms`, `max_continuous_ms`). Mọi kênh `motion.*` luôn là cơ cấu chấp hành, không khai `signal_pins` được. Thiếu phong bì ⇒ `BoardCapabilityError` (NE3001) lúc nạp. `enable_pin` của kênh do HAL tự quản: agent không gọi được (lệnh `digital.out` trực tiếp tới nó bị từ chối), miễn phong bì riêng của RFC-0007, không khai trong `signal_pins`.

### 3b. API và phong bì

Tách đôi (§9.4): `motion.motor(channel, speed, direction, ramp_ms)` và `motion.servo(channel, target, speed_max)`. Gọi `motion.servo` lên kênh `motor` (và ngược lại) bị từ chối như kênh lạ. Cả hai đi qua cùng đường HAL: `require_channel → giới hạn bo mạch → envelope → authorize → record`.

Quy tắc cưỡng chế phong bì và lần chạy của `motion.*`:

- **Định nghĩa lần chạy (run):** Lần chạy của `motion.*` là một chuỗi lease liên tiếp trên cùng kênh, trong đó lease mới được cấp trước khi lease cũ hết. Mỗi lease dùng cho đúng một lệnh; lệnh tiếp theo là một lời gọi mới qua gate. Không được lặp lệnh trong cùng một lease.
- **Thứ tự HAL và `min_interval_ms`:** `min_interval_ms` chỉ áp cho lệnh bật, tức lúc bắt đầu một lần chạy để đưa cơ cấu từ trạng thái an toàn sang hoạt động, tính từ lúc lần chạy trước kết thúc. Các lần gia hạn lease trong cùng một lần chạy không bị chặn bởi `min_interval_ms`.
- **Thời lượng chạy liên tục:** `max_continuous_ms` áp cho toàn bộ cả lần chạy, tính từ thời điểm bắt đầu lần chạy.
- **Tự tắt và giữ trước ngân sách:** Mọi lệnh bật đều có thời hạn hữu hạn. Lúc bắt đầu lần chạy, phong bì giữ trước `max_continuous_ms` trong `max_on_ms_per_window`. Khi lần chạy kết thúc, HAL hoàn lại phần chưa dùng. Nếu `authorize` thất bại sau khi đã giữ trước, hoàn lại toàn bộ phần đã giữ: không tiêu token, không phát xung.
- **Phong bì sống qua khởi động lại (write-ahead):** Tổng thời gian bật đã giữ trong cửa sổ được ghi bền trước khi bật: NVS trên `esp32s3`, tệp trạng thái trên `linux`; `sim` mô phỏng cùng luật. Với `motion.*`, ghi một lần mỗi lần chạy (lúc bắt đầu), không ghi mỗi lần gia hạn để chống mòn flash. Sau khởi động lại, coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động, chiếm ngân sách tới `window_s` sau khởi động. Không đọc được, hỏng hoặc thiếu bản ghi ⇒ coi cả cửa sổ đã dùng hết. Vẫn giữ luật chờ `min_interval_ms` trước lần bật đầu sau khởi động.

Giới hạn ở hai nơi, **cả hai cùng cưỡng chế, giới hạn chặt hơn thắng** (§9.5):

- **Bo mạch:** giới hạn phần cứng của kênh (khai ở `board.v1`) sinh thành bảng firmware, kiểm lúc boot; self-test hỏng ⇒ từ chối mọi lệnh `motion.*` trừ `safe_state`.
- **Gate:** giới hạn tham số (tốc độ, đích) là `arguments` của gate như RFC-0005, nằm trong `NETR`; walker C đã đọc được.

### 3c. Token thuê có hạn (Q-37)

Một **lease** mang: kênh, biên độ tối đa (tốc độ, góc), thời hạn `lease_ms` của kênh (mặc định 200, trần 500 khai ở bo mạch). `gate.v1` **không** mang `lease_ms`, nên gate không có đường nào nâng hay hạ lease quá giá trị bo mạch (§9.2). Mỗi lease dùng cho đúng một lệnh. Gia hạn **chỉ** bằng một lời gọi mới qua gate, lượng giá lại đầy đủ; kiểm biên độ chặt chẽ; không còn lệnh ⇒ lease hết hạn ⇒ cơ cấu về `safe_state`. Lời gọi bị BLOCK không gia hạn lease. Lease tách khỏi `TTL_FACTOR` của token phán quyết (§9.2).

`budget.p95_latency_ms` của gate phải ≤ `lease_ms / 2`, không thì **`neuroedge build`** từ chối (`BoardCapabilityError`, NE3001). Chỉ lúc build mới có cả gate lẫn `lease_ms` của bo mạch; `gate lint` và ngữ nghĩa phân giải không đổi (§9.2).

Cơ chế đếm hạn và giám sát độc lập ngoài tiến trình: Hẹn giờ tự tắt và lease không được chỉ sống trong tiến trình runtime vì tiến trình có thể bị treo.
- Trên `esp32s3`: Task Watchdog (TWDT) cộng hẹn giờ phần cứng; watchdog reset thì boot với `enable_pin` ở mức kéo xuống.
- Trên `linux`: `enable_pin` (và line chân cơ cấu) do một tiến trình giám sát riêng giữ; runtime gửi nhịp tim; mất nhịp quá thời hạn ⇒ giám sát thả `enable_pin` và tắt kênh.

Thay đổi: `VerdictToken`, `TokenLedger.issue/authorize` (host) và `ne_token.c`/`ne_token.h` (thiết bị) cùng đổi; lease không dùng lại được khi hết hạn hay sai kênh. Gate vẫn thuần.

### 3d. Cắt lời (barge-in) — đóng `TODOS.md` #39 cho chuyển động

Với `motion.*`: cắt lời, BLOCK hay mất liên lạc ⇒ **gửi ngay lệnh `safe_state`** và ngừng gia hạn lease; không có cờ nào cho chuyển động "chạy tiếp khi đã giao" (§9.1). Lệnh dừng tức thì là lớp chính; lease hết hạn là lớp dự phòng (mất liên lạc mà không phía nào kịp gửi lệnh vẫn dẫn tới `safe_state`, như `cmd_vel` timeout của ROS). **Không thêm cờ vào `gate.v1`.** Xung `digital.out` (chốt cửa) giữ luật "chạy hết" của `docs/spec/voice_fsm.md` §5.3; nếu về sau có cơ cấu `digital.out` cần "cắt cả khi đã chạy", #39 vẫn là mục hoãn cho phần đó.

**Lệnh về phía an toàn không bao giờ bị chặn:** Gồm `motion.*` gửi `safe_state` (`stop`/`hold`) và mọi lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, hết lease, khi cắt lời, BLOCK, mất liên lạc, `hal.close()`. Các lệnh này không qua phong bì, không cần ALLOW hay token, không chờ `ramp_min_ms`, `min_interval_ms` hay chờ sau khởi động. Đây là **ngoại lệ duy nhất** của luật "không lệnh nào ra phần cứng mà không có ALLOW". Nó chỉ áp cho lệnh đưa cơ cấu về trạng thái an toàn đã khai ở bo mạch. Lệnh vẫn ghi vết ghi, kèm nguyên nhân. Ngoại lệ này phải được ghi vào `docs/spec/threat_model.md` §1 khi hiện thực (ghi ở §8).

### 3e. `NETR` (`TODOS.md` #36)

Bản thân `motion.*` **không thêm trường nào vào `NETR`**. Giới hạn tốc độ/đích dùng bảng tham số RFC-0005. Bảng giới hạn phần cứng của §3b là bảng firmware sinh từ `board.v1`, **không** thuộc `NETR`. Lần tăng `layout_version` = 2 là của [RFC-0009](0009-tieu-chi-so-numeric.md) (TSK-W1-02), mang bảng `numeric` và nhãn gate + chữ `on_block` (#36). RFC này chỉ đổi sổ token `ne_token.c` và host `TokenLedger` để quản lý lease.

### 3f. Kiểm thử trên bo mạch thật và an toàn cơ khí

Bo mạch mang `motion` (§9.6): `linux-rpi5` (PWM phần cứng + driver có `enable_pin`) và `esp32s3-box-3` (LEDC qua chân dock, xác minh ở TSK-I3a-01; nếu dock không đủ chân thì `esp32s3-cores3` (M5Stack CoreS3, Q-61) mang qua cổng Grove/M5-Bus). Trong trường hợp CoreS3 mang, chỉ `sim-rpi5` soi `motion`, `sim-default` không soi `motion` vì `sim-default` soi Box-3 (bất biến "sim không giàu hơn bo").

Test crash-safe và treo tiến trình: Test crash-safe (SIGKILL/crash tiến trình, rút mạng, watchdog reset, mất điện giữa lệnh) và **tiến trình bị treo (SIGSTOP)** **chạy trên cả hai bo thật** (TSK-W1-04, TSK-I2a-05), không QEMU/Wokwi (#21). Tiêu chí chấp nhận: tiến trình treo (SIGSTOP) trong lúc bật ⇒ cơ cấu về an toàn trong thời hạn cộng biên đã khai. Robot di động bắt buộc nút dừng khẩn phần cứng cắt nguồn motor không qua phần mềm (Q-38).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — khối `motion` là tuỳ chọn. Trong khối, `enable_pin` và phong bì tại `[capabilities.motion.envelope.<kênh>]` là bắt buộc; `safe_state` chỉ nhận `stop`/`hold` (§3a). Kênh `motion` không được khai `signal_pins`. Ba profile bậc 1 trong `boards/` phải thêm phong bì trong PR hiện thực, với giá trị đủ rộng để ba vết ghi chuẩn mực vẫn replay y nguyên (ví dụ `door_lock` nhận xung 30.000 ms ⇒ `max_continuous_ms` ≥ 30000); chưa có profile bên ngoài |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `motion` đúng hình dạng và có phong bì kênh (cùng điểm siết chặt khoá `capabilities` chưa từng có nghĩa như RFC-0007 §4) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `board.v1`. **Không** cho `NETR` trong RFC này: `layout_version = 2` do RFC-0009 (TSK-W1-02) mang; RFC này không thêm trường nào vào `NETR` |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — `gate.v1`, `gate lint` và ngữ nghĩa phân giải không đổi. Kiểm `p95_latency_ms ≤ lease_ms / 2` là kiểm mới của `neuroedge build` trên cặp gate + bo mạch; chỉ chạm agent dùng `motion.*`, chưa có |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không; sự kiện `motion.*` mới (kể cả lệnh `safe_state`) đặt cạnh `actuator_command`/`actuator_aborted` (`docs/spec/simulation_coverage.md` §3) |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | **Không** đổi bố cục `NETR` hay walker C trong RFC này. Chỉ đổi sổ token `TokenLedger` (host) và `ne_token.c` (thiết bị) để quản lý lease. Firmware thêm bảng giới hạn kênh sinh từ `board.v1` và self-test lúc boot (§3b) |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca `motion.motor`/`motion.servo` mới. Token `digital.out` giữ ngữ nghĩa một-lần |
| Danh mục mã lỗi (`neuroedge-prd.md` Phụ lục B) | Không thêm lớp hay mã mới. Dòng `BoardCapabilityError` (NE3001) mở rộng nguyên nhân: gate có `p95_latency_ms > lease_ms / 2` của kênh chuyển động mà agent dùng, hoặc bo mạch khai kênh `motion` mà thiếu khối phong bì `[capabilities.motion.envelope.<kênh>]` |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1`, ngữ nghĩa phân giải, năm nguyên tắc không đổi. Mọi lệnh chuyển động vẫn đi qua gate; lease chỉ **rút ngắn** thời gian một phán quyết còn hiệu lực, và mỗi lần gia hạn là một lần lượng giá lại đầy đủ. Mỗi lease dùng cho đúng một lệnh.
- **Fail-closed sâu hơn:** không khai `safe_state` ⇒ `stop`; cắt lời, BLOCK, mất liên lạc, hết hạn lease, hết `max_continuous_ms` ⇒ gửi ngay `safe_state`; `hold` quá `max_hold_ms` ⇒ `stop`; không trạng thái an toàn nào tự di chuyển; kênh lạ, sai loại kênh, biên độ vượt lease, lease đã hết ⇒ từ chối, không dùng lại; self-test giới hạn hỏng lúc boot ⇒ từ chối mọi lệnh `motion.*` trừ `safe_state`. Lệnh `safe_state` là ngoại lệ duy nhất không bao giờ bị chặn, đảm bảo cơ cấu luôn được đưa về an toàn khi có sự cố.
- **Lớp fail-safe lúc chạy khi `p95_latency_ms` rỗng nghĩa:** `budget.p95_latency_ms` do tác giả gate tự khai, nên kiểm tra lúc build có thể rỗng nghĩa nếu khai báo lạc quan. Việc cưỡng chế hết hạn lease ở HAL/runtime lúc chạy thực tế vẫn là lớp phòng vệ fail-safe cốt lõi, không phụ thuộc vào khai báo của gate.
- **Hai lớp giới hạn độc lập:** gate lỏng không vượt được bảng giới hạn phần cứng, bo mạch khai sai không vượt được gate; giới hạn chặt hơn thắng.
- **Lease không thay thế crash-safe:** khi tiến trình bị SIGKILL hoặc bị treo (SIGSTOP), phần mềm runtime không tự gửi được `safe_state`. Trên `esp32s3`, Task Watchdog (TWDT) cộng timer phần cứng đảm bảo reset và boot với `enable_pin` kéo xuống. Trên `linux`, tiến trình giám sát độc lập giữ `enable_pin` qua nhịp tim; mất nhịp tim do crash hay SIGSTOP sẽ tự động thả `enable_pin` và ngắt kênh. Test crash-safe và treo tiến trình trên bo thật là điều kiện chấp nhận. Hệ quả: khi crash/treo, `enable_pin` ngắt driver bất kể `safe_state` khai `hold`.
- **Phong bì sống qua khởi động lại (write-ahead):** Tổng thời gian bật được ghi bền vào NVS/tệp trạng thái một lần mỗi lần chạy; sau khởi động lại, ngân sách đã ghi chiếm cửa sổ `window_s`, chống bypass hạn mức bằng cách khởi động lại thiết bị.
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
| Cho gate điều chỉnh `lease_ms` (nâng hoặc hạ) | Đổi `gate.v1`; gate hiện tại không mang trường lease. Lease hoàn toàn do bo mạch quyết định (§9.2) |
| Kiểm `p95_latency_ms ≤ lease_ms / 2` ở `gate lint` | Gate không mang `lease_ms`; thêm trường là đổi `gate.v1`. Chỉ `build` có đủ cả hai (§9.2) |
| Gate đếm thời gian chạy tích luỹ | Phá tính thuần (bất biến số 4) |
| Tách `NETR` v2 riêng cho mỗi RFC | Nhiều lần bump; firmware phải theo từng bản (§3e) |

## 7. Bằng chứng kiểm chứng

- [ ] Profile `boards/` khai `motion` trên `linux-rpi5`, `esp32s3-box-3` (hoặc `esp32s3-cores3` qua cổng Grove/M5-Bus nếu dock Box-3 thiếu chân, §9.6); khi CoreS3 mang, chỉ `sim-rpi5` soi `motion`, `sim-default` không soi `motion` (bất biến "sim không giàu hơn bo"). Phản chứng: kênh `motion` thiếu phong bì `[capabilities.motion.envelope.<kênh>]` ⇒ `BoardCapabilityError` (NE3001) lúc nạp; kênh `motion` khai `signal_pins` bị từ chối; `safe_state` ngoài {`stop`, `hold`} (`home`, `release`); `hold` thiếu `holds_position = true` hoặc `max_hold_ms`; thiếu `enable_pin`; `lease_ms` ≤ 0 hoặc > 500; khoá servo trên bản ghi `motor` và ngược lại; `speed_max` ngoài (0, 1]. Ba profile bậc 1 thêm phong bì đủ rộng cho ba vết ghi chuẩn mực replay y nguyên
- [x] Test host — lệnh an toàn không bao giờ bị chặn: lệnh `safe_state` (`stop`/`hold`) gửi khi cắt lời, BLOCK, mất liên lạc, hết hạn lease, hết `max_continuous_ms`, hoặc `hal.close()` không cần token/ALLOW, không qua phong bì, không chờ `ramp_min_ms` hay `min_interval_ms`, không chờ sau khởi động; vết ghi ghi nhận đầy đủ kèm nguyên nhân — *đạt (TSK-I2a-05): `test_stop_needs_no_token_no_envelope_and_does_not_wait_for_a_ramp`, `test_close_stops_every_channel_whatever_it_declares_and_records_why`, `test_a_blocked_call_does_not_renew_it_and_sends_the_channel_safe`, `test_a_late_tick_still_stops_the_model_at_the_leases_end`, `test_an_unreadable_record_refuses_a_run_but_never_the_stop` (`tests/test_motion.py`)*
- [x] Test host — chuỗi lease và lần chạy qua phong bì: chuỗi lease gia hạn liên tiếp mỗi ~100 ms trên cùng kênh không bị chặn bởi `min_interval_ms` (dù `min_interval_ms = 2000`); `min_interval_ms` chỉ kiểm tại thời điểm bắt đầu lần chạy mới; `max_continuous_ms` áp cho toàn bộ cả lần chạy, hết `max_continuous_ms` ⇒ HAL tự động phát lệnh `safe_state` — *đạt: `test_renewals_every_100ms_are_not_held_up_by_min_interval_ms`, `test_min_interval_ms_is_checked_only_when_a_run_starts`, `test_max_continuous_ms_covers_the_whole_run_and_the_hal_sends_safe_at_its_end` (`tests/test_motion.py`); trên `linux` `test_the_envelope_gates_a_run_on_linux_too` (`tests/test_motion_linux.py`)*
- [x] Test host — một lệnh mỗi lease: mỗi lease dùng cho đúng một lệnh; gửi lệnh thứ hai hoặc lặp lại lệnh trên cùng một lease bị HAL từ chối — *đạt: `test_a_lease_carries_exactly_one_command` (`tests/test_motion.py`)*
- [x] Test host — giữ trước và hoàn ngân sách: bắt đầu lần chạy phong bì giữ trước `max_continuous_ms` trong `max_on_ms_per_window`; lần chạy kết thúc sớm ⇒ HAL hoàn lại thời gian dư vào ngân sách cửa sổ; nếu `authorize` thất bại sau khi giữ ⇒ hoàn lại toàn bộ phần đã giữ, không tiêu token, không phát xung — *đạt: `test_a_run_reserves_max_continuous_ms_and_gives_back_the_unused_part`, `test_an_over_budget_run_is_refused_and_nothing_moves`, `test_a_proof_the_hal_refuses_gives_the_whole_reservation_back` (`tests/test_motion.py`)*
- [ ] Test host — phong bì sống qua khởi động lại: tổng thời gian bật được ghi bền (write-ahead) vào NVS (`esp32s3`) hoặc tệp trạng thái (`linux`) một lần mỗi lần chạy (không ghi mỗi lần gia hạn); sau khởi động lại, ngân sách đã ghi chiếm cửa sổ `window_s`; hỏng hoặc thiếu bản ghi ⇒ coi cả cửa sổ đã dùng hết; kiểm tra bắt buộc chờ `min_interval_ms` trước lần bật đầu sau khởi động — *phần tệp trạng thái (`linux`) đạt: `test_a_run_writes_its_on_time_once_at_its_start_and_not_for_every_renewal`, `test_after_a_restart_the_recorded_run_holds_budget_and_the_channel_waits`, `test_an_unreadable_record_refuses_a_run_but_never_the_stop`; NVS của `esp32s3` thuộc firmware (TSK-W1-04), chưa*
- [x] Test host — lease (§9.2): thiếu `lease_ms` ⇒ 200; lease hết hạn ⇒ `safe_state` và sự kiện có thể replay; lease sai kênh/hết hạn bị từ chối; không có đường gia hạn nào ngoài lời gọi mới qua gate (lời gọi bị BLOCK không gia hạn); đổi `TTL_FACTOR` không đổi lease — *đạt: `test_a_missing_lease_ms_is_200`, `test_a_channel_nobody_commands_goes_to_its_safe_state_when_the_lease_ends`, `test_a_session_with_leases_replays_the_same_decisions`, `test_a_lease_that_ran_out_before_the_command_is_refused`, `test_a_lease_for_one_channel_is_no_proof_for_another`, `test_a_blocked_call_does_not_renew_it_and_sends_the_channel_safe`, `test_the_lease_is_the_boards_and_not_the_gates_or_the_ttl`*
- [x] Test host — cắt lời (§9.1): cắt lời, BLOCK, mất liên lạc ⇒ lệnh `safe_state` ghi ở cùng tick đồng hồ ảo với sự kiện kích, **trước** khi lease hết, và không gia hạn nữa; xung `digital.out` đã giao vẫn chạy hết (`voice_fsm.md` §5.3) — *đạt: `test_a_barge_in_sends_safe_in_the_same_tick_and_before_the_lease_ends`, `test_a_barge_in_does_not_cut_a_delivered_digital_pulse`, `test_the_voice_session_wires_barge_in_to_motion`*
- [x] Test host — `safe_state` (§9.3): không khai ⇒ `stop`; `hold` hết `max_hold_ms` ⇒ `stop` — *đạt: `test_a_missing_lease_ms_is_200` (không khai ⇒ `stop`), `test_a_servo_that_declares_hold_holds_when_its_lease_ends_then_stops_after_max_hold_ms`, `test_a_hold_never_outlives_the_runs_max_continuous_ms`*
- [x] Test host — API (§9.4): `motion.motor` lên kênh `servo` và ngược lại bị từ chối; ca mới ở `fixtures/tool_calls/`, khép kín hai chiều trong `expected_results.yaml` — *đạt: `test_a_command_of_the_wrong_kind_is_refused_like_an_unknown_channel`; ca `fixtures/tool_calls/{valid,invalid}/motion_*.yaml` khép kín hai chiều (`tests/test_tool_corpus.py`)*
- [ ] Test giới hạn (§9.5): gate lỏng hơn bo mạch ⇒ giới hạn bo mạch thắng; bo mạch lỏng hơn gate ⇒ gate thắng; self-test lúc boot hỏng ⇒ mọi lệnh `motion.*` trừ `safe_state` bị từ chối — *phần host đạt: `test_a_gate_looser_than_the_board_leaves_the_board_in_force`, `test_the_gate_narrows_the_board_and_the_tighter_limit_wins`, `test_the_board_limits_a_motor_command`; self-test giới hạn lúc boot của firmware chưa (TSK-W1-04)*
- [x] Test `neuroedge build` (§9.2): gate có `p95_latency_ms > lease_ms / 2` ⇒ `BoardCapabilityError` (NE3001), không sinh firmware; đúng ngưỡng thì qua. `neuroedge gate lint` không đổi kết quả trên cùng gate — *đạt: `test_a_gate_slower_than_half_the_lease_is_refused_at_build_and_the_boundary_passes`, `test_the_lease_check_is_the_builds_and_gate_lint_does_not_change`, `test_a_failed_lease_check_writes_no_firmware_or_artifact`*
- [ ] Walker C/`ne_token.c` khớp `TokenLedger` host (mở rộng `python/tests/test_c_token.py`), fuzz ASan/UBSan; kiểm tra `NETR` không có trường mới nào từ RFC-0011 — *chưa: firmware ngoài phạm vi TSK-I2a-05 (TSK-W1-04); host `TokenLedger` đã có lease*
- [ ] **Test crash-safe và treo tiến trình trên cả hai bo thật** (§9.6): kill -9 tiến trình (SIGKILL), rút WiFi, mất điện giữa lệnh, và tiến trình bị treo (SIGSTOP) ⇒ trên `linux` tiến trình giám sát độc lập thả `enable_pin` và tắt kênh; trên `esp32s3` TWDT/timer phần cứng reset boot với `enable_pin` kéo xuống; cơ cấu về `safe_state` trong thời hạn cộng biên đã khai; kết quả đo đính kèm PR — *phần CI đạt: SIGSTOP và SIGKILL của runtime làm đường enable xuống trong heartbeat + biên (`tests/test_motion_linux.py`, `tests_linux/test_gpio_motion.py` trên gpio-sim, xanh ở CI run 37153005998); motor/servo/driver thật và `esp32s3` chưa — giai đoạn B*
- [x] `sim` mô hình lease bằng đồng hồ ảo, không giàu hơn bo mạch tham chiếu; `neuroedge verify` và `neuroedge gate lint` xanh — *`SimActuator` + `MotionController` trên đồng hồ ảo, `test_a_session_with_leases_replays_the_same_decisions`; `neuroedge verify` và `gate lint` xanh*

## 8. Việc phải làm khi chấp thuận

- [x] Cập nhật `schemas/board.v1.json` (`motion.motor`, `motion.servo`, `safe_state`, `lease_ms`, `enable_pin`, `holds_position`, `max_hold_ms`, và phong bì bắt buộc `[capabilities.motion.envelope.<kênh>]`, không nhận `signal_pins` trên kênh `motion`); ba profile bậc 1 trong `boards/` bổ sung phong bì đủ rộng để ba vết ghi chuẩn mực replay y nguyên — *đạt: `motion.motor`/`servo`, `safe_state`, `lease_ms`, `enable_pin`, `holds_position`, `max_hold_ms`, phong bì bắt buộc, không nhận `signal_pins` — `tests/test_board_fixtures.py`; ba profile bậc 1 có phong bì*
- [ ] Ghim bố cục `NETR` v2 trong RFC-0009 (TSK-W1-02, đóng #36); RFC-0011 không thêm trường vào `NETR`. Đóng #39 cho `motion.*`, giữ hoãn phần `digital.out`
- [x] Ghi nhận ngoại lệ duy nhất của luật "không lệnh nào ra phần cứng mà không có ALLOW" vào `docs/spec/threat_model.md` §1 cho các lệnh đưa cơ cấu về `safe_state` — *đạt: `docs/spec/threat_model.md` §1 (đoạn "Chuyển động có lease")*
- [x] Sửa `docs/spec/voice_fsm.md` §5: §5.3 có ngoại lệ cho `motion.*` (cắt lời ⇒ gửi ngay `safe_state`); dừng do mất liên lạc là một lần dừng kiểu tắt máy — TSK-W1-04 — *đạt: §5.2 bước 1 và §5.5 (TSK-I2a-05)*
- [ ] `neuroedge-prd.md` FR-HAL-01 và dòng `BoardCapabilityError` (NE3001) ở Phụ lục B (§4); quyết định mới cấp `Q-N`; `neuroedge-roadmap.md` (TSK-W1-03, TSK-W1-04, TSK-I2a-05, TSK-I3a-01 xác minh dock `esp32s3-box-3` / `esp32s3-cores3`) — *dòng NE3001 và NE1002 ở Phụ lục B đã sửa (TSK-I2a-05)*
- [ ] `python/neuroedge/actions/token.py`, `python/neuroedge/hal/` (định nghĩa lần chạy, kiểm `min_interval_ms`, giữ trước/hoàn ngân sách, ghi bền NVS/tệp, tiến trình giám sát độc lập trên `linux`), kiểm `p95_latency_ms ≤ lease_ms / 2` trong `neuroedge build`, đổi sổ token trong `ne_token.c`, firmware `esp32s3` (TWDT + timer phần cứng, NVS write-ahead), bảng giới hạn firmware và self-test lúc boot — *host đạt (TSK-I2a-05): lease ở `actions/token.py`, `hal/motion_core.py` (lần chạy, giữ trước/hoàn, safe state), `hal/motion_pwm.py` (`linux`), kiểm `p95 ≤ lease_ms / 2` ở `neuroedge build`; `ne_token.c`, firmware, NVS, bảng giới hạn và self-test lúc boot chưa (TSK-W1-04)*
- [ ] Fixture/test (gồm test SIGSTOP treo tiến trình trên cả hai bo thật); cập nhật `docs/rfc/README.md` và `CHANGELOG.md` — *fixture `fixtures/agents/rover` + ca corpus + `tests/test_motion*.py` + `tests_linux/test_gpio_motion.py` (xanh ở CI run 37153005998); SIGSTOP trên bo thật chưa*

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30; Q-62, 2026-10-01)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã gộp** vào §3–§8; mục này giữ lại làm hồ sơ quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Cắt lời (`TODOS.md` #39).** Với `motion.*`: cắt lời, BLOCK hay mất liên lạc ⇒ **gửi ngay lệnh `safe_state`** và ngừng gia hạn lease; không có cờ nào cho phép chuyển động "chạy tiếp khi đã giao". Xung `digital.out` giữ luật hiện hành (`docs/spec/voice_fsm.md` §5.3). *Vì sao:* motor đang quay khi người dùng phản đối là nguy hiểm; lease là lớp dự phòng, lệnh dừng tức thì là lớp chính. Đóng #39 cho chuyển động.
2. **Lease.** `lease_ms` mặc định 200, trần 500 (hoàn toàn do bo mạch quyết định ở `board.v1`, gate không mang trường `lease_ms` nên không có đường nâng hay hạ). Gia hạn chỉ bằng một lời gọi mới qua gate, lượng giá lại đầy đủ. `budget.p95_latency_ms` của gate phải ≤ `lease_ms / 2`, không thì `neuroedge build` từ chối (`BoardCapabilityError`, NE3001): chỉ lúc build mới có cả gate lẫn `lease_ms` của bo mạch — gate không mang `lease_ms` nên `gate lint` không kiểm được. Lease tách khỏi `TTL_FACTOR` của token phán quyết. *Vì sao:* gia hạn phải kịp tới trước khi lease hết, và mỗi lần gia hạn là một lần gate được hỏi lại.
3. **`safe_state` ∈ {`stop`, `hold`}**, mặc định `stop`. `hold` chỉ khai được khi bo mạch khai kênh đó `holds_position = true` kèm `max_hold_ms`; hết `max_hold_ms` thì về `stop`. Không có `home` hay trạng thái nào tự di chuyển. *Vì sao:* khi mất giám sát, không cơ cấu nào được tự chuyển động.
4. **API tách đôi:** `motion.motor` (tốc độ, chiều, ramp) và `motion.servo` (góc đích, tốc độ tối đa), hai hình dạng năng lực riêng. *Vì sao:* giới hạn của hai loại khác nhau về bản chất; gộp làm một thì ràng buộc lỏng.
5. **Nơi giữ giới hạn.** Giới hạn phần cứng của kênh (khai ở `board.v1`) sinh thành bảng firmware, kiểm lúc boot (self-test hỏng ⇒ từ chối mọi lệnh `motion.*` trừ `safe_state`); ràng buộc của gate nằm trong `NETR`. Cả hai cùng cưỡng chế, giới hạn chặt hơn thắng. Kênh chuyển động cũng bắt buộc `enable_pin` như PWM (RFC-0010 §9). *Vì sao:* gate lỏng không vượt được phần cứng, phần cứng khai sai không vượt được gate.
6. **Bo mạch mang `motion`:** `linux-rpi5` (PWM phần cứng + driver có `enable_pin`) và `esp32s3-box-3` (LEDC qua chân dock, xác minh ở TSK-I3a-01; nếu dock không đủ chân thì `esp32s3-cores3` (M5Stack CoreS3, Q-61) mang qua cổng Grove/M5-Bus). Trong trường hợp CoreS3 mang, chỉ `sim-rpi5` soi `motion` (không `sim-default`, vì `sim-default` soi Box-3 — bất biến "sim không giàu hơn bo"). Test mất điện giữa lệnh và treo tiến trình chạy trên cả hai bo thật (TSK-W1-04).
7. **Lệnh về phía an toàn là ngoại lệ duy nhất** (review 2026-10-01, Q-62). Lệnh `safe_state` (`stop`/`hold`) và mọi lệnh HAL tự phát khi hết hạn, cắt lời, BLOCK, mất liên lạc hay `hal.close()` không bao giờ bị chặn: không qua phong bì, không cần token/ALLOW, không chờ `ramp_min_ms`, `min_interval_ms` hay chờ sau khởi động; đây là ngoại lệ duy nhất của luật cấm lệnh ra phần cứng không có ALLOW. *Vì sao:* an toàn tính mạng và cơ khí là tối thượng, không một cơ chế an toàn thứ cấp nào được chặn lệnh đưa cơ cấu về trạng thái an toàn.
8. **Định nghĩa lần chạy và gia hạn lease qua phong bì** (review 2026-10-01, Q-62). Lần chạy của `motion.*` là chuỗi lease liên tiếp trên cùng kênh; `min_interval_ms` chỉ áp lúc bắt đầu lần chạy; `max_continuous_ms` áp cho toàn bộ lần chạy; mỗi lease dùng cho đúng một lệnh. *Vì sao:* loại bỏ lỗi từ chối gia hạn khi `min_interval_ms` lớn hơn chu kỳ lease (~100 ms), đồng thời ngăn chặn lặp lệnh hoặc dồn lệnh trong cùng một lease.
9. **Tự tắt bắt buộc và giữ trước ngân sách phong bì** (review 2026-10-01, Q-62). Mọi lệnh bật đều có thời hạn hữu hạn; lúc bắt đầu lần chạy, phong bì giữ trước `max_continuous_ms` trong `max_on_ms_per_window`, khi lần chạy kết thúc thì hoàn phần dư; `authorize` thất bại sau khi giữ thì hoàn lại toàn bộ. *Vì sao:* đảm bảo cơ cấu luôn tự tắt nếu mất điều khiển và bảo toàn hạn mức thời gian hoạt động khi lệnh không thành công.
10. **Phong bì sống qua khởi động lại** (review 2026-10-01, Q-62). Tổng thời gian bật đã giữ được ghi bền trước khi bật (write-ahead vào NVS trên `esp32s3`, tệp trạng thái trên `linux`); với `motion.*` ghi một lần mỗi lần chạy (không ghi mỗi lần gia hạn để chống mòn flash); sau khởi động coi như vừa xảy ra ngay trước đó và chiếm ngân sách tới `window_s`. *Vì sao:* chống khởi động lại để xóa hạn mức phong bì mà vẫn bảo vệ độ bền của bộ nhớ flash.
11. **Phong bì bắt buộc cho kênh chuyển động** (review 2026-10-01, Q-62). Mọi kênh `motion.*` luôn là cơ cấu chấp hành, bắt buộc khai phong bì tại `[capabilities.motion.envelope.<kênh>]`, không được khai `signal_pins`; thiếu phong bì từ chối lúc nạp bo mạch. *Vì sao:* chuyển động vật lý luôn mang tải và rủi ro va chạm, bắt buộc phải có phong bì khống chế thời gian và chu kỳ hoạt động.
12. **Giám sát độc lập ngoài tiến trình** (review 2026-10-01, Q-62). Hẹn giờ lease và tự tắt không chỉ sống trong tiến trình runtime: `esp32s3` dùng TWDT cộng hẹn giờ phần cứng; `linux` dùng tiến trình giám sát độc lập giữ `enable_pin` qua nhịp tim; tiến trình runtime bị treo (SIGSTOP) thì cơ cấu vẫn về an toàn trong thời hạn cộng biên đã khai. *Vì sao:* tiến trình runtime có thể bị treo hoặc nghẽn, ngắt an toàn phải dựa vào phần cứng hoặc tiến trình độc lập.
13. **Không đổi bố cục `NETR` trong RFC này** (review 2026-10-01, Q-62). RFC này không thêm trường nào vào `NETR`; `layout_version = 2` do RFC-0009 (TSK-W1-02) mang; RFC này chỉ đổi sổ token `ne_token.c`/`TokenLedger` để quản lý lease. *Vì sao:* gom một lần nâng phiên bản `NETR`, tránh phân mảnh định dạng nhị phân và giữ walker C thuần túy.
14. **`safe_state` khi self-test hỏng, `enable_pin`, mốc của `min_interval_ms`** (review 2026-10-01, Q-62). Self-test giới hạn hỏng lúc boot ⇒ từ chối mọi lệnh `motion.*` **trừ** `safe_state`. `enable_pin` không gọi được từ agent, miễn phong bì riêng. `min_interval_ms` tính từ lúc lần chạy trước kết thúc. *Vì sao:* không trạng thái lỗi nào được chặn lệnh dừng; mốc kết thúc là mốc bảo thủ.
