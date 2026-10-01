# RFC-0010: PWM và kênh phản hồi trạng thái trong `digital.out`

| | |
|:---|:---|
| **Mã RFC** | 0010 |
| **Tiêu đề** | Thao tác `pwm` (tần số, độ rộng xung) và đọc lại trạng thái chân trong `digital.out` |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khối `pwm`, `enable_pin` và `feedback` trong `digital_out`)* · **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-05, FR-ACE-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (Q-57) và gộp vào §3–§8; §9 là bản ghi quyết định |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm đường tới chân vật lý và mở rộng phong bì của RFC-0007) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-W1-01.
> Nguồn: bản nháp robot FOFOCA (`roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md`), nay rút về RFC này. Quyết định
> nền: `neuroedge-prd.md` §15 Q-52 (gói PWM nằm trong MVP), Q-53 (bốn gói trên cả ba target bậc 1), Q-55, Q-57
> (§9). Phụ thuộc: phong bì, khoá `max_continuous_ms` và `actuator` ở
> [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5, mẫu ràng buộc tham số ở
> [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md).

## 1. Vấn đề

`digital.out` chỉ có ba thao tác: `pulse`, `on`, `off` (`python/neuroedge/hal/digital.py`; `SimHAL.digital_out` và `LinuxHAL.digital_out` từ chối thao tác khác). Quạt, đèn điều sáng, còi và servo RC cần **điều biến độ rộng xung**: một tần số và một tỉ lệ bật. Không có cách nào diễn đạt *"quạt chạy 40% công suất"* mà không giả bằng chuỗi `pulse` ngắn — chuỗi đó vừa sai tần số vừa tốn một token mỗi lần.

Ngoài ra chưa có cách đọc lại **trạng thái thực** của chân sau lệnh: `PinAssertion` (`python/neuroedge/hal/__init__.py`) ghi những gì HAL *nhận*, không ghi chân *đang ở đâu*. Với PWM, "đã lệnh 40%" khác "đang xuất 40%".

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/board.v1.json`, `digital_out`: chỉ có `pins` và `backend`; không có chỗ khai chân nào hỗ trợ PWM, dải tần số, độ phân giải, hay chân nào đọc lại được.
- Tính giới hạn trong code agent (dữ kiện tự tính) là cách vòng RFC-0005 đã bác: giới hạn phải ở gate và ở bo mạch, không ở agent.
- Phong bì RFC-0007 tính **thời gian bật**; với PWM, "bật" không còn nhị phân nên định nghĩa đó cần mở rộng.

## 3. Thay đổi đề xuất

### 3a. Bo mạch khai chân PWM và giới hạn phần cứng

```toml
[capabilities.digital_out.pwm]
pins             = ["fan"]                 # tập con của digital_out.pins; chỉ kênh PWM phần cứng
frequency_hz     = { min = 100, max = 25000 }
resolution_bits  = 10
max_duty         = 0.8                     # trần cứng của tải; 1.0 nếu không khai
enable_pin       = { fan = "fan_en" }      # kênh → line digital.out có điện trở kéo xuống

[capabilities.digital_out.feedback]
pins = ["fan"]                             # chỉ chân có readback phần cứng thật

[capabilities.digital_out.envelope.fan]    # khoá phong bì của RFC-0007 §9.5
window_s             = 3600
max_on_ms_per_window = 1800000
min_interval_ms      = 2000
max_continuous_ms    = 600000              # trần một lệnh PWM
```

- **Chỉ kênh PWM phần cứng.** Bo mạch không có kênh PWM phần cứng thì không khai `pwm`; không có PWM phần mềm (§3e, §9.1).
- **`enable_pin` bắt buộc** cho kênh PWM nối cơ cấu chấp hành (`actuator = true`, khoá của RFC-0007 §9.5): một chân trong `digital_out.pins`, không thuộc `pwm.pins`, có điện trở kéo xuống trên mạch. Thiếu ⇒ `BoardCapabilityError` lúc nạp. HAL chỉ bật `enable_pin` trong lúc có lệnh PWM đã qua gate; lệnh `digital.out` trực tiếp tới `enable_pin` bị từ chối (§9.2).
- **Phong bì bắt buộc** cho kênh nối cơ cấu chấp hành (RFC-0007 §9.5); thiếu ⇒ `BoardCapabilityError` lúc nạp.
- **`feedback`** chỉ khai chân đọc lại được từ phần cứng; bo mạch không có readback thì không khai (§9.4).

`board.v1` là **sự thật phần cứng** (tải chịu được gì); gate là **chính sách** (được phép gì). Gate chặt hơn được, không bao giờ nới trần bo mạch.

### 3b. Thao tác và API

`HardwareAbstractionLayer.digital_out` nhận thêm `operation = "pwm"` kèm `frequency_hz`, `duty` (0.0–1.0) và `duration_ms` — **cả ba bắt buộc**; `duration_ms` là số nguyên dương, không có giá trị mặc định hay nghĩa "chạy mãi" (§9.5). Phía agent (`hal/digital.py`): `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)`, `ms` không có giá trị mặc định; tool call thiếu tham số bắt buộc đã là `REJECTED` (`docs/spec/tool_calling.md`).

Thứ tự giữ như RFC-0007: `require_pin → kiểm giới hạn bo mạch → envelope → authorize → record`. Chân không khai `pwm` hoặc lệnh `pwm` thiếu `duration_ms` ⇒ `BoardCapabilityError` ba phần (cùng lớp với thao tác lạ hôm nay), **chưa tiêu token**; `duty`/`frequency_hz` vượt giới hạn bo mạch cũng bị từ chối ở bước này. Hết `duration_ms`, HAL đưa `duty = 0` và thả `enable_pin`; muốn chạy tiếp phải gọi lại qua gate.

Đọc lại trạng thái: `digital.out("fan").state()` trả `{value, source}` (§9.4). `value` là mức (`on`/`off`) hoặc `{duty, frequency_hz}` khi chân đang PWM; `source` là `measured` khi chân thuộc `feedback.pins` và giá trị đọc lại từ phần cứng, `commanded` (giá trị HAL đã ghi) với mọi chân khác. Đọc lại hỏng không bao giờ trả `commanded` thay — là lỗi đọc như RFC-0007 §9.4. Gate chỉ được dùng giá trị `measured` làm dữ kiện. `state()` không cần token (không di chuyển gì), ghi thành sự kiện kèm `source` để replay.

### 3c. Ràng buộc tham số ở gate (mẫu RFC-0005)

Không đổi `gate.v1`. `@action` khai `duty`, `frequency_hz` và `duration_ms` là tham số; gate dùng khối `arguments` sẵn có:

```yaml
arguments:
  duty:         { type: number,  minimum: 0.0, maximum: 0.6 }
  frequency_hz: { type: integer, minimum: 200, maximum: 5000 }
  duration_ms:  { type: integer, minimum: 1,   maximum: 10000 }
```

Vi phạm ⇒ BLOCK `argument_out_of_range` trước `evaluate`; giá trị mặc định của `@action` cũng được kiểm; gate con chỉ thu hẹp (RFC-0005 §3). `duration_ms` bị chặn hai lớp: `arguments` của gate và `max_continuous_ms` của bo mạch (§3d); cả hai cùng cưỡng chế, giới hạn chặt hơn thắng. Walker C đã đọc bảng giới hạn tham số nên **không cần nút mới**.

### 3d. Mở rộng phong bì

Phong bì của RFC-0007 tính thời gian *có xung ra*. Với PWM, **toàn bộ** thời gian có `duty > 0` được tính là "bật", **không nhân với duty** (§9.3); trần `max_duty` của bo mạch cưỡng chế thêm. Mỗi lệnh PWM xin trước đúng `duration_ms` của nó: `duration_ms > max_continuous_ms`, vượt phần `max_on_ms_per_window` còn lại, hoặc lệnh trong `min_interval_ms` ⇒ phong bì từ chối (`EnvelopeRefusedError`, NE1003, sự kiện `envelope_refused` — RFC-0007 §9.4), chưa tiêu token. Lệnh vượt bị từ chối, không bị cắt ngắn rồi cho chạy (RFC-0007 §5: không có chế độ "cảnh báo rồi cho qua"). Luật chờ `min_interval_ms` sau khởi động lại (RFC-0007 §9.6) áp cho kênh PWM như mọi chân có phong bì.

### 3e. Backend theo target

- **`linux`:** **chỉ PWM phần cứng của kernel** (`/sys/class/pwm`); không có PWM phần mềm (bit-bang qua gpiod). Bo mạch khai `pwm` mà kernel không có kênh tương ứng ⇒ từ chối lúc nạp, không lùi về PWM phần mềm. Test CI chạy trên cây sysfs giả (cùng cách `hal/sysfs.py`); bằng chứng phần cứng ở nightly Pi 5 (§9.1). `hal.close()` đưa `duty` về 0, tắt kênh và thả `enable_pin`.
- **`esp32s3`:** firmware dùng kênh PWM phần cứng của chip, cùng luật `enable_pin` và phong bì (§8).
- **`sim`:** mô hình soi bo mạch tham chiếu, không giàu hơn (RFC-0013).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có với ba profile `boards/`; `digital_out` không đóng nên `pwm`/`feedback` chưa từng bị từ chối |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `pwm`/`feedback` đúng hình dạng (kênh nối cơ cấu chấp hành phải kèm `enable_pin` và `envelope`). Cùng điểm siết chặt như RFC-0007 §4 nếu có ai đã dùng tên khoá này trước: không có trong kho |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không, với điều kiện hình dạng chốt trước khi có profile ngoài kho |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chưa có `pwm` trong chuỗi phán quyết của chúng |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không — dùng lại bảng giới hạn tham số của RFC-0005/RFC-0003 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca mới cho `duty`/`frequency_hz`/`duration_ms`, kể cả thiếu `duration_ms` ⇒ `REJECTED` |
| Mã lỗi (`neuroedge-prd.md` Phụ lục B) | `BoardCapabilityError` (NE3001) và `PerceptionUnavailableError` (NE5001) đã có. `EnvelopeRefusedError` (**NE1003**, RFC-0007 §9.4) **chưa có**: khi chấp thuận, Phụ lục B thêm dòng này nếu RFC-0007 chưa thêm. `argument_out_of_range` là lý do BLOCK đã có (FR-ACE-08), không phải lớp lỗi |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1` và năm nguyên tắc kế thừa giữ nguyên; ràng buộc `duty`/`frequency_hz`/`duration_ms` chạy tất định trước `evaluate`, không tốn ngân sách mô hình.
- **Lớp thứ hai độc lập:** trần cứng ở `board.v1` (`max_duty`, dải tần số, `max_continuous_ms`) chặn cả gate viết quá rộng. Một gate cho `duty` tới 1.0 trên tải chỉ chịu 0.8 vẫn bị từ chối ở HAL.
- **Không có PWM không giới hạn:** PWM giống `on()` — chân tiếp tục xuất xung sau khi action trả về, nhưng chỉ tới hết `duration_ms`. `duration_ms` luôn bắt buộc, bị chặn bởi gate và `max_continuous_ms`; phong bì bắt buộc cho kênh nối cơ cấu chấp hành; phong bì đếm toàn bộ thời gian `duty > 0`. Đây là điểm chính cần kỹ thuật trưởng duyệt.
- **Không PWM phần mềm:** xung phần mềm lệch thời gian và dừng giữa chừng khi tiến trình nghẽn (§9.1).
- **Tắt máy:** SIGTERM/thoát bình thường đưa chân về mức an toàn qua `hal.close()` (`duty = 0`, tắt kênh, thả `enable_pin`; `LinuxHAL.close` thả mọi line về không hoạt động). Crash/SIGKILL: kênh PWM của kernel **vẫn chạy sau khi tiến trình chết**; line gpiod của `enable_pin` được thả nên điện trở kéo xuống ngắt driver (§9.2, `roadmap/neuroedge-design-neurobrain.md` §2.3). Kênh không nối cơ cấu chấp hành không bắt buộc `enable_pin` nên có thể còn xuất xung sau crash; watchdog phần cứng vẫn là T0 crash-safe (RFC-0011 §5).
- **Kênh phản hồi chỉ đọc**, không thể dùng để tránh gate: `state()` không tạo hay gia hạn quyền điều khiển, và giá trị `commanded` không bao giờ được trình bày hay dùng như trạng thái đã đo (§9.4).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Nguyên thủy `pwm.out` riêng | PWM là cách điều khiển *một chân số*; tách ra nhân đôi bảng chân, `require_pin` và phong bì. Bản nháp FOFOCA cũng xếp PWM vào nhóm mở rộng trong năm nguyên thủy |
| PWM giả bằng chuỗi `pulse` | Sai tần số, mỗi xung tốn một token, phong bì tính sai |
| PWM phần mềm (bit-bang qua gpiod) trên `linux` | Lệch thời gian, dừng giữa chừng khi tiến trình nghẽn (§9.1) |
| Không có `enable_pin`, dựa vào `hal.close()` | Kênh PWM của kernel vẫn chạy sau crash/SIGKILL; chỉ line gpiod kéo xuống ngắt được driver (§9.2) |
| Phong bì tính `duty × thời gian` | Phụ thuộc mô hình năng lượng của tải; không bảo thủ (§9.3) |
| `state()` trả một giá trị không nhãn nguồn | Lệnh đã gửi bị đọc như trạng thái đã đo (§9.4) |
| PWM không `duration_ms`, chạy tới `max_continuous_ms` rồi dừng | Là PWM "chạy mãi" có trần; muốn chạy tiếp phải gọi lại qua gate (§9.5) |
| Nhét `duty`/`frequency_hz` vào `gate.v1` như trường riêng | `arguments` đã đủ (RFC-0005); thêm trường là nới lược đồ gate không cần thiết |
| Cho `motion.*` (RFC-0011) làm cả PWM | Motor/servo có kênh, đích, ramp, lease; quạt/đèn không cần. Hai hợp đồng khác nhau |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: profile `boards/` khai `pwm`, `enable_pin`, `feedback` và `envelope` (bo mạch tham chiếu theo RFC-0013)
- [ ] Phản chứng: chân `pwm` không thuộc `pins`, `min > max`, `max_duty` ngoài (0, 1], tần số ngoài dải; kênh nối cơ cấu chấp hành thiếu `enable_pin` hoặc thiếu `envelope`; `enable_pin` không thuộc `digital_out.pins` hoặc trùng một kênh `pwm`
- [ ] Test tham số: `duty` vượt `maximum` của gate ⇒ BLOCK `argument_out_of_range`, chân không đổi; `duty` vượt `max_duty` bo mạch ⇒ từ chối ở HAL, **token không bị tiêu**; giá trị mặc định cũng được kiểm
- [ ] Test `duration_ms` (§9.5): lệnh `pwm` thiếu `duration_ms` ⇒ HAL từ chối trước `authorize`, token không bị tiêu, chân không đổi; tool call thiếu `duration_ms` ⇒ `REJECTED`; vượt `arguments` ⇒ BLOCK `argument_out_of_range`; vượt `max_continuous_ms` ⇒ `EnvelopeRefusedError`, token không bị tiêu; hết `duration_ms` ⇒ `duty = 0` và `enable_pin` được thả
- [ ] Test phong bì (§9.3): một lệnh `duty = 0.1` trong 1000 ms trừ đủ 1000 ms khỏi `max_on_ms_per_window`
- [ ] Test `enable_pin` (§9.2): chỉ bật trong lúc có lệnh PWM đã qua gate; lệnh `digital.out` trực tiếp tới `enable_pin` bị từ chối; trên gpio-sim (`python/tests_linux/`), SIGKILL tiến trình giữa lệnh ⇒ line `enable_pin` về mức kéo xuống
- [ ] Test `state()` (§9.4): chân thuộc `feedback.pins` ⇒ `source: measured`; chân khác ⇒ `commanded`; đọc lại hỏng không trả `commanded`; giá trị `commanded` không thành dữ kiện cho gate; replay nạp lại cả `source`
- [ ] Test backend (§9.1): `linux` chỉ đi qua `/sys/class/pwm` (cây sysfs giả); bo mạch khai `pwm` mà kernel không có kênh ⇒ từ chối lúc nạp; sau `hal.close()` `duty = 0`, kênh tắt, `enable_pin` được thả; bằng chứng phần cứng ở nightly Pi 5
- [ ] Ca mới ở `fixtures/tool_calls/` cho tham số PWM (gồm thiếu `duration_ms`), khép kín hai chiều trong `expected_results.yaml`
- [ ] `sim` không khai PWM mà bo mạch tham chiếu thiếu; `neuroedge gate lint` và `neuroedge verify` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json` (`pwm`, `enable_pin`, `feedback`)
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`; Phụ lục B của PRD thêm dòng `EnvelopeRefusedError` (NE1003) nếu RFC-0007 chưa thêm
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-W1-01)
- [ ] Hiện thực `python/neuroedge/hal/` (`__init__.py`, `digital.py`, `sim.py`, `linux.py` với backend `/sys/class/pwm`); firmware `esp32s3`
- [ ] Thêm fixture/test (gồm `python/tests_linux/` trên gpio-sim và nightly Pi 5); cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã gộp vào §3–§8**; mục này giữ làm bản ghi quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Backend PWM trên `linux`:** **chỉ PWM phần cứng của kernel** (`/sys/class/pwm`). Không có PWM phần mềm; bo mạch không có kênh PWM phần cứng thì không khai `pwm`. Test CI chạy trên cây sysfs giả (cùng cách `hal/sysfs.py`), bằng chứng phần cứng ở nightly Pi 5. *Vì sao:* xung phần mềm lệch thời gian và dừng giữa chừng khi tiến trình nghẽn.
2. **Chân cho phép (thêm mới).** Kênh PWM nối cơ cấu chấp hành **bắt buộc** khai `enable_pin` — một line `digital.out` có điện trở kéo xuống trên mạch; HAL chỉ bật `enable_pin` trong lúc có lệnh PWM đã qua gate. *Vì sao:* kênh PWM của kernel **vẫn chạy sau khi tiến trình chết**; line gpiod thì được thả khi tiến trình thoát, nên kéo xuống ngắt driver kể cả khi crash (`neuroedge-design-neurobrain.md` §2.3).
3. **Phong bì đếm thời gian bật** là toàn bộ thời gian có duty > 0, không nhân với duty. *Vì sao:* bảo thủ, không phụ thuộc mô hình năng lượng của tải.
4. **`state()`** trả `{value, source}` với `source` là `measured` (đọc lại từ phần cứng) hoặc `commanded` (giá trị đã ghi); gate chỉ được dùng giá trị `measured` làm dữ kiện, và bo mạch không có readback thì không khai `feedback`. *Vì sao:* không bao giờ trình bày lệnh đã gửi như trạng thái đã đo.
5. **`duration_ms` luôn bắt buộc**, bị chặn bởi `arguments` của gate và `max_continuous_ms` của bo mạch (RFC-0007). *Vì sao:* không có PWM "chạy mãi"; muốn chạy tiếp phải gọi lại qua gate.
