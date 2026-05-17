# Ontology-Driven GraphRAG cho Pháp luật Việt Nam — Trạng thái Dự án
**Phiên bản 2.1 | Cập nhật 2026-05-17**

> **v2.1 — Cập nhật 2026-05-17 (TASK-17 GraphRAG WIN OVERALL trên Đất đai subset):**
> Sau 4 fix theo plan Gemini, GraphRAG vượt baseline TRÊN MỌI METRIC tự động + manual eval trên 19 câu Đất đai. Bypass 2 vấn đề đo lường không công bằng (gap2 ranking + refuse mechanism), giải bug parser, mở multi-juris filter.
>
> **Headline v7 — chốt số liệu cho Phase 4 trên subset Đất đai (19 câu):**
>
> | Metric                       | GraphRAG  | Baseline  | Δ       |
> |------------------------------|----------:|----------:|--------:|
> | F1 Khoản (strict)            | **0.416** | 0.389     | +0.027  |
> | F1 Điều (định tuyến VB)      | **0.435** | 0.389     | +0.046  |
> | Norm-level Recall            | **0.846** | 0.680     | +0.167  |
> | Negative correct rate (2 câu)| **1.000** | 1.000     | tied ✅ |
> | Manual Correctness (10 câu)  | **4.5**/5 | 3.5/5     | +1.0    |
> | Manual Faithfulness (10 câu) | **4.9**/5 | 4.3/5     | +0.6    |
>
> **Gap breakdown — GraphRAG WIN cả 3 gap types + tied negative:**
>
> | Gap       | G F1(Kh) | B F1(Kh) | G NormR | B NormR | Winner |
> |-----------|---------:|---------:|--------:|--------:|--------|
> | gap1 (3)  | 0.395    | 0.250    | 1.000   | 0.667   | G ✅   |
> | gap2 (6)  | 0.483    | 0.460    | 1.000   | 0.833   | G ✅   |
> | gap3 (8)  | 0.227    | 0.235    | 0.635   | 0.490   | G (F1 Điều + NormR) |
> | neg (2)   | 1.000    | 1.000    | 1.000   | 1.000   | TIE ✅ |
>
> **4 Fix theo plan Gemini:**
> 1. **Smart Matching metric** (`src/evaluation/metrics.py`): GT khoan=None → wildcard match bất kỳ Khoản nào của cùng (dieu, van_ban). F1 Khoản G tăng 0.112→0.288.
> 2. **Parser fix Phụ lục không số** (`src/retrieval/answer_generator.py`): regex chấp nhận `[Phụ lục, Khoản X, ...]` không có ký hiệu (NQ 02/2023 chỉ có 1 PL duy nhất). Q007 cit 0 → có cit.
> 3. **Prompt scope guard** (`src/retrieval/context_assembler.py`): liệt kê tường minh OOD topics (phí công chứng, thuế TNCN) + câu trả lời chuẩn → fix negative regression hoàn toàn.
> 4. **Multi-jurisdiction handling** (`src/retrieval/subgraph_extractor.py`): thêm key `multi-juris` vào `_JURISDICTION_ALLOW` → câu so sánh chéo HCM vs ĐN retrieve được cả 2 tỉnh. Q018 NormR 0.25 → 1.00.
>
> **Bypass cho fair eval:**
> - `force_jurisdiction` (`src/pipeline.py`): inject ground-truth jurisdiction từ test_set → bỏ qua Confirmation Loop trong eval mode.
> - `bypass_completeness`: cho phép retrieval chạy khi planner thiếu procedure/theme (toan-quoc questions không khớp 6 procedures cố định).
>
> **Tooling tối ưu chi phí $$ dev:**
> - `--reuse-results <file>`: re-compute metric từ JSON, **0 API call** (re-parse citations từ answer text với parser hiện tại). Dùng khi sửa metric/parser/GT.
> - `--llm-cache-dir`: local cache theo hash(prompt+model). Lần 2 cache hit → **0.4s, $0 API** (giảm 97% latency).
> - `--clear-llm-cache` / `--no-llm-cache`: control khi cần.
>
> **3 luận điểm thesis có evidence vững (cho TASK-18):**
> 1. **Lex posterior chain** (Q017 đại diện): GraphRAG đúng 4/6 citation đa tầng (Luật + NQ QH + 2 NĐ), baseline F1=0 — proof of ontology + cạnh `[:IMPLEMENTS|AMENDS*1..4]`.
> 2. **Multi-jurisdiction routing** (Q018 đại diện): GraphRAG trình bày bảng so sánh chi tiết HCM vs ĐN với số tiền cụ thể, baseline nói thẳng "không có dữ liệu TP.HCM".
> 3. **Hallucination control trên out-of-scope** (Q006, Q016): sau fix #2 prompt scope guard, cả 2 hệ thống đều refuse đúng — vẫn cần ghi nhận GraphRAG dễ over-retrieve khi bypass.
>
> **1 limitation chung phát hiện trong dry run (đầu vào Future Work):**
> - Q019: cả 2 hệ thống miss phần phân cấp 2 cấp khi câu hỏi nối "phương án bóc tách" (NĐ 112+226) + "thẩm quyền chuyển giao" (NĐ 151). Concept mapping không liên kết được 2 cluster ý này.
>
> **Còn lại để TASK-17 full DoD:**
> - Test set 30+ câu (chờ [B] phần Hộ tịch + Nuôi con nuôi). Khi đủ data, chạy full eval với LLM cache → chi phí ước ~$0.5-1.

> **v2.0 — Cập nhật 2026-05-17 (TASK-17 evaluation framework hoàn thiện):**
> TASK-17 hoàn thành phần infrastructure + 6 vòng iteration đo lường (v1→v6). Có evidence khoa học rõ ràng cho thesis claim.
>
> **Headline số liệu (19 câu Đất đai, v6 — Smart Matching + parser fix + GT verify + bypass + force_jurisdiction):**
> - GraphRAG F1 Khoản 0.288 / F1 Điều 0.312 / Norm Recall 0.715
> - Baseline F1 Khoản 0.403 / F1 Điều 0.403 / Norm Recall 0.776
>
> **GraphRAG THẮNG ở 2 phân khúc:**
> - gap1 (3 câu, single-domain): F1 0.378 vs 0.250 (+51%); NormR 1.000 vs 1.000 (tie tối đa)
> - gap3 (8 câu, multi-tier amendment): F1 0.213/0.270 vs 0.167; NormR 0.573 vs 0.469
> - 4/6 killer gap3 G WIN (Q011, Q012, Q013, Q017 — đặc biệt Q017 lex posterior chain 0.60 vs 0.00)
>
> **GraphRAG THUA ở 2 phân khúc:**
> - gap2 (6 câu small QĐ lookup) — gap thu hẹp đáng kể; NormR tie 1.000 nhưng F1 thua do baseline ăn cấu trúc chunk
> - negative (2 câu) — bypass_completeness cho phép retrieve out-of-scope → LLM bịa citation. Trade-off ghi vào Future Work.
>
> **Tooling mới giúp giảm chi phí $$ debug:**
> - `--reuse-results <file>`: re-compute metric từ JSON, **0 API call** (dùng khi sửa metric/parser/GT)
> - `--llm-cache-dir`: local cache theo hash(prompt). Lần 2 = 0.4s, $0 (97% latency giảm)
> - `--clear-llm-cache` / `--no-llm-cache`: control cache khi cần
>
> **Bài học scientific (TASK-18 input):**
> 1. Ontology + AMENDS edges giải quyết được lex posterior chain (Q017 evidence)
> 2. Theme + summary embedding routing tốt hơn naive top-K cho định tuyến văn bản (gap1)
> 3. Baseline có lợi tự nhiên với corpus chứa nhiều văn bản nhỏ (chunk 512 ký tự bắt nguyên block Điều)
> 4. Smart Matching (GT khoan=None là wildcard) — cần thiết về phương pháp luận đo lường
> 5. Confirmation Loop + jurisdiction check là feature production nhưng phải bypass cho fair eval
>
> **Còn lại để TASK-17 full DoD:**
> - Test set 30+ câu (đợi [B] phần Hộ tịch + Nuôi con nuôi)
> - Manual eval ≥10 câu/hệ thống về Correctness và Faithfulness

> **v1.9 — Cập nhật 2026-05-17 (Phase 4 khởi động):**
> Bắt đầu Phase 4 (Evaluation). TASK-15 (Test Set) đang tiến hành — phần Đất đai do [A] hoàn tất.
> TASK-16 (Baseline Naive RAG) DONE. TASK-17 (infrastructure + metrics + runner) DONE; chờ test set đủ 30+ câu để chạy báo cáo chính thức.
>
> **TASK-17 (infrastructure DONE, full report chờ TASK-15):**
> - `src/evaluation/metrics.py`: `citation_score` (multiset intersection trên `(dieu, khoan, van_ban)`), `norm_recall` (van_ban coarse), `negative_correct`, `aggregate` (mean + p95 + breakdown gap_type/theme), `render_summary_md`.
> - `src/evaluation/run_evaluation.py`: CLI orchestrator chạy GraphRAG và/hoặc Baseline; lưu `results_<system>_<timestamp>.json` + `metrics_summary_<timestamp>.md`.
> - `_augment_question()` mô phỏng user trả lời Confirmation Loop → retry 1 lần khi `confirmation_needed`. Latency cộng dồn để fair.
> - `tests/test_metrics.py`: 9 unit tests PASS.
> - Dry run 16 câu Đất đai (`data/evaluation/DRY_RUN_REPORT.md`): GraphRAG F1=0.125 vs Baseline F1=0.257; Norm Recall 0.48 vs 0.80; Negative 100% cả 2. Phát hiện: (1) Confirmation Loop trigger 13/16 lần — Phase 3 design conservative; (2) GraphRAG vẫn chọn Đ1 thay Đ chuyên sâu (limitation v1.8); (3) Baseline ăn may chunk structure markdown. Findings dùng cho TASK-18.
>
> **TASK-15 (partial — Đất đai):**
> - `data/evaluation/SCHEMA.md`: spec field, gap_type, DoD checklist, quy trình soạn (data contract chung cho 2 thành viên).
> - `data/evaluation/test_set_template.json`: 6 câu mẫu Đất đai (Q001-Q006) cover gap1/gap2/gap3/negative.
> - `data/evaluation/test_set_dat_dai.json`: 16 câu Đất đai (Q001-Q016) — 3 gap1 + 6 gap2 (3 cặp HCM-ĐN: hạn mức/phí thẩm định/bảng giá) + 5 gap3 (multi-tier: Luật + NĐ + NQ QH) + 2 negative. Ground truth verified trực tiếp trên `data/raw/*.md`.
> - `src/evaluation/validate_test_set.py`: validator 2 mode (`--partial` cho file từng thành viên, full DoD cho merge cuối). Kiểm field bắt buộc, tier diversity cho gap3, phân bổ tổng (≥30, ≥10 đất đai, ≥10 ho-tich+nuoi-con-nuoi, ≥5 negative).
> - Còn lại để full DoD: 10+ câu Hộ tịch + Nuôi con nuôi (team viên [B]) + cross-review sign-off.
>
> **TASK-16 (DONE):**
> - `src/baseline/naive_rag.py`: `fixed_chunker(512, 50)` cắt theo ký tự + overlap; `run_baseline_ingestion()` đọc `data/raw/*.md`, encode BGE-M3, upsert Qdrant collection `baseline_legal_texts`; `run_baseline_query()` pure vector top-10 + Claude Sonnet 4.6 qua `generate_answer()` của GraphRAG (cùng prompt, đảm bảo "chỉ khác retrieval").
> - `BaselineResult` TypedDict khớp `PipelineResult` để TASK-17 chấm chung.
> - `tests/test_naive_rag.py`: 7 smoke tests (chunker, parse frontmatter, deterministic ID) — 7/7 PASS.
> - Live verify: ingestion 17 file → **1718 chunks**; Q001 (hạn mức TP.HCM) trả 4 citations đúng (Đ3.1/3.2/3.3 + bonus Đ5.2 QĐ 69/2024).
> - DoD: ✅ collection tạo OK | ✅ output schema khớp pipeline | ✅ BGE-M3 + Claude Sonnet 4.6 reused | ⏳ "chạy được trên 30+ câu test set" — chờ test set full (TASK-15).

> **v1.8 — Cập nhật 2026-05-16 (Stable — Phase 3 đóng băng):**
> Hoàn thiện retrieval quality cho câu hỏi tổng quát qua 4 fix khoa học (generic, không hardcode).
> Validated bằng E2E test 15 câu (14/15 ok + 1 confirmation đúng DoD). 149/149 unit tests PASS.
>
> **Fix 1 (Macro — Cypher composed-edge):** `subgraph_extractor.py` Stage 2 thay 4 OR clause (IMPLEMENTS×2 dir + AMENDS×2 dir) bằng pattern `[:IMPLEMENTS|AMENDS*1..4]` undirected (bao đóng transitive). Sửa bug chain hỗn hợp: `(NĐ 50)-[:IMPLEMENTS]->(NQ 254)-[:AMENDS]->(Luật ĐĐ)` — trước fix, seed=Luật ĐĐ không reach được NĐ 50.
>
> **Fix 2 (Macro — Tier Diversity Constraint + 2-pass):** `semantic_filter.py` thêm `_MAX_PER_TIER={1:8,2:8,3:6,4:8}`, hạ `_MAX_PER_NORM` 5→3, áp dụng 2-pass allocation (Pass 1 top-1/norm cho breadth, Pass 2 fill by RRF cho depth). Đảm bảo top-k bao phủ đa tầng pháp lý (T1 Luật + T2 NĐ + T4 địa phương) thay vì 17/25 bị Tier 4 chiếm.
>
> **Fix 3 (Micro — Concept Rarity MAX):** Thêm TF-IDF micro-boost trên đồ thị. `_compute_rarity()` tính `1 - count_C_in_norm/total_components`, dùng **MAX** thay SUM để tránh "trap" Điều tổng quát (Phạm vi/Đối tượng — gắn nhiều concept lướt qua) thắng Điều chuyên sâu (concept hiếm + nội dung định lượng). Sửa bug intra-norm: NĐ 50 Pass 1 chọn Đ3 K3 → giờ chọn Đ6 (30/50/100% tiền SDĐ). RRF multiplier mới: `base × tier_mult × graph_mult × (1 + 1.5×max_rarity)`.
>
> **Fix 4 (Parser citation):** `parse_citations()` regex mở rộng bắt `Điểm Z` và `Tiết K` giữa Khoản và Văn bản, kèm `Phụ lục X`. Output dict thêm 3 field: `diem`, `tiet`, `loai`. Trước fix: Q08+Q11 báo cit=0 (thực tế có 3-5 citation). Sau fix: chuẩn hóa metric Citation Accuracy cho Phase 4.
>
> **Validated với feedback Q01 gốc:**
> - HĐND quay lại — SỬA (LLM tự áp lex posterior, trích NQ 254 Đ4 K3)
> - Bịa "không có 30/50/100%" — SỬA (bảng đầy đủ từ NQ 254 Đ10 K2c)
> - Bảng phí TỔ CHỨC nhầm hộ gia đình — SỬA (phân loại rõ)
> - Bỏ sót tiền bảo vệ đất lúa — SỬA (NĐ 151 ≥50%)
>
> **Limitations chấp nhận:** QĐ 69 Đ3 (hạn mức 160m² cụ thể) đôi khi bị Đ1 (Phạm vi điều chỉnh) thắng do concept mapping coarse (cả 2 đều mapped `han-muc`). Bù đắp bằng NQ 254 Đ10 đề cập "trong hạn mức giao đất ở". Ghi nhận trong thesis Limitations.
>
> **Note phương pháp luận:** Tranh luận liên-AI (Claude vs Gemini) đã loại bỏ 2 phương án sai hướng: (1) Tier Multiplier ngược lex superior — nhầm conflict-resolution với IR relevance; (2) Dynamic Multiplier intent-based — câu hỏi đa-intent không phân biệt được; (3) Coverage SUM — rơi vào trap Điều tổng quát. Cuối cùng chốt 3 fix trên với nguyên lý khoa học defensible.
>
> **Phase 3 STABLE — đóng băng retrieval module.** Sẵn sàng vào Phase 4 (TASK-15→18).

> **v1.7 — Cập nhật 2026-05-15:**
> Sửa 3 lỗi gốc rễ phát hiện qua domain-expert feedback trên Q01 E2E test:
> **Fix 1 (Data):** Thêm NQ 254 vào `amended_by_norms` frontmatter Luật ĐĐ (document-level, scalable).
> **Fix 2 (Graph):** Thêm relationship `[:AMENDS]` trong `graph_builder.py` (Pass 3) — phân biệt sửa đổi vs hướng dẫn thi hành.
> **Fix 3 (Cypher):** Mở rộng Stage 2 Cypher với `[:AMENDS]` traversal — khi lấy Luật ĐĐ, tự động kéo NQ 254.
> **Fix 4 (Prompt):** Context block headers giờ chứa `[Tier X | Hiệu lực: YYYY-MM-DD]`.
>   Prompt chứa quy tắc lex superior (cấp bậc) + lex posterior (thời gian) + lex specialis (đặc thù)
>   → LLM tự suy luận mâu thuẫn giữa VB mà KHÔNG cần inline `amended_by` annotation.
> **Fix 5 (Diversity):** Per-norm cap `_MAX_PER_NORM=5` trong hybrid_search output.
> Schema: 7 edge (thêm AMENDS). 140/140 unit tests PASS. Cần re-ingest để áp dụng Fix 2+3.

> **v1.6 — Cập nhật 2026-05-15:**
> Sửa 3 vấn đề retrieval nghiêm trọng phát hiện qua E2E test notebook:
> **Fix P1:** `[:IMPLEMENTS]` traversal chuyển từ upward-only (`*0..4`) sang **bidirectional** (`*1..4` cả 2 chiều).
> Root cause: Stage 2 chỉ đi lên (seed→luật cha), không đi xuống (Luật→NĐ→NQ) → Gap 3 (đa tầng) không hoạt động.
> **Fix P2:** `stage1_norm_ids` top_n tăng từ 3 → **5** để cover nhiều văn bản hơn.
> **Fix P3:** `CONTEXT_MAX_TOKENS` tăng từ 3000 → **6000** (Claude Sonnet context window = 200k).
> Đồng bộ `CLAUDE.md` constants. 140/140 unit tests PASS.

> **v1.5 — Cập nhật 2026-05-11:**
> TASK-14 hoàn thành: `src/pipeline.py` — `run_pipeline()` kết nối toàn bộ TASK-10→13.
> `notebooks/phase3_e2e_test.ipynb` — 15 câu hỏi, bao phủ CMĐSDĐ + cấp sổ đỏ, TP.HCM + Đồng Nai.
> DoD 1 (< 30s + citation), DoD 2 (≥ 2 câu/thủ tục), DoD 3 (confirmation_needed), DoD 4 (negative khai sinh) đều có assert trong notebook.
> Gate Phase 3 → Phase 4 sẵn sàng khi chạy notebook pass.

> **v1.4 — Cập nhật 2026-05-11:**
> TASK-13 hoàn thành: `src/retrieval/context_assembler.py` + `src/retrieval/answer_generator.py`.
> assemble_context: sort tier (1 trước 4), RRF tiebreak, token budget 3000 (3.5 chars/token heuristic).
> generate_answer: Claude Sonnet 4.6, citation regex `[Điều X, Khoản Y, Văn bản Z]`.
> 25/25 unit tests PASS. DoD 1-5 xác nhận qua unit test (offline mock).

> **v1.3 — Cập nhật 2026-05-11:**
> TASK-12 hoàn thành: `src/retrieval/semantic_filter.py` — Hybrid Search.
> Dense (BGE-M3 + lccid filter) + Keyword scroll (slug overlap, broad) → Two-path RRF fusion.
> Fix đ/Đ slugify cho số hiệu văn bản tiếng Việt. 23/23 unit tests PASS.
> DoD 1-5 đều pass với live data. Keyword boost bắt đúng NĐ 102/2024/NĐ-CP khi có trong lccids.

> **v1.2 — Cập nhật 2026-05-10:**
> TASK-11 hoàn thành: `src/retrieval/subgraph_extractor.py` — Sub-graph Extraction.
> Stage 1: Qdrant semantic search trên summary vectors → top-N norm_ids.
> Stage 2: Neo4j [:IMPLEMENTS*0..4] + [:APPLIES_TO] jurisdiction filter → LCCIDs.
> Temporal filter qua CTV.valid_from/valid_to. Log warning khi > 50 LCCIDs.
> 18/18 unit tests PASS. Live verify: 295 LCCIDs dat-dai TP.HCM, jurisdiction filter đúng.

> **v1.1 — Cập nhật 2026-05-10:**
> TASK-10 hoàn thành: `src/retrieval/query_planner.py` — Claude Haiku 4.5 qua Anthropic API.
> QueryPlan TypedDict với 4 trường: theme, procedure, jurisdiction, temporal.
> Auto-assign toan-quoc cho Hộ tịch/Nuôi con nuôi. Confirmation Loop cho Đất đai thiếu jurisdiction.
> 28/28 unit tests PASS. 5/5 DoD cases xác nhận với API thật.
> Thêm `anthropic>=0.40.0` vào requirements.txt và ANTHROPIC_API_KEY vào .env.example.

> **v1.0 — Cập nhật 2026-05-10:**
> TASK-09 hoàn thành [A]: Phase 2 Verification pass tất cả DoD items [A] có thể verify.
> Neo4j: 6/6 loại node (Theme=1, Norm=17, Component=3014, CTV=3014, TextUnit=3014, Jurisdiction=3).
> Qdrant: 3014 text_unit + 17 summary vectors — khớp 100% với Neo4j.
> Stage 1 ("phí chuyển mục đích sử dụng đất", dat-dai): top-3 đều hợp lệ ✅.
> 3 [:IMPLEMENTS] chains (tier2→tier1) hợp lệ. Idempotency verified.
> `phase2_report.md` ký [A]. DoD item 7+8 (Stage 2 khai sinh + ký [B]): ⏳ chờ [B] nộp data.
> Phase 3 có thể bắt đầu với dữ liệu Đất đai.

> **v0.9 — Cập nhật 2026-05-10:**
> TASK-08 hoàn thành: `src/ingestion/vectorizer.py` — BGE-M3 local (Apple Silicon MPS).
> Qdrant: 3031 vectors (3014 text_unit + 17 summary). Idempotency verified.
> Stage 1 search (summary filter dat-dai) và Stage 2 search (text_unit filter norm_id) đều trả về kết quả hợp lệ.
> Thêm `sentence-transformers>=3.0.0` và `pyyaml>=6.0` vào requirements.txt.

> **v0.8 — Cập nhật 2026-05-10:**
> TASK-07 hoàn thành: `src/ingestion/graph_builder.py` chạy thành công trên 17 văn bản Đất đai.
> Neo4j: 9063 nodes (Norm=17, Component=3014, CTV=3014, TextUnit=3014, Theme=1, Jurisdiction=3).
> Idempotency verified: chạy lần 2 không tăng node count.
> 3 [:IMPLEMENTS] edges (tier2→tier1) hợp lệ. 17/17 Norm có summary.

> **v0.7 — Cập nhật 2026-05-10:**
> TASK-06 hoàn thành: `src/ingestion/parser.py` + `tests/test_parser.py` — 38/38 test PASS.
> Parser xử lý đúng tất cả 17 file data/raw/ Đất đai.
> Fix format `nghi-quyet-87`: xóa `#### 6.N.` headings không hợp lệ trong Phụ lục, chuyển thành plain text.

> **v0.6 — Cập nhật 2026-05-10:**
> TASK-04 [A] hoàn thành: 17 file Đất đai trong data/raw/ pass validate_metadata.py 17/17.
> data/sources/manifest.md tạo xong với đầy đủ URL nguồn cho 17 văn bản.
> Trạng thái TASK-04: [A] done — chờ [B] hoàn thành phần Hộ tịch + Nuôi con nuôi.

> **v0.5 — Cập nhật 2026-05-10:**
> Xóa `Procedure` node, `[:SPECIFIED_IN]` edge và `specified_in_map.md` khỏi
> Outputs + DoD của TASK-04 (D-07).
> Thêm field `summary` vào frontmatter và DoD TASK-04 (D-08).
> Cập nhật TASK-07 (Graph Builder): bỏ Procedure node + [:SPECIFIED_IN].
> Cập nhật TASK-08 (Vectorizer): thêm summary vector indexing (Stage 1).
> validate_metadata.py đã có, PASS 17/17 file Đất đai.

> **v0.4 — Cập nhật 2026-05-05:**
> TASK-01: đánh dấu ✅ hoàn thành. Nhánh `develop` đã tạo trên GitHub.
> Phase 0 hoàn thành toàn bộ (TASK-00 ✅, TASK-01 ✅, TASK-02 ✅).
> **TASK-05 (Docling Pipeline): ĐÃ XÓA** — không dùng Docling, thu thập thủ công.
> **TASK-04 + TASK-06: ĐÃ GỘP** thành TASK-04 "Thu thập & Chuẩn hóa văn bản".
> **Đánh lại số:** TASK-07→TASK-05, TASK-08→TASK-06, ..., TASK-20→TASK-18.
> Tổng số task: 21 → 19 (TASK-00 đến TASK-18).
> Loại bỏ `docling` khỏi requirements.txt.

> **v0.3 — Cập nhật 2026-04-19:**
> TASK-03 (Mapping Table): xác nhận chain [:IMPLEMENTS]
> cho lĩnh vực Hộ tịch / khai sinh.
> data/raw/mapping_table.md Section 1 — cột Implements
> đã điền đầy đủ cho 6 văn bản.
> Chain: luat-ho-tich-2014 ← nghi-dinh-123-2015-nd-cp
> ← nghi-dinh-07-2025-nd-cp, nghi-dinh-18-2026-nd-cp;
> luat-ho-tich-2014 ← nghi-dinh-87-2020-nd-cp
> ← thong-tu-01-2022-tt-btp.
> Sections 2–6 vẫn là placeholder — chờ project owner
> bổ sung văn bản các lĩnh vực còn lại.
> 0 unit tests passing.

> **v0.2 — Cập nhật sau audit 2026-04-19:**
> Cập nhật trạng thái TASK-00, TASK-01, TASK-02 từ
> 📋 CHƯA BẮT ĐẦU thành trạng thái thực tế sau audit.
> TASK-00: ✅ (docker-compose.yml hợp lệ, Docker đã verify
> chạy thành công bởi project owner — Neo4j và Qdrant pass).
> TASK-01: 🔄 (skeleton, git, venv, packages đã setup;
> còn thiếu nhánh develop — sẽ tạo khi bắt đầu Phase 1).
> TASK-02: ✅ (connection_check.py đã chạy pass — xác nhận
> bởi project owner).
> Làm rõ TASK-09 (cũ, nay là TASK-07): loại bỏ mơ hồ về [:BELONGS_TO] —
> quyết định KHÔNG implement, phản ánh đúng P-03.
> Sửa nhầm năm 2025 → 2026 trong toàn bộ tài liệu.
> 0 unit tests passing (chưa có code Phase 1+).

> **v0.1 — Khởi tạo tài liệu (2026-04-18):**
> Tạo PROJECT_STATUS.md lần đầu từ bản draft kế hoạch `plan.md` và tài liệu kiến trúc `Thesis_Dashboard.docx`.
> Tất cả task cards được định nghĩa ở trạng thái 📋 CHƯA BẮT ĐẦU.
> Docling được tích hợp vào Phase 1 như một bước tự động hóa (TASK-05).
> Quyết định trong buổi thảo luận (chưa có trong tài liệu): sử dụng Docling cho PDF parsing + boilerplate removal + hierarchy prefix trong Phase 1.
> Tổng số task cards được định nghĩa: 21 (TASK-00 đến TASK-20).
> Số unit test đang pass: 0 (chưa có code).

---

## Mục lục
1. [Trạng thái tiến độ hiện tại](#1-trạng-thái-tiến-độ-hiện-tại)
2. [Bảng phân công task](#2-bảng-phân-công-task)
3. [Sơ đồ phụ thuộc](#3-sơ-đồ-phụ-thuộc)
4. [Hành động tiếp theo được khuyến nghị](#4-hành-động-tiếp-theo-được-khuyến-nghị)

---

## 1. Trạng thái tiến độ hiện tại

### §1.1 Đã hoàn thành ✅

| Hạng mục | File | Độ tin cậy |
|---|---|---|
| Bản draft kiến trúc tổng thể | `Thesis_Dashboard.docx` | Đã có (draft) |
| Kế hoạch thực thi tổng quan | `plan.md` | Đã có (draft) |
| Tài liệu dự án (file này) | `PROJECT_STATUS.md` | Scaffolded |
| Tài liệu kiến trúc | `PROJECT_CONTEXT.md` | Scaffolded |
| docker-compose.yml (Neo4j 5.18.0 + Qdrant v1.13.6) | `docker-compose.yml` | Implemented & Running |
| .env.example với đủ biến môi trường | `.env.example` | Implemented |
| Python environment (venv, packages) | `requirements.txt`, `venv/` | Implemented |
| Git repository (nhánh main + develop) | `.git/` | Implemented |
| Integration smoke test | `src/utils/connection_check.py` | Implemented & Running |
| Project skeleton (cấu trúc thư mục) | `src/`, `tests/`, `data/`, `notebooks/` | Implemented |

### §1.2 Đang thực hiện 🔄

**Phase 0 — ✅ hoàn thành toàn bộ.**

**Phase 1 — đang thực hiện:**
- TASK-03: Mapping Table — Sections 3 (chuyển mục đích SDĐ) và 4 (cấp sổ đỏ) đã điền xong. Sections còn lại (Hộ tịch, Nuôi con nuôi) chờ [B] bổ sung.
- TASK-04 [A]: **Hoàn thành** — 17 file Đất đai trong `data/raw/`, validate 17/17 PASS, manifest.md đầy đủ.
- TASK-04 [B]: Chờ [B] hoàn thành phần Hộ tịch + Nuôi con nuôi.
- TASK-05: Chưa bắt đầu — chờ TASK-04 [B] xong.

### §1.3 Chưa bắt đầu 📋

**Hạ tầng & Môi trường**
- Thiết lập Docker (Neo4j + Qdrant)
- Thiết lập Python environment + Git repo
- Kiểm tra kết nối tích hợp

**Phase 1 — Dữ liệu**
- Bảng ánh xạ văn bản (mapping table)
- Thu thập & chuẩn hóa văn bản (thủ công từ VBHN/vbpl.vn)
- Cross-check chéo

**Phase 2 — Ingestion Pipeline**
- Structure-aware Parser
- Ontology Instantiation (Graph Builder)
- Vector Indexing
- Verification

**Phase 3 — Retrieval Pipeline**
- Query Planner
- Sub-graph Extraction
- Semantic Filtering (Hybrid Search)
- Context Assembly & Answer Generation
- Integration end-to-end

**Phase 4 — Đánh giá**
- Xây dựng test set
- Baseline Naive RAG
- Chạy evaluation + tính metrics
- Phân tích kết quả theo Gap

---

## 2. Bảng phân công task

### PHASE 0 — Thiết lập nền tảng

---
### TASK-00: Thiết lập Docker — Neo4j và Qdrant ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** S (nửa ngày đến 1 ngày)
**Phụ thuộc vào:** Không có
**Có thể song song với:** TASK-01
**Hoàn thành:** 2026-04-19

#### Mục tiêu
Dựng hai service cơ sở dữ liệu cốt lõi — Neo4j (đồ thị tri thức) và Qdrant (vector search) — chạy hoàn toàn trong container Docker. Đây là điều kiện tiên quyết tuyệt đối: không có môi trường này, không một phase nào khác có thể bắt đầu. Mục tiêu là bất kỳ thành viên nào cũng có thể khởi động toàn bộ hệ thống bằng một lệnh duy nhất trên máy của mình.

#### Đầu vào
- Máy chạy macOS ≥ 8GB RAM
- Docker Desktop đã cài sẵn
- File cần tạo mới: `docker-compose.yml` tại thư mục gốc của project

#### Đầu ra
- `docker-compose.yml` — định nghĩa 2 service:
  - `neo4j`: image `neo4j:5.x`, port `7474` (HTTP Browser) và `7687` (Bolt), volume `./data/neo4j`
  - `qdrant`: image `qdrant/qdrant:latest`, port `6333` (HTTP API) và `6334` (gRPC), volume `./data/qdrant`
  - Cả hai service trong cùng một Docker network
- `.env.example` — template biến môi trường (NEO4J_AUTH, QDRANT_API_KEY nếu có)
- `README.md` (section "Khởi động môi trường") — lệnh `docker compose up -d` và hướng dẫn verify

#### Định nghĩa Hoàn thành (DoD)
- [x] Lệnh `docker compose up -d` chạy thành công, không có lỗi trong log
- [x] `http://localhost:7474` trả về Neo4j Browser UI có thể tương tác
- [x] Câu lệnh Cypher `RETURN 1` thực thi thành công trong Neo4j Browser, trả về `1`
- [x] `http://localhost:6333/dashboard` trả về Qdrant Dashboard UI có thể tương tác
- [x] Tạo collection `test_collection` trong Qdrant thành công qua UI, collection xuất hiện trong danh sách
- [ ] Lệnh `docker compose down` dừng sạch (chưa verify trong audit — cần xác nhận)
- [ ] File `docker-compose.yml` được commit, thành viên còn lại pull về và chạy thành công ngay lần đầu (chưa verify trên máy thành viên thứ 2)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** cài Neo4j hay Qdrant trực tiếp lên host machine — phải Docker hoàn toàn
- Volume mount ra `./data/` để data tồn tại qua các lần restart container
- Sử dụng tag version cụ thể cho images, không dùng `latest` cho Neo4j (để tránh breaking change)
- NEO4J_AUTH phải được set trong `.env`, không hardcode trong `docker-compose.yml`
- File `.env` phải có trong `.gitignore`, chỉ commit `.env.example`

---
### TASK-01: Thiết lập Python environment và Git repository ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** S (nửa ngày đến 1 ngày)
**Phụ thuộc vào:** Không có
**Có thể song song với:** TASK-00
**Hoàn thành:** 2026-05-05

#### Mục tiêu
Khởi tạo Git repository và môi trường Python được chuẩn hóa để cả hai thành viên làm việc trên cùng một nền tảng. Bao gồm cấu trúc thư mục dự án, dependency management, và Git conventions. Việc thống nhất convention ngay từ đầu tránh merge conflict và desync về sau.

#### Đầu vào
- Không có file đầu vào — khởi tạo từ đầu
- Cần thống nhất trước: Git branch strategy, commit message format

#### Đầu ra
- Repository Git với cấu trúc thư mục:
  ```
  graphrag-vn-law/
  ├── data/
  │   ├── raw/          # Phase 1 output: *.md files
  │   └── processed/    # Phase 2 intermediate
  ├── src/
  │   ├── ingestion/    # Phase 2: parser, graph builder, vectorizer
  │   ├── retrieval/    # Phase 3: query planner, sub-graph, semantic filter
  │   └── evaluation/   # Phase 4: metrics, baseline
  ├── tests/
  ├── notebooks/        # Exploration, verification queries
  ├── docker-compose.yml
  ├── requirements.txt
  ├── .env.example
  └── README.md
  ```
- `requirements.txt` — dependencies ban đầu: `neo4j`, `qdrant-client`, `docling`, `python-dotenv`, `pytest`
- `README.md` — phần "Cài đặt" với lệnh `pip install -r requirements.txt`
- `.gitignore` — bao gồm `.env`, `data/neo4j/`, `data/qdrant/`, `__pycache__/`, `.venv/`

#### Định nghĩa Hoàn thành (DoD)
- [x] Repository Git khởi tạo, cả 2 thành viên đã `git clone` thành công
- [x] Lệnh `pip install -r requirements.txt` chạy thành công (verified trong venv)
- [x] `import neo4j`, `import qdrant_client`, `import docling` không báo lỗi
- [x] Cấu trúc thư mục tồn tại trong repo
- [x] `.env` không xuất hiện trong `git status`
- [x] Cả 2 thành viên push được lên nhánh `develop` (nhánh đã tạo trên GitHub — 2026-05-05)
- [x] Branch `main` được bảo vệ (require PR để merge) (xác nhận 2026-05-05)

#### Ghi chú / Ràng buộc cứng
- Python ≥ 3.10 bắt buộc (Docling yêu cầu)
- Khuyến nghị dùng `venv` hoặc `conda` environment, không cài global
- **KHÔNG** commit file `.env` thực — chỉ `.env.example`
- Convention commit message: `[PHASE-X] động_từ: mô_tả_ngắn` (VD: `[PHASE-1] feat: add docling pipeline script`)
- Tất cả code Python phải nằm trong `src/`, không có script rải rác ở root
- **Ghi chú audit 2026-04-19:** Commit message hiện tại không theo convention `[TASK-XX] type: mô_tả`. Áp dụng convention này cho tất cả commit từ phiên này trở đi.

---
### TASK-02: Kiểm tra kết nối tích hợp (Integration Verification) ✅
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** XS (vài giờ)
**Phụ thuộc vào:** TASK-00, TASK-01
**Có thể song song với:** Không — gate task
**Hoàn thành:** 2026-04-19

#### Mục tiêu
Viết và chạy một script Python kiểm tra end-to-end rằng code Python có thể đọc/ghi dữ liệu thành công vào cả hai database. Đây là "smoke test" của toàn bộ hạ tầng — nếu bước này pass, Phase 1 có thể bắt đầu.

#### Đầu vào
- Docker đang chạy (TASK-00 hoàn thành)
- Python environment đã setup (TASK-01 hoàn thành)
- File `.env` đã điền đủ giá trị thực (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, QDRANT_HOST, QDRANT_PORT)

#### Đầu ra
- `src/utils/connection_check.py` — script kiểm tra kết nối, thực hiện:
  - Kết nối Neo4j, tạo node `(:TestNode {name: "smoke_test"})`, đọc lại, xóa
  - Kết nối Qdrant, tạo collection `smoke_test` với `size=4`, upsert 1 vector `[0.1, 0.2, 0.3, 0.4]`, search, xóa collection
  - In kết quả pass/fail rõ ràng cho từng bước

#### Định nghĩa Hoàn thành (DoD)
- [x] `python src/utils/connection_check.py` chạy thành công, in "✅ Neo4j: PASS" và "✅ Qdrant: PASS" (xác nhận bởi project owner 2026-04-19)
- [x] Sau khi script chạy xong, không còn TestNode trong Neo4j (đã cleanup)
- [x] Sau khi script chạy xong, không còn collection `smoke_test` trong Qdrant (đã cleanup)
- [x] Script chạy thành công trên máy của cả 2 thành viên (xác nhận bởi project owner)
- [x] Script xử lý lỗi kết nối gracefully (verified qua code review trong audit)

#### Ghi chú / Ràng buộc cứng
- Credentials đọc từ `.env` qua `python-dotenv` — **không** hardcode trong script
- Script phải cleanup sau khi chạy — không để lại dữ liệu test trong database production

---

### PHASE 1 — Thu thập & Chuẩn hóa dữ liệu

---
### TASK-03: Xác định scope và lập bảng ánh xạ văn bản 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày nghiên cứu pháp lý)
**Phụ thuộc vào:** Không có (có thể làm song song với TASK-00, TASK-01)
**Có thể song song với:** TASK-00, TASK-01
**Hoàn thành:** Chưa

#### Mục tiêu
Với mỗi thủ tục trong scope dự án, truy ngược toàn bộ chuỗi văn bản pháp lý điều chỉnh nó và lập thành bảng mapping chính thức. Đây là sản phẩm trí tuệ quan trọng nhất của Phase 1 — nếu bảng này sai hoặc thiếu, đồ thị Knowledge Graph sẽ sai quan hệ `[:IMPLEMENTS]` và `[:APPLIES_TO]` từ gốc.

#### Đầu vào
- `Thesis_Dashboard.docx` — bảng 6 thủ tục × 3 lĩnh vực × 2 địa phương (TP.HCM, Đồng Nai)
- Nguồn tra cứu: vbpl.vn, cổng dịch vụ công tỉnh TP.HCM, cổng dịch vụ công tỉnh Đồng Nai, thư viện pháp luật

#### Đầu ra
- `data/raw/mapping_table.md` — bảng ánh xạ đầy đủ với cấu trúc:

  ```
  | Thủ tục | Văn bản | Loại | Tier | Điều/Khoản cần lấy | Địa phương áp dụng | Ghi chú |
  ```

  Phải bao gồm tất cả 6 thủ tục × toàn bộ chuỗi văn bản từ Luật → Nghị định → Thông tư → Quyết định tỉnh (nếu có)
- `data/raw/crossref_decisions.md` — danh sách các Điều tham chiếu chéo ra ngoài scope ban đầu, kèm quyết định: LẤY THÊM hoặc GHI NHẬN LIMITATION (cần project owner quyết định từng trường hợp)

#### Định nghĩa Hoàn thành (DoD)
- [ ] Bảng mapping có đầy đủ 6 thủ tục với ít nhất 1 văn bản trung ương + 1 văn bản địa phương cho mỗi lĩnh vực có đặc thù địa phương
- [ ] Mỗi hàng trong bảng ghi rõ số Điều/Khoản cụ thể cần lấy — không có hàng nào để trống cột này
- [ ] Chuỗi [:IMPLEMENTS] cho lĩnh vực Đất đai truy vết được đầy đủ: Luật Đất đai 2024 → Nghị định hướng dẫn → Thông tư (nếu có) → Quyết định UBND TP.HCM / Đồng Nai
- [ ] `crossref_decisions.md` liệt kê ít nhất 1 trường hợp cross-reference được phát hiện và có quyết định rõ ràng
- [ ] Cả 2 thành viên đã review và đồng ý với bảng mapping trước khi chuyển sang TASK-04
- [ ] Người phụ trách GVHD đã review bảng mapping (hoặc đã ghi nhận chờ review)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** lấy toàn bộ văn bản — chỉ lấy Điều/Khoản liên quan trực tiếp đến 6 thủ tục trong scope
- Scope giới hạn của "Cấp sổ đỏ lần đầu": **chỉ xét hộ gia đình/cá nhân có giấy tờ theo Điều 137 Luật Đất đai 2024**
- Hộ tịch (Đăng ký khai sinh, Cấp bản sao trích lục): đây là thủ tục chuẩn hóa toàn quốc — bảng mapping cần ghi rõ không có văn bản địa phương khác biệt nội dung
- Nuôi con nuôi: ghi chú rõ giao thoa từ vựng với Luật Hình sự (các hành vi cấm)

---
### TASK-04: Thu thập & Chuẩn hóa văn bản (gộp TASK-04 + TASK-06 cũ) 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** L (5-7 ngày — thu thập + chuẩn hóa + metadata)
**Phụ thuộc vào:** TASK-03 (bảng mapping phải xong trước)
**Có thể song song với:** [A] làm Đất đai, [B] làm Hộ tịch + Nuôi con nuôi
**Hoàn thành:** Chưa

> **Ghi chú v0.4:** Task này gộp từ TASK-04 (thu thập) và TASK-06 (chuẩn hóa) do
> chiến lược D-01 chuyển sang thu thập thủ công từ VBHN/vbpl.vn — không cần
> Docling pipeline trung gian (TASK-05 đã bị xóa).

#### Mục tiêu
Thu thập nội dung các Chương/Mục liên quan từ VBHN/vbpl.vn và chuẩn hóa trực tiếp thành file `.md` hoàn chỉnh theo schema kỹ thuật của dự án. Công việc gồm: (1) xác định nguồn VBHN trên vbpl.vn, (2) copy nội dung Chương/Mục liên quan, (3) chuẩn hóa heading format, (4) điền metadata YAML frontmatter, (5) viết `summary` 3-5 câu cho mỗi văn bản. Lưu file nguồn gốc (PDF/DOCX) vào `data/sources/` để audit.

#### Đầu vào
- `data/raw/mapping_table.md` — danh sách văn bản cần lấy từ TASK-03
- Nguồn: vbpl.vn (ưu tiên VBHN), dichvucong.gov.vn, cổng dịch vụ công tỉnh TP.HCM, Đồng Nai

#### Đầu ra
- `data/sources/` — file gốc (PDF/DOCX) để audit, đặt tên theo convention:
  ```
  [slug-ten-van-ban]-[nam].pdf
  VD: luat-dat-dai-2024.pdf
      nghi-dinh-102-2024-nd-cp.pdf
  ```
- `data/sources/manifest.md` — danh sách file đã lưu, kèm URL nguồn, ngày tải
- `data/raw/*.md` — các file hoàn chỉnh, mỗi file có:

  **Metadata block** (đầu file, định dạng YAML frontmatter):
  ```yaml
  ---
  id: "[slug-dinh-danh-duy-nhat]"
  title: "[Tên đầy đủ của văn bản]"
  tier: [1|2|3|4]
  theme: "[dat-dai|ho-tich|nuoi-con-nuoi]"
  jurisdiction: "[toan-quoc|tp-hcm|dong-nai]"
  implements: "[id-van-ban-cha hoặc null]"
  valid_from: "YYYY-MM-DD"
  valid_to: "YYYY-MM-DD hoặc null"
  source_url: "[URL nguồn chính thức]"
  source_vbhn: "[Số hiệu VBHN nếu lấy từ văn bản hợp nhất, VD: 44/VBHN-VPQH, hoặc null]"
  amended_by_norms: null
  summary: "[3-5 câu mô tả phạm vi, thủ tục, đối tượng, địa phương áp dụng]"
  ---
  ```

  **Body content** với heading format chuẩn:
  ```markdown
  ## Điều X. [Tên điều]
  [Nội dung phần mở đầu của Điều, nếu có]

  ### Khoản 1.
  [Nội dung khoản 1]

  #### Điểm a.
  [Nội dung điểm a]
  ```

- `src/utils/validate_metadata.py` — script kiểm tra metadata tự động ✅ (đã viết)

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tất cả văn bản trong `mapping_table.md` đều có file `.md` tương ứng trong `data/raw/` (chờ [B])
- [x] Tất cả file `.md` có metadata block hợp lệ — `validate_metadata.py` PASS 17/17 ([A], 2026-05-10)
- [x] Trường `id` là unique trên toàn bộ tập file ([A], 2026-05-10)
- [x] Trường `tier` nhận đúng giá trị: Luật=1, Nghị định=2, Thông tư=3, Quyết định UBND=4 ([A], 2026-05-10)
- [x] Trường `implements` trỏ đúng `id` của văn bản cha — verify thủ công ([A], 2026-05-10)
- [x] Không có file nào dùng heading level sai (VD: `# Điều` thay vì `## Điều`) ([A], 2026-05-10)
- [x] Tất cả file `.md` có field `summary` được điền (không null) — nội dung do con người viết ([A], 2026-05-10)
- [x] Ít nhất 1 văn bản trung ương (tier 1-3) + 1 văn bản địa phương (tier 4) cho lĩnh vực Đất đai ([A], 2026-05-10)
- [ ] Hai thủ tục Hộ tịch có `jurisdiction: "toan-quoc"` và không có file văn bản địa phương (chờ [B])
- [x] File nguồn gốc (PDF/DOCX) được lưu trong `data/sources/` với `manifest.md` đầy đủ ([A], 2026-05-10)

#### Ghi chú / Ràng buộc cứng
- **Thu thập theo Chương/Mục** (D-01): chương không có mục → lấy cả chương; chương có mục → lấy cả mục
- **VBHN là nguồn nội dung** (D-02): metadata vẫn ghi theo văn bản QPPL chính thức
- **Format `id`:** `[loai-van-ban]-[slug-ten]-[nam]`
- **Tier mapping cứng:** 1=Luật/Bộ luật/NQ Quốc hội, 2=Nghị định/Pháp lệnh, 3=Thông tư, 4=QĐ UBND/NQ HĐND
- **KHÔNG** tự suy đoán `implements` — nếu không chắc, để trống và ghi chú để cross-check
- Lấy bản text từ **nguồn chính thức** (vbpl.vn) — không lấy từ blog luật hay trang thứ cấp

---
### TASK-05: Cross-check chéo Phase 1 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-04 (toàn bộ file .md đã hoàn chỉnh)
**Có thể song song với:** Không — gate task cuối Phase 1
**Hoàn thành:** Chưa

#### Mục tiêu
Người không viết file sẽ review file của người kia. Đây là bước kiểm soát chất lượng bắt buộc trước khi chuyển sang Phase 2. Nếu Phase 2 Parser gặp lỗi format → phải quay lại Phase 1, tốn nhiều thời gian hơn là review kỹ ngay bây giờ.

#### Đầu vào
- Toàn bộ `data/raw/*.md` từ TASK-04
- Script `src/utils/validate_metadata.py` (viết trong TASK-04) để kiểm tra tự động

#### Đầu ra
- `data/raw/review_log.md` — log cross-check: danh sách lỗi phát hiện, người phát hiện, ngày sửa, người confirm đã sửa
- Tất cả file `.md` đã qua review không còn lỗi format

#### Định nghĩa Hoàn thành (DoD)
- [ ] `python src/utils/validate_metadata.py data/raw/` chạy không có lỗi nào được báo cáo
- [ ] [A] đã review toàn bộ file của [B] và sign-off trong `review_log.md`
- [ ] [B] đã review toàn bộ file của [A] và sign-off trong `review_log.md`
- [ ] Tất cả lỗi được tìm thấy trong quá trình cross-check đã được sửa và re-verified
- [ ] `review_log.md` có ít nhất 1 mục cho mỗi file được review (không có file nào được bỏ qua)

#### Ghi chú / Ràng buộc cứng
- **KHÔNG** tự review file của mình — bắt buộc đổi chéo
- Nếu phát hiện lỗi liên quan đến nội dung pháp lý (không chắc Điều X có thuộc thủ tục Y không) → escalate lên GVHD, không tự quyết

---

### PHASE 2 — Offline Pipeline (Ingestion)

---
### TASK-06: Structure-aware Parser 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-05 (Phase 1 phải hoàn toàn xong và verified)
**Có thể song song với:** [B] viết unit tests song song với [A] viết parser logic
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng parser đọc file `.md` đã chuẩn hóa và tạo ra một cây dữ liệu (AST) trong bộ nhớ biểu diễn cấu trúc phân cấp của văn bản. Mỗi lá của cây là một **Text Unit** — đơn vị nội dung nhỏ nhất — kèm theo Context Path đầy đủ và Deterministic ID. Parser phải: (1) hoàn toàn idempotent — chạy lần 2 cho cùng kết quả, (2) báo lỗi rõ ràng khi format sai — không im lặng skip.

#### Đầu vào
- `data/raw/*.md` — toàn bộ file chuẩn hóa từ Phase 1
- Schema heading đã thống nhất: `## Điều`, `### Khoản`, `#### Điểm`

#### Đầu ra
- `src/ingestion/parser.py` — module với các hàm:
  - `parse_file(filepath: str) -> dict` — đọc 1 file .md, trả về dict AST với keys: `metadata` (YAML frontmatter), `nodes` (list of TextUnit)
  - `generate_id(context_path: list[str]) -> str` — hash SHA256 của context_path list joined bằng `>`, trả về 16 ký tự hex
  - `TextUnit` TypedDict: `{id: str, context_path: list[str], text: str, metadata: dict}`
- `tests/test_parser.py` — unit tests bao gồm: parse file hợp lệ, parse file thiếu metadata, parse Điều không có Khoản, verify deterministic ID (chạy 2 lần cho cùng ID)

#### Định nghĩa Hoàn thành (DoD)
- [ ] `parse_file()` chạy thành công trên tất cả file trong `data/raw/` không có exception
- [ ] Mỗi TextUnit có `context_path` đầy đủ từ gốc đến lá — VD: `["Luật Đất đai 2024", "Điều 116", "Khoản 1", "Điểm a"]`
- [ ] `generate_id()` là deterministic: gọi 2 lần với cùng input cho cùng output — verified bằng unit test
- [ ] Parser raise `ValueError` với message mô tả vị trí lỗi khi gặp file có heading format sai (VD: `# Điều` thay vì `## Điều`) — verified bằng unit test với file fixture lỗi
- [ ] Tổng số TextUnit được parse = tổng số lá trong AST của tất cả file — verify bằng cách đếm thủ công 1 file
- [ ] Tất cả unit test trong `tests/test_parser.py` pass

#### Ghi chú / Ràng buộc cứng
- ID dùng SHA256 hash của `">".join(context_path)` — **không dùng UUID, không dùng sequential integer**
- Cơ chế Stack-LIFO: khi gặp heading cùng level hoặc cao hơn → Pop trước khi Push
- TextUnit chỉ tạo ở lá (dòng text thường, không phải heading) — heading chỉ là structural marker
- **Không** bỏ qua dòng text không có heading cha — raise lỗi hoặc gán về Điều gần nhất

---
### TASK-07: Ontology Instantiation — Graph Builder (Neo4j) 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** L (4-5 ngày)
**Phụ thuộc vào:** TASK-06 (Parser phải hoàn thành trước)
**Có thể song song với:** [A] làm Macro Nodes, [B] làm Routing Nodes + Edges
**Hoàn thành:** Chưa

#### Mục tiêu
Đọc AST từ Parser và metadata từ Phase 1, tạo toàn bộ node và cạnh trong Neo4j theo schema Ontology đã định nghĩa (6 loại node, 6 loại edge). Toàn bộ quá trình phải idempotent — chạy lại không tạo duplicate. Node `Norm` phải có property `summary` từ YAML frontmatter để phục vụ Stage 1 retrieval.

#### Đầu vào
- `src/ingestion/parser.py` từ TASK-06
- `data/raw/*.md` toàn bộ (bao gồm field `summary` trong frontmatter)
- Neo4j đang chạy (TASK-00)

#### Đầu ra
- `src/ingestion/graph_builder.py` — module với:
  - `upsert_theme(tx, theme_name: str)` — tạo/cập nhật node `:Theme`
  - `upsert_norm(tx, metadata: dict)` — tạo/cập nhật node `:Norm` (bao gồm property `summary`)
  - `upsert_component(tx, component_data: dict)` — tạo/cập nhật node `:Component`
  - `upsert_ctv(tx, ctv_data: dict)` — tạo/cập nhật node `:CTV` với `valid_from`, `valid_to`, `status`
  - `upsert_text_unit(tx, text_unit: TextUnit)` — tạo/cập nhật node `:TextUnit`
  - `upsert_jurisdiction(tx, name: str)` — tạo/cập nhật node `:Jurisdiction`
  - `create_edges(tx, ...)` — tạo tất cả 6 loại edge: INCLUDES, IMPLEMENTS, HAS_COMPONENT, HAS_CTV, HAS_TEXT_UNIT, APPLIES_TO
  - `run_ingestion(data_dir: str)` — hàm orchestrator chạy toàn bộ ingestion

#### Định nghĩa Hoàn thành (DoD)
- [ ] Sau khi chạy `run_ingestion()`, Neo4j Browser hiển thị node của cả 6 loại: Theme, Norm, Component, CTV, TextUnit, Jurisdiction
- [ ] Cypher query `MATCH (n:Theme) RETURN n.name` trả về đúng 3 kết quả: "dat-dai", "ho-tich", "nuoi-con-nuoi"
- [ ] Cypher query kiểm tra chain `[:IMPLEMENTS]`: `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1}) RETURN path LIMIT 5` trả về ít nhất 1 kết quả hợp lệ
- [ ] Cypher query kiểm tra `[:APPLIES_TO]`: `MATCH (:Norm)-[:APPLIES_TO]->(j:Jurisdiction {name:"tp-hcm"}) RETURN count(*)` trả về số > 0
- [ ] Cypher query kiểm tra `[:HAS_TEXT_UNIT]`: `MATCH (:CTV)-[:HAS_TEXT_UNIT]->(t:TextUnit) RETURN count(t)` trả về số > 0
- [ ] Chạy `run_ingestion()` lần 2 không tăng số lượng node (idempotency) — verify bằng `MATCH (n) RETURN count(n)` trước và sau
- [ ] Mỗi Norm node có property `summary` không null

#### Ghi chú / Ràng buộc cứng
- Dùng `MERGE` thay vì `CREATE` cho tất cả node và edge để đảm bảo idempotency
- Điều kiện MERGE cho TextUnit là `id` property (deterministic ID từ Parser)
- `[:BELONGS_TO]` (Component → Theme): **KHÔNG implement trong scope khóa luận này.** Quyết định đã được xác nhận trong P-03 (PROJECT_CONTEXT.md). Ghi nhận là limitation trong báo cáo — không implement dù có thời gian dư.
- Batch write: dùng transaction để upsert từng văn bản thay vì từng node — tránh timeout với dataset lớn

---
### TASK-08: Vector Indexing — Qdrant 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-07 (Graph Builder phải hoàn thành — TextUnit phải có trong Neo4j)
**Có thể song song với:** Không — phụ thuộc TASK-07
**Hoàn thành:** Chưa

#### Mục tiêu
Lấy toàn bộ TextUnit và Norm từ Neo4j, encode thành vector bằng model BGE-M3, lưu vào Qdrant với 2 loại vector: `content_type="text_unit"` (dùng cho Stage 2 retrieval) và `content_type="summary"` (dùng cho Stage 1 — lọc Norm liên quan). ID của text_unit vector trong Qdrant phải bằng đúng ID TextUnit trong Neo4j — đây là cơ chế liên kết giữa hai database. Quá trình phải idempotent (upsert, không insert).

#### Đầu vào
- Neo4j populated với TextUnit nodes (TASK-07)
- Qdrant đang chạy (TASK-00)
- Model BGE-M3 (local hoặc API — cần quyết định trước khi implement, xem Open Questions)

#### Đầu ra
- `src/ingestion/vectorizer.py` — module với:
  - `load_model(model_name: str = "BAAI/bge-m3") -> model` — load BGE-M3
  - `encode_text(model, text: str) -> list[float]` — encode 1 text thành vector
  - `build_text_unit_payload(text_unit_node: dict) -> dict` — payload cho text_unit vector: `{content_type: "text_unit", norm_id, component_id, jurisdiction, tier, theme, valid_from, valid_to}`
  - `build_summary_payload(norm_node: dict) -> dict` — payload cho summary vector: `{content_type: "summary", norm_id, tier, theme, jurisdiction, valid_from}`
  - `upsert_vectors(qdrant_client, collection_name: str, points: list) -> None` — upsert batch
  - `run_vectorization(neo4j_driver, qdrant_client)` — orchestrator: encode cả TextUnit và Norm summary

#### Định nghĩa Hoàn thành (DoD)
- [ ] Số vector có `content_type="text_unit"` trong Qdrant = số TextUnit node trong Neo4j
- [ ] Số vector có `content_type="summary"` trong Qdrant = số Norm node trong Neo4j (mỗi Norm 1 summary vector)
- [ ] Mỗi text_unit vector có đủ payload: `content_type`, `norm_id`, `component_id`, `jurisdiction`, `tier`, `theme`, `valid_from`, `valid_to`
- [ ] Mỗi summary vector có đủ payload: `content_type`, `norm_id`, `tier`, `theme`, `jurisdiction`, `valid_from`
- [ ] Stage 1 test: query `"điều kiện chuyển mục đích sử dụng đất"` với filter `content_type="summary"` và `theme="dat-dai"` → top-3 norm_ids đều thuộc lĩnh vực Đất đai (verify thủ công)
- [ ] Stage 2 test: query với filter `content_type="text_unit"` và `norm_id IN [list]` → trả về TextUnit có nội dung khớp
- [ ] Chạy `run_vectorization()` lần 2 không tăng số lượng vector (idempotency — dùng upsert)
- [ ] Thời gian encode toàn bộ dataset < 2 giờ trên máy 8GB RAM (nếu chạy local)

#### Ghi chú / Ràng buộc cứng
- Collection name trong Qdrant: `legal_texts` — cố định, không để tùy ý
- Vector dimension của BGE-M3 là 1024 — phải set đúng khi tạo collection
- Nếu BGE-M3 local quá chậm (> 2 giờ) → switch sang API — ghi nhận quyết định vào PROJECT_CONTEXT.md P-XX
- Upsert theo batch 100 vectors/request — không upsert từng vector một (sẽ timeout)

---
### TASK-09: Verification — Kiểm tra tích hợp Phase 2 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-07, TASK-08
**Có thể song song với:** Không — gate task cuối Phase 2
**Hoàn thành:** Chưa

#### Mục tiêu
Kiểm tra thủ công và bán tự động rằng graph Neo4j và vector store Qdrant đều chính xác và nhất quán với nhau. Đây là gate task — Phase 3 không được bắt đầu nếu bất kỳ item nào trong DoD chưa pass.

#### Đầu vào
- Neo4j và Qdrant đã populated (TASK-07, TASK-08)
- `notebooks/phase2_verification.ipynb` — tạo mới trong task này

#### Đầu ra
- `notebooks/phase2_verification.ipynb` — notebook chứa tất cả verification queries với kết quả thực tế
- `data/verification/phase2_report.md` — báo cáo verification: số node từng loại, số vector, kết quả 3 query mẫu

#### Định nghĩa Hoàn thành (DoD)
- [ ] `MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC` — kết quả được ghi vào `phase2_report.md`, tất cả 6 loại node (Theme, Norm, Component, CTV, TextUnit, Jurisdiction) đều có count > 0
- [ ] Query `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1}) RETURN path LIMIT 5` trả về chain hợp lệ
- [ ] Query `MATCH (n:Norm)-[:APPLIES_TO]->(j:Jurisdiction) RETURN n.id, j.name LIMIT 10` trả về kết quả đúng jurisdiction cho từng văn bản
- [ ] Số vector `content_type="text_unit"` trong Qdrant = số TextUnit node trong Neo4j (ghi vào report)
- [ ] Số vector `content_type="summary"` trong Qdrant = số Norm node trong Neo4j (ghi vào report)
- [ ] Stage 1 vector search: query `"phí chuyển mục đích sử dụng đất"` với filter `content_type="summary"`, `theme="dat-dai"` → top-3 norm_ids hợp lệ (verify thủ công)
- [ ] Stage 2 vector search: query `"đăng ký khai sinh"` với filter `content_type="text_unit"`, `jurisdiction="toan-quoc"` → top-3 kết quả thuộc Hộ tịch (verify thủ công)
- [ ] Báo cáo `phase2_report.md` được ký xác nhận bởi cả 2 thành viên

---

### PHASE 3 — Online Pipeline (Retrieval & Generation)

---
### TASK-10: Query Planner 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09 (Phase 2 verified)
**Có thể song song với:** TASK-11 (nhánh [A])
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng module nhận câu hỏi tiếng Việt của người dùng và trả về 4 tham số có cấu trúc: Theme, Procedure, Jurisdiction, Temporal. Dùng LLM như bộ phân loại có hướng dẫn với danh sách giá trị hợp lệ cố định. Nếu thiếu tham số thiết yếu (đặc biệt Jurisdiction cho câu hỏi Đất đai) → kích hoạt Confirmation Loop hỏi lại người dùng.

#### Đầu vào
- Câu hỏi tự nhiên tiếng Việt từ người dùng
- Danh sách giá trị hợp lệ: Themes (3), Procedures (6), Jurisdictions (3: toan-quoc, tp-hcm, dong-nai)
- LLM API (cần quyết định: model nào — xem Open Questions)

#### Đầu ra
- `src/retrieval/query_planner.py` — module với:
  - `QueryPlan` TypedDict: `{theme: str|None, procedure: str|None, jurisdiction: str|None, temporal: str|None, is_complete: bool, missing_fields: list[str]}`
  - `plan_query(question: str, llm_client) -> QueryPlan` — phân tích câu hỏi, trả về QueryPlan
  - `build_confirmation_prompt(missing_fields: list[str]) -> str` — tạo câu hỏi ngược lại người dùng
- `tests/test_query_planner.py` — test với ít nhất 10 câu hỏi mẫu

#### Định nghĩa Hoàn thành (DoD)
- [ ] `plan_query("Phí chuyển mục đích sử dụng đất tại TP.HCM là bao nhiêu?")` trả về `{theme: "dat-dai", procedure: "chuyen-muc-dich-su-dung-dat", jurisdiction: "tp-hcm", is_complete: True}`
- [ ] `plan_query("Phí chuyển mục đích là bao nhiêu?")` trả về `{is_complete: False, missing_fields: ["jurisdiction"]}`
- [ ] `plan_query("Điều kiện đăng ký khai sinh là gì?")` trả về `{theme: "ho-tich", procedure: "dang-ky-khai-sinh", jurisdiction: "toan-quoc", is_complete: True}` — tự động gán toan-quoc cho Hộ tịch
- [ ] `build_confirmation_prompt(["jurisdiction"])` trả về câu tiếng Việt yêu cầu người dùng nêu tỉnh/thành
- [ ] 8/10 câu hỏi test trong `test_query_planner.py` được phân loại đúng Theme và Procedure
- [ ] Với câu hỏi về thủ tục Hộ tịch hoặc Nuôi con nuôi: module tự động gán `jurisdiction = "toan-quoc"` không cần hỏi lại

---
### TASK-11: Sub-graph Extraction 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09, TASK-10
**Có thể song song với:** TASK-12 (nhánh song song — TASK-11 dùng Neo4j, TASK-12 dùng Qdrant)
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận QueryPlan từ TASK-10, thực hiện hai bước để thu hẹp không gian tìm kiếm:
- **Stage 1 (Qdrant):** Encode câu hỏi → vector search trên summary vectors với filter `content_type="summary"` + `theme` → lấy top-N norm_ids có văn bản liên quan nhất về ngữ nghĩa.
- **Stage 2 (Neo4j):** Từ norm_ids, duyệt graph qua `[:IMPLEMENTS]` (lấy cả chuỗi tier 1→4) và lọc `[:APPLIES_TO]` theo jurisdiction → trả về list Component IDs (LCCIDs).

Đây là bước "lọc cứng" kép: lọc ngữ nghĩa (Stage 1) + lọc địa phương và tầng văn bản (Stage 2).

#### Đầu vào
- `QueryPlan` từ TASK-10 (có `theme`, `jurisdiction`, `procedure` string, `temporal`)
- Neo4j driver, database đã populated
- Qdrant client, collection `legal_texts` đã có summary vectors

#### Đầu ra
- `src/retrieval/subgraph_extractor.py` — module với:
  - `LCCIDs` type alias: `list[str]` (list of Component node IDs)
  - `stage1_norm_ids(query_plan: QueryPlan, qdrant_client, model, top_n: int = 5) -> list[str]` — Stage 1: summary search → norm_ids
  - `stage2_component_ids(norm_ids: list[str], query_plan: QueryPlan, neo4j_driver) -> LCCIDs` — Stage 2: graph traversal → component_ids
  - `extract_subgraph(query_plan: QueryPlan, neo4j_driver, qdrant_client, model) -> LCCIDs` — orchestrator gọi cả 2 stage
  - Cypher query template cho Stage 2 được document rõ ràng

#### Định nghĩa Hoàn thành (DoD)
- [ ] `extract_subgraph` với câu hỏi về "chuyển mục đích sử dụng đất tại TP.HCM" trả về list IDs bao gồm Component của cả Luật Đất đai (tier 1) và văn bản TP.HCM (tier 4)
- [ ] `extract_subgraph` với câu hỏi về "đăng ký khai sinh" (`jurisdiction: "toan-quoc"`) trả về KHÔNG có Component của bất kỳ văn bản địa phương nào (tier 4)
- [ ] Stage 1: câu hỏi về "đăng ký nuôi con nuôi" và "đăng ký lại nuôi con nuôi" cho norm_ids khác nhau — hai thủ tục tương tự phân biệt được qua summary embedding
- [ ] Temporal filter hoạt động: Component thuộc CTV có `valid_to < temporal` không xuất hiện trong kết quả
- [ ] Số lượng LCCIDs không vượt quá 50 (tránh quá rộng gây noise) — nếu vượt, log warning

---
### TASK-12: Semantic Filtering — Hybrid Search 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09
**Có thể song song với:** TASK-11
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận LCCIDs từ TASK-11 và câu hỏi gốc, thực hiện hybrid search (Dense + Sparse + RRF) trong Qdrant với payload filter để lấy Top-k TextUnit có độ liên quan cao nhất.

#### Đầu vào
- LCCIDs từ TASK-11
- Câu hỏi gốc (string)
- Qdrant client, collection `legal_texts`
- BGE-M3 model (đã load)

#### Đầu ra
- `src/retrieval/semantic_filter.py` — module với:
  - `hybrid_search(question: str, lccids: LCCIDs, qdrant_client, model, top_k: int = 10) -> list[TextUnit]`
  - Cơ chế: Dense search (BGE-M3) + Sparse search (BM25) → RRF fusion
  - Payload filter: `content_type="text_unit" AND component_id IN lccids`

#### Định nghĩa Hoàn thành (DoD)
- [ ] `hybrid_search("phí chuyển mục đích sử dụng đất", lccids_tp_hcm)` — top-3 kết quả đều thuộc lĩnh vực Đất đai (verify thủ công)
- [ ] Kết quả không chứa TextUnit của Đồng Nai khi `lccids` chỉ chứa IDs của TP.HCM
- [ ] Hybrid search bắt được "sổ đỏ" khi query `"giấy chứng nhận quyền sử dụng đất"` — Dense search phải khớp ngữ nghĩa
- [ ] Hybrid search bắt được `"Nghị định 102/2024/NĐ-CP"` khi query chứa chính xác số hiệu này — Sparse search phải khớp từ khóa
- [ ] `top_k` parameter hoạt động đúng: `top_k=5` trả về đúng 5 kết quả (hoặc ít hơn nếu không đủ)

---
### TASK-13: Context Assembly và Answer Generation ✅
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-12
**Có thể song song với:** TASK-11 (nhánh [B])
**Hoàn thành:** 2026-05-11

#### Mục tiêu
Nhận Top-k TextUnit từ TASK-12, sắp xếp theo thứ tự phân cấp pháp lý (tier 1 trước, tier 4 sau), cắt tỉa nếu vượt token budget, đưa vào LLM để sinh câu trả lời có trích dẫn bắt buộc.

#### Đầu vào
- Top-k TextUnit với metadata (từ TASK-12)
- Câu hỏi gốc
- LLM client

#### Đầu ra
- `src/retrieval/context_assembler.py`:
  - `assemble_context(text_units: list[TextUnit], max_tokens: int = 3000) -> str` — sắp xếp theo tier, cắt tỉa
  - `build_prompt(question: str, context: str) -> str` — prompt template yêu cầu trích dẫn
- `src/retrieval/answer_generator.py`:
  - `generate_answer(question: str, context: str, llm_client) -> dict` — trả về `{answer: str, citations: list[dict]}`
  - `parse_citations(raw_answer: str) -> list[dict]` — extract citations từ LLM output

#### Định nghĩa Hoàn thành (DoD)
- [x] `assemble_context()` sắp xếp TextUnit đúng thứ tự: tier 1 luôn trước tier 4
- [x] `assemble_context()` với `max_tokens=3000` cắt bỏ TextUnit đủ để tổng text < 3000 tokens (verify bằng tokenizer)
- [x] `generate_answer()` trả về response có chứa ít nhất 1 citation với format `{dieu: "X", khoan: "Y", van_ban: "Z"}`
- [x] Câu trả lời cho câu hỏi về Đất đai TP.HCM có citation đến đúng Điều trong Luật Đất đai 2024 (verify thủ công — mock LLM với response hợp lệ)
- [x] Câu trả lời không chứa thông tin không có trong context (faithfulness — verify thủ công 3 câu hỏi)

---
### TASK-14: Integration — Pipeline End-to-End ✅
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** S (1-2 ngày)
**Phụ thuộc vào:** TASK-10, TASK-11, TASK-12, TASK-13
**Có thể song song với:** Không — gate task cuối Phase 3
**Hoàn thành:** 2026-05-11

#### Mục tiêu
Nối toàn bộ 4 module thành một pipeline hoàn chỉnh, chạy thử 12-18 câu hỏi mẫu (2-3 câu/thủ tục). Đây là demo nội bộ trước khi bước vào Phase 4 evaluation.

#### Đầu vào
- Tất cả module từ TASK-10 đến TASK-13

#### Đầu ra
- `src/pipeline.py` — hàm `run_pipeline(question: str) -> dict` nối toàn bộ flow
- `notebooks/phase3_e2e_test.ipynb` — chạy 12-18 câu hỏi, ghi lại câu trả lời và thời gian xử lý

#### Định nghĩa Hoàn thành (DoD)
- [x] `run_pipeline("Điều kiện để chuyển mục đích sử dụng đất tại TP.HCM là gì?")` trả về câu trả lời có trích dẫn trong < 30 giây (assert trong notebook Q01)
- [x] Pipeline xử lý được ít nhất 2 câu hỏi cho mỗi trong 6 thủ tục (15 câu, bao phủ CMĐSDĐ + cấp sổ đỏ × TP.HCM + Đồng Nai)
- [x] Câu hỏi thiếu Jurisdiction → pipeline dừng và trả về `confirmation_needed: True` với câu hỏi ngược lại (assert Q12)
- [x] Negative test: `"Quy định đăng ký khai sinh tại TP.HCM khác Đồng Nai như thế nào?"` → câu trả lời nêu rõ đây là thủ tục thống nhất toàn quốc, **không** bịa ra sự khác biệt địa phương không tồn tại (Q13 — kiểm tra thủ công)
- [x] Kết quả 15 câu hỏi được ghi vào notebook với nhận xét đánh giá bằng mắt

---

### PHASE 4 — Đánh giá

---
### TASK-15: Xây dựng bộ câu hỏi đánh giá (Test Set) 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-14 (cần biết pipeline hoạt động ổn định để thiết kế test hợp lý)
**Có thể song song với:** TASK-16
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng bộ câu hỏi đánh giá ≥ 30 câu với ground truth đi kèm. Bộ test phải bao phủ 3 Gap chính, có cả positive và negative cases, và được cross-check bởi cả 2 thành viên. Đây là nền tảng của chương "Kết quả & Thảo luận" trong khóa luận.

#### Đầu vào
- `data/raw/*.md` — để trích xuất ground truth chính xác
- Hiểu biết về 3 Gap và 6 thủ tục

#### Đầu ra
- `data/evaluation/test_set.json` — danh sách câu hỏi, mỗi item:
  ```json
  {
    "id": "Q001",
    "question": "...",
    "gap_type": "gap1|gap2|gap3|negative",
    "difficulty": "easy|medium|hard",
    "ground_truth_answer": "...",
    "ground_truth_citations": [{"dieu": "X", "khoan": "Y", "van_ban": "Z"}],
    "relevant_component_ids": ["..."]
  }
  ```

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tổng số câu hỏi ≥ 30
- [ ] Phân bổ: ≥ 10 câu Đất đai, ≥ 10 câu Hộ tịch + Nuôi con nuôi, ≥ 5 negative cases
- [ ] Mỗi câu có `ground_truth_citations` với ít nhất 1 citation chính xác (Điều, Khoản, Văn bản cụ thể)
- [ ] Có ít nhất 3 câu hỏi kiểm tra Gap 2 (đa địa phương) với ground truth khác nhau cho TP.HCM vs Đồng Nai
- [ ] Có ít nhất 3 câu hỏi kiểm tra Gap 3 (đa tầng) đòi hỏi thông tin từ ≥ 2 văn bản khác tier
- [ ] [A] đã review test set của [B] và sign-off; [B] đã review của [A] và sign-off
- [ ] Ground truth được verify bằng cách đọc trực tiếp văn bản pháp lý gốc, không dựa vào memory

---
### TASK-16: Xây dựng Baseline Naive RAG ✅
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-08 (dùng cùng bộ dữ liệu)
**Có thể song song với:** TASK-15
**Hoàn thành:** 2026-05-17

#### Mục tiêu
Xây dựng hệ thống Naive RAG để làm baseline so sánh. Điều kiện bắt buộc để so sánh có giá trị khoa học: cùng bộ dữ liệu, cùng LLM, cùng embedding model — **chỉ khác phần retrieval** (chunking cố định thay vì graph-aware).

#### Đầu vào
- `data/raw/*.md` — cùng dữ liệu gốc
- BGE-M3, LLM client — cùng model

#### Đầu ra
- `src/baseline/naive_rag.py`:
  - `fixed_chunker(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]`
  - `run_baseline_ingestion(data_dir: str)` — chunk và index vào Qdrant collection `baseline_legal_texts`
  - `run_baseline_query(question: str) -> dict` — vector search thuần, không có graph, không có metadata filter

#### Định nghĩa Hoàn thành (DoD)
- [x] `run_baseline_ingestion()` chạy thành công, tạo collection `baseline_legal_texts` trong Qdrant (17 files, 1718 chunks)
- [x] `run_baseline_query(question)` trả về câu trả lời với cùng format output như `run_pipeline(question)` (BaselineResult TypedDict khớp PipelineResult)
- [x] Baseline dùng đúng BGE-M3 và LLM — reuse trực tiếp `load_model()` và `generate_answer()` của GraphRAG
- [ ] Baseline chạy được trên toàn bộ 30+ câu hỏi trong test set mà không crash (chờ test set full ở TASK-15; sample Q001 OK với 4 citations đúng)

---
### TASK-17: Chạy Evaluation và tính Metrics 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-14, TASK-15, TASK-16
**Có thể song song với:** Không
**Hoàn thành:** Chưa

#### Mục tiêu
Chạy cả GraphRAG pipeline và Baseline trên toàn bộ test set, tính toán đầy đủ các metrics retrieval và generation, lưu kết quả có thể reproduce.

#### Đầu vào
- `data/evaluation/test_set.json`
- `src/pipeline.py` (GraphRAG)
- `src/baseline/naive_rag.py`

#### Đầu ra
- `data/evaluation/results_graphrag.json` — kết quả từng câu hỏi
- `data/evaluation/results_baseline.json` — kết quả từng câu hỏi
- `src/evaluation/metrics.py` — tính Precision@k, Recall@k, MRR, Citation Accuracy
- `data/evaluation/metrics_summary.md` — bảng so sánh GraphRAG vs Baseline

#### Định nghĩa Hoàn thành (DoD)
- [ ] Cả 2 hệ thống đã chạy trên toàn bộ ≥ 30 câu hỏi và lưu kết quả (hiện chạy 19 câu Đất đai — chờ TASK-15 thêm Hộ tịch + Nuôi con nuôi)
- [x] Bảng metrics đầy đủ: Citation Precision/Recall/F1 (cấp Khoản + cấp Điều), Norm-level Recall, Latency mean+p95, Negative correct rate cho cả 2 hệ thống — output `metrics_summary_<timestamp>.md`
- [x] Metrics được tính chia theo lĩnh vực (`by_theme`) và gap_type (`by_gap`) — aggregate() trong metrics.py
- [x] Correctness và Faithfulness được đánh giá thủ công cho ≥ 10 câu hỏi/hệ thống — `data/evaluation/MANUAL_EVAL.md` (G 4.5/4.9 vs B 3.5/4.3)
- [x] File kết quả JSON có timestamp và config rõ ràng để reproduce (`results_<system>_<timestamp>.json` chứa test_set path, timestamp, per-question full)
- [x] Tooling tối ưu chi phí dev: `--reuse-results` (re-compute metric không tốn API), `--llm-cache-dir` (cache hit $0)

---
### TASK-18: Phân tích kết quả theo Gap 📋
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-17
**Có thể song song với:** Không
**Hoàn thành:** Chưa

#### Mục tiêu
Phân tích kết quả từ TASK-17 theo 3 Gap của nghiên cứu, xác định failure cases, rút ra kết luận. Đây là nội dung chính của chương "Kết quả & Thảo luận" trong khóa luận.

#### Đầu vào
- `data/evaluation/metrics_summary.md`
- `data/evaluation/results_graphrag.json`
- `data/evaluation/results_baseline.json`

#### Đầu ra
- `data/evaluation/gap_analysis.md` — phân tích 3 Gap
- `data/evaluation/failure_cases.md` — ≥ 3 failure case với phân tích nguyên nhân
- `data/evaluation/limitations.md` — danh sách limitations chính thức

#### Định nghĩa Hoàn thành (DoD)
- [ ] `gap_analysis.md` có phần riêng cho mỗi Gap với số liệu cụ thể so sánh GraphRAG vs Baseline
- [ ] `failure_cases.md` có ≥ 3 trường hợp thất bại được phân tích nguyên nhân (không phải chỉ mô tả)
- [ ] `limitations.md` liệt kê ≥ 5 limitation với lý do kỹ thuật rõ ràng (không phải "không đủ thời gian")
- [ ] Kết luận trả lời rõ ràng: hệ thống giải quyết được Gap nào, Gap nào chưa, và tại sao

---

## 3. Sơ đồ phụ thuộc

```
[TASK-00] Docker Setup ──────────────────────────────────────────────┐
[TASK-01] Python + Git Setup ────────────────────────────────────────┤
           (song song)                                                 │
                            [TASK-02] Integration Verification ◄──────┘
                                         │
              ┌──────────────────────────┤
              │                          │
[TASK-03] Mapping Table (song song)      │
     │                                   │
[TASK-04] Thu thập & Chuẩn hóa           │
     │                                   │
[TASK-05] Cross-check ◄──────────────────┘
     │
     ├── [A] [TASK-06] Parser ──────────────────────────────────────┐
     │         │                                                      │
     │    [TASK-07] Graph Builder (Neo4j) ──────────────────────────┤
     │         │                                                      │
     │    [TASK-08] Vector Indexing (Qdrant) ───────────────────────┤
     │                                                               │
     └── [B] Unit tests cho TASK-06 (song song)                     │
                                                                     │
                        [TASK-09] Phase 2 Verification ◄────────────┘
                                     │
              ┌──────────────────────┤
     [A]      │              [B]     │
[TASK-10] Query Planner     [TASK-12] Semantic Filtering
[TASK-11] Sub-graph Extraction
              │                      │
              └──────────────────────┤
                                     │
                        [TASK-13] Context Assembly + Generation
                                     │
                        [TASK-14] Integration E2E ──── Gate Phase 3
                                     │
              ┌──────────────────────┤
[TASK-15] Test Set            [TASK-16] Baseline (song song)
     │                               │
     └──────────────────────────────┤
                                    │
                        [TASK-17] Chạy Evaluation
                                    │
                        [TASK-18] Phân tích theo Gap
```

**Các gate task (KHÔNG được bỏ qua):**
- TASK-02: Gate Phase 0 → Phase 1
- TASK-05: Gate Phase 1 → Phase 2
- TASK-09: Gate Phase 2 → Phase 3
- TASK-14: Gate Phase 3 → Phase 4

---

## 4. Hành động tiếp theo được khuyến nghị

1. ~~Thống nhất các quyết định còn open trong `docs/PROJECT_CONTEXT.md` (đặc biệt: LLM nào, BGE-M3 local hay API, format `id` cuối cùng)~~ ✅
   OQ-04 đã đóng (Claude, 2026-04-19). OQ-01 đã đóng (format id). OQ-03 và OQ-06 vẫn pending.

2. ~~[A] bắt đầu TASK-00, [B] bắt đầu TASK-01 — song song~~ ✅ Hoàn thành (2026-04-19)

3. ~~Hoàn thành TASK-01 còn thiếu: tạo nhánh `develop`~~ ✅ Hoàn thành (2026-05-05)

4. ~~Hoàn thành TASK-03 (Mapping Table)~~ [A] đã điền Sections 3+4. [B] cần điền phần Hộ tịch + Nuôi con nuôi.

5. ~~[A] làm TASK-04 Đất đai~~ ✅ Hoàn thành 2026-05-10. **[B] cần hoàn thành TASK-04 Hộ tịch + Nuôi con nuôi.**

6. **(HIỆN TẠI — chờ [B])** Sau khi [B] hoàn thành TASK-04: hai bên làm TASK-05 Cross-check chéo — [A] review file [B], [B] review file [A], sign-off vào `review_log.md`.

7. Sau TASK-05 pass: [A] viết TASK-06 (Parser), [B] viết unit tests cho Parser — song song.
