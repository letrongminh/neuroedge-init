# Hướng dẫn sử dụng — NeuroEdge làm được gì và thử thế nào

Tài liệu này dành cho người muốn **dùng** NeuroEdge: maker, lập trình viên nhúng, người làm sản phẩm.
Nó trả lời năm câu hỏi, theo đúng thứ tự:

1. NeuroEdge là gì (§1).
2. Nó chạy được ở đâu, và mỗi nơi đã sẵn sàng tới mức nào (§2).
3. Cài thế nào (§3).
4. Mỗi nhóm năng lực làm được gì, cần gì, còn giới hạn gì (§4–§5).
5. Muốn tự tay thử thì làm từng bước ra sao (§6).

Gặp lỗi thì xem §7.

Tài liệu này mô tả **năng lực**, không lặp lại cú pháp đầy đủ của từng lệnh. Cú pháp, mọi tuỳ chọn và
đầu ra kỳ vọng nằm ở một nơi duy nhất: [`CHANGELOG.md`](../../CHANGELOG.md) §2.3. Tiến độ theo từng
task nằm ở [`trang-thai.md`](trang-thai.md). Gặp một mã viết tắt lạ (`FR-*`, `Q-N`, `TSK-*`, `I3`…),
tra ở [`thuat-ngu.md`](thuat-ngu.md).

---

## 1. NeuroEdge là gì

Một chatbot trả lời sai thì người dùng bấm "tạo lại". Một agent điều khiển thiết bị vật lý mà sai thì
chốt cửa đã mở, quạt đã tắt, và không có nút "tạo lại". NeuroEdge giải quyết đúng chỗ đó.

**Gate.** Mọi lệnh ra phần cứng phải đi qua một *gate*: một chính sách an toàn viết bằng YAML, có tên,
có phiên bản, kế thừa được từ gate khác. Gate đọc các dữ kiện của lúc đó (khách có đúng phòng không,
phòng máy đang nóng tới đâu, ai đang ra lệnh) và cho một trong ba phán quyết:

| Phán quyết | Nghĩa | Ví dụ |
|:---|:---|:---|
| **ALLOW** | Cho phép; chân GPIO được điều khiển | Khách phòng 101 mở cửa phòng 101 |
| **BLOCK** kèm **hỏi lại** | Chưa cho; hỏi người có mặt xác nhận trước | Tắt quạt khi phòng máy đang nóng |
| **BLOCK** | Từ chối; có thể chuyển cho người thật (lễ tân) | Khách phòng 101 đòi mở cửa phòng 202 |

**Lời gọi chỉ là yêu cầu.** Một LLM, một agent khác qua MCP, hay một câu nói đều chỉ *xin* làm một hành
động; gate mới là nơi quyết định. Trong mã, chân GPIO chỉ động được bên trong `c.do()` khi có một
phán quyết hợp lệ, và phán quyết đó dùng được đúng một lần.

**Không chắc thì chặn (fail-closed).** Gate không thẩm định được — lỗi, quá hạn, mất mạng, dữ kiện thiếu —
thì kết quả là BLOCK, không bao giờ là ALLOW.

**Vết ghi.** Mọi phán quyết được ghi vào một *vết ghi* (trace) theo lược đồ cố định. Vết ghi phát lại
được: NeuroEdge tính lại từng phán quyết từ dữ kiện đã ghi và so với lần chạy gốc, mà không động vào
thiết bị hay gọi model nào.

**Cùng một gate, ba môi trường.** Cùng tệp gate đó chạy trên trình mô phỏng (`sim`), trên máy Linux
(`linux`, ví dụ Raspberry Pi 5) và trên chip ESP32-S3 (`esp32s3`, bo mạch ESP32-S3-BOX-3), không rẽ
nhánh logic theo môi trường.

> **NeuroEdge không phải chức năng an toàn được chứng nhận** — không có mức SIL (IEC 61508) hay PL
> (ISO 13849), hai chuẩn chứng nhận an toàn chức năng. Gate không thay thế
> nút dừng khẩn cấp hay khoá liên động phần cứng. Sản phẩm đang ở giai đoạn phát triển nội bộ, chưa
> phát hành ra ngoài.

---

## 2. Chạy được ở đâu, sẵn sàng tới mức nào

Bảng dưới là bức tranh tổng. Chi tiết của từng ô nằm trong §4 và §5.

| Môi trường | Là gì | Hôm nay chạy được | Chưa có |
|:---|:---|:---|:---|
| **`sim`** — trình mô phỏng | Thiết bị ảo trên máy tính của bạn: chốt cửa, đèn, quạt, cảm biến, màn hình, micro và loa ảo | **Đầy đủ**: gate, gõ lệnh, trang web theo dõi, vết ghi, thoại từ tệp WAV, model AI thật, MCP | — |
| **`linux`** — máy Linux | Chân GPIO thật của kernel, cảm biến hwmon/IIO, framebuffer, micro/loa qua PipeWire | Gõ lệnh, thoại từ tệp WAV, MCP, đọc cảm biến, vẽ màn hình — **đã kiểm trên phần cứng ảo** (gpio-sim, `i2c-stub` + `lm75`, `vkms`) trong CI | Chưa chạy trên Raspberry Pi 5 thật (bo mạch chưa về); micro và loa thật chưa kiểm trên phần cứng; chưa có trang web theo dõi |
| **`esp32s3`** — chip | Firmware ESP-IDF cho ESP32-S3-BOX-3 | Gate của agent chạy và tự kiểm lúc khởi động, vết ghi qua UART, so phán quyết với máy tính, cập nhật OTA có ký — **đã kiểm trên QEMU** (máy ảo của Espressif) | Chưa có bo mạch; chưa chân GPIO nào động; chưa có âm thanh, Wi-Fi thật, màn hình thật |

Chưa có bo mạch thật nào trong tay đội: Box-3 và Raspberry Pi 5 đang chờ về (tiến độ ở
[`trang-thai.md`](trang-thai.md)). Mọi thứ có dấu "đã kiểm trên phần cứng ảo" hay "trên QEMU" nghĩa là
logic đã được chứng minh, còn phần điện (chân thật, âm thanh thật, mạng thật) thì chưa.

---

## 3. Cài đặt

**Chưa có bản phát hành ra ngoài.** PyPI mở ở increment I6 (công khai). Hôm nay có hai cách:

- Từ mã nguồn, theo [`python/README.md`](../../python/README.md): tạo venv trong `python/` rồi
  `pip install -e '.[dev]'`. Lệnh `neuroedge` nằm ở `python/.venv/bin/`.
- Từ wheel nội bộ của một increment, khi đội đưa cho bạn.

Yêu cầu: **Python 3.11 trở lên**. Bản cài cơ bản chạy được toàn bộ `sim` mà không cần mạng hay khoá.
Mỗi năng lực cần thêm thư viện được tách thành một phần mở rộng, cài khi cần:

| Phần mở rộng | Để làm gì | Mục |
|:---|:---|:---|
| `neuroedge[mcp]` | Máy chủ MCP, Claude Desktop, MCP server bên ngoài cho System 2 | §4.6, §4.4 |
| `neuroedge[cloud]` | LLM thật cho System 2 (LiteLLM) | §4.4 |
| `neuroedge[linux]` | Chân GPIO thật trên Linux (libgpiod) | §5.1 |
| `neuroedge[audio]` | Micro và loa thật trên Linux (sounddevice) | §5.1 |
| `neuroedge[wake]` | Từ đánh thức bằng openWakeWord (mô hình là của bạn) | §4.5 |
| `neuroedge[serial]` | Đọc vết ghi qua cổng serial của bo mạch | §5.2 |

Ví dụ: `pip install -e '.[mcp,cloud]'`.

---

## 4. Năng lực lõi — không cần phần cứng

Mọi năng lực ở đây chạy trên `sim`, tức là trên máy tính của bạn; mục nào chạy thêm được trên `linux`
hay `esp32s3` thì ghi rõ. Mỗi mục trả lời: làm được gì · cần gì · giới hạn. Mục nào cần cài thêm một phần mở rộng thì ghi
tên phần mở rộng đó (`neuroedge[mcp]`…); danh sách phần mở rộng ở §3.

### 4.0 NeuroEdge Studio: mọi năng lực trong một trang

`neuroedge studio` mở một ứng dụng web cục bộ (chỉ `127.0.0.1`, không cần mạng) với bảy màn: phiên trực tiếp (gõ,
và nói qua micro với `--mic`), gate và ô thử nhanh, vết ghi và phát lại, kiểm chứng (`verify`), thiết bị ESP32-S3
(ảnh giao diện, QEMU, OTA), MCP, và cấu hình agent. Song ngữ Việt/Anh. Hợp đồng: `docs/spec/studio.md`;
kịch bản demo: `demo/i1-studio/`.

### 4.1 Viết gate và kiểm gate

**Làm được**

- Viết gate bằng YAML theo lược đồ đã đóng băng; một gate con **kế thừa** gate cha và chỉ được **siết
  chặt** hơn, không bao giờ nới lỏng. Nới lỏng là lỗi, bị từ chối lúc kiểm.
- Kiểm cả thư mục gate có phân giải được hay không (`neuroedge gate lint`). Đây là phép kiểm quyết định
  một gate có an toàn hay không — chỉ thẩm định theo lược đồ là **không đủ**.
- Xem chính sách hiệu dụng sau khi gộp chuỗi kế thừa (`gate resolve`), và đọc gate bằng lời cho người
  duyệt: tiêu chí đến từ cấp nào, mệnh đề nào bị siết, ngân sách thời gian (`gate explain`).
- In mã băm SHA-256 của gate để ghim phiên bản (`gate publish`), và xem việc kế thừa một gate từ kho sẽ áp
  đặt gì (`gate add`).
- Gate kiểm cả **tham số** của lệnh: ví dụ thời gian giữ cửa mở không được quá 30 giây
  (`fixtures/gates/valid/narrows_arguments.yaml`); vượt giới hạn là chặn trước khi lệnh chạy.
- Gate được **hỏi lại** người có mặt trước khi cho phép (khai bằng `confirms`): người đó trả lời "có" thì
  gate xét lại; model hay agent khác không trả lời thay được.
- Gate có **ngân sách thời gian**: không thẩm định kịp trong thời hạn thì chặn.

**Cần gì:** chỉ cần NeuroEdge.

**Giới hạn**

- `gate publish` dừng ở mã băm, **chưa ký số** (ký cần kho gate có khoá — sau này).
- Gate chưa so trực tiếp được một con số với ngưỡng (`pressure < 8 bar`). Cách làm hôm nay: agent đổi số
  đọc thành một mức (`low`/`normal`/`high`/`critical`) rồi gate so mức đó (§4.2) — `TODOS.md` #30.
- Chưa có cú pháp CEL cho `allow_when`; chỉ có dạng ánh xạ toán tử (`TODOS.md` #42).

### 4.2 Tạo và chạy một agent

**Làm được**

- Tạo dự án agent mới từ một mẫu (`neuroedge new <tên> --template …`). Dự án có sẵn gate, action, bộ
  test, ngữ pháp lệnh và thư mục vết ghi; `neuroedge test` qua ngay. Bốn mẫu:

  | Mẫu | Là gì | Thấy được gì |
  |:---|:---|:---|
  | `minimal` | Khung trống | Điểm bắt đầu cho agent của bạn |
  | `villa-concierge` | Chốt cửa phòng khách sạn | ALLOW khi đúng phòng, BLOCK và chuyển lễ tân khi sai |
  | `home-voice` | Trợ lý giọng nói trong nhà: đèn, hỏi đáp, tin tức | Bật/tắt đèn qua gate; câu hỏi tự do cho LLM |
  | `factory-monitor` | Quạt thông gió và còi báo động theo nhiệt độ phòng máy | Hỏi lại trước khi tắt quạt lúc nóng; từ chối tắt báo động khi còn nóng |

- **Đối chiếu agent với bo mạch** trước khi chạy (`neuroedge build --target … --board …`): agent cần chân,
  cảm biến, micro nào thì bo mạch phải có đúng thứ đó; thiếu một thứ ⇒ build dừng, in từng vấn đề, không
  ghi gì. Xem bo mạch nào có năng lực gì: `neuroedge board list`, `neuroedge board show <tên>`.
- Chạy agent bằng cách **gõ lệnh** (`neuroedge run`): câu gõ khớp ngữ pháp lệnh cục bộ thành một lời gọi
  action, qua gate, rồi điều khiển chân ảo. Không cần mạng, không cần khoá API, kết quả tất định.
- Chạy một lệnh rồi thoát (`run -c "…"`), hoặc mở vòng lặp gõ lệnh có các lệnh phụ để xem và đổi dữ kiện,
  chân, cảm biến, màn hình (`:facts`, `:set`, `:pins`, `:sensor`, `:screen`, `:confirm`…).
- Mở **trang web** của phiên (`run --ui`, chỉ trên máy của bạn, 127.0.0.1): chốt cửa, đèn, cảm biến,
  màn hình ảo, dòng phán quyết, và một ô để gõ lệnh; bấm Đồng ý / Huỷ khi gate hỏi lại.
- Giả lập **cảm biến** và **màn hình** trên `sim`, và đổi số đọc cảm biến thành dữ kiện gate: so ngưỡng
  (`gte`/`lte`) hoặc chia dải (`bands`, ví dụ 25 °C → `normal`). Cùng luật đó chạy trên `linux` với cảm
  biến thật.
- Viết và chạy **test an toàn** cho agent (`neuroedge test`, dựa trên pytest): kiểm rằng lệnh nguy hiểm bị
  chặn và lệnh hợp lệ được cho phép.
- Gọi agent từ mã Python (thư viện): `c.do()` trên HAL ảo `SimHAL`.

**Cần gì:** chỉ cần NeuroEdge.

**Giới hạn**

- Hành trình "người lạ cài và chạy trong 10 phút" chưa được đo với người ngoài đội (increment I1).
- Lệnh hẹn giờ (`pulse(after_ms=…)`) chỉ có trên `sim`.

### 4.3 Vết ghi: ghi, xem, phát lại, so sánh

**Làm được**

- Ghi một phiên ra vết ghi đã thẩm định (`neuroedge record`), kể cả phiên thoại. Vết ghi chỉ lưu
  quyết định: chữ thô (câu lệnh, bản chép lời, câu trả lời) được băm tại nguồn, phán quyết giữ nguyên
  (NFR-PRIV-03). Muốn giữ nguyên văn, thêm `--raw` khi ghi — vết ghi đó mang `metadata.anonymized = false`.
- Thẩm định vết ghi theo lược đồ (`trace validate`) và in dòng thời gian sự kiện (`trace show`), gồm độ
  trễ từng chặng và tỷ lệ lượt do System 1 / System 2 xử lý (§4.4).
- Mở vết ghi thành **một tệp HTML tự chứa** để xem lại, tua thời gian, gửi đồng nghiệp — mở không cần
  mạng (`trace view`).
- Xuất vết ghi sang định dạng của Perfetto — công cụ xem dòng thời gian chạy trên trình duyệt
  (`ui.perfetto.dev`) — để phân tích thời gian (`trace export --format chrome`).
- **Phát lại** (`neuroedge replay`): dữ kiện đã ghi được đưa vào lại, phán quyết và lệnh chân được tính
  lại, rồi so với bản ghi. Lệch ⇒ báo dòng lệch đầu tiên, mã 1. Phát lại không gọi model và không đọc
  máy thật.
- **Kiểm cả kho** một lệnh (`neuroedge verify`): mọi gate phân giải, mọi vết ghi chuẩn mực thẩm định và
  phát lại ra đúng quyết định, mọi ca tool call ra đúng đáp án — trên từng môi trường bạn chọn
  (`--targets sim,linux,esp32s3`).

**Cần gì:** chỉ cần NeuroEdge (phát lại trên `linux` cần chân GPIO, §5.1; so trên `esp32s3` cần firmware
đang chạy, §5.2).

**Giới hạn**

- So sánh giữa các môi trường mới so **quyết định** (phán quyết và lệnh chân), chưa so thời gian. Trên
  `esp32s3`, thao tác và thời lượng của lệnh chân còn lấy từ bảng dựng trên máy tính, chưa do chip tự
  chạy action (`TODOS.md` #37).
- Vết ghi chưa được ký số (`TODOS.md` #1).

### 4.4 Model AI: System 1, System 2, và khi mất mạng

NeuroEdge tách hai tầng hiểu lệnh. **System 1** là tầng nhanh, cục bộ: ngữ pháp lệnh cố định (danh sách
câu → ý định), luôn có, không cần mạng. **System 2** là tầng chậm, thông minh: một LLM trả lời câu tự do.
Cả hai chỉ đề xuất lời gọi action; gate vẫn quyết định.

**Làm được**

- **LLM thật cho System 2** (Claude, GPT, DeepSeek, model qua OpenRouter…): câu tự do thành lời gọi tool,
  vẫn qua gate. Khai ở `[system_two]` trong `agent.toml`; khoá API chỉ nằm trong biến môi trường, không
  bao giờ ghi vào tệp.
- **Model cloud cho System 1 — Jev** (`typesafe/jev-1.13` qua OpenRouter): quyết một số tiêu chí gate từ
  **lời người nói** (ví dụ "người dùng muốn gì"). Chỉ các tiêu chí bạn liệt kê trong `[system_one]`, và
  câu trả lời vẫn bị kiểm miền giá trị và ngưỡng tin cậy trước khi vào gate.
- **Khi mất mạng**: model không trả lời (mất mạng, quá hạn, trả sai hợp đồng, dưới ngưỡng) thì ngữ pháp
  lệnh cục bộ quyết như cũ, vết ghi ghi lại việc chuyển đó; thiết bị nói cho người dùng những lệnh cục bộ
  còn dùng được. Một tiêu chí do model quyết mà không còn nguồn quyết định cục bộ nào chạy được thì hành động bị chặn với
  lý do `gate_unreachable`.
- **Hỏi đáp từ tri thức cục bộ** (`knowledge.toml`, như mẫu `home-voice`): câu hỏi khớp một mục tri thức
  được trả lời tất định từ mục đó; có System 2 thì model diễn đạt câu trả lời dựa trên mục tìm được, mất
  mạng thì thiết bị đọc nguyên văn mục đó.
- **Adapter tự viết** cho model chưa theo chuẩn OpenAI (`provider = "python:gói.mô_đun:hàm"`).
- System 2 được dùng **MCP server bên ngoài** để lấy thông tin (tin tức, tra cứu) — chỉ lấy thông tin,
  không điều khiển thiết bị (`[mcp.servers]`, cần `neuroedge[mcp]`).

**Cần gì:** System 2 cần `neuroedge[cloud]` và khoá API của nhà cung cấp; Jev cần khoá OpenRouter
(`OPENROUTER_API_KEY`), không cần phần mở rộng.

**Giới hạn**

- **Không bao giờ** giao cho model tiêu chí về danh tính, quyền hay đặt phòng (`guest_authenticated`,
  `room_matches`…): đó là dữ kiện của hệ thống quản lý. Build từ chối những tiêu chí agent tự tính và
  tiêu chí nguồn gọi (`call_source`).
- `[system_one]` gửi **lời người nói** lên OpenRouter (không gửi action hay tham số). Băm tại nguồn
  chỉ áp cho vết ghi, không ngăn việc gửi đó.
- Jev đọc tiếng Anh tốt nhất; độ tin cậy trên câu tiếng Việt **chưa đo** — đặt ngưỡng thận trọng
  (`TODOS.md` #27).
- CI không gọi model thật; lượt gọi bằng khoá thật chạy tay (`scripts/live_llm_smoke.py`,
  `scripts/live_jev_smoke.py`).

### 4.5 Thoại: nói với agent

**Làm được**

- **Nói bằng tệp WAV** (`run --voice-file cau-noi.wav`, hoặc `record --voice-file …`): âm thanh đi qua bộ
  phát hiện tiếng nói (VAD), sang nhận dạng giọng nói (STT), bản chép lời đi đúng đường của lệnh gõ tới
  gate, câu trả lời đi sang tổng hợp giọng nói (TTS) và ghi ra tệp (`--voice-out tra-loi.wav`). Chạy
  trên `sim` và `linux`.
- **Nói qua micro laptop, thời gian thực** (`run --mic`, chỉ `sim`, cần `neuroedge[audio]`): đeo tai nghe để
  cắt lời được; dùng loa ngoài thì thêm `--half-duplex` (micro tắt khi agent đang nói, không cắt lời). Lần đầu
  macOS hỏi quyền micro cho terminal. Kịch bản: `demo/i4-thoai-laptop/`.
- **STT/TTS qua mọi nhà cung cấp theo chuẩn OpenAI audio** — OpenAI, Groq, OpenRouter, faster-whisper, Kokoro… — đổi
  bằng `base_url` trong `[stt]` / `[tts]`; server trả PCM thô (OpenRouter) thì khai `format = "pcm"` và `sample_rate_hz`. Có sẵn nhà cung cấp giả để thử không cần khoá (§6.6).
- **Cắt lời**: người dùng nói chen khi loa đang phát ⇒ loa dừng, và mọi lệnh chưa giao tới chân bị huỷ.
  Lệnh đã giao (một xung chốt cửa đang chạy) thì chạy hết.
- **Từ đánh thức** (`[wake_word]`): lượt chỉ mở khi nghe đúng từ khoá, thay cho việc mở theo mọi tiếng nói.
  Dùng openWakeWord (`neuroedge[wake]`) hoặc adapter của bạn. **Mô hình là của bạn**: NeuroEdge không kèm
  và không tải mô hình nào, vì mọi mô hình dựng sẵn của openWakeWord có giấy phép phi thương mại. Bộ phát
  hiện hỏng ⇒ không lượt nào mở, phiên vẫn chạy.
- **STT dự phòng cục bộ** (`[stt.fallback]`): STT chính hỏng thì một endpoint trên máy (faster-whisper,
  speaches…) nhận lượt đó với hạn chót riêng. Kết quả đến muộn của STT chính bị bỏ, không bao giờ điều
  khiển chân. Chỉ khi cả hai hỏng, thiết bị mới nói câu offline.

**Cần gì:** agent khai `audio.in` (và `audio.out` nếu có `--voice-out`) trong `[requires]`; một nhà cung
cấp STT (khoá API hoặc server trên máy, hoặc nhà cung cấp giả).

**Giới hạn**

- **Micro thật mới có trên laptop, target `sim`** (Q-50). Chưa có trên `linux`/Pi (cần khử vang PipeWire,
  `TODOS.md` #45) và chưa có trang web theo dõi cho phiên micro (`--mic --ui` ⇒ mã 2).
- Chưa có mô hình từ đánh thức nào dùng được mà hợp giấy phép (`TODOS.md` #49); CI kiểm bằng mô hình giả.
- Tệp WAV với trang web theo dõi (`--voice-file` cùng `--ui`) chưa hỗ trợ (mã 2).
- Thoại trên chip ESP32-S3 là increment I5, chưa bắt đầu.

### 4.6 Claude Desktop và agent khác qua MCP

MCP (Model Context Protocol) là cách chuẩn để một ứng dụng AI gọi công cụ bên ngoài. NeuroEdge biến mỗi
action của agent thành một công cụ MCP, và mọi lời gọi vẫn phải qua gate.

**Làm được**

- Xem các action dưới dạng công cụ — schema cho MCP hoặc cho function calling của OpenAI (`mcp tools`).
- Chạy agent như một **máy chủ MCP** qua stdio (`mcp serve`) trên `sim` hoặc `linux`: mọi lời gọi qua kiểm
  schema rồi qua gate.
- **Ghi sẵn cấu hình cho Claude Desktop** (`mcp desktop-config --write`): đường dẫn tuyệt đối, sao lưu
  tệp cũ, giữ nguyên mọi mục khác.
- Nhờ Claude Desktop "bật đèn" và **thấy đèn ảo đổi trên trình duyệt**, cùng một phiên (`mcp serve --ui`,
  trang ở `http://127.0.0.1:8765`).

**Cần gì:** `neuroedge[mcp]`; Claude Desktop cho phần Desktop.

**Giới hạn**

- Chỉ qua stdio, chưa có MCP qua mạng (`TODOS.md` #24, #25).
- Trang web theo dõi chỉ có trên `sim`.

---

## 5. Đưa agent lên thiết bị

### 5.1 Máy Linux (`--target linux`)

**Làm được**

- `run`, `record` và `mcp serve` với `--target linux`: chân là **line GPIO thật** của kernel, cùng sổ phán
  quyết như `sim`. Thoát phiên ⇒ mọi line về trạng thái nghỉ, kể cả khi bị dừng bằng tín hiệu.
- Đủ năm nguyên thủy phần cứng (HAL): `digital.out` (chân ra), `sensor.read` (cảm biến hwmon/IIO, tìm theo
  **tên**), `display` (framebuffer — thiết bị màn hình của kernel, `/dev/fbN` — hoặc trong bộ nhớ),
  `audio.in` và `audio.out`.
- **Âm thanh từ tệp WAV**: `run` / `record --voice-file` trên `linux` đưa tệp về tần số lấy mẫu của bo
  mạch, không cần micro hay loa.
- **Nối sẵn micro và loa thật** qua PipeWire đã khử vang (`NEUROEDGE_LINUX_AUDIO=live`, `neuroedge[audio]`;
  tệp cấu hình PipeWire giao kèm): phiên mở cả micro và loa **trước khi** giữ chân GPIO nào, và thiếu thiết
  bị thì dừng ngay. Mới dừng ở mức mở thiết bị — xem Giới hạn.
- **Chưa có máy Linux gắn thiết bị?** Tạo line GPIO ảo bằng gpio-sim (`scripts/setup_gpio_sim.sh`, kernel
  ≥ 5.19). CI chạy toàn bộ phần `linux` trên gpio-sim, cảm biến ảo `i2c-stub` + `lm75`, và màn hình ảo.
- Kiểm cùng quyết định trên `sim` và `linux` (`verify --targets sim,linux`).

**Cần gì:** máy Linux; `neuroedge[linux]` (thư viện libgpiod); line GPIO thật hoặc ảo. Âm thanh thật cần
thêm `neuroedge[audio]` và PipeWire.

**Giới hạn**

- **Chưa chạy trên Raspberry Pi 5 thật**; phiên chạy hằng đêm trên Pi chưa có.
- **Chưa có phiên nói qua micro thật.** Đường micro/loa thật mới mở thiết bị lúc bắt đầu phiên; chưa có
  phiên nào thu và phát âm thanh sống (`TODOS.md` #45). Phiên thoại trên `linux` hôm nay luôn đọc tệp WAV.
- Micro và loa thật **chưa kiểm trên phần cứng**: tên nút PipeWire có tới được qua PortAudio/ALSA trên Pi
  hay không chưa được xác minh. `linux-rpi5` chưa khai khử vang đạt chuẩn.
- Dữ kiện gate không đến từ cảm biến mà khai cố định ở `[sim.facts]` (ví dụ "khách đã xác thực") vẫn là
  **giá trị cố định** trên `linux`, vì chưa có hệ thống nào cung cấp chúng; `run` in cảnh báo khi một gate
  quyết dựa trên chúng.
- Cảm biến dạng đầu vào GPIO (`motion`, `door_contact`) chưa đọc được; agent cần chúng bị từ chối trước
  khi giữ chân nào.
- Chưa có trang web theo dõi (`--ui` ⇒ mã 2). Framebuffer chỉ nhận khung điểm ảnh.

### 5.2 Chip ESP32-S3 (`--target esp32s3`)

Thủ tục đầy đủ — sinh, build, nạp, QEMU, OTA — ở một nơi duy nhất: [`nap-firmware.md`](nap-firmware.md).
Dưới đây là năng lực.

**Làm được (đã kiểm trên QEMU)**

- **Sinh firmware cho agent của bạn** (`neuroedge build --target esp32s3`): một project ESP-IDF đầy đủ.
  Gate chạy trên chip dưới dạng cây quyết định nhị phân trong flash, bộ duyệt viết bằng C, và sổ phán
  quyết dùng một lần.
- **Tự kiểm lúc khởi động**: firmware chạy lại các phép kiểm của agent và phải ra **đúng** phán quyết máy
  tính đã tính lúc build. Lệch một chỗ ⇒ `NE_SELFTEST FAIL` và firmware dừng, không action nào chạy.
- **Vết ghi qua UART**: ghi các phiên của thiết bị thành vết ghi trên máy tính
  (`record --target esp32s3 --port …`), rồi so phán quyết của chip với máy tính
  (`verify --targets esp32s3 --port …`).
- **Cập nhật OTA có ký** — tuỳ chọn, bật bằng lớp cấu hình `sdkconfig.ota` lúc build (bản mặc định không có
  đường tải nào): hai khe firmware A/B; ảnh cập nhật phải được ký RSA-3072 bằng khoá của bạn; ảnh
  mới chỉ được xác nhận sau khi vượt tự kiểm, hỏng thì bootloader tự quay về bản trước; không nhận bản cũ
  hơn bản đã xác nhận. Tải từ bất kỳ máy chủ HTTP(S) nào. Ảnh mới **treo** mà không tự khởi động lại thì
  chỉ quay về ở lần tắt nguồn rồi bật lại kế tiếp (`nap-firmware.md` §6.3).
- **Ngôn ngữ giao diện theo agent**: màn hình thiết bị nói ngôn ngữ của agent (tiếng Việt hoặc tiếng Anh),
  lấy từ `[agent] language`, không có thì `[stt] language`, không có nữa thì tiếng Việt. Chín màn hình
  LVGL đã có và được so ảnh chuẩn (ảnh golden) mỗi PR.

**Cần gì:** ESP-IDF v5.4 (hoặc Docker `espressif/idf:v5.4`); Box-3 khi bo mạch về, còn hôm nay dùng QEMU.

**Giới hạn**

- **Chưa có bo mạch; chưa chân GPIO nào động** (HAL trên chip chưa có).
- Chưa có âm thanh trên chip (I5); thư viện ESP-SR chưa được link vì giấy phép chưa xác minh
  (`TODOS.md` #17).
- **OTA chưa chạy qua mạng thật**: QEMU dùng card mạng Ethernet ảo; Box-3 chưa kết nối Wi-Fi và chưa có
  cách nhập thông tin mạng (`TODOS.md` #50).
- **Chưa có Secure Boot và chống hạ cấp bằng eFuse**: ai có cáp vẫn nạp được mọi ảnh đã ký.
- Giao diện mới build trên máy tính để so ảnh golden; **chưa nối vào firmware** (chờ driver màn hình).
  Giao diện chỉ có tiếng Việt và tiếng Anh; ngôn ngữ khác bị build từ chối.
- Phát lại một vết ghi tuỳ ý trên chip chưa có (`replay --target esp32s3` ⇒ mã 2).

---

## 6. Thử nghiệm từng bước

Mỗi kịch bản ghi rõ cần gì, lệnh nào, và bạn sẽ thấy gì. Làm theo thứ tự từ trên xuống là đi từ dễ tới
khó. Mọi lệnh viết như thể `neuroedge` đã nằm trong `PATH` (§3).

### 6.1 Gate cho và gate chặn — 2 phút, không cần gì

Trong thư mục gốc của kho (agent mẫu mặc định là chốt cửa khách sạn `villa-concierge`):

```bash
neuroedge run -c "mở cửa phòng 101"
neuroedge run -c "mở cửa phòng 202"
```

Lệnh đầu cho `✓ ALLOW unlock_door@1.2.0` và chân `door_lock` thành `PULSED 30s`. Lệnh sau cho
`✗ BLOCK … criterion: room_matches` và chuyển cho lễ tân: khách không ở phòng 202.

### 6.2 Hỏi lại và từ chối — agent nhà máy

```bash
neuroedge new nhamay --template factory-monitor && cd nhamay
neuroedge run -c "bật quạt"        # ✓ ALLOW: thêm gió luôn an toàn
neuroedge run -c "tắt quạt"        # ✗ BLOCK kèm hỏi lại: "Phòng máy đang nóng — bạn chắc muốn tắt quạt thông gió?"
neuroedge run -c "tắt báo động"    # ✗ BLOCK, action deny: không ai tắt còi khi phòng còn nóng
neuroedge test                     # bộ test an toàn của agent: mọi test đạt
```

Phòng máy ảo bắt đầu ở 45 °C (dải `high`). Mở vòng lặp gõ lệnh (`neuroedge run`), gõ
`:sensor temperature 30` để hạ nhiệt về dải `normal`, rồi gõ lại `tắt quạt`: lần này được cho phép. Gõ
`:help` để xem mọi lệnh phụ.

### 6.3 Xem trên trình duyệt

Trong thư mục `nhamay`:

```bash
neuroedge run --ui
```

Trình duyệt mở trang `http://127.0.0.1:…` (địa chỉ cũng in ra terminal) với quạt, còi, cảm biến nhiệt
và dòng phán quyết. Gõ lệnh vào ô **"Gõ lệnh cho agent"** trên trang: `tắt quạt` làm trang hiện câu hỏi
cùng hai nút Đồng ý / Huỷ; `:sensor temperature 30` hạ nhiệt độ ngay trên trang. Dừng bằng Ctrl-C ở
terminal.

### 6.4 Ghi, xem lại, phát lại

```bash
neuroedge record -c "tắt báo động"                  # in: trace: traces/sess_….json
neuroedge trace view traces/sess_….json -o xem.html # mở xem.html bằng trình duyệt, không cần mạng
neuroedge replay traces/sess_….json
```

`replay` tính lại phán quyết từ dữ kiện đã ghi và in `✓ decisions match the recording`. Thử sửa gate
`alarm_off` cho dễ dãi hơn rồi phát lại: phát lại báo lệch và thoát mã 1 — đó là cách NeuroEdge bắt một
thay đổi làm yếu an toàn.

### 6.5 Nhờ Claude Desktop điều khiển thiết bị ảo

Cần `pip install 'neuroedge[mcp]'` và Claude Desktop.

```bash
neuroedge mcp desktop-config --agent agent.toml --ui --write
```

Thoát hẳn Claude Desktop rồi mở lại, nhờ nó "bật quạt". Phán quyết hiện ở `http://127.0.0.1:8765`. Trang
không đổi thì xem §7.

### 6.6 Nói với agent bằng tệp WAV — không cần khoá

Tạo agent `home-voice`, rồi thêm vào `agent.toml` hai việc:

1. Trong `[requires]`, thêm dòng `"audio.in" = { sample_rate_hz = 16000 }`.
2. Cuối tệp, khai nhà cung cấp giả (nó "nghe" đúng câu bạn cho sẵn):

   ```toml
   [stt]
   provider = "python:neuroedge.perception.providers.fake:stt"
   [stt.options]
   transcripts = ["bật đèn"]

   [tts]
   provider = "python:neuroedge.perception.providers.fake:tts"
   ```

Cần một tệp WAV 16 kHz, mono, 16-bit có một đoạn âm thanh (tiếng nói hay một tiếng bíp đều được, vì nhà
cung cấp giả không nghe thật). Rồi:

```bash
neuroedge run --voice-file cau-noi.wav --voice-out tra-loi.wav
```

Bạn sẽ thấy `turn 1 · … · heard: “bật đèn”`, `✓ ALLOW light_on@1.0.0` và một dòng tổng kết `voice: …`.
Muốn nghe thật: thay `[stt]` / `[tts]` bằng nhà cung cấp thật (`base_url`, `model`, `api_key_env`) — cách
khai ở `CHANGELOG.md` §2.3 (lệnh `run`).

### 6.7 LLM thật cho câu tự do

Cần `pip install 'neuroedge[cloud]'` và khoá API. Agent `home-voice` có sẵn mẫu `[system_two]` đã comment
trong `agent.toml`: bỏ comment, đặt biến môi trường chứa khoá, rồi `neuroedge run`. Câu ngoài ngữ pháp
(ví dụ một câu hỏi) do model trả lời; câu điều khiển đèn vẫn qua gate. Tắt mạng rồi thử lại: thiết bị nói
câu offline và liệt kê lệnh cục bộ còn dùng được.

### 6.8 Chân GPIO thật của Linux — trên máy Linux

Cần máy Linux kernel ≥ 5.19, quyền `sudo`, và `pip install 'neuroedge[linux]'`.

```bash
bash scripts/setup_gpio_sim.sh     # tạo line GPIO ảo tên door_lock, porch_light, gate_relay (tự gọi sudo)
neuroedge run --target linux --agent fixtures/agents/driveway/agent.toml -c "bật đèn hiên"
neuroedge verify --targets sim,linux
```

Lệnh `run` bật line `porch_light` thật của kernel (agent mẫu `driveway`: đèn hiên và cổng). Lệnh
`verify` phát lại mọi vết ghi chuẩn mực trên cả `sim` lẫn `linux` và đòi hai bên ra cùng quyết định.
Agent `villa-concierge` thì bị từ chối trên `linux`: nó đòi micro có khử vang phần cứng, thứ
`linux-rpi5` không khai — đúng là điều NeuroEdge phải chặn khi agent và bo mạch không hợp nhau.

### 6.9 Firmware của agent trên QEMU

Cần Docker và image `espressif/idf:v5.4`. Trong một dự án `home-voice`:

```bash
neuroedge build --target esp32s3     # in: firmware: build/esp32s3 — ESP-IDF project, …
```

Rồi build và chạy trên QEMU theo [`nap-firmware.md`](nap-firmware.md) §5. Trong đầu ra, dòng
`NE_SELFTEST PASS walker=… token=…` là bằng chứng gate của agent chạy đúng trên chip ảo: `walker` là số
phép kiểm bộ duyệt cây gate đã qua, `token` là số phép kiểm sổ phán quyết đã qua.

### 6.10 Cập nhật OTA trên QEMU

Cần Docker. Trong thư mục gốc của kho:

```bash
docker run --rm -v "$PWD":/work -w /work espressif/idf:v5.4 \
  bash -lc '. $IDF_PATH/export.sh >/dev/null 2>&1; bash scripts/qemu_ota.sh'
```

Kịch bản dựng máy chủ cập nhật, ký ảnh bằng khoá dùng-một-lần, rồi chạy bảy pha: bản mới hợp lệ được nạp
và xác nhận; ảnh sai khoá bị từ chối; ảnh không ký bị từ chối; hai loại ảnh hỏng tự quay về; bản cũ hơn bị
bỏ qua. Kết thúc bằng `OTA on QEMU: all phases passed`. Ý nghĩa từng dòng `NE_OTA …`:
[`nap-firmware.md`](nap-firmware.md) §6.4.

### 6.11 Xem giao diện thiết bị

Không cần gì: mở các ảnh PNG trong `targets/esp32s3/ui/golden/vi/` (tiếng Việt) và
`targets/esp32s3/ui/golden/en/` (tiếng Anh). Đó là đúng từng điểm ảnh của chín màn hình trên panel
320×240 của Box-3, kể cả các ca chữ dài bị cắt có dấu `…`. Tự dựng lại và so: `bash scripts/run_ui_golden.sh`
(cần cmake hoặc Docker).

---

## 7. Khi gặp lỗi

**Mọi thông báo lỗi có đủ ba phần**: ở đâu · vì sao · cách xử lý. Cách đọc một thông báo lỗi và nghĩa
của từng mã `NE…`: `CHANGELOG.md` §2.4.

**Mã thoát** của mọi lệnh theo một hợp đồng: `0` đã kiểm và đạt · `1` đã kiểm và không đạt · `2` tính năng
đó chưa có. Mã `2` nói thật rằng tính năng chưa có — NeuroEdge không bao giờ giả vờ đạt.

**Claude Desktop và `mcp serve --ui`: trang không đổi khi gọi từ Desktop.** Desktop thường chạy vài tiến
trình máy chủ cùng lúc, mỗi tiến trình có trang riêng, và chỉ một giữ được cổng 8765
(`docs/spec/tool_calling.md` §8). Cách tìm đúng trang:

1. Mở log của Desktop — trên macOS là `~/Library/Logs/Claude/mcp-server-<tên>.log`.
2. Tìm các dòng `sim UI at http://127.0.0.1:…` và `warning: sim UI port 8765 is taken … the page is at …`.
3. Mở từng URL trong các dòng đó; trang của cuộc trò chuyện là trang đổi khi bạn gọi.

Firmware và OTA có bảng lỗi riêng: [`nap-firmware.md`](nap-firmware.md) §7.

---

## 8. Đọc tiếp

| Muốn | Đọc |
|:---|:---|
| Cú pháp đầy đủ của mọi lệnh | [`CHANGELOG.md`](../../CHANGELOG.md) §2.3 |
| Tiến độ theo task và increment | [`trang-thai.md`](trang-thai.md) |
| Nạp firmware, QEMU, OTA | [`nap-firmware.md`](nap-firmware.md) |
| Mỗi nguyên thủy phần cứng chạy bằng gì trên từng môi trường | [`simulation_coverage.md`](../spec/simulation_coverage.md) |
| Những đường tắt qua gate đã bị chặn | [`threat_model.md`](../spec/threat_model.md) |
| Mọi tài liệu khác | [`README.md`](README.md) (bản đồ tài liệu) |

Muốn tài liệu này có thêm mục gì: mở issue hoặc PR theo [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
