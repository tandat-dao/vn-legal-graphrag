# Ontology-Driven GraphRAG cho Pháp luật Việt Nam

Hệ thống hỏi–đáp pháp luật hành chính có trích dẫn, kết hợp Đồ thị tri thức (Neo4j) và Tìm kiếm ngữ nghĩa (Qdrant + BGE-M3).

Phạm vi 3 lĩnh vực — **Đất đai**, **Hộ tịch**, **Nuôi con nuôi**; 6 thủ tục hành chính; 32 văn bản. Bốn thách thức được giải quyết: đa lĩnh vực, đa địa phương (TP.HCM, Đồng Nai), đa tầng văn bản (Luật → Nghị định → Thông tư → Quyết định UBND) và đa phiên bản (hiệu lực theo thời gian).

> Đây là repo phát triển của khóa luận. Bản mã nguồn nộp kèm báo cáo là bản chốt đã lược bớt, chỉ chạy Gemini; repo này giữ đầy đủ lịch sử phát triển và cả đường chạy Claude (xem mục [Khác biệt với bản nộp](#khác-biệt-với-bản-nộp)).

> Sản phẩm nghiên cứu, không thay thế tư vấn pháp lý. Luôn đối chiếu lại với văn bản gốc trên vbpl.vn.

---

## Kết quả chính

Bộ câu hỏi 137 câu đã đóng băng, mô hình Gemini, trung bình 3 lần chạy. **Số trong bảng tính trên cả 137 câu:**

| Thước đo | GraphRAG | Naive RAG |
|---|---:|---:|
| **F1 cấp Khoản** | **0.617 ± 0.001** | 0.435 ± 0.008 |
| F1 cấp Điều | 0.638 ± 0.002 | 0.459 ± 0.008 |
| Norm Recall | 0.829 ± 0.005 | 0.588 ± 0.005 |

Chênh lệch ghép cặp theo từng câu — cơ sở tính khác bảng trên, chỉ gồm **123 câu** có đáp án tham chiếu (137 − 14 câu bẫy phủ định): **Δ +0.187**, khoảng tin cậy 95% **[0.108, 0.264]**, Wilcoxon **p = 0.00003**, thắng/thua/hòa 67/32/24 → có ý nghĩa thống kê. *(bootstrap 10000 lần lấy mẫu lại, seed cố định)*. Ý nghĩa thống kê chỉ tồn tại ở cơ sở ghép cặp này.

Bậc thang hệ tham chiếu (F1 cấp Khoản, 137 câu): gold-context 0.858 > **graphrag 0.617** > bm25 0.571 > naive RAG 0.435 > llm-only 0.043.

**Ablation phân ly kép.** Bước duyệt đồ thị cần thiết cho thách thức đa tầng và đa phiên bản (gỡ bước duyệt: −0.101 / −0.122), bộ lọc lĩnh vực cần thiết cho thách thức đa lĩnh vực (−0.039) và không gây gánh nặng cho ba thách thức còn lại. Hai bộ lọc cứng theo địa phương và theo thời gian **chưa** chứng minh được đóng góp riêng — khi bị cô lập, chúng làm tăng điểm ở chính thách thức của mình (+0.050 và +0.045); đây là kết quả phủ định và được báo cáo nguyên trạng.

**Tính trung thực của trích dẫn.** Tỉ lệ tồn tại 295/296 = 99.7% (kiểm tra tất định, không gọi mô hình, đo khi verifier đang **tắt**); tỉ lệ được hậu thuẫn 260/295 = 88.1%. Giám khảo là `gemini-2.5-pro`, **trùng mô hình sinh**, nên con số 88.1% chịu rủi ro thiên lệch tự-đánh-giá và chỉ nên đọc như chỉ báo tương đối; đo lại bằng giám khảo độc lập là việc chưa làm.

**Nút thắt nằm ở khâu sinh, không phải khâu truy hồi.** Trong 32 câu thua Naive RAG, 26 câu có đủ văn bản đúng trong ngữ cảnh nhưng mô hình vẫn dẫn sai hoặc bỏ sót.

**Đánh giá của người dùng** (25 câu, chấm mù, 2 nhóm) cho kết quả hai chiều: chuyên gia pháp lý chấm GraphRAG cao hơn (đúng luật 4.53 vs 4.11), người dùng phổ thông chấm **thấp hơn** (dễ hiểu 3.96 vs 4.16, hữu ích 3.87 vs 4.23) vì câu trả lời dày trích dẫn và cảnh báo hiệu lực.

**Độ vững khi đổi mô hình sinh.** Giữ nguyên ngữ cảnh, chỉ thay mô hình sinh: ưu thế của kiến trúc giữ dấu dương ở cả mô hình thương mại lẫn mô hình 4B chạy cục bộ (ΔF1 +0.182 / +0.101 / +0.272).

Toàn bộ số liệu chốt: [`docs/V3_RESULTS.md`](docs/V3_RESULTS.md). [`docs/V2_RESULTS.md`](docs/V2_RESULTS.md) là bộ số trước khi sửa lỗi phân loại địa phương, chỉ còn giá trị lịch sử.

---

## Yêu cầu môi trường

**Đường chạy chính (API)** — đủ để tái lập mọi số liệu ở trên:

- Python 3.10 trở lên (đã kiểm thử trên 3.12)
- Docker + Docker Compose v2
- RAM tối thiểu 8 GB, dung lượng trống khoảng 5 GB; không cần GPU
- Khóa mô hình ngôn ngữ: Anthropic Claude và/hoặc Google Gemini

**Đường chạy tinh chỉnh cục bộ (tùy chọn)** — chỉ cần khi tái lập ma trận đổi mô hình sinh: GPU NVIDIA ≥ 24 GB VRAM hỗ trợ bf16 (thực nghiệm chạy trên RTX 4090), CUDA 12.8, Torch 2.10 + Transformers 5.5 + Unsloth + PEFT. Chi tiết ở [`finetune/README.md`](finetune/README.md).

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

Kết quả mong đợi: `=== Result: 2/2 PASSED ===` (Neo4j PASS, Qdrant PASS).

---

## Nạp dữ liệu

Chạy lần lượt. Cả hai đều idempotent (dùng `MERGE` và `upsert`) nên chạy lại nhiều lần vẫn cho cùng một kết quả.

```bash
python -m src.ingestion.graph_builder    # dựng đồ thị tri thức trong Neo4j
python -m src.ingestion.vectorizer       # nạp vector vào Qdrant
```

**Lưu ý trước khi chạy:**

- `graph_builder` có bước ánh xạ ontology bằng mô hình ngôn ngữ (Pass 4) nên cần khóa API và mất vài phút. Kết quả mong đợi trên kho 32 văn bản: **4549 Component, 4551 CTV, 323 Amendment**.
- `vectorizer` tải mô hình nhúng BGE-M3 (khoảng 2 GB) trong lần chạy đầu. Đây là bước tải qua mạng, không phải treo máy. Qdrant giữ **chỉ mục kép**: vector `text_unit` (tìm nội dung, kèm trường lọc cứng) và vector `summary` (định tuyến văn bản ở Giai đoạn 1).

**Thêm một văn bản mới vào `data/raw/`:** mỗi tệp Markdown gồm khối metadata YAML ở đầu và nội dung tổ chức bằng heading, trong đó (1) cấp heading ánh xạ cố định vào cấp đơn vị pháp lý — parser suy toàn bộ cây cấu trúc chỉ từ đó; (2) trường `summary` do người viết, là căn cứ **duy nhất** cho bước định tuyến Giai đoạn 1; (3) mỗi ghi chú sửa đổi thành một chú thích HTML đặt ngay dưới điều khoản bị tác động: `<!-- amended_by: [số hiệu VB sửa], [vị trí sửa], hiệu lực: [dd/mm/yyyy], nội dung: [tóm tắt] -->`. Khái niệm nghiệp vụ mới thì khai báo thêm vào `data/ontology/core_v1.json`.

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

**Giao diện web demo:**

```bash
python -m ui.server        # rồi mở http://localhost:8000
```

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

| Cờ | Ý nghĩa |
|---|---|
| `--systems` | `graphrag`, `baseline` (Naive RAG), `bm25`, `closed-book` (LLM-Only), `oracle` (Gold-Context) |
| `--faithfulness-tier 1` | Chỉ đo tỉ lệ tồn tại — đối chiếu tất định, không gọi mô hình |
| `--faithfulness-tier 2` | Đo thêm tỉ lệ hậu thuẫn — LLM-as-a-judge, tốn thêm lượt gọi API |
| `--verify` / `--verify-tier` | Bật tầng kiểm chứng trích dẫn. **Mặc định tắt** — mọi số liệu công bố đo khi tắt |
| `--no-llm-cache` | Tắt bộ nhớ đệm lời gọi mô hình; bắt buộc khi đo tính tái lập N=3 |
| `--limit N` | Chạy nhanh N câu đầu để kiểm tra pipeline |
| `--ablation <tên>` | Chạy biến thể ablation, xem bảng dưới |

Ma trận phân ly kép — chạy lần lượt từng giá trị `--ablation`, tên ablation được gắn vào tên tệp kết quả:

| `--ablation` | Điểm cắt |
|---|---|
| `no-theme` | Giai đoạn 1: bỏ lọc trước theo `theme` |
| `no-jurisdiction` | Giai đoạn 2: bỏ hard-filter `APPLIES_TO` |
| `no-implements` / `no-amends` | Giai đoạn 2: duyệt chỉ còn một trong hai quan hệ |
| `no-temporal` | Giai đoạn 2: tắt lọc CTV theo `valid_from`/`valid_to` |
| `no-traversal` | Giai đoạn 2: chỉ giữ văn bản hạt giống, không mở rộng |
| `dense-only` | Bỏ toàn bộ mở rộng đồ thị và graph-boost |
| `graphrag-basic` | Giữ ba giai đoạn, tắt đồng thời ba bộ lọc do ontology dẫn dắt |

Tổng hợp ma trận và các phân tích sau khi chạy (không gọi mô hình):

```bash
python -m src.evaluation.build_ablation_matrix          # ma trận phân ly kép
python -m src.evaluation.expanded_eval \
       --graphrag data/evaluation/results_graphrag_<thời điểm>.json \
       --baseline data/evaluation/results_baseline_<thời điểm>.json   # CI + Wilcoxon
python -m src.evaluation.error_analysis                 # phân loại 3 loại lỗi trích dẫn
python -m src.evaluation.compare_runs run_A.json run_B.json
python -m src.evaluation.build_review_sheet             # phiếu chấm mù cho đánh giá người dùng
```

Tệp kết quả sinh ra trong `data/evaluation/`:

- `results_<hệ>[_<ablation>]_<thời điểm>.json` — chi tiết từng câu, **kèm nguyên văn chuỗi ngữ cảnh** mà mô hình sinh đã nhận (đây là đầu vào cho `finetune/replay.py`)
- `metrics_summary_<thời điểm>.md` — bảng tổng hợp
- `REPORT_<thời điểm>.md` — báo cáo dễ đọc theo từng câu, kèm khối `run_config` ghi lại các cờ đã chạy

> Số liệu ở mục Kết quả chính đo với `--llm-mode gemini`. Đổi mô hình thì kết quả sẽ khác.

---

## Tinh chỉnh mô hình sinh cục bộ

Nhánh thực nghiệm ở [`finetune/`](finetune/README.md), trả lời câu hỏi: ưu thế đo được thuộc về cơ chế truy hồi hay chỉ là hiện tượng riêng của một mô hình sinh đủ mạnh? Nguyên tắc nền: **đóng băng truy hồi, chỉ đổi mô hình sinh** — `replay.py` đọc lại đúng chuỗi `context` đã lưu trong `results_*.json`, nên không cần Neo4j, Qdrant hay khóa API.

Mô hình: **Qwen3-4B-Instruct-2507**, tinh chỉnh **QLoRA** 4-bit (hạng 16, độ dài chuỗi 16384, 5.000 mẫu, 2 lượt duyệt). F1 cấp Khoản trên 137 câu:

| Mô hình sinh | Naive RAG | GraphRAG | Chênh lệch |
|---|---:|---:|---:|
| Gemini 2.5 Pro | 0.435 | 0.617 | +0.182 |
| Cục bộ đã tinh chỉnh, không ví dụ mẫu | 0.301 | 0.402 | +0.101 |
| Cục bộ gốc, hai ví dụ mẫu | 0.239 | 0.511 | +0.272 |
| Cục bộ gốc, không ví dụ mẫu | 0.154 | 0.131 | −0.022 |

Hai điều cần đọc kèm bảng. Thứ nhất, hàng cuối **không phải bằng chứng phản bác**: ô GraphRAG của hàng đó chỉ đúng định dạng 0.065 (8/123 câu phân tích được) nên thang đo không còn phân giải. Thứ hai, **một kết quả âm**: mô hình đã tinh chỉnh không vượt được mô hình gốc ở cấu hình hai ví dụ mẫu (0.402 so với 0.511) — với bài toán mà nút thắt là định dạng đầu ra, hai ví dụ đặt trong ngữ cảnh là cách dạy cạnh tranh được với tinh chỉnh. Tinh chỉnh vẫn đạt mục tiêu đã đặt ra là dạy định dạng: tỉ lệ câu trả lời phân tích được trên ngữ cảnh GraphRAG tăng ×11.6.

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
│   ├── raw/              ← Kho ngữ liệu đã chuẩn hóa — 32 VBQPPL (.md)
│   │                       + mapping_table.md, crossref_decisions.md, review_log.md
│   ├── ontology/         ← core_v1.json — Core Ontology (khái niệm + thủ tục)
│   ├── sources/          ← manifest.md — truy vết nguồn thu thập
│   ├── evaluation/       ← Bộ câu hỏi, kết quả các lần chạy, báo cáo phân tích
│   ├── verification/     ← phase2_report.md
│   ├── processed/
│   ├── neo4j/            ← Volume Docker (gitignore)
│   └── qdrant/           ← Volume Docker (gitignore)
├── src/
│   ├── ingestion/        ← parser, graph_builder, vectorizer, ontology_mapper
│   ├── retrieval/        ← query_planner, subgraph_extractor, semantic_filter,
│   │                        context_assembler, answer_generator, verifier,
│   │                        ablation_config, reranker
│   ├── baseline/         ← naive_rag, bm25_rag, closed_book
│   ├── evaluation/       ← run_evaluation, metrics, faithfulness, oracle,
│   │                        expanded_eval, error_analysis, human_eval,
│   │                        build_ablation_matrix, build_reproducibility_report,
│   │                        build_review_sheet, report_builder, retrieval_eval,
│   │                        instrument_retrieval, compare_runs, term_validator,
│   │                        validate_test_set, verify_gt
│   ├── utils/            ← llm_config, gemini_fallback, connection_check,
│   │                        validate_metadata, migrate_valid_to_sentinel
│   ├── pipeline.py       ← Điều phối pipeline đầu-cuối
│   ├── demo.py           ← Giao diện dòng lệnh chạy thử
│   └── precache_demo.py  ← Nạp sẵn cache cho demo
├── finetune/             ← Nhánh mô hình sinh cục bộ (xem finetune/README.md)
│   ├── build_dataset.py, slug.py, dataset_report.py      ← dựng 5.000 mẫu
│   ├── train_qlora.py, run.sh, upload_dataset.sh         ← huấn luyện QLoRA
│   ├── replay.py, select_gate_ids.py,
│   │   measure_token_budget.py, recover_response_mode.py ← phát lại và chẩn đoán
│   ├── kaggle_ft06.py, notebooks/                        ← chạy trên Kaggle
│   └── data/ · reports/ · results/ · logs/ · models/
├── ui/                   ← Giao diện demo: server.py, adapters.py, corpus.py,
│                            trace.py, static/, fixtures/
├── tests/                ← Kiểm thử đơn vị (25 tệp test_*.py)
├── notebooks/            ← Notebook kiểm chứng Phase 2, 3, 4 + kaggle_clean
├── docs/                 ← Tài liệu dự án (xem bảng Tài liệu bên dưới)
├── docker-compose.yml    ← Neo4j 5.18 + Qdrant v1.13.6
├── requirements.txt
├── .env.example
└── CLAUDE.md             ← Quy ước, lược đồ, nhật ký quyết định thiết kế
```

---

## Kiến trúc truy hồi ba giai đoạn

Trước cả ba giai đoạn, **bộ lập kế hoạch truy vấn** dùng một mô hình ngôn ngữ nhẹ để trích từ câu hỏi các trường `theme`, `procedure`, `jurisdiction`, `temporal` và `temporal_intent`. Trường nào không gán được thì nới lỏng ràng buộc tương ứng chứ không chặn truy hồi; nếu không nhận diện được lĩnh vực, bộ lập kế hoạch trích số hiệu văn bản bằng biểu thức chính quy rồi tra ngược vào Neo4j.

1. **Định tuyến văn bản** — nhúng câu hỏi, so với vector `summary` của từng văn bản, lọc trước theo `theme`; giữ tối đa 5 văn bản hạt giống vượt ngưỡng tương đồng 0.3.
2. **Duyệt đồ thị và lọc cứng** — mở rộng theo bao đóng dẫn xuất: duyệt vô hướng tối đa 4 bước trên hợp của `IMPLEMENTS` (hướng dẫn thi hành) và `AMENDS` (sửa đổi), rồi lọc cứng theo địa phương và theo khoảng hiệu lực `[valid_from, valid_to]` của CTV.
3. **Tìm kiếm lai** — xếp hạng điều khoản bằng bốn nguồn tín hiệu (trích dẫn có cấu trúc, ngữ nghĩa, từ khóa, đồ thị): ngữ nghĩa và từ khóa hợp nhất bằng RRF, tín hiệu đồ thị vào dưới dạng hệ số nhân, trích dẫn có cấu trúc tách riêng ở mức ưu tiên cao nhất. Điểm hợp nhất được điều biến theo tầng hiệu lực và độ hiếm khái niệm. Chọn tối đa 25 điều khoản, mỗi văn bản góp tối đa 3 đơn vị nội dung.

Mô hình sinh chạy ở nhiệt độ 0. Sau khâu sinh là tầng kiểm chứng trích dẫn (verifier, mặc định tắt): đối chiếu tất định từng trích dẫn với ngữ cảnh đã nạp và loại những trích dẫn không xuất hiện — nó cố tình không tự chấm điểm câu trả lời.

Lược đồ đồ thị: **9 loại nút** (Theme, Norm, Component, CTV, TextUnit, Jurisdiction, Amendment, Concept, Procedure) và **10 loại cạnh**. Chi tiết ở [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

**Hạ tầng:** Neo4j 5.18 · Qdrant 1.13 · BGE-M3 (1024 chiều) · Query Planner = Gemini 2.5 Flash · Generator = Gemini 2.5 Pro · Faithfulness judge = Gemini 2.5 Pro.

---

## Hạn chế đã biết

- **Ưu thế của đồ thị phân bố không đều** — chỉ hơn BM25 0.046 điểm F1 cấp Khoản trên tổng thể. Với câu tra cứu trực tiếp, so khớp từ vựng đã đủ tốt; ưu thế thật sự chỉ bộc lộ ở bài toán đòi hỏi liên kết nhiều văn bản, theo dõi hiệu lực và kỷ luật từ chối.
- **Hai bộ lọc cứng theo địa phương và thời gian chưa chứng minh được đóng góp riêng** — năng lực xử lý hai thách thức này trên thực tế đến từ bộ lập kế hoạch truy vấn và bước duyệt đồ thị.
- **Nút thắt ở khâu sinh** — trích dẫn tồn tại 99.7% nhưng được nội dung hậu thuẫn chỉ 88.1%; sai sót tập trung ở bước diễn giải nguồn.
- **Đánh đổi giữa chặt chẽ và dễ đọc** — câu trả lời giàu trích dẫn chính xác hơn về pháp lý nhưng khó đọc với người dùng phổ thông.
- **Kho ngữ liệu hẹp và phụ thuộc khâu thủ công** — 3 lĩnh vực, 6 thủ tục; trường `summary` và quan hệ `[:REQUIRES_CONCEPT]` do người khai báo. Tỉ lệ thua cũng lệch theo quy mô kho: đất đai 22%, hộ tịch 24%, nuôi con nuôi 36%.
- **Đánh giá người dùng quy mô nhỏ và giám khảo trung thực trùng mô hình sinh** — cả hai chỉ nên đọc như chỉ báo định tính.

---

## Khác biệt với bản nộp

Bản mã nguồn nộp kèm báo cáo được lược bớt cho gọn: chỉ giữ đường chạy **Gemini**, bỏ toàn bộ mã liên quan tới Claude, và vì thế có ít test hơn. Repo này giữ nguyên cả hai nhà cung cấp cùng bốn chế độ `--llm-mode`, nên số test cao hơn.

Kết quả đánh giá của hai bản là **như nhau** vì mọi số liệu công bố đều đo ở chế độ `gemini`.

---

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/V3_RESULTS.md`](docs/V3_RESULTS.md) | **Số liệu chốt** — nguồn cho chương đánh giá |
| [`docs/V2_RESULTS.md`](docs/V2_RESULTS.md) | Bộ số trước khi sửa lỗi phân loại địa phương — chỉ còn giá trị lịch sử |
| [`docs/EVALUATION_ARCHITECTURE.md`](docs/EVALUATION_ARCHITECTURE.md) | Kiến trúc đánh giá 4 khối E0–E3 |
| [`docs/GT_FREEZE.md`](docs/GT_FREEZE.md) | Đăng ký trước bộ câu hỏi vàng (đóng băng, có mã băm) |
| [`docs/GT_AUTHORING_GUIDE.md`](docs/GT_AUTHORING_GUIDE.md) | Quy tắc soạn đáp án tham chiếu |
| [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Kiến trúc hệ thống, lược đồ ontology, hạn chế đã biết |
| [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) | Nhật ký thay đổi và trạng thái công việc |
| [`docs/FINETUNE_EXECUTION_PLAN.md`](docs/FINETUNE_EXECUTION_PLAN.md) | Kế hoạch nhánh tinh chỉnh (FT-00 → FT-07) |
| [`ui/docs/UI_DEMO_SPEC.md`](docs/UI_DEMO_SPEC.md) | Đặc tả giao diện demo |
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
- Chạy đủ 5 hệ × 137 câu với `--no-llm-cache` tốn khá nhiều lượt gọi API; kiểm tra pipeline trước bằng `--limit 3`.
- Kho ngữ liệu trong `data/raw/` là bản chép lại từ nguồn công khai của cơ quan nhà nước, phục vụ mục đích nghiên cứu.

---

## Nhóm thực hiện

Đào Nguyễn Tấn Đạt, Nguyễn Duy Minh Đăng — ngành Khoa học Máy tính.
Giảng viên hướng dẫn: Lê Anh Cường, Khoa Công nghệ thông tin.