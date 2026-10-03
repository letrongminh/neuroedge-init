# RFC-0007: `digital.in`, bus I2C chỉ đọc, `analog.in` và phong bì an toàn theo chân

| | |
|:---|:---|
| **Mã RFC** | 0007 |
| **Tiêu đề** | Ba nguyên thủy đầu vào mới (`digital.in`, I2C chỉ đọc, `analog.in`) và phong bì an toàn khai ở `board.v1` |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(thêm khoá `digital_in`, `i2c`, `analog_in` và khối `envelope`)* · danh mục mã lỗi `neuroedge-prd.md` Phụ lục B *(thêm NE1003, mở phạm vi NE5001 — §4)* · **không** đụng `gate.v1`, `trace.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ✅ Đã chấp thuận (2026-10-01) — kỹ thuật trưởng ký trên PR #75; sửa theo review 2026-10-01 (§9, Q-62); hiện thực trong PR thứ hai |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc.** Phong bì chạm đường tới chân vật lý (§5), và §4 nêu một điểm siết chặt lược đồ cần chữ ký |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json`. RFC này sửa `schemas/board.v1.json`.
> Quyết định nền: `neuroedge-prd.md` §15 Q-52 (MVP là v1.0 đầy đủ gồm bốn gói nguyên thủy, một bản phát hành,
> trượt ngày thay vì cắt), Q-53 (bốn gói bắt buộc trên cả ba target bậc 1; **`analog.in` chuyển từ RFC-motion
> sang RFC này**), Q-55 (NeuroBrain vào MVP). Nguồn: bản nháp robot FOFOCA (`roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md`),
> nay rút về RFC này, và `roadmap/neuroedge-design-neurobrain.md` §7, §8. Task: TSK-N0-03 (soạn RFC này), TSK-N2-01
> (hook phong bì), TSK-N2-02 (check-và-reserve nguyên tử), TSK-N3-03 (spike ADC).

## 1. Vấn đề

HAL có năm nguyên thủy (`PRIMITIVES` trong `python/neuroedge/hal/board.py`). Ba nhu cầu thật không diễn đạt được:

1. **Đọc mức logic** — nút nhấn, công tắc hành trình, tiếp điểm cửa. `digital.out` chỉ ghi.
2. **Nhìn thấy cái gì đang gắn trên bus I2C** — bring-up bo mạch cần quét bus và đọc thiết bị lạ mà không phải viết driver trước.
3. **Đọc điện áp tương tự** (ADC) — áp suất, dòng, pin.

Và một thiếu sót an toàn: đầu ra chỉ bị chặn bởi token một lần, không bởi **hậu quả vật lý tích luỹ**. Một `digital.out("porch_light").on()` lặp qua gate hợp lệ mỗi giây vẫn giữ tải bật liên tục. Tích luỹ thời gian không thể nằm trong gate (gate thuần, bất biến số 4), nên phải có chỗ khác khai và cưỡng chế.

## 2. Vì sao lược đồ hiện tại không giải quyết được

- `schemas/board.v1.json` chỉ định hình năm khoá `capabilities` (`audio_in`, `audio_out`, `digital_out`, `sensor_read`, `display`). Khoá khác **validate qua** vì `capabilities` không có `additionalProperties: false`, nhưng không có hình dạng nào để đối chiếu với `[requires]` của agent (FR-HAL-04).
- `digital_out` chỉ khai `pins` và `backend`; không có chỗ khai giới hạn thời gian bật hay tần suất.
- **Vì sao không mở rộng `sensor.read`** (TSK-N0-03 đòi lý giải):
  - `sensor.read` là hợp đồng *"đọc một giá trị vô hướng theo tên đã khai"*: `BoardProfile.require_sensor` từ chối tên ngoài `sensor_read.sensors`, và `sensor_read` được ghi thành sự kiện `sensor_read` để replay nạp lại (`docs/spec/simulation_coverage.md`). Quét bus trả về **tập thiết bị chưa đặt tên**, thao tác trên bus có tác dụng phụ, và không có tên để replay.
  - Nhét bus/địa chỉ vào `sensor.read` làm mờ `[requires]`: agent khai `"sensor.read" = { sensors = ["motion"] }` (xem `fixtures/agents/home-voice/agent.toml`) nghĩa là *"cần đúng cảm biến này"*; nếu `sensor.read` còn có nghĩa *"quyền chạm bus thô"* thì một bo mạch có cảm biến hợp lệ nhưng không cho quét vẫn "khớp".
  - `digital.in` là mức logic tức thời không đơn vị; `analog.in` là số có đơn vị và thang. Cả hai cần khai riêng (chân, kênh, thang) mà `sensors: string[]` không mang được.
  - FR-HAL-01 đóng tập nguyên thủy có chủ ý (bảng năng lực firmware là mảng tĩnh). Mở rộng một nguyên thủy sẵn có bằng ngữ nghĩa ẩn còn tệ hơn thêm nguyên thủy có tên: đường kiểm `missing_primitives()` không thấy được.

## 3. Thay đổi đề xuất

### 3a. `digital.in`

```toml
[capabilities.digital_in]
pins    = ["button_boot", "door_contact_raw"]
backend = "esp_driver_gpio"        # cùng vai trò trường `backend` của digital_out
```

Tên: nguyên thủy `digital.in` trong `[requires]`, khoá bo mạch `capabilities.digital_in`; HAL thêm `HardwareAbstractionLayer.digital_in(pin, called_from=...) -> bool` cạnh `digital_out`; API cho agent là `digital.input("door_contact").level()` (không đụng từ khoá `in` của Python; tên chân là tên logic, FR-HAL-06). Chân phải có trong `digital_in.pins`: chân không khai ⇒ `BoardCapabilityError` (NE3001) ba phần lúc nạp, và cũng bị từ chối khi gọi. Đọc **không di chuyển gì** nên không cần token (như `sensor.read`), và được ghi thành sự kiện `digital_in` để replay nạp lại; `sim` phát lại giá trị đã ghi (`set_sensor`-tương đương cho chân), không giàu hơn bo mạch tham chiếu. Đọc hỏng ⇒ `PerceptionUnavailableError` (§3e).

Giá trị `digital.in` đưa vào gate dưới dạng dữ kiện `bool`, kèm mốc đọc HAL trên trục thời gian đơn điệu của phiên. Mốc đọc dùng tính `age_ms`: thời điểm lượng giá là offset của sự kiện phán quyết trên cùng trục thời gian; vết ghi ghi cả mốc đọc lẫn `age_ms`; `replay` tính lại và so; `age_ms < 0` (mốc đọc sau thời điểm lượng giá) ⇒ BLOCK `criterion_unavailable`. HAL đọc `digital.in` **ngay lúc lượng giá**, không dùng giá trị đệm; tuổi vượt trần cố định `DIGITAL_IN_MAX_AGE_MS = 100` trong mã ⇒ BLOCK `criterion_unavailable` (tiêu chí `bool` không có `max_age_ms`). Trần này bắt được đường đọc treo; đầu vào kẹt mức ở phần cứng thì không phát hiện được bằng tuổi, nên gate quan trọng nên có thêm một tiêu chí độc lập.

### 3b. Bus I2C chỉ đọc

```toml
[capabilities.i2c]
buses = [{ id = "i2c0", devices = [{ name = "ads1015", address = 0x48, readable_registers = [0x00, 0x01] }] }]
```

"Chỉ đọc" nghĩa là **không có đường ghi dữ liệu**; lần ghi duy nhất API phát ra là byte con trỏ thanh ghi ở dưới.

- **Quét bằng read-byte** (TSK-N3-01): thăm dò địa chỉ chỉ bằng thao tác đọc; **không** dùng quick-write.
- **Địa chỉ ngoài allowlist** (không có trong `devices`) chỉ được **báo cáo có mặt** khi quét: ngoài read-byte thăm dò đó, chúng **không bao giờ được đọc hay ghi**.
- **Thiết bị trong allowlist** đọc được bằng receive-byte (không địa chỉ thanh ghi). **Đọc thanh ghi** (ghi con trỏ thanh ghi rồi repeated-start đọc) chỉ được phép khi thanh ghi nằm trong `readable_registers` bo mạch khai cho thiết bị đó; thanh ghi không khai bị từ chối như chân không khai (`BoardCapabilityError`), không phát giao dịch nào lên bus. Lý do giữ hẹp: một số chip coi mọi lần ghi là lệnh.
- Không có hàm ghi dữ liệu nào trong API. Mỗi lần đọc ghi thành sự kiện `i2c_read`; bus NACK hay timeout ⇒ `PerceptionUnavailableError` (§3e). Công cụ `lab_read` của NeuroBrain (`roadmap/neuroedge-design-neurobrain.md` §6) đọc chân qua `digital.in` của RFC này; cờ `[lab]` mặc định tắt và không nới allowlist.
- Trên `linux`, kiểm thử dựng trên `i2c-stub` (Khối N3, roadmap); `sim` chỉ phát lại giá trị đã ghi, không quét thật.

### 3c. `analog.in`

```toml
[capabilities.analog_in]
channels = [{ name = "supply_v", unit = "V", min = 0.0, max = 5.0, resolution_bits = 12 }]
```

Trả số kèm đơn vị và thang khai; giá trị ngoài `[min, max]` là lỗi đọc, không bị cắt lặng lẽ. Ngưỡng an toàn trên giá trị này **không** nằm ở nguyên thủy mà ở tiêu chí `numeric` của gate ([RFC-0009](0009-tieu-chi-so-numeric.md)). Giá trị `analog.in` vào gate dạng tiêu chí `numeric`, kèm mốc đọc HAL trên trục thời gian đơn điệu của phiên; mốc đọc dùng tính `age_ms`; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. Ràng buộc kênh với tiêu chí: khi agent nối tiêu chí `numeric` với kênh `analog.in`, `neuroedge build` kiểm `unit` trùng nhau và `[min, max]` của kênh nằm trong `range` của tiêu chí; lệch ⇒ `BoardCapabilityError` (NE3001) lúc build. Tiêu chí `numeric` nối `analog.in` không được nằm trong `on_block.confirms` của RFC-0006: `gate lint` từ chối (`GateSchemaError`, NE2002). **Có điều kiện**: đường kiểm thử trên `linux` phụ thuộc spike TSK-N3-03 (chip ADC I2C có driver hwmon trên `i2c-stub`, runner tắt `CONFIG_IIO`). Spike trượt không có nghĩa bỏ `analog.in` (Q-52, Q-53 buộc có mặt trên cả ba target): `analog.in` được kiểm hằng đêm trên runner tự quản gắn ADC thật (Pi 5 + ADC I2C), và **chặn tiêu chí ra của I2a** tới khi có bằng chứng đó — nguyên thủy chưa kiểm trên phần cứng không được phát hành. Mỗi lần đọc ghi thành sự kiện `analog_in`; cảm biến mất hay timeout ⇒ `PerceptionUnavailableError` (§3e).

### 3d. Phong bì an toàn theo chân — khai ở `board.v1`

```toml
[capabilities.digital_out]
pins        = ["porch_light", "status_led"]
signal_pins = ["status_led"]    # chân chỉ là tín hiệu, không nối tải

[capabilities.digital_out.envelope.porch_light]
window_s              = 3600      # cửa sổ trượt
max_on_ms_per_window  = 1800000   # tổng thời gian bật tối đa trong cửa sổ
min_interval_ms       = 2000      # giãn cách tối thiểu trước lần bật tiếp theo
max_continuous_ms     = 600000    # trần một lần bật, độc lập với `arguments` của gate
```

Bốn khoá này dùng chung cho RFC-0010, RFC-0011. Khai phong bì ở `[capabilities.digital_out.envelope.<tên>]` với `<tên>` là tên chân.

**Cơ cấu chấp hành và `signal_pins`:** Cờ cơ cấu chấp hành không dùng `actuator = true` theo từng chân vì `digital_out.pins` là mảng chuỗi. Thay vào đó, **mọi chân `digital_out` mặc định là cơ cấu chấp hành, bắt buộc có phong bì**. Ngoại lệ: `enable_pin` của RFC-0010, RFC-0011 do HAL tự quản, agent không gọi được, miễn phong bì riêng (thời gian bật của nó đã bị phong bì của kênh nó phục vụ chặn). Chân chỉ là tín hiệu (không nối tải) khai trong mảng `[capabilities.digital_out] signal_pins = [...]` (tập con của `pins`, không giao `pwm.pins`). Chân thuộc `signal_pins` không bắt buộc có phong bì. Thiếu phong bì trên chân không thuộc `signal_pins` ⇒ `BoardCapabilityError` (NE3001) lúc nạp profile. Lý do: giới hạn phần cứng phải đứng được cả khi gate viết lỏng.

**Lệnh về phía an toàn không bao giờ bị chặn:**
- Lệnh về phía an toàn gồm: `digital.out` `off`; mọi lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, khi cắt lời, BLOCK, mất liên lạc, `hal.close()`.
- Các lệnh này **không bao giờ bị chặn**: không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay chờ sau khởi động. Đây là **ngoại lệ duy nhất** của luật "không lệnh nào ra phần cứng mà không có ALLOW". Lệnh vẫn ghi vết ghi kèm nguyên nhân.
- `min_interval_ms` **chỉ áp cho lệnh bật**, tức lệnh đưa cơ cấu từ trạng thái an toàn sang hoạt động, và tính từ lúc lần bật trước **kết thúc** (chân về trạng thái an toàn). Lệnh `off` ngay sau `on` không bao giờ bị từ chối bởi `min_interval_ms`.

**Tự tắt bắt buộc và hoàn phần giữ trước:**
- Mọi lệnh bật trên chân có phong bì đều có thời hạn hữu hạn. Lúc bật, HAL và firmware hẹn giờ tự tắt tại `min(thời hạn của lệnh, max_continuous_ms)`. `on()` không thời hạn ⇒ thời hạn = `max_continuous_ms`.
- Phong bì giữ trước đúng thời hạn đó trong `max_on_ms_per_window`. Tắt sớm thì hoàn phần chưa dùng.
- `authorize` thất bại sau khi đã giữ trước thì hoàn trả toàn bộ phần đã giữ: không tiêu token, không phát xung ra chân.

**Hook và cưỡng chế firmware (TSK-N2-01, RB-4):**
- Hook nằm trong `HardwareAbstractionLayer.digital_out` (`python/neuroedge/hal/__init__.py`), được tiêm vào như `authorize`. Thứ tự: `require_pin → envelope → authorize → record`. Phong bì đứng trước `authorize` nên lệnh bị từ chối không tiêu token; lệnh bị từ chối ném `EnvelopeRefusedError` (§3e) và ghi sự kiện `envelope_refused`.
- Check-và-reserve là một bước nguyên tử (TSK-N2-02) để hai lệnh đồng thời không cùng qua ngân sách còn lại.
- Hook phong bì không chỉ ở Python HAL: firmware `esp32s3` cưỡng chế cùng luật; bảng phong bì là bảng `const` sinh lúc build từ `board.v1` nằm trong flash (RB-4 của `docs/spec/hal_mcu_review.md`).

**Giám sát độc lập ngoài tiến trình:**
- Hẹn giờ tự tắt và `duration_ms` không được chỉ sống trong tiến trình runtime có thể treo.
- Trên `esp32s3`: task watchdog (TWDT) cộng hẹn giờ phần cứng; watchdog reset thì boot với chân ở mức kéo xuống an toàn.
- Trên `linux`: line của chân cơ cấu do một tiến trình giám sát riêng giữ; runtime gửi nhịp tim; mất nhịp quá thời hạn ⇒ giám sát thả line và tắt chân.

**Phong bì sống qua khởi động lại:**
- Tổng thời gian bật đã giữ trong cửa sổ được ghi bền trước khi bật (write-ahead): NVS trên `esp32s3`, tệp trạng thái trên `linux`; `sim` mô phỏng cùng luật.
- Sau khởi động không có đồng hồ tin cậy xuyên khởi động, nên coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động; chúng chiếm ngân sách tới `window_s` sau khởi động. Không đọc được, hỏng hoặc thiếu bản ghi ⇒ coi cả cửa sổ đã dùng hết (fail-closed).
- Sau khởi động, mỗi chân có phong bì vẫn phải chờ `min_interval_ms` trước lần bật đầu tiên. Chân thuộc `signal_pins` không khai `envelope` ⇒ hành vi không đổi.

### 3e. Mã đi kèm

`PRIMITIVES` tách thành lõi và mở rộng, `_CAPABILITY_KEYS` thêm ba khoá: chi tiết ở [RFC-0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md).

Lỗi (`python/neuroedge/errors.py`) — mỗi loại hỏng một mã riêng để hậu kiểm, không loại nào dẫn tới ALLOW:

| Tình huống | Lỗi | Vết ghi |
|:---|:---|:---|
| Phong bì từ chối | Lớp mới `EnvelopeRefusedError` (**NE1003**, lớp con của `ActionContractViolation`); token không bị tiêu | `envelope_refused` |
| Đọc hỏng (bus NACK, timeout, cảm biến mất) | `PerceptionUnavailableError` (NE5001) ⇒ tiêu chí chưa quyết ⇒ BLOCK `criterion_unavailable` (như RFC-0009) | `digital_in` / `i2c_read` / `analog_in` |
| Chân, kênh, thiết bị hoặc thanh ghi không khai | `BoardCapabilityError` (NE3001) lúc nạp; lời gọi tới tên không khai cũng bị từ chối, không chạm bus hay chân | — |

NE5001 hôm nay chỉ định nghĩa lúc nạp/build (`neuroedge-prd.md` Phụ lục B); RFC này **mở phạm vi** của nó sang lúc chạy cho lần đọc HAL hỏng — §4.

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Ba profile bậc 1 trong `boards/` phải thêm phong bì (hoặc khai `signal_pins`) trong PR hiện thực, với giá trị đủ rộng để ba vết ghi chuẩn mực vẫn replay y nguyên (ví dụ `door_lock` nhận xung 30.000 ms ⇒ `max_continuous_ms` ≥ 30000); chưa có profile bên ngoài kho. **Điểm siết chặt:** `digital_in`, `i2c`, `analog_in` hôm nay được nhận ở dạng *bất kỳ* vì `capabilities` không đóng; sau RFC chúng có hình dạng bắt buộc. Mọi chân `digital_out` mặc định là cơ cấu chấp hành bắt buộc có phong bì trừ khi liệt kê trong `signal_pins`. Kỹ thuật trưởng phải xác nhận việc này không cần `board.v2` (RFC-0002 §9.1 đã cảnh báo cùng bẫy: sửa hình dạng sau khi phát hành mới là siết chặt) |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai ba khoá mới đúng hình dạng và khối `envelope` |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Đề xuất **không**, với điều kiện hình dạng ở §3 được chốt **trước** khi có profile ngoài kho dùng chúng |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — `gate.v1` không đổi |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — ba profile bậc 1 được cấu hình phong bì đủ rộng trong PR hiện thực để ba vết ghi chuẩn mực replay y nguyên (ví dụ `max_continuous_ms` ≥ 30000 cho `door_lock`). Bốn loại sự kiện mới (`digital_in`, `i2c_read`, `analog_in`, `envelope_refused`) không đổi `trace.v1` vì `type` là chuỗi mở; chúng thêm dòng vào bảng sự kiện `docs/spec/simulation_coverage.md` |
| Danh mục mã lỗi (`neuroedge-prd.md` Phụ lục B)? | Có, khi chấp thuận: thêm dòng `EnvelopeRefusedError` NE1003 (Chạy · phong bì từ chối · ném ngoại lệ, chân không được kích, token không bị tiêu, ghi `envelope_refused`); dòng NE5001 mở cột thời điểm sang *Chạy (đọc HAL)* với hành vi BLOCK `criterion_unavailable` |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không — không có phong bì thì `digital_out` cùng thứ tự lỗi (hợp đồng hồi quy `neuroedge-design-neurobrain.md` §7.1). Phong bì từ chối thêm ca mới ở corpus riêng |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn theo đường nào**: `gate.v1`, ngữ nghĩa phân giải và năm nguyên tắc kế thừa (Phụ lục B.5) không đổi. Phong bì là **lớp chặn thứ hai, độc lập**, chỉ thêm khả năng từ chối.
- **Gate vẫn thuần (bất biến số 4):** tích luỹ thời gian bật và tần suất nằm ở HAL, không ở gate. Đây là lý do khai ở `board.v1` chứ không thêm trường vào gate.
- **Lệnh về phía an toàn không bao giờ bị chặn:** `digital.out` `off` và các lệnh HAL tự phát khi hết hạn, hết `max_continuous_ms`, BLOCK, cắt lời, mất liên lạc, `hal.close()` không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay sau khởi động. Đây là ngoại lệ duy nhất của luật "không lệnh nào ra phần cứng mà không có ALLOW". Lệnh vẫn ghi vết ghi kèm nguyên nhân.
- **Mặc định fail-closed:** lệnh vượt phong bì bị từ chối trước `authorize`; không có chế độ "cảnh báo rồi cho qua". Không dùng cờ `[lab]` làm ngoại lệ phong bì. mọi chân `digital_out` mặc định là cơ cấu chấp hành bắt buộc có phong bì (trừ chân khai `signal_pins`). Tự tắt bắt buộc tại `min(thời hạn lệnh, max_continuous_ms)`. `authorize` thất bại thì hoàn trả toàn bộ phần đã giữ trước.
- **Phong bì sống qua khởi động lại:** tổng thời gian bật đã giữ được ghi bền trước khi bật (write-ahead: NVS trên `esp32s3`, tệp trạng thái trên `linux`). Sau khởi động, coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động, chiếm ngân sách tới `window_s`; hỏng hoặc thiếu bản ghi ⇒ coi cả cửa sổ đã dùng hết; chờ `min_interval_ms` trước lần bật đầu sau khởi động.
- **Giám sát ngoài tiến trình:** hẹn giờ tự tắt không chỉ sống trong tiến trình runtime có thể treo; TWDT và timer phần cứng trên `esp32s3` (watchdog reset boot với chân kéo xuống an toàn); tiến trình giám sát giữ line và nhịp tim trên `linux` (mất nhịp thả line tắt chân); SIGSTOP tiến trình runtime thì cơ cấu chấp hành tự về trạng thái an toàn trong thời hạn cộng biên đã khai.
- **Đầu vào fail-closed và bất biến thời gian:** đọc hỏng hoặc mốc đọc sau thời điểm lượng giá (`age_ms < 0`) ⇒ `PerceptionUnavailableError` ⇒ BLOCK `criterion_unavailable`, không bao giờ ALLOW (§3e). Tiêu chí `numeric` nối `analog.in` kiểm tra chặt chẽ thang đo và đơn vị lúc build, không cho phép xác nhận người dùng thay thế (`on_block.confirms`).
- **Đầu vào không có quyền ghi dữ liệu:** `digital.in`, `analog.in` không di chuyển chân. I2C không có đường ghi dữ liệu; lần ghi duy nhất là con trỏ tới thanh ghi trong `readable_registers` của thiết bị trong allowlist, và địa chỉ ngoài allowlist không bao giờ được đọc hay ghi ngoài read-byte thăm dò (§3b). Rủi ro còn lại: *đọc lộ thông tin* (giảm bằng allowlist), và một chip coi lần ghi con trỏ là lệnh — trách nhiệm của bo mạch khi khai `readable_registers`.
- Cần kỹ thuật trưởng duyệt vì chạm đường tới chân vật lý (`digital_out`).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Mở rộng `sensor.read` (quét bus, mức logic, ADC) | Xem §2: vô hướng có tên vs. tập chưa đặt tên; làm mờ `[requires]`; ADC cần thang và đơn vị |
| Khai phong bì trong `gate.v1` | Tích luỹ thời gian là trạng thái, phá tính thuần của gate (bất biến số 4); gate chia sẻ qua registry không biết phần cứng |
| Kiểm phong bì **sau** `authorize` | Lệnh bị từ chối đã tiêu token; sửa lỗi sau mất một token vô ích |
| I2C cho phép ghi dữ liệu tuỳ ý (kể cả có allowlist thanh ghi) | Mở đường thay đổi trạng thái thiết bị ngoài mọi gate; để dành cho RFC riêng nếu có nhu cầu thật. Dạng hẹp được nhận (§3b): chỉ ghi con trỏ của thanh ghi đã khai trong `readable_registers`, ngay trước repeated-start đọc — cách hẹp nhất vẫn đọc được cảm biến thật |
| Đọc thanh ghi bất kỳ trên thiết bị trong allowlist | Một số chip coi mọi lần ghi (kể cả ghi con trỏ) là lệnh; chỉ thanh ghi bo mạch khai mới được trỏ tới |
| Phong bì tuỳ chọn cho mọi chân | Chân nối cơ cấu chấp hành phải có giới hạn phần cứng đứng được cả khi gate viết lỏng. Mọi chân `digital_out` mặc định là cơ cấu chấp hành bắt buộc có phong bì; chỉ chân khai trong `signal_pins` mới là tín hiệu không nối tải; bỏ cờ `actuator = true` vì `pins` là mảng chuỗi |
| Chỉ dựa vào hẹn giờ mềm trong tiến trình runtime | Tiến trình có thể bị treo (SIGSTOP) hoặc crash; phải có watchdog phần cứng trên MCU và tiến trình giám sát độc lập trên Linux để đưa chân về an toàn |
| Áp `min_interval_ms` cho cả lệnh tắt (`off`) | Vi phạm §9 mục 7: lệnh đưa cơ cấu về an toàn không bao giờ bị chặn, không được từ chối `off` ngay sau `on` |
| Spike ADC trượt ⇒ dời `analog.in` vào `TODOS.md` | Q-53 đòi `analog.in` có mặt; nguyên thủy chưa kiểm trên phần cứng không được phát hành — kiểm trên runner tự quản và chặn tiêu chí ra I2a (§3c) |
| Để `analog.in` trong RFC-motion | Q-53: `analog.in` là gói đầu vào độc lập với `motion.*`; ràng buộc lên số đọc dùng tiêu chí `numeric`, không cần chuyển động |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: profile `boards/` khai `digital_in`, `i2c`, `analog_in`, `signal_pins` và `envelope` (bo mạch tham chiếu, RFC-0013); ba profile bậc 1 trong `boards/` bổ sung khai báo phong bì đủ rộng (`door_lock` có `max_continuous_ms` ≥ 30000) vẫn replay y nguyên ba vết ghi chuẩn mực
- [ ] Phản chứng: khoá sai hình dạng (`pins` không phải mảng), `address` ngoài 0x03..0x77, `min > max`, `window_s` <= 0, `max_continuous_ms` <= 0; chân `digital_out` không nằm trong `signal_pins` mà thiếu phong bì ⇒ `BoardCapabilityError` (NE3001); `signal_pins` chứa tên chân không có trong `pins` ⇒ `BoardCapabilityError`
- [ ] Test lệnh an toàn: lệnh `digital.out` `off` không bao giờ bị chặn, thực thi thành công ngay cả trong khoảng `min_interval_ms` ngay sau `on`, không qua phong bì, không cần ALLOW hay token, không chờ sau khởi động; `min_interval_ms` chỉ từ chối lệnh bật tiếp theo
- [ ] Test tự tắt bắt buộc và hoàn phần giữ trước: lệnh `on()` không thời hạn tự tắt tại `max_continuous_ms`; lệnh có thời hạn tự tắt tại `min(thời hạn lệnh, max_continuous_ms)`; phong bì giữ trước đúng thời hạn đó; tắt sớm hoàn phần dư chưa dùng; `authorize` thất bại thì hoàn trả 100% thời gian đã giữ trước, không tiêu token, không phát xung ra chân
- [ ] Test phong bì sống qua khởi động lại: thời gian bật được ghi bền trước khi bật (write-ahead: NVS trên `esp32s3`, tệp trạng thái trên `linux`); sau khởi động lại, thời gian đã ghi chiếm ngân sách trong `window_s`; bản ghi hỏng hoặc thiếu ⇒ từ chối bật (coi cả cửa sổ đã dùng hết); lần bật đầu sau khởi động trong `min_interval_ms` bị từ chối; mọi từ chối là `EnvelopeRefusedError` (NE1003) kèm sự kiện `envelope_refused`; hai lệnh đồng thời không cùng qua ngân sách (TSK-N2-02)
- [ ] Test giám sát ngoài tiến trình: tiến trình runtime bị treo (SIGSTOP) trong lúc chân cơ cấu đang bật ⇒ cơ cấu chấp hành tự động về trạng thái an toàn trong thời hạn cộng biên đã khai (watchdog reset boot kéo chân xuống trên `esp32s3`, giám sát ngắt line khi mất nhịp tim trên `linux`)
- [ ] Test tương đương host ↔ C (RB-4): firmware `esp32s3` cưỡng chế cùng luật phong bì từ bảng `const` trong flash; bộ test tương đương host Python ↔ firmware C cho phong bì và các driver `digital.in`, I2C, ADC
- [x] Test tuổi dữ kiện: mốc đọc `digital.in` và `analog.in` ghi vào vết ghi cùng `age_ms`; `replay` tính lại và so; `age_ms < 0` (mốc đọc sau thời điểm lượng giá) ⇒ BLOCK `criterion_unavailable` — *phần `analog.in` đạt (TSK-I2a-04): `test_a_reading_older_than_max_age_is_unavailable_and_exactly_that_old_is_valid`, `test_a_read_mark_after_the_evaluation_instant_is_unavailable`, `test_replay_reproduces_every_verdict_from_the_recorded_readings`, `test_replay_distrusts_a_trace_whose_age_was_altered` (`tests/test_analog_in.py`); phần `digital.in` đạt (TSK-I2a-02): `test_a_level_exactly_as_old_as_the_ceiling_passes_and_one_ms_older_does_not`, `test_a_level_read_after_the_verdict_is_unavailable`, `test_the_fact_carries_its_source_and_read_marks_into_the_trace`, `test_replay_does_not_trust_an_age_the_trace_cannot_account_for` (`tests/test_digital_in.py`)*
- [x] Test ràng buộc kênh `analog.in` với tiêu chí `numeric`: `neuroedge build` kiểm `unit` trùng và `[min, max]` của kênh nằm trong `[range_min, range_max]` của tiêu chí; lệch ⇒ `BoardCapabilityError` (NE3001); tiêu chí `numeric` nối `analog.in` nằm trong `on_block.confirms` ⇒ `gate lint` từ chối (`GateSchemaError`, NE2002) — *đạt (TSK-I2a-04): `test_a_criterion_range_that_contains_the_channel_range_builds`, `test_a_criterion_range_the_channel_can_leave_is_refused_at_build`, `test_a_criterion_in_another_unit_than_the_channel_is_refused_at_build`, `test_a_numeric_criterion_bound_to_a_channel_cannot_be_in_confirms`, `test_gate_lint_refuses_the_same_gate` (`tests/test_analog_in.py`)*
- [ ] Quét `i2c-stub`: địa chỉ ngoài allowlist chỉ được liệt kê; mọi lời gọi đọc tới nó bị từ chối và `i2c-stub` không thấy giao dịch nào ngoài read-byte thăm dò
- [ ] I2C trên `i2c-stub`: đọc thanh ghi trong `readable_registers` thành công (một lần ghi con trỏ rồi repeated-start đọc); thanh ghi không khai bị từ chối, không phát giao dịch; API không có hàm ghi dữ liệu
- [ ] Đọc hỏng (NACK, timeout, cảm biến mất) trên `digital.in`, I2C, `analog.in` ⇒ `PerceptionUnavailableError` ⇒ BLOCK `criterion_unavailable`, không bao giờ ALLOW — *phần `analog.in` đạt (TSK-I2a-04): `test_a_reading_the_channel_cannot_give_blocks_criterion_unavailable`, `test_a_read_that_fails_is_unavailable_and_recorded`, `test_an_adc_that_fails_mid_session_blocks_criterion_unavailable` (`tests/`); `tests_linux/test_analog_in.py` trên `i2c-stub` (chưa chạy được trên máy tác giả); `digital.in` đạt (TSK-I2a-02): `test_any_failed_read_blocks_even_a_gate_that_fails_open`, `test_an_input_nobody_set_blocks_criterion_unavailable`, `test_a_line_that_fails_to_read_blocks_criterion_unavailable_on_linux` (`tests/test_digital_in.py`, `tests/test_digital_in_linux.py`); I2C còn lại*
- [x] `analog.in` trên `linux`: spike TSK-N3-03 đạt trên `i2c-stub`, hoặc bằng chứng hằng đêm từ runner tự quản gắn ADC thật trước tiêu chí ra I2a — *đạt trên `i2c-stub` 2026-10-03 (`ads7828`, `ina219`; PR #87)*
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; ba vết ghi chuẩn mực không đổi

## 8. Việc phải làm khi chấp thuận

- [x] Cập nhật `schemas/board.v1.json`: thêm `digital_in`, `i2c`, `analog_in`, `signal_pins` và lược đồ khối `envelope`; bắt buộc phong bì cho mọi chân `digital_out` không thuộc `signal_pins` — *đạt: `digital_in`, `i2c`, `analog_in`, `signal_pins`, `envelope`; thiếu phong bì ⇒ NE3001 — `tests/test_board_fixtures.py`*
- [x] Bổ sung khối phong bì cho ba profile bậc 1 trong `boards/` đủ rộng (`door_lock` có `max_continuous_ms` ≥ 30000) để ba vết ghi chuẩn mực replay y nguyên — *đạt: ba profile bậc 1 và `sim-rpi5` — `test_the_envelopes_are_wide_enough_for_the_canonical_traces`; `neuroedge verify --targets sim` xanh*
- [ ] Ghi ngoại lệ duy nhất của luật "không lệnh nào ra phần cứng mà không có ALLOW" cho lệnh về phía an toàn (`digital.out` `off`, HAL tự ngắt) vào `docs/spec/threat_model.md` §1 khi hiện thực
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md` và FR-HAL-01 ở `neuroedge-prd.md`; quyết định mới cấp `Q-N` ở §15
- [x] `neuroedge-prd.md` Phụ lục B: thêm dòng `EnvelopeRefusedError` NE1003, mở phạm vi NE5001 sang lúc chạy (§4); `python/neuroedge/errors.py` thêm lớp và sửa docstring `PerceptionUnavailableError` — *đạt: NE1003 và NE5001 ở Phụ lục B, lớp `EnvelopeRefusedError` và docstring `PerceptionUnavailableError` ở `errors.py`, `__all__`, `docs/spec/python_api.md`*
- [x] `docs/spec/simulation_coverage.md`: thêm sự kiện `digital_in`, `i2c_read`, `analog_in`, `envelope_refused` vào bảng sự kiện — *đạt: `digital_in`, `i2c_read`, `analog_in`, `envelope_refused` ở §3*
- [ ] `neuroedge-design-neurobrain.md` §8: nhánh "spike không đạt" theo §3c (runner tự quản, chặn tiêu chí ra I2a), thay cho việc đưa ADC vào `TODOS.md`
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-N0-03 xong; TSK-N2-01, TSK-N2-02, TSK-N3-03; tiêu chí ra I2a đòi bằng chứng ADC trên phần cứng)
- [ ] Hiện thực trong `python/neuroedge/hal/` (`board.py`, `__init__.py`, `sim.py`, `linux.py`): phong bì theo chân, tự tắt bắt buộc, hoàn phần giữ trước khi tắt sớm hoặc authorize hỏng, ghi bền write-ahead tệp trạng thái trên linux, tiến trình giám sát giữ line và nhịp tim runtime; mô hình `sim` không giàu hơn bo mạch tham chiếu
- [ ] Hiện thực trong firmware C (`esp32s3`): bảng `const` phong bì sinh từ `board.v1` trong flash (RB-4 của `docs/spec/hal_mcu_review.md`), ghi bền write-ahead vào NVS, tự tắt bằng TWDT và timer phần cứng, driver `digital.in`, I2C chỉ đọc, ADC
- [x] Hiện thực kiểm tra ràng buộc kênh `analog.in` với tiêu chí `numeric` và cấm trong `on_block.confirms` trong `neuroedge build` / `gate lint`; ghi mốc đọc và tính `age_ms` — *đạt cho `analog.in` (TSK-I2a-04): `check_analog_facts` ở `engine/compiler.py` (nối bằng `[sim.analog_facts]`), cấm `confirms` do bộ phân giải gate đã làm cho mọi tiêu chí `numeric`, mốc đọc `Fact.read_ms` ở `SimSession._analog_facts`; mốc đọc và `age_ms` của `digital.in` đạt (TSK-I2a-02, `engine/gate.py`, `engine/decision_tree.py`)*
- [ ] Thêm/điều chỉnh fixture và test: bộ test tương đương host Python ↔ firmware C cho phong bì và driver (RB-4); test SIGSTOP giám sát ngoài tiến trình
- [ ] Cập nhật dòng của RFC trong `docs/rfc/README.md` và một mục `CHANGELOG.md` `[Chưa phát hành]`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30; Q-62, 2026-10-01)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Các quyết định dưới đây **đã được gộp vào §3–§8**; mục này giữ lại làm hồ sơ quyết định (Q-57), và nếu còn chỗ lệch thì mục này thắng. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Tên API.** Nguyên thủy tên `digital.in` trong `[requires]`; khoá bo mạch `capabilities.digital_in`; phương thức HAL `digital_in(pin)` đặt cạnh `digital_out`; API cho agent là `digital.input("door_contact").level()`. *Vì sao:* cùng khuôn với `digital.out`, không đụng từ khoá `in` của Python; tên chân vẫn là tên logic (FR-HAL-06).
2. **Đọc thanh ghi trên I2C.** Cho phép đọc có địa chỉ thanh ghi (ghi con trỏ rồi repeated-start đọc) **chỉ** với thiết bị trong allowlist của bo mạch **và** thanh ghi nằm trong danh sách `readable_registers` bo mạch khai cho thiết bị đó; ngoài trường hợp đó, thiết bị trong allowlist chỉ được receive-byte. Địa chỉ ngoài allowlist **không bao giờ được đọc hay ghi** — chỉ được báo cáo có mặt qua read-byte thăm dò khi quét. Không có đường ghi dữ liệu nào. Quét bus chỉ bằng read-byte (TSK-N3-01). *Vì sao:* một số chip coi mọi lần ghi là lệnh; giới hạn lần ghi duy nhất vào con trỏ của thanh ghi đã khai là cách hẹp nhất vẫn đọc được cảm biến thật.
3. **Nếu spike ADC (TSK-N3-03) trượt:** `analog.in` được kiểm trên runner tự quản gắn ADC thật (Pi 5 + ADC I2C) hằng đêm, và **chặn tiêu chí ra của I2a** tới khi có bằng chứng đó. *Vì sao:* Q-53 đòi `analog.in` có mặt; một nguyên thủy chưa kiểm trên phần cứng không được phát hành.
4. **Lỗi và vết ghi.** Phong bì từ chối ⇒ lớp mới `EnvelopeRefusedError` (**NE1003**, lớp con của `ActionContractViolation`), sự kiện vết ghi `envelope_refused`, token không bị tiêu. Đọc hỏng (bus NACK, timeout, cảm biến mất) ⇒ `PerceptionUnavailableError` (NE5001) ⇒ tiêu chí chưa quyết ⇒ BLOCK. Chân hoặc thiết bị không khai ⇒ `BoardCapabilityError` (NE3001) lúc nạp. Sự kiện vết ghi: `digital_in`, `i2c_read`, `analog_in`. *Vì sao:* mỗi loại hỏng có một mã riêng để hậu kiểm, và không loại nào dẫn tới ALLOW.
5. **Khoá phong bì và cờ cơ cấu chấp hành** (review 2026-10-01 sửa lại). `window_s`, `max_on_ms_per_window`, `min_interval_ms` và `max_continuous_ms` (dùng chung cho RFC-0010, RFC-0011). Khai ở `[capabilities.digital_out.envelope.<tên_chân>]`. mọi chân `digital_out` mặc định là cơ cấu chấp hành, bắt buộc có phong bì. Chân chỉ là tín hiệu (không nối tải) khai trong mảng `signal_pins = [...]`. Bỏ `actuator = true`. Ba profile bậc 1 trong `boards/` phải thêm phong bì đủ rộng trong PR hiện thực. *Vì sao:* `digital_out.pins` là mảng chuỗi nên không có chỗ gắn thuộc tính `actuator`; mặc định là cơ cấu chấp hành để an toàn cao nhất, không bỏ sót tải vật lý.
6. **Phong bì sống qua khởi động lại** (review 2026-10-01 sửa lại). Tổng thời gian bật đã giữ trong cửa sổ được ghi bền trước khi bật (write-ahead): NVS trên `esp32s3`, tệp trạng thái trên `linux`; `sim` mô phỏng cùng luật. Sau khởi động, coi mọi lần bật đã ghi như xảy ra ngay trước lúc khởi động, chiếm ngân sách tới `window_s`; bản ghi hỏng hoặc thiếu thì coi cả cửa sổ đã dùng hết; vẫn chờ `min_interval_ms` trước lần bật đầu sau khởi động. Bỏ câu "bộ đếm cửa sổ nằm trong bộ nhớ". *Vì sao:* bộ đếm trong RAM bị xoá khi khởi động lại liên tục; ghi bền write-ahead và giả định xấu nhất đảm bảo phong bì không bị qua mặt bởi khởi động lại.
7. **Lệnh về phía an toàn không bao giờ bị chặn và `min_interval_ms` chỉ áp cho lệnh bật** (review 2026-10-01, Q-62). Lệnh `digital.out` `off` và các lệnh HAL tự phát khi hết `duration_ms`, hết `max_continuous_ms`, BLOCK, cắt lời, mất liên lạc, `hal.close()` không bao giờ bị chặn, không qua phong bì, không cần ALLOW hay token, không chờ `min_interval_ms` hay sau khởi động; `min_interval_ms` chỉ áp cho lệnh bật cơ cấu từ an toàn sang hoạt động. *Vì sao:* lệnh đưa cơ cấu về trạng thái an toàn phải luôn luôn được thực thi ngay lập tức, không được phép bị cản trở bởi bất kỳ cơ chế kiểm soát nào.
8. **Tự tắt bắt buộc và hoàn phần giữ trước** (review 2026-10-01, Q-62). Mọi lệnh bật trên chân có phong bì đều có thời hạn hữu hạn: HAL và firmware hẹn giờ tự tắt tại `min(thời hạn lệnh, max_continuous_ms)` (`on()` không thời hạn lấy `max_continuous_ms`); phong bì giữ trước thời hạn này trong `max_on_ms_per_window`, tắt sớm hoàn phần dư; `authorize` thất bại thì hoàn toàn bộ phần đã giữ. *Vì sao:* loại bỏ hoàn toàn khả năng bật vĩnh viễn ngoài tầm kiểm soát và không làm hao hụt ngân sách khi lệnh không được cấp quyền.
9. **Cưỡng chế phần cứng và giám sát ngoài tiến trình** (review 2026-10-01, Q-62). Firmware `esp32s3` cưỡng chế cùng luật phong bì từ bảng `const` trong flash (RB-4); hẹn giờ tự tắt không chỉ sống trong tiến trình có thể treo: `esp32s3` dùng TWDT + timer phần cứng (reset kéo chân về mức an toàn), `linux` dùng tiến trình giám sát riêng giữ line và nhịp tim runtime; SIGSTOP tiến trình runtime thì cơ cấu chấp hành tự về trạng thái an toàn trong thời hạn cộng biên. *Vì sao:* đảm bảo an toàn phần cứng độc lập với sự cố treo hay crash của tiến trình phần mềm runtime (RB-4).
10. **Ràng buộc dữ kiện `digital.in` và `analog.in` vào gate** (review 2026-10-01, Q-62). `digital.in` vào gate dạng dữ kiện `bool`, `analog.in` dạng tiêu chí `numeric` ([RFC-0009](0009-tieu-chi-so-numeric.md)), kèm mốc đọc để tính `age_ms`; `neuroedge build` kiểm `unit` trùng và `[min, max]` của kênh nằm trong `range` tiêu chí; `age_ms < 0` ⇒ BLOCK `criterion_unavailable`. *Vì sao:* chuẩn hoá giao diện dữ kiện vào walker, phát hiện lệch cấu hình sớm lúc build và loại bỏ dữ kiện có mốc đọc sai thời gian.
11. **Tuổi của `digital.in` và mốc của `min_interval_ms`** (review 2026-10-01, Q-62). `digital.in` đọc ngay lúc lượng giá, trần tuổi cố định `DIGITAL_IN_MAX_AGE_MS = 100` ⇒ quá trần là `criterion_unavailable`. `min_interval_ms` tính từ lúc lần bật trước kết thúc. `enable_pin` của RFC-0010, RFC-0011 miễn phong bì riêng và không gọi được từ agent. *Vì sao:* tiêu chí `bool` không có `max_age_ms`, nên cần một trần trong mã để đường đọc treo không cho ALLOW; tính từ lúc kết thúc là mốc bảo thủ hơn tính từ lúc bắt đầu.
