# RFC-0011: Nguyên thủy `motion.*` — lease token, trạng thái an toàn theo cơ cấu

| | |
|:---|:---|
| **Mã RFC** | 0011 |
| **Tiêu đề** | `motion.*` (motor/servo), token thuê có hạn, trạng thái an toàn khai theo cơ cấu, phong bì mở rộng |
| **Hợp đồng bị ảnh hưởng** | `board.v1` · bố cục `NETR` *(chung một lần tăng phiên bản với RFC-0009)* · token `TokenLedger`/`ne_token.c` · **không** đụng `gate.v1` |
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

```toml
[capabilities.motion]
channels = [
  { name = "wheel_left", kind = "motor", speed_max = 0.6, ramp_min_ms = 200,
    safe_state = "stop", lease_ms = 200 },
  { name = "gripper", kind = "servo", target_min = 0, target_max = 90, unit = "deg",
    safe_state = "hold", lease_ms = 200 },
]
```

`safe_state` là bắt buộc theo Q-35: giá trị hợp lệ do RFC này liệt kê (`stop`, `hold`, `release`, `finish_pulse`…). **Không khai ⇒ `stop`** (fail-closed). Ngắt điện không phải lúc nào cũng an toàn (chốt cửa ở `voice_fsm.md` §5.3), nên đó là quyết định của từng cơ cấu.

### 3b. API và phong bì

`motion.drive(channel, target, speed, duration_ms, ramp_ms)` (tên mở, §9). Đi qua cùng đường HAL: `require_channel → envelope → authorize → record`. Phong bì của RFC-0007 mở rộng theo kênh: duty/tốc độ tối đa, **thời gian chạy liên tục tối đa**, và tần suất lệnh. Tích luỹ ở HAL, không ở gate (bất biến số 4). Giới hạn tham số (tốc độ, đích) là `arguments` của gate như RFC-0005, walker C đã đọc được.

### 3c. Token thuê có hạn (Q-37)

Một **lease** mang: kênh, biên độ tối đa (tốc độ, góc), thời hạn ngắn (`lease_ms`, cỡ 200 ms). Mỗi lệnh mới **qua gate** để gia hạn; không còn lệnh ⇒ lease hết hạn ⇒ cơ cấu về `safe_state`. Mất liên lạc vì vậy tự dẫn tới dừng, như `cmd_vel` timeout của ROS. Thay đổi: `VerdictToken`, `TokenLedger.issue/authorize` (host) và `ne_token.c`/`ne_token.h` (thiết bị) cùng đổi, lease không dùng lại được khi hết hạn hay sai kênh. Gate vẫn thuần: đếm hạn ở HAL/runtime.

### 3d. Cắt lời (barge-in) — quyết định `TODOS.md` #39

Đề xuất: với `motion.*`, **không thêm cờ vào `gate.v1`**. Cắt lời thôi gia hạn lease, nên chuyển động đã giao dừng trong tối đa `lease_ms` tự nhiên. Xung `digital.out` (chốt cửa) giữ quy tắc "chạy hết" của `voice_fsm.md` §5.3. Nếu về sau có cơ cấu `digital.out` cần "cắt cả khi đã chạy", #39 vẫn là mục hoãn. Cần kỹ thuật trưởng chốt (§9).

### 3e. `NETR` (`TODOS.md` #36)

Bản thân `motion.*` **không** cần nút mới: giới hạn tốc độ/đích dùng bảng tham số RFC-0005. Lần tăng `layout_version` là chung với [RFC-0009](0009-tieu-chi-so-numeric.md) và mang nhãn gate + chữ `on_block` (#36) để chỉ bump một lần. Bố cục byte ghim ở PR thứ hai.

### 3f. Kiểm thử trên bo mạch thật và an toàn cơ khí

Test crash-safe (SIGKILL/crash tiến trình, rút mạng, watchdog) **chạy trên phần cứng thật** (TSK-W1-04, TSK-I2a-05), không QEMU/Wokwi (#21). Robot di động bắt buộc nút dừng khẩn phần cứng cắt nguồn motor không qua phần mềm (Q-38).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có — mọi thứ mới là tuỳ chọn |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `motion` đúng hình dạng (cùng điểm siết chặt khoá `capabilities` chưa từng có nghĩa như RFC-0007 §4) |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không cho `board.v1`. **Có** cho `NETR` (`layout_version` 2, chung với RFC-0009 và #36) |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — gate không đổi |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không; sự kiện `motion.*` mới đặt cạnh `actuator_command`/`actuator_aborted` (`docs/spec/simulation_coverage.md` §3) |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | **Có** (§3e), và `ne_token.c` |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca `motion` mới. Token `digital.out` giữ ngữ nghĩa một-lần |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1`, ngữ nghĩa phân giải, năm nguyên tắc không đổi. Mọi lệnh chuyển động vẫn đi qua gate; lease chỉ **rút ngắn** thời gian một phán quyết còn hiệu lực.
- **Fail-closed sâu hơn:** không khai `safe_state` ⇒ dừng; lease hết hạn ⇒ `safe_state`; kênh lạ, biên độ vượt lease, lease đã hết ⇒ từ chối, không dùng lại.
- **Lease không thay thế crash-safe:** khi tiến trình bị SIGKILL, không phần mềm nào về được `safe_state`. Chỉ có phần cứng (kéo xuống, watchdog, giới hạn dòng, nút dừng khẩn) — nên test trên bo mạch thật là điều kiện chấp nhận, không phải tuỳ chọn.
- **NeuroEdge không phải chức năng an toàn được chứng nhận** (Q-38): RFC này không tuyên bố SIL/PL. Robot di động cần nút dừng khẩn phần cứng ngoài phạm vi phần mềm.
- **Rủi ro thay đổi token:** `ne_token.c` là mã thiết bị; đổi ngữ nghĩa một-lần sang lease có thể tạo đường phát lại. Bắt buộc fuzz và test đột biến như RFC-0003 §7.
- **Gate 10–20 lần/giây** cho robot di động (Q-34) cần lease dài hơn `p95_latency_ms` của gate; ràng buộc này phải được kiểm khi `build`.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Nhồi motor vào `digital.out` | Q-32: hợp đồng rõ hơn khi nguyên thủy riêng; `digital.out` không có kênh/ramp/lease |
| Token một lần dài hơn (TTL lớn) | Cơ cấu chạy đến hết TTL sau khi mất liên lạc; chính điều Q-37 muốn tránh |
| Cờ "vẫn cắt khi đã chạy" trong `gate.v1` (#39) | Đổi `gate.v1`, kéo theo ngữ nghĩa kế thừa; lease đạt cùng kết quả cho chuyển động mà không đổi gate |
| Gate đếm thời gian chạy tích luỹ | Phá tính thuần (bất biến số 4) |
| Tách `NETR` v2 riêng cho mỗi RFC | Nhiều lần bump; firmware phải theo từng bản (§3e) |

## 7. Bằng chứng kiểm chứng

- [ ] Profile `boards/` khai `motion` (bo mạch tham chiếu, RFC-0013); phản chứng: thiếu `safe_state`, `lease_ms` <= 0, `speed_max` ngoài (0, 1]
- [ ] Test host: lease hết hạn ⇒ `safe_state` và sự kiện có thể replay; lease sai kênh/hết hạn bị từ chối; cắt lời thôi gia hạn ⇒ dừng trong ≤ `lease_ms`; không khai `safe_state` ⇒ dừng
- [ ] Walker C/`ne_token.c` khớp `TokenLedger` host (mở rộng `python/tests/test_c_token.py`), fuzz ASan/UBSan
- [ ] **Test crash-safe trên bo mạch thật:** kill -9 tiến trình, rút WiFi, treo firmware ⇒ cơ cấu về `safe_state`; kết quả đo đính kèm PR
- [ ] `sim` mô hình lease bằng đồng hồ ảo, không giàu hơn bo mạch tham chiếu; `neuroedge verify` và `neuroedge gate lint` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json`; ghim bố cục `NETR` v2 cùng RFC-0009 và `TODOS.md` #36 (đóng #36; ghi quyết định #39)
- [ ] Sửa `docs/spec/voice_fsm.md` §5 (dừng do mất liên lạc là một lần dừng kiểu tắt máy) — TSK-W1-04
- [ ] `neuroedge-prd.md` FR-HAL-01; quyết định mới cấp `Q-N`; `neuroedge-roadmap.md` (TSK-W1-03, TSK-W1-04, TSK-I2a-05)
- [ ] `python/neuroedge/actions/token.py`, `python/neuroedge/hal/`, `ne_token.c`, walker C
- [ ] Fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Mục này **thay** mọi đoạn đề xuất trái với nó ở §3; khi mở PR RFC, gộp nội dung vào §3. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Cắt lời (`TODOS.md` #39).** Với `motion.*`: cắt lời, BLOCK hay mất liên lạc ⇒ **gửi ngay lệnh `safe_state`** và ngừng gia hạn lease; không có cờ nào cho phép chuyển động "chạy tiếp khi đã giao". Xung `digital.out` giữ luật hiện hành (`docs/spec/voice_fsm.md` §5.3). *Vì sao:* motor đang quay khi người dùng phản đối là nguy hiểm; lease là lớp dự phòng, lệnh dừng tức thì là lớp chính. Đóng #39 cho chuyển động.
2. **Lease.** `lease_ms` mặc định 200, trần 500 (trần khai ở bo mạch, gate chỉ được hạ). Gia hạn chỉ bằng một lời gọi mới qua gate, lượng giá lại đầy đủ. `budget.p95_latency_ms` của gate phải ≤ `lease_ms / 2`, không thì `gate lint` từ chối (`GateSchemaError`). Lease tách khỏi `TTL_FACTOR` của token phán quyết. *Vì sao:* gia hạn phải kịp tới trước khi lease hết, và mỗi lần gia hạn là một lần gate được hỏi lại.
3. **`safe_state` ∈ {`stop`, `hold`}**, mặc định `stop`. `hold` chỉ khai được khi bo mạch khai kênh đó `holds_position = true` kèm `max_hold_ms`; hết `max_hold_ms` thì về `stop`. Không có `home` hay trạng thái nào tự di chuyển. *Vì sao:* khi mất giám sát, không cơ cấu nào được tự chuyển động.
4. **API tách đôi:** `motion.motor` (tốc độ, chiều, ramp) và `motion.servo` (góc đích, tốc độ tối đa), hai hình dạng năng lực riêng. *Vì sao:* giới hạn của hai loại khác nhau về bản chất; gộp làm một thì ràng buộc lỏng.
5. **Nơi giữ giới hạn.** Giới hạn phần cứng của kênh (khai ở `board.v1`) sinh thành bảng firmware, kiểm lúc boot (self-test hỏng ⇒ từ chối mọi lệnh `motion.*`); ràng buộc của gate nằm trong `NETR`. Cả hai cùng cưỡng chế, giới hạn chặt hơn thắng. Kênh chuyển động cũng bắt buộc `enable_pin` như PWM (RFC-0010 §9). *Vì sao:* gate lỏng không vượt được phần cứng, phần cứng khai sai không vượt được gate.
6. **Bo mạch mang `motion`:** `linux-rpi5` (PWM phần cứng + driver có `enable_pin`) và `esp32s3-box-3` (LEDC qua chân dock, xác minh ở TSK-I3a-01; nếu dock không đủ chân thì bo camera của RFC-0013 mang); `sim-rpi5` và `sim-default` soi theo. Test mất điện giữa lệnh chạy trên cả hai bo thật (TSK-W1-04).
