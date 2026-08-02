# UI_DEMO_SPEC — Web UI trình diễn pipeline cho buổi bảo vệ

> **Đối tượng đọc:** Claude Code (hoặc người implement).
> **Trạng thái:** spec chốt, chờ implement. Mọi quyết định trong file này đã được cân nhắc — nếu thấy cần đi ngược lại một quyết định, DỪNG và hỏi người dùng trước, đừng tự đổi.
> **Ngày:** 2026-07-26

---

## 0. Mục tiêu

Dựng một web UI **một process** để trình diễn hệ thống trong buổi bảo vệ khóa luận. Yêu cầu cốt lõi của người dùng:

1. Showcase được **luồng xử lý từ câu hỏi ra câu trả lời** — 7 bước, hiện dần theo thời gian thực, tạo cảm giác "thinking process".
2. Chạy được ở **hai chế độ**: `live` (có DB — **đường chính lúc bảo vệ**) và `replay` (không cần DB — **lưới an toàn** + môi trường phát triển) — cùng một codebase, đổi bằng biến môi trường **hoặc bấm nút trên UI, không cần restart** (Task 5).
3. Đây là **demo**, không phải sản phẩm. Không cần auth, không cần multi-user, không cần CI, không cần test coverage cao. Ưu tiên: chạy được, trông thuyết phục, không sập giữa buổi bảo vệ.

### Bối cảnh hai máy

> **Cập nhật 2026-08-02 — đảo vai trò so với bản đầu.** Bản đầu của spec này giả định máy A trình diễn bằng `replay`. Không còn đúng: **máy B là máy trình diễn và `live` là đường chính.**

- **Máy B** (bạn cùng nhóm) — **MÁY TRÌNH DIỄN**: có Neo4j + Qdrant đã ingest + LLM credentials. Buổi bảo vệ chạy `DEMO_MODE=live` trên máy này.
- **Máy A** (Windows) — **MÁY PHÁT TRIỂN**: có code + `data/raw/` + `data/evaluation/`, **Neo4j và Qdrant rỗng**, thiếu cả `sentence_transformers`. Không chạy `live` được; dùng `replay` để dựng và test giao diện.

Hệ quả:

1. **`replay` là lưới an toàn, không phải đường trình diễn.** Vai trò của nó: (a) máy A phát triển UI không cần DB; (b) khi `live` hỏng giữa buổi (Neo4j rớt, LLM 429/529, mạng chết) thì bấm một nút trên thanh trạng thái là về `replay` chạy tiếp — xem Task 5. Fixture vì thế vẫn **bắt buộc phải ghi trước** và commit, dù kịch bản chính không dùng tới.
2. **Fixture phải ghi trên chính máy B, với đúng bộ cờ sẽ dùng lúc demo.** Cờ lệch thì lúc fallback câu hỏi không khớp fixture, và cache LLM cũng không HIT.
3. **Máy B phải chạy `scripts/preflight.py` trước buổi bảo vệ** để biết Docker/Neo4j/Qdrant/`.env`/BGE-M3 đã sẵn sàng chưa. Quy trình dựng máy B từ đầu: `ui/docs/LIVE_GUIDE.md`.
4. Phần lớn thứ **chưa kiểm chứng được ở máy A** đều nằm ở đường `live` (regex parse log thật, `_build_clients()`, lỗi LLM thật) — danh sách ở cuối `ui/README.md`, phải chạy ở máy B.

---

## 1. Nguyên tắc bất biến

Vi phạm những điều này làm hỏng giá trị học thuật của bản demo:

1. **KHÔNG sửa bất cứ gì trong `src/`.** Toàn bộ code mới nằm trong `ui/`. Nếu thấy "chỉ cần thêm một tham số vào `run_pipeline` là xong" — không. Lý do: `src/` là code đã sinh ra số liệu trong `docs/V2_RESULTS.md`; sửa nó là làm mất tính tái lập của luận văn.

2. **Chế độ `live` PHẢI gọi `src.pipeline.run_pipeline()` nguyên bản.** Không gọi lẻ `stage1_norm_ids` / `stage2_norm_ids` / `hybrid_search` rồi tự ghép. `src/evaluation/instrument_retrieval.py` có làm vậy, nhưng nó **copy lại tầng temporal của `pipeline.py`** (xem comment "sao chép từ pipeline.py" trong file đó) — nếu bản copy lệch thì demo sẽ hiển thị kết quả khác Chương 4 của luận văn. Đừng đi đường đó.

3. **KHÔNG bịa "luồng suy nghĩ".** Hệ thống này không có chain-of-thought. Hai lần gọi LLM là query planner (trả JSON) và answer generator (trả câu trả lời). Mọi thứ hiển thị trong panel trace PHẢI đến từ event log thật hoặc `PipelineResult` thật. **Tuyệt đối không gọi LLM để sinh văn tự thuật kiểu "Tôi đang cân nhắc…".** Nếu hội đồng hỏi "đó là suy luận thật của hệ thống hay văn LLM sinh ra", câu trả lời phải là "event log thật".

4. **KHÔNG lấy trace từ `data/evaluation/results_*.json`.** File đó không có `query_plan`, không có điểm Stage 1, không có danh sách norm Stage 2, không có phân bổ pass. Nó *có* hai field tên `theme` và `jurisdiction` — nhưng đó là **nhãn ground truth copy từ `test_set_v2.json`**, KHÔNG phải output của planner. Hiển thị chúng ở bước "Query Planner" là trình bày đáp án như thể là kết quả của hệ thống. Fixture cho `replay` phải do `ui/record.py` sinh ra (mục 4.2).

5. **Không dùng `localStorage` / `sessionStorage`.** Giữ toàn bộ state trong biến JS trong bộ nhớ.

6. **Tiếng Việt** cho mọi text hiển thị, comment và docstring — theo `CLAUDE.md` của repo.

7. **Không hardcode credentials.** Đọc từ `.env` qua `python-dotenv`, giống `src/pipeline.py`.

---

## 2. Kiến trúc

```
ui/
├── __init__.py
├── server.py       # FastAPI app + các endpoint
├── trace.py        # logging.Handler → TraceEvent có cấu trúc
├── adapters.py     # LiveAdapter | ReplayAdapter (cùng interface)
├── record.py       # CLI ghi fixture, CHẠY Ở MÁY B
├── corpus.py       # đọc data/raw/*.md → norm graph + tra nguyên văn Điều/Khoản
├── fixtures/       # *.json do record.py sinh — commit vào git
└── static/
    └── index.html  # toàn bộ frontend trong 1 file
```

Chọn bằng env var, thêm vào `.env` và `.env.example`:

```
DEMO_MODE=replay        # replay | live — chỉ là mode LÚC KHỞI ĐỘNG.
                        # Máy B (trình diễn) đặt live; máy A để replay.
                        # Đổi lúc đang chạy bằng POST /api/mode (Task 5).
UI_PORT=8000
```

Chạy: `uvicorn ui.server:app --port 8000`

### 2.1 Frontend

Một file `ui/static/index.html`. Tailwind và Cytoscape.js **đã vendor về `ui/static/vendor/`** (Task 5 đã làm — không còn CDN nào). **Không npm, không build step** — để copy thư mục sang máy khác là chạy được ngay, kể cả khi máy đó không có internet.

Nếu về sau cần thư viện khác: tải về `ui/static/vendor/` và tham chiếu `/static/vendor/…` (đường dẫn tương đối `vendor/…` sẽ 404 vì `/` do `FileResponse` phục vụ, không nằm dưới mount point). **Không thêm thẻ trỏ ra CDN** — máy trình diễn có thể không có mạng lúc bảo vệ.

### 2.2 Vòng đời client

`LiveAdapter` khởi tạo Neo4j driver, Qdrant client, LLM client và **BGE-M3 model một lần duy nhất lúc startup** (FastAPI lifespan), rồi truyền vào `run_pipeline(...)` qua keyword args ở mỗi request. Không được để `run_pipeline` tự khởi tạo client mỗi lần — `load_model()` mất hàng chục giây, sẽ phá buổi demo.

`run_pipeline` đã nhận sẵn các tham số này (`neo4j_driver`, `qdrant_client`, `anthropic_client`, `model`) và chỉ tự khởi tạo khi `neo4j_driver is None`. Dùng lại `src.pipeline._build_clients(llm_mode)` để tạo — nó trả tuple 4 phần tử `(neo4j_driver, qdrant_client, anthropic_client, model)`.

### 2.3 Vòng đời request và đồng thời — BẮT BUỘC

`logging.getLogger("src")` là **toàn cục theo process**. Hai request `/api/ask` chồng nhau sẽ làm hỏng trace theo hai cách cùng lúc: log record của cả hai pipeline rơi vào cùng một queue (event câu A và câu B trộn trong một luồng SSE), và việc đặt lại mốc thời gian cho câu B khiến `t` của câu A âm, `seq` nhảy lùi. Đây là lỗi **vỡ ngay trước mặt hội đồng**, không phải lỗi biên.

Ba quy tắc, áp dụng cho **cả `live` lẫn `replay`** — bấm đúp trong lúc phát lại cũng loạn stream y hệt:

1. **Serialize `/api/ask` bằng lock cấp module.** Thử lấy lock kiểu **không chờ**: request đến trong lúc đang chạy thì trả ngay một event `kind="error"` với thông báo "đang xử lý câu trước", **không xếp hàng** (xếp hàng chỉ dời cơn loạn sang muộn hơn và làm người trình bày tưởng hệ treo). Nhả lock trong `finally` của generator. Frontend khóa nút Hỏi trong lúc stream.

2. **Mỗi request một `TraceCollector` mới.** `addHandler` lúc bắt đầu, `removeHandler` trong `finally` — dùng context manager `ui.trace.gan_collector()`. **KHÔNG** dùng một collector dùng chung rồi `reset()`. Nếu quên `removeHandler`, handler tích lũy qua từng câu: hỏi 50 câu thì có 50 handler cùng phát → event nhân bản và bộ nhớ phình.

3. **Frontend KHÔNG dùng `EventSource`.** Nó chỉ làm được GET (không truyền được câu hỏi + tham số trong body) và **tự động kết nối lại** khi stream đóng — nghĩa là hết một câu nó sẽ tự chạy lại câu đó, đúng lúc đang trình bày. Dùng `fetch()` POST rồi đọc `response.body.getReader()`, tự tách khung `data: …\n\n`.

---

## 3. Bảy bước và nguồn dữ liệu

Đây là phần quan trọng nhất của spec. Mỗi bước chỉ được hiển thị dữ liệu có nguồn thật. Cột "Nguồn" là bắt buộc.

| # | Bước | Hiển thị | Nguồn |
|---|------|----------|-------|
| 1 | Câu hỏi | câu hỏi, jurisdiction ép (nếu có), response_mode | input request |
| 2 | Query Planner | theme, jurisdiction, procedure, temporal_intent, temporal đã resolve, response_mode | `PipelineResult["query_plan"]` + `PipelineResult["response_mode"]`; quyết định temporal lấy từ log `TEMPORAL MODE` |
| 3 | Stage 1 — Qdrant summary | danh sách norm seed + điểm similarity + ngưỡng 0.3, chỉ rõ norm nào bị loại | log `Stage 1:` (có cả `scores=[...]` và `norm_ids = [...]`) |
| 4 | Stage 2 — Graph traversal | seed → bung qua `IMPLEMENTS\|AMENDS*1..4` → lọc jurisdiction + temporal → norm còn lại; vẽ trên đồ thị | log `Stage 2 (norm_ids):` cho tập kết quả + tham số lọc; cạnh đồ thị từ `ui/corpus.py` |
| 5 | Stage 3 — Procedure mapping | số component được boost, procedure id | log `Stage 3:` |
| 6 | Hybrid search + Context | bảng các block context (nhãn, tier, hiệu lực, cảnh báo sửa đổi, nguyên văn), thanh token budget, phân bổ 4 pass | bảng: **parse từ `PipelineResult["context"]`** (mục 5.2); phân bổ pass: log `hybrid_search: top-N \| pass-1(...)...` |
| 7 | Câu trả lời | answer markdown, citation chip, verifier | `PipelineResult["answer"]`, `["citations"]`, `["verifier"]` |

### 3.1 Giới hạn phải tôn trọng ở bước 6

`PipelineResult` **không chứa** list `ScoredTextUnit` của `hybrid_search`. Nó chỉ có `top_k_count` và `context` (string đã ghép).

Hệ quả — nói rõ để không tự bịa:

- **Có**: nhãn từng block (Điều/Khoản/Điểm + norm slug), tier, `valid_from`/`valid_to`, cờ `(HẾT HIỆU LỰC)`, block cảnh báo sửa đổi, nguyên văn, thứ tự block (chính là thứ tự rrf giảm dần).
- **Có**: tổng số block mỗi pass, `best rrf`, `tier_dist`, `norm_dist` — từ dòng log `hybrid_search:`.
- **KHÔNG có**: `rrf_score` của **từng** block, và **pass nào** sinh ra **từng** block cụ thể.

→ Bước 6 hiển thị **bảng block** (không có cột rrf per-block) cộng **một dải phân bổ pass dạng tổng hợp** (ví dụ: `struct-cite 2 · dense-floor 9 · rrf-breadth 6 · depth 8`). **Không gắn badge pass cho từng dòng** — dữ liệu đó không tồn tại. Nếu badge per-dòng là bắt buộc, phải hỏi người dùng trước, vì đường duy nhất để có nó là sửa `src/`, mà mục 1.1 cấm.

### 3.2 Thứ tự norm ở bước 4 KHÔNG phải xếp hạng

`stage2_norm_ids()` trả về `list({row["norm_id"] for row in rows})` — dựng từ **set**, nên thứ tự phụ thuộc hash randomization và **đổi giữa các lần chạy**. Đó là một *tập hợp* các norm sống sót sau lọc jurisdiction + temporal, không có điểm số nào.

Hệ quả cho frontend:

- Hiển thị dạng tập hợp: sắp theo **tier** (1→4) hoặc **alphabet**, và nói rõ tiêu chí sắp xếp là của UI.
- **KHÔNG** đánh số `1.` `2.` `3.`, không dùng từ "top", không xếp thứ tự dọc gợi ý mức độ liên quan — hội đồng sẽ đọc đó là xếp hạng, mà hệ thống không hề xếp hạng ở bước này.
- Phân biệt với **bước 3**: Stage 1 có `scores` thật theo rank → ở đó đánh số và hiện điểm là đúng.

### 3.3 Lớp hiển thị tên văn bản

`luat-dat-dai-2024` là **ID kỹ thuật**, không phải thứ đọc lên trước hội đồng. Bảng đầy slug làm người xem phải tự dịch trong đầu suốt buổi. Đổi sang tên thật ở **lớp hiển thị**, không đụng dữ liệu.

**Làm ở frontend, không ở backend.** Nguồn tên là `/api/norm-graph` (đã có `title` + `so_hieu` cho cả 32 văn bản, gọi một lần lúc khởi động). Backend không cần thêm endpoint, không cần đổi `TraceEvent`, và `ui/record.py` không phải ghi lại fixture khi tên hiển thị đổi.

**Quy tắc dựng tên:**
- `so_hieu` **chưa** nằm trong `title` → nối trong ngoặc: `Luật Đất đai` + `31/2024/QH15` → `Luật Đất đai (31/2024/QH15)`.
- `title` **đã** chứa `so_hieu` → để nguyên: `Nghị định 102/2024/NĐ-CP` (không thành `Nghị định 102/2024/NĐ-CP (102/2024/NĐ-CP)`).
- Hai Norm ra cùng một tên → thêm `theme` để phân biệt. Ca thật: D-23 tách NQ 124/2016 TP.HCM thành `-datdai` và `-hotich`, cùng `title` lẫn `so_hieu`.
- **Slug không có trong corpus → giữ nguyên.** Đây là tín hiệu thật (LLM cite văn bản ngoài corpus), không được che bằng cách đoán tên.

**Thay bằng MỘT lượt `replace` với regex alternation, sắp theo độ dài GIẢM DẦN.** Không lặp `.replace()` từng slug — 32 lượt quét chuỗi vừa chậm vừa sai: `nghi-quyet-124-2016-nq-hdnd-tp-hcm` khớp trước sẽ ăn mất phần `-datdai` của slug dài hơn và để lại rác `-datdai` lửng lơ. Ở bước 7 dùng alternation `citation | slug` để cùng một lượt vừa dựng chip trích dẫn vừa đổi slug lọt trong văn xuôi; `String.replace` không quét lại phần vừa chèn nên slug nằm trong `data-vb` của chip không bị đụng.

**Áp dụng cho bước 3, 4, 6, 7** (Stage 1, Stage 2 + nhãn đồ thị, bảng block context, chip trích dẫn + văn xuôi câu trả lời) và panel nguyên văn. Slug gốc vẫn luôn tra được: để ở `title=` tooltip, và ở panel bên phải in dưới tên bằng chữ mono.

**KHÔNG đổi `citation.van_ban`.** Giá trị đó là dữ liệu — dùng để nối citation → block và để gọi `/api/text`. Chỉ *nhãn* đổi; `data-vb` giữ slug.

**Nút "Nguyên văn LLM"** ở bước 7: bật lên thì hiện đúng chuỗi `PipelineResult["answer"]` — slug nguyên bản, markdown chưa render, không chip. Có lớp hiển thị thì phải có đường xem bản gốc: nếu hội đồng hỏi "LLM có thật sự trả về tên văn bản đó không", bấm một nút là thấy nó viết `quyet-dinh-69-2024-qd-ubnd-tp-hcm`, và thấy luôn là hệ **bắt buộc LLM cite bằng slug** (quy tắc trong system prompt) chứ không phải LLM tự viết tên đẹp.

---

## 4. Hợp đồng dữ liệu

### 4.1 TraceEvent

Cả `live` và `replay` phát ra **cùng một** dòng event. Frontend chỉ biết loại này, không biết mode nào đang chạy.

```python
{
  "seq": 0,                  # int, tăng dần
  "t": 1.234,                # float, giây kể từ lúc bắt đầu request
  "step": "stage1",          # xem enum bên dưới
  "kind": "log",             # "log" | "result" | "error" | "done"
  "raw": "Stage 1: top-5 …", # message log gốc, luôn giữ để đối chiếu
  "data": {...}              # dict đã parse; {} nếu không parse được
}
```

`step` ∈ `question`, `plan`, `temporal`, `stage1`, `stage2`, `stage3`, `hybrid`, `context`, `generate`, `verify`, `done`.

Nguyên tắc: **`raw` luôn được giữ nguyên**. Nếu regex không khớp, vẫn phát event với `data={}` và cho frontend hiện `raw` ở dạng dòng log mờ. Không được im lặng bỏ event — thà hiện thô còn hơn mất thông tin.

### 4.2 Fixture

`ui/fixtures/<slug-câu-hỏi>.json`:

```json
{
  "question": "…",
  "recorded_at": "2026-07-20T10:00:00",
  "mode": "live",
  "params": {"force_jurisdiction": null, "response_mode": null, "verify": false, "llm_mode": "claude-fallback"},
  "events": [ /* TraceEvent, đúng thứ tự, có t thật */ ],
  "result": { /* PipelineResult nguyên vẹn, kể cả context đầy đủ */ }
}
```

Fixture do `ui/record.py` sinh trên máy B. Commit vào git (`ui/fixtures/` KHÔNG được thêm vào `.gitignore`).

Vì `live` là đường chính (mục 0), fixture tồn tại để **đỡ lúc `live` hỏng giữa buổi**. Do đó nó phải phủ **đúng những câu sẽ trình bày** và ghi bằng **đúng bộ cờ sẽ dùng** — lệch một cờ là lúc fallback không tìm thấy fixture.

`ReplayAdapter` phát lại đúng chuỗi `events` đó. Về thời gian: dùng `t` thật nhưng **chia cho `REPLAY_SPEED` (mặc định 4.0)**, vì một câu chạy thật mất ~22s. Frontend PHẢI hiện badge "PHÁT LẠI" khi ở chế độ này — không được để hội đồng tưởng là đang chạy live. Điều này càng quan trọng khi `live` là mặc định: nếu giữa buổi phải fallback, hội đồng phải thấy ngay là hệ đã đổi sang phát lại.

---

## 5. Các định dạng phải parse

Trích nguyên văn từ code hiện tại. **Đừng đoán, đừng tự sửa cho "đẹp hơn".** Nếu một regex không khớp lúc chạy thật, sửa regex — đừng sửa `src/`.

### 5.1 Log records

Handler gắn vào logger `"src"`, giống `src/demo.py`:

```python
logging.getLogger("src").setLevel(logging.INFO)
logging.getLogger("src").addHandler(handler)
```

Lấy message bằng `record.getMessage()`.

**Khác với `demo.py`: KHÔNG lọc theo danh sách keyword.** `demo._TraceHandler` lọc bằng `("plan_query", "Stage 1", …, "Pass -", …)`; danh sách đó có mục chết (`"Pass -"` không khớp gì, vì log thật viết `Path -1` và `pass-1(...)`) và sẽ mục ruỗng thêm khi `src/` thay đổi. Thay vào đó: **bắt mọi record INFO của logger `src`**, rồi phân loại bằng regex. Record nào không khớp → `step` suy từ tên logger (`record.name`), `data={}`.

Các dòng cần parse (nguyên văn từ `src/`):

```
run_pipeline: plan=<theme>/<jurisdiction>
run_pipeline: response_mode='<mode>'
run_pipeline: force_jurisdiction='<j>' áp dụng
run_pipeline: TEMPORAL MODE — anchor='<a>' status='<s>' → <reason>
Stage 1: top-<n> scores=[0.712, 0.688, …], threshold=0.3 → <k> norm_ids = ['<id>', …]
Stage 1 [no-theme]: <k> norm_ids = ['<id>', …]
Stage 2 (norm_ids): <n> norms (jurisdiction=<j>, temporal=<t>): ['<id>', …]
Stage 3: <n> graph_component_ids mapped for procedure <proc_id>
run_pipeline: <n> norm_ids, <m> graph_comp_ids từ Stage 2+3
hybrid_search Path -1 (struct cite): cites=[…] → <n> comps → <m> text_units
hybrid_search: dense=<n>, keyword=<m>, graph=<k> candidates
hybrid_search: rarity stats — <n> norms, <m> components mapped, <k> required concepts
hybrid_search: top-<N> | pass-1(struct-cite)=<a>, pass-0.5(label-keyword)=<b>, pass0(dense-floor)=<c>, pass1(rrf-breadth)=<d>, pass2(depth)=<e> | caps: per_norm=3, per_tier={1: 8, 2: 8, 3: 6, 4: 8} | best rrf=<f> | tier_dist={…} | norm_dist={…}
assemble_context: <n> blocks, ~<m> tokens
assemble_context: dừng tại <n> blocks (<m>/6000 tokens)
generate_answer: cache HIT (<key>) — $0 API
generate_answer: <n> chars, <k> citations, sections={…}
run_pipeline: verifier tier=<T> <n>→<m> citations (drop <x>, flag <y>)
run_pipeline: hoàn thành trong <X.X>s — <n> citations
```

Ghi chú:
- Dòng `Stage 1` có **cả** `scores` (theo thứ tự rank) **và** `norm_ids` (đã lọc ≥ ngưỡng). Số phần tử của hai list **có thể khác nhau** — `scores` là toàn bộ top-n, `norm_ids` chỉ những cái vượt `threshold`. Ghép theo thứ tự để biết cái nào bị loại.
- `generate_answer: cache HIT` cho biết câu này $0 — hiện lên UI thì rất có lợi khi trình bày.
- `temporal=None` in ra literal `None` (Python repr), không phải `null`.
- `dừng tại … blocks` chỉ xuất hiện khi context bị token budget cắt.

### 5.2 Block context

`assemble_context()` ghép các block bằng `"\n\n"`. Mỗi block:

```
--- <label> ---
<nguyên văn>
```

hoặc khi component có amendment:

```
--- <label> ---
[AMENDMENT WARNING — nội dung Component này đã/sắp bị sửa đổi:]
  - <amending_norm> (<amending_loc>, hiệu lực <YYYY-MM-DD>): <content_summary>
<nguyên văn>
```

`<label>` có ba dạng (từ `_format_citation_label`):

```
[Tier 4 | Hiệu lực: 2024-09-30] Điều 3, Khoản 1 (quyet-dinh-69-2024-qd-ubnd-tp-hcm)
[Tier 1 | Hiệu lực: 2014-07-01 → 2025-01-01 (HẾT HIỆU LỰC)] Điều 95 (luat-dat-dai-2013)
luat-dat-dai-2024
```

Dạng thứ ba xảy ra khi `context_path` rỗng **và** không có tier/valid_from → label chỉ là norm slug, **không có** prefix `[...]`. Parser phải chịu được cả ba. `valid_to == "9999-12-31"` là sentinel nghĩa là còn hiệu lực → không in mũi tên.

Từ mỗi block, trích: `tier`, `valid_from`, `valid_to`, `het_hieu_luc` (bool), `vi_tri` (phần "Điều 3, Khoản 1"), `norm_id`, `amendments[]`, `text`.

### 5.3 Citation

`PipelineResult["citations"]` là `list[dict]`, keys chính xác:

```python
{"dieu": "116", "khoan": "5", "diem": None, "tiet": None,
 "van_ban": "luat-dat-dai-2024", "loai": "dieu"}
```

`loai` ∈ `"dieu"` | `"phu_luc"`. Khi `loai == "phu_luc"`, `dieu` chứa số/ký hiệu Phụ lục (hoặc `"_default"`). Định dạng inline trong answer text: `[Điều X, Khoản Y, Điểm Z, Văn bản slug]`, **thứ tự các phần có thể đảo**.

Ghép citation → block context (cho tính năng bấm chip ở bước 7): so `van_ban` với `norm_id` của block, và so `dieu`/`khoan`/`diem` với `vi_tri` đã parse. Khớp **lỏng**: nếu chỉ khớp được Điều mà không khớp Khoản thì vẫn nối tới block của Điều đó và đánh dấu là khớp gần đúng. Citation không khớp block nào → hiện chip màu khác kèm chú thích "không tìm thấy trong context" (đây là tín hiệu thật, có ý nghĩa, không phải bug cần che).

### 5.4 Frontmatter `data/raw/*.md`

```yaml
id, title, so_hieu, tier, theme, jurisdiction, implements,
valid_from, valid_to, source_url, source_vbhn, amended_by_norms, summary
```

`implements` và `amended_by_norms` có thể là **string, list, hoặc null** — xử lý phòng vệ cả ba. Thân bài: `## Điều N. <tiêu đề>`, cấp dưới `### Khoản N.`. Dùng để (a) dựng đồ thị norm cho bước 4 mà **không cần Neo4j**, (b) tra nguyên văn Điều/Khoản khi bấm citation.

Không dùng thư viện YAML nếu tránh được — frontmatter đơn giản, tự tách giữa hai dòng `---` rồi split `: ` là đủ. Nếu dùng thì `pyyaml` đã có trong `requirements.txt`, kiểm tra trước.

---

## 6. Task

Làm theo thứ tự. Task 1–3 test được hoàn toàn ở máy A không cần DB — làm xong 3 task này là đã có UI xem được. **Task 4–5 chỉ nghiệm thu trọn vẹn được ở máy B**, vì đó là nơi có DB và là máy sẽ trình diễn.

Phạm vi UI là **luồng hỏi–đáp, một trang duy nhất**. Không có tab, không có dashboard đánh giá: số liệu Chương 4 đã nằm ở `docs/V2_RESULTS.md` và sẽ được trình bày bằng slide, dựng lại trong UI chỉ thêm đường sập mà không thêm bằng chứng nào.

### Task 1 — `ui/corpus.py`
Đọc toàn bộ `data/raw/*.md` một lần lúc startup, cache trong bộ nhớ. API:
- `load_corpus() -> dict[norm_id, NormMeta]`
- `norm_graph() -> {"nodes": [...], "edges": [...]}` — cạnh từ `implements` (loại `IMPLEMENTS`) và `amended_by_norms` (loại `AMENDS`). Node có `id`, `title`, `so_hieu`, `tier`, `jurisdiction`, `theme`, `valid_from`, `valid_to`.
- `get_component_text(norm_id, dieu, khoan=None, diem=None) -> str | None` — tra nguyên văn từ heading markdown.

**Xong khi:** chạy được ở máy A, in ra 32 node và danh sách cạnh hợp lý.

### Task 2 — `ui/trace.py`
- `TraceCollector(logging.Handler)`: `emit()` đẩy `TraceEvent` vào `queue.Queue`.
- `parse_message(name, msg) -> (step, data)` theo mục 5.1.
- `parse_context(context_str) -> list[ContextBlock]` theo mục 5.2.
- `link_citations(citations, blocks) -> list[dict]` theo mục 5.3.

**Xong khi:** có unit test dùng chuỗi log và context giả (viết tay theo đúng format ở mục 5) — parse ra đúng. Không cần DB. Đặt test ở `tests/test_ui_trace.py`.

### Task 3 — `ui/adapters.py` + `ui/server.py` + frontend, chạy `replay`
- Interface chung: `async def ask(question, **params) -> AsyncIterator[TraceEvent]`.
- `ReplayAdapter`: tìm fixture theo câu hỏi (khớp chuẩn hóa: lowercase, bỏ dấu câu, gộp khoảng trắng), phát lại events theo `t/REPLAY_SPEED`. Không khớp fixture nào → phát `kind="error"` với thông báo rõ ràng bằng tiếng Việt kèm danh sách câu có sẵn.
- Endpoints:
  - `GET /` → `ui/static/index.html`
  - `GET /api/mode` → `{"mode": "...", "questions": [...]}` (danh sách câu có fixture, để frontend hiện gợi ý)
  - `POST /api/ask` → SSE stream các TraceEvent
  - `GET /api/norm-graph` → Task 1
  - `GET /api/text?norm_id=&dieu=&khoan=` → nguyên văn
- Frontend: **một trang duy nhất** cho luồng hỏi–đáp (không tab, không màn hình phụ) — stepper dọc 7 bước hiện dần theo SSE; panel phải cho nguyên văn khi bấm citation; đồ thị Cytoscape cho bước 4.

**Xong khi:** ở máy A, `DEMO_MODE=replay uvicorn ui.server:app` chạy được và hiện đủ 7 bước từ một fixture viết tay tạm.

### Task 4 — `LiveAdapter` + `ui/record.py` (chạy ở máy B)

Hai phần gộp làm một vì `record.py` **dùng chính `LiveAdapter`** để ghi fixture — chuỗi event trong fixture phải giống hệt lúc chạy live, tách ra làm hai lượt là tự chuốc lấy hai đường code khác nhau.

**`LiveAdapter`:** khởi tạo client lúc startup (mục 2.2), chạy `run_pipeline` trong thread (`asyncio.to_thread` hoặc `ThreadPoolExecutor`), mỗi request một `TraceCollector` qua `gan_collector()` (mục 2.3) bơm event vào queue, generator SSE rót ra. Bắt `anthropic.APIStatusError` → phát `kind="error"` với thông báo tiếng Việt gợi ý chuyển sang `replay` (xem cách `src/demo.py` xử lý 529).

Truyền `llm_cache_dir` (mặc định `data/llm_cache` — kiểm tra tên thật trong `demo.py` argparse) để câu đã chạy thì $0.

**`ui/record.py`:**
```
python -m ui.record "một câu hỏi"
python -m ui.record data/evaluation/demo_questions.txt      # bỏ dòng trống và dòng bắt đầu bằng #
```
Cờ: `--jurisdiction`, `--mode {general,irac}`, `--verify`, `--llm-mode` — **phải khớp** với cờ dùng lúc demo. Ghi ra `ui/fixtures/`.

**Xong khi:** máy B chạy `live` được end-to-end (đây là kịch bản bảo vệ, không phải bước phụ) và `record.py` sinh JSON hợp lệ; máy A pull về, replay thấy đủ 7 bước.

Trước khi chạy `live` lần đầu ở máy B: `python scripts/preflight.py` để kiểm Docker/Neo4j/Qdrant/`.env`/BGE-M3. Quy trình dựng máy B: `ui/docs/LIVE_GUIDE.md`.

### Task 5 — Chống sự cố buổi bảo vệ
- Tải các file CDN về `ui/static/vendor/`, đổi sang tham chiếu local.
- Nút chuyển `live` ⇄ `replay` ngay trên UI (không cần restart server) — **đây là cơ chế cứu buổi bảo vệ**: kịch bản chính chạy `live`, hỏng thì bấm một nút là về `replay` trình bày tiếp. Server phải GIỮ adapter cũ nếu dựng adapter mới hỏng.
- Badge "PHÁT LẠI" khi ở replay, và nút điều chỉnh tốc độ.

---

## 7. Những điều KHÔNG được làm

- Không sửa `src/`, không sửa `data/raw/`, `data/sources/`, `data/evaluation/`.
- Không gọi LLM để sinh văn tự thuật cho panel trace.
- Không lấy `theme`/`jurisdiction` từ `results_*.json` để hiện ở bước Query Planner.
- Không gắn badge pass cho từng dòng ở bước 6 (mục 3.1).
- Không trình bày danh sách norm Stage 2 như một bảng xếp hạng (mục 3.2).
- Không dùng `localStorage`/`sessionStorage`.
- Không dùng `EventSource`, không dùng chung một `TraceCollector` giữa các request, không để `/api/ask` chạy chồng (mục 2.3).
- Không thêm auth, không thêm database riêng cho UI, không thêm Docker service mới.
- Không thêm tab / màn hình phụ / dashboard đánh giá — UI chỉ có một trang hỏi–đáp (mục 6).
- Không viết lại `ScoredTextUnit`, `PipelineResult` hay bất kỳ TypedDict nào của `src/` — import chúng.

---

## 8. Cần hỏi người dùng trước khi tự quyết

- Muốn badge pass per-dòng ở bước 6 (cần sửa `src/`).
- Muốn hiển thị system prompt / full prompt gửi LLM (dài ~4000 token, có thể hay mà có thể loãng).
- Danh sách câu hỏi cuối cùng cho buổi bảo vệ — hiện `data/evaluation/demo_questions.txt` chỉ có 2 câu ví dụ.
