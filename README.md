# Ontology-Driven GraphRAG cho Pháp luật Việt Nam

Hệ thống hỏi–đáp pháp luật hành chính có trích dẫn, kết hợp Đồ thị tri thức (Neo4j) và Tìm kiếm ngữ nghĩa (Qdrant + BGE-M3).

Phạm vi 3 lĩnh vực — **Đất đai**, **Hộ tịch**, **Nuôi con nuôi**. Bốn thách thức được giải quyết: đa lĩnh vực, đa địa phương (TP.HCM, Đồng Nai), đa tầng văn bản (Luật → Nghị định → Thông tư → Quyết định UBND) và đa phiên bản (hiệu lực theo thời gian).

> Đây là repo phát triển của khóa luận. Bản mã nguồn nộp kèm báo cáo là bản chốt đã lược bớt, chỉ chạy Gemini; repo này giữ đầy đủ lịch sử phát triển và cả đường chạy Claude (xem mục [Khác biệt với bản nộp](#khác-biệt-với-bản-nộp)).

---

## Kết quả chính

Bộ câu hỏi 137 câu đã đóng băng, 3 lĩnh vực, mô hình Gemini, trung bình 3 lần chạy:

| Thước đo | GraphRAG | Naive RAG |
|---|---:|---:|
| **F1 cấp Khoản** | **0.578 ± 0.004** | 0.435 ± 0.008 |
| F1 cấp Điều | 0.596 ± 0.006 | 0.459 ± 0.008 |
| Norm Recall | 0.771 ± 0.016 | 0.588 ± 0.005 |

Chênh lệch ghép cặp theo từng câu (123 câu có đáp án tham chiếu): **Δ +0.143**, khoảng tin cậy 95% **[0.061, 0.225]**, Wilcoxon **p = 0.0015** → có ý nghĩa thống kê. *(bootstrap 10000 lần lấy mẫu lại, seed cố định)*

Bậc thang hệ tham chiếu (F1 cấp Khoản): oracle 0.858 > **graphrag 0.578** ≈ bm25 0.571 > naive RAG 0.435 > closed-book 0.102.

Ablation phân ly kép chứng minh bước duyệt đồ thị cần thiết cho thách thức đa tầng và đa phiên bản (gỡ bước duyệt: −0.091 / −0.130).

Tính trung thực của trích dẫn: tỉ lệ tồn tại 880/881 = 99.9% (kiểm tra tất định, không gọi mô hình); tỉ lệ được hậu thuẫn 247/296 = 83.5% (giám khảo `gemini-2.5-pro` — lưu ý hạn chế tự-đánh-giá vì hệ cũng chạy Gemini).

Toàn bộ số liệu chốt: [`docs/V2_RESULTS.md`](docs/V2_RESULTS.md). Tài liệu đánh giá cũ (bộ 26 câu, F1 0.539) chỉ còn giá trị lịch sử.

---

## Yêu cầu môi trường

- Python 3.10 trở lên (đã kiểm thử trên 3.12)
- Docker + Docker Compose v2
- RAM tối thiểu 8 GB, dung lượng trống khoảng 5 GB
- Khóa mô hình ngôn ngữ: Anthropic Claude và/hoặc Google Gemini

---

## Cài đặt

**1. Sao chép cấu hình rồi điền khóa và mật khẩu thật**

```bash
cp .env.example .env
# mở .env, điền NEO4J_PASSWORD, ANTHROPIC_API_KEY và/hoặc nhóm biến GEMINI_*
```

**2. Cài thư viện**

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Khởi động cơ sở dữ liệu**

```bash
docker compose up -d
```

- Neo4j Browser: <http://localhost:7474>
- Qdrant Dashboard: <http://localhost:6333/dashboard>

**4. Kiểm tra kết nối**

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

## Nạp dữ liệu

Chạy lần lượt. Cả hai đều idempotent (dùng `MERGE` và `upsert`) nên chạy lại nhiều lần vẫn cho cùng một kết quả.

```bash
python -m src.ingestion.graph_builder    # dựng đồ thị tri thức trong Neo4j
python -m src.ingestion.vectorizer       # nạp vector vào Qdrant
```

**Lưu ý trước khi chạy:**

- `graph_builder` có bước ánh xạ ontology bằng mô hình ngôn ngữ (Pass 4) nên cần khóa API và mất vài phút.
- `vectorizer` tải mô hình nhúng BGE-M3 (khoảng 2 GB) trong lần chạy đầu. Đây là bước tải qua mạng, không phải treo máy.

---

## Chạy thử

```bash
python -m src.demo "Hạn mức giao đất ở cho cá nhân tại TP.HCM tối đa là bao nhiêu m²?" \
       --jurisdiction tp-hcm
```

Kết quả hiển thị: câu hỏi → câu trả lời → bảng trích dẫn → thống kê. Thêm `--trace` để xem chi tiết từng bước truy hồi.

Hệ là 1 hỏi–1 đáp: khi câu hỏi thiếu thông tin (ví dụ không nêu địa phương), pipeline trả lời best-effort chứ không dừng lại hỏi ngược.

**Chọn mô hình** qua `--llm-mode`:

| Giá trị | Hành vi |
|---|---|
| `claude` | Chỉ Claude — dùng cho đánh giá để tái lập được |
| `claude-fallback` | Claude, tự chuyển sang Gemini khi lỗi hạ tầng |
| `gemini` | Chỉ Gemini — khớp số liệu ở mục Kết quả chính |
| `gemini-fallback` | Gemini, tự chuyển sang Claude khi lỗi hạ tầng |

Hai chế độ dự phòng chỉ chuyển khi gặp lỗi hạ tầng (quá hạn mức, lỗi 5xx, hết thời gian chờ); lỗi logic vẫn ném ra bình thường.

---

## Chạy đánh giá

So sánh hệ đề xuất với đối thủ chính:

```bash
python -m src.evaluation.run_evaluation \
       --test-set data/evaluation/test_set_v2.json \
       --systems graphrag,baseline \
       --llm-mode gemini \
       --no-llm-cache \
       --faithfulness-tier 2
```

Tái lập toàn bộ bậc thang 5 hệ tham chiếu:

```bash
python -m src.evaluation.run_evaluation \
       --test-set data/evaluation/test_set_v2.json \
       --systems graphrag,baseline,bm25,closed-book,oracle \
       --llm-mode gemini --no-llm-cache
```

Tính khoảng tin cậy và kiểm định ý nghĩa thống kê từ tệp kết quả đã lưu (không gọi mô hình):

```bash
python -m src.evaluation.expanded_eval \
       --graphrag data/evaluation/results_graphrag_<thời điểm>.json \
       --baseline data/evaluation/results_baseline_<thời điểm>.json
```

So sánh hai lần chạy:

```bash
python -m src.evaluation.compare_runs run_A.json run_B.json
```

Tệp kết quả sinh ra trong `data/evaluation/`:

- `results_<hệ>_<thời điểm>.json` — chi tiết từng câu
- `metrics_summary_<thời điểm>.md` — bảng tổng hợp
- `REPORT_<thời điểm>.md` — báo cáo dễ đọc theo từng câu

> Số liệu ở mục Kết quả chính đo với `--llm-mode gemini`. Đổi mô hình thì kết quả sẽ khác.

---

## Chạy kiểm thử

```bash
pytest tests/ -q
```

Kết quả mong đợi: **316 test pass** (không cần Docker hay khóa API).

---

## Cấu trúc thư mục

```
vn-legal-graphrag/
├── data/
│   ├── raw/              ← Kho ngữ liệu đã chuẩn hóa — 32 văn bản pháp luật (.md)
│   ├── ontology/         ← core_v1.json — Core Ontology (khái niệm + thủ tục)
│   ├── sources/          ← manifest.md — truy vết nguồn thu thập
│   └── evaluation/       ← Bộ câu hỏi, kết quả các lần chạy, báo cáo phân tích
├── src/
│   ├── ingestion/        ← parser, graph_builder, vectorizer, ontology_mapper
│   ├── retrieval/        ← query_planner, subgraph_extractor, semantic_filter,
│   │                        context_assembler, answer_generator, verifier,
│   │                        ablation_config, reranker
│   ├── baseline/         ← naive_rag, bm25_rag, closed_book
│   ├── evaluation/       ← run_evaluation, metrics, faithfulness, oracle,
│   │                        expanded_eval, error_analysis, human_eval, ...
│   ├── utils/            ← llm_config, gemini_fallback, connection_check,
│   │                        validate_metadata
│   ├── pipeline.py       ← Điều phối pipeline đầu-cuối
│   └── demo.py           ← Giao diện dòng lệnh chạy thử
├── tests/                ← Kiểm thử đơn vị
├── notebooks/            ← Notebook kiểm chứng Phase 2, 3, 4
├── docs/                 ← Tài liệu dự án
├── docker-compose.yml    ← Neo4j 5.18 + Qdrant v1.13.6
├── requirements.txt
├── .env.example
└── CLAUDE.md             ← Quy ước, lược đồ, nhật ký quyết định thiết kế
```

---

## Kiến trúc truy hồi ba giai đoạn

1. **Định tuyến văn bản** — nhúng câu hỏi, so với tóm tắt của từng văn bản để chọn ra nhóm ứng viên.
2. **Duyệt đồ thị và lọc cứng** — mở rộng sang văn bản liên đới qua quan hệ `IMPLEMENTS` (hướng dẫn thi hành) và `AMENDS` (sửa đổi), rồi lọc theo địa phương và thời điểm hiệu lực.
3. **Tìm kiếm lai** — xếp hạng điều khoản bằng bốn nguồn tín hiệu (trích dẫn có cấu trúc, ngữ nghĩa, từ khóa, đồ thị), hợp nhất theo thứ hạng nghịch đảo, có trần đa dạng theo văn bản và theo tầng.

Lược đồ đồ thị: **9 loại nút** (Theme, Norm, Component, CTV, TextUnit, Jurisdiction, Amendment, Concept, Procedure) và **10 loại cạnh**. Chi tiết ở [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

---

## Khác biệt với bản nộp

Bản mã nguồn nộp kèm báo cáo được lược bớt cho gọn: chỉ giữ đường chạy **Gemini**, bỏ toàn bộ mã liên quan tới Claude, và vì thế có ít test hơn. Repo này giữ nguyên cả hai nhà cung cấp cùng bốn chế độ `--llm-mode`, nên số test cao hơn.

Kết quả đánh giá của hai bản là **như nhau** vì mọi số liệu công bố đều đo ở chế độ `gemini`.

---

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/V2_RESULTS.md`](docs/V2_RESULTS.md) | Số liệu chốt — nguồn cho chương đánh giá |
| [`docs/EVALUATION_ARCHITECTURE.md`](docs/EVALUATION_ARCHITECTURE.md) | Kiến trúc đánh giá 4 khối E0–E3 |
| [`docs/GT_FREEZE.md`](docs/GT_FREEZE.md) | Đăng ký trước bộ câu hỏi vàng (đóng băng, có mã băm) |
| [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Kiến trúc hệ thống, lược đồ ontology, hạn chế đã biết |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | Nhật ký thay đổi và trạng thái công việc |
| [`CLAUDE.md`](CLAUDE.md) | Quy ước mã nguồn, lược đồ tra nhanh, nhật ký quyết định D-01…D-26 |

**Phân tích và kết quả phủ định** *(các hướng đã thử và bị loại — số liệu trên bộ 26 câu đời đầu)*

- [`data/evaluation/ABLATION_MATRIX.md`](data/evaluation/ABLATION_MATRIX.md) — tác động tích lũy của bốn lớp sửa
- [`data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md`](data/evaluation/ROOT_CAUSE_ANALYSIS_20260519.md) — truy nguyên khoảng cách F1
- [`data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md`](data/evaluation/RETRIEVAL_LIMITATIONS_20260520.md) — hạn chế của khâu truy hồi
- [`data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md`](data/evaluation/PROMPT_TUNING_EXPERIMENT_20260519.md) — ba vòng tinh chỉnh lời nhắc
- [`data/evaluation/REPRODUCIBILITY_REPORT_20260520.md`](data/evaluation/REPRODUCIBILITY_REPORT_20260520.md) — nghiên cứu tái lập N=3

---

## Ghi chú

- Không commit tệp `.env` thật vì chứa khóa API.
- Mọi thay đổi cơ sở dữ liệu đều đi qua script Python (`MERGE` và `upsert`, idempotent), không thao tác trực tiếp qua HTTP.
- Gemini có thể chạy qua Vertex AI + ADC thay cho api_key: chạy `gcloud auth application-default login` và đặt `GEMINI_USE_VERTEX=true` trong `.env`.
- Định danh mọi nút trong đồ thị sinh bằng hàm băm SHA-256 từ đường dẫn ngữ cảnh, không dùng UUID, nên hai lần nạp dữ liệu khác nhau vẫn cho cùng một đồ thị.
- `src/retrieval/reranker.py` (cross-encoder) không nằm trong luồng truy hồi chính: tích hợp đã được thử và bị loại sau thí nghiệm gỡ bỏ, mã giữ lại làm tư liệu cho kết quả phủ định.

---

## Nhóm thực hiện

Đào Nguyễn Tấn Đạt, Nguyễn Duy Minh Đăng — ngành Khoa học Máy tính.
Giảng viên hướng dẫn: Lê Anh Cường, Khoa Công nghệ thông tin.
