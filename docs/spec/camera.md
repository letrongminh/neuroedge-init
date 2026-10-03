# Camera `vision.in` — chế độ, camera ảo trên `sim`, V4L2 trên `linux`

**Trạng thái:** đặc tả chuẩn tắc (TSK-V1b-01, TSK-V1b-02). Hợp đồng gốc: [RFC-0012](../rfc/0012-nguyen-thuy-vision-in.md)
§3a, §3b, §3e, §3f; RFC-0013 §3f (mỗi bo mạch replay corpus của nguyên thủy nó mang); bất biến
`CHANGELOG.md` §3.3 #7 (`sim` không giàu hơn bo mạch nó soi). Hiện thực: `python/neuroedge/hal/vision.py`,
`hal/v4l2.py`, `hal/sim.py` · `hal/linux.py` (`vision_in`), `python/neuroedge/sim/vision/`. Phần *khung hình → dữ kiện
gate* (mô hình, cửa sổ, `vision_fact`, replay) là [`vision.md`](vision.md); tài liệu này là phần *camera*, tức
`Frame` đến từ đâu. Từ khoá **PHẢI**, **KHÔNG ĐƯỢC** mang nghĩa như RFC 2119.

## 1. Camera là một nguyên thủy mở rộng, có hợp đồng của riêng nó

`vision.in` là nguyên thủy mở rộng (RFC-0013 §3a): bo mạch khai hoặc không. Bo mạch khai năng lực bằng
`modes` (`board.v1`, `vision_in`); agent khai nhu cầu ở `[requires]`; `neuroedge build` đối chiếu; phiên mở camera
**đúng chế độ build đã chọn**. Hôm nay chỉ `sim-rpi5` và `linux-rpi5` khai `vision_in`: `sim-default` (soi Box-3)
**không có camera**, nên agent đòi `vision.in` bị từ chối lúc build ở đó (FR-HAL-05, tiêu chí ra I2a số 7).

## 2. `[requires] "vision.in"` — so khớp theo RFC-0012 §3b

```toml
[requires]
"vision.in" = { min_width = 640, min_height = 480, min_fps = 10.0, pixel_formats = ["yuyv", "mjpeg"] }
```

| Khoá | Kiểu | Ý nghĩa |
|:---|:---|:---|
| `min_width`, `min_height` | số nguyên ≥ 0 | chế độ phải rộng/cao ít nhất bằng |
| `min_fps` | số ≥ 0 (hữu hạn) | chế độ phải chạy ít nhất bằng |
| `pixel_formats` | danh sách trong `yuyv` · `mjpeg` · `rgb565` · `rgb888` · `gray8` | chế độ phải thuộc một trong các định dạng đó |

Bo mạch thoả khi **tồn tại ít nhất một chế độ** đủ mọi ngưỡng (`Requirement.failures`, `hal/vision.py`, một hàm
cho cả build lẫn phiên). Chế độ được chọn là chế độ **đầu tiên theo thứ tự bo mạch khai** thoả — tất định. Các điều sau
bị từ chối, không bị lờ đi: khoá lạ (một ngưỡng gõ sai là ngưỡng không có, nên build sẽ cho qua agent đòi nhiều hơn bo
mạch có), giá trị sai kiểu, định dạng ngoài enum đóng. Không chế độ nào thoả ⇒ `BoardCapabilityError` (`NE3001`) nêu chế
độ gần nhất và ngưỡng nó trượt (`vision.in … closest mode, 640x480 @ 30 fps rgb888, misses ['min_width 1920 > 640']`).

`[vision]` kéo theo `[requires] "vision.in"`; thiếu ⇒ build từ chối. Cùng với `[vision]`, build kiểm (RFC-0012 §3c, §8):
kiểu tiêu chí cùng tên khớp `kind`, không gate nào dùng `confidence_gte` trên dữ kiện thị giác, `present`/`count` luôn kèm
`confidence` cùng nhãn và vùng, mô hình đặt tên được, và không dữ kiện thị giác nào bị `[sim.*]` hay `[system_one]`
quyết thay (`check_vision`, `check_system_one`, `engine/compiler.py`).

## 3. Giao diện HAL

```python
camera = hal.vision_in(mode, called_from="…", clock=session_clock)   # một chế độ của bo mạch
frames = camera.read_available()   # mọi khung đến từ lần gọi trước, cũ nhất trước; có thể rỗng; không chặn
camera.close()
```

| Kiểu (`hal/vision.py`) | Ý nghĩa |
|:---|:---|
| `Mode` | `width`, `height`, `fps` (số thực), `pixel_format` — đúng một mục của `vision_in.modes` |
| `CameraFrame` | `seq` (số khung **của camera**), `captured_ms` (mốc HAL đọc, trên `clock` của phiên — cùng đồng hồ với `Fact.read_ms`), `pixels`, mô tả khung |
| `CameraUnavailable` | camera không giao được: biến mất, đứng, hết chuỗi, khung sai kích thước. Là lớp con của `PerceptionUnavailableError` (`NE5001`): không thêm mã lỗi |

`vision_in` chỉ mở chế độ **bo mạch khai**; chế độ khác bị từ chối (`BoardCapabilityError`). Camera **không bao giờ bịa khung**.
`captured_ms` đo bằng đồng hồ phiên: `captured_ms` của camera thật là lúc *lấy khung ra khỏi driver*, không phải lúc cảm biến
chụp — sai lệch là độ trễ của luồng chụp (vài ms) và làm tuổi khung trông **trẻ hơn** chút ít, không già hơn; trần 1000 ms và
`max_age_ms` của gate đủ rộng hơn sai lệch đó.

## 4. Camera ảo trên `sim` (TSK-V1b-02)

`sim` không đọc camera nào. Nó **phát lại** một chuỗi khung đã ghi trên đồng hồ phiên, trong một chế độ của bo mạch, và nó
được dựng để **không tốt hơn phần cứng nó thay**:

* chỉ chạy ở chế độ bo mạch khai, với `fps` của chế độ đó — khung thứ *k* sẵn sàng sau *k + 1* chu kỳ `1000 / fps` ms của
  đồng hồ phiên, không nhanh hơn;
* chế độ thô (`yuyv`, `rgb565`, `rgb888`, `gray8`) giao khung đúng `rộng × cao × byte/điểm` byte; khung sai kích thước không
  phải khung của camera này và camera báo `CameraUnavailable` (chế độ nén `mjpeg` nhận mọi kích thước);
* có **hàng đợi kiểu driver** `depth` khung (mặc định 4). Người đọc muộn thấy `depth` khung mới nhất và một **bước nhảy ở số
  khung** cho những khung đã bị ghi đè — đúng điều driver thật làm, và điều khởi động lại cửa sổ (RFC-0012 §9.9) — không phải
  khung cũ được trình bày như mới;
* **hết chuỗi thì camera mất**: giao nốt những khung nó đã chụp, rồi báo `CameraUnavailable` (`loop = true` mới lặp lại; chuỗi
  một khung lặp lại là camera đứng hình, mà nhận thức từ chối).

Nhãn mô hình tìm thấy trong khung là việc khác, phát lại từ kịch bản (`provider = "replay"`, `vision.md` §3.5); camera chỉ cấp khung.

```toml
[sim.vision]
source = "synthetic"      # hoặc thư mục khung, tương đối với agent.toml
frames = 90               # chỉ với synthetic: chuỗi dài bao nhiêu khung
loop   = false            # lặp lại chuỗi
depth  = 4                # hàng đợi: người đọc muộn còn thấy bao nhiêu khung
drop   = [7, 8]           # số khung camera làm mất (số khung nhảy qua)
```

`synthetic` sinh khung tất định, đúng kích thước chế độ, **mỗi khung khác nhau**. Thư mục khung: mỗi tệp thường là một khung, theo
thứ tự tự nhiên của tên (`2` trước `10`); đuôi tệp không được đọc. Thiếu `[sim.vision]` ở agent khai `[vision]` ⇒ phiên **không
khởi động** (`CameraUnavailable`): một mô phỏng đưa ra khung của hư không sẽ biến mọi agent thị giác thành đạt.

## 5. `linux`: Video4Linux2 không phụ thuộc (TSK-V1b-01)

`LinuxHAL.vision_in` đọc một node capture V4L2 (`/dev/videoN`) bằng Python thuần — `ctypes` cho cấu trúc, `fcntl.ioctl` cho lời gọi,
`mmap` cho bộ đệm (`hal/v4l2.py`). **Không thêm phụ thuộc nào** (không OpenCV, GStreamer, `av`): `import neuroedge` không bao giờ cần
chúng, và ai muốn đường ống nặng hơn viết nó thành adapter `VisionModel`, nơi nó chỉ nhận byte khung. Cấu trúc theo bố cục LP64 của
UAPI (`sizeof(v4l2_buffer) == 88`; `hal/v4l2.py::LAYOUT`) — đúng với `linux-rpi5` (aarch64) và runner x86_64; userspace 32 bit bị từ chối
(`layout_problem`), không đưa kernel cấu trúc sai cỡ.

**Node là lựa chọn của máy, không đoán.** Một Pi có cả chục node `/dev/video*` mà đa số không phải camera: `NEUROEDGE_LINUX_CAMERA=/dev/video0`
(hoặc `LinuxHAL(camera=…)`). Không chọn ⇒ `CameraUnavailable` nói cách chọn. Replay không đọc máy, nên không mở camera.

**Giao thức** (`V4L2Camera`): `QUERYCAP` (node phải là capture và stream được) → `S_FMT` và `S_PARM` xin **đúng chế độ khai** → bốn bộ đệm
`mmap` → `STREAMON`. Câu trả lời của driver **PHẢI là chính chế độ đó**: driver làm tròn kích thước, chọn định dạng khác hay chạy
tốc độ khác (sai quá 2 %) bị từ chối bằng lỗi ba phần — bo mạch đã khai một chế độ, agent build theo nó, và tương đương giữa target
(RFC-0012 §3f) không chấp nhận "gần đúng". Một luồng chụp lấy mọi khung ngay khi sẵn sàng, gắn đồng hồ phiên, giữ 64 khung mới nhất
cho phiên lấy qua `read_available()`; số khung là `sequence` của driver nên khung kernel làm rơi là một bước nhảy mà nhận thức thấy.

**Fail-closed.** Thiết bị biến mất, lỗi đọc, hoặc **không khung nào trong `stall_ms` (mặc định 1000 ms)** ⇒ `read_available()` ném
`CameraUnavailable`. Khung driver gắn `V4L2_BUF_FLAG_ERROR` bị bỏ chứ không sửa; khung thô sai kích thước kết thúc camera. `close()` dừng luồng,
`STREAMOFF`, thả bộ đệm và node; idempotent, và `LinuxHAL.close()` gọi nó.

**Kiểm.** `tests/test_v4l2.py` chạy cả giao thức với một driver giả (kích thước cấu trúc, số ioctl, thứ tự lời gọi, từ chối chế độ, số khung,
khung lỗi, thiết bị chết, đứng hình, đóng). Trên kernel thật: job CI `linux-hal` nạp `vivid` (`scripts/setup_vivid.sh`: driver video ảo
của kernel, cùng ioctl và bộ đệm `mmap` với camera thật, mẫu thử có dấu thời gian nên không hai khung giống nhau) và chạy
`python/tests_linux/test_camera_v4l2.py`. Tệp đó được viết trên máy không phải Linux: **chưa chạy trên kernel nào ở lúc viết**.

## 6. Từ camera tới gate

`SimSession` dựng, với agent có `[vision]`, một `VisionFeed` (`sim/vision/feed.py`): camera của chế độ build đã chọn, `VisionPipeline` của
`vision.md`, và đăng ký hàm `facts(tree)` vào `Conversation.fact_sources`. Ngay **trước mỗi lần lượng giá gate** có tiêu chí thị giác:

1. mọi khung camera giao từ lần trước đi vào `VisionPipeline.push`, theo thứ tự; bước nhảy số khung khởi động lại cửa sổ;
2. pipeline ghi một `vision_fact` cho mỗi dữ kiện tree cần và trả những dữ kiện đọc được;
3. mọi tiêu chí thị giác của tree **không đọc được** được đưa cho engine là `None` — "không có dữ kiện", engine chặn `criterion_unavailable`
   thay vì hỏi nguồn khác (System One sẽ bị hỏi, và có thể trả lời từ lời người nói điều chỉ camera được nói).

Gate không có tiêu chí thị giác thì không chạy mô hình. Dữ kiện thị giác thắng `[sim.facts]` cùng tên, nên phiên từ chối nạp nếu có trùng.
Phiên mở camera **lúc nạp**, sau khi xin line GPIO: camera không mở được (không có node, driver từ chối chế độ, không có chuỗi ghi trên `sim`)
⇒ lỗi ba phần, các line được thả, phiên không tồn tại — agent cần mắt không khởi động khi mù.

## 7. Mất camera ⇒ chặn (RFC-0012 §3e)

| Tình huống | Điều xảy ra |
|:---|:---|
| Camera báo `CameraUnavailable` (mất, đứng, hết chuỗi, khung sai) | sự kiện `camera_unavailable {reason}`, **cửa sổ bị xoá**, dữ kiện chưa quyết ngay (`window_size`), gate chặn `criterion_unavailable` — không chờ khung cũ già đi |
| Camera im lặng nhưng chưa quá `stall_ms` | khung cũ già đi: `stale` (trần 1000 ms) hoặc `max_age_ms` của tiêu chí `numeric` ⇒ chặn |
| Khung giống hệt nhau dù driver gắn mốc mới | `frozen` ⇒ chặn (nhận thức, `vision.md` §4.3) |
| Mất khung (số khung nhảy) | cửa sổ bắt đầu lại; chưa đủ `min_frames` ⇒ `window_size` ⇒ chặn |
| Chưa đủ khung khi khởi động | `window_size` ⇒ chặn |

Không nhánh nào cho ALLOW, không nội suy từ khung trước, không có giá trị mặc định "không thấy người".

## 8. Vết ghi, riêng tư, corpus

* `camera_unavailable` `{reason}` (nhóm `perception`, `vision.in`): camera không giao được ở lần lượng giá này. Replay bỏ qua nó — phán quyết
  `criterion_unavailable` đi cùng được tính lại từ `vision_fact` chưa quyết.
* Vết ghi mang **`vision_ref` (băm + kích thước) và nhãn**, không bao giờ điểm ảnh; `metadata.raw_capture` chỉ bật khi cố ý (`vision.md` §1.3).
* **Corpus** (RFC-0013 §3f mục 7): `fixtures/traces/vision/*.json` — ba phiên của agent mẫu `fixtures/agents/gate-watch` trên `sim-rpi5` (cho
  qua, chặn, mất camera), sinh bằng `scripts/gen_vision_traces.py` (`--check` là cái test chạy). `neuroedge verify` replay chúng trên **mọi** bo
  tham chiếu khai `vision.in` (`sim/sim-rpi5`, `linux/linux-rpi5`), từ nhãn đã ghi, không camera, không mô hình; bo không khai (`sim-default`)
  bỏ qua chứ không thất bại, vì đây không phải vết ghi chuẩn mực. Replay hai target phải ra cùng phán quyết và lệnh chân.

## 9. Chưa làm

* Golden suy luận theo sha256 mô hình và kiểm sai số `tolerance` giữa các target (TSK-V1b-04) — mệnh đề "mô hình thấy giống nhau" của RFC-0012 §3f.
* Giải mã `mjpeg`: camera giao nguyên byte nén; adapter mô hình tự giải mã nếu cần.
* Camera trên `esp32s3` (TSK-I3a-04): không có HAL; replay của thiết bị chỉ chạy vết ghi chuẩn mực.
* Nhiều camera mỗi phiên, đa mặt phẳng (`V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE`), CSI qua libcamera: node phải là capture đơn mặt phẳng.
