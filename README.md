# Ontology-Driven GraphRAG cho Pháp luật Việt Nam

Hệ thống trả lời câu hỏi pháp lý hành chính Việt Nam có trích dẫn, kết hợp Knowledge Graph (Neo4j) và Vector Search (Qdrant). Hệ thống xử lý 3 lĩnh vực: **Đất đai**, **Hộ tịch**, và **Nuôi con nuôi** (Hôn nhân & Gia đình), giải quyết 3 gap nghiên cứu: đa lĩnh vực, đa địa phương (TP.HCM & Đồng Nai), và đa tầng văn bản (Luật → Nghị định → Thông tư → Quyết định UBND).

## Kết quả chính (v2.7, 26 câu Đất đai, N=3)

| Metric | GraphRAG (v2.7) | Baseline (Naive RAG) | Δ % |
|---|---:|---:|---:|
| **F1 Khoản** (strict cấp Điều+Khoản) | **0.539 ± 0.021** | 0.295 | **+82.7%** |
| F1 Điều (cấp văn bản+Điều) | 0.567 ± 0.032 | 0.295 | +92.2% |
| Norm Recall (văn bản) | 0.931 ± 0.005 | 0.699 | +33.2% |
| **Gap 3 (đa tầng, n=15)** | **0.466** | 0.145 | **+221%** ← hypothesis chính chứng minh |
| Faithfulness (citation trust) | 0.916 ± 0.069 | n/a | mới |
| Negative correct (refusal) | 100% | 100% | tied |
| Latency mean | 22.92 ± 0.12s | 18.29s | +25% |

Toàn bộ chi tiết trong [`data/evaluation/ABLATION_MATRIX.md`](data/evaluation/ABLATION_MATRIX.md) và [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md).

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
       --jurisdiction tp-hcm --bypass-completeness
```

Output: panel câu hỏi → panel trả lời (markdown render) → table citations → thống kê.

```bash
# Hiện chi tiết pipeline trace
python -m src.demo "..." --trace
```

### Evaluation framework

Chạy full eval 26 câu Đất đai + so sánh với Baseline:

```bash
python -m src.evaluation.run_evaluation \
       --test-set data/evaluation/test_set_dat_dai.json \
       --systems graphrag,baseline \
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
├── docs/                 ← Tài liệu dự án (PROJECT_CONTEXT, PROJECT_STATUS, plan, Instruction)
├── thesis/               ← Skeleton chapters cho luận văn (CHAPTERS_OUTLINE, CHAPTER_4_EXPERIMENTS)
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
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Changelog đầy đủ + trạng thái task hiện tại (v2.7)
- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) — Kiến trúc hệ thống, schema Ontology, tech stack, known problems
- [`docs/plan.md`](docs/plan.md) — Kế hoạch thực thi ban đầu (historical reference)

### Tài liệu evaluation
- [`data/evaluation/ABLATION_MATRIX.md`](data/evaluation/ABLATION_MATRIX.md) — Bảng impact cumulative 4 fix layers (Baseline → v2.7)
- [`data/evaluation/REPRODUCIBILITY_REPORT_20260520.md`](data/evaluation/REPRODUCIBILITY_REPORT_20260520.md) — N=3 study (F1 = 0.539 ± 0.021)
- [`data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md`](data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md) — Phân tích nguyên nhân F1 gap
- [`data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md`](data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md) — Limitations honest (Q022 embedding blindness)
- [`data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md`](data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md) — 3-round prompt ablation

### Tài liệu thesis
- [`thesis/CHAPTERS_OUTLINE.md`](thesis/CHAPTERS_OUTLINE.md) — Skeleton 5 chapters + Appendix với data refs
- [`thesis/CHAPTER_4_EXPERIMENTS.md`](thesis/CHAPTER_4_EXPERIMENTS.md) — Chapter 4 detailed scaffold với tables ready
