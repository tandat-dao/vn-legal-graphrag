# LIVE_GUIDE — Dựng và chạy demo `live` trên máy trình diễn (máy B)

> **Đối tượng đọc:** thành viên giữ máy có Neo4j + Qdrant + credentials LLM (máy B).
> **Vai trò máy B:** đây là **máy trình diễn**, chạy `DEMO_MODE=live` — đường chính lúc bảo vệ.
> **Dự phòng khi `live` hỏng giữa buổi: bản ghi màn hình một lượt chạy `live` thật, quay sẵn ở nhà.**
> Bạn **không cần đụng tới `replay`** — chế độ đó chỉ để dựng giao diện trên máy KHÔNG có dữ liệu.
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
| `DEMO_MODE` | — | đặt `live` để khởi động thẳng vào chế độ chạy thật | `ui/server.tao_adapter` |
| `GEMINI_MODEL_PLANNER` | `gemini-2.5-flash` | model cho ontology mapping lúc ingest (Pass 4) | `src/ingestion/ontology_mapper.py` |

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
tốn khóa API và là phần chậm nhất. LLM dùng ở đây là **Gemini Flash** (`GEMINI_MODEL_PLANNER`,
mặc định `gemini-2.5-flash`) — không phụ thuộc `LLM_MODE` của retrieval/demo.

Ước lượng thời gian ở trên là **khoảng chừng**, phụ thuộc máy và tốc độ API — chưa đo trên máy B.

---

## 3. Tự kiểm bằng preflight

```bash
python scripts/preflight.py            # đầy đủ (có nạp thử BGE-M3, chậm hơn)
python scripts/preflight.py --nhanh    # bỏ bước nạp thử model
```

Script chỉ đọc, **không sửa gì trong database**. Nó kiểm: Docker + hai container, kết nối Neo4j và
số Norm/Component/CTV/TextUnit + số cạnh, collection `legal_texts` (tồn tại / số điểm / số chiều),
các khóa `.env` còn thiếu, các package bắt buộc, và cache BGE-M3.

Mỗi mục hỏng đều in kèm một câu chỉ cách sửa. **Exit code 1 nếu có mục bắt buộc hỏng**, 0 nếu chỉ
còn cảnh báo — dùng được trong script:

```bash
python scripts/preflight.py --nhanh && echo "SẴN SÀNG" || echo "CÒN LỖI, xem ở trên"
```

---

## 4. Chạy demo

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

## 5. Quay bản ghi dự phòng

Sau khi mục 4 chạy ngon, quay màn hình **một lượt `live` thật cho từng câu sẽ trình bày**, rồi để
tệp ngay trên máy này. Đó là dự phòng khi buổi bảo vệ gặp sự cố (mục 6).

Quay toàn màn hình, thấy rõ URL `127.0.0.1:8000` và đủ 7 bước chạy từ đầu tới cuối.

> Không cần đụng tới `replay` hay `ui/fixtures/`. Chế độ đó chỉ dùng để dựng giao diện trên máy
> KHÔNG có dữ liệu; máy bạn có dữ liệu nên chạy thẳng `live`.

---

## 6. Khi `live` hỏng giữa buổi

1. **Thử chữa tại chỗ trước** — phần lớn sự cố ở mục 7 chữa được trong một phút: Neo4j rớt thì
   `docker compose up -d`, LLM 429/529 thì hỏi lại (SDK đã tự thử lại 8 lần).
2. **Không chữa được thì mở bản ghi màn hình** đã quay ở mục 5 và trình bày tiếp.

Nói thẳng khi chuyển sang bản ghi: *"đây là bản ghi một lượt chạy thật, máy hiện không kết nối được
DB nên tôi trình bằng bản ghi"*. Trung thực và dễ chấp nhận. Đổi lại, bản ghi **không trả lời được**
câu hội đồng hỏi ngoài kịch bản — cứ nói rõ như vậy.

---

## 7. Xử lý sự cố

### 7.1 LLM trả 429 / 529

Triệu chứng: bảng lỗi hiện "LLM trả lỗi 529…" hoặc 429; bước 7 không ra câu trả lời.

- SDK Anthropic đã tự thử lại: `ANTHROPIC_MAX_RETRIES = 8` (`src/utils/llm_config.py`) — nhiều hơn
  mặc định 2 của SDK. Hết 8 lần vẫn lỗi mới hiện ra UI.
- Cách xử lý ngay: hỏi lại sau vài giây; không được thì dùng bản ghi màn hình (mục 6).
- Đổi nhà cung cấp: khởi động lại với `LLM_MODE=claude-fallback` (Claude chính, Gemini đỡ khi
  Claude drop) hoặc `gemini-fallback` (Gemini chính, Claude đỡ khi Vertex hết quota — D-26).
- 429 phía Vertex thường là **hết quota**, chờ không giải quyết được; đổi sang `claude`.
- Phòng ngừa tốt nhất: **chạy trước ở nhà đúng những câu sẽ hỏi với đúng bộ cờ sẽ dùng** → lúc demo
  là cache LLM HIT, gần như không gọi API nên không dính 429/529.

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
  được, server **tự lùi về chế độ không-DB** (xem log `ui.server`) — badge sẽ KHÔNG phải `TRỰC TIẾP`.
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

# 2. Làm nóng cache LLM: chạy trước đúng các câu sẽ hỏi, với đúng bộ cờ sẽ dùng
#    (mở UI và hỏi từng câu một lượt là đủ)
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
chắc phòng bảo vệ không có mạng, hãy chuẩn bị sẵn bản ghi màn hình ở mục 5.

---

## 8. Danh sách kiểm trước khi vào phòng

- [ ] `docker compose ps` — Neo4j và Qdrant đều đang chạy
- [ ] `python scripts/preflight.py` — exit code 0, không còn mục ❌
- [ ] **`DEMO_DEVMODE` đã TẮT** (preflight mục 2 kiểm). Bật nó thì `live` chỉ là giả lập —
      trang hiện `TRỰC TIẾP` trong khi không hề gọi Neo4j/Qdrant/LLM.
- [ ] **Đã quay sẵn bản ghi màn hình** một lượt `live` thật cho từng câu sẽ trình (mục 5), và
      bản ghi nằm ngay trên máy trình diễn — không phải trên cloud cần mạng mới mở được
- [ ] Server đã bật sẵn, log có "client + BGE-M3 đã sẵn sàng" đúng một lần
- [ ] Hỏi thử một câu: đủ 7 bước, bước 3 có điểm, bước 4 có norm, bước 6 có phân bổ pass
- [ ] `git status` sạch
- [ ] Nếu phòng có thể không có mạng: đặt `HF_HUB_OFFLINE=1` và xác nhận model nạp được
