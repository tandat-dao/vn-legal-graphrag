# Ontology-Driven GraphRAG cho Pháp luật Việt Nam

Hệ thống trả lời câu hỏi pháp lý hành chính Việt Nam có trích dẫn, kết hợp Knowledge Graph (Neo4j) và Vector Search (Qdrant). Hệ thống xử lý 3 lĩnh vực: **Đất đai**, **Hộ tịch**, và **Nuôi con nuôi** (Hôn nhân & Gia đình), giải quyết 3 gap nghiên cứu: đa lĩnh vực, đa địa phương (TP.HCM & Đồng Nai), và đa tầng văn bản (Luật → Nghị định → Thông tư → Quyết định UBND).

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

## Kiểm tra kết nối

Sau khi Docker đã chạy và Python dependencies đã cài, chạy script kiểm tra kết nối:

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
│   ├── evaluation/       ← Phase 4: bộ câu hỏi test và kết quả đánh giá
│   ├── neo4j/            ← Docker volume cho Neo4j (gitignored)
│   └── qdrant/           ← Docker volume cho Qdrant (gitignored)
├── src/
│   ├── ingestion/        ← Phase 2: parser, graph builder, vectorizer
│   ├── retrieval/        ← Phase 3: query planner, sub-graph, semantic filter
│   ├── baseline/         ← Phase 4: hệ thống Naive RAG baseline
│   ├── evaluation/       ← Phase 4: tính toán metrics
│   └── utils/            ← Tiện ích dùng chung (kiểm tra kết nối, validate metadata)
├── tests/                ← Unit tests
├── notebooks/            ← Jupyter notebooks cho exploration và verification
├── docs/                 ← Tài liệu dự án (PROJECT_CONTEXT, PROJECT_STATUS)
├── docker-compose.yml    ← Định nghĩa Docker services (Neo4j + Qdrant)
├── .env.example          ← Template biến môi trường
├── requirements.txt      ← Python dependencies
├── .gitignore            ← Danh sách file/thư mục không theo dõi bởi Git
├── CLAUDE.md             ← Quy tắc và conventions cho AI assistant
└── README.md             ← File này
```

---

## Tài liệu dự án

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) — Kiến trúc hệ thống, schema Ontology, tech stack, quyết định thiết kế
- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Trạng thái 21 task cards với Definition of Done
- [`CLAUDE.md`](CLAUDE.md) — Conventions, rules, schema quick reference
