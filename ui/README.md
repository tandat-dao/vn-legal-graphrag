# `ui/` — Demo trực quan pipeline GraphRAG

Trang web **một câu hỏi → 7 bước → câu trả lời có trích dẫn**, dùng cho buổi bảo vệ khóa luận.
Không có bước build, không có dependency npm, **không còn CDN** — copy thư mục sang máy khác là chạy.

Spec: `ui/docs/UI_DEMO_SPEC.md` (chức năng) · `ui/docs/UI_STYLE_SPEC.md` (giao diện).
Lịch sử chỉnh sửa: `ui/docs/UI_CHANGELOG.md` — **mỗi phiên sửa giao diện ghi một mục** (cái gì
hỏng, vì sao sửa vậy, kiểm chứng thế nào).

## Chạy

**Ngày bảo vệ — một lệnh duy nhất:**

```bash
./scripts/chay-demo.sh
```

Nó tự chọn đúng bản Python (bản `python3` mặc định của máy có thể thiếu deps), dựng Docker và
**chờ** hai CSDL trả lời, kiểm `.env`, rồi mở trình duyệt khi server thật sự sẵn sàng. Cổng đang
bận mà chính là UI này thì mở luôn thay vì dựng lại; bận bởi thứ khác thì báo rõ ai đang giữ.
Thêm `replay` để chạy không cần DB, thêm số để đổi cổng: `./scripts/chay-demo.sh replay 8010`.

Các lệnh thủ công bên dưới vẫn dùng được khi cần kiểm soát từng bước:

```bash
# Chế độ mặc định — phát lại fixture đã ghi sẵn, KHÔNG cần Neo4j/Qdrant/LLM
uvicorn ui.server:app --port 8000

# Chạy thật (chỉ ở máy có DB + credentials)
DEMO_MODE=live uvicorn ui.server:app --port 8000

# DEV: xem giao diện chế độ `live` trên máy KHÔNG có DB (dữ liệu vẫn là fixture)
python -m ui.run --port 8000 --devmode
```

> `uvicorn ui.server:app --devmode` **không chạy được** — `uvicorn` chỉ nhận cờ của chính nó và sẽ
> báo `No such option: --devmode`. Dùng launcher `python -m ui.run` (nó bọc `uvicorn.run()`), hoặc
> đặt thẳng biến: `DEMO_DEVMODE=1 uvicorn ui.server:app --port 8000`.

**Dev mode làm gì:** `DevAdapter` khai `mode = "live"` để trang đi đúng các nhánh giao diện của
`live` (badge `TRỰC TIẾP`, ẩn nhóm tốc độ, ẩn dải cảnh báo fixture, đổi mode qua lại được), nhưng
dữ liệu vẫn phát lại từ `ui/fixtures/`. Vì nó nói dối về `mode`, trang **luôn hiện một dải đỏ**
"CHẾ ĐỘ DEV" — đừng bỏ dải đó đi. `preflight.py` báo lỗi chặn nếu `DEMO_DEVMODE` còn bật.

Mở http://127.0.0.1:8000 → bấm một chip gợi ý (hoặc gõ câu hỏi) → **Hỏi**.

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `DEMO_MODE` | `replay` | Chế độ lúc khởi động: `replay` \| `live` |
| `REPLAY_SPEED` | `4.0` | Hệ số tua nhanh mặc định (đổi được trên UI) |

**Mọi thiết lập nằm ở bánh răng ⚙ góc phải header** — chế độ chạy (`TRỰC TIẾP` / `PHÁT LẠI`),
tốc độ phát lại (`×1 ×2 ×4 ×8`), bảng màu (A/B), cùng badge chế độ đang chạy. Thanh trạng
thái tầng hai đã bỏ.

> Vì badge nằm trong bảng thiết lập, **dải cảnh báo vàng dưới header là tín hiệu "đang phát
> lại" duy nhất luôn nhìn thấy**. Đừng bỏ hay làm nhạt nó.

**Không cần restart để đổi chế độ.** Nếu `live` dựng hỏng, server **giữ nguyên adapter đang
chạy** và trả lỗi ra bảng lỗi — bấm nhầm giữa buổi bảo vệ không làm mất demo.

## Hai máy

| | Máy A (trình diễn) | Máy B (có DB) |
|---|---|---|
| Có | code, `data/raw/`, fixtures | Neo4j + Qdrant đã ingest, LLM credentials |
| Chạy | `DEMO_MODE=replay` | `DEMO_MODE=live`, và `python -m ui.record` để ghi fixture |

Dự phòng lúc bảo vệ là **bản ghi màn hình một lượt `live` thật** (xem `ui/docs/LIVE_GUIDE.md` mục 6.1),
không phải `replay`. Ghi fixture nay là **tùy chọn** — chỉ làm nếu muốn thêm một đường dự phòng
tương tác được. `replay` vẫn là cách chạy UI ở máy không có DB.

```bash
# Ở MÁY B
python -m ui.record "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu?"
python -m ui.record --jurisdiction tp-hcm
```

Cờ: `--jurisdiction` `--mode {general,irac}` `--verify` `--verify-tier` `--llm-mode`
`--llm-cache-dir` `--no-llm-cache` `--out-dir` `--overwrite`.
**Cờ lúc ghi phải khớp cờ lúc demo** — chúng đi thẳng vào `run_pipeline`, đổi cờ là đổi kết quả.

## API

| Endpoint | Trả về |
|---|---|
| `GET /` | `static/index.html` |
| `GET /api/mode` | `mode`, `replay_speed`, `questions`, `dang_ban`, `co_the_live`, `loi_doi_mode` |
| `POST /api/mode` | `{"mode": "live"\|"replay"}` — đổi adapter tại chỗ. `400` sai giá trị · `409` đang chạy một câu · `503` dựng `live` hỏng (giữ adapter cũ) |
| `POST /api/ask` | **SSE** `data: {json}\n\n`, mỗi khung một `TraceEvent` |
| `GET /api/norm-graph` | `{nodes, edges}` toàn corpus — đồ thị bước 4 |
| `GET /api/text` | Nguyên văn Điều/Khoản/Điểm đọc thẳng từ `data/raw/*.md` (**không qua Neo4j**) |

`POST /api/ask` **serialize bằng lock cấp module, lấy kiểu không chờ**: hỏi chồng thì nhận ngay
event `kind="error"` (`loai: "dang-ban"`), không xếp hàng. `LiveAdapter` có **khóa thứ hai** cho
riêng `run_pipeline`, vì lock của server nhả ngay khi luồng SSE đóng — client ngắt giữa chừng thì
pipeline vẫn còn chạy, và để câu sau chen vào là trộn trace (spec mục 2.3).

## Tệp

```
server.py    FastAPI: 6 endpoint + lock + đổi adapter tại chỗ
adapters.py  BaseAdapter · ReplayAdapter (đọc fixtures/) · LiveAdapter (gọi run_pipeline nguyên bản)
record.py    CLI ghi fixture — CHẠY Ở MÁY B
trace.py     TraceCollector + parse log/context/citation → TraceEvent
corpus.py    load_corpus / norm_graph / get_component_text — đọc data/raw/*.md
fixtures/    lượt chạy đã ghi, mỗi câu một .json {question, params, events, result}
static/      index.html (toàn bộ frontend) + vendor/ (Tailwind, Cytoscape, font)
docs/        UI_DEMO_SPEC.md (đặc tả chức năng) · UI_STYLE_SPEC.md (đặc tả giao diện)
             DEMO_QUESTIONS.md — câu hỏi mẫu cho buổi bảo vệ, CHIA NHÓM (A/B/C/X)
```

### Sau khi clone, partner có gì

**Có — đều được commit:**

| Đường dẫn | Nội dung |
|---|---|
| `ui/**` (trừ `__pycache__`) | toàn bộ code + `static/vendor/` (~1 MB) + `fixtures/*.json` |
| `ui/docs/UI_DEMO_SPEC.md` | đặc tả chức năng — 7 task, hợp đồng `TraceEvent`, quy tắc đồng thời |
| `ui/docs/UI_STYLE_SPEC.md` | đặc tả giao diện — token màu, ràng buộc `id`/hook JS, checklist |
| `ui/docs/LIVE_GUIDE.md` | **đọc file này trước** — dựng và chạy `live` ở máy B |
| `scripts/preflight.py` | tự kiểm máy trước buổi bảo vệ |
| `tests/test_ui_*.py`, `tests/test_preflight.py` | test chạy được không cần DB |
| `.env.example` | mẫu cấu hình |

**Không có — bị `.gitignore` chặn, phải tự tạo:**

| Đường dẫn | Cách có |
|---|---|
| `.env` | `cp .env.example .env` rồi điền mật khẩu Neo4j + khóa LLM (mục 1 của `LIVE_GUIDE`) |
| `data/evaluation/.llm_cache/` | tự sinh khi chạy; cache rỗng nghĩa là câu đầu tiên phải gọi API thật |
| Volume Docker của Neo4j/Qdrant | `docker compose up -d` + ingest (mục 2 của `LIVE_GUIDE`) |
| Cache HuggingFace của BGE-M3 | tải tự động lần chạy đầu (~2,2 GB, **cần mạng**) |

> `data/raw/*.md` **có** trong repo — partner không phải thu thập lại; chỉ cần ingest.

`LiveAdapter` giữ **một** bộ client cho cả vòng đời process (`_build_clients()` gọi đúng một lần
lúc dựng adapter) và truyền vào `run_pipeline` qua keyword ở mỗi request — `load_model()` mất hàng
chục giây, để `run_pipeline` tự khởi tạo là phá buổi demo (spec mục 2.2).

Fixture chỉ chứa **event log**; đuôi `context`/`generate`/`verify`/`done` do `ReplayAdapter` dựng
lại từ `result` bằng `su_kien_ket_qua()`. Ghi cả hai sẽ làm replay phát trùng.

## Chạy offline

Toàn bộ tài nguyên đã nằm trong `static/vendor/` (~1 MB), `index.html` **không còn URL ngoài nào**:

```
vendor/tailwind.min.js       Tailwind Play CDN  (cdn.tailwindcss.com)
vendor/cytoscape.min.js      Cytoscape 3.30.2   (unpkg.com/cytoscape@3.30.2)
vendor/fonts/                Be Vietnam Pro 300–700, 15 woff2 (latin, latin-ext, vietnamese)
                             be-vietnam-pro.css đã sửa url() trỏ file cạnh nó
```

Đường dẫn phải là `/static/vendor/...`: `/` do `FileResponse` phục vụ chứ không nằm dưới mount
point, nên đường dẫn tương đối `vendor/...` sẽ 404.

Cần tải lại (đổi phiên bản chẳng hạn) thì lấy đúng ba nguồn trên; với font, tải CSS bằng
User-Agent trình duyệt để Google trả `woff2`, rồi tải từng `url()` về và sửa CSS trỏ file local.

## Sửa frontend — đọc trước khi động vào

`static/index.html` chỉ có ~100 dòng markup thật; **phần lớn HTML sinh bằng template literal trong
`<script>`**, còn màu đồ thị nằm trong **mảng `style` của Cytoscape** (hex thuần). Ràng buộc chi
tiết — `id` và hook JS không được đổi, quy tắc màu, checklist nghiệm thu — ở `ui/docs/UI_STYLE_SPEC.md`
mục 6 và 9. Ba cái dễ vấp nhất:

- **Chip gợi ý:** `b.textContent` **chính là câu hỏi gửi đi**. Chèn ký tự trang trí dạng text vào
  trong nút là làm sai đầu vào pipeline (và trượt khớp fixture ở replay). Trang trí bằng CSS.
- **Trạng thái bước:** JS gỡ cả `.buoc-cho` lẫn `.buoc-chay` khi xong và **không bao giờ gắn
  `.buoc-xong`** → "đã xong" = *không có class nào*.
- **Bảng màu A/B:** đổi vai trò token qua `data-theme` trên `<html>`. Cytoscape không đọc CSS var
  → mọi màu đồ thị đi qua `mauToken()` và phải `CY.style()` lại khi đổi chế độ.
- **`.nut-mau` nằm trên nền TRẮNG** (trong bảng thiết lập), không phải trên dải chrome tối như
  bản trước. Đừng bê lại kiểu `rgba(255,255,255,…)` cũ — trên nền trắng sẽ không đọc được.

## Trạng thái kiểm chứng

`pytest tests/ -q` → **606 pass, 2 skip** ở máy A (không cần DB, **không cần cả `.env`**).
Trong đó `tests/test_ui_live.py`
(35 test) phủ `LiveAdapter` + `record.py` bằng client giả, và `tests/test_preflight.py`
(23 test) phủ các nhánh "DB kết nối được" của preflight bằng Neo4j/Qdrant giả — những nhánh
chỉ thực sự chạy ở máy B.

**Đã chạy thật ở máy A:** replay end-to-end đủ 7 bước; `POST /api/mode` (400/409/503 + giữ adapter
cũ khi đổi hụt); nút tốc độ (×8 → 2,4s, ×1 → 9,1s); vendor phục vụ 200 và không còn URL ngoài.

**CHƯA kiểm chứng — cần chạy ở máy B** (máy A thiếu Neo4j/Qdrant/LLM và cả `sentence_transformers`,
nên `_build_clients()` chưa từng chạy thật ở đây):

```bash
# 1. LiveAdapter dựng được client thật (mục 2.2) và chạy hết một câu
DEMO_MODE=live uvicorn ui.server:app --port 8000
#    → kiểm: badge "TRỰC TIẾP"; đủ 7 bước; log startup có
#      "LiveAdapter: client + BGE-M3 đã sẵn sàng" ĐÚNG MỘT LẦN cho cả process.

# 2. Regex parse log khớp log THẬT của src/ (máy A chỉ thử được 3 dòng viết tay)
#    → kiểm: bước 3 có scores, bước 4 có danh sách norm, bước 5 có n_components,
#      bước 6 có phân bổ pass. Bước nào chỉ hiện dòng log mờ = regex chưa khớp.

# 3. record.py sinh fixture hợp lệ
python -m ui.record --jurisdiction tp-hcm
#    → kiểm: ui/fixtures/*.json có events + result; commit; máy A pull về replay đủ 7 bước.

# 4. Đổi live → replay → live trên UI khi đã có DB (máy A mới thử được chiều hỏng)

# 5. Lỗi LLM thật (429/529) ra event tiếng Việt gợi ý replay
#    (máy A chỉ thử bằng exception giả có thuộc tính status_code)

# 6. Rút mạng thật rồi tải lại trang
#    (máy A mới kiểm được ở mức: 0 URL ngoài trong HTML/CSS, vendor JS không
#     gọi fetch/XHR, mọi asset trả 200 từ localhost — chưa ngắt mạng vật lý)
```
