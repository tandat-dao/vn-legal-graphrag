# LIVE_GUIDE — Dựng và chạy demo `live` trên máy trình diễn (máy B)

> **Đối tượng đọc:** thành viên giữ máy có Neo4j + Qdrant + credentials LLM (máy B).
> **Vai trò máy B:** đây là **máy trình diễn**, chạy `DEMO_MODE=live` — đường chính lúc bảo vệ.
> `replay` là **lưới an toàn** khi `live` hỏng giữa buổi, không phải kịch bản chính (`ui/docs/UI_DEMO_SPEC.md` mục 0).
> **Ngày:** 2026-08-02

Mọi lệnh và tên biến dưới đây đọc từ code thật trong repo, không viết theo trí nhớ.
Đường dẫn tính từ thư mục gốc repo.

---

## 0. Điều kiện cần

| Thứ | Kiểm bằng | Ghi chú |
|---|---|---|
| Python 3.12 + `pip install -r requirements.txt` | `python -c "import sentence_transformers, neo4j, qdrant_client, anthropic, fastapi"` | Thiếu `sentence_transformers` là `_build_clients()` ném `ImportError` và `LiveAdapter` không dựng được |
| Docker Desktop đang chạy | `docker ps` | Ảnh dùng: `neo4j:5.18.0`, `qdrant/qdrant:v1.13.6` |
| Cổng trống: 7474, 7687, 6333, 6334, 8000 | `docker compose ps` | Xem mục 7 nếu trùng cổng |
| `.env` đã điền (mục 1) | `python scripts/preflight.py` | |
| `data/raw/*.md` có đủ | `ls data/raw/*.md \| wc -l` → **35** | 32 văn bản QPPL + 3 tệp tài liệu (`mapping_table`, `crossref_decisions`, `review_log`) — nên 35 tệp ra 32 Norm |
| Model BGE-M3 đã cache | `python scripts/preflight.py` | Lần đầu tải ~2,2 GB — **cần mạng**, làm trước buổi bảo vệ |

---

## 1. Khóa `.env`

Chép `.env.example` → `.env` rồi điền. Bảng dưới chỉ liệt kê khóa **code thật có đọc**
(`os.getenv` trong `src/` và `ui/`):

| Khóa | Bắt buộc | Giá trị | Ai đọc |
|---|---|---|---|
| `NEO4J_URI` | ✔ | `bolt://localhost:7687` | `src/pipeline._build_clients`, `ui/server._co_the_live` |
| `NEO4J_USER` | ✔ | `neo4j` | như trên |
| `NEO4J_PASSWORD` | ✔ | khớp `NEO4J_AUTH` trong `docker-compose.yml` | như trên |
| `QDRANT_HOST` | — | mặc định `localhost` | `_build_clients` |
| `QDRANT_PORT` | — | mặc định `6333` | `_build_clients` |
| `ANTHROPIC_API_KEY` | ✔ (nếu dùng Claude) | khóa Anthropic | SDK đọc trực tiếp; `LLM_API_KEY` là alias cũ |
| `LLM_MODE` | — | `claude` \| `claude-fallback` \| `gemini` \| `gemini-fallback` | `make_llm_client` khi không truyền `mode` |
| `GEMINI_API_KEY` | — | chỉ khi dùng Gemini Developer API | `make_llm_client` |
| `GEMINI_USE_VERTEX` | — | `true` → dùng Vertex qua ADC, **không** nhận api_key | `make_llm_client` |
| `GEMINI_VERTEX_PROJECT` / `GEMINI_VERTEX_LOCATION` | — | chỉ khi `GEMINI_USE_VERTEX=true` | `src/utils/gemini_fallback.py` |
| `DEMO_MODE` | — | `live` \| `replay` — **mode lúc khởi động** | `ui/server.tao_adapter` |
| `REPLAY_SPEED` | — | mặc định `4.0` | `ui/adapters._doc_speed` |
| `INGEST_LLM_MODE` | — | LLM cho ontology mapping lúc ingest | `src/ingestion/graph_builder.py` |

Hai điểm dễ nhầm:

- **`UI_PORT` trong `.env.example` KHÔNG được code nào đọc.** Cổng đặt bằng `--port` trên dòng lệnh `uvicorn`.
- **`EMBEDDING_MODEL` cũng không được đọc.** `src/ingestion/vectorizer.load_model()` hardcode mặc định `"BAAI/bge-m3"`. Đổi biến này trong `.env` sẽ không có tác dụng.

Với Vertex thì ngoài `.env` còn phải đăng nhập một lần:

```bash
gcloud auth application-default login
```

---

## 2. Dựng dữ liệu — ba bước, theo đúng thứ tự

```bash
# 2.1 — bật Neo4j + Qdrant                      (~20–40 giây)
docker compose up -d
docker compose ps                # cả hai phải ở trạng thái running/healthy

# 2.2 — dựng đồ thị Neo4j từ data/raw/*.md      (~5–15 phút, CÓ GỌI LLM)
python -m src.ingestion.graph_builder

# 2.3 — encode và nạp vector vào Qdrant         (~5–20 phút, tùy CPU/GPU)
python -m src.ingestion.vectorizer
```

**Chạy dạng module (`python -m ...`), không chạy thẳng đường dẫn tệp** — hai script này import theo package `src.*`.

**Chỗ nào idempotent:**

| Bước | Idempotent? | Vì sao |
|---|---|---|
| `docker compose up -d` | ✔ | Container đã chạy thì không dựng lại |
| `graph_builder` | ✔ | 23 câu Cypher đều `MERGE`, **không có `CREATE`** nào. Chạy lại cho cùng kết quả, không nhân đôi node |
| `vectorizer` | ✔ | `_ensure_collection()` chỉ tạo khi chưa có; ghi bằng `client.upsert` nên chạy lại là ghi đè, không nhân bản |

→ **Bị gián đoạn giữa chừng thì cứ chạy lại từ đầu bước đó.** Không cần xóa gì trước.

Lưu ý về `graph_builder`: Pass 4 (ontology mapping) **gọi LLM** cho từng Component, nên bước này
tốn khóa API và là phần chậm nhất. LLM dùng ở đây theo `INGEST_LLM_MODE` (mặc định lấy `LLM_MODE`,
cuối cùng lùi về `claude`).

Ước lượng thời gian ở trên là **khoảng chừng**, phụ thuộc máy và tốc độ API — chưa đo trên máy B.

---

## 3. Tự kiểm bằng preflight

```bash
python scripts/preflight.py            # đầy đủ (có nạp thử BGE-M3, chậm hơn)
python scripts/preflight.py --nhanh    # bỏ bước nạp thử model
```

Script chỉ đọc, **không sửa gì trong database**. Nó kiểm: Docker + hai container, kết nối Neo4j và
số Norm/Component/CTV/TextUnit + số cạnh, collection `legal_texts` (tồn tại / số điểm / số chiều),
các khóa `.env` còn thiếu, các package bắt buộc, cache BGE-M3, và số fixture trong `ui/fixtures/`.

Mỗi mục hỏng đều in kèm một câu chỉ cách sửa. **Exit code 1 nếu có mục bắt buộc hỏng**, 0 nếu chỉ
còn cảnh báo — dùng được trong script:

```bash
python scripts/preflight.py --nhanh && echo "SẴN SÀNG" || echo "CÒN LỖI, xem ở trên"
```

---

## 4. Ghi fixture (lưới an toàn)

Làm **trước** buổi bảo vệ, trên chính máy B:

```bash
# Một câu
python -m ui.record "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu?"

# Cả tệp danh sách (bỏ dòng trống và dòng bắt đầu bằng #)
python -m ui.record data/evaluation/demo_questions.txt --jurisdiction tp-hcm
```

Cờ có thật (`python -m ui.record --help`):

| Cờ | Giá trị |
|---|---|
| `--jurisdiction` | `toan-quoc` \| `tp-hcm` \| `dong-nai` |
| `--mode` | `general` \| `irac` (bỏ trống = để planner tự quyết) |
| `--verify` | bật Verifier agent |
| `--verify-tier` | `0` \| `1` \| `2` |
| `--llm-mode` | `claude` \| `claude-fallback` \| `gemini` \| `gemini-fallback` |
| `--llm-cache-dir` | mặc định `data/evaluation/.llm_cache` |
| `--no-llm-cache` | ép gọi LLM tươi |
| `--out-dir` | mặc định `ui/fixtures/` |
| `--overwrite` | ghi đè fixture đã có (mặc định bỏ qua nếu trùng tên) |

> ### ⚠ Cờ lúc ghi PHẢI khớp cờ lúc demo
>
> Hai lý do, cả hai đều làm hỏng buổi bảo vệ theo cách khác nhau:
>
> 1. **Cache LLM.** Khóa cache tính theo nội dung prompt, mà prompt phụ thuộc `--jurisdiction`,
>    `--mode`, `--verify`, `--llm-mode`. Ghi bằng một bộ cờ rồi demo bằng bộ khác → **cache MISS**,
>    câu hỏi phải gọi API thật ngay giữa buổi (chậm, và dính rủi ro 429/529). Ghi đúng cờ thì lúc
>    demo là **cache HIT, $0, gần như tức thì**.
> 2. **Khớp fixture lúc fallback.** `ReplayAdapter` tra fixture theo **câu hỏi** đã chuẩn hóa
>    (lowercase, bỏ dấu câu, gộp khoảng trắng, **giữ dấu tiếng Việt**). Câu nào chưa ghi thì lúc
>    bấm sang `replay` sẽ báo "chưa có fixture cho câu hỏi này".
>
> Nói gọn: **bộ cờ lúc `ui.record` = bộ cờ lúc demo = danh sách câu sẽ hỏi.**

Kiểm lại bằng `python scripts/preflight.py --nhanh` — mục 6 liệt kê fixture đang có, đánh dấu
fixture viết tay tạm, và chỉ ra câu nào trong `demo_questions.txt` còn thiếu fixture.

`ui/fixtures/*.json` **phải commit** (`ui/fixtures/` không nằm trong `.gitignore`) để máy A cũng
replay được.

### 4.1 Xóa fixture tạm sau khi đã ghi fixture thật — BẮT BUỘC

Trong repo có sẵn fixture **viết tay tạm** từ Task 3 (mang cờ `"tam": true`), dựng khi chưa có máy
nào chạy `live` được. Nội dung của nó là **số liệu bịa để test giao diện**, không phải một lượt
chạy thật.

**Vì sao phải xóa, chứ không chỉ để đó:**

Danh sách **chip gợi ý** hiện trên trang lấy thẳng từ `ui/fixtures/` (`ReplayAdapter.cau_hoi_co_san()`
→ `/api/mode` → `#goi-y`). Fixture tạm vì thế hiện thành **một chip trông y hệt chip thật** ngay
cạnh các câu đã chuẩn bị. Giữa buổi bảo vệ, bấm nhầm vào nó — hoặc để hội đồng bấm — sẽ trình ra
một câu trả lời bịa kèm trích dẫn bịa, đúng lúc không thể giải thích. Dải cảnh báo vàng
"FIXTURE TẠM" có hiện, nhưng đó là thứ dễ bỏ qua nhất trên màn hình khi đang nói.

```bash
# 1. Xem fixture nào đang mang cờ tạm
python scripts/preflight.py --nhanh      # mục 6 đánh dấu "(VIẾT TAY TẠM)"

# 2. Ghi đè bằng lượt chạy thật (khuyến nghị — giữ được câu hỏi đó)
python -m ui.record "<đúng câu hỏi trong fixture tạm>" --overwrite   # + cờ demo

# 3. Hoặc xóa hẳn nếu không định hỏi câu đó
git rm ui/fixtures/<tên-tệp>.json

# 4. Kiểm lại: mục 6 KHÔNG còn dòng "(VIẾT TAY TẠM)" nào
python scripts/preflight.py --nhanh
```

Chỉ nên còn fixture do `ui.record` sinh (`"mode": "live"`, có `recorded_at`, **không** có `"tam"`).
Việc này nằm trong danh sách kiểm ở mục 8.

---

## 5. Chạy demo

```bash
DEMO_MODE=live uvicorn ui.server:app --port 8000
```

PowerShell:

```powershell
$env:DEMO_MODE="live"; uvicorn ui.server:app --port 8000
```

Mở http://127.0.0.1:8000.

**Bật server sớm, đừng bật lúc đã vào phòng.** Lúc khởi động `LiveAdapter` dựng client và nạp
BGE-M3 **một lần cho cả process** (spec mục 2.2); nạp model mất hàng chục giây. Log phải có:

```
INFO ui.adapters: LiveAdapter: khởi tạo client (llm_mode=claude)…
INFO ui.adapters: LiveAdapter: client + BGE-M3 đã sẵn sàng.
INFO ui.server: UI sẵn sàng — mode=live
```

Dòng "client + BGE-M3 đã sẵn sàng" phải xuất hiện **đúng một lần**. Nếu nó lặp lại ở mỗi câu hỏi
thì vòng đời client đang sai.

Kiểm nhanh trước khi trình bày: hỏi thử một câu, xem đủ 7 bước, và xem **bước 3 có điểm số, bước 4
có danh sách norm, bước 6 có phân bổ pass**. Bước nào chỉ hiện dòng log mờ nghĩa là regex parse
chưa khớp log thật — báo lại để sửa `ui/trace.py` (**không sửa `src/`**).

---

## 6. Khi `live` hỏng giữa buổi — chuyển sang `replay`

Trên thanh trạng thái (dải màu tầng hai) có hai nút **`TRỰC TIẾP`** / **`PHÁT LẠI`**.
Bấm `PHÁT LẠI` → server đổi adapter tại chỗ, **không cần restart**.

- Badge đổi sang **PHÁT LẠI** nền vàng, kèm dải cảnh báo nói rõ đang phát lại từ fixture — hội đồng
  phải thấy được điều đó, không được để tưởng là chạy thật.
- Nhóm nút **tốc độ** `×1 ×2 ×4 ×8` hiện ra; tốc độ gửi kèm mỗi câu hỏi.
- Đổi ngược lại `TRỰC TIẾP` cũng bằng một nút.

Ba điều cần biết trước khi bấm:

1. **Không bấm được khi đang chạy một câu** — server trả `409` kèm "đợi câu đó chạy xong". Đợi câu
   hiện tại xong đã.
2. **Đổi hụt thì không mất gì.** Nếu dựng adapter mới hỏng, server **giữ nguyên adapter đang chạy**
   và chỉ hiện lỗi ra bảng lỗi.
3. **Chỉ những câu đã ghi fixture mới phát lại được.** Đây là lý do mục 4 phải làm trước.

Đường cứu cuối cùng nếu UI cũng không phản hồi: tắt server, chạy lại bằng
`DEMO_MODE=replay uvicorn ui.server:app --port 8000`.

---

## 7. Xử lý sự cố

### 7.1 LLM trả 429 / 529

Triệu chứng: bảng lỗi hiện "LLM trả lỗi 529…" hoặc 429; bước 7 không ra câu trả lời.

- SDK Anthropic đã tự thử lại: `ANTHROPIC_MAX_RETRIES = 8` (`src/utils/llm_config.py`) — nhiều hơn
  mặc định 2 của SDK. Hết 8 lần vẫn lỗi mới hiện ra UI.
- Cách xử lý ngay: **bấm `PHÁT LẠI`** (mục 6). Câu đã ghi fixture chạy lại được ngay.
- Đổi nhà cung cấp: khởi động lại với `LLM_MODE=claude-fallback` (Claude chính, Gemini đỡ khi
  Claude drop) hoặc `gemini-fallback` (Gemini chính, Claude đỡ khi Vertex hết quota — D-26).
- 429 phía Vertex thường là **hết quota**, chờ không giải quyết được; đổi sang `claude` hoặc dùng replay.
- Phòng ngừa: ghi fixture trước bằng đúng cờ demo → câu demo là cache HIT, gần như không gọi API.

### 7.2 Docker không lên

```bash
docker compose ps
docker compose logs neo4j    | tail -30
docker compose logs qdrant   | tail -30
```

- `docker ps` báo *"cannot find the file … dockerDesktopLinuxEngine"* → Docker Desktop chưa chạy.
  Mở nó lên, đợi icon hết quay rồi thử lại.
- Neo4j log có *authentication failure*: `docker-compose.yml` đặt
  `NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}` — tức là nó **nội suy từ chính `.env`**, nên hai bên
  không thể lệch nhau vì gõ sai. Nguyên nhân thật là **đổi mật khẩu SAU khi volume đã tạo**: Neo4j
  lưu mật khẩu trong volume và không đọc lại `NEO4J_AUTH` nữa. Cách sửa: hoặc trả `.env` về mật khẩu
  cũ, hoặc xóa volume rồi ingest lại (`docker compose down -v` — **xóa sạch đồ thị**, phải chạy lại
  mục 2.2 và 2.3).
- Neo4j lên chậm: bình thường mất ~20–30 giây sau `up -d` mới nhận kết nối bolt. Chạy lại preflight.

### 7.3 Thiếu package

```bash
pip install -r requirements.txt
```

- `No module named 'sentence_transformers'` → `_build_clients()` chết, `LiveAdapter` không dựng
  được, server **tự lùi về `replay`** (xem log `ui.server`). Đây chính xác là tình trạng máy A.
- `No module named 'google.genai'` → chỉ ảnh hưởng `--llm-mode gemini*`: `pip install google-genai`.
- Cài nhiều môi trường Python thì kiểm đúng cái đang chạy: preflight in `sys.executable` ở mục 5.

### 7.4 Trùng cổng

```bash
# Windows: xem ai giữ cổng 8000
netstat -ano | findstr :8000
```

- UI: đổi bằng `--port`, ví dụ `uvicorn ui.server:app --port 8010`. (`UI_PORT` trong `.env` **không**
  được đọc.)
- Neo4j/Qdrant: sửa phần `ports:` trong `docker-compose.yml`, rồi sửa `NEO4J_URI` / `QDRANT_PORT`
  trong `.env` cho khớp.
- Còn tiến trình uvicorn cũ chạy nền là nguyên nhân hay gặp nhất — tắt nó trước.

### 7.5 Chạy offline (không có mạng lúc bảo vệ)

Cái gì đã an toàn, cái gì không:

| Thành phần | Offline được? |
|---|---|
| Frontend (Tailwind, Cytoscape, font Be Vietnam Pro) | ✔ đã vendor về `ui/static/vendor/`, `index.html` không còn URL ngoài nào |
| Neo4j + Qdrant | ✔ chạy local trong Docker |
| **BGE-M3** | ✔ **chỉ khi model đã có trong cache HuggingFace** |
| **Gọi LLM** | ✘ luôn cần mạng — trừ khi câu hỏi đã có trong cache LLM |

Hai việc phải làm trước, khi còn mạng:

```bash
# 1. Nạp model một lần cho nó vào cache (preflight bỏ --nhanh sẽ làm việc này)
python scripts/preflight.py

# 2. Ghi fixture + làm nóng cache LLM cho đúng các câu sẽ hỏi
python -m ui.record data/evaluation/demo_questions.txt --jurisdiction tp-hcm
```

Khi đã có cache, ép chế độ offline cho HuggingFace để nó khỏi thử gọi hub và treo:

```bash
HF_HUB_OFFLINE=1 DEMO_MODE=live uvicorn ui.server:app --port 8000
```

```powershell
$env:HF_HUB_OFFLINE="1"; $env:DEMO_MODE="live"; uvicorn ui.server:app --port 8000
```

Preflight cảnh báo nếu thư mục cache `models--BAAI--bge-m3` chưa có hoặc nhỏ bất thường (bản đủ
khoảng 2,2 GB — nhỏ hơn nhiều nghĩa là tải dở).

**Không có mạng thì `live` chỉ chạy được câu đã cache LLM.** Câu mới sẽ lỗi ở bước 7. Nếu biết
chắc phòng bảo vệ không có mạng, kịch bản an toàn là chạy thẳng `replay`.

---

## 8. Danh sách kiểm trước khi vào phòng

- [ ] `docker compose ps` — Neo4j và Qdrant đều đang chạy
- [ ] `python scripts/preflight.py` — exit code 0, không còn mục ❌
- [ ] Fixture phủ **hết** câu sẽ hỏi, ghi bằng **đúng bộ cờ** sẽ dùng (preflight mục 6)
- [ ] **Không còn fixture nào mang cờ `tam`** — preflight mục 6 sạch dòng "(VIẾT TAY TẠM)" (mục 4.1). Nếu còn, nó sẽ hiện thành một chip gợi ý trông như thật trên UI.
- [ ] `git status` sạch, `ui/fixtures/*.json` đã commit và đẩy để máy A có
- [ ] Server đã bật sẵn, log có "client + BGE-M3 đã sẵn sàng" đúng một lần
- [ ] Hỏi thử một câu: đủ 7 bước, bước 3 có điểm, bước 4 có norm, bước 6 có phân bổ pass
- [ ] Bấm thử `PHÁT LẠI` rồi `TRỰC TIẾP` một lượt cho quen tay
- [ ] Nếu phòng có thể không có mạng: đặt `HF_HUB_OFFLINE=1` và xác nhận model nạp được
