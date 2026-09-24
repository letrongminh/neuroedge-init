# Rà soát tái định vị thông điệp — "Hợp đồng vào Physical AI" (2026-09-24)

> **Lưu trữ, không quy phạm.** Bản ghi vì sao Q-30 chọn định vị mới, những gì đã cân nhắc
> và loại, và các mốc phải đọc lại. Quyết định nằm ở `neuroedge-prd.md` §15, Q-30; việc
> theo dõi ở `TODOS.md` #32 và #34.

## 1. Vì sao có bản rà soát này

Đề xuất "tái định vị theo tư duy AI-Native Agency của YC và Paul Graham" được đưa ra
2026-09-24 (ngoài kho). Trước khi cập nhật tài liệu, hai luận điểm nguồn được kiểm chứng
tại nguồn và bản đồ đối thủ được khảo sát lại. Kết luận: **luận điểm nguồn là thật, nhưng
phần lớn giá trị của đề xuất đã có trong chiến lược hiện hành; phần mới chưa có bằng chứng.**
Quyết định: đổi **thông điệp** (engine-first không đổi), hoãn đổi **mô hình** (autopilot,
agency, bán theo kết quả) tới khi có dữ liệu.

## 2. Hai luận điểm nguồn — đã kiểm chứng

| Nguồn | Luận điểm | Hiệu chỉnh khi trích dẫn |
|:---|:---|:---|
| **Sequoia — "Services: The New Software"** (Julien Bek, 2026-03-05) | *"The next \$1T company will be a software company masquerading as a services firm."* · *"A copilot sells the tool. An autopilot sells the work."* · \$1 phần mềm : \$6 dịch vụ | Không cần sửa; tài liệu gốc ngoài kho chỉ nêu tên lãnh đạo chung chung |
| **YC RFS 2026** | Spring 2026 — **"AI-Native Agencies" (Eric Migicovsky)**; Summer 2026 — **"AI-Native Service Companies" (Gustaf Alströmer)**; Aaron Epstein: *"use the software yourself and sell them the finished product at 100x the price"* | **Sửa tên người**: đề xuất ngoài kho gán sai cho Garry Tan / Dalton Caldwell / Jared Friedman (Garry Tan có RFS "AI-Native Hedge Funds"; Jared Friedman có "AI for Government"). Nguồn: `ycombinator.com/rfs` |
| **Paul Graham — "Making Startups Powerful"** (2026-09, [paulgraham.com/powerful.html](https://paulgraham.com/powerful.html)) | Full-stack / *"eat your customer's hardest work"* · *"help users make money"* · tails wag the dog · network effects · open source → chuẩn (note 2: *"first to be proposed tends to win"*) · bán cho khách quyết nhanh | **Hai vế bị lược phải khôi phục**: full-stack nghĩa là *"in competition with them"* (cạnh tranh với khách hàng của mình), và ràng buộc *"They all have to make things better for the customer."* |

## 3. Khảo sát đối thủ (2026-09-24)

### 3.1 Phe builder / agent platform

| Sản phẩm | Định vị nổi bật | Nhận xét cho NeuroEdge |
|:---|:---|:---|
| [ESP-Claw](https://github.com/espressif/esp-claw) (Espressif) | "Chat as Creation" — LLM viết Lua, chạy ngay trên chip $5 | Không gate/CI/trace; vendor-bound |
| [OpenClaw](https://openclaw.ai) | *"The AI that really does things."* — agent cá nhân, quỹ 501(c)(3), 346k+ sao | Định vị "làm việc thật" nhưng trên máy tính, không actuator |
| [XiaoZhi](https://github.com/78/xiaozhi-esp32) | Chatbot MCP-based, ~29k sao, hệ sinh thái bo mạch lớn nhất | Kênh phân phối tiềm năng, không có lớp an toàn |
| [ESPHome](https://esphome.io) | *"Smart Home Made Simple"* / *"Custom smart home devices, built by you"* | No-code cho maker; không gate động |
| [Home Assistant](https://www.home-assistant.io) | *"Open source home automation that puts local control and privacy first."* | "X-first" là mẫu câu đáng học; local ≠ an toàn hành động |

### 3.2 Phe Physical AI / an toàn vật lý

| Sản phẩm | Định vị nổi bật | Va chạm cần tránh |
|:---|:---|:---|
| [NVIDIA](https://nvidianews.nvidia.com/news/nvidia-us-manufacturing-robotics-physical-ai) | *"The next wave of AI is physical AI"* (Jensen Huang); full-stack Jetson/CUDA/Omniverse | Sở hữu khái niệm "Physical AI" ở tầng hạ tầng compute |
| [Peridio — Avocado OS](https://www.peridio.com) | *"The Operating System for Physical AI"* | **"OS cho Physical AI"** — cùng Meshcore/Kosmos/Quasi/Certus: ít nhất 5 chủ |
| [Meshcore AI](https://meshcore-ai.com) | *"An Operating System for the Physical World"* | Cùng cụm "OS" |
| [Kosmos OS](https://kosmosos.ai) | "Physical AI infrastructure", "Agentic Gateway", "World Truth Engine" | Cụm "gateway" bắt đầu xuất hiện |
| [Quasi Intelligence](https://www.quasiintelligence.ai) | *"The AI operating system for the physical world"* | Cùng cụm "OS" |
| [Certus](https://certusai.dev) | *"Living OS for physical AI"* — bằng chứng tuân thủ sống | Cùng cụm "OS"; mạnh về compliance |
| [OneDiagonal](https://www.onediagonal.com) | *"The Release Gate for Physical AI"* — crash-test trên phần cứng trước khi phát hành fleet | **"gate"** trong định vị đã có chủ mạnh |
| [AI Safety Gate](https://aisafegate.com) | *"Enforcement layer between AI output and irreversible actions"*; fail-closed | Cụm "safety gate" + fail-closed đã bị dùng |
| [STATE16](https://state16.ai) | *"Physical AI Guardrails & Assurance"* — runtime integrity cho VLA/world models | Cụm "guardrails/runtime" |
| [THEMAIN.AI](https://themain.ai) | *"The hardware safety layer for Physical AI"* — chip an toàn, EU Machinery Reg 2027 | "Safety layer" ở tầng silicon |

**Kết luận khảo sát:** cụm *"operating system for Physical AI"* và *"safety/release gate"* đã
đông; **chưa ai sở hữu chữ "contract"** trong định vị Physical AI. Đó là trục được chọn.

## 4. Quyết định (Q-30)

- **VI:** *"NeuroEdge — Hợp đồng vào Physical AI. Không hợp đồng, không hành động."*
- **EN (master quốc tế):** *"NeuroEdge — Physical AI, under contract. No contract, no action."*
- **Contract = lớp bảo vệ gần nhất, đứng ngay trên 5 nguyên thủy HAL** (`audio.in/out`,
  `digital.out`, `sensor.read`, `display`): mọi lệnh tới phần cứng đều qua gate — kiểm thử
  trong CI, viết một lần, chạy mọi phần cứng. Chi tiết kiến trúc: proposal §0.3, §3.3.
- **Engine-first không đổi:** sản phẩm, người mua (U1/U2), mô hình doanh thu (Fleet OS) và
  lộ trình giữ nguyên.
- **NeuroBrain (đề xuất, chờ `Q-31`):** *"Copilot for building Physical AI"* — ghi tại
  `neuroedge-roadmap-phase1-5.md` §1 kèm **rủi ro tên gọi**: "Copilot" thuộc họ nhãn
  Microsoft/GitHub; va chạm đã kiểm chứng ([navigate.ai](https://www.navigate.ai/company)
  — "the trusted AI copilot for the physical world"; Bench Copilot — bring-up embedded).
  **Xem lại trước Beta công khai**; dự phòng: "Đồng đội bring-up".

## 5. Đã cân nhắc và loại

| Phương án | Lý do loại |
|:---|:---|
| Tái định vị sang **Autopilot / AI-Native Studio** (tự giao dự án) | Đổi mô hình kinh doanh và đội ngũ, chưa có dữ liệu; trái "Fleet OS là dịch vụ thương mại duy nhất" (CR-1.0) |
| **Mạng agency** là kênh chính | Chưa có một cuộc phỏng vấn nào; hoãn ở `TODOS.md` #34, mốc cổng 25-10 / ≥3 agency hỏi mua |
| **Bán theo kết quả / Outcome Royalty** | Chưa qua PF-1..4; premise giá chưa kiểm (`CEO-X2`) |
| **Chương trình "Certified AI-Agency"** | Thu phí đang bị Chặn (PF-3); miễn phí thì trùng chương trình Giai đoạn 2 |
| Cụm **"Operating System for Physical AI"** | Ít nhất 5 chủ (Peridio, Meshcore, Kosmos, Quasi, Certus) |
| Cụm **"Safety/Release Gate"** làm tagline chính | Đã có chủ mạnh (OneDiagonal, AI Safety Gate) |
| Tagline **A1** ("Đưa AI Agent vào Physical AI" + 3 trụ) | Đúng nhưng nhạt; đã thay bằng V2'/E-B |
| Tagline **B1** ("Cánh cổng vào Physical AI") | Giữ "cánh cổng" trong tuyên ngôn dài; headline chuyển sang "contract" theo chỉ đạo |

## 6. Mốc phải đọc lại

1. **Cổng nhu cầu 2026-10-25 (C1–C10)** — dữ liệu phân khúc; nếu muốn dữ liệu kênh agency rẻ:
   thêm C11 (xem `TODOS.md` #34).
2. **MHS công bố open source / DCP v0.4** — đọc lại §10 và `TODOS.md` #32 (danh sách theo dõi
   đã mở rộng: OneDiagonal, AI Safety Gate, STATE16, Peridio).
3. **Trước Beta công khai** — chốt tên NeuroBrain (rủi ro "Copilot") và `Q-31`.
4. **≥3 agency thật hỏi mua** — xem lại `TODOS.md` #34.

## 7. Tệp đã đổi trong phiên

`neuroedge-prd.md` (masthead, §1.2, §15 Q-30) · `neuroedge-proposal.md` (masthead, §0.3, §1.2) ·
`README.md` (hero EN-first) · `neuroedge-roadmap-phase1-5.md` (§1 định vị đề xuất) ·
`docs/user/thuat-ngu.md` (NeuroBrain) · `TODOS.md` (#32 mở rộng, #34 mới) · `CHANGELOG.md` ·
`neuroedge-roadmap.md` (§0.1, §0.3, §10.1).
