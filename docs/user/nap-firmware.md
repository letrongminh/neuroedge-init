# Nạp firmware cho agent của bạn lên `esp32s3`

> **Mã task:** TSK-I3-01 · TSK-S6-01…04 · **Yêu cầu:** FR-CLI-02, FR-TGT-03, FR-OTA-01…04.
> Đây là **nơi duy nhất** mô tả thủ tục nạp và thủ tục OTA; cú pháp lệnh `build` ở
> [`CHANGELOG.md`](../../CHANGELOG.md) §2.3.

## 1. Firmware này làm gì, và chưa làm gì

`neuroedge build --target esp32s3` sinh từ agent của bạn một project ESP-IDF đầy đủ. Gate của
agent chạy trên chip: cây `NETR` trong flash (RFC-0003), walker C, sổ token dùng một lần. Lúc khởi
động, firmware tự kiểm trước khi bật runtime gate:

- mọi cây trong flash nạp được và đúng là cây máy tính đã biên dịch cho gate đó (digest);
- walker C quyết từng phép kiểm của agent — dữ kiện đổi từng tiêu chí một, nguồn dữ kiện mất
  mạng, người xác nhận (RFC-0006) — **đúng như engine trên máy tính** đã quyết lúc build;
- token của mỗi action chỉ cho đúng các chân của action đó, mỗi chân một lần.

Lệch một chỗ ⇒ `NE_SELFTEST FAIL …` và firmware dừng: không runtime gate, không action.

**Chưa có**, nói thẳng để bạn không mất thời gian:

- Chưa chân GPIO nào động: HAL trên chip là TSK-S4-01. Bảng chân mang tên chân, chưa có số GPIO.
- Chưa âm thanh (I5). ESP-SR chưa được link: giấy phép của nó chưa được xác minh (`TODOS.md` #17).
- Firmware còn replay ba vết ghi chuẩn mực lúc khởi động (TSK-S4-09) — không liên quan tới agent
  của bạn, nhưng cho `neuroedge verify --targets esp32s3 --port …` kiểm walker trên chính chip đó.
- **Chưa Secure Boot, chưa mã hóa flash, chưa nút ngắt micro** (TSK-S6-05). OTA xác minh chữ ký
  bằng khóa nằm trong ảnh đang chạy, nên người có cáp vẫn thay được cả khóa lẫn firmware. Hạ cấp bị
  chặn bằng mốc nước cao phiên bản trong NVS (eFuse anti-rollback chỉ có khi bật Secure Boot —
  TSK-S6-05). Xem §6.

## 2. Cần gì

| Thứ | Ghi chú |
|:---|:---|
| `neuroedge` | Cài theo [`huong-dan.md`](huong-dan.md) §1. Wheel mang sẵn mã nguồn firmware |
| ESP-IDF **v5.4** | [Hướng dẫn cài của Espressif](https://docs.espressif.com/projects/esp-idf/en/v5.4/esp32s3/get-started/), hoặc Docker `espressif/idf:v5.4` |
| ESP32-S3-BOX-3 + cáp USB-C | Bo mạch tham chiếu duy nhất (bất biến 6, `CHANGELOG.md` §3.3). Chưa có: §5 |

## 3. Sinh project từ agent

```bash
cd my-agent                                     # thư mục có agent.toml
neuroedge build --target esp32s3 --board esp32s3-box-3
```

Thành công ⇒ dòng `firmware: build/esp32s3 — ESP-IDF project, …`. Trong `build/esp32s3/`:

| Đường dẫn | Nội dung |
|:---|:---|
| `main/`, `components/ne_gate/`, `components/ne_trace/`, `CMakeLists.txt`, `sdkconfig.*`, `partitions.csv` | Mã nguồn firmware, chép nguyên văn — giống nhau cho mọi agent |
| `components/ne_agent/` | Phần của agent: cây `NETR` mỗi gate (`gates/`), bảng gate, chân, action, phép kiểm self-test kèm phán quyết của engine (`ne_agent.c`) |
| `version.txt` | Phiên bản app của agent này — ESP-IDF đọc thành `PROJECT_VER`; cách đặt và tăng: §6.6 |
| `.neuroedge-build` | Danh sách tệp lần build này đã ghi |

**Đừng sửa tay `components/ne_agent/`.** Đổi gate hay action thì chạy lại `build`: cùng agent cho
cùng từng byte; tệp lần trước ghi mà lần này không còn thì bị xoá; `build/`, `sdkconfig` của
`idf.py` giữ nguyên. Thư mục `build/esp32s3/` có sẵn mà không do `neuroedge build` ghi, hay có liên
kết tượng trưng (symlink) ở một đường dẫn build ghi vào ⇒ từ chối: build không bao giờ ghi xuyên qua
liên kết ra ngoài project.

Agent không hợp bo mạch (thiếu chân, thiếu năng lực — FR-HAL-04), key gate không phải định danh C
(`unlock-door`), `[agent] name`/`version` có ký tự điều khiển hay xuống dòng, hay quá 32 chân ⇒ in mọi
vấn đề (cách đọc: `CHANGELOG.md` §2.4), **mã 1, không ghi gì**.

## 4. Build và nạp lên Box-3

```bash
cd build/esp32s3
idf.py set-target esp32s3                       # một lần; xoá cấu hình cũ
idf.py build
idf.py -p <cổng> flash monitor                  # Linux /dev/ttyACM0 · macOS /dev/cu.usbmodem… · Windows COMn
```

Box-3 đưa console qua USB-Serial-JTAG hay UART chưa chốt được khi chưa có bo mạch (`TODOS.md` #35);
`idf.py` tự dò cổng nếu bỏ `-p`. Trong monitor, tìm theo đúng thứ tự:

```text
I (…) neuroedge_core: Agent: my-agent@0.1.0 · 1 gate(s), 1 action(s), 1 pin(s)
NE_SELFTEST PASS walker=<n> token=<n>
NEUROEDGE_HEAP_JSON {"schema":"neuroedge.heap/v1",…}
NE_TRACE DONE sessions=4
```

`NE_SELFTEST PASS` là bằng chứng gate của agent chạy trên chip. Ghi các phiên của thiết bị thành vết
ghi trên máy tính: `neuroedge record --target esp32s3 --port <cổng>` (cần `neuroedge[serial]`).

## 5. Chưa có bo mạch: Espressif QEMU

Cùng project, thêm lớp cấu hình `sdkconfig.qemu` (bỏ Wi-Fi, `device_id = "qemu"`):

```bash
cd build/esp32s3
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.qemu" set-target esp32s3
idf.py build
python "$IDF_PATH/tools/idf_tools.py" install qemu-xtensa    # một lần
idf.py qemu monitor
```

QEMU không có GPIO, I2S, Wi-Fi hay PSRAM của Box-3 (Q-21): nó chứng minh gate và self-test, không
chứng minh phần cứng. Quay lại bo mạch thì chạy lại `idf.py set-target esp32s3` (không có `-D`).

## 6. Cập nhật OTA (FR-OTA-01…04)

Hai khe A/B. Bản mới chỉ được coi là đáng tin **sau khi vượt self-test gate**; nếu không nó bị
đánh dấu hỏng và thiết bị tự quay về bản trước, không cần can thiệp (kể cả khi ảnh mới panic
trước khi kịp tự kiểm). Không cần dịch vụ hay tài khoản NeuroEdge: chỉ một HTTP(S) endpoint mở.
Đây là cấu hình **tùy chọn**; bản build mặc định không có đường OTA (§6.5).

Hai ràng buộc cứng của đường OTA:

- **Chữ ký + rollback là bắt buộc.** OTA chỉ được biên dịch khi bật đủ xác minh chữ ký trên bản
  cập nhật (`CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`) **và** rollback
  (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`); thiếu một trong hai thì Kconfig từ chối bật
  `CONFIG_NEUROEDGE_OTA`. Lớp `sdkconfig.ota` bật cả hai.
- **OTA không bao giờ ghi bootloader.** Nó chỉ ghi khe app (`esp_https_ota` →
  `esp_ota_set_boot_partition`). Bootloader biết rollback phải nạp **một lần bằng cáp** từ project
  build với lớp OTA (§6.2); các bản OTA về sau không đụng tới nó.

### 6.1 Máy chủ cập nhật

Máy chủ chỉ cần trả về **một tệp**: ảnh `app` đã ký — trong `build/esp32s3/build/`, tên theo
project (mặc định `neuroedge-esp32s3-box3.bin`). Bất kỳ máy chủ tĩnh nào cũng được:

```bash
python3 -m http.server 8070        # ví dụ, chạy từ thư mục chứa ảnh
```

URL cấu hình trên thiết bị bằng một trong hai cách:

| Cách | Ở đâu | Đổi khi nào |
|:---|:---|:---|
| Kconfig | `idf.py menuconfig` → **NeuroEdge OTA** → *Update URL* | Lúc build |
| NVS | namespace `ne_ota`, khóa `url` | Lúc chạy, không cần build lại |

URL rỗng = tắt kiểm tra cập nhật. HTTP trần được phép vì **chữ ký mới là phần toàn vẹn**, không
phải TLS; HTTP không mã hóa nên đừng đặt bí mật trong URL. HTTPS cũng chạy: client gắn CA bundle
(`CONFIG_MBEDTLS_CERTIFICATE_BUNDLE`) để xác thực máy chủ.

### 6.2 Khóa ký — của bạn, không bao giờ trong kho mã

Ảnh nạp phải được ký bằng **đúng khóa đã ký ảnh đang chạy** (RSA-3072, định dạng Secure Boot v2).
Tạo khóa một lần và cất nó ngoài kho mã (sao lưu hai chỗ; mất khóa = hết đường OTA):

```bash
cd build/esp32s3
idf.py secure-generate-signing-key secure_boot_signing_key.pem
```

Build với lớp OTA sẽ tự ký app bằng khóa đó (`CONFIG_SECURE_BOOT_SIGNING_KEY`, mặc định tên tệp
trên, tính từ thư mục project):

```bash
idf.py -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.ota" set-target esp32s3
idf.py build
```

Muốn ký một ảnh đã build sẵn thay vì ký lúc build
(`CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=n`):

```bash
espsecure.py sign_data --version 2 --keyfile secure_boot_signing_key.pem \
    -o app-signed.bin app.bin
```

Đổi khóa thì thiết bị đang chạy **không nhận** ảnh mới (khóa trong ảnh đang chạy không khớp); khi
đó phải nạp lại qua cáp. Tệp khóa bị `.gitignore` chặn (`secure_boot_signing_key.pem`, `*.pem`);
đừng gỡ.

OTA chỉ đổi khe app; bootloader (kèm `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`) không bao giờ được
cập nhật qua mạng. Lần nạp **đầu tiên** bằng cáp phải là bản build có lớp `sdkconfig.ota`
(`idf.py -p <cổng> flash`), nếu không bootloader không có logic rollback và ảnh OTA hỏng sẽ không
tự quay về. Các lần OTA sau không đụng tới bootloader.

### 6.3 Một lần cập nhật diễn ra thế nào

1. Thiết bị tải ảnh, đọc app descriptor, rồi so phiên bản với **mốc nước cao** lưu trong NVS:
   phiên bản bằng hoặc **thấp hơn mốc bị bỏ qua** — hạ cấp không bao giờ được ghi vào khe nào.
   Mốc đơn điệu (chỉ tăng) và so theo số; eFuse anti-rollback chỉ có khi bật Secure Boot
   (TSK-S6-05).
2. `esp_https_ota` ghi vào khe còn trống rồi xác minh (cấu trúc + chữ ký). Sai chữ ký ⇒ từ chối,
   **không đổi khe**.
3. Đặt khe mới làm khe khởi động rồi reset. Ảnh mới khởi động ở trạng thái *chờ xác nhận*.
4. Self-test gate chạy. Đạt ⇒ `NE_OTA VALID` và ảnh được xác nhận (mốc nước cao được cập nhật).
   Không đạt ⇒ `NE_OTA INVALID`, đánh dấu hỏng và reset; bootloader quay về ảnh trước.
5. Ảnh mới reset/panic trước bước 4 ⇒ bootloader tự quay về ảnh trước ở lần khởi động kế tiếp.
   Nếu ảnh **treo** mà không reset: task watchdog không được cấu hình panic (`CONFIG_ESP_TASK_WDT_PANIC`
   mặc định `n`), nên máy không tự khởi động lại — rollback chỉ xảy ra ở lần **mất điện rồi bật lại**
   kế tiếp.
6. Phiên bản vừa bị quay về **bị chặn**: mốc nước cao không hạ; muốn sửa thì phát hành phiên bản
   cao hơn (§6.6).

### 6.4 Đọc dấu vết trên UART

Mỗi sự kiện in đúng một dòng ở cột 0, bắt đầu bằng `NE_OTA`. **Định dạng từng dòng do
[`ne_ota_policy.c`](../../targets/esp32s3/components/ne_ota/src/ne_ota_policy.c) định nghĩa** — nguồn
duy nhất, gồm tên đầy đủ của mọi trường. Bảng dưới chỉ nói mỗi loại dòng có nghĩa gì:

| Dòng | Nghĩa |
|:---|:---|
| `NE_OTA CHECK` | Bắt đầu kiểm tra cập nhật (URL in ra đã bỏ `user:password@`) |
| `NE_OTA DOWNLOADED` | Ảnh đã tải và xác minh chữ ký xong |
| `NE_OTA SWITCH` | Khe mới thành khe khởi động; thiết bị reset |
| `NE_OTA VALID` | Self-test đạt; ảnh được xác nhận |
| `NE_OTA INVALID` | Self-test hỏng; ảnh bị đánh dấu và reset |
| `NE_OTA ROLLBACK` | Lần cập nhật trước đã bị quay về; thiết bị đang chạy bản ghi ở trường `to` |
| `NE_OTA REJECTED` | Từ chối trước khi đổi khe (chữ ký, HTTP, descriptor, …) |
| `NE_OTA SKIP` | Không nạp (trùng phiên bản, hạ cấp, bản vừa bị quay về, không đọc được phiên bản) |

### 6.5 Build không OTA (mặc định) và thử trên QEMU

Không thêm `sdkconfig.ota` thì `CONFIG_NEUROEDGE_OTA=n`: ảnh **không có đường tải**, không thể
nhận OTA — đúng cho phát triển cục bộ. Không có lớp `sdkconfig.ota`, cũng không có yêu cầu khóa.

Kịch bản đầy đủ trên QEMU (`scripts/qemu_ota.sh`) dựng máy chủ HTTP, ký bằng khóa dùng-một-lần
dưới `targets/esp32s3/build/` (bị git bỏ qua), rồi kiểm: bản factory vẫn chạy; bản mới hợp lệ
được nạp, khởi động và xác nhận; ảnh sai khóa bị từ chối; ảnh hỏng bị quay về. Số đo kích thước
của bản OTA ở [`docs/reports/memory_spike_report.md`](../reports/memory_spike_report.md) §4.1.
QEMU chỉ chứng minh logic phân vùng và chữ ký — danh sách đầy đủ ở
[`docs/spec/simulation_coverage.md`](../spec/simulation_coverage.md) §4.

QEMU chạy đường mạng bằng NIC `open_eth` (`CONFIG_NEUROEDGE_OTA_ETH`, chỉ có trong lớp QEMU).
Trên **Box-3 thật**, đường Wi-Fi của `main.c` mới chỉ dựng STA (`esp_wifi_set_mode(WIFI_MODE_STA)`
rồi `esp_wifi_start()`) mà **chưa** gọi `esp_wifi_connect()` và chưa có provisioning (SSID, mật
khẩu, CA): hôm nay chưa có đường OTA nào chạy trên bo mạch — chỉ đường `open_eth` của QEMU.

### 6.6 Phiên bản app — đặt và tăng

Phiên bản app là `[agent] version` trong `agent.toml`, phải là **MAJOR.MINOR.PATCH**: ba số thập
phân, không số 0 đứng đầu. Build `--target esp32s3` từ chối mọi thứ khác **trước khi ghi gì**, vì
thiết bị đọc nó để chặn hạ cấp. `neuroedge build --target esp32s3` ghi nó vào `version.txt` của
project; ESP-IDF đọc tệp đó thành `PROJECT_VER` — không có nó, project ngoài git báo phiên bản
`1`. Firmware tham chiếu trong kho: `targets/esp32s3/version.txt` = `0.1.0`.

Mỗi lần phát hành: sửa `[agent] version` trong `agent.toml`, build lại, và tăng ít nhất số cuối —
`0.1.0` → `0.1.1` (sửa lỗi), `0.1.0` → `0.2.0` (tính năng). Thiết bị chỉ nhận phiên bản **cao
hơn mốc nước cao** (§6.3 bước 1); phát lại phiên bản cũ không có tác dụng.

## 7. Khi lỗi

| Thấy | Nghĩa | Làm gì |
|:---|:---|:---|
| `neuroedge build` mã 1 | Agent không build được cho `esp32s3`; không có gì được ghi | Sửa từng vấn đề đã in (ở đâu · vì sao · cách xử lý) |
| `NE_SELFTEST FAIL load <gate>` | Cây trong flash hỏng, hoặc không phải cây của gate đó | Build lại từ `neuroedge build`; không sửa tay `components/ne_agent/` |
| `NE_SELFTEST FAIL check <i> <gate>` | Walker trên chip không quyết như engine trên máy tính | Build lại từ đầu; còn lỗi là lỗi firmware — mở issue kèm log monitor |
| Không có dòng `NE_SELFTEST` | Firmware không tới được self-test | Xem log boot phía trên trong monitor |
| `NE_OTA REJECTED reason=signature` | Ảnh không ký bằng khóa của ảnh đang chạy (hoặc thiếu chữ ký) | Ký lại bằng đúng khóa (§6.2), rồi thử lại |
| `NE_OTA REJECTED reason=http` | Không mở được URL, hoặc máy chủ trả 404/403 | Kiểm URL và máy chủ từ một máy khác; nhớ HTTP trần chỉ in trong `NE_OTA CHECK` |
| `NE_OTA REJECTED reason=descriptor` | URL trả về tệp không phải ảnh app | Trỏ URL đúng tệp `.bin` đã ký |
| `NE_OTA SKIP` | Không nạp: phiên bản trùng hay **thấp hơn mốc nước cao**, hoặc là bản vừa bị quay về | Phát hành phiên bản **cao hơn** (§6.6), không phát lại bản cũ |
| `NE_OTA INVALID` rồi `NE_OTA ROLLBACK` | Ảnh mới hỏng self-test (hoặc reset trước khi xác nhận) và đã bị quay về | Sửa firmware, tăng phiên bản, phát hành lại |
