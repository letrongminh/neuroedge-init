# RFC-0007: `digital.in`, bus I2C chỉ đọc, `analog.in` và phong bì an toàn theo chân

| | |
|:---|:---|
| **Mã RFC** | 0007 |
| **Tiêu đề** | Ba nguyên thủy đầu vào mới (`digital.in`, I2C chỉ đọc, `analog.in`) và phong bì an toàn khai ở `board.v1` |
| **Hợp đồng bị ảnh hưởng** | `board.v1` *(thêm khoá `digital_in`, `i2c`, `analog_in` và khối `envelope`)* · **không** đụng `gate.v1` |
| **Yêu cầu PRD liên quan** | FR-HAL-01, FR-HAL-04, FR-HAL-05 |
| **Người đề xuất** | — |
| **Ngày mở** | 2026-09-30 |
| **Trạng thái** | ⏳ Nháp — chưa mở PR · câu hỏi mở đã quyết (§9, Q-57) |
| **Người phê duyệt** | **Kỹ thuật trưởng — bắt buộc.** Phong bì chạm đường tới chân vật lý (§5), và §4 nêu một điểm siết chặt lược đồ cần chữ ký |

> **Khi nào cần RFC:** `CONTRIBUTING.md` §3 — sửa `schemas/*.json`. RFC này sửa `schemas/board.v1.json`.
> Quyết định nền: `neuroedge-prd.md` §15 Q-52 (MVP là v1.0 đầy đủ gồm bốn gói nguyên thủy, một bản phát hành,
> trượt ngày thay vì cắt), Q-53 (bốn gói bắt buộc trên cả ba target bậc 1; **`analog.in` chuyển từ RFC-motion
> sang RFC này**), Q-55 (NeuroBrain vào MVP). Dàn ý gốc: `roadmap/draft-ke-hoach-mo-rong-robot-fofoca.md`
> Phụ lục A và `roadmap/neuroedge-design-neurobrain.md` §7, §8. Task: TSK-N0-03 (soạn RFC này), TSK-N2-01
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

HAL thêm `HardwareAbstractionLayer.digital_in(pin, called_from=...) -> bool`; chân phải có trong `digital_in.pins`, sai tên ⇒ `BoardCapabilityError` ba phần. Đọc **không di chuyển gì** nên không cần token (như `sensor.read`), và được ghi thành sự kiện để replay nạp lại; `sim` phát lại giá trị đã ghi (`set_sensor`-tương đương cho chân), không giàu hơn bo mạch tham chiếu.

### 3b. Bus I2C chỉ đọc

```toml
[capabilities.i2c]
buses = [{ id = "i2c0", devices = [{ name = "ads1015", address = 0x48 }] }]
```

- **Quét bằng read-byte**: thăm dò địa chỉ chỉ bằng thao tác đọc; **không** dùng quick-write.
- **Allowlist thiết bị**: chỉ địa chỉ có trong `devices` mới đọc được; địa chỉ thấy khi quét nhưng không có trong allowlist chỉ được **báo cáo**, không đọc.
- Không có thao tác ghi nào trong API. Công cụ `lab_read` của NeuroBrain (`roadmap/neuroedge-design-neurobrain.md` §6) đọc chân qua `digital.in` của RFC này; cờ `[lab]` mặc định tắt và không nới allowlist.
- Trên `linux`, kiểm thử dựng trên `i2c-stub` (Khối N3, roadmap); `sim` chỉ phát lại giá trị đã ghi, không quét thật.

### 3c. `analog.in`

```toml
[capabilities.analog_in]
channels = [{ name = "supply_v", unit = "V", min = 0.0, max = 5.0, resolution_bits = 12 }]
```

Trả số kèm đơn vị và thang khai; giá trị ngoài `[min, max]` là lỗi đọc, không bị cắt lặng lẽ. Ngưỡng an toàn trên giá trị này **không** nằm ở nguyên thủy mà ở tiêu chí `numeric` của gate ([RFC-0009](0009-tieu-chi-so-numeric.md)). **Có điều kiện**: đường kiểm thử trên `linux` phụ thuộc spike TSK-N3-03 (chip ADC I2C có driver hwmon trên `i2c-stub`, runner tắt `CONFIG_IIO`). Spike trượt không có nghĩa bỏ `analog.in` (Q-52, Q-53 buộc có mặt trên cả ba target): nghĩa là kiểm thử ADC thật chuyển sang runner tự host — xem §9.

### 3d. Phong bì an toàn theo chân — khai ở `board.v1`

```toml
[capabilities.digital_out.envelope.porch_light]
window_s              = 3600      # cửa sổ trượt
max_on_ms_per_window  = 1800000   # tổng thời gian bật tối đa trong cửa sổ
min_interval_ms       = 2000      # giới hạn tần suất giữa hai lệnh
```

Hook nằm trong `HardwareAbstractionLayer.digital_out` (`python/neuroedge/hal/__init__.py`), được tiêm vào như `authorize`. Thứ tự (TSK-N2-01): `require_pin → envelope → authorize → record`. Phong bì đứng **trước** `authorize` nên lệnh bị từ chối **không tiêu token**. Check-và-reserve là một bước nguyên tử (TSK-N2-02) để hai lệnh đồng thời không cùng qua ngân sách còn lại. Không khai `envelope` cho một chân ⇒ hành vi y hệt hôm nay.

### 3e. Mã đi kèm

`PRIMITIVES` tách thành lõi và mở rộng, `_CAPABILITY_KEYS` thêm ba khoá: chi tiết ở [RFC-0013](0013-nguyen-thuy-tuy-chon-va-nhieu-bo-tham-chieu.md).

## 4. Ảnh hưởng tương thích

| Hạng mục | Ảnh hưởng |
|:---|:---|
| Tệp đang hợp lệ có còn hợp lệ? | Có với ba profile trong `boards/` (không dùng khoá mới). **Điểm siết chặt:** `digital_in`, `i2c`, `analog_in` hôm nay được nhận ở dạng *bất kỳ* vì `capabilities` không đóng; sau RFC chúng có hình dạng bắt buộc. Không tệp nào trong kho dùng chúng; kỹ thuật trưởng phải xác nhận việc này không cần `board.v2` (RFC-0002 §9.1 đã cảnh báo cùng bẫy: sửa hình dạng sau khi phát hành mới là siết chặt) |
| Tệp đang không hợp lệ có trở nên hợp lệ? | Có — profile khai ba khoá mới đúng hình dạng và khối `envelope` |
| Cần tăng phiên bản lược đồ (`v1` → `v2`)? | Đề xuất **không**, với điều kiện hình dạng ở §3 được chốt **trước** khi có profile ngoài kho dùng chúng |
| Ảnh hưởng tới mã băm / chữ ký gate đã phát hành? | Không — `gate.v1` không đổi |
| Ảnh hưởng tới ba tệp vết ghi chuẩn mực? | Không — phán quyết không đổi khi không cấu hình phong bì |
| Gate nào trong `digests.lock` đổi digest? | Không gate nào |
| Bố cục `NETR` hoặc walker C phải đổi? | Không |
| Đáp án nào của corpus tool call (`expected_results.yaml`) đổi? | Không — không có phong bì thì `digital_out` cùng thứ tự lỗi (hợp đồng hồi quy `neuroedge-design-neurobrain.md` §7.1). Phong bì từ chối thêm ca mới ở corpus riêng |

## 5. Ảnh hưởng an toàn

- **Gate không lỏng hơn theo đường nào**: `gate.v1`, ngữ nghĩa phân giải và năm nguyên tắc kế thừa (Phụ lục B.5) không đổi. Phong bì là **lớp chặn thứ hai, độc lập**, chỉ thêm khả năng từ chối.
- **Gate vẫn thuần (bất biến số 4):** tích luỹ thời gian bật và tần suất nằm ở HAL, không ở gate. Đây là lý do khai ở `board.v1` chứ không thêm trường vào gate.
- **Mặc định fail-closed:** lệnh vượt phong bì bị từ chối trước `authorize`; không có chế độ "cảnh báo rồi cho qua". Không dùng cờ `[lab]` làm ngoại lệ phong bì.
- **Giới hạn phần mềm khi tắt:** phong bì không cứu được chân khi tiến trình bị SIGKILL hay crash (libgpiod thả line); phần đó thuộc T0 crash-safe (điện trở kéo xuống/watchdog) ở `neuroedge-design-neurobrain.md` §2.3 và RFC-0011.
- **Đầu vào không có quyền ghi:** `digital.in`, `analog.in` không di chuyển chân; I2C không có thao tác ghi trong API. Rủi ro còn lại là *đọc lộ thông tin*, giảm bằng allowlist.
- Cần kỹ thuật trưởng duyệt vì chạm đường tới chân vật lý (`digital_out`).

## 6. Phương án đã xem xét và bác bỏ

| Phương án | Lý do bác bỏ |
|:---|:---|
| Mở rộng `sensor.read` (quét bus, mức logic, ADC) | Xem §2: vô hướng có tên vs. tập chưa đặt tên; làm mờ `[requires]`; ADC cần thang và đơn vị |
| Khai phong bì trong `gate.v1` | Tích luỹ thời gian là trạng thái, phá tính thuần của gate (bất biến số 4); gate chia sẻ qua registry không biết phần cứng |
| Kiểm phong bì **sau** `authorize` | Lệnh bị từ chối đã tiêu token; sửa lỗi sau mất một token vô ích |
| I2C cho phép ghi có allowlist thanh ghi | Mở đường thay đổi trạng thái thiết bị ngoài mọi gate; để dành cho RFC riêng nếu có nhu cầu thật |
| Để `analog.in` trong RFC-motion | Q-53: `analog.in` là gói đầu vào độc lập với `motion.*`; ràng buộc lên số đọc dùng tiêu chí `numeric`, không cần chuyển động |

## 7. Bằng chứng kiểm chứng

- [ ] Ví dụ hợp lệ: profile `boards/` khai `digital_in`, `i2c`, `analog_in`, `envelope` (bo mạch tham chiếu, RFC-0013)
- [ ] Phản chứng: khoá sai hình dạng (`pins` không phải mảng), `address` ngoài 0x03..0x77, `min > max`, `window_s` <= 0
- [ ] Test: lệnh thứ hai trong `min_interval_ms` bị từ chối và **token không bị tiêu**; tổng thời gian vượt cửa sổ bị từ chối; hai lệnh đồng thời không cùng qua ngân sách (TSK-N2-02); không khai `envelope` ⇒ corpus `fixtures/tool_calls/` y hệt cũ
- [ ] Quét `i2c-stub`: thiết bị ngoài allowlist chỉ được liệt kê, đọc bị từ chối
- [ ] `neuroedge gate lint` và `neuroedge verify` vẫn xanh; ba vết ghi chuẩn mực không đổi

## 8. Việc phải làm khi chấp thuận

- [ ] Cập nhật `schemas/board.v1.json`
- [ ] Cập nhật Phụ lục tương ứng trong `neuroedge-proposal.md` và FR-HAL-01 ở `neuroedge-prd.md`; quyết định mới cấp `Q-N` ở §15
- [ ] Cập nhật `neuroedge-roadmap.md` (TSK-N0-03 xong; TSK-N2-01, TSK-N2-02, TSK-N3-03)
- [ ] Hiện thực trong `python/neuroedge/hal/` (`board.py`, `__init__.py`, `sim.py`, `linux.py`); mô hình `sim` không giàu hơn bo mạch tham chiếu
- [ ] Thêm/điều chỉnh fixture và test
- [ ] Cập nhật dòng của RFC trong `docs/rfc/README.md` và một mục `CHANGELOG.md` `[Chưa phát hành]`

## 9. Quyết định cho các câu hỏi mở (Q-57, 2026-09-30)

Chủ sản phẩm uỷ quyền quyết các câu hỏi mở theo nguyên tắc **an toàn cao nhất**: giữa hai phương án, chọn phương án fail-closed và khó dùng sai hơn, kể cả khi nó tốn công hơn. Mục này **thay** mọi đoạn đề xuất trái với nó ở §3; khi mở PR RFC, gộp nội dung vào §3. Chấp thuận RFC vẫn cần chữ ký kỹ thuật trưởng (`CONTRIBUTING.md` §3).

1. **Tên API.** Nguyên thủy tên `digital.in` trong `[requires]`; khoá bo mạch `capabilities.digital_in`; phương thức HAL `digital_in(pin)` đặt cạnh `digital_out`; API cho agent là `digital.input("door_contact").level()`. *Vì sao:* cùng khuôn với `digital.out`, không đụng từ khoá `in` của Python; tên chân vẫn là tên logic (FR-HAL-06).
2. **Đọc thanh ghi trên I2C.** Cho phép đọc có địa chỉ thanh ghi (ghi con trỏ rồi repeated-start đọc) **chỉ** với thiết bị trong allowlist của bo mạch **và** thanh ghi nằm trong danh sách `readable_registers` bo mạch khai cho thiết bị đó; mọi thiết bị khác chỉ receive-byte. Không có đường ghi dữ liệu nào. Quét bus chỉ bằng read-byte (TSK-N3-01). *Vì sao:* một số chip coi mọi lần ghi là lệnh; giới hạn lần ghi duy nhất vào con trỏ của thanh ghi đã khai là cách hẹp nhất vẫn đọc được cảm biến thật.
3. **Nếu spike ADC (TSK-N3-03) trượt:** `analog.in` được kiểm trên runner tự quản gắn ADC thật (Pi 5 + ADC I2C) hằng đêm, và **chặn tiêu chí ra của I2a** tới khi có bằng chứng đó. *Vì sao:* Q-53 đòi `analog.in` có mặt; một nguyên thủy chưa kiểm trên phần cứng không được phát hành.
4. **Lỗi và vết ghi.** Phong bì từ chối ⇒ lớp mới `EnvelopeRefusedError` (**NE1003**, lớp con của `ActionContractViolation`), sự kiện vết ghi `envelope_refused`, token không bị tiêu. Đọc hỏng (bus NACK, timeout, cảm biến mất) ⇒ `PerceptionUnavailableError` (NE5001) ⇒ tiêu chí chưa quyết ⇒ BLOCK. Chân hoặc thiết bị không khai ⇒ `BoardCapabilityError` (NE3001) lúc nạp. Sự kiện vết ghi: `digital_in`, `i2c_read`, `analog_in`. *Vì sao:* mỗi loại hỏng có một mã riêng để hậu kiểm, và không loại nào dẫn tới ALLOW.
5. **Khoá phong bì** (dùng chung cho RFC-0010, RFC-0011): `window_s`, `max_on_ms_per_window`, `min_interval_ms` và thêm **`max_continuous_ms`** — trần một lần bật, độc lập với `arguments` của gate. Bảng phong bì là tuỳ chọn cho chân tín hiệu, **bắt buộc** cho mọi chân nối cơ cấu chấp hành (khai bằng `actuator = true`). *Vì sao:* giới hạn phần cứng phải đứng được cả khi gate viết lỏng.
6. **Khởi động lại.** Sau khi tiến trình (hoặc firmware) khởi động, mỗi chân có phong bì phải chờ `min_interval_ms` trước lần bật đầu tiên. *Vì sao:* bộ đếm cửa sổ nằm trong bộ nhớ; không có luật này, khởi động lại liên tục sẽ xoá phong bì.
