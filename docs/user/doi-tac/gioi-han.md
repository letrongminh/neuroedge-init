# Đợt thử với đối tác — những gì chưa có

Trang này nói thẳng điều đợt thử **không** làm hoặc **chưa kiểm**. Nếu một điều ở đây chặn bạn, báo qua [mẫu phản hồi](phan-hoi.md): đó là thông tin chúng tôi cần.

## Chưa có trong đợt thử

| Hạng mục | Tình trạng |
|:---|:---|
| `esp32s3` (chạy gate trên chip ESP32-S3-Box-3) | **Ngoài đợt thử.** Chưa có bo mạch trong tay; không có firmware nào để giao |
| Thoại trên chip (micro, loa, wake-word trên thiết bị) | **Ngoài đợt thử** |
| NeuroBrain (điều phối nhiều thiết bị/phòng lab) | **Ngoài đợt thử** |
| `linux` trên Raspberry Pi thật (chân GPIO thật) | **Thử nghiệm**, chưa được kiểm tự động trên Pi thật; đừng dùng cho thứ nguy hiểm khi chưa tự thử |
| Cơ cấu chấp hành từ xa (điều khiển thiết bị qua mạng bằng chân ảo có phong bì) | Có trong lõi (`[actuators.<tên>]`, [`extension_sdk.md`](../../spec/extension_sdk.md) §7) và một plugin Home Assistant **mức L1** (`switch`, `light`, `input_boolean`) giao riêng dưới dạng wheel `neuroedge-homeassistant` nếu đợt thử cần. L1 nghĩa là NeuroEdge tự gửi lệnh tắt khi hết giờ; mất liên lạc thì thiết bị có thể bật mãi, nên hành động **không hoàn tác** (van, khoá, máy sưởi) bị `neuroedge build` từ chối với plugin này. Chỉ kiểm trên bản giả Home Assistant, **chưa kiểm trên Home Assistant thật** (TSK-I2c-16). |
| Plugin bên thứ ba (bridge, nguồn dữ kiện…) | Chưa có bộ nạp (TSK-I2c-11); `plugin doctor` in "không kiểm được: plugin" |
| Phát hành công khai (PyPI, index) | Không có: wheel giao trực tiếp |

## Chưa kiểm trên thiết bị thật

- **Home Assistant:** hướng dẫn [`home-assistant-mcp.md`](home-assistant-mcp.md) mới chạy trên một **bản giả** dựng theo tài liệu công khai của tích hợp MCP Server
  ([`fixtures/ha_mcp_double/`](../../../fixtures/ha_mcp_double/server.py)). Địa chỉ (`/api/mcp`), tên tool và tham số của HA thật có thể khác; **chưa kiểm trên Home Assistant thật**.
- **API thiết bị:** [`proxy-http.md`](proxy-http.md) chạy trên một bản giả (`GET /cm?cmnd=…`, `POST /api/{lệnh}`). Thiết bị thật có thể cần xác thực, định dạng hay phản hồi khác.
  Tasmota có mật khẩu web (tham số `user`/`password` trong query) **chưa được hỗ trợ** như một cấu hình có sẵn: proxy chỉ chuyển tham số bạn khai.

## Giới hạn an toàn — hiểu trước khi dùng

- **Proxy không chặn được lời gọi thẳng.** Nó chỉ canh con đường đi qua nó. Máy khách nào còn tới được thiết bị hay MCP server gốc (có token, hoặc trong cùng mạng) gọi thẳng được, và gate chỉ để trang trí.
  `neuroedge plugin doctor` báo những lối vòng nó thấy và nói rõ điều nó không kiểm được; đặt thiết bị sau tường lửa/ACL và để token chỉ proxy biết là việc của bạn
  ([`threat_model.md`](../../spec/threat_model.md) §2b).
- **`proxy http` không có xác thực ở phía trước**, nên nó chỉ nghe ở loopback (`127.0.0.1`, `::1`) và từ chối khởi động nếu `listen` là địa chỉ khác. Máy khác trong mạng không dùng được front của nó; ai dùng được máy này thì dùng được.
- **http thuần trên mạng nhà** chỉ được bật bằng khoá `allow_lan_http = true` (hoặc cờ `--allow-lan-http` của `guard init`) và chỉ tới IP riêng hay tên `*.local`, `*.lan`, `*.home.arpa`.
  Khi bật, lời gọi và **token đi không mã hoá trên LAN**: ai nghe được mạng nhà đọc và chép lại được token, rồi gọi thẳng thiết bị. Dùng `https` nếu thiết bị hỗ trợ. `plugin doctor` luôn cảnh báo khi cờ bật.
- **Token trong cấu hình Claude Desktop** (khối `env` bạn tự thêm) nằm dạng chữ rõ trong tệp của Claude Desktop. Dùng một người dùng/token riêng với quyền hẹp cho proxy.
- **Vết ghi có thể chứa tham số của lời gọi** (tên thiết bị, giá trị) — không băm. Đọc trước khi gửi cho chúng tôi.
- **Proxy và `Guard` không phải hộp cát**: không chống mã chạy cùng tiến trình hay cùng máy với quyền như bạn.
- **Gate mở rộng là trách nhiệm của bạn.** Gate sinh ra chặn tất cả; gate bạn mở chỉ an toàn bằng điều kiện bạn viết vào nó. Đừng mở "cho mọi client" với thứ khó hoàn tác (khoá cửa, nguồn điện).

## Giấy phép và dữ liệu

- Mã nguồn dùng giấy phép **PolyForm Noncommercial 1.0.0** ([`LICENSING.md`](../../../LICENSING.md)): chỉ cho dùng **không thương mại**. Đợt thử là *đánh giá* theo **thoả thuận thử nghiệm bằng văn bản** giữa hai bên;
  dùng thương mại cần thoả thuận khác. Không có gì ở đây thay thế thoả thuận đó.
- Wheel giao trực tiếp, **không** có trên PyPI. Chúng tôi không thu vết ghi của bạn: bạn gửi cái bạn chọn, qua kênh riêng.
