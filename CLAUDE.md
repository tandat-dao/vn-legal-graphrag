# CLAUDE.md — Ontology-Driven GraphRAG cho Pháp luật Việt Nam

> **ĐỌC FILE NÀY TRƯỚC KHI LÀM BẤT CỨ ĐIỀU GÌ.**
> Sau đó đọc `docs/PROJECT_STATUS.md` để biết task hiện tại và `docs/PROJECT_CONTEXT.md` để nắm kiến trúc.
> Không viết bất kỳ dòng code nào trước khi đọc xong cả ba file.

---

## NHẬN DẠNG DỰ ÁN

**Tên:** Ontology-Driven GraphRAG cho Pháp luật Việt Nam
**Loại:** Khóa luận tốt nghiệp — 2 thành viên [A] và [B]
**Mục tiêu kỹ thuật:** Xây dựng hệ thống trả lời câu hỏi pháp lý có trích dẫn, kết hợp Knowledge Graph (Neo4j) và Vector Search (Qdrant), giải quyết 3 gap: đa lĩnh vực, đa địa phương, đa tầng văn bản.
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
│   │   ├── specified_in_map.md
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
| D-07 | Xóa Procedure node và edge `[:SPECIFIED_IN]` khỏi schema | Manual mapping không scalable; Theme + Jurisdiction filter + `[:IMPLEMENTS]` traversal đã đủ để routing và chứng minh 3 Gap | 2026-05-10 |
| D-08 | Thêm field `summary` vào frontmatter; Stage 1 retrieval qua summary embedding | Cho phép semantic routing ở cấp Norm mà không cần manual mapping; con người viết đảm bảo độ chính xác pháp lý | 2026-05-10 |

---

## SCHEMA ONTOLOGY — QUICK REFERENCE

### 6 loại Node

| Node | Mô tả | Key properties |
|---|---|---|
| `Theme` | Lĩnh vực pháp lý | `name`: dat-dai \| ho-tich \| nuoi-con-nuoi |
| `Norm` | Văn bản quy phạm pháp luật | `id`, `title`, `tier` (1-4), `valid_from`, `summary` |
| `Component` | Điều/Khoản/Điểm/Tiết (xuyên thời gian) | `id`, `label` |
| `CTV` | Snapshot của Component tại thời điểm | `valid_from`, `valid_to`, `status`, `amended_by` (optional), `added_by` (optional) |
| `TextUnit` | Nội dung văn bản thuần túy | `id` (deterministic), `text` |
| `Jurisdiction` | Địa phương | `name`: toan-quoc \| tp-hcm \| dong-nai |

### 6 loại Edge

| Edge | Từ → Đến | Ý nghĩa |
|---|---|---|
| `[:INCLUDES]` | Theme → Norm | Văn bản thuộc lĩnh vực |
| `[:IMPLEMENTS]` | Norm → Norm | NĐ implements Luật (Gap 3) |
| `[:HAS_COMPONENT]` | Norm → Component | Phân rã cấu trúc |
| `[:HAS_CTV]` | Component → CTV | Quản lý phiên bản |
| `[:HAS_TEXT_UNIT]` | CTV → TextUnit | Nội dung vật lý |
| `[:APPLIES_TO]` | Norm → Jurisdiction | Hard-filter địa phương (Gap 2) |

> **Lưu ý (D-07):** `Procedure` node và `[:SPECIFIED_IN]` đã bị xóa khỏi schema (xem Decision Log D-07). Routing theo thủ tục được thực hiện qua Theme filter + summary-based Stage 1 retrieval. `[:BELONGS_TO]` cũng không implement trong scope này (xem P-03).

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
CONTEXT_MAX_TOKENS = 3000
DEFAULT_TOP_K = 10
```

---

## DEPENDENCIES — CÁC MODULE LIÊN KẾT

```
parser.py          ← đọc data/raw/*.md
                   → trả về List[TextUnit] với Deterministic ID

graph_builder.py   ← nhận TextUnit list từ parser.py
                   ← nhận metadata từ YAML frontmatter (kể cả summary)
                   → write vào Neo4j (MERGE, idempotent)

vectorizer.py      ← đọc TextUnit nodes từ Neo4j
                   ← dùng BGE-M3 để encode
                   → upsert vào Qdrant collection "legal_texts"
                   → ID vector = ID TextUnit trong Neo4j (BẮT BUỘC)

query_planner.py   ← nhận câu hỏi string
                   → trả về QueryPlan TypedDict

subgraph_extractor.py ← nhận QueryPlan
                      ← query Neo4j
                      → trả về LCCIDs (List[str])

semantic_filter.py ← nhận LCCIDs + câu hỏi gốc
                   ← query Qdrant với payload filter
                   → trả về Top-k List[TextUnit]

context_assembler.py ← nhận List[TextUnit]
                     → trả về sorted, capped context string

answer_generator.py  ← nhận context + câu hỏi gốc
                     → trả về {answer: str, citations: List[dict]}
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
| TASK-14 (Integration E2E) | Phase 4 | Notebook `phase3_e2e_test.ipynb` chạy được 12+ câu hỏi |

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
```

**Biến môi trường cần có trong `.env`:**

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=BAAI/bge-m3
LLM_PROVIDER=<openai|anthropic|local>
LLM_MODEL=<model-name>
LLM_API_KEY=<key>
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
- **Không** tự quyết định `[:SPECIFIED_IN]` mapping nếu không chắc — để trống, ghi "cần xác nhận GVHD"
- **Không** implement `[:BELONGS_TO]` — đây là enhancement ngoài scope hiện tại
- **Không** dùng UUID làm ID bất kỳ đâu trong codebase
- **Không** sửa file trong `data/sources/` — đây là raw data bất biến
- **Không** để code chạy mà không có error handling — mọi lỗi kết nối database phải được catch và log rõ ràng
- **Không** hardcode bất kỳ giá trị nào trong danh sách đóng (themes, jurisdictions, tiers) — luôn import từ constants
