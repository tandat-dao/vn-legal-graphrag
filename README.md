# Ontology-Driven GraphRAG cho Pháp luật Việt Nam

Hệ thống trả lời câu hỏi pháp lý hành chính Việt Nam có trích dẫn, kết hợp Knowledge Graph (Neo4j) và Vector Search (Qdrant). Hệ thống xử lý 3 lĩnh vực: **Đất đai**, **Hộ tịch**, và **Nuôi con nuôi** (Hôn nhân & Gia đình), giải quyết 4 gap nghiên cứu: đa lĩnh vực, đa địa phương (TP.HCM & Đồng Nai), đa tầng văn bản (Luật → Nghị định → Thông tư → Quyết định UBND), và **đa phiên bản** (temporal versioning: CTV, amendment tracking, regime change).

## Kết quả chính (v2 canonical — GT freeze 137 câu, 3 lĩnh vực, Gemini, N=3)

| Metric | GraphRAG | Baseline (Naive RAG) |
|---|---:|---:|
| **F1 Khoản** (strict cấp Điều+Khoản) | **0.578 ± 0.004** | 0.435 ± 0.008 |
| Norm Recall (văn bản) | 0.771 ± 0.016 | — |

Chênh lệch ghép cặp (123 câu có GT): **Δ +0.156, KTC 95% [0.070, 0.242], Wilcoxon p = 0.001** → có ý nghĩa thống kê. Bậc thang baseline: oracle 0.858 > bm25 0.571 ≈ graphrag 0.578 > baseline 0.435 > closed-book 0.102. Ablation phân ly kép chứng minh cạnh duyệt đồ thị cần thiết cho Gap 3/4 (no-traversal −0.091/−0.130).

Toàn bộ số liệu chốt: [`docs/V2_RESULTS.md`](docs/V2_RESULTS.md) (nguồn cho Chương 4). Tài liệu eval cũ (dev set 26 câu, F1 0.539) chỉ còn giá trị lịch sử.

---

## Yêu cầu hệ thống

- **Python** ≥ 3.10
- **Docker Desktop** (Docker Compose v2)
- **RAM** ≥ 8GB

---

## Khởi động môi trường

1. Copy file `.env.example` thành `.env` và điền giá trị thực:

   ```bash
   cp .env.example .env
   # Mở .env và thay đổi NEO4J_PASSWORD thành mật khẩu bạn muốn sử dụng
   ```

2. Khởi động các service Docker:

   ```bash
   docker compose up -d
   ```

3. Kiểm tra các service đã chạy:

   - **Neo4j Browser:** truy cập [http://localhost:7474](http://localhost:7474) — đăng nhập bằng tài khoản trong `.env`
   - **Qdrant Dashboard:** truy cập [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

4. Dừng các service khi không cần:

   ```bash
   docker compose down
   ```

---

## Cài đặt Python dependencies

1. Tạo virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Kích hoạt virtual environment:

   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```

3. Cài đặt dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Sử dụng hệ thống

### Demo CLI (cho 1 câu hỏi)

Sau khi đã ingest dữ liệu (Phase 2 hoàn tất), thử hỏi 1 câu:

```bash
python -m src.demo "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu m²?" \
       --jurisdiction tp-hcm
```

Output: panel câu hỏi → panel trả lời (markdown render) → table citations → thống kê. Hệ chạy best-effort khi thiếu field (1Q-1A, không hỏi lại). Demo Gemini có dự phòng Claude: thêm `--llm-mode gemini-fallback`.

```bash
# Hiện chi tiết pipeline trace
python -m src.demo "..." --trace
```

### Evaluation framework

Chạy eval canonical (GT freeze 137 câu, 3 lĩnh vực) + so sánh với Baseline:

```bash
python -m src.evaluation.run_evaluation \
       --test-set data/evaluation/test_set_v2.json \
       --systems graphrag,baseline \
       --llm-mode gemini \
       --no-llm-cache \
       --faithfulness-tier 2
```

Output:
- `data/evaluation/results_<system>_<timestamp>.json` — per-question detail
- `data/evaluation/metrics_summary_<timestamp>.md` — aggregate tables
- `data/evaluation/REPORT_<timestamp>.md` — human-readable per-question report

### So sánh 2 runs

```bash
python -m src.evaluation.compare_runs run_A.json run_B.json
```

### Kiểm tra kết nối

```bash
python src/utils/connection_check.py
```

Kết quả mong đợi:

```
=== Integration Verification ===
Checking Neo4j connection...
  → verify_connectivity: OK
  → Create TestNode: OK
  → Read TestNode: OK
  → Delete TestNode: OK
  → Verify cleanup: OK
✅ Neo4j: PASS

Checking Qdrant connection...
  → Create collection smoke_test: OK
  → Upsert vector: OK
  → Search vector: OK
  → Delete collection: OK
  → Verify cleanup: OK
✅ Qdrant: PASS

=== Result: 2/2 PASSED ===
```

---

## Cấu trúc thư mục

```
graphrag-vn-law/
├── data/
│   ├── raw/              ← Phase 1: các file *.md đã chuẩn hóa
│   ├── sources/          ← Phase 1: file PDF/DOCX gốc từ vbpl.vn
│   ├── processed/        ← Phase 2: dữ liệu trung gian
│   ├── evaluation/       ← Phase 4: bộ câu hỏi test, kết quả, comparison reports
│   ├── verification/     ← Phase 2: phase2_report.md sign-off
│   ├── neo4j/            ← Docker volume cho Neo4j (gitignored)
│   └── qdrant/           ← Docker volume cho Qdrant (gitignored)
├── src/
│   ├── ingestion/        ← Phase 2: parser, graph_builder, vectorizer
│   ├── retrieval/        ← Phase 3: query_planner, subgraph_extractor, semantic_filter (4-pass), context_assembler, answer_generator
│   ├── baseline/         ← Phase 4: hệ thống Naive RAG baseline
│   ├── evaluation/       ← Phase 4: run_evaluation, metrics, faithfulness, report_builder, compare_runs, instrument_retrieval, build_ablation_matrix, build_reproducibility_report
│   ├── utils/            ← Tiện ích dùng chung (connection_check, validate_metadata, llm_config)
│   ├── demo.py           ← Demo CLI cho weekly meeting (rich UI)
│   └── pipeline.py       ← End-to-end pipeline orchestrator
├── tests/                ← Unit tests
├── notebooks/            ← Jupyter notebooks cho exploration
├── docs/                 ← Tài liệu dự án (PROJECT_CONTEXT, PROJECT_STATUS, V2_RESULTS...)
│   └── thesis/           ← Bản nháp luận văn (Ch1–5 + front/back matter)
├── docker-compose.yml    ← Định nghĩa Docker services (Neo4j + Qdrant)
├── .env.example          ← Template biến môi trường
├── requirements.txt      ← Python dependencies
├── .gitignore            ← Danh sách file/thư mục không theo dõi bởi Git
├── CLAUDE.md             ← Quy tắc và conventions cho AI assistant
└── README.md             ← File này
```

---

## Tài liệu dự án

- [`CLAUDE.md`](CLAUDE.md) — Conventions, rules, schema quick reference, Decision Log
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Changelog đầy đủ + trạng thái task hiện tại (v2.22)
- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) — Kiến trúc hệ thống, schema Ontology, tech stack, known problems

### Tài liệu evaluation
- [`data/evaluation/ABLATION_MATRIX.md`](data/evaluation/ABLATION_MATRIX.md) — Bảng impact cumulative 4 fix layers + per-gap 4-gap breakdown (Baseline → v2.8)
- [`data/evaluation/REPRODUCIBILITY_REPORT_20260520.md`](data/evaluation/REPRODUCIBILITY_REPORT_20260520.md) — N=3 study (F1 = 0.539 ± 0.021)
- [`data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md`](data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md) — Phân tích nguyên nhân F1 gap
- [`data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md`](data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md) — Limitations honest (Q022 embedding blindness)
- [`data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md`](data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md) — 3-round prompt ablation

### Tài liệu thesis
- [`docs/thesis/`](docs/thesis/) — Bản nháp toàn quyển luận văn (Ch1–5 + front/back matter, Markdown) — xem `docs/thesis/README.md`
- [`docs/thesis/00_DE_CUONG.md`](docs/thesis/00_DE_CUONG.md) — Đề cương chi tiết
