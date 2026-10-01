# RFC-0010: PWM và kênh phản hồi trạng thái trong `digital.out`

| | |
|:---|:---|
| **Mã RFC** | 0010 |
| **Tiêu đề** | Thao tác `pwm` (tần số, độ rộng xung) và đọc lại trạng thái chân trong `digital.out` |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khối `pwm`, `enable_pin` và `feedback` trong `digital_out`)* · **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-05, FR-ACE-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | 🟡 Đang thảo luận — đã sửa theo review 2026-10-01 (§9, Q-62); chờ chữ ký kỹ thuật trưởng |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm đường tới chân vật lý và mở rộng phong bì của RFC-0007) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-W1-01.
> Nguồn: bản nháp robot FOFOCA (`roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md`), nay rút về RFC này. Quyết định
> nền: `neuroedge-prd.md` §15 Q-52 (gói PWM nằm trong MVP), Q-53 (bốn gói trên cả ba target bậc 1), Q-55, Q-57
> (§9). Phụ thuộc: phong bì và khoá `max_continuous_ms` ở [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md) §9.5
> (cờ cơ cấu chấp hành và vị trí phong bì theo §9 mục 5 của RFC đó), mẫu ràng buộc tham số ở [RFC-0005](0005-rang-buoc-tham-so-trong-gate.md).

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
max_duty         = 0.8                     # trần cứng của tải; bắt buộc, không có mặc định
enable_pin       = { fan = { pin = "fan_en", enable_active = "high", pull = "down" } }

[capabilities.digital_out.feedback]
pins = ["fan"]                             # chỉ chân có readback phần cứng thật

[capabilities.digital_out.envelope.fan]    # khoá phong bì (RFC-0007 §9.5)
window_s             = 3600
max_on_ms_per_window = 1800000
min_interval_ms      = 2000
max_continuous_ms    = 600000              # trần một lệnh PWM
```

- **Chỉ kênh PWM phần cứng.** Bo mạch không có kênh PWM phần cứng thì không khai `pwm`; không có PWM phần mềm (§3e, §9.1).
- **Lượng tử hoá `duty`:** HAL lượng tử hoá `duty` theo `resolution_bits` và luôn làm tròn về 0 để không bao giờ vượt `max_duty` phần cứng (§9.15).
- **`enable_pin` bắt buộc cho mỗi kênh PWM:** mỗi kênh PWM bắt buộc có một `enable_pin` riêng, không dùng chung kênh khác (dùng chung ⇒ `BoardCapabilityError` lúc nạp, §9.15). Khai báo bắt buộc đủ hai trường `enable_active = "high"` và `pull = "down"`; bản này chỉ nhận đúng hai giá trị đó (mức tích cực thấp hoặc kéo lên ⇒ từ chối lúc nạp, §9.14). HAL chỉ bật `enable_pin` trong lúc có lệnh PWM đã qua gate; lệnh `digital.out` trực tiếp tới `enable_pin` bị từ chối (§9.2). `enable_pin` do HAL tự quản: agent không gọi được (lệnh `digital.out` trực tiếp tới nó bị từ chối), miễn phong bì riêng của RFC-0007 và không khai trong `signal_pins`.
- **Mọi chân PWM luôn là cơ cấu chấp hành:** theo RFC-0007 §9 mục 5, mọi chân `digital_out` mặc định là cơ cấu chấp hành và bắt buộc có phong bì tại `[capabilities.digital_out.envelope.<tên>]`; chỉ chân khai trong `signal_pins` mới được miễn. Mọi chân `pwm.pins` luôn là cơ cấu chấp hành, cấm khai `signal_pins`. Thiếu phong bì ⇒ `BoardCapabilityError` lúc nạp (§9.10).
- **`feedback`** chỉ khai chân đọc lại được từ phần cứng; bo mạch không có readback thì không khai (§9.4).

`board.v1` là **sự thật phần cứng** (tải chịu được gì); gate là **chính sách** (được phép gì). Gate chặt hơn được, không bao giờ nới trần bo mạch.

### 3b. Thao tác và API

- **Thao tác trên chân PWM:** Trên chân thuộc `pwm.pins`, các thao tác `on` và `pulse` bị từ chối (`BoardCapabilityError` NE3001, chưa tiêu token) để tránh xuất xung 100% duty vượt trần `max_duty` phần cứng; chân PWM **chỉ nhận thao tác `pwm` và `off`** (§9.13).
- **Thao tác `pwm`:** `HardwareAbstractionLayer.digital_out` nhận thêm `operation = "pwm"` kèm `frequency_hz`, `duty` (0.0–1.0) và `duration_ms` — **cả ba bắt buộc**; `duration_ms` là số nguyên dương, không có giá trị mặc định hay nghĩa "chạy mãi" (§9.5). Phía agent (`hal/digital.py`): `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)`, `ms` không có giá trị mặc định; tool call thiếu tham số bắt buộc đã là `REJECTED` (`docs/spec/tool_calling.md`).
- **Thứ tự xử lý và hoàn ngân sách:** Thứ tự xử lý: `require_pin → kiểm giới hạn bo mạch → envelope reserve → authorize → record`. Chân không khai `pwm` hoặc lệnh `pwm` thiếu `duration_ms`, `duty`/`frequency_hz` ngoài giới hạn ⇒ `BoardCapabilityError`, chưa tiêu token. Phong bì giữ trước đúng thời hạn `min(duration_ms, max_continuous_ms)` trong `max_on_ms_per_window`. Nếu `authorize` thất bại sau khi đã giữ ngân sách, toàn bộ phần đã giữ được hoàn trả ngay: không tiêu token, không có xung ra phần cứng (§9.8). Tắt sớm (bởi `off` hoặc cắt lời) thì hoàn phần chưa dùng.
- **Lệnh về phía an toàn không bao giờ bị chặn:** Lệnh `digital.out` `off`, PWM đưa `duty = 0`/thả `enable_pin`, và mọi lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, khi cắt lời, BLOCK, mất liên lạc, `hal.close()` không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay chờ sau khởi động (§9.6). Đây là ngoại lệ duy nhất của luật "không lệnh nào ra phần cứng mà không có ALLOW", chỉ áp cho lệnh đưa cơ cấu về trạng thái an toàn. Lệnh vẫn ghi vết ghi kèm nguyên nhân. `min_interval_ms` chỉ áp cho lệnh bật (§9.7).
- **Không chỉ dựa vào hẹn giờ trong tiến trình:** Hẹn giờ tự tắt tại `min(duration_ms, max_continuous_ms)` không được chỉ sống trong tiến trình runtime có thể treo (§9.11). Trên `esp32s3`: task watchdog (TWDT) cộng hẹn giờ phần cứng; watchdog reset thì khởi động lại với `enable_pin` ở mức kéo xuống. Trên `linux`: `enable_pin` và line của chân cơ cấu do một tiến trình giám sát riêng giữ; runtime gửi nhịp tim; mất nhịp quá thời hạn ⇒ giám sát thả `enable_pin` và tắt chân.
- **Đọc lại trạng thái và dữ kiện số cho gate:** `digital.out("fan").state()` trả về trạng thái của chân. Với chân PWM, mỗi đại lượng (`duty`, `frequency_hz`) là một dữ kiện numeric riêng kèm `source` (§9.12). `source` là `measured` khi chân thuộc `feedback.pins` và đọc lại từ phần cứng, `commanded` (giá trị HAL đã ghi) với mọi chân khác. Đọc lại hỏng không bao giờ trả `commanded` thay — ném lỗi `PerceptionUnavailableError` (NE5001). Gate chỉ được dùng giá trị `measured` làm dữ kiện; giá trị `commanded` tới gate bị coi là chưa có số đo ⇒ BLOCK `criterion_unavailable`. Khi agent nối một tiêu chí `numeric` với readback `feedback`, `neuroedge build` kiểm `unit` trùng nhau và `[min, max]` của kênh nằm trong `range` của tiêu chí; lệch ⇒ `BoardCapabilityError` (NE3001). Tiêu chí `numeric` KHÔNG được nằm trong `on_block.confirms` của RFC-0006: `gate lint` từ chối (`GateSchemaError`, NE2002). `state()` không cần token (không di chuyển gì), ghi thành sự kiện kèm `source` để replay. Đơn vị và thang của readback cố định: `duty` có `unit = ratio`, thang `[0, max_duty]`; `frequency_hz` có `unit = Hz`, thang `[frequency_hz.min, frequency_hz.max]` của bo mạch; `build` kiểm theo RFC-0009 §3f với các giá trị này.

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

Phong bì của RFC-0007 tính thời gian *có xung ra*. Với PWM, **toàn bộ** thời gian có `duty > 0` được tính là "bật", **không nhân với duty** (§9.3); trần `max_duty` của bo mạch cưỡng chế thêm.

- **Giữ trước và hoàn trả:** Mỗi lệnh PWM xin giữ trước đúng `min(duration_ms, max_continuous_ms)` trong `max_on_ms_per_window`. Lệnh có `duration_ms > max_continuous_ms`, vượt phần ngân sách còn lại của cửa sổ, hoặc gọi khi chưa đủ `min_interval_ms` tính từ lúc lần bật trước kết thúc ⇒ phong bì từ chối (`EnvelopeRefusedError`, NE1003, sự kiện `envelope_refused` — RFC-0007 §9.4), chưa tiêu token. Lệnh vượt bị từ chối dứt khoát, không bị cắt ngắn rồi cho chạy (không có chế độ "cảnh báo rồi cho qua"). Tắt sớm thì hoàn phần chưa dùng. `authorize` thất bại sau khi đã giữ thì hoàn toàn bộ phần đã giữ: không tiêu token, không có xung (§9.8).
- **Lệnh an toàn không qua phong bì:** `min_interval_ms` chỉ áp cho lệnh bật (§9.7). Lệnh `off` hoặc đưa `duty = 0`/thả `enable_pin` không qua phong bì, không bị chặn bởi `min_interval_ms`, không cần token hay ALLOW (§9.6).
- **Phong bì sống qua khởi động lại:** Tổng thời gian bật đã giữ trong cửa sổ được ghi bền trước khi bật (write-ahead): NVS trên `esp32s3`, tệp trạng thái trên `linux`; `sim` mô phỏng cùng luật (§9.9). Sau khởi động không có đồng hồ tin cậy xuyên khởi động, nên coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động. Chúng chiếm ngân sách tới `window_s` sau khởi động. Không đọc được, hỏng hoặc thiếu bản ghi ⇒ coi cả cửa sổ đã dùng hết (fail-closed). Vẫn giữ luật chờ `min_interval_ms` trước lần bật đầu sau khởi động.
- **Khai báo bắt buộc:** Khai ở `[capabilities.digital_out.envelope.<tên>]`. Mọi chân PWM luôn là cơ cấu chấp hành, bắt buộc có phong bì; thiếu phong bì ⇒ `BoardCapabilityError` lúc nạp (§9.10).

### 3e. Backend theo target

- **`linux`:** **chỉ PWM phần cứng của kernel** (`/sys/class/pwm`); không có PWM phần mềm (bit-bang qua gpiod). Bo mạch khai `pwm` mà kernel không có kênh tương ứng ⇒ từ chối lúc nạp (`BoardCapabilityError`), không lùi về PWM phần mềm. Test CI chạy trên cây sysfs giả (cùng cách `hal/sysfs.py`); bằng chứng phần cứng ở nightly Pi 5 (§9.1). Hẹn giờ tự tắt và `enable_pin` được bảo vệ bởi tiến trình giám sát độc lập chống tiến trình runtime bị treo (§9.11). Phong bì ghi bền write-ahead vào tệp trạng thái (§9.9). `hal.close()` đưa `duty` về 0, tắt kênh và thả `enable_pin`.
- **`esp32s3`:** firmware dùng kênh PWM phần cứng của chip, cùng luật `enable_pin` và phong bì (§8). Task watchdog (TWDT) cộng hẹn giờ phần cứng đảm bảo boot với `enable_pin` ở mức kéo xuống nếu runtime bị treo (§9.11). Phong bì ghi bền write-ahead vào NVS (§9.9).
- **`sim`:** mô hình soi bo mạch tham chiếu, không giàu hơn (RFC-0013); mô phỏng cùng luật ghi bền và phong bì.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có. Theo RFC-0007 §9 mục 5, mọi chân `digital_out` mặc định là cơ cấu chấp hành và bắt buộc có phong bì. Ba profile bậc 1 trong `boards/` phải thêm phong bì trong PR hiện thực, với giá trị đủ rộng để ba vết ghi chuẩn mực vẫn replay y nguyên (ví dụ `door_lock` nhận xung 30.000 ms ⇒ `max_continuous_ms` ≥ 30000). Chưa có profile bên ngoài kho |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `pwm`/`feedback` đúng hình dạng (mọi kênh PWM là cơ cấu chấp hành, bắt buộc kèm `enable_pin` riêng với `enable_active = "high"` và `pull = "down"`, và khối `envelope`). Cùng điểm siết chặt như RFC-0007 §4 nếu có ai đã dùng tên khoá này trước: không có trong kho |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không, với điều kiện hình dạng chốt trước khi có profile ngoài kho |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chưa có `pwm` trong chuỗi phán quyết của chúng; phong bì bổ sung ở ba profile bậc 1 đủ rộng để replay y nguyên |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không — dùng lại bảng giới hạn tham số của RFC-0005/RFC-0003 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca mới cho `duty`/`frequency_hz`/`duration_ms`, kể cả thiếu `duration_ms` ⇒ `REJECTED` |
| Mã lỗi (`neuroedge-prd.md` Phụ lục B) | `BoardCapabilityError` (NE3001) và `PerceptionUnavailableError` (NE5001) đã có; NE3001 áp thêm cho `on`/`pulse` trên chân PWM, sai cấu hình `enable_pin`, hoặc lệch `unit`/dải đo feedback. Thêm `GateSchemaError` (NE2002) khi tiêu chí `numeric` nằm trong `on_block.confirms`. `EnvelopeRefusedError` (**NE1003**, RFC-0007 §9.4) chưa có: khi chấp thuận, Phụ lục B thêm dòng này nếu RFC-0007 chưa thêm. `argument_out_of_range` là lý do BLOCK đã có (FR-ACE-08), không phải lớp lỗi |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1` và năm nguyên tắc kế thừa giữ nguyên; ràng buộc `duty`/`frequency_hz`/`duration_ms` chạy tất định trước `evaluate`, không tốn ngân sách mô hình.
- **Lớp thứ hai độc lập:** trần cứng ở `board.v1` (`max_duty`, dải tần số, `max_continuous_ms`) chặn cả gate viết quá rộng. Thao tác `on()` và `pulse()` bị từ chối trên chân PWM để ngăn xuất 100% duty vượt trần `max_duty` của bo mạch (§9.13). Lượng tử hoá `duty` theo `resolution_bits` luôn làm tròn về 0 để không vượt `max_duty` phần cứng (§9.15).
- **Không có PWM không giới hạn:** mọi lệnh bật trên kênh PWM đều có thời hạn hữu hạn: `duration_ms` luôn bắt buộc, bị chặn bởi gate và `max_continuous_ms` (§9.5). Mọi chân PWM luôn là cơ cấu chấp hành, không khai `signal_pins` được, bắt buộc có phong bì (§9.10); phong bì đếm toàn bộ thời gian `duty > 0` (§9.3). Giữ trước ngân sách tại `min(duration_ms, max_continuous_ms)`; tắt sớm hoàn lại phần chưa dùng; `authorize` thất bại sau khi giữ thì hoàn trả toàn bộ ngân sách (không tiêu token, không phát xung, §9.8).
- **Lệnh về phía an toàn không bao giờ bị chặn:** lệnh `digital.out` `off`, PWM đưa `duty = 0`/thả `enable_pin`, và mọi lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, khi cắt lời, BLOCK, mất liên lạc, `hal.close()` không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay chờ sau khởi động (§9.6). Đây là ngoại lệ duy nhất của luật bắt buộc ALLOW, chỉ áp cho việc đưa cơ cấu về trạng thái an toàn.
- **`min_interval_ms` chỉ áp cho lệnh bật:** cơ cấu được phép ngắt về an toàn ngay lập tức mà không bị trì hoãn bởi giới hạn tần suất (§9.7).
- **Phong bì sống qua khởi động lại:** ghi bền write-ahead (NVS trên `esp32s3`, tệp trạng thái trên `linux`). Sau khởi động coi các lần bật đã ghi như xảy ra ngay trước khởi động, chiếm ngân sách tới `window_s`; hỏng hoặc thiếu bản ghi coi như hết cửa sổ (fail-closed); vẫn chờ `min_interval_ms` trước lần bật đầu sau khởi động (§9.9).
- **Không chỉ dựa vào hẹn giờ trong tiến trình:** tiến trình runtime có thể bị treo (SIGSTOP) giữ nguyên trạng thái xuất xung của kernel driver. Trên `linux`, tiến trình giám sát độc lập giữ `enable_pin` và ngắt khi mất nhịp tim; trên `esp32s3`, task watchdog (TWDT) cộng timer phần cứng reset về mức kéo xuống (§9.11). Cơ cấu chấp hành luôn về trạng thái an toàn trong thời hạn cộng biên đã khai.
- **Cấu hình phần cứng bảo đảm:** mọi chân PWM luôn là cơ cấu chấp hành, mỗi kênh bắt buộc có một `enable_pin` riêng biệt không dùng chung (§9.15), khai báo bắt buộc `enable_active = "high"` và `pull = "down"` (§9.14). Crash/SIGKILL: kênh PWM của kernel vẫn chạy sau khi tiến trình chết, nhưng tiến trình giám sát đang giữ line của `enable_pin` thả nó khi mất nhịp tim; nếu chính giám sát chết, line gpiod được thả và điện trở kéo xuống ngắt driver (§9.2, `roadmap/neuroedge-design-neurobrain.md` §2.3).
- **Không PWM phần mềm:** xung phần mềm lệch thời gian và dừng giữa chừng khi tiến trình nghẽn (§9.1).
- **Kênh phản hồi và ràng buộc dữ kiện số:** `state()` tách mỗi đại lượng (`duty`, `frequency_hz`) thành một dữ kiện numeric riêng kèm `source` (§9.12). Chỉ giá trị `measured` (từ chân thuộc `feedback.pins`) mới được gate dùng làm dữ kiện hợp lệ; `commanded` tới gate bị coi là chưa có số đo ⇒ BLOCK `criterion_unavailable`. `build` kiểm tra khớp `unit` và `[min, max]` nằm trong `range` tiêu chí (`BoardCapabilityError` NE3001). Cấm đưa tiêu chí numeric vào `on_block.confirms` (`GateSchemaError` NE2002) vì người không thể xác nhận thay cho số đo cảm biến.

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

- [ ] Ví dụ hợp lệ: profile `boards/` khai `pwm`, `enable_pin` (kèm `enable_active = "high"` và `pull = "down"`), `feedback` và `envelope` (bo mạch tham chiếu theo RFC-0013)
- [ ] Phản chứng cấu hình bo mạch: chân `pwm` không thuộc `pins`, `min > max`, thiếu `max_duty`, `max_duty` ngoài (0, 1], tần số ngoài dải; kênh `pwm` thiếu `enable_pin`, `enable_pin` sai trường hoặc có `enable_active != "high"` hoặc `pull != "down"` (§9.14); hai kênh PWM dùng chung một `enable_pin` (§9.15); chân PWM khai trong `signal_pins` hoặc thiếu `envelope` (§9.10); `enable_pin` không thuộc `digital_out.pins` hoặc trùng kênh `pwm` ⇒ `BoardCapabilityError` lúc nạp
- [ ] Phản chứng thao tác và ràng buộc: gọi `on()` hoặc `pulse()` trên chân thuộc `pwm.pins` ⇒ từ chối trước `authorize` (`BoardCapabilityError`), token không bị tiêu (§9.13); tiêu chí `numeric` nối readback `feedback` bị lệch `unit` hoặc ngoài `[min, max]` ⇒ `BoardCapabilityError` (NE3001) lúc build (§9.12); tiêu chí `numeric` nằm trong `on_block.confirms` ⇒ `GateSchemaError` (NE2002) lúc `gate lint` (§9.12)
- [ ] Test tham số: `duty` vượt `maximum` của gate ⇒ BLOCK `argument_out_of_range`, chân không đổi; `duty` vượt `max_duty` bo mạch ⇒ từ chối ở HAL, **token không bị tiêu**; lượng tử hoá `duty` theo `resolution_bits` làm tròn về 0 không bao giờ vượt quá `max_duty` (§9.15); giá trị mặc định cũng được kiểm
- [ ] Test `duration_ms` và tự tắt (§9.5): lệnh `pwm` thiếu `duration_ms` ⇒ HAL từ chối trước `authorize`, token không bị tiêu; tool call thiếu `duration_ms` ⇒ `REJECTED`; vượt `arguments` ⇒ BLOCK `argument_out_of_range`; vượt `max_continuous_ms` ⇒ `EnvelopeRefusedError`, token không bị tiêu; hết `min(duration_ms, max_continuous_ms)` ⇒ `duty = 0` và `enable_pin` được thả; tắt sớm hoàn phần chưa dùng; `authorize` thất bại sau khi giữ thì hoàn lại toàn bộ ngân sách (§9.8)
- [ ] Test lệnh an toàn: lệnh `off` và đưa `duty = 0`/thả `enable_pin` (kể cả khi hết thời hạn hoặc `hal.close()`) không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay sau khởi động, vẫn ghi vết ghi kèm nguyên nhân (§9.6); `min_interval_ms` chỉ áp cho lệnh bật, gọi `off` ngay sau lệnh `pwm` không bị chặn (§9.7)
- [ ] Test phong bì và khởi động lại (§9.3): một lệnh `duty = 0.1` trong 1000 ms trừ đủ 1000 ms khỏi `max_on_ms_per_window`; ghi bền write-ahead vào NVS (`esp32s3`) hoặc tệp trạng thái (`linux`) trước khi bật; sau khởi động coi các lần bật đã ghi như xảy ra ngay trước khởi động và chiếm ngân sách tới `window_s`; lần bật đầu tiên trong `min_interval_ms` sau khởi động bị từ chối; bản ghi hỏng/thiếu ⇒ coi hết cả cửa sổ (§9.9)
- [ ] Test `enable_pin` và chống treo tiến trình (§9.2): `enable_pin` chỉ bật trong lúc có lệnh PWM đã qua gate; lệnh `digital.out` trực tiếp tới `enable_pin` bị từ chối; trên gpio-sim (`python/tests_linux/`), SIGKILL tiến trình giữa lệnh ⇒ line `enable_pin` về mức kéo xuống; test chấp nhận runtime nhận SIGSTOP trong lúc bật ⇒ tiến trình giám sát độc lập (`linux`) hoặc TWDT / timer phần cứng (`esp32s3`) thả `enable_pin` và tắt kênh trong thời hạn cộng biên đã khai (§9.11)
- [ ] Test `state()` và numeric feedback (§9.4): `state()` tách `duty` và `frequency_hz` thành các dữ kiện numeric riêng kèm `source`; chân thuộc `feedback.pins` ⇒ `source: measured`; chân khác ⇒ `commanded`; đọc lại hỏng ném `PerceptionUnavailableError` và không trả `commanded`; giá trị `commanded` tới gate ⇒ BLOCK `criterion_unavailable`; chỉ `measured` được gate nhận làm dữ kiện; replay nạp lại cả `source` (§9.12)
- [ ] Test backend (§9.1): `linux` chỉ đi qua `/sys/class/pwm` (cây sysfs giả); bo mạch khai `pwm` mà kernel không có kênh ⇒ từ chối lúc nạp; sau `hal.close()` `duty = 0`, kênh tắt, `enable_pin` được thả; bằng chứng phần cứng ở nightly Pi 5
- [ ] Ca mới ở `fixtures/tool_calls/` cho tham số PWM (gồm thiếu `duration_ms`), khép kín hai chiều trong `expected_results.yaml`
- [ ] `sim` không khai PWM mà bo mạch tham chiếu thiếu; `neuroedge gate lint` và `neuroedge verify` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json` (`pwm`, `enable_pin` bắt buộc `enable_active = "high"` và `pull = "down"`, cấm dùng chung `enable_pin`, `feedback`, `signal_pins` và quy tắc phong bì bắt buộc cho mọi chân cơ cấu chấp hành theo RFC-0007 §9 mục 5)
- [ ] Ghi nhận ngoại lệ của lệnh về phía an toàn (không cần ALLOW, không qua phong bì, không chờ `min_interval_ms`) vào `docs/spec/threat_model.md` §1
- [ ] Bổ sung khối phong bì cho ba profile bậc 1 trong `boards/` trong PR hiện thực với giá trị đủ rộng để ba vết ghi chuẩn mực replay y nguyên
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`; Phụ lục B của PRD thêm dòng `EnvelopeRefusedError` (NE1003) nếu RFC-0007 chưa thêm
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-W1-01)
- [ ] Hiện thực `python/neuroedge/hal/` (`__init__.py`, `digital.py`, `sim.py`, `linux.py` với backend `/sys/class/pwm`): từ chối `on`/`pulse` trên chân PWM, lượng tử hoá `duty` làm tròn về 0, hoàn ngân sách phong bì khi tắt sớm hoặc authorize thất bại, ghi bền phong bì write-ahead, và tiến trình giám sát độc lập ngoài runtime trên `linux`
- [ ] Hiện thực firmware `esp32s3`: PWM phần cứng, TWDT cộng timer phần cứng boot kéo xuống `enable_pin`, ghi bền phong bì write-ahead vào NVS
- [ ] Hiện thực tách `state()` trên chân PWM thành các dữ kiện numeric riêng cho `duty` và `frequency_hz` kèm `source`; cập nhật `neuroedge build` kiểm tra khớp `unit`/dải đo (NE3001) và `gate lint` từ chối tiêu chí numeric trong `on_block.confirms` (NE2002)
- [ ] Thêm fixture/test (gồm `python/tests_linux/` trên gpio-sim, test SIGSTOP tiến trình treo, và nightly Pi 5); cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30; Q-62, 2026-10-01)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã gộp vào §3–§8**; mục này giữ làm bản ghi quyết định (Q-57). Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Backend PWM trên `linux`:** **chỉ PWM phần cứng của kernel** (`/sys/class/pwm`). Không có PWM phần mềm; bo mạch không có kênh PWM phần cứng thì không khai `pwm`. Test CI chạy trên cây sysfs giả (cùng cách `hal/sysfs.py`), bằng chứng phần cứng ở nightly Pi 5. *Vì sao:* xung phần mềm lệch thời gian và dừng giữa chừng khi tiến trình nghẽn.
2. **Chân cho phép (thêm mới).** Kênh PWM nối cơ cấu chấp hành **bắt buộc** khai `enable_pin` — một line `digital.out` có điện trở kéo xuống trên mạch; HAL chỉ bật `enable_pin` trong lúc có lệnh PWM đã qua gate. *Vì sao:* kênh PWM của kernel **vẫn chạy sau khi tiến trình chết**; line gpiod thì được thả khi tiến trình thoát, nên kéo xuống ngắt driver kể cả khi crash (`neuroedge-design-neurobrain.md` §2.3).
3. **Phong bì đếm thời gian bật** là toàn bộ thời gian có duty > 0, không nhân với duty. *Vì sao:* bảo thủ, không phụ thuộc mô hình năng lượng của tải.
4. **`state()`** trả `{value, source}` với `source` là `measured` (đọc lại từ phần cứng) hoặc `commanded` (giá trị đã ghi); gate chỉ được dùng giá trị `measured` làm dữ kiện, và bo mạch không có readback thì không khai `feedback`. *Vì sao:* không bao giờ trình bày lệnh đã gửi như trạng thái đã đo.
5. **`duration_ms` luôn bắt buộc**, bị chặn bởi `arguments` của gate và `max_continuous_ms` của bo mạch (RFC-0007). *Vì sao:* không có PWM "chạy mãi"; muốn chạy tiếp phải gọi lại qua gate.
6. **Lệnh về phía an toàn không bao giờ bị chặn** (review 2026-10-01, Q-62). Các lệnh đưa cơ cấu về trạng thái an toàn (`digital.out` `off`, PWM đưa `duty = 0`/thả `enable_pin`, lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, cắt lời, BLOCK, mất liên lạc, `hal.close()`) không bao giờ bị chặn; không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay sau khởi động; vẫn ghi vết ghi kèm nguyên nhân. *Vì sao:* đảm bảo cơ cấu luôn được đưa về an toàn tức thời trong mọi tình huống nguy cấp; là ngoại lệ duy nhất của luật bắt buộc ALLOW.
7. **`min_interval_ms` chỉ áp cho lệnh bật** (review 2026-10-01, Q-62). Giới hạn khoảng cách tối thiểu giữa hai lệnh chỉ áp dụng cho lệnh chuyển cơ cấu từ trạng thái an toàn sang hoạt động; không áp dụng cho lệnh tắt hoặc đưa về an toàn. *Vì sao:* lệnh ngắt cơ cấu không bao giờ được phép bị trì hoãn bởi giới hạn tần suất.
8. **Tự tắt bắt buộc và hoàn ngân sách phong bì** (review 2026-10-01, Q-62). Mọi lệnh bật trên chân có phong bì đều có thời hạn hữu hạn `min(duration_ms, max_continuous_ms)`. Phong bì giữ trước đúng thời hạn đó trong `max_on_ms_per_window`; tắt sớm hoàn phần chưa dùng; `authorize` thất bại sau khi đã giữ thì hoàn toàn bộ phần đã giữ (không tiêu token, không có xung). *Vì sao:* triệt tiêu rò rỉ ngân sách thời gian bật và ngăn xung ra phần cứng khi lệnh bị gate từ chối.
9. **Phong bì sống qua khởi động lại** (review 2026-10-01, Q-62). Tổng thời gian bật đã giữ được ghi bền trước khi bật (write-ahead) vào NVS trên `esp32s3` hoặc tệp trạng thái trên `linux`; sau khởi động coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động và chiếm ngân sách tới `window_s`; hỏng hoặc thiếu bản ghi thì coi cả cửa sổ đã dùng hết; vẫn chờ `min_interval_ms` trước lần bật đầu sau khởi động. *Vì sao:* ngăn chặn việc khởi động lại thiết bị liên tục để xoá giới hạn phong bì khi thiếu đồng hồ tin cậy xuyên khởi động.
10. **Bắt buộc phong bì và bỏ cờ `actuator` theo chân** (review 2026-10-01, Q-62). mọi chân `digital_out` mặc định là cơ cấu chấp hành, bắt buộc có phong bì tại `[capabilities.digital_out.envelope.<tên>]`; chỉ chân khai trong `signal_pins` mới được miễn; mọi chân `pwm.pins` luôn là cơ cấu chấp hành, không được khai trong `signal_pins`. Ba profile bậc 1 trong `boards/` phải bổ sung phong bì đủ rộng để vết ghi chuẩn mực replay y nguyên. *Vì sao:* loại bỏ cấu hình phân tán `actuator = true`, thiết lập mặc định an toàn fail-closed cho mọi chân điều khiển tải.
11. **Giám sát độc lập ngoài tiến trình runtime** (review 2026-10-01, Q-62). Hẹn giờ tự tắt và `duration_ms` không được chỉ sống trong tiến trình runtime có thể treo; trên `linux` dùng tiến trình giám sát riêng giữ `enable_pin` và ngắt khi mất nhịp tim; trên `esp32s3` dùng task watchdog (TWDT) và hẹn giờ phần cứng boot kéo xuống `enable_pin`. *Vì sao:* ngăn lỗi tiến trình bị treo (SIGSTOP) giữ nguyên trạng thái xuất xung của kernel driver quá thời hạn an toàn.
12. **Ràng buộc dữ kiện numeric từ `feedback`** (review 2026-10-01, Q-62). `digital.out(...).state()` tách mỗi đại lượng (`duty`, `frequency_hz`) thành một dữ kiện numeric riêng kèm `source`; gate chỉ nhận `source = measured` (từ chân thuộc `feedback.pins`), `commanded` tới gate bị coi là chưa có số đo ⇒ BLOCK `criterion_unavailable`; `build` kiểm tra khớp `unit` và dải đo (`BoardCapabilityError`, NE3001); cấm đưa tiêu chí numeric vào `on_block.confirms` (`GateSchemaError`, NE2002). *Vì sao:* bảo toàn tính toàn vẹn của dữ kiện lượng giá, ngăn người xác nhận thay đổi số đo cảm biến và ngăn nhầm lẫn giữa lệnh đã gửi với trạng thái thực tế.
13. **Từ chối `on()` và `pulse()` trên chân PWM** (review 2026-10-01, Q-62). Chân thuộc `pwm.pins` từ chối các thao tác `on` và `pulse` (`BoardCapabilityError`, chưa tiêu token); chỉ nhận thao tác `pwm` và `off`. *Vì sao:* ngăn việc vô tình xuất 100% duty làm cháy tải vượt trần `max_duty` của bo mạch.
14. **Ràng buộc cấu hình `enable_pin`** (review 2026-10-01, Q-62). Mỗi khai báo `enable_pin` bắt buộc chỉ định rõ `enable_active = "high"` và `pull = "down"`; giá trị khác bị từ chối lúc nạp (`BoardCapabilityError`). *Vì sao:* kiểm chứng chắc chắn trên lược đồ rằng mạch có cơ chế phần cứng kéo xuống an toàn khi mất điều khiển.
15. **Lượng tử hoá duty và cấm dùng chung `enable_pin`** (review 2026-10-01, Q-62). `duty` được lượng tử hoá theo `resolution_bits` và luôn làm tròn về 0; mỗi kênh PWM bắt buộc có một `enable_pin` riêng biệt, không dùng chung kênh khác (dùng chung ⇒ từ chối lúc nạp `BoardCapabilityError`). *Vì sao:* làm tròn về 0 đảm bảo không bao giờ vượt `max_duty` do sai số lượng tử; `enable_pin` riêng biệt cô lập lỗi giữa các cơ cấu chấp hành.
16. **`max_duty` bắt buộc, readback có đơn vị, `enable_pin` do HAL quản** (review 2026-10-01, Q-62). `max_duty` không có mặc định, thiếu ⇒ `BoardCapabilityError`. Readback `duty` là `ratio` trên `[0, max_duty]`, `frequency_hz` là `Hz` trên dải của bo. `enable_pin` không gọi được từ agent và miễn phong bì riêng. `min_interval_ms` tính từ lúc lần bật trước kết thúc. *Vì sao:* mặc định 1.0 là mặc định lỏng duy nhất còn lại; `build` cần đơn vị và thang để kiểm ràng buộc của RFC-0009.
