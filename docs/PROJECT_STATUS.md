# Ontology-Driven GraphRAG cho Pháp luật Việt Nam — Trạng thái Dự án
**Phiên bản 0.3 | Cập nhật 2026-04-19**

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
> Làm rõ TASK-09: loại bỏ mơ hồ về [:BELONGS_TO] —
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
| Git repository (3 commits, nhánh main) | `.git/` | Implemented |
| Integration smoke test | `src/utils/connection_check.py` | Implemented & Running |
| Project skeleton (cấu trúc thư mục) | `src/`, `tests/`, `data/`, `notebooks/` | Implemented |

### §1.2 Đang thực hiện 🔄

**Phase 0 — hoàn thành một phần:**
- TASK-01: Còn thiếu nhánh `develop` —
  sẽ tạo khi bắt đầu Phase 1 thực sự.

**Phase 1 — chưa bắt đầu:**
- Chưa có file nào trong `data/raw/` hay `data/sources/`.

### §1.3 Chưa bắt đầu 📋

**Hạ tầng & Môi trường**
- Thiết lập Docker (Neo4j + Qdrant)
- Thiết lập Python environment + Git repo
- Kiểm tra kết nối tích hợp

**Phase 1 — Dữ liệu**
- Bảng ánh xạ văn bản (mapping table)
- Thu thập văn bản gốc (PDF/DOCX)
- Docling Pipeline (tự động hóa)
- Điền metadata thủ công + chuẩn hóa .md
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
### TASK-01: Thiết lập Python environment và Git repository 🔄
**Phase:** 0
**Ưu tiên:** Critical
**Ước tính công sức:** S (nửa ngày đến 1 ngày)
**Phụ thuộc vào:** Không có
**Có thể song song với:** TASK-00
**Hoàn thành:** Chưa

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
- [ ] Cả 2 thành viên push được lên nhánh `develop` (nhánh chưa tạo — sẽ tạo khi bắt đầu Phase 1)
- [ ] Branch `main` được bảo vệ (require PR để merge) (chưa verify)

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
Với mỗi thủ tục trong scope dự án, truy ngược toàn bộ chuỗi văn bản pháp lý điều chỉnh nó và lập thành bảng mapping chính thức. Đây là sản phẩm trí tuệ quan trọng nhất của Phase 1 — nếu bảng này sai hoặc thiếu, đồ thị Knowledge Graph sẽ sai quan hệ [:IMPLEMENTS] và [:SPECIFIED_IN] từ gốc.

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
### TASK-04: Thu thập văn bản gốc (Raw Document Collection) 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-03 (bảng mapping phải xong trước)
**Có thể song song với:** TASK-00, TASK-01, TASK-02
**Hoàn thành:** Chưa

#### Mục tiêu
Tải về hoặc copy toàn bộ văn bản pháp lý xác định trong bảng mapping từ các nguồn chính thức. Mỗi văn bản lưu thành một file riêng biệt ở định dạng PDF hoặc DOCX gốc — chưa qua xử lý — để làm đầu vào cho Docling pipeline (TASK-05). Việc lưu bản gốc là bắt buộc để có thể audit sau này.

#### Đầu vào
- `data/raw/mapping_table.md` — danh sách văn bản cần lấy từ TASK-03
- Nguồn: vbpl.vn, cổng dịch vụ công tỉnh TP.HCM, cổng dịch vụ công tỉnh Đồng Nai, thư viện pháp luật

#### Đầu ra
- `data/sources/` — thư mục chứa toàn bộ file gốc, mỗi file đặt tên theo convention:
  ```
  [tier]-[slug-ten-van-ban]-[nam].pdf
  VD: luat-dat-dai-2024.pdf
      nghi-dinh-102-2024-nd-cp.pdf
      quyet-dinh-ban-gia-dat-tp-hcm-2025.pdf
  ```
- `data/sources/manifest.md` — danh sách tất cả file đã tải, kèm URL nguồn, ngày tải, định dạng (PDF có text layer / PDF scan / DOCX), và ghi chú nếu cần OCR

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tất cả văn bản trong `mapping_table.md` đều có file tương ứng trong `data/sources/`
- [ ] `manifest.md` có đủ mục cho mỗi file, trong đó cột "định dạng" được điền rõ ràng
- [ ] File PDF có text layer: mở bằng PDF reader và chọn được text (không phải ảnh)
- [ ] File PDF scan được đánh dấu ⚠️ trong manifest — đây là input cần OCR trong TASK-05
- [ ] Không có file nào được đặt tên theo kiểu `download(1).pdf` hoặc tên tùy tiện
- [ ] Tất cả file được commit vào Git LFS hoặc ghi rõ link download trong manifest (nếu file quá lớn)

#### Ghi chú / Ràng buộc cứng
- Ưu tiên lấy bản DOCX nếu có (ít lỗi OCR hơn PDF)
- Với PDF scan: nếu đánh máy thủ công mất hơn 2 giờ/văn bản, ghi nhận là limitation và tham khảo GVHD
- Lấy bản text từ **nguồn chính thức** (vbpl.vn) — không lấy từ các blog luật hay trang thứ cấp

---
### TASK-05: Xây dựng Docling Pipeline tự động hóa 📋
**Phase:** 1
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-01, TASK-04
**Có thể song song với:** TASK-03 (về thời gian, nhưng cần output của TASK-04)
**Hoàn thành:** Chưa

#### Mục tiêu
Xây dựng pipeline Python tự động hóa việc chuyển đổi từ file PDF/DOCX gốc sang file Markdown có cấu trúc sơ bộ. Pipeline gồm 4 bước nối tiếp: (1) Docling PDF parsing với layout analysis và hierarchy detection, (2) `clean_pdf_text()` loại bỏ boilerplate đặc thù văn bản pháp lý Việt Nam, (3) `article_boundary_split()` bóc tách theo ranh giới từng Điều, (4) `hierarchy_prefix_attach()` gắn Context Path từ DoclingDocument hierarchy. Output là file `.md` sơ bộ — vẫn cần điền metadata thủ công ở TASK-06.

#### Đầu vào
- `data/sources/*.pdf` và `data/sources/*.docx` từ TASK-04
- `data/sources/manifest.md` — để biết file nào cần OCR

#### Đầu ra
- `src/ingestion/docling_pipeline.py` — module chứa 4 hàm:
  - `run_docling(file_path: str) -> DoclingDocument` — chạy Docling, trả về DoclingDocument
  - `clean_pdf_text(doc: DoclingDocument) -> DoclingDocument` — xóa boilerplate: khối "Cộng hòa XHCN Việt Nam", "Nơi nhận:", "TM. ỦY BAN NHÂN DÂN", số trang, running header/footer
  - `article_boundary_split(doc: DoclingDocument) -> list[dict]` — dùng regex pattern `r"^Điều\s+\d+"` trên heading nodes, trả về list dict `{article_id, heading_text, content, context_path}`
  - `hierarchy_prefix_attach(doc: DoclingDocument, article: dict) -> str` — sinh context path string dạng `"[Tên văn bản] > [Chương] > [Điều]"` từ DoclingDocument heading hierarchy
- `src/ingestion/run_pipeline.py` — script CLI: nhận đường dẫn folder, chạy pipeline trên tất cả file, ghi output ra `data/raw/[ten-van-ban]-draft.md`
- `tests/test_docling_pipeline.py` — unit tests dùng 1 file PDF mẫu nhỏ (2-3 Điều)

#### Định nghĩa Hoàn thành (DoD)
- [ ] `python src/ingestion/run_pipeline.py --input data/sources/` chạy không có lỗi trên toàn bộ file text-layer PDF
- [ ] File output `*-draft.md` của mỗi văn bản chứa các heading `## Điều X` đúng với số Điều trong văn bản gốc (verify thủ công 3 văn bản bất kỳ)
- [ ] `clean_pdf_text()` loại bỏ được cụm "Cộng hòa xã hội chủ nghĩa Việt Nam" và "Nơi nhận:" trong 100% file test
- [ ] Context path của Điều đầu tiên trong mỗi file output có dạng `"[Tên văn bản] > Điều X"` — verify thủ công
- [ ] Pipeline xử lý được file PDF scan (có OCR via Docling + Tesseract) cho ít nhất 1 file scan trong dataset
- [ ] Tất cả unit test trong `tests/test_docling_pipeline.py` pass (`pytest tests/test_docling_pipeline.py`)
- [ ] Script không crash khi gặp file DOCX — xử lý được cả 2 định dạng

#### Ghi chú / Ràng buộc cứng
- Docling version phải được pin trong `requirements.txt` (không dùng `docling>=x`)
- `clean_pdf_text()` chỉ xóa boilerplate cấu trúc — **không được** xóa bất kỳ nội dung pháp lý nào
- Nếu Docling không phát hiện được heading "Điều" trong một file → log warning rõ ràng, không im lặng bỏ qua
- OCR qua Tesseract cần `lang='vie'` cho tiếng Việt — thiếu language pack sẽ cho kết quả sai
- File `*-draft.md` output là **trung gian** — không phải file cuối cho Phase 2; người dùng vẫn phải review và điền metadata ở TASK-06

---
### TASK-06: Điền metadata thủ công và chuẩn hóa format .md 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** L (4-5 ngày — công việc pháp lý + kiểm tra)
**Phụ thuộc vào:** TASK-05 (Docling draft output)
**Có thể song song với:** [A] làm Đất đai, [B] làm Hộ tịch + Nuôi con nuôi
**Hoàn thành:** Chưa

#### Mục tiêu
Chuyển đổi các file `*-draft.md` từ Docling thành các file `.md` hoàn chỉnh theo đúng schema kỹ thuật của dự án. Công việc gồm: (1) điền đầy đủ metadata block ở đầu mỗi file, (2) kiểm tra và sửa heading format nếu Docling xử lý sai, (3) lập bảng ánh xạ [:SPECIFIED_IN] — quyết định Điều/Khoản nào thuộc thủ tục nào. Đây là công việc đòi hỏi hiểu biết pháp lý, **không thể tự động hóa hoàn toàn**.

#### Đầu vào
- `data/raw/*-draft.md` từ TASK-05 (Docling pipeline output)
- `data/raw/mapping_table.md` từ TASK-03
- Schema metadata đã thống nhất (xem Ghi chú bên dưới)

#### Đầu ra
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

- `data/raw/specified_in_map.md` — bảng ánh xạ thủ công:
  ```
  | Thủ tục | Component ID (file_id + Điều + Khoản) | Lý do |
  ```

#### Định nghĩa Hoàn thành (DoD)
- [ ] Tất cả file `.md` trong `data/raw/` có metadata block hợp lệ — kiểm tra bằng script Python đọc YAML frontmatter không lỗi
- [ ] Trường `id` là unique trên toàn bộ tập file — kiểm tra bằng script: `assert len(ids) == len(set(ids))`
- [ ] Trường `tier` nhận đúng giá trị: Luật=1, Nghị định=2, Thông tư=3, Quyết định UBND=4 — không có giá trị nào khác
- [ ] Trường `implements` của mỗi Nghị định/Thông tư/Quyết định trỏ đúng `id` của văn bản cha — verify thủ công chuỗi Luật Đất đai 2024 → Nghị định → Thông tư
- [ ] Không có file nào dùng heading level sai (VD: `# Điều` thay vì `## Điều`)
- [ ] `specified_in_map.md` có đủ mapping cho 6 thủ tục, mỗi thủ tục có ít nhất 3 Component được map
- [ ] Ít nhất 1 văn bản trung ương (tier 1-3) + 1 văn bản địa phương (tier 4) cho lĩnh vực Đất đai và Hộ tịch
- [ ] Hai thủ tục Hộ tịch (Đăng ký khai sinh, Cấp bản sao trích lục) có `jurisdiction: "toan-quoc"` và không có file văn bản địa phương kèm theo

#### Ghi chú / Ràng buộc cứng
- **Format `id`:** `[loai-van-ban]-[slug-ten]-[nam]` — VD: `luat-dat-dai-2024`, `nghi-dinh-102-2024-nd-cp`, `quyet-dinh-bang-gia-dat-tp-hcm-2025`
- **Tier mapping cứng:** 1=Luật/Bộ luật, 2=Nghị định/Pháp lệnh, 3=Thông tư/Thông tư liên tịch, 4=Quyết định UBND tỉnh
- **KHÔNG** tự suy đoán `implements` — nếu không chắc văn bản cha là gì, để trống và ghi chú để cross-check
- Cột "Lý do" trong `specified_in_map.md` bắt buộc — ghi rõ tại sao Điều đó thuộc thủ tục đó (để review và audit)

---
### TASK-07: Cross-check chéo Phase 1 📋
**Phase:** 1
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-06 (toàn bộ file .md đã hoàn chỉnh)
**Có thể song song với:** Không — gate task cuối Phase 1
**Hoàn thành:** Chưa

#### Mục tiêu
Người không viết file sẽ review file của người kia. Đây là bước kiểm soát chất lượng bắt buộc trước khi chuyển sang Phase 2. Nếu Phase 2 Parser gặp lỗi format → phải quay lại Phase 1, tốn nhiều thời gian hơn là review kỹ ngay bây giờ.

#### Đầu vào
- Toàn bộ `data/raw/*.md` từ TASK-06
- Script `src/utils/validate_metadata.py` (viết trong TASK-06) để kiểm tra tự động

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
### TASK-08: Structure-aware Parser 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-07 (Phase 1 phải hoàn toàn xong và verified)
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
### TASK-09: Ontology Instantiation — Graph Builder (Neo4j) 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** L (4-5 ngày)
**Phụ thuộc vào:** TASK-08 (Parser phải hoàn thành trước)
**Có thể song song với:** [A] làm Macro Nodes, [B] làm Routing Nodes + Edges
**Hoàn thành:** Chưa

#### Mục tiêu
Đọc AST từ Parser và metadata từ Phase 1, tạo toàn bộ node và cạnh trong Neo4j theo schema Ontology đã định nghĩa (7 loại node, 8 loại edge). Toàn bộ quá trình phải idempotent — chạy lại không tạo duplicate. Cạnh `[:SPECIFIED_IN]` được load từ `specified_in_map.md` (semi-manual mapping từ TASK-06).

#### Đầu vào
- `src/ingestion/parser.py` từ TASK-08
- `data/raw/*.md` toàn bộ
- `data/raw/specified_in_map.md` từ TASK-06
- Neo4j đang chạy (TASK-00)

#### Đầu ra
- `src/ingestion/graph_builder.py` — module với:
  - `upsert_theme(tx, theme_name: str)` — tạo/cập nhật node `:Theme`
  - `upsert_norm(tx, metadata: dict)` — tạo/cập nhật node `:Norm`
  - `upsert_component(tx, component_data: dict)` — tạo/cập nhật node `:Component`
  - `upsert_ctv(tx, ctv_data: dict)` — tạo/cập nhật node `:CTV` với `valid_from`, `valid_to`, `status`
  - `upsert_text_unit(tx, text_unit: TextUnit)` — tạo/cập nhật node `:TextUnit`
  - `upsert_jurisdiction(tx, name: str)` — tạo/cập nhật node `:Jurisdiction`
  - `upsert_procedure(tx, name: str)` — tạo/cập nhật node `:Procedure`
  - `create_edges(tx, ...)` — tạo tất cả 8 loại edge
  - `run_ingestion(data_dir: str)` — hàm orchestrator chạy toàn bộ ingestion

#### Định nghĩa Hoàn thành (DoD)
- [ ] Sau khi chạy `run_ingestion()`, Neo4j Browser hiển thị node của cả 7 loại: Theme, Norm, Component, CTV, TextUnit, Jurisdiction, Procedure
- [ ] Cypher query `MATCH (n:Theme) RETURN n.name` trả về đúng 3 kết quả: "dat-dai", "ho-tich", "nuoi-con-nuoi"
- [ ] Cypher query kiểm tra chain [:IMPLEMENTS]: `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1}) RETURN path LIMIT 5` trả về ít nhất 1 kết quả hợp lệ
- [ ] Cypher query kiểm tra [:APPLIES_TO]: `MATCH (:Norm)-[:APPLIES_TO]->(j:Jurisdiction {name:"tp-hcm"}) RETURN count(*)` trả về số > 0
- [ ] Chạy `run_ingestion()` lần 2 không tăng số lượng node (idempotency) — verify bằng `MATCH (n) RETURN count(n)` trước và sau
- [ ] `MATCH (p:Procedure {name:"dang-ky-khai-sinh"})-[:SPECIFIED_IN]->(c:Component) RETURN c` trả về ít nhất 3 Component

#### Ghi chú / Ràng buộc cứng
- Dùng `MERGE` thay vì `CREATE` cho tất cả node và edge để đảm bảo idempotency
- Điều kiện MERGE cho TextUnit là `id` property (deterministic ID từ Parser)
- `[:BELONGS_TO]` (Component → Theme): **KHÔNG implement trong scope khóa luận này.** Quyết định đã được xác nhận trong P-03 (PROJECT_CONTEXT.md). Ghi nhận là limitation trong báo cáo — không implement dù có thời gian dư.
- Batch write: dùng transaction để upsert từng văn bản thay vì từng node — tránh timeout với dataset lớn

---
### TASK-10: Vector Indexing — Qdrant 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-09 (Graph Builder phải hoàn thành — TextUnit phải có trong Neo4j)
**Có thể song song với:** Không — phụ thuộc TASK-09
**Hoàn thành:** Chưa

#### Mục tiêu
Lấy toàn bộ TextUnit từ Neo4j, encode thành vector bằng model BGE-M3, lưu vào Qdrant kèm metadata payload đầy đủ. ID của vector trong Qdrant phải bằng đúng ID của TextUnit trong Neo4j — đây là cơ chế liên kết giữa hai database. Quá trình phải idempotent (upsert, không insert).

#### Đầu vào
- Neo4j populated với TextUnit nodes (TASK-09)
- Qdrant đang chạy (TASK-00)
- Model BGE-M3 (local hoặc API — cần quyết định trước khi implement, xem Open Questions)

#### Đầu ra
- `src/ingestion/vectorizer.py` — module với:
  - `load_model(model_name: str = "BAAI/bge-m3") -> model` — load BGE-M3
  - `encode_text(model, text: str) -> list[float]` — encode 1 text thành vector
  - `build_payload(text_unit_node: dict) -> dict` — tạo metadata payload từ Neo4j node properties: `{component_id, jurisdiction, tier, theme, procedure, valid_from, valid_to}`
  - `upsert_vectors(qdrant_client, collection_name: str, text_units: list) -> None` — upsert batch
  - `run_vectorization(neo4j_driver, qdrant_client)` — orchestrator

#### Định nghĩa Hoàn thành (DoD)
- [ ] Số vector trong Qdrant collection `legal_texts` = số TextUnit node trong Neo4j — verify bằng `MATCH (t:TextUnit) RETURN count(t)` và Qdrant collection info
- [ ] Mỗi vector trong Qdrant có payload đầy đủ 7 fields: `component_id`, `jurisdiction`, `tier`, `theme`, `procedure`, `valid_from`, `valid_to`
- [ ] Vector của 1 TextUnit bất kỳ có thể được lấy từ Qdrant bằng đúng ID của TextUnit đó trong Neo4j
- [ ] Chạy `run_vectorization()` lần 2 không tăng số lượng vector (idempotency — dùng upsert)
- [ ] Qdrant search thử nghiệm: query `"điều kiện cấp sổ đỏ"` với filter `jurisdiction = "toan-quoc"` trả về ít nhất 1 kết quả liên quan đến Đất đai
- [ ] Thời gian encode toàn bộ dataset < 2 giờ trên máy 8GB RAM (nếu chạy local)

#### Ghi chú / Ràng buộc cứng
- Collection name trong Qdrant: `legal_texts` — cố định, không để tùy ý
- Vector dimension của BGE-M3 là 1024 — phải set đúng khi tạo collection
- Nếu BGE-M3 local quá chậm (> 2 giờ) → switch sang API — ghi nhận quyết định vào PROJECT_CONTEXT.md P-XX
- Upsert theo batch 100 vectors/request — không upsert từng vector một (sẽ timeout)

---
### TASK-11: Verification — Kiểm tra tích hợp Phase 2 📋
**Phase:** 2
**Ưu tiên:** Critical
**Ước tính công sức:** S (1 ngày)
**Phụ thuộc vào:** TASK-09, TASK-10
**Có thể song song với:** Không — gate task cuối Phase 2
**Hoàn thành:** Chưa

#### Mục tiêu
Kiểm tra thủ công và bán tự động rằng graph Neo4j và vector store Qdrant đều chính xác và nhất quán với nhau. Đây là gate task — Phase 3 không được bắt đầu nếu bất kỳ item nào trong DoD chưa pass.

#### Đầu vào
- Neo4j và Qdrant đã populated (TASK-09, TASK-10)
- `notebooks/phase2_verification.ipynb` — tạo mới trong task này

#### Đầu ra
- `notebooks/phase2_verification.ipynb` — notebook chứa tất cả verification queries với kết quả thực tế
- `data/verification/phase2_report.md` — báo cáo verification: số node từng loại, số vector, kết quả 3 query mẫu

#### Định nghĩa Hoàn thành (DoD)
- [ ] `MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC` — kết quả được ghi vào `phase2_report.md`, tất cả 7 loại node đều có count > 0
- [ ] Query `MATCH (p:Procedure)-[:SPECIFIED_IN*1..3]->(c:Component)<-[:HAS_COMPONENT]-(n:Norm) WHERE p.name = "dang-ky-khai-sinh" RETURN DISTINCT n.title` trả về đúng tên văn bản liên quan
- [ ] Query `MATCH path = (:Norm {tier:2})-[:IMPLEMENTS]->(:Norm {tier:1})-[:IMPLEMENTS*0..1]->(:Norm) RETURN path LIMIT 5` trả về chain hợp lệ
- [ ] Số vector Qdrant = số TextUnit Neo4j (so sánh 2 số này và ghi vào report)
- [ ] Vector search `"phí chuyển mục đích sử dụng đất"` với filter `jurisdiction = "tp-hcm"` trả về top-3 kết quả thuộc Đất đai (verify thủ công)
- [ ] Vector search `"đăng ký khai sinh"` với filter `jurisdiction = "toan-quoc"` trả về top-3 kết quả thuộc Hộ tịch (verify thủ công)
- [ ] Báo cáo `phase2_report.md` được ký xác nhận bởi cả 2 thành viên

---

### PHASE 3 — Online Pipeline (Retrieval & Generation)

---
### TASK-12: Query Planner 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-11 (Phase 2 verified)
**Có thể song song với:** TASK-13 (nhánh [A])
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
### TASK-13: Sub-graph Extraction 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-11, TASK-12
**Có thể song song với:** TASK-14 (nhánh song song — TASK-13 dùng Neo4j, TASK-14 dùng Qdrant)
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận QueryPlan từ TASK-12, duyệt đồ thị Neo4j để tìm ra danh sách Component IDs (LCCIDs) liên quan. Đây là bước "lọc cứng" — thu hẹp không gian tìm kiếm từ toàn bộ graph xuống chỉ còn các Component có liên quan đến thủ tục được hỏi, địa phương được hỏi, và khoảng thời gian hợp lệ.

#### Đầu vào
- `QueryPlan` từ TASK-12
- Neo4j driver, database đã populated

#### Đầu ra
- `src/retrieval/subgraph_extractor.py` — module với:
  - `LCCIDs` type alias: `list[str]` (list of Component node IDs)
  - `extract_subgraph(query_plan: QueryPlan, neo4j_driver) -> LCCIDs`
  - Cypher query template được dùng bên trong (document rõ ràng)

#### Định nghĩa Hoàn thành (DoD)
- [ ] `extract_subgraph({procedure: "chuyen-muc-dich-su-dung-dat", jurisdiction: "tp-hcm", temporal: "2024"})` trả về list IDs bao gồm Component của cả Luật Đất đai (tier 1) và Quyết định TP.HCM (tier 4)
- [ ] `extract_subgraph({procedure: "dang-ky-khai-sinh", jurisdiction: "toan-quoc"})` trả về KHÔNG có Component của bất kỳ văn bản địa phương nào (tier 4)
- [ ] `extract_subgraph({procedure: "dang-ky-nuoi-con-nuoi"})` trả về list IDs khác với `extract_subgraph({procedure: "dang-ky-lai-nuoi-con-nuoi"})` — hai thủ tục tương tự phải cho kết quả khác nhau
- [ ] Temporal filter hoạt động: Component thuộc CTV có `valid_to < temporal` không xuất hiện trong kết quả
- [ ] Số lượng LCCIDs không vượt quá 50 (tránh quá rộng gây noise) — nếu vượt, log warning

---
### TASK-14: Semantic Filtering — Hybrid Search 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-11
**Có thể song song với:** TASK-13
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận LCCIDs từ TASK-13 và câu hỏi gốc, thực hiện hybrid search (Dense + Sparse + RRF) trong Qdrant với payload filter để lấy Top-k TextUnit có độ liên quan cao nhất.

#### Đầu vào
- LCCIDs từ TASK-13
- Câu hỏi gốc (string)
- Qdrant client, collection `legal_texts`
- BGE-M3 model (đã load)

#### Đầu ra
- `src/retrieval/semantic_filter.py` — module với:
  - `hybrid_search(question: str, lccids: LCCIDs, qdrant_client, model, top_k: int = 10) -> list[TextUnit]`
  - Cơ chế: Dense search (BGE-M3) + Sparse search (BM25) → RRF fusion
  - Payload filter: `component_id IN lccids AND status = "active"`

#### Định nghĩa Hoàn thành (DoD)
- [ ] `hybrid_search("phí chuyển mục đích sử dụng đất", lccids_tp_hcm)` — top-3 kết quả đều thuộc lĩnh vực Đất đai (verify thủ công)
- [ ] Kết quả không chứa TextUnit của Đồng Nai khi `lccids` chỉ chứa IDs của TP.HCM
- [ ] Hybrid search bắt được "sổ đỏ" khi query `"giấy chứng nhận quyền sử dụng đất"` — Dense search phải khớp ngữ nghĩa
- [ ] Hybrid search bắt được `"Nghị định 102/2024/NĐ-CP"` khi query chứa chính xác số hiệu này — Sparse search phải khớp từ khóa
- [ ] `top_k` parameter hoạt động đúng: `top_k=5` trả về đúng 5 kết quả (hoặc ít hơn nếu không đủ)

---
### TASK-15: Context Assembly và Answer Generation 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-14
**Có thể song song với:** TASK-13 (nhánh [B])
**Hoàn thành:** Chưa

#### Mục tiêu
Nhận Top-k TextUnit từ TASK-14, sắp xếp theo thứ tự phân cấp pháp lý (tier 1 trước, tier 4 sau), cắt tỉa nếu vượt token budget, đưa vào LLM để sinh câu trả lời có trích dẫn bắt buộc.

#### Đầu vào
- Top-k TextUnit với metadata (từ TASK-14)
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
- [ ] `assemble_context()` sắp xếp TextUnit đúng thứ tự: tier 1 luôn trước tier 4
- [ ] `assemble_context()` với `max_tokens=3000` cắt bỏ TextUnit đủ để tổng text < 3000 tokens (verify bằng tokenizer)
- [ ] `generate_answer()` trả về response có chứa ít nhất 1 citation với format `{dieu: "X", khoan: "Y", van_ban: "Z"}`
- [ ] Câu trả lời cho câu hỏi về Đất đai TP.HCM có citation đến đúng Điều trong Luật Đất đai 2024 (verify thủ công)
- [ ] Câu trả lời không chứa thông tin không có trong context (faithfulness — verify thủ công 3 câu hỏi)

---
### TASK-16: Integration — Pipeline End-to-End 📋
**Phase:** 3
**Ưu tiên:** Critical
**Ước tính công sức:** S (1-2 ngày)
**Phụ thuộc vào:** TASK-12, TASK-13, TASK-14, TASK-15
**Có thể song song với:** Không — gate task cuối Phase 3
**Hoàn thành:** Chưa

#### Mục tiêu
Nối toàn bộ 4 module thành một pipeline hoàn chỉnh, chạy thử 12-18 câu hỏi mẫu (2-3 câu/thủ tục). Đây là demo nội bộ trước khi bước vào Phase 4 evaluation.

#### Đầu vào
- Tất cả module từ TASK-12 đến TASK-15

#### Đầu ra
- `src/pipeline.py` — hàm `run_pipeline(question: str) -> dict` nối toàn bộ flow
- `notebooks/phase3_e2e_test.ipynb` — chạy 12-18 câu hỏi, ghi lại câu trả lời và thời gian xử lý

#### Định nghĩa Hoàn thành (DoD)
- [ ] `run_pipeline("Điều kiện để chuyển mục đích sử dụng đất tại TP.HCM là gì?")` trả về câu trả lời có trích dẫn trong < 30 giây
- [ ] Pipeline xử lý được ít nhất 2 câu hỏi cho mỗi trong 6 thủ tục
- [ ] Câu hỏi thiếu Jurisdiction → pipeline dừng và trả về `confirmation_needed: True` với câu hỏi ngược lại
- [ ] Negative test: `"Quy định đăng ký khai sinh tại TP.HCM khác Đồng Nai như thế nào?"` → câu trả lời nêu rõ đây là thủ tục thống nhất toàn quốc, **không** bịa ra sự khác biệt địa phương không tồn tại
- [ ] Kết quả 12-18 câu hỏi được ghi vào notebook với nhận xét đánh giá bằng mắt

---

### PHASE 4 — Đánh giá

---
### TASK-17: Xây dựng bộ câu hỏi đánh giá (Test Set) 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-16 (cần biết pipeline hoạt động ổn định để thiết kế test hợp lý)
**Có thể song song với:** TASK-18
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
### TASK-18: Xây dựng Baseline Naive RAG 📋
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-10 (dùng cùng bộ dữ liệu)
**Có thể song song với:** TASK-17
**Hoàn thành:** Chưa

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
- [ ] `run_baseline_ingestion()` chạy thành công, tạo collection `baseline_legal_texts` trong Qdrant
- [ ] `run_baseline_query(question)` trả về câu trả lời với cùng format output như `run_pipeline(question)`
- [ ] Baseline dùng đúng BGE-M3 và LLM — không được dùng model khác (verify bằng code review)
- [ ] Baseline chạy được trên toàn bộ 30+ câu hỏi trong test set mà không crash

---
### TASK-19: Chạy Evaluation và tính Metrics 📋
**Phase:** 4
**Ưu tiên:** Critical
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-16, TASK-17, TASK-18
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
- [ ] Cả 2 hệ thống đã chạy trên toàn bộ ≥ 30 câu hỏi và lưu kết quả
- [ ] Bảng metrics đầy đủ: Precision@5, Recall@5, MRR, Citation Accuracy cho cả 2 hệ thống
- [ ] Metrics được tính chia theo lĩnh vực (Đất đai, Hộ tịch, Nuôi con nuôi)
- [ ] Correctness và Faithfulness được đánh giá thủ công cho ≥ 10 câu hỏi/hệ thống
- [ ] File kết quả JSON có timestamp và config rõ ràng để reproduce

---
### TASK-20: Phân tích kết quả theo Gap 📋
**Phase:** 4
**Ưu tiên:** High
**Ước tính công sức:** M (2-3 ngày)
**Phụ thuộc vào:** TASK-19
**Có thể song song với:** Không
**Hoàn thành:** Chưa

#### Mục tiêu
Phân tích kết quả từ TASK-19 theo 3 Gap của nghiên cứu, xác định failure cases, rút ra kết luận. Đây là nội dung chính của chương "Kết quả & Thảo luận" trong khóa luận.

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
[TASK-04] Thu thập văn bản               │
     │                                   │
[TASK-05] Docling Pipeline               │
     │                                   │
[TASK-06] Điền Metadata + Chuẩn hóa     │
     │                                   │
[TASK-07] Cross-check ◄──────────────────┘
     │
     ├── [A] [TASK-08] Parser ──────────────────────────────────────┐
     │         │                                                      │
     │    [TASK-09] Graph Builder (Neo4j) ──────────────────────────┤
     │         │                                                      │
     │    [TASK-10] Vector Indexing (Qdrant) ───────────────────────┤
     │                                                               │
     └── [B] Unit tests cho TASK-08 (song song)                     │
                                                                     │
                        [TASK-11] Phase 2 Verification ◄────────────┘
                                     │
              ┌──────────────────────┤
     [A]      │              [B]     │
[TASK-12] Query Planner     [TASK-14] Semantic Filtering
[TASK-13] Sub-graph Extraction
              │                      │
              └──────────────────────┤
                                     │
                        [TASK-15] Context Assembly + Generation
                                     │
                        [TASK-16] Integration E2E ──── Gate Phase 3
                                     │
              ┌──────────────────────┤
[TASK-17] Test Set            [TASK-18] Baseline (song song)
     │                               │
     └──────────────────────────────┤
                                    │
                        [TASK-19] Chạy Evaluation
                                    │
                        [TASK-20] Phân tích theo Gap
```

**Các gate task (KHÔNG được bỏ qua):**
- TASK-02: Gate Phase 0 → Phase 1
- TASK-07: Gate Phase 1 → Phase 2
- TASK-11: Gate Phase 2 → Phase 3
- TASK-16: Gate Phase 3 → Phase 4

---

## 4. Hành động tiếp theo được khuyến nghị

1. ~~Thống nhất các quyết định còn open trong `docs/PROJECT_CONTEXT.md` (đặc biệt: LLM nào, BGE-M3 local hay API, format `id` cuối cùng)~~ ✅
   OQ-04 đã đóng (Claude, 2026-04-19). OQ-01 đã đóng (format id). OQ-03 và OQ-06 vẫn pending.

2. ~~[A] bắt đầu TASK-00, [B] bắt đầu TASK-01 — song song~~ ✅ Hoàn thành (2026-04-19)

3. **(HIỆN TẠI)** Hoàn thành TASK-01 còn thiếu: tạo nhánh `develop` (thực hiện khi bắt đầu Phase 1).

4. **(HIỆN TẠI)** Bắt đầu TASK-03 (Mapping Table) — không cần chờ môi trường, có thể làm ngay.

5. Song song với TASK-03: [A] bắt đầu thu thập văn bản nguồn (TASK-04), [B] setup Docling pipeline (TASK-05) để sẵn sàng khi có file PDF/DOCX.

6. Sau khi TASK-07 pass: tạo nhánh `develop`, [A] viết TASK-08 (Parser), [B] viết unit tests cho Parser — song song.
