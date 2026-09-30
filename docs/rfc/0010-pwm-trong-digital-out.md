# RFC-0010: PWM và kênh phản hồi trạng thái trong `digital.out`

| | |
|:---|:---|
| **Mã RFC** | 0010 |
| **Tiêu đề** | Thao tác `pwm` (tần số, độ rộng xung) và đọc lại trạng thái chân trong `digital.out` |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(khối `pwm` và `feedback` trong `digital_out`)* · **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-05, FR-ACE-08 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (§9, Q-57) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc** (chạm đường tới chân vật lý và mở rộng phong bì của RFC-0007) |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/board.v1.json`. Task: TSK-W1-01.
> Nguồn: `roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md` §7.1. Quyết định nền: `neuroedge-prd.md` §15
> Q-52 (gói PWM nằm trong MVP), Q-53 (bốn gói trên cả ba target bậc 1), Q-55. Phụ thuộc: phong bì ở
> [RFC-0007](0007-digital-in-i2c-analog-in-phong-bi.md), mẫu ràng buộc tham số ở
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
pins             = ["fan"]                 # tập con của digital_out.pins
frequency_hz     = { min = 100, max = 25000 }
resolution_bits  = 10
max_duty         = 0.8                     # trần cứng của tải; 1.0 nếu không khai

[capabilities.digital_out.feedback]
pins = ["fan"]                             # chân đọc lại được trạng thái
```

`board.v1` là **sự thật phần cứng** (tải chịu được gì); gate là **chính sách** (được phép gì). Gate chặt hơn được, không bao giờ nới trần bo mạch.

### 3b. Thao tác và API

`HardwareAbstractionLayer.digital_out` nhận thêm `operation = "pwm"` kèm `frequency_hz`, `duty` (0.0–1.0) và `duration_ms`. Phía agent (`hal/digital.py`): `digital.out("fan").pwm(frequency_hz=1000, duty=0.4, ms=5000)`. Thứ tự giữ như RFC-0007: `require_pin → kiểm giới hạn bo mạch → envelope → authorize → record`; chân không khai `pwm` ⇒ `BoardCapabilityError` ba phần, **chưa tiêu token**. Đọc lại trạng thái: `digital.out("fan").state()` trả `{level | duty, frequency_hz}` thực; không cần token (không di chuyển gì), ghi thành sự kiện để replay.

### 3c. Ràng buộc tham số ở gate (mẫu RFC-0005)

Không đổi `gate.v1`. `@action` khai `duty` và `frequency_hz` là tham số; gate dùng khối `arguments` sẵn có:

```yaml
arguments:
  duty:         { type: number,  minimum: 0.0, maximum: 0.6 }
  frequency_hz: { type: integer, minimum: 200, maximum: 5000 }
```

Vi phạm ⇒ BLOCK `argument_out_of_range` trước `evaluate`; giá trị mặc định của `@action` cũng được kiểm; gate con chỉ thu hẹp (RFC-0005 §3). Walker C đã đọc bảng giới hạn tham số nên **không cần nút mới**.

### 3d. Mở rộng phong bì

Phong bì của RFC-0007 tính thời gian *có xung ra*. Với PWM: mọi lúc `duty > 0` được tính là "bật" (bảo thủ), cộng thêm trần `max_duty` của bo mạch. Có thể thêm `max_continuous_ms` theo chân (một lệnh PWM không có `duration_ms` bị chặn ở giá trị này, rồi về `duty = 0`).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có với ba profile `boards/`; `digital_out` không đóng nên `pwm`/`feedback` chưa từng bị từ chối |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai `pwm`/`feedback` đúng hình dạng. Cùng điểm siết chặt như RFC-0007 §4 nếu có ai đã dùng tên khoá này trước: không có trong kho |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Không, với điều kiện hình dạng chốt trước khi có profile ngoài kho |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — chưa có `pwm` trong chuỗi phán quyết của chúng |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không — dùng lại bảng giới hạn tham số của RFC-0005/RFC-0003 |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không đổi đáp án cũ; thêm ca mới cho tham số `duty`/`frequency_hz` |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn:** `gate.v1` và năm nguyên tắc kế thừa giữ nguyên; ràng buộc `duty`/`frequency_hz` chạy tất định trước `evaluate`, không tốn ngân sách mô hình.
- **Lớp thứ hai độc lập:** trần cứng ở `board.v1` chặn cả gate viết quá rộng. Một gate cho `duty` tới 1.0 trên tải chỉ chịu 0.8 vẫn bị từ chối ở HAL.
- **Trạng thái tồn tại sau khi action trả về:** PWM giống `on()` — chân tiếp tục xuất xung. Vì vậy phong bì (thời gian liên tục tối đa) là bắt buộc để không có PWM không giới hạn; đây là điểm chính cần kỹ thuật trưởng duyệt.
- **Tắt máy:** SIGTERM/thoát bình thường đưa chân về mức an toàn qua `hal.close()` (`LinuxHAL.close` thả mọi line về không hoạt động). Crash/SIGKILL không bảo đảm được bằng phần mềm: cần điện trở kéo xuống hoặc watchdog (xem `roadmap/neuroedge-design-neurobrain.md` §2.3 và RFC-0011 §5).
- **Kênh phản hồi chỉ đọc**, không thể dùng để tránh gate: `state()` không tạo hay gia hạn quyền điều khiển.

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Nguyên thủy `pwm.out` riêng | PWM là cách điều khiển *một chân số*; tách ra nhân đôi bảng chân, `require_pin` và phong bì. Kế hoạch gốc (§7.1) đã giữ nó trong `digital.out` |
| PWM giả bằng chuỗi `pulse` | Sai tần số, mỗi xung tốn một token, phong bì tính sai |
| Nhét `duty`/`frequency_hz` vào `gate.v1` như trường riêng | `arguments` đã đủ (RFC-0005); thêm trường là nới lược đồ gate không cần thiết |
| Cho `motion.*` (RFC-0011) làm cả PWM | Motor/servo có kênh, đích, ramp, lease; quạt/đèn không cần. Hai hợp đồng khác nhau |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: profile `boards/` khai `pwm` và `feedback` (bo mạch tham chiếu theo RFC-0013)
- [ ] Phản chứng: chân `pwm` không thuộc `pins`, `min > max`, `max_duty` ngoài (0, 1], tần số ngoài dải
- [ ] Test: `duty` vượt `maximum` của gate ⇒ BLOCK `argument_out_of_range`, chân không đổi; `duty` vượt `max_duty` bo mạch ⇒ từ chối ở HAL, **token không bị tiêu**; giá trị mặc định cũng được kiểm; PWM không `duration_ms` bị chặn bởi `max_continuous_ms`; sau `hal.close()` chân về mức không hoạt động
- [ ] Ca mới ở `fixtures/tool_calls/` cho tham số PWM, khép kín hai chiều trong `expected_results.yaml`
- [ ] `sim` không khai PWM mà bo mạch tham chiếu thiếu; `neuroedge gate lint` và `neuroedge verify` xanh

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json`
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md`; FR-HAL-01 ở `neuroedge-prd.md`
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-W1-01)
- [ ] Hiện thực `python/neuroedge/hal/` (`__init__.py`, `digital.py`, `sim.py`, `linux.py`); firmware `esp32s3`
- [ ] Thêm fixture/test; cập nhật `docs/rfc/README.md` và `CHANGELOG.md`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Mục này **thay** mọi đoạn đề xuất trái với nó ở §3; khi mở PR RFC, gộp nội dung vào §3. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Backend PWM trên `linux`:** **chỉ PWM phần cứng của kernel** (`/sys/class/pwm`). Không có PWM phần mềm; bo mạch không có kênh PWM phần cứng thì không khai `pwm`. Test CI chạy trên cây sysfs giả (cùng cách `hal/sysfs.py`), bằng chứng phần cứng ở nightly Pi 5. *Vì sao:* xung phần mềm lệch thời gian và dừng giữa chừng khi tiến trình nghẽn.
2. **Chân cho phép (thêm mới).** Kênh PWM nối cơ cấu chấp hành **bắt buộc** khai `enable_pin` — một line `digital.out` có điện trở kéo xuống trên mạch; HAL chỉ bật `enable_pin` trong lúc có lệnh PWM đã qua gate. *Vì sao:* kênh PWM của kernel **vẫn chạy sau khi tiến trình chết**; line gpiod thì được thả khi tiến trình thoát, nên kéo xuống ngắt driver kể cả khi crash (`neuroedge-design-neurobrain.md` §2.3).
3. **Phong bì đếm thời gian bật** là toàn bộ thời gian có duty > 0, không nhân với duty. *Vì sao:* bảo thủ, không phụ thuộc mô hình năng lượng của tải.
4. **`state()`** trả `{value, source}` với `source` là `measured` (đọc lại từ phần cứng) hoặc `commanded` (giá trị đã ghi); gate chỉ được dùng giá trị `measured` làm dữ kiện, và bo mạch không có readback thì không khai `feedback`. *Vì sao:* không bao giờ trình bày lệnh đã gửi như trạng thái đã đo.
5. **`duration_ms` luôn bắt buộc**, bị chặn bởi `arguments` của gate và `max_continuous_ms` của bo mạch (RFC-0007). *Vì sao:* không có PWM "chạy mãi"; muốn chạy tiếp phải gọi lại qua gate.
