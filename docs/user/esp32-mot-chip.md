# ESP32-S3 một mình: bộ não và gate trên một chip

> **Quyết định:** Q-79 · **Task:** TSK-I2f-10 (giai đoạn 1, xong), TSK-I2f-11, I2f-12 (chờ bo) ·
> **Rủi ro:** [`threat_model.md`](../spec/threat_model.md) §2l. Đây là **nơi duy nhất** mô tả cách
> dùng bảng điều khiển serial, safe mode và nơi lưu bí mật trên chip. Thủ tục nạp firmware:
> [`nap-firmware.md`](nap-firmware.md).

## 1. Ba cách chạy bộ não, và cách này ở đâu

| Cách chạy | Bộ não ở đâu | Gate ở đâu | Cô lập | Trạng thái |
|:---|:---|:---|:---|:---|
| NeuroEdge Cloud (Q-76) | instance riêng trên cloud (microVM) | hộp tại nhà | hai máy | ⏸ I2f |
| Tự host (Q-76, Q-78) | NeuroClaw trên board Linux rẻ | hộp tại nhà | hai tiến trình | demo chạy được |
| **Một chip (Q-79)** | **ESP32-S3** | **cùng chip đó** | **không** — nhãn `risk=single_chip` | giai đoạn 1 |

Một chip là rẻ nhất: chỉ một ESP32-S3, chat và duyệt trên Telegram. Đổi lại, bộ não và gate chung một không
gian bộ nhớ: lỗi trong mã bộ não có thể chạm tới gate. Vì vậy mọi tool call của LLM vẫn đi qua `ne_gate`, và
việc không hoàn tác cần nút trên bo hoặc callback của đúng chủ nhà (giai đoạn 3).

## 2. Giai đoạn 1 có gì (chạy trên QEMU, chưa trên bo)

- **Boot guard.** Mỗi lần khởi động tự đếm trong NVS. Đứng được 30 giây sau khởi động thì bộ đếm về 0. Ba lần
  liên tiếp không đứng được (crash, tự reset, mất điện) thì lần thứ tư vào **safe mode**.
- **Safe mode.** Chỉ còn bảng điều khiển serial: không mạng, không runtime gate, không cập nhật. Ảnh OTA đang
  chờ không bao giờ được đánh dấu hợp lệ ở đây, nên lần reset sau bootloader quay về ảnh cũ.
- **Cấu hình và bí mật** trong phân vùng NVS riêng `ne_config`: Wi-Fi, token bot, owner ID, LLM.
- **Bảng điều khiển serial** qua cáp USB, ở cả chế độ thường lẫn safe mode.
- **Stack guard** trong CI.

Bộ não cho chip đã có riêng: **NeuroClaw-ESP**, trong repo [`neuroclaw`](https://github.com/letrongminh/neuroclaw)
thư mục `esp32/` (MIT). Cùng workspace và cùng tool với NeuroClaw trên Linux hay cloud: trò chuyện Telegram chỉ
với chủ nhà, trí nhớ `memory/MEMORY.md`, ghi chú ngày, tệp `USER.md`/`SOUL.md`, skills, cuộc trò chuyện giữ qua
khởi động lại kèm tóm tắt phần cũ, nhắc lịch `cron`, heartbeat, tìm kiếm web và đọc trang (không chạm mạng nhà),
tự nhắn hay gửi tệp cho chủ nhà, và một LLM dự phòng khi LLM chính lỗi.
Nó đã chạy trên QEMU với một gate giả; bảng so sánh với bản Go ở `esp32/README.md` của repo đó.

Chưa có trong firmware NeuroEdge: Wi-Fi kết nối, nối NeuroClaw-ESP vào `ne_gate` (TSK-I2f-11, I2f-12). Các khoá
đã lưu chưa được ai đọc cho tới lúc đó.

## 3. Bảng điều khiển serial

Mở bằng `idf.py monitor` (hoặc `screen /dev/ttyUSB0 115200`). Dấu nhắc là `neuroedge>`, hoặc
`neuroedge(safe)>` trong safe mode.

| Lệnh | Làm gì |
|:---|:---|
| `status` | Chế độ, số lần khởi động, kiểu lưu trữ, heap trống, stack còn lại |
| `config list` | Mọi khoá; bí mật hiện `<secret>`, khoá chưa đặt hiện `<unset>` |
| `config get <khoá>` | Một khoá |
| `config set <khoá> <giá trị>` | Đặt khoá thường |
| `config set <khoá bí mật>` | Hỏi giá trị ở **dấu nhắc ẩn**: không hiện chữ, không vào lịch sử lệnh |
| `config unset <khoá>` | Xoá một khoá |
| `bootguard` · `bootguard clear` | Xem bộ đếm · đặt lại (rồi `reboot` để rời safe mode) |
| `reboot` | Khởi động lại |
| `factory-reset confirm` | Xoá mọi cấu hình và bí mật, đặt lại bộ đếm, khởi động lại |
| `help` | Danh sách lệnh |

Không lệnh nào bật chân hay gọi tool.

**Khoá:**

| Khoá | Bí mật | Luật |
|:---|:---:|:---|
| `wifi.ssid` | | 1–32 byte |
| `wifi.pass` | ✓ | 8–64 byte |
| `telegram.token` | ✓ | `<số>:<chuỗi>` như @BotFather đưa |
| `telegram.owner` | | ID người dùng Telegram, chỉ chữ số (lấy từ @userinfobot) |
| `llm.url` | | `https://…` (hay `http://…`, kèm nhãn `risk=cleartext_url`: key đi dạng rõ) |
| `llm.key` | ✓ | không dấu cách |
| `llm.model` | | không dấu cách |

Gõ bí mật thẳng trên dòng lệnh bị từ chối (`reason=inline_secret`): chữ đã gõ hiện trên màn hình và vào lịch
sử lệnh. Ví dụ đặt token:

```text
neuroedge> config set telegram.token
telegram.token (hidden, Enter to finish):
NE_CONFIG SET key=telegram.token storage=plaintext risk=readable_flash
```

## 4. Bí mật lưu thế nào

| Firmware build với | Phân vùng `ne_config` | Nhãn |
|:---|:---|:---|
| `sdkconfig.defaults` (mặc định) | dạng rõ: ai cầm bo đọc được token và key | `risk=readable_flash` |
| `sdkconfig.defaults;sdkconfig.secure` | mã hoá (khoá trong phân vùng `nvs_keys`, flash mã hoá); mã hoá hỏng thì không lưu gì | — |

`sdkconfig.secure` bật **mã hoá flash: lần khởi động đầu đốt eFuse, không làm lại được**. Chế độ phát triển
vẫn nạp lại được bằng `idf.py encrypted-flash monitor`. Chỉ bật khi bạn đã sẵn sàng giữ bo đó cho việc này:

```bash
cd targets/esp32s3
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.secure" set-target esp32s3 build
idf.py flash monitor   # lần đầu: bootloader mã hoá flash rồi khởi động lại
```

CI chỉ build lớp này, không thử trên chip.

## 5. Safe mode: ra sao, ra thế nào

```text
NE_BOOT count=4 max=4 mode=safe reason=panic
NE_CONSOLE READY mode=safe
SAFE MODE: too many boots in a row did not stay up. ...
neuroedge(safe)> bootguard clear
NE_BOOT CLEARED
neuroedge(safe)> reboot
```

`reason=` là lý do reset của chip (`poweron`, `sw`, `panic`, `task_wdt`, `brownout`…), để biết vì sao nó lặp.
Nếu nguyên nhân còn đó, ba lần sau lại vào safe mode. Số lần đổi được qua `CONFIG_NEUROEDGE_BOOT_GUARD_MAX`
(mặc định 4, như zclaw).

## 6. Thử trên QEMU

```bash
. $IDF_PATH/export.sh
cd targets/esp32s3
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3 build
cd ../.. && python3 scripts/qemu_console.py targets/esp32s3/build
```

Script khởi động sáu lần trên cùng ảnh flash: ba lần không đứng được, lần bốn vào safe mode và nhập cấu hình qua
bảng điều khiển, lần năm bình thường và cấu hình còn nguyên, rồi factory reset. Log từng lần ở
`targets/esp32s3/build/console-test/`.

## 7. Nguồn

Boot guard, cách mã hoá NVS và ý tưởng stack guard port từ [zclaw](https://github.com/tnm/zclaw) (MIT); khung
bảng điều khiển theo [MimiClaw](https://github.com/memovai/mimiclaw) (MIT). Ghi nhận: [`NOTICE`](../../NOTICE)
mục 6, 7.
