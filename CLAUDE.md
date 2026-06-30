# CLAUDE.md — Ontology-Driven GraphRAG cho Pháp luật Việt Nam

> **ĐỌC FILE NÀY TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ.**
> Sau đó đọc `docs/PROJECT_STATUS.md` để biết task hiện tại và `docs/PROJECT_CONTEXT.md` để nắm kiến trúc.
> Không viết bất kỳ dòng code nào trước khi đọc xong cả ba file.

---

## NHẬN DẠNG DỰ ÁN

**Tên:** Ontology-Driven GraphRAG cho Pháp luật Việt Nam
**Loại:** Khóa luận tốt nghiệp — 2 thành viên [A] và [B]
**Mục tiêu kỹ thuật:** Xây dựng hệ thống trả lời câu hỏi pháp lý có trích dẫn, kết hợp Knowledge Graph (Neo4j) và Vector Search (Qdrant), giải quyết 4 gap: đa lĩnh vực, đa địa phương, đa tầng văn bản, đa phiên bản.
**Ngôn ngữ user-facing:** Tiếng Việt. Mọi string, log, comment trong code đều bằng tiếng Việt trừ khi là tên kỹ thuật chuẩn (class name, function name, config key).

---

## TRẠNG THÁI HIỆN TẠI

Phase 0 (Môi trường) và Phase 1 (Dữ liệu) — xem `docs/PROJECT_STATUS.md` để biết task nào đang active.

**Trước khi bắt đầu bất kỳ task nào:**
1. Đọc `docs/PROJECT_STATUS.md` — xác định TASK-ID cần làm, đọc kỹ phần Inputs / Outputs / DoD
2. Đọc `docs/PROJECT_CONTEXT.md` — kiến trúc, schema, quyết định thiết kế
3. Đọc toàn bộ file code có liên quan được liệt kê trong phần Inputs của task card

---

## CẤU TRÚC THƯ MỤC

```
graphrag-vn-law/
├── CLAUDE.md                    ← file này
├── docs/
│   ├── PROJECT_STATUS.md        ← trạng thái task (đọc mỗi session)
│   └── PROJECT_CONTEXT.md       ← kiến trúc & quyết định thiết kế
├── docker-compose.yml
├── requirements.txt
├── .env.example                 ← template (KHÔNG commit .env thật)
├── .gitignore
├── .claude/
│   ├── settings.json
│   └── hooks.sh
├── data/
│   ├── sources/                 ← PDF/DOCX gốc từ vbpl.vn (KHÔNG sửa)
│   │   └── manifest.md
│   ├── raw/                     ← Phase 1 output: *.md đã chuẩn hóa
│   │   ├── mapping_table.md
│   │   ├── crossref_decisions.md
│   │   ├── review_log.md
│   │   └── *.md                 ← văn bản pháp luật đã chuẩn hóa
│   ├── processed/               ← Phase 2 intermediate
│   └── evaluation/              ← Phase 4: test set, kết quả, phân tích
├── src/
│   ├── ingestion/               ← Phase 2
│   │   ├── parser.py            ← TASK-06
│   │   ├── graph_builder.py     ← TASK-07
│   │   └── vectorizer.py        ← TASK-08
│   ├── retrieval/               ← Phase 3
│   │   ├── query_planner.py     ← TASK-10
│   │   ├── subgraph_extractor.py← TASK-11
│   │   ├── semantic_filter.py   ← TASK-12
│   │   ├── context_assembler.py ← TASK-13
│   │   └── answer_generator.py  ← TASK-13
│   ├── baseline/                ← Phase 4
│   │   └── naive_rag.py         ← TASK-16
│   ├── evaluation/              ← Phase 4
│   │   └── metrics.py           ← TASK-17
│   └── utils/
│       ├── connection_check.py  ← TASK-02
│       └── validate_metadata.py ← TASK-04
├── tests/
│   ├── test_parser.py
│   └── test_query_planner.py
└── notebooks/
    ├── phase2_verification.ipynb
    └── phase3_e2e_test.ipynb
```

---

## QUY TẮC TUYỆT ĐỐI — KHÔNG ĐƯỢC VI PHẠM

### 1. Không thao tác database trực tiếp

```
# ❌ TUYỆT ĐỐI CẤM
curl -X POST http://localhost:7474/db/neo4j/tx/commit -d '{"statements":[...]}'
curl -X PUT http://localhost:6333/collections/legal_texts/points -d '{...}'

# ✅ ĐÚNG — luôn đi qua Python scripts
python src/ingestion/graph_builder.py
python src/ingestion/vectorizer.py
```

Lý do: mọi thay đổi database phải traceable qua code, không có thay đổi thủ công nào được commit.

### 2. Không xóa hoặc sửa data/sources/

```
# ❌ TUYỆT ĐỐI CẤM
rm data/sources/luat-dat-dai-2024.pdf
# Bất kỳ thao tác write nào vào data/sources/
```

`data/sources/` là raw data gốc — không bao giờ sửa. Nếu cần sửa nội dung, sửa ở `data/raw/*.md`.

### 3. Idempotency là bắt buộc

Mọi script write vào Neo4j phải dùng `MERGE`, không dùng `CREATE`.
Mọi write vào Qdrant phải dùng `upsert`, không dùng `insert`.
Chạy pipeline 2 lần phải cho kết quả giống nhau.

### 4. Deterministic ID — không dùng UUID

```python
# ❌ SAI
import uuid
node_id = str(uuid.uuid4())

# ✅ ĐÚNG
import hashlib
node_id = hashlib.sha256(">".join(context_path).encode()).hexdigest()[:16]
```

### 5. Credentials từ .env — không hardcode

```python
# ❌ TUYỆT ĐỐI CẤM
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

# ✅ ĐÚNG
from dotenv import load_dotenv
load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
```

### 6. Không commit .env thật

`.env` phải nằm trong `.gitignore`. Chỉ commit `.env.example`.

### 7. Cập nhật docs/PROJECT_STATUS.md sau mỗi task

Sau khi hoàn thành một task (tất cả DoD items checked): cập nhật `docs/PROJECT_STATUS.md`:
- Thêm changelog entry ở đầu (reverse-chronological)
- Tick `[x]` toàn bộ DoD items
- Điền ngày vào `Completed:`
- Cập nhật `§1.1 Đã hoàn thành`

---

## QUYẾT ĐỊNH THIẾT KẾ — DECISION LOG

| # | Quyết định | Lý do | Ngày |
|---|---|---|---|
| D-01 | Thu thập theo Chương/Mục thay vì từng Điều | Tiết kiệm thời gian Phase 1; dữ liệu thừa dùng làm noise test cho evaluation | 2026-04-27 |
| D-02 | Dùng VBHN làm nguồn nội dung chính | Giải quyết vấn đề nghị định chồng chéo sửa đổi lẫn nhau, không cần tự tra từng NĐ | 2026-04-27 |
| D-03 | CTV chỉ tạo bản hiện hành trước | Ưu tiên chạy pipeline end-to-end; bổ sung temporal versioning sau nếu kịp | 2026-04-27 |
| D-04 | Tier 1 bao gồm NQ Quốc hội; Tier 4 bao gồm NQ HĐND | NQ QH có giá trị tương đương Luật; NQ HĐND tỉnh có giá trị tương đương QĐ UBND | 2026-04-27 |
| D-05 | Scope CMĐSDĐ: cá nhân, đất NN trừ lâm nghiệp, sang đất ở | Hạn chế liên đới tới luật lâm nghiệp, luật đầu tư; giảm số văn bản cần thu thập | 2026-04-27 |
| D-06 | Điều mới hoàn toàn (VD: Điều 44a) thuộc Norm gốc, CTV ghi added_by | Giữ nhất quán cấu trúc bố cục văn bản; truy vết nguồn gốc qua CTV | 2026-04-27 |
| D-07 | Xóa Procedure node và edge `[:SPECIFIED_IN]` khỏi schema | Manual mapping không scalable; Theme + Jurisdiction filter + `[:IMPLEMENTS]` traversal đã đủ để routing và chứng minh 4 Gap | 2026-05-10 |
| D-08 | Thêm field `summary` vào frontmatter; Stage 1 retrieval qua summary embedding | Cho phép semantic routing ở cấp Norm mà không cần manual mapping; con người viết đảm bảo độ chính xác pháp lý | 2026-05-10 |
| D-09 | Thêm edge `[:AMENDS]` (Norm → Norm) cho sửa đổi/bổ sung | Phân biệt với `[:IMPLEMENTS]` (hướng dẫn thi hành) — VD: NQ 254 AMENDS Luật ĐĐ, NĐ 49 IMPLEMENTS NQ 254. Stage 2 traversal qua `[:IMPLEMENTS|AMENDS*1..4]` undirected | 2026-05-19 |
| D-10 | Pass 0 Dense Floor trong `hybrid_search` — top-1 dense per norm | KG graph_boost (procedure mapping) có thể override pure semantic match → Q024 GT Điều 116 K5 rank #2 dense bị drop. Principle: "embedding similarity là ground signal; KG augments, không replace" | 2026-05-19 |
| D-11 | Pass -1 Structured Citation Boost — regex "Khoản X Điều Y" → ép Components match vào top-K | Q026 GT cite trực tiếp "Khoản 1 Điều 13" — dense top NĐ 49 = K11/K12 vì label dài bias embedding. Additive boost: no-op nếu pattern không match | 2026-05-20 |
| D-12 | Label-keyword Boost (Pass -0.5) — REJECTED sau ablation | Empirical net F1 −0.055 trên 8-câu (Q022 +0.5 nhưng Q001/Q002/Q008/Q024 regress vì label keyword overlap đa Điều cùng tier). Documented as embedding limitation, future work cross-encoder | 2026-05-20 |
| D-13 | Giữ `Procedure` node + thêm `Concept` node (TASK-15) cho concept rarity scoring | D-07 xóa `[:SPECIFIED_IN]` (manual mapping không scalable) nhưng node `Procedure` được REPURPOSED: kết hợp `Concept` node (Core Ontology) + `[:MAPS_TO_CONCEPT]` (Component → Concept) + `[:REQUIRES_CONCEPT]` (Procedure → Concept) → `hybrid_search` boost components giàu concept hiếm thuộc procedure quan tâm. Ontology Mapping bottom-up qua LLM Haiku (`src/ingestion/ontology_mapper.py`) | Phase 4 |
| D-14 | Prompt L1 rewrite chống hallucination (no-leak + slug enforcement + amendment dual-cite mềm) | Faithfulness analysis run 20260520-211930 phát hiện 4 nhóm lỗi: F1 prompt leak (`SPAN-REGIME` UPPERCASE label rò rỉ vào output Q022/Q023), F2 citation slug vs số hiệu (`47/2024/QH15` thay vì slug ở Q024/Q025), F3 pointer misattribution (NĐ 226 K10 không tồn tại — phải là NĐ 112 K10 sửa bởi NĐ 226 Đ5 ở Q019), F4 malformed (`Phụ lục I và Phụ lục II` gộp ở Q008). Fix: bỏ hoàn toàn nhãn nội bộ khỏi prompt + meta-rule chống leak + rule cứng slug + rule dual-cite mềm cho amendment. Iter2: hallucination 7→0, leak 2→0, F1 0.539→0.554 (+0.015 N=1 vs N=3 cũ). Refactor `build_prompt()` → `build_messages()` để hỗ trợ prompt caching | 2026-05-28 |
| D-15 | Anthropic prompt caching cho system prompt (~2117 tokens, `cache_control: ephemeral`) | System rules giống nhau cho mọi câu hỏi → trả tiền lặp lại 78 lần (N=3 × 26 câu) cho cùng nội dung. Caching giảm ~90% input cost trên phần system từ request thứ 2 trở đi, TTL ~5 phút (đủ 1 batch eval). Yêu cầu: tách `build_messages(q,c) -> (system, user)`, system phải ≥ **2048 tokens** — ngưỡng cache tối thiểu thực tế của Sonnet 4.6 (KHÔNG phải 1024; nếu prompt bị cắt xuống dưới 2048 thì cache im lặng ngừng hoạt động, không báo lỗi). Local prompt-hash cache vẫn được giữ độc lập | 2026-05-28 |
| D-16 | Prompt sanitization B1 — loại bỏ MỌI shorthand/label trong prompt, cấm coin thuật ngữ | Demo span-regime sau v2.9 phát hiện LLM tự promote `(cắt ngang)` thành **"(nguyên tắc cắt ngang)"** trong output — thuật ngữ pháp lý GIẢ. Class bug lớn hơn: bất kỳ shorthand `(X)` / Latin label `(lex superior)` nào trong prompt đều có thể leak. Fix: xóa hết parenthetical shortcuts khỏi prompt + meta-rule mạnh cấm "tự tạo tên gọi/nhãn cho nguyên tắc". Loại bỏ `(lex superior/posterior/specialis)` (Latin), `(cắt ngang)` (rút gọn). Pair với D-17 (auto-detect) tạo defense-in-depth chống thuật ngữ giả | 2026-05-28 |
| D-17 | Term grounding validator B2 — module `src/evaluation/term_validator.py` auto-detect thuật ngữ giả | Sửa từng case không scalable; câu hỏi mới có thể sinh thuật ngữ giả mới. Approach khoa học: extract candidate "term-like" phrases bằng 4 regex pattern (`named_principle`, `quoted`, `parenthetical`, `bold`) + heuristic `_looks_like_term` (loại measurement/function-word/descriptive), validate qua substring lookup vào CONTEXT + corpus `data/raw/*.md`. Metric `grounding_rate = #grounded / #candidates_total` — analogue của citation existence_rate cho thuật ngữ. Validation: trên 8-câu subset post-B1 đạt **100% grounding rate** (15 candidates / 0 ungrounded); trên run cũ canonical bắt được tất cả leak đã biết (SPAN-REGIME, cắt ngang, chuyển giao thẩm quyền…) | 2026-05-28 |
| D-18 | Verifier agent (tầng multi-agent: Generator → Verifier → prune) — `src/retrieval/verifier.py` | Nút thắt F1 không phải retrieval (NormR đã 0.93) mà là **over-citation**: ROOT_CAUSE_ANALYSIS cho thấy 47 citation dư là nguyên nhân DOMINANT của precision thấp. Pipeline gốc một lượt Generator, không ai kiểm lại. Verifier = mẫu Self-Refine/CRITIC, **tái dùng hạ tầng `faithfulness.py`** (faithfulness metric → filter inline, không circular import). Tier 1 grounding ($0 deterministic) drop citation không có trong context (bắt hallucination); Tier 2 (Haiku, tùy chọn) judge support, mặc định UNSUPPORTED→flag (bảo thủ, tránh over-prune), `drop_unsupported` để prune cứng. Mặc định `verify=False` → hành vi pipeline cũ KHÔNG đổi; cờ `--verify`/`--verify-tier` cho ablation ±verifier (demo + run_evaluation). Hiệu quả thực nghiệm: **Tier 1 +0.023 F1 Khoản** (offline $0, 26 câu canonical, bỏ 7 citation bịa); wiring live xác nhận. | 2026-06-23 |
| D-19 | Verifier Tier 2 (LLM support-judge) — REJECTED làm bộ lọc DROP; sửa bug snippet Phụ lục | Thử Tier 2 live trên 3 câu over-cite (Q004/Q008/Q019): (1) **không bắt được over-cite thật** — Q004 (3 vs GT 2) judge giữ cả 3 vì citation thừa vẫn grounded + được chunk khẳng định ("support" ≠ "là đáp án GT tối thiểu"); (2) **over-flag citation ĐÚNG** — Q008 flag cả 2 citation GT (mismatch cấu trúc Phụ lục), Q019 flag citation mà metric tính match → hard-drop sẽ REGRESS F1; (3) phần lớn "over-cite" đo được là **metric/GT artifact** (H4 9 ca + H5 8 ca — Q004 citation thừa thực ra ĐÚNG, GT thiếu) → drop = tối ưu theo thước đo lỗi. Quyết định: **giữ Tier 1, reject Tier 2-support cho mục đích drop** (giống D-12). Phát hiện kèm: bug `faithfulness._extract_answer_snippet` chỉ bắt regex `Điều`, bỏ sót `[Phụ lục ...]` → fallback 400 ký tự → flag oan; đã fix (dispatch theo `loai`, ảnh hưởng cả faithfulness Tier 2 metric). **Future work**: relevance/necessity-judge (thay support-judge) + GT completeness + Tier 2 dạng flag-only-for-reporting (không drop). | 2026-06-23 |
| D-20 | Cross-encoder (`bge-reranker-v2-m3`) làm **retrieval modifier** — REJECTED sau ablation; `reranker.py` GIỮ làm teacher | Direction 2: vá embedding blindness disambiguation cấp Điều (P-08/Q022). Thử 2 cách tích hợp vào `hybrid_search`, ablation 7-câu (subset thiên vị, base cache vs rerank fresh): **(A) Rerank Floor** (thay Dense Floor ở Pass 0): F1 Khoản +0.019 NHƯNG regression Q021 (1.00→0.80). **(B) Blend** (cộng `rerank_rank` thành tín hiệu RRF thứ 3, giữ Dense Floor): F1 Khoản +0.048 (chữa được Q021) NHƯNG **NormR −0.071 + F1 Điều −0.050** (cross-encoder kéo chunk lexically-relevant nhưng sai norm lên — Q022/Q003). Cả 2 là **đánh đổi, không thắng sạch** → **REJECT làm default + GỠ integration** khỏi `hybrid_search`/`pipeline`/CLI (giữ D-10: dense là ground signal, không để feature không-ăn-thua trong core path). Giống D-12. **GIỮ `src/retrieval/reranker.py`** (module độc lập, LOCAL $0, **CPU** vì MPS treo 3.5h — env `RERANKER_DEVICE`) — REPURPOSE làm **teacher** sinh hard-negative/soft-label cho finetune embedding (bước direction-2 kế tiếp). | 2026-06-23 |
| D-21 | Evaluation Tier 0 — mở rộng thang đo $0 (significance + citation behavior + per-gap/juris), KHÔNG gọi API | Sau khi 2 hướng thuật toán (verifier, rerank/finetune) phần lớn cho negative result, giá trị biên cao nhất ở **đo lường** chứ không thêm cơ chế. `metrics.aggregate` đã có per-gap/per-theme/PR/latency → KHÔNG dựng lại; chỉ bổ sung cái còn thiếu: **(1)** paired bootstrap 95% CI (10000 resamples, seed=42 deterministic) + Wilcoxon signed-rank — trả lời "N=26 nhỏ, +Δ có thật không"; **(2)** citation behavior (over-cite rate, P–R gap); **(3)** report tiếng Anh hợp nhất. Module `src/evaluation/expanded_eval.py` đọc 2 results JSON SẴN ($0). **Fix alignment quan trọng**: nhãn `gap_type` đồng bộ theo `test_set_dat_dai.json` HIỆN TẠI theo id (baseline run 05-19 gộp gap4 vào gap3 trước relabel → nếu đọc nhãn lưu trong run sẽ lệch). **Kết quả** (graphrag 0528-142757 vs baseline 0519-204426): F1 Khoản Δ **+0.281, CI [0.154, 0.417], p=0.001 *** (win/loss/tie 18/3/3)** → ưu thế KG **có ý nghĩa thống kê**; per-gap: **Gap4 Δ +0.522** (lớn nhất, baseline 0.071 — KG temporal quyết định), Gap2 mạnh nhất tuyệt đối (0.726); **nhược điểm thật**: `multi-juris` Δ −0.244 (1 câu thua → Limitations). Đủ "thật sự có cải tiến" để cân nhắc Tier 1 (ablation suite). | 2026-06-23 |
| D-22 | Tái cấu trúc khâu đánh giá thành kiến trúc 4 khối **E0–E3** (triết lý "Claim → Evidence") — `docs/EVALUATION_ARCHITECTURE.md` | Evaluation cũ (Full vs Naive RAG) chỉ chứng minh *toàn bộ* hệ thống hơn baseline, KHÔNG chứng minh từng thành phần KG giải đúng gap của nó. Tái cấu trúc: **E0** nền tin cậy (reproducibility + significance + GT provenance + metric validity) → **E1** ablation **double dissociation** (no-theme/no-jurisdiction/no-traversal/no-temporal phải sụp ĐÚNG gap tương ứng VÀ ổn định ở gap khác — chứng minh *necessity* từng cơ chế) → **E2** baseline ladder đa-**trục** (thêm **closed-book** "có cần retrieval?" + **auto-GraphRAG** "có cần ontology?" + **oracle** trần) + E2b consistency per-domain (Gap 1) + **E2c bỏ BERTScore → người chấm/máy chấm** (chủ-tớ: LLM-judge validated với người qua kappa rồi mới mở rộng; D-19 là tiền lệ cảnh báo) → **E3** failure taxonomy + negative results (D-12/19/20). Mỗi gap có **gói bằng chứng đa nguồn**. Phân biệt cứng: baseline (thắng) ≠ ablation (sụp) ≠ upper bound (tiến gần). Build mới: `ablation_config.py` + `human_eval.py` + `error_analysis.py`. Ablation suite E1 + E2b chờ corpus [B] (xem `project_eval_tier1_deferred`) | 2026-06-29 |
| D-23 | `implements` frontmatter chấp nhận **string \| list \| null** (đa văn bản cha) | Corpus [B] (Hộ tịch + Nuôi con nuôi) có văn bản hướng dẫn thi hành ĐỒNG THỜI nhiều cha — VD `thong-tu-04-2020-tt-btp` implements cả `nghi-dinh-123-2015-nd-cp` LẪN `luat-ho-tich-2014`; `nghi-dinh-120-2025-nd-cp` implements cả Luật Nuôi con nuôi lẫn Luật Hộ tịch. Đây là quan hệ pháp lý THẬT và chính là tín hiệu đa-tầng **Gap 3** → làm phẳng về 1 cha sẽ vứt mất cạnh `[:IMPLEMENTS]` thật. Schema cũ giả định 1 cha khiến `validate_metadata.py` crash (`unhashable list`) + `graph_builder` tạo edge hỏng. Fix: chuẩn hóa thành list ở 3 điểm — validator (type-check + global-ref), `graph_builder.create_edges` + Pass 2 (lặp qua từng cha). Đa-parent IMPLEMENTS vốn đã được đồ thị hỗ trợ (1 Norm có nhiều cạnh `[:IMPLEMENTS]`); chỉ frontmatter single-value là hẹp. **Kèm theo**: NQ 124/2016 TP.HCM (văn bản đa-**theme** đầu tiên — đụng P-03) xử lý theo hướng A (tách 2 Norm theo theme: id `-datdai` / `-hotich`), KHÔNG implement `[:BELONGS_TO]` (giữ P-03 hoãn). 243 test pass | 2026-06-30 |

---

## SCHEMA ONTOLOGY — QUICK REFERENCE

### 9 loại Node

| Node | Mô tả | Key properties |
|---|---|---|
| `Theme` | Lĩnh vực pháp lý | `name`: dat-dai \| ho-tich \| nuoi-con-nuoi |
| `Norm` | Văn bản quy phạm pháp luật | `id`, `title`, `tier` (1-4), `valid_from`, `summary` |
| `Component` | Điều/Khoản/Điểm/Tiết (xuyên thời gian) | `id`, `label`, `ontology_mapped` (bool) |
| `CTV` | Snapshot của Component tại thời điểm | `valid_from`, `valid_to` (sentinel `9999-12-31` khi còn hiệu lực), `status`, `amended_by`, `added_by` (optional) |
| `TextUnit` | Nội dung văn bản thuần túy | `id` (deterministic SHA256), `text` |
| `Jurisdiction` | Địa phương | `name`: toan-quoc \| tp-hcm \| dong-nai |
| `Amendment` | Metadata sửa đổi (parse từ `<!-- amended_by --> comment`) | `amending_norm`, `amending_loc`, `effective_date`, `content_summary` |
| `Concept` | Core Ontology concept (TASK-15 Phase 4) | `id`, `name` — load từ `data/ontology/core_v1.json` |
| `Procedure` | Mapping thủ tục → concepts (D-13) | `id`, `name` — KHÔNG có `[:SPECIFIED_IN]` edge (D-07), chỉ `[:REQUIRES_CONCEPT]` |

### 10 loại Edge

**Edge cốt lõi cho retrieval (Gap 1/2/3/4):**

| Edge | Từ → Đến | Ý nghĩa |
|---|---|---|
| `[:INCLUDES]` | Theme → Norm | Văn bản thuộc lĩnh vực (Gap 1) |
| `[:IMPLEMENTS]` | Norm → Norm | Hướng dẫn thi hành (NĐ → Luật) — Gap 3 |
| `[:AMENDS]` | Norm → Norm | Sửa đổi/bổ sung (VD: NQ 254 → Luật ĐĐ) — **Gap 4**. Cùng `[:IMPLEMENTS]` tạo derivation closure cho Stage 2 traversal (D-09) |
| `[:HAS_COMPONENT]` | Norm → Component | Phân rã cấu trúc |
| `[:HAS_CTV]` | Component → CTV | Quản lý phiên bản theo thời gian — **Gap 4** |
| `[:HAS_TEXT_UNIT]` | CTV → TextUnit | Nội dung vật lý |
| `[:APPLIES_TO]` | Norm → Jurisdiction | Hard-filter địa phương (Gap 2) |

**Edge cho metadata + concept scoring:**

| Edge | Từ → Đến | Ý nghĩa |
|---|---|---|
| `[:AMENDED_BY]` | Component → Amendment | Liên kết điều khoản bị sửa đổi với metadata sửa đổi (parse từ `<!-- amended_by -->` annotation) — **Gap 4** |
| `[:MAPS_TO_CONCEPT]` | Component → Concept | Bottom-up LLM classification (TASK-15) gán concept cho từng Điều/Khoản. Dùng trong `hybrid_search._compute_rarity` để boost components giàu concept hiếm |
| `[:REQUIRES_CONCEPT]` | Procedure → Concept | Top-down mapping thủ tục → concepts cần thiết. Dùng để identify Component khả năng liên quan procedure |

> **Lưu ý (D-07 + D-13):**
> - `[:SPECIFIED_IN]` edge ĐÃ XÓA khỏi schema (D-07). Routing theo thủ tục qua Theme + Jurisdiction filter + summary-based Stage 1 retrieval.
> - `Procedure` node ĐƯỢC GIỮ LẠI (D-13) cho mục đích **concept rarity scoring** (TASK-15 Phase 4) — chỉ kết nối qua `[:REQUIRES_CONCEPT]`, KHÔNG có `[:SPECIFIED_IN]` cũ.
> - `[:BELONGS_TO]` không implement (xem P-03).

### Tier mapping (CỨNG — không thay đổi)

```
tier 1 = Luật / Bộ luật / Nghị quyết Quốc hội
tier 2 = Nghị định / Pháp lệnh
tier 3 = Thông tư / Thông tư liên tịch
tier 4 = Quyết định UBND tỉnh / Nghị quyết HĐND tỉnh
```

---

## CONVENTIONS

### Format `id` văn bản

```
[loai-van-ban]-[slug-ten-van-ban]-[nam]

Ví dụ:
  luat-dat-dai-2024
  nghi-dinh-102-2024-nd-cp
  thong-tu-10-2024-btnmt
  quyet-dinh-bang-gia-dat-tp-hcm-2025
```

Quy tắc slug: lowercase, dấu gạch ngang, không dấu tiếng Việt, không ký tự đặc biệt.

### Format heading trong data/raw/*.md

```markdown
---
id: "luat-dat-dai-2024"
title: "Luật Đất đai 2024 (Luật số 31/2024/QH15)"
tier: 1
theme: "dat-dai"
jurisdiction: "toan-quoc"
implements: null
valid_from: "2025-01-01"
valid_to: null
source_url: "https://vbpl.vn/..."
source_vbhn: null        # số hiệu VBHN nếu nội dung lấy từ văn bản hợp nhất, VD: "44/VBHN-VPQH"
amended_by_norms: null   # list id văn bản sửa đổi nếu file chứa điều khoản đã bị sửa, VD: ["nghi-dinh-07-2025-nd-cp", "nghi-dinh-18-2026-nd-cp"]
summary: null            # 3-5 câu mô tả phạm vi văn bản (thủ tục, đối tượng, địa phương) — do con người viết
---

## Điều X. [Tên điều]

### Khoản 1.

#### Điểm a.

##### Tiết 1.

```

**Đối với phần Phụ lục:** Cấp `##` dùng đường dẫn phân cấp đầy đủ từ Phụ lục đến Mục, thay thế cho `## Điều`. Từ Mục trở xuống vẫn tổ chức theo `### Khoản` / `#### Điểm` / `##### Tiết` như cũ.

```markdown
## Phụ lục [X] - Phần [Y] - Mục [N]. [Tên mục]
## Phụ lục [X] - Phần [Y] - Nội dung [Z] - Mục [N]. [Tên mục]
## Phụ lục [X]. [Tên phụ lục]

### Khoản 1.

#### Điểm a.

##### Tiết 1.
```

**Không được dùng:** `# Điều`, `## Khoản`, hay bất kỳ cấp heading nào khác.

**Quy tắc định dạng nội dung bắt buộc (Rất quan trọng):**
1. **Bỏ tiêu đề Chương, Mục:** Tuyệt đối không giữ lại các tiêu đề như "Chương I", "Mục 1". Chỉ giữ lại các cấp bậc hợp lệ là `## Điều`, `### Khoản`, `#### Điểm`, `##### Tiết`. **Ngoại lệ:** Phần Phụ lục dùng `## Phụ lục [X] - Phần [Y] - Mục [N]. [Tên]` thay cho `## Điều`.
2. **Loại bỏ rác (Watermark/Header/Footer):** Phải xóa sạch các đoạn text rác như `CÔNG BÁO/Số.../Ngày...` hoặc số trang.
3. **Bảo toàn Footnote/Amended:** Tuyệt đối không được làm mất các chú thích sửa đổi, bổ sung (footnote). Phải chuyển đổi chúng thành định dạng HTML comment và đặt ngay bên dưới nội dung bị ảnh hưởng.
4. **Cấu trúc chuẩn của `amended_by`:** Các ghi chú sửa đổi phải được format thống nhất theo cú pháp:
   `<!-- amended_by: [SỐ HIỆU LUẬT], [VỊ TRÍ SỬA ĐỔI], hiệu lực: [NGÀY], nội dung: [TÓM TẮT NỘI DUNG SỬA ĐỔI] -->`
   *(Ví dụ: `<!-- amended_by: 47/2024/QH15, điểm a khoản 2 Điều 57, hiệu lực: 01/07/2025, nội dung: thay "..." bằng "..." -->`)*
5. **Quy tắc SPACING (Khoảng trắng):**
   - Luôn có 1 dòng trống giữa các heading (ví dụ giữa `## Điều 1` và `### Khoản 1.`).
   - Luôn có 1 dòng trống giữa heading và đoạn nội dung đi kèm dưới nó.
   - Các đoạn văn thuộc cùng một Khoản/Điểm mà không có ký hiệu mới thì viết tiếp xuống hàng dưới heading hiện tại (không tạo heading giả). Do ta áp dụng quy tắc gộp dòng (unwrap), các câu trong cùng một đoạn sẽ nằm trên một dòng duy nhất.

### Tên file data/raw/

```
[id-van-ban].md
Ví dụ: luat-dat-dai-2024.md
```

### Tên file data/sources/

```
[tier]-[slug-ten-van-ban]-[nam].[pdf|docx]
Ví dụ: luat-dat-dai-2024.pdf
```

### Python naming conventions

- Module: `snake_case.py`
- Class: `PascalCase`
- Function: `snake_case`
- Constant: `UPPER_SNAKE_CASE`
- TypedDict: `PascalCase` với suffix mô tả (VD: `TextUnit`, `QueryPlan`)

### Git commit format

```
[TASK-XX] type: mô tả ngắn bằng tiếng Việt

Ví dụ:
  [TASK-04] feat: thêm hàm validate_metadata cho Phase 1
  [TASK-06] fix: sửa lỗi Stack pop khi gặp Điều không có Khoản
  [TASK-07] test: thêm unit test cho idempotency của graph_builder
```

---

## CÁC GIÁ TRỊ HỢP LỆ — DANH SÁCH ĐÓNG

Các trường sau **chỉ nhận giá trị trong danh sách này**, không có ngoại lệ:

```python
VALID_THEMES = ["dat-dai", "ho-tich", "nuoi-con-nuoi"]

VALID_JURISDICTIONS = ["toan-quoc", "tp-hcm", "dong-nai"]

VALID_TIERS = [1, 2, 3, 4]

VALID_PROCEDURES = [
    "chuyen-muc-dich-su-dung-dat",  # Scope: cá nhân, từ đất nông nghiệp (trừ đất lâm nghiệp) sang đất ở (nông thôn + đô thị)
    "cap-so-do-lan-dau",
    "dang-ky-khai-sinh",
    "cap-ban-sao-trich-luc-ho-tich",
    "dang-ky-nuoi-con-nuoi",
    "dang-ky-lai-nuoi-con-nuoi"
]

QDRANT_COLLECTION_NAME = "legal_texts"
QDRANT_VECTOR_DIM = 1024          # BGE-M3
CONTEXT_MAX_TOKENS = 6000
DEFAULT_TOP_K = 25
MAX_PER_NORM = 3                  # _MAX_PER_NORM trong semantic_filter.py — cap top-k diversity
ANTHROPIC_MAX_RETRIES = 8         # src/utils/llm_config.py — chống 529 Overloaded
VALID_VERIFY_TIERS = (0, 1, 2)    # verifier.py — 0=no-op, 1=grounding $0, 2=+LLM judge
VALID_TO_SENTINEL = "9999-12-31"  # CTV.valid_to khi vẫn còn hiệu lực (thay null per ac516ad)

# Neo4j schema: 9 node types + 10 edge types (8 retrieval core + 2 concept scoring)
# IMPLEMENTS: hướng dẫn thi hành (NĐ -> Luật)
# AMENDS: sửa đổi/bổ sung (NQ 254 -> Luật ĐĐ)  [D-09]
# MAPS_TO_CONCEPT / REQUIRES_CONCEPT: concept rarity scoring (D-13)
```

---

## DEPENDENCIES — CÁC MODULE LIÊN KẾT

```
Phase 2 — Ingestion:
parser.py          ← đọc data/raw/*.md
                   → trả về List[TextUnit] với Deterministic ID

graph_builder.py   ← nhận TextUnit list từ parser.py
                   ← nhận metadata từ YAML frontmatter (summary, amended_by_norms,...)
                   → write vào Neo4j (MERGE, idempotent)
                   → 5 pass:
                     Pass 0: Concept + Procedure + REQUIRES_CONCEPT từ data/ontology/core_v1.json
                     Pass 1: Theme + Jurisdiction nodes
                     Pass 2: Norm + Component + CTV + TextUnit + structural edges
                     Pass 3: Amendment nodes + [:AMENDED_BY] edges (<!-- amended_by --> annotation)
                     Pass 4: Ontology Mapping LLM (TASK-15) — gán [:MAPS_TO_CONCEPT] cho Components

ontology_mapper.py ← Claude Haiku 4.5 classification: Component label → Concept IDs
                   ← input: data/ontology/core_v1.json (Core Ontology — concepts + procedures)
                   → return list concept_ids cho mỗi Component (temperature=0, filter hallucinated)

vectorizer.py      ← đọc TextUnit nodes từ Neo4j
                   ← BGE-M3 encode
                   → upsert vào Qdrant collection "legal_texts" (text_unit + summary vectors)

Phase 3 — Retrieval (3-stage + 4-pass hybrid):
query_planner.py   ← câu hỏi string + Anthropic client + Neo4j (cho Cách C backfill)
                   → QueryPlan TypedDict + có planner cache (data/evaluation/.planner_cache/)

subgraph_extractor.py
  stage1_norm_ids() ← question → Qdrant summary search → top-N norm_ids
  stage2_norm_ids() ← Neo4j traversal [:IMPLEMENTS|AMENDS*1..4] + filter juris/temporal → result_norms
  stage3_graph_component_ids() ← procedure mapping → component IDs cho Pass -1/-0/-1/-2

semantic_filter.py — Hybrid Search 4-pass:
  Path -1: Structured Citation fetch (regex "Khoản X Điều Y" → Neo4j → Qdrant)
  Path -0.5: Label-keyword [REJECTED D-12, inactive]
  Path 0: Dense search (BGE-M3, dense_pool=50)
  Path 1: Keyword search (slug overlap)
  Path 2: Graph boost (procedure components)
  Pass -1: Structured Cite alloc (top priority)
  Pass 0: Dense Floor (top-1 dense per norm, D-10)
  Pass 1: RRF breadth (top-1 RRF per remaining norm)
  Pass 2: RRF depth (fill remaining)

context_assembler.py ← List[ScoredTextUnit] + Neo4j
                     → context string (sort tier 1→4, cap 6000 tokens, build_prompt() w/ TEMPORAL #4 rule)

answer_generator.py  ← context + question + Anthropic client + cache_dir
                     → {answer, citations, context_used, cache_hit}
                     → parse_citations() w/ dedupe (commit 023bb64)

verifier.py          ← question + context + answer + citations (tầng multi-agent, D-18)
                     → VerifierResult {filtered_citations, verdicts, n_dropped, ...}
                     → verify_citations(tier=0/1/2): Tier 1 grounding ($0) + Tier 2
                       LLM support judge (Haiku, tùy chọn). Tái dùng faithfulness.py.
                     → pipeline.run_pipeline(verify=, verify_tier=) — mặc định OFF

reranker.py          ← question + candidates [{text}] (cross-encoder, direction 2, D-20)
                     → rerank(query, candidates, model=) → sorted theo rerank_score
                     → bge-reranker-v2-m3 LOCAL $0 (CPU — MPS treo); load_reranker() lazy
                     → KHÔNG wire vào retrieval (integration REJECTED, D-20). Dùng làm
                       TEACHER sinh hard-negative/soft-label cho finetune embedding (bước sau)

src/utils/llm_config.py — make_anthropic_client() factory với max_retries=8

Phase 4 — Evaluation:
src/evaluation/run_evaluation.py — orchestrator CLI
                                   --systems graphrag,baseline
                                   --faithfulness-tier 0|1|2

src/evaluation/metrics.py        — citation_score (F1 cấp Khoản/Điều), norm_recall, negative_correct
                                   cit_matches() là single source of truth cho semantic match

src/evaluation/faithfulness.py   — Tier 1 (existence, $0) + Tier 2 (LLM judge Haiku)

src/evaluation/report_builder.py — auto sinh REPORT_<timestamp>.md per-Q detail

src/evaluation/compare_runs.py   — A/B diff giữa 2 results JSON

src/evaluation/build_ablation_matrix.py — table cumulative impact 4 fix layers
src/evaluation/build_reproducibility_report.py — N=3 study mean ± σ
src/evaluation/instrument_retrieval.py  — debug Stage 1/2/3 (API-free)
src/evaluation/retrieval_eval.py — Recall@k/MRR cấp Điều/Khoản, dense vs cross-encoder ($0, không generation) — go/no-go finetune embedding + harness #4
src/evaluation/expanded_eval.py  — Tier 0 metric expansion ($0, offline): đọc 2 results JSON sẵn → paired bootstrap 95% CI + Wilcoxon significance, citation behavior (over-cite/PR-gap), per-gap/per-juris breakdown, report tiếng Anh. Đồng bộ nhãn gap_type theo test set hiện tại (D-21)

Demo:
src/demo.py        — Rich CLI cho weekly meeting (panels + Markdown render + spinner + Tree trace)
                   python -m src.demo "câu hỏi" [--trace] [--jurisdiction] [--bypass-completeness]

Baseline:
src/baseline/naive_rag.py — chunked retrieval (512 chars, overlap 50) cho A/B comparison
```

---

## PIPELINE THU THẬP DỮ LIỆU — QUICK REFERENCE

Dữ liệu được thu thập **thủ công** từ các nguồn pháp luật chính thức, không dùng Docling/OCR pipeline.

**Workflow:**
1. Xác định thủ tục trên dichvucong.gov.vn → lấy danh sách văn bản liên quan
2. Tìm Văn bản hợp nhất (VBHN) trên vbpl.vn nếu có → dùng làm nguồn nội dung
3. Nếu không có VBHN → lấy trực tiếp từ văn bản gốc
4. Copy nội dung các Chương/Mục liên quan → chuẩn hóa thành file `data/raw/*.md`

**Quy tắc thu thập:**
- Nếu chương **không** có mục: có ít nhất 1 điều liên quan → lấy **cả chương**
- Nếu chương **có** mục: có ít nhất 1 điều liên quan → lấy **cả mục** chứa điều đó
- VBHN chỉ là nguồn lấy nội dung; metadata vẫn ghi theo văn bản QPPL chính thức
- Điều mới hoàn toàn (được thêm bởi nghị định sửa đổi): Component thuộc Norm gốc, CTV ghi `added_by`

**Chiến lược CTV:**
- Phase 1: chỉ tạo CTV bản hiện hành (`status: active`) từ VBHN
- Sau Phase 3 nếu kịp: bổ sung 2-3 CTV phiên bản cũ bằng cách truy ngược từ VBHN để demo temporal evolution
- Không bắt buộc tạo CTV cũ cho tất cả điều khoản

---

## GATE TASKS — KHÔNG ĐƯỢC BỎ QUA

Bốn task sau là "cổng" bắt buộc. Phase sau **không được bắt đầu** nếu gate task chưa pass toàn bộ DoD:

| Gate | Cho phép bắt đầu | Verify bằng |
|---|---|---|
| TASK-02 (Integration Verification) | Phase 1 | Script `connection_check.py` chạy "✅ PASS" cả Neo4j và Qdrant |
| TASK-05 (Cross-check Phase 1) | Phase 2 | `review_log.md` có sign-off của cả 2 thành viên; `validate_metadata.py` không báo lỗi |
| TASK-09 (Phase 2 Verification) | Phase 3 | `phase2_report.md` có đủ count checks và sign-off |
| TASK-14 (Integration E2E) | Phase 4 | `python -m src.evaluation.run_evaluation --test-set data/evaluation/test_set_dat_dai.json --systems graphrag,baseline` chạy được 26+ câu hỏi không crash |

---

## MÔI TRƯỜNG PHÁT TRIỂN

```bash
# Khởi động databases
docker compose up -d

# Kiểm tra databases đang chạy
docker compose ps

# Chạy tests
pytest tests/ -v

# Validate metadata files Phase 1
python src/utils/validate_metadata.py data/raw/

# Kiểm tra kết nối
python src/utils/connection_check.py

# Chạy ingestion (Phase 2) — chỉ sau khi Phase 1 done
python src/ingestion/graph_builder.py
python src/ingestion/vectorizer.py

# Demo CLI (Phase 3) — input câu hỏi → output answer + citations
python -m src.demo "Hạn mức giao đất ở TP.HCM tối đa bao nhiêu?" --jurisdiction tp-hcm --bypass-completeness
python -m src.demo "..." --trace            # hiện pipeline trace chi tiết (Tree view)

# Evaluation (Phase 4) — đo F1/NormR/Faithfulness vs Baseline
python -m src.evaluation.run_evaluation --test-set data/evaluation/test_set_dat_dai.json \
       --systems graphrag,baseline --no-llm-cache --faithfulness-tier 2

# A/B diff 2 results JSON
python -m src.evaluation.compare_runs results_old.json results_new.json

# Ablation matrix cumulative
python -m src.evaluation.build_ablation_matrix

# Reproducibility report N=3
python -m src.evaluation.build_reproducibility_report run1.json run2.json run3.json
```

**Biến môi trường cần có trong `.env`:**

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=BAAI/bge-m3
LLM_PROVIDER=anthropic
LLM_MODEL_PLANNER=claude-haiku-4-5-20251001     # Query Planner + Faithfulness judge + Ontology mapper
LLM_MODEL_GENERATOR=claude-sonnet-4-6           # Answer Generator
ANTHROPIC_API_KEY=<key>                         # SDK đọc trực tiếp biến này (make_anthropic_client)
LLM_API_KEY=<key>                               # alias giữ tương thích
```

---

## KHI GẶP LỖI THƯỜNG GẶP

**Neo4j không kết nối được:**
```bash
docker compose logs neo4j | tail -20
# Nếu thấy "authentication failure" → kiểm tra NEO4J_PASSWORD trong .env
```

**Qdrant collection không tìm thấy:**
```bash
# Qdrant collection "legal_texts" chưa được tạo
# Chạy vectorizer.py sẽ tự tạo nếu chưa có
```

**Parser lỗi "invalid heading format":**
```
# File .md có heading sai level (# Điều thay vì ## Điều)
# Mở file đó, tìm heading bắt đầu bằng #, sửa thành ##
```

**Deterministic ID bị duplicate giữa hai file khác nhau:**
```
# Hai TextUnit có cùng context_path → một trong hai file có id metadata trùng
# Kiểm tra: python src/utils/validate_metadata.py data/raw/ --check-duplicates
```

---

## NHỮNG GÌ KHÔNG LÀM

- **Không** tự quyết định cross-reference ngoài scope — hỏi project owner, xem `data/raw/crossref_decisions.md`
- **Không** implement `[:BELONGS_TO]` — đây là enhancement ngoài scope hiện tại
- **Không** dùng UUID làm ID bất kỳ đâu trong codebase
- **Không** sửa file trong `data/sources/` — đây là raw data bất biến
- **Không** để code chạy mà không có error handling — mọi lỗi kết nối database phải được catch và log rõ ràng
- **Không** hardcode bất kỳ giá trị nào trong danh sách đóng (themes, jurisdictions, tiers) — luôn import từ constants
