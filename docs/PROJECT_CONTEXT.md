> Tài liệu này chứa tầm nhìn dự án, kiến trúc hệ thống, quyết định thiết kế, tech stack, và lộ trình tính năng.
> Tài liệu thay đổi **hiếm khi** — chỉ khi kiến trúc thay đổi hoặc có quyết định thiết kế mới.
> Để theo dõi tiến độ task, DoD checklist, và hành động tiếp theo, xem `PROJECT_STATUS.md`.

# Ontology-Driven GraphRAG cho Pháp luật Việt Nam — Kiến trúc & Ngữ cảnh Hệ thống
**Phiên bản 0.4 | Cập nhật 2026-05-10**

> **v0.4 — Cập nhật 2026-05-10:**
> Xóa node `Procedure` và edge `[:SPECIFIED_IN]` khỏi schema ontology (D-07).
> Thêm field `summary` vào frontmatter và Norm node; bổ sung Stage 1 retrieval
> qua summary embedding trước Stage 2 TextUnit search (D-08).
> Cập nhật §2.2, §2.3, §2.4, §2.5, §2.6 và P-05 tương ứng.

> **v0.3 — Cập nhật 2026-04-27:**
> Thay đổi chiến lược thu thập dữ liệu Phase 1: bỏ Docling/OCR pipeline,
> chuyển sang thu thập thủ công từ VBHN/vbpl.vn theo Chương/Mục.
> Cập nhật Tier mapping: tier 1 bổ sung NQ Quốc hội, tier 4 bổ sung NQ HĐND tỉnh.
> Bổ sung thuộc tính CTV: amended_by, added_by.
> Bổ sung metadata fields: source_vbhn, amended_by.
> Cập nhật Tech Stack, Lộ trình tính năng Phase 1, và §2.3 Data Flow.
> Xóa P-04 (Docling OCR accuracy) — không còn liên quan.
> Ghi nhận 6 quyết định thiết kế D-01 đến D-06 (xem CLAUDE.md Decision Log).

> **v0.2 — Cập nhật sau audit 2026-04-19:**
> Đóng OQ-04: xác nhận dùng Claude (Anthropic) làm LLM
> provider cho cả Query Planner và Answer Generator.
> Query Planner dùng claude-haiku-4-5-20251001 để tối ưu
> token; Answer Generator dùng claude-sonnet-4-6 cho output
> chất lượng cao. Cập nhật Tech Stack Section 3 tương ứng.
> Làm rõ INCONSISTENCY-02: [:BELONGS_TO] KHÔNG implement
> trong scope khóa luận — TASK-07 được cập nhật để phản
> ánh quyết định dứt khoát này (xem PROJECT_STATUS.md v0.2).

> **v0.1 — Khởi tạo tài liệu (2026-04-18):**
> Tạo PROJECT_CONTEXT.md lần đầu từ `Thesis_Dashboard.docx` và `plan.md`.
> Định nghĩa kiến trúc tổng thể, schema Ontology, tech stack dự kiến.
> Docling được bổ sung vào kiến trúc Phase 1 (quyết định trong buổi thảo luận 2025-04-18).
> Mở 6 câu hỏi thiết kế chưa được giải quyết (xem Section 5).

---

## Mục lục
1. [Tầm nhìn hệ thống](#1-tầm-nhìn-hệ-thống)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Tech Stack](#3-tech-stack)
4. [Lộ trình tính năng](#4-lộ-trình-tính-năng)
5. [Câu hỏi mở & Blockers](#5-câu-hỏi-mở--blockers)
6. [Vấn đề đã biết & Quyết định kiến trúc](#6-vấn-đề-đã-biết--quyết-định-kiến-trúc)

---

## 1. Tầm nhìn hệ thống

Hệ thống giải quyết bài toán trả lời câu hỏi pháp lý hành chính tại Việt Nam — cụ thể là các thủ tục hành chính thuộc lĩnh vực Đất đai, Hộ tịch, và Hôn nhân & Gia đình (Nuôi con nuôi). Người dùng mục tiêu là công dân hoặc cán bộ hành chính cần tra cứu nội dung quy định pháp luật liên quan đến một thủ tục cụ thể tại một địa phương cụ thể.

Điểm khác biệt của hệ thống so với RAG thông thường nằm ở ba khả năng: (1) duy trì tính ổn định khi xử lý đồng thời nhiều lĩnh vực pháp lý có cấu trúc từ vựng và điều khoản hoàn toàn khác nhau; (2) phân biệt và định tuyến chính xác đến văn bản quy định của từng địa phương mà không nhầm lẫn giữa các quy định có nội dung gần giống nhau; (3) tổng hợp thông tin từ chuỗi văn bản đa tầng (Luật → Nghị định → Thông tư → Quyết định UBND) để cho ra câu trả lời đầy đủ.

Mọi câu trả lời đều đi kèm trích dẫn bắt buộc đến Điều, Khoản, và Văn bản cụ thể — đảm bảo người dùng có thể kiểm chứng nguồn gốc thông tin và không bị mislead bởi hallucination.

### Đóng góp khoa học

Khóa luận kiểm chứng khả năng của kiến trúc Ontology-Driven GraphRAG trong việc giải quyết đồng thời 3 gap chưa được xử lý trong các công trình hiện tại:

- **Gap 1 — Đa lĩnh vực:** Chứng minh một kiến trúc KG + RAG duy nhất có thể duy trì độ chính xác ổn định khi xử lý các lĩnh vực pháp luật có cấu trúc điều khoản và từ vựng chuyên ngành dị cấu trúc (Đất đai vs. Hộ tịch vs. HN&GĐ).
- **Gap 2 — Đa địa phương:** Chứng minh graph routing qua `[:APPLIES_TO]` và Jurisdiction nodes ngăn chặn được tình trạng retrieval nhầm lẫn giữa quy định của 2 địa phương có ngữ nghĩa gần giống nhau (TP.HCM vs. Đồng Nai).
- **Gap 3 — Đa tầng:** Chứng minh quan hệ `[:IMPLEMENTS]` giúp tăng Recall trên các câu hỏi đòi hỏi tổng hợp từ nhiều tầng văn bản mà flat RAG không thu thập được.

Thang đo: so sánh GraphRAG với Baseline Naive RAG (chunking cố định 512 tokens, vector search thuần) trên cùng bộ dữ liệu, cùng LLM, cùng embedding model.

### Phạm vi hiện tại

**Trong scope:**
- 3 lĩnh vực: Đất đai, Hộ tịch (Hành chính), Nuôi con nuôi (HN&GĐ)
- 6 thủ tục: Chuyển mục đích sử dụng đất; Cấp sổ đỏ lần đầu (giới hạn Điều 137 LĐĐ 2024); Đăng ký khai sinh; Cấp bản sao trích lục hộ tịch; Đăng ký nuôi con nuôi trong nước; Đăng ký lại nuôi con nuôi trong nước
- 2 địa phương: TP.HCM và Đồng Nai
- Văn bản đã được số hóa và làm sạch (pre-processed)

**Ngoài scope:**
- OCR / Data Extraction từ ảnh hoặc PDF scan — dữ liệu được lấy từ VBHN/vbpl.vn dạng text, không xử lý tài liệu scan
- Đánh giá trên toàn bộ hệ thống pháp luật Việt Nam (không mở rộng ngoài 6 thủ tục)
- Suy luận pháp lý nội hàm (legal reasoning) — hệ thống tìm và trình bày thông tin, không giải quyết tranh chấp pháp lý
- Giao diện người dùng đồ họa (UI) — scope khóa luận dừng ở pipeline và đánh giá

---

## 2. Kiến trúc hệ thống

### §2.1 Sơ đồ tổng thể các tầng hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                    OFFLINE PIPELINE (Data Ingestion)             │
│                                                                   │
│  Thu thập thủ công từ VBHN / vbpl.vn                             │
│  (dichvucong.gov.vn → danh sách văn bản → VBHN → copy nội dung) │
│      │                                                            │
│      ▼                                                            │
│  [Chuẩn hóa heading + Điền metadata YAML frontmatter]           │
│  (tier, jurisdiction, implements, source_vbhn, amended_by_norms, ...)  │
│                                        │                          │
│                                        ▼                          │
│                               [data/raw/*.md]                    │
│                                        │                          │
│                          ┌─────────────┤                          │
│                          │             │                          │
│                          ▼             ▼                          │
│              [Structure-aware    [Metadata từ                     │
│               Parser → AST]      YAML frontmatter]               │
│                          │             │                          │
│                          └──────┬──────┘                          │
│                                 │                                  │
│                                 ▼                                  │
│                    [Ontology Instantiation]                        │
│                                 │                                  │
│                    ┌────────────┴────────────┐                    │
│                    ▼                         ▼                    │
│             [Neo4j Graph]             [BGE-M3 Encode]             │
│          (Nodes + Edges)                    │                     │
│          port: 7687                         ▼                     │
│                                    [Qdrant Vectors]               │
│                                  + Metadata Payload               │
│                                    port: 6333                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    ONLINE PIPELINE (Retrieval & Generation)       │
│                                                                   │
│  Câu hỏi người dùng (tiếng Việt)                                 │
│      │                                                            │
│      ▼                                                            │
│  [Query Planner / LLM]                                           │
│  Extract: Theme, Procedure, Jurisdiction, Temporal               │
│  → Nếu thiếu: Confirmation Loop                                  │
│      │                                                            │
│      ▼                                                            │
│  [Sub-graph Extraction] ──► Neo4j Graph Traversal                │
│  Output: LCCIDs (List of Candidate Component IDs)               │
│      │                                                            │
│      ▼                                                            │
│  [Semantic Filtering] ──► Qdrant Hybrid Search                   │
│  Dense (BGE-M3) + Sparse (BM25) → RRF Fusion                    │
│  Filter: component_id IN LCCIDs, CTV status = active            │
│  Output: Top-k TextUnit                                           │
│      │                                                            │
│      ▼                                                            │
│  [Context Assembly]                                               │
│  Sort by tier (1→4), Token Budget Cap (3000 tokens)             │
│      │                                                            │
│      ▼                                                            │
│  [Answer Generator / LLM]                                        │
│  Prompt: context + question + citation requirement               │
│  Output: Câu trả lời + Citations {Điều, Khoản, Văn bản}         │
└─────────────────────────────────────────────────────────────────┘
```

### §2.2 Schema Ontology (Graph Model)

```
                    ┌──────────┐
                    │  Theme   │ (dat-dai | ho-tich | nuoi-con-nuoi)
                    └────┬─────┘
                         │ [:INCLUDES]
                         ▼
                    ┌──────────────────────────┐
                    │   Norm                   │
                    │   tier: 1-4, valid_from  │
                    │   title, summary         │
                    └────┬─────────────────────┘
          [:IMPLEMENTS]  │  [:HAS_COMPONENT]   [:APPLIES_TO]
          (Norm→Norm)    │       │                  │
          ┌─────────────┘       ▼                  ▼
          │              ┌──────────┐        ┌────────────┐
          │              │Component │        │Jurisdiction│
          │              └────┬─────┘        └────────────┘
          │                   │ [:HAS_CTV]   (tp-hcm | dong-nai
          │                   │              | toan-quoc)
          │                   ▼
          │              ┌──────────┐
          │              │   CTV    │ valid_from, valid_to, status
          │              └────┬─────┘
          │                   │ [:HAS_TEXT_UNIT]
          │                   ▼
          │              ┌──────────┐
          └─────────────►│TextUnit  │ id (deterministic), text
                         └──────────┘
```

> **D-07:** Node `Procedure` và edge `[:SPECIFIED_IN]` đã bị xóa. Routing theo thủ tục được thực hiện qua Theme filter + summary-based Stage 1 retrieval (xem §2.6). `[:BELONGS_TO]` cũng không implement trong scope này (xem P-03).

**Bảng Edge (6 loại active):**

| Edge | Từ | Đến | Vai trò chiến lược |
|---|---|---|---|
| `[:INCLUDES]` | Theme | Norm | Phân nhóm văn bản theo lĩnh vực |
| `[:IMPLEMENTS]` | Norm | Norm | **Xương sống Gap 3** — duyệt chuỗi Luật→NĐ→TT→QĐ |
| `[:HAS_COMPONENT]` | Norm | Component | Phân rã văn bản thành đơn vị cấu trúc |
| `[:HAS_CTV]` | Component | CTV | Quản lý phiên bản theo thời gian |
| `[:HAS_TEXT_UNIT]` | CTV | TextUnit | Liên kết phiên bản trừu tượng → nội dung vật lý |
| `[:APPLIES_TO]` | Norm | Jurisdiction | **Xương sống Gap 2** — hard-filter theo địa phương |

### §2.3 Data Flow — Phase 1 Thu thập thủ công

```
[Bước 1] Xác định thủ tục trên dichvucong.gov.vn
  → Lấy danh sách văn bản liên quan cho từng thủ tục
  │
  ▼
[Bước 2] Tìm Văn bản hợp nhất (VBHN) trên vbpl.vn
  → Nếu có VBHN: dùng làm nguồn nội dung (giải quyết chồng chéo NĐ sửa đổi)
  → Nếu không có VBHN: lấy trực tiếp từ văn bản gốc
  │
  ▼
[Bước 3] Xác định phạm vi lấy theo Chương/Mục
  → Chương không có Mục: có ≥1 điều liên quan → lấy cả Chương
  → Chương có Mục: có ≥1 điều liên quan → lấy cả Mục chứa điều đó
  │
  ▼
[Bước 4] Copy nội dung + chuẩn hóa heading format
  → ## Điều X. [Tên điều]
  → ### Khoản 1.
  → #### Điểm a.
  │
  ▼
[Bước 5] Điền metadata YAML frontmatter
  → id, tier, theme, jurisdiction, implements, valid_from, valid_to
  → source_vbhn (nếu dùng VBHN), amended_by_norms (nếu file chứa điều khoản đã bị sửa)
  → Viết `summary` (3-5 câu mô tả phạm vi văn bản — con người viết)
  │
  ▼
[Output] data/raw/*.md ← Input cho Phase 2
```

**Lưu ý VBHN:** `source_vbhn` chỉ ghi nhận nguồn lấy nội dung. Metadata `id`, `tier`, `implements` vẫn theo văn bản QPPL chính thức (Luật, NĐ, TT gốc), không phải số hiệu VBHN.

### §2.4 Schema File `.md` chuẩn (Phase 1 Output)

```yaml
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
amended_by_norms: null   # list id văn bản sửa đổi nếu file chứa điều khoản đã bị sửa, VD: ["nghi-dinh-07-2025-nd-cp"]
summary: null            # 3-5 câu mô tả phạm vi văn bản (thủ tục, đối tượng, địa phương) — do con người viết
---

## Điều 116. [Tên điều]
Nội dung phần mở đầu của Điều (nếu có).

### Khoản 1.
Nội dung khoản 1.

#### Điểm a.
Nội dung điểm a.
```

**Quy tắc bất biến của metadata:**

| Trường | Type | Ràng buộc |
|---|---|---|
| `id` | string | Unique trên toàn bộ tập file. Format: `[loai-vb]-[slug]-[nam]`. VD: `luat-dat-dai-2024`, `nghi-dinh-102-2024-nd-cp`, `quyet-dinh-bang-gia-dat-tp-hcm-2025` |
| `tier` | int | Chỉ nhận 1 trong 4 giá trị: 1=Luật/Bộ luật/NQ Quốc hội, 2=Nghị định/Pháp lệnh, 3=Thông tư/Thông tư liên tịch, 4=Quyết định UBND tỉnh/NQ HĐND tỉnh |
| `theme` | string | Chỉ nhận: `dat-dai`, `ho-tich`, `nuoi-con-nuoi` |
| `jurisdiction` | string | Chỉ nhận: `toan-quoc`, `tp-hcm`, `dong-nai` |
| `implements` | string\|null | Phải trỏ đúng `id` tồn tại trong tập file. null nếu là Luật gốc |
| `valid_from` | string | Format `YYYY-MM-DD` bắt buộc |
| `valid_to` | string\|null | Format `YYYY-MM-DD` hoặc `null` nếu vẫn còn hiệu lực |
| `source_vbhn` | string\|null | **Optional.** Số hiệu VBHN dùng làm nguồn nội dung, VD: `"44/VBHN-VPQH"`. null nếu lấy từ văn bản gốc |
| `amended_by_norms` | list\|null | **Optional.** List `id` các văn bản sửa đổi nếu file chứa điều khoản đã bị sửa. null nếu không |
| `summary` | string\|null | **Bắt buộc điền.** 3-5 câu mô tả phạm vi văn bản: thủ tục điều chỉnh, đối tượng áp dụng, địa phương. Do con người viết để đảm bảo độ chính xác pháp lý. Dùng cho Stage 1 retrieval (xem D-08) |

### §2.5 Data Flow — Dual Indexing (Phase 2)

```
data/raw/*.md
  │
  ├──[Structure-aware Parser]──►  AST (in memory)
  │    Regex heading detection        │
  │    Stack-based state mgmt         │ TextUnit list
  │    Deterministic ID: SHA256       │ + Context Path
  │    (context_path joined)          │
  │                                   ▼
  └──[YAML frontmatter]──►  [Ontology Instantiation]
       metadata: id, tier,                │
       theme, jurisdiction,               ├──► Neo4j (port 7687)
       implements, valid_from,            │    Nodes: 7 loại
       valid_to                           │    Edges: 8 loại
                                          │    Upsert (MERGE)
                                          │
                                          └──► Qdrant (port 6333)
                                               Collection: legal_texts
                                               Vector dim: 1024 (BGE-M3)
                                               2 loại vector:
                                               • content_type="summary": 1 vector/Norm
                                                 Payload: norm_id, tier, theme,
                                                          jurisdiction, valid_from
                                               • content_type="text_unit": 1 vector/TextUnit
                                                 Payload: norm_id, component_id,
                                                          tier, theme, jurisdiction,
                                                          valid_from, valid_to
                                               ID: = TextUnit ID Neo4j (cho text_unit)
```

### §2.6 Data Flow — Online Retrieval (Phase 3)

```
Câu hỏi: "Phí chuyển mục đích sử dụng đất tại TP.HCM?"

[Query Planner — LLM]
  Extract: theme=dat-dai, procedure=chuyen-muc-dich-su-dung-dat,
           jurisdiction=tp-hcm, temporal=hiện tại
  is_complete=True → tiếp tục

[Stage 1 — Summary Retrieval — Qdrant]
  Filter: content_type="summary", theme="dat-dai",
          jurisdiction IN ["tp-hcm", "toan-quoc"]
  Dense: BGE-M3 encode(câu hỏi) → so sánh với summary vectors
  Output: Top-N norm_ids có summary liên quan nhất
          VD: ["luat-dat-dai-2024", "nghi-dinh-102-2024-nd-cp",
               "nghi-quyet-87-2025-nq-hdnd-tp-hcm", ...]

[Stage 2 — Sub-graph Extraction — Neo4j]
  Cypher: START FROM Norm IDs từ Stage 1
          FOLLOW [:IMPLEMENTS] chains (all tiers)
          FILTER: Norm [:APPLIES_TO] Jurisdiction("tp-hcm") OR "toan-quoc"
          FILTER: CTV.valid_from <= now, CTV.valid_to IS NULL OR > now
          COLLECT all Component IDs
  Output: LCCIDs = [comp_001, comp_002, comp_045, comp_089, ...]

[Semantic Filtering — Qdrant Hybrid]
  Payload filter: content_type="text_unit", norm_id IN norm_ids
  Dense: BGE-M3 encode("Phí chuyển mục đích sử dụng đất tại TP.HCM?")
  Sparse: BM25 tokenize
  Fusion: RRF(dense_scores, sparse_scores)
  Output: Top-10 TextUnit

[Context Assembly]
  Sort: tier 1 → tier 4
  Cap: max 3000 tokens
  Output: Ordered context string

[Answer Generator — LLM]
  Prompt: [System: bắt buộc trích dẫn] + [Context] + [Question]
  Output: {
    answer: "Theo Điều X Luật Đất đai 2024... Tuy nhiên tại TP.HCM, theo Điều Y Quyết định Z...",
    citations: [{dieu:"X", khoan:"1", van_ban:"luat-dat-dai-2024"}, ...]
  }
```

---

## 3. Tech Stack

| Tầng | Công nghệ | Phiên bản / Ghi chú | Trạng thái |
|---|---|---|---|
| **Cơ sở dữ liệu đồ thị** | Neo4j | 5.x (Community Edition) | ✅ Đã xác nhận |
| **Cơ sở dữ liệu vector** | Qdrant | latest stable | ✅ Đã xác nhận |
| **Container hóa** | Docker + Docker Compose | v2.x | ✅ Đã xác nhận |
| **Ngôn ngữ lập trình** | Python | ≥ 3.10 | ✅ Đã xác nhận |
| **Neo4j driver** | neo4j (Python official) | 5.x | ✅ Đã xác nhận |
| **Qdrant client** | qdrant-client | latest | ✅ Đã xác nhận |
| **Embedding model** | BGE-M3 (BAAI/bge-m3) | dim=1024 | ⚙️ Cần quyết định: local vs API |
| **Sparse retrieval** | BM25 (via Qdrant sparse) | — | ✅ Đã xác nhận |
| **Rank fusion** | Reciprocal Rank Fusion (RRF) | custom impl hoặc thư viện | ✅ Đã xác nhận |
| **LLM — Query Planner** | Claude (Anthropic) | claude-haiku-4-5-20251001 | ✅ Đã xác nhận |
| **LLM — Answer Generator** | Claude (Anthropic) | claude-sonnet-4-6 | ✅ Đã xác nhận |
| **Testing** | pytest | latest | ✅ Đã xác nhận |
| **Notebook** | Jupyter | — | ✅ Đã xác nhận |
| **Version control** | Git | — | ✅ Đã xác nhận |
| **Dependency management** | pip + requirements.txt | — | ✅ Đã xác nhận |

---

## 4. Lộ trình tính năng

### Hạ tầng & Môi trường (Phase 0)

| Tính năng | Phase | Loại |
|---|---|---|
| Docker Compose với Neo4j + Qdrant | 0 | Core |
| Python environment chuẩn hóa | 0 | Core |
| Script kiểm tra kết nối tích hợp | 0 | Core |
| Git repository với convention | 0 | Core |

### Thu thập & Chuẩn hóa dữ liệu (Phase 1)

| Tính năng | Phase | Loại |
|---|---|---|
| Bảng ánh xạ văn bản (mapping table) | 1 | Core |
| Thu thập thủ công từ VBHN/vbpl.vn theo Chương/Mục | 1 | Core |
| YAML metadata block chuẩn hóa (kể cả source_vbhn, amended_by_norms, summary) | 1 | Core |
| ~~`specified_in_map.md` ([:SPECIFIED_IN] manual mapping)~~ | ~~1~~ | ~~Đã xóa (D-07)~~ |
| Script validate metadata | 1 | Core |
| Cross-check chéo giữa 2 thành viên | 1 | Core |

### Ingestion Pipeline (Phase 2)

| Tính năng | Phase | Loại |
|---|---|---|
| Structure-aware Parser (AST) | 2 | Core |
| Deterministic ID generation (SHA256) | 2 | Core |
| Ontology Instantiation — 6 loại node | 2 | Core |
| Edge creation — 6 loại edge bắt buộc | 2 | Core |
| `[:BELONGS_TO]` (Component → Theme) | 2 | Enhancement (xem P-03) |
| BGE-M3 encoding + Qdrant upsert | 2 | Core |
| Metadata payload đầy đủ trong Qdrant | 2 | Core |
| Idempotency toàn bộ pipeline | 2 | Core |
| Verification notebook + báo cáo | 2 | Core |

### Retrieval Pipeline (Phase 3)

| Tính năng | Phase | Loại |
|---|---|---|
| Query Planner (LLM + structured extraction) | 3 | Core |
| Confirmation Loop khi thiếu Jurisdiction | 3 | Core |
| Sub-graph Extraction via Cypher | 3 | Core |
| Temporal filtering (CTV valid_from/to) | 3 | Core |
| Qdrant payload filtering | 3 | Core |
| Dense retrieval (BGE-M3) | 3 | Core |
| Sparse retrieval (BM25) | 3 | Core |
| RRF fusion | 3 | Core |
| Context assembly + hierarchy ordering | 3 | Core |
| Token budget cap | 3 | Core |
| Answer generation với citation bắt buộc | 3 | Core |
| Citation parsing từ LLM output | 3 | Core |
| Pipeline end-to-end integration | 3 | Core |

### Đánh giá (Phase 4)

| Tính năng | Phase | Loại |
|---|---|---|
| Test set ≥ 30 câu hỏi với ground truth | 4 | Core |
| Baseline Naive RAG (chunking 512 + vector search) | 4 | Core |
| Retrieval metrics: Precision@k, Recall@k, MRR | 4 | Core |
| Generation metrics: Correctness, Faithfulness, Citation Accuracy | 4 | Core |
| Gap analysis (Gap 1, 2, 3) | 4 | Core |
| Failure case analysis | 4 | Core |
| Limitations documentation | 4 | Core |

---

## 5. Câu hỏi mở & Blockers

| # | Câu hỏi / Blocker | Chặn task nào | Giải quyết |
|---|---|---|---|
| OQ-01 | Format `id` cuối cùng: `luat-dat-dai-2024` hay `LDD-2024` hay hash? | TASK-06, TASK-07, toàn bộ Phase 2 | **Đã quyết định trong tài liệu này:** format `[loai-vb]-[slug]-[nam]`. VD: `luat-dat-dai-2024`. Xem §2.4. |
| OQ-02 | Cross-reference ngoài scope: lấy thêm Điều hay ghi limitation? | TASK-03, TASK-06 | Cần project owner quyết định từng trường hợp trong TASK-03. Output: `crossref_decisions.md`. |
| OQ-03 | BGE-M3: chạy local hay dùng API? | TASK-08, TASK-12 | Ngưỡng quyết định: nếu encode toàn bộ dataset > 2 giờ trên máy 8GB RAM → chuyển sang API. Xem P-02. |
| OQ-04 | LLM nào cho Query Planner và Answer Generator? | TASK-10, TASK-13, TASK-16, TASK-17 | Đã quyết định 2026-04-19: dùng Claude (Anthropic). Query Planner: claude-haiku-4-5-20251001. Answer Generator: claude-sonnet-4-6. Tối ưu token bằng cách dùng model nhẹ hơn cho bước phân loại, model mạnh hơn cho bước sinh câu trả lời. |
| OQ-05 | `[:BELONGS_TO]` có implement trong scope khóa luận không? | TASK-07 | Xem P-03. Khuyến nghị: **không implement trong scope này** — ghi nhận là limitation. |
| OQ-06 | Top-k mặc định cho Semantic Filtering là bao nhiêu? | TASK-12, TASK-15, TASK-17 | Chưa quyết định. Cần thử nghiệm trong TASK-14. Ảnh hưởng trực tiếp đến Precision@k và Recall@k. |

---

## 6. Vấn đề đã biết & Quyết định kiến trúc

### P-01 — Idempotency của Ingestion Pipeline

Việc chạy lại pipeline ingestion nhiều lần (ví dụ sau khi sửa file `.md`) có thể tạo duplicate nodes và vectors nếu không được xử lý đúng. Với Neo4j, sử dụng `MERGE` thay vì `CREATE` với điều kiện match trên `id` property. Với Qdrant, sử dụng `upsert` với ID là Deterministic ID của TextUnit.

**Quyết định:** Toàn bộ write operation vào cả hai database đều dùng upsert semantics. ID là deterministic SHA256 hash của context path — không dùng UUID hay sequential integer.

**Điều kiện nâng cấp:** Nếu dataset mở rộng vượt 10,000 TextUnit và upsert toàn bộ mỗi lần chạy trở nên quá chậm (> 10 phút) → implement incremental ingestion dựa trên file modification timestamp.

---

### P-02 — BGE-M3 Local vs. API

BGE-M3 chạy local trên máy 8GB RAM có thể gặp bottleneck về tốc độ encoding và memory. Ngưỡng cụ thể chưa được đo.

**Quyết định:** Mặc định thử local trước. Nếu encode toàn bộ dataset Phase 1 (dự kiến ~500-2000 TextUnit) mất hơn 2 giờ → chuyển sang API (OpenAI text-embedding-3-small hoặc Cohere embed-multilingual). **Ghi nhận quyết định này vào changelog của tài liệu khi đưa ra.**

**Điều kiện nâng cấp:** Khi dataset mở rộng vượt scope khóa luận hiện tại.

**Lưu ý quan trọng:** Nếu chuyển sang API embedding, dimension vector có thể thay đổi (không còn 1024). Phải **xóa và tạo lại** Qdrant collection với đúng dimension — không thể mix vectors từ hai model khác nhau trong cùng collection.

---

### P-03 — `[:BELONGS_TO]` không implement trong scope hiện tại

**Bối cảnh:** Edge `[:BELONGS_TO]` (Component → Theme) cho phép gán nhãn chuyên ngành **trực tiếp ở cấp Điều/Khoản**, độc lập với Theme của Norm chứa nó.

**Khi nào cần?** Khi scope có **văn bản đa-theme** — tức một văn bản thuộc nhiều lĩnh vực cùng lúc. Ví dụ: Bộ luật Dân sự (BLDS) chứa cả điều khoản dân sự lẫn điều khoản liên quan đến bồi thường đất. Nếu Norm "BLDS" chỉ `[:INCLUDES]` vào Theme "dan-su", thì điều khoản về bồi thường đất sẽ **không được tìm thấy** khi query Theme "dat-dai" — trừ khi có `[:BELONGS_TO]` gán nhãn riêng ở cấp Component.

**Quyết định:** Không implement `[:BELONGS_TO]`. Lý do:

1. **Scope hiện tại không có văn bản đa-theme.** Ba lĩnh vực (Đất đai, Hộ tịch, Nuôi con nuôi) sử dụng các bộ luật **riêng biệt** — không có văn bản nào xuất hiện ở 2 Theme cùng lúc. Do đó, routing qua `Norm → [:INCLUDES] → Theme` đã đủ chính xác.
2. **Effort gán nhãn thủ công rất cao.** Mỗi Component (Điều/Khoản) cần được đọc nội dung và gán Theme thủ công — không thể tự động hóa đáng tin cậy.
3. **Không giải quyết gap nghiên cứu nào.** Ba gap (đa lĩnh vực, đa địa phương, đa tầng) đều đã được xử lý bởi các edge khác (`[:INCLUDES]`, `[:APPLIES_TO]`, `[:IMPLEMENTS]`).

**Limitation chấp nhận:** Nếu sau này mở rộng scope bao gồm văn bản đa-theme (ví dụ: Bộ luật Dân sự), các Component liên quan đến đất đai trong văn bản đó sẽ không được routing đúng.

**Điều kiện nâng cấp:** Khi evaluation (Phase 4) cho thấy ≥ 3 failure case có nguyên nhân trực tiếp là thiếu `[:BELONGS_TO]` routing → xem xét implement và đo lại metrics.


---

### P-05 — Routing thủ tục qua summary embedding thay vì `[:SPECIFIED_IN]`

**Bối cảnh:** Schema ban đầu dùng edge `[:SPECIFIED_IN]` (Procedure → Component) để ánh xạ thủ công từng thủ tục đến từng Điều/Khoản liên quan. Cách này không scalable: đòi hỏi đọc kỹ từng điều khoản, không tự động hóa được, và khi hệ thống mở rộng lên hàng nghìn văn bản thì chi phí maintenance là không khả thi.

**Quyết định (D-07 + D-08):** Xóa `Procedure` node và `[:SPECIFIED_IN]` edge. Thay thế bằng hai cơ chế:
1. **Theme + Jurisdiction filter** (hard filter): Query Planner classify câu hỏi thành theme + jurisdiction, dùng để lọc cứng trong Qdrant và Neo4j.
2. **Summary-based Stage 1 retrieval**: Mỗi văn bản có field `summary` (3-5 câu, do con người viết). Vectorizer index summary thành vector riêng (`content_type="summary"`). Khi có câu hỏi, Stage 1 tìm top-N Norm có summary liên quan → Stage 2 mới search TextUnit trong tập đó.

**Tại sao summary rẻ hơn `[:SPECIFIED_IN]`:**
- `[:SPECIFIED_IN]` cấp Điều: đọc kỹ, map thủ công từng điều khoản (2-4 giờ/văn bản dài)
- `summary`: viết 3-5 câu mô tả phạm vi tổng thể (10-15 phút/văn bản)

**Limitation chấp nhận:** Trong cùng một theme, khi jurisdiction không đủ phân biệt (VD: hai thủ tục Hộ tịch đều là toan-quoc), Stage 1 có thể trả về một số văn bản ít liên quan. Stage 2 semantic search sẽ tự nhiên loại chúng ra khi ranking. Ghi nhận là limitation trong thesis.

**Hướng phát triển tương lai:** Auto-generate `[:SPECIFIED_IN]` bằng LLM (document-level routing), hoặc dùng embedding similarity giữa procedure description và Norm summary để tự động xây dựng lại edge này mà không cần manual mapping.

---

### P-06 — Token Budget Cap mất thông tin

Context Assembly cắt bỏ TextUnit khi vượt `max_tokens=3000`. Với câu hỏi đa tầng đòi hỏi nhiều văn bản, cắt tỉa có thể loại bỏ TextUnit quan trọng ở tier thấp (Quyết định địa phương) vì nằm cuối danh sách sau sort.

**Quyết định:** Sort theo tier (tier 1 trước) nhưng **không** chỉ đưa tier 1 vào. Sau khi sort, fill từ top xuống cho đến khi gần đạt `max_tokens=3000`. Nếu tier 4 (Quyết định địa phương) bị cut hoàn toàn → log warning vì đây là thông tin địa phương quan trọng cho Gap 2. Xem xét tăng `max_tokens` nếu LLM context window cho phép.

**Điều kiện nâng cấp:** Nếu evaluation (Phase 4) cho thấy câu hỏi Gap 2 có Citation Accuracy thấp hơn Gap 1 đáng kể → nguyên nhân có thể là token budget cắt mất văn bản địa phương → tăng budget hoặc ưu tiên đảm bảo ít nhất 1 TextUnit từ mỗi tier có mặt trong context.
