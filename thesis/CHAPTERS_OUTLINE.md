# Thesis Chapters — Outline với data references

> Skeleton structure cho thesis. Mỗi chapter có: (a) Mục tiêu; (b) Sub-sections;
> (c) Specific data points / file references; (d) Key claims kèm số liệu.
> Prose viết theo voice của tác giả — outline này là scaffolding.

---

## Chapter 3 — Phương pháp luận (Methodology)

### 3.1 Kiến trúc tổng thể
- **Schema ontology** (6 node types + 7 edge types): [CLAUDE.md](../CLAUDE.md) section "SCHEMA ONTOLOGY"
- **Tier mapping 1-4**: Luật/Bộ luật → NĐ/PL → TT → QĐ địa phương
- **3 Gap targeted**: đa lĩnh vực, đa địa phương, đa tầng → motivation
- **Quyết định thiết kế** (D-01 đến D-08): xem Decision Log trong CLAUDE.md

### 3.2 Phase 1 — Thu thập và chuẩn hoá dữ liệu
- Thu thập **thủ công** từ vbpl.vn (KHÔNG dùng OCR pipeline) — D-01
- **VBHN làm nguồn nội dung chính** — D-02 (giải quyết NĐ chồng chéo sửa đổi)
- Format chuẩn `data/raw/*.md`:
  - YAML frontmatter (id, title, tier, theme, jurisdiction, implements, valid_from, valid_to, summary, amended_by_norms)
  - Heading 4 cấp: `## Điều X. → ### Khoản N. → #### Điểm n. → ##### Tiết k.`
  - HTML comment `<!-- amended_by: ... -->` cho footnote sửa đổi
- Validation: `src/utils/validate_metadata.py` — check 17/17 file Đất đai PASS

### 3.3 Phase 2 — Ingestion pipeline
- **Structure-aware Parser** (`src/ingestion/parser.py`):
  - Stack-based heading parser preserve hierarchy
  - Deterministic ID = `sha256(">".join(context_path))[:16]` — D #4 trong CLAUDE.md
- **Graph Builder** (`src/ingestion/graph_builder.py`):
  - `MERGE` everywhere (idempotent) — D #3
  - CTV node với `valid_from`/`valid_to` (sentinel '9999-12-31' thay null per fix commit ac516ad)
- **Vector Indexing** (`src/ingestion/vectorizer.py`):
  - BGE-M3 (1024 dim) cho TextUnit + Summary
  - 2 collection: `legal_texts` (TextUnit + Summary cấp Norm)

### 3.4 Phase 3 — Retrieval pipeline

**Sub-graph Extraction (3 stages)**:
1. **Stage 1** ([src/retrieval/subgraph_extractor.py:100](../src/retrieval/subgraph_extractor.py#L100)): Qdrant summary search → top-N norm_ids (default N=10)
2. **Stage 2**: Neo4j traverse `[:IMPLEMENTS|AMENDS*1..4]` + filter jurisdiction + temporal → result_norms
3. **Stage 3**: Procedure-mapped Components qua `[:IMPLEMENTS]` → graph_component_ids

**Hybrid Search** ([src/retrieval/semantic_filter.py:hybrid_search](../src/retrieval/semantic_filter.py)):
- Dense (BGE-M3) + Keyword (slug overlap) + Graph boost → RRF fusion
- **4-pass allocation** (innovation key cho thesis):
  - **Pass -1 (Structured Citation Boost)**: regex `Khoản X Điều Y` → fetch matching components qua Neo4j → ép vào top-K
  - **Pass 0 (Dense Floor)**: top-1 dense per norm — preserve pure semantic ground truth
  - **Pass 1 (RRF Breadth)**: top-1 per norm theo RRF score (bổ sung norms ko có dense)
  - **Pass 2 (Depth)**: fill remaining theo RRF order
- Caps: per_norm=3, per_tier={1:8, 2:8, 3:6, 4:8}

**Context Assembly + Answer Generation**:
- `assemble_context` ([src/retrieval/context_assembler.py:174](../src/retrieval/context_assembler.py)): sort + token cap (6000)
- Prompt template với 5 rule blocks: lex superior/posterior/specialis, amendment warning, **TEMPORAL span-regime** (rule mới — point 4), phạm vi corpus
- Claude Sonnet 4.6 + temperature=0 + max_retries=8

### 3.5 Phase 4 — Evaluation framework
- **Test set** ([data/evaluation/test_set_dat_dai.json](../data/evaluation/test_set_dat_dai.json)): 26 câu Đất đai
  - 3 gap1, 6 gap2, 15 gap3, 2 negative
  - Mỗi câu có `ground_truth_citations` Khoản-level
- **Metrics**:
  - F1 Khoản (strict), F1 Điều (loose)
  - Norm Recall (van_ban level)
  - Negative correctness (refusal rate)
  - **Faithfulness** (mới — [src/evaluation/faithfulness.py](../src/evaluation/faithfulness.py)): existence_rate + support_rate
  - Latency mean/P95
- **Baseline**: Naive RAG với chunked retrieval (`src/baseline/naive_rag.py`)
  - Cùng dữ liệu, cùng embedding, cùng LLM → chỉ khác retrieval logic

---

## Chapter 4 — Thực nghiệm và Kết quả (Experiments)

### 4.1 Setup
- Hardware: MacBook (MPS), Docker Neo4j + Qdrant local
- LLM: Claude Sonnet 4.6 (answer) + Haiku 4.5 (query planner + faithfulness judge)
- Reproducibility: temperature=0, llm_cache, max_retries=8
- Eval mode: `force_jurisdiction` + `bypass_completeness` để đo retrieval+generation thuần (xem PROJECT_STATUS commit 225b3aa cho verify reproducibility 100%)

### 4.2 Bảng tổng hợp Ablation
**Sử dụng [ABLATION_MATRIX.md](../data/evaluation/ABLATION_MATRIX.md)** — copy/paste table này trực tiếp vào thesis.

Key takeaways từ matrix:
- Baseline → v2.6: F1 Khoản **+86%** (0.295 → 0.549)
- v2.3 canonical → v2.6 (4 fix cumulative): **+24.8%** (0.440 → 0.549)
- Negative correctness 100% giữ qua mọi config

### 4.3 Per-Gap breakdown — chứng minh hypothesis chính
Lấy table Per-Gap từ ABLATION_MATRIX.md.

**Hypothesis chính**: ontology + graph traversal mang lại lợi thế lớn nhất ở Gap 3 (đa tầng văn bản).

| Gap | Baseline F1 | GraphRAG v2.6 F1 | Δ % |
|---|---:|---:|---:|
| Gap 1 (đa lĩnh vực, n=3) | 0.194 | 0.350 | +80% |
| Gap 2 (đa địa phương, n=6) | 0.485 | 0.658 | +36% |
| **Gap 3 (đa tầng, n=15)** | **0.145** | **0.485** | **+234%** |
| Negative (n=2) | 1.000 | 1.000 | tied |

→ Gap 3 thắng vượt trội (3.3×) — đúng narrative thesis về Knowledge Graph traversal cho cross-tier relationships.

### 4.4 Case studies (deep dive)
4 cases để minh hoạ từng fix:

**Case A — Q024 (Dense Floor fix)**: 
- Vấn đề: GT "Điều 116 K5 Luật ĐĐ 2024" rank #2 dense nhưng bị graph_boost (procedure mapping "chuyen-muc-dich-su-dung-dat") đẩy Điều 121/123/227 lên đầu, chiếm per-norm cap (3) → GT mất top-25
- Diagnosis: empirical instrumentation [data/evaluation/RETRIEVAL_DEBUG_20260519-200009/](../data/evaluation/RETRIEVAL_DEBUG_20260519-200009/)
- Fix: Pass 0 Dense Floor — preserve top-1 dense per norm
- Kết quả: F1 0.00 → 0.67

**Case B — Q026 (Structured Cite + GT correction)**:
- Vấn đề: question "Khoản 1 Điều 13 NĐ 102/2024" — NĐ 102 không có Điều 13 trong corpus (data scope D-01/D-05) + dense top NĐ 49 = K11/K12 thay vì K1
- 2 fix: (1) GT correction cite AMENDING provision NĐ 49 Đ13 K1, (2) Pass -1 Structured Cite regex extraction
- Kết quả: F1 0.00 → 1.00

**Case C — Q022 (limitation case — embedding blindness)**:
- Vấn đề: GT "Điều 1 K1 Đa QĐ 18" — dense rank #7 trong QĐ 18 alone
- Đã thử Label-keyword Boost (Pass -0.5) — failed (net F1 -0.055 trên 8-câu ablation): "hạn mức" overlap với Điều 1 (GT) và Điều 3 (different topic) → TIE → wrong pick
- Decision: document as embedding limitation
- Reference: [RETRIEVAL_LIMITATIONS_20260520.md](../data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md)

**Case D — Q023 (Prompt TEMPORAL #4)**:
- Vấn đề: span-regime question (Luật 2013 vs Luật 2024) — Luật 2013 Điều 100 trong top-25 nhưng LLM chỉ cite Luật 2024
- Fix: prompt rule "PHẢI cite cả 2 regime khi span-regime signal"
- Kết quả: F1 0.00 → 0.40 (Edit 1 working as designed)
- Reference: [PROMPT_TUNING_EXPERIMENT_20260519.md](../data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md)

### 4.5 Latency analysis
- v2.6 latency mean: ~23s (real, --no-llm-cache)
- v2.3 canonical 2.85s là cache artifact — KHÔNG dùng
- Latency budget: ~15s LLM generation + ~5s retrieval + ~3s graph traversal

---

## Chapter 5 — Thảo luận (Discussion)

### 5.1 Khi nào GraphRAG vượt trội?
- **Gap 3 (đa tầng) là sweet spot**: KG traversal `[:IMPLEMENTS|AMENDS]` cho phép retrieve toàn bộ chuỗi Luật → NĐ → TT → QĐ khi câu hỏi cần tổng hợp đa tầng. Baseline (chunked) không có signal về tier → 0.145 vs 0.485 (3.3×)
- **Gap 1 (đa lĩnh vực)**: theme filter giúp định tuyến → +80%
- **Negative refusal**: cả 2 đều 100% — không phải differentiator (prompt rule đủ mạnh cho cả 2)

### 5.2 Khi nào GraphRAG KHÔNG vượt trội đáng kể? (Honest)
- **Gap 2 (đa địa phương)**: chỉ +36%. Nguyên nhân: Baseline với BGE-M3 vẫn match được "TP.HCM"/"Đồng Nai" qua keyword địa danh. Lexical overlap đủ cho hầu hết câu Gap 2 — đây là phát hiện thực nghiệm giá trị, KHÔNG manipulate.
- **Embedding semantic blindness** (Q022): cùng prefix "Hạn mức đất ở" cho 2 đối tượng khác nhau (hộ gia đình vs người có công) — embedding alone không phân biệt được; KG cũng không có signal về target population

### 5.3 Phương pháp luận lessons
- **N=1 ablation noisy**: LLM stochastic decoding gây F1 swing trên cùng câu input. Future eval cần N≥3 per case + bootstrap CI.
- **Empirical evidence trumps a priori reasoning both ways**:
  - "Regex = overfitting" prediction wrong (Pass -1 Struct Cite work +1.0 cho Q026)
  - "Label-keyword = p-hacking" prediction right (Pass -0.5 net -0.055)
- **Decision-by-data, not dogma**: mỗi proposed fix → ablation → quyết định
- Reference: [ROOT_CAUSE_ANALYSIS_20260519.md](../data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md)

### 5.4 Trade-off Knowledge Graph vs Pure Embedding
- KG mang context (tier, jurisdiction, AMENDED_BY) mà embedding không capture
- **NHƯNG**: graph_boost có thể OVERRIDE pure semantic match → cần Dense Floor (Pass 0) để balance
- Insight: "KG augments, không replace embedding ground truth"

---

## Chapter 6 — Giới hạn (Limitations)

### 6.1 Embedding semantic blindness
- Q022 case study (chi tiết từ RETRIEVAL_LIMITATIONS_20260520.md)
- BGE-M3 không phân biệt được target population qua label prefix similar

### 6.2 Test set scope
- 26 câu / 1 domain (Đất đai) — proof-of-concept, không đủ cho statistical claim mạnh
- 2 negative cases — sample nhỏ
- Đa số câu chosen by author — có potential selection bias (mặc dù không cherry-picking conscious)

### 6.3 Data scope (D-01/D-05)
- Thu thập theo Chương/Mục → bỏ một số Điều ngoài scope CMĐSDĐ cá nhân
- VD: NĐ 102/2024 không có Điều 13 trong corpus → Q026 GT phải correct theo data thực tế

### 6.4 Latency
- 23s mean — không suitable cho real-time UX
- Bottleneck: LLM call (~15s) — không phải retrieval

### 6.5 Methodology
- N=1 ablation không reliably distinguish signal vs LLM stochastic noise
- API outages (529 Overloaded) đe doạ reproducibility — đã document

### 6.6 Single-team domain coverage
- Chỉ Đất đai có data; chờ [B] đổ Hộ tịch + Nuôi con nuôi để verify cross-domain generalization

---

## Chapter 7 — Future Work

### 7.1 Cross-encoder re-ranking
- Vấn đề: Q022-class — embedding alone không disambiguate label prefix similar
- Hướng: BGE-Reranker / multilingual cross-encoder làm Stage 4 — rerank top-25 hybrid bằng (question, label) attention bidirectional

### 7.2 Multi-query expansion
- Rewrite question thành multi-aspect sub-queries
- VD: "ai được áp dụng hạn mức?" + "hạn mức bao nhiêu m²?" → dense match improve

### 7.3 Question-aware label filtering
- Parse question để extract target population, predicate → pre-filter Components theo target trước khi rank

### 7.4 Multi-domain coverage
- [B] đổ Hộ tịch + Nuôi con nuôi → verify generalization
- Mở test set ≥40-60 câu cross-domain

### 7.5 Production hardening
- Latency optimization (caching, parallel stages, smaller LLM cho easy queries)
- Confidence calibration cho refusal
- Multi-turn conversation support

### 7.6 N≥3 ablation methodology
- Bootstrap confidence intervals
- Statistical significance testing (paired t-test) cho prompt/retrieval changes

---

## Appendix — Data + Code references

### Output artifacts (tất cả trong [data/evaluation/](../data/evaluation/))
- `ABLATION_MATRIX.md` — bảng cumulative
- `COMPARE_canonical_vs_prompt-fix_20260519.md` — v2.3 → v2.4 diff
- `COMPARE_prompt-fix_vs_dense-floor_20260519.md` — v2.4 → v2.5 diff
- `COMPARE_v2.5_vs_v2.6_pass-neg1_20260520.md` — v2.5 → v2.6 diff
- `ROOT_CAUSE_ANALYSIS_20260519.md` — root-cause analysis methodology
- `PROMPT_TUNING_EXPERIMENT_20260519.md` — 3-round prompt ablation
- `RETRIEVAL_LIMITATIONS_20260520.md` — Q022 embedding limitation
- `RETRIEVAL_DEBUG_20260519-200009/` + `20260519-211804/` — Stage 1/2/3 dumps
- `REPORT_<timestamp>.md` — human-readable per-question reports

### Key source files
- `src/ingestion/parser.py` — structure-aware MD parser
- `src/ingestion/graph_builder.py` — Neo4j idempotent ingestion
- `src/retrieval/query_planner.py` — Claude Haiku query planning + Cách C theme backfill
- `src/retrieval/subgraph_extractor.py` — 3-stage retrieval
- `src/retrieval/semantic_filter.py` — Hybrid search với 4-pass allocation
- `src/retrieval/context_assembler.py` — context formatting + prompt building
- `src/retrieval/answer_generator.py` — LLM call + citation parsing
- `src/evaluation/metrics.py` — F1/NormR computation
- `src/evaluation/faithfulness.py` — 2-tier faithfulness metric
- `src/evaluation/run_evaluation.py` — eval orchestrator
- `src/baseline/naive_rag.py` — Naive RAG baseline

### Commits roadmap (git log)
- Phase 0-3: TASK-00 through TASK-14 (baseline implementation)
- Session 2026-05-19/20: 14 commits đóng góp 4 fix layers + tooling
  - `faeed8f` llm_config centralize
  - `155d170` cit_matches single source of truth
  - `e18e96f` report_builder
  - `023bb64` dedupe parse_citations
  - `da3eb4a` root-cause + instrumentation
  - `299b71a` prompt TEMPORAL #4
  - `a2728a8` compare_runs tool
  - `bdf6e2a` Dense Floor (Pass 0)
  - `705a02c` Pass -1 Structured Cite + Q026 GT fix
  - `20ffc81` revert Label-keyword + limitations doc
  - `1fa4dfc` Demo CLI + query_planner cache
  - `a08c02f` Faithfulness metric
  - `d7260a5` Ablation Matrix builder
