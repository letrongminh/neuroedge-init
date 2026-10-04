# Ba kit phần cứng: từ hộp tới chạy thật

> **Mã task:** TSK-I2b-01 · **Yêu cầu:** FR-DX-05, FR-DX-09 · **Quyết định:** Q-52.
> Trang này là **nơi duy nhất** của quy trình chung "từ hộp tới chạy thật" và của danh sách việc
> **chưa kiểm trên phần cứng thật**. Mỗi kit có trang riêng cho BOM và sơ đồ đấu dây.

> **Đọc trước.** Mọi BOM, sơ đồ và bước ở đây **chưa được kiểm trên phần cứng thật**. Kho chỉ chứng
> minh được phần mềm: `sim` (mọi test), `linux` trên chân GPIO ảo của kernel (`gpio-sim`, job `linux-hal`
> của CI) và firmware dựng được từ agent. Việc dựng thiết bị thật từ BOM và sơ đồ rồi đo là một bước
> **của người** (`docs/reports/uoc-luong-mvp-2026-09-30.md`, dòng I2b: kiểm BOM và sơ đồ đấu dây trên Pi). Mạch điện sai có thể làm
> hỏng linh kiện hoặc gây nguy hiểm: kiểm bằng đồng hồ vạn năng trước khi cấp nguồn cho tải.

## 1. Ba kit

| Kit | Mẫu (`--template`) | Thiết bị | Gate | `sim` | `linux` (Pi 5) | `esp32s3` (Box-3) |
|:---|:---|:---|:---|:---|:---|:---|
| [Khoá cửa villa](kit-khoa-cua-villa.md) | `villa-concierge` | Khoá điện của một cửa | `unlock_door@1.2.0` (`gates/`, đã khoá) | chạy | khoá + gate chạy trên `linux`, nhưng agent **không build** trên `linux-rpi5` (cần AEC, bo khai `aec = false`: `NE3003`) | build ra firmware |
| [Trợ lý giọng nói trong nhà](kit-tro-ly-giong-noi.md) | `home-voice` | Đèn + cảm biến chuyển động + loa | `light_on`, `light_off` (`fixtures/agents/home-voice/gates/`, đã khoá) | chạy | phiên chỉ chạy khi khai nguồn `motion`, và `light_off` luôn chặn (xem trang kit) | build ra firmware |
| [Giám sát phòng máy](kit-giam-sat-nha-may.md) | `factory-monitor` | Quạt xả (hoặc van xả) + còi báo động theo nhiệt độ | `vent_on`, `vent_off`, `alarm_on`, `alarm_off` (`fixtures/agents/factory-monitor/gates/`, đã khoá) | chạy | chạy với LM75 qua hwmon | **không build**: agent khai `supported = ["sim", "linux"]` |

Tên và cơ cấu của kit thứ ba theo `roadmap/neuroedge-proposal.md` §1.6 mục 3 ("kích hoạt van xả an toàn
hoặc còi báo động"). Kho giữ tên mẫu `factory-monitor` (đổi tên một mẫu công khai là thay đổi vỡ của CLI,
`docs/spec/python_api.md` §6) và chỉnh cơ cấu: chân `gate_relay` là **một rơ-le tải xả** — quạt xả hoặc
cuộn van xả điện từ, cùng một chân, cùng bốn gate — và chân `porch_light` là **còi báo động** (trước kia
tài liệu gọi nhầm là đèn). Phần "cảm biến khí ga" của proposal **chưa có**: gate so dải nhiệt, không so
nồng độ khí (kênh `analog.in` có từ I2a nhưng kit này chưa dùng).

## 2. Quy trình chung

Mỗi bước dùng được ngay cả khi bạn chưa có phần cứng: dừng ở bước nào cũng có kết quả kiểm chứng được.

### Bước 0. Cài

```bash
pip install neuroedge            # hoặc: cd python && pip install -e '.[dev]'
neuroedge board list             # thấy sim-default, sim-rpi5, linux-rpi5, esp32s3-box-3
```

### Bước 1. `sim` — không cần phần cứng, không cần mạng, không cần khoá

```bash
neuroedge new villa --template villa-concierge      # hoặc home-voice, factory-monitor
cd villa
neuroedge build --target sim --board sim-default
neuroedge run -c "mở cửa phòng 101"                 # lệnh mẫu của từng kit: xem trang kit
neuroedge test                                      # test an toàn của dự án: 0 = đạt
```

Dự án sinh ra có sẵn gate, action, ngữ pháp lệnh, test và thư mục `traces/`. `neuroedge test` khẳng
định điều chân **thật sự làm** (lệnh của chân ảo), không chỉ phán quyết.

### Bước 2. Vết golden — chứng cứ rằng quyết định không đổi

Mỗi kit có một bộ vết ghi chuẩn trong `fixtures/traces/kits/`, **sinh bằng
`scripts/gen_kit_traces.py`, không sửa tay**, và `neuroedge verify` phát lại chúng trên mọi bo tham
chiếu khai đủ năng lực:

```bash
neuroedge verify --targets sim            # phát lại trên sim-default và sim-rpi5
neuroedge verify --targets sim,linux      # thêm linux-rpi5, trên chân của kernel (job linux-hal)
python scripts/gen_kit_traces.py --check  # vết trong kho có đúng là thứ agent mẫu ghi ra không
```

`neuroedge new --template <kit>` chép hai vết của kit vào `traces/golden/` của dự án; kiểm bằng
`neuroedge replay traces/golden/<tệp>.json --agent agent.toml --golden traces/golden/<tệp>.json`.

Chỉ chạy lại `python scripts/gen_kit_traces.py` (không `--check`) khi agent mẫu, gate hay hợp đồng cảm
biến đổi **có chủ đích**; diff của các tệp JSON là nội dung cần review.

### Bước 3. `linux` — Raspberry Pi 5

1. Dựng mạch theo sơ đồ ở trang kit, **không cắm tải thật** lúc đầu: chỉ gắn LED và điện trở lên chân
   rơ-le để thấy chân đổi mức.
2. Mỗi chân số của agent là một **line GPIO tìm theo tên**: line phải mang đúng tên chân của bo
   (`door_lock`, `porch_light`, `gate_relay`; `boards/linux-rpi5.toml`). Trên Pi, đặt tên bằng
   device-tree overlay (thuộc tính `gpio-line-names`) hoặc truyền `line_names={...}` khi dựng `LinuxHAL`
   từ mã Python; CLI không có cờ ánh xạ tên. *Chưa kiểm trên Pi thật.*
3. Cài phần mở rộng và chạy:

   ```bash
   pip install 'neuroedge[linux]'
   neuroedge run --target linux --agent agent.toml -c "bật đèn"
   ```

   Không có `/dev/gpiochip*` thì HAL **dừng với lỗi** chứ không im lặng (Q-16): runner hay máy cấu hình
   sai không bao giờ "xanh giả".
4. Cảm biến đọc qua sysfs (hwmon/IIO), tìm theo tên, khai bằng biến môi trường — ví dụ
   `NEUROEDGE_LINUX_SENSORS="temperature=hwmon:lm75/temp1"`. Cảm biến không đọc được ⇒ gate **chặn**
   (`criterion_unavailable`), không bao giờ đọc ra một giá trị mặc định.
5. Mọi test của kit trên kernel thật nằm ở `python/tests_linux/test_kit_*.py`; CI chạy chúng bằng
   `scripts/setup_gpio_sim.sh` + `scripts/setup_i2c_stub.sh` (job `linux-hal`). Trên Pi thật, các test
   này **chưa chạy**.

### Bước 4. `esp32s3` — ESP32-S3-BOX-3

```bash
neuroedge build --target esp32s3 --board esp32s3-box-3
# rồi idf.py build / flash theo docs/user/nap-firmware.md
```

Thủ tục build, nạp và OTA ở [`nap-firmware.md`](nap-firmware.md) — nơi duy nhất. Giới hạn hiện nay,
nói thẳng: firmware **chưa điều khiển chân GPIO nào** (HAL trên chip là TSK-S4-01) và bảng chân của bo
mang tên chân, **chưa có số GPIO**; vì vậy sơ đồ phần ESP32-S3 dùng tên chân, và bạn không thể nối rơ-le
vào firmware này để thấy nó đóng. Bo Box-3 là loại duy nhất được hỗ trợ (bất biến 6, `CHANGELOG.md`
§3.3); nó không có sẵn rơ-le, cổng I2C ra ngoài hay đầu vào PIR nào được kho kiểm.

## 3. Quy tắc an toàn của mọi kit

- **Tải mạnh qua rơ-le.** Chân của bo không bao giờ nối thẳng vào khoá, quạt, van hay còi: luôn qua mạch
  rơ-le (hoặc MOSFET) có cách ly. Nguồn của tải tách khỏi nguồn của bo.
- **Mặc định tắt.** Chân thả nổi (reset, runtime chết) phải ra trạng thái an toàn: kéo xuống bằng điện
  trở, hoặc dùng mạch rơ-le mà đầu vào hở là tắt. Kho không kiểm được điều này; mạch của bạn phải bảo
  đảm (RFC-0010 §9.2 mô tả cùng nguyên tắc cho các chân enable).
- **Phong bì an toàn.** Mỗi chân `digital.out` có phong bì thời gian trong profile bo mạch
  (`[capabilities.digital_out.envelope.*]`): `door_lock` xung tối đa 60 s liên tục; `gate_relay` tối đa
  60 s liên tục và 10 phút bật mỗi giờ; `porch_light` tối đa 10 phút liên tục. Phong bì cắt lệnh vượt mức
  dù gate đã cho phép. Lệnh **tắt** (`off`) không bao giờ bị chặn (RFC-0007, Q-62).
- **Không có số liệu thì chặn.** Mọi cảm biến mất, hỏng hay ngoài dải ⇒ gate chặn lệnh nguy hiểm, không
  hỏi; lệnh theo hướng an toàn (bật quạt, bật còi) vẫn chạy.

## 4. Chưa kiểm trên phần cứng thật

| Hạng mục | Tình trạng |
|:---|:---|
| Mọi BOM (linh kiện mô tả theo chức năng và thông số, không có mã hàng, giá hay nhà bán) | chưa kiểm; cần người dựng thử |
| Mọi sơ đồ đấu dây | chưa kiểm; tên chân đúng với `boards/*.toml` (test `test_kits.py`), phần còn lại của mạch chưa |
| `linux` trên Pi 5 thật | chỉ kiểm trên `gpio-sim` + `i2c-stub` + `lm75` (CI); job nightly trên Pi chưa có kit |
| Mức kích của rơ-le (active-high hay active-low) | chưa kiểm; chọn mạch kích mức cao hoặc khai active-low ở device-tree |
| Đặt tên line GPIO bằng device-tree overlay trên Pi 5 | chưa kiểm |
| `esp32s3`: điều khiển chân, đọc cảm biến, âm thanh | chưa có (TSK-S4-01, I5); firmware dựng được và tự kiểm gate lúc khởi động |
| Nguồn `motion` (PIR) trên `linux` | chưa có: kernel không có driver hwmon/IIO cho PIR nối GPIO, và số đọc sysfs không phải đúng/sai nên `room_empty` chưa xác định |
| Âm thanh trên Pi 5 (AEC, I2S HAT) | profile khai `aec = false`; kit khoá cửa không build trên `linux-rpi5` vì thế |

Phát hiện khi dựng thật ⇒ ghi vào `TODOS.md`, không sửa trang này cho khớp với điều chưa đo.
