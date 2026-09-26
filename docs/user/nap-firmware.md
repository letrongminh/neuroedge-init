# Nạp firmware cho agent của bạn lên `esp32s3`

> **Mã task:** TSK-I3-01 · **Yêu cầu:** FR-CLI-02, FR-TGT-03. Đây là **nơi duy nhất**
> mô tả thủ tục nạp; cú pháp lệnh `build` ở [`CHANGELOG.md`](../../CHANGELOG.md) §2.3.

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

## 6. Khi lỗi

| Thấy | Nghĩa | Làm gì |
|:---|:---|:---|
| `neuroedge build` mã 1 | Agent không build được cho `esp32s3`; không có gì được ghi | Sửa từng vấn đề đã in (ở đâu · vì sao · cách xử lý) |
| `NE_SELFTEST FAIL load <gate>` | Cây trong flash hỏng, hoặc không phải cây của gate đó | Build lại từ `neuroedge build`; không sửa tay `components/ne_agent/` |
| `NE_SELFTEST FAIL check <i> <gate>` | Walker trên chip không quyết như engine trên máy tính | Build lại từ đầu; còn lỗi là lỗi firmware — mở issue kèm log monitor |
| Không có dòng `NE_SELFTEST` | Firmware không tới được self-test | Xem log boot phía trên trong monitor |
