# ĐỀ CƯƠNG CHI TIẾT KHÓA LUẬN

> **Đề tài:** Ontology-Driven GraphRAG cho Hệ thống Hỏi–đáp Pháp luật Việt Nam có Trích dẫn
> **Nhóm:** [A] (mảng Đất đai) + [B] (mảng Hộ tịch & Nuôi con nuôi) — 1 quyển chung, 2 đồng tác giả
> **Chuẩn trình bày:** QĐ 2284/2020/QĐ-TĐT (ĐH Tôn Đức Thắng) — xem `memory/reference_thesis_format_tdtu.md`
> **Định dạng nháp:** Markdown tiếng Việt trong `docs/thesis/`, convert Word áp format ở bước cuối.

Ký hiệu trạng thái mỗi mục:
- 🟢 **Viết được ngay** — tư liệu đã có (code + Decision Log + docs).
- 🟡 **Viết khung được, số liệu chờ** — phần thiết kế viết ngay, phần kết quả chờ chạy đo (sau khi [B] chốt GT + freeze).
- 🔵 **Tra cứu thêm** — cần bổ sung trích dẫn APA / công trình liên quan từ web.

---

## PHẦN ĐẦU QUYỂN (front matter — theo §Điều 2 & §3 QĐ 2284)

1. Trang bìa chính (Mẫu 1)
2. Trang bìa phụ (Mẫu 2)
3. Lời cảm ơn (Mẫu 3)
4. Lời cam đoan (Mẫu 4-1, 4-2) — có chữ ký cả A và B
5. (Phiếu giao nhiệm vụ — nếu Khoa yêu cầu)
6. Tóm tắt / Abstract — **cả tiếng Việt và tiếng Anh**, 1–2 trang (Mẫu 5)
7. Mục lục (Mẫu 6)
8. Danh mục hình vẽ (Mẫu 7)
9. Danh mục bảng biểu (Mẫu 8)
10. Danh mục ký hiệu & chữ viết tắt (Mẫu 9) — RAG, KG, KLTN, VBQPPL, VBHN, CTV, NĐ, TT, NQ, F1, NormR…

---

## CHƯƠNG 1 — MỞ ĐẦU  🟢
*(~4–6 trang; định khung toàn bộ)*

- **1.1. Lý do chọn đề tài** — pháp luật VN đồ sộ, phân mảnh; nhu cầu tra cứu có trích dẫn; hạn chế của LLM thuần (bịa citation) và RAG naive; đặt vấn đề 4 thách thức.
- **1.2. Mục tiêu nghiên cứu**
  - 1.2.1. Mục tiêu tổng quát — hệ hỏi–đáp pháp luật có trích dẫn, kết hợp KG + vector.
  - 1.2.2. Mục tiêu cụ thể — (a) mô hình ontology; (b) pipeline ingest→retrieve→generate; (c) giải 4 gap; (d) khung đánh giá chứng minh từng cơ chế.
- **1.3. Đối tượng và phạm vi nghiên cứu**
  - 1.3.1. Đối tượng — VBQPPL 3 lĩnh vực: đất đai, hộ tịch, nuôi con nuôi.
  - 1.3.2. Phạm vi — 32 Norm (dat-dai 20 / ho-tich 8 / ncn 4); 3 jurisdiction (toàn quốc, TP.HCM, Đồng Nai); 6 thủ tục; scope CMĐSDĐ (D-05).
- **1.4. Phương pháp nghiên cứu** — xây dựng hệ thống (design science) + đánh giá thực nghiệm định lượng (ablation, baseline, human-eval).
- **1.5. Ý nghĩa khoa học và thực tiễn**
  - 1.5.1. Khoa học — ontology-driven GraphRAG cho luật VN; khung đánh giá double-dissociation.
  - 1.5.2. Thực tiễn — công cụ tra cứu có trích dẫn, giảm sai sót pháp lý.
- **1.6. Bố cục luận văn.**

---

## CHƯƠNG 2 — TỔNG QUAN & CƠ SỞ LÝ THUYẾT  🟢🔵
*(~10–14 trang)*

- **2.1. Bài toán hỏi–đáp pháp luật Việt Nam và bốn thách thức**
  - 2.1.1. Đặc thù hệ thống VBQPPL (đa lĩnh vực, đa địa phương, đa tầng hiệu lực, đa phiên bản theo thời gian).
  - 2.1.2. Bốn khoảng trống Gap 1–4 (định nghĩa hình thức từng gap). 🟢
- **2.2. Các kỹ thuật nền tảng** 🔵
  - 2.2.1. Retrieval-Augmented Generation (RAG).
  - 2.2.2. Biểu diễn ngữ nghĩa & vector search (embedding, BGE-M3, Qdrant).
  - 2.2.3. Knowledge Graph & cơ sở dữ liệu đồ thị (Neo4j, Cypher).
  - 2.2.4. Ontology & mô hình hoá tri thức.
- **2.3. GraphRAG và các công trình liên quan** 🔵
  - 2.3.1. GraphRAG (Microsoft) và các biến thể.
  - 2.3.2. Ứng dụng RAG/KG trong lĩnh vực pháp luật (legal QA).
  - 2.3.3. Xử lý ngôn ngữ tự nhiên pháp luật tiếng Việt.
- **2.4. Khoảng trống nghiên cứu & định vị đề tài** — vì sao RAG naive/LLM thuần không giải được 4 gap; đóng góp khác biệt của đề tài. 🟢

---

## CHƯƠNG 3 — THIẾT KẾ HỆ THỐNG & PHƯƠNG PHÁP  🟢
*(~14–20 trang; chương xương sống, tư liệu chín nhất)*

- **3.1. Kiến trúc tổng thể** — sơ đồ Phase 1→4; luồng dữ liệu ingest / luồng truy vấn 3-stage.
- **3.2. Mô hình Ontology pháp luật**
  - 3.2.1. Chín loại node (Theme, Norm, Component, CTV, TextUnit, Jurisdiction, Amendment, Concept, Procedure).
  - 3.2.2. Mười loại edge (INCLUDES, IMPLEMENTS, AMENDS, HAS_COMPONENT, HAS_CTV, HAS_TEXT_UNIT, APPLIES_TO, AMENDED_BY, MAPS_TO_CONCEPT, REQUIRES_CONCEPT).
  - 3.2.3. Ánh xạ 4 gap ↔ cơ chế KG (bảng: Gap1=Theme/INCLUDES; Gap2=Jurisdiction/APPLIES_TO; Gap3=IMPLEMENTS; Gap4=CTV/AMENDS/AMENDED_BY).
- **3.3. Thu thập & chuẩn hoá dữ liệu (Phase 1)**
  - 3.3.1. Nguồn & phạm vi (vbpl.vn, VBHN; quy tắc thu thập theo Chương/Mục — D-01, D-02).
  - 3.3.2. Chuẩn hoá Markdown + YAML frontmatter (heading Điều/Khoản/Điểm/Tiết; annotation `amended_by`).
- **3.4. Pipeline nạp dữ liệu (Phase 2)**
  - 3.4.1. Parser & Deterministic ID (SHA256, idempotency).
  - 3.4.2. Graph builder 5-pass (Concept→Theme/Juris→Norm/Component/CTV→Amendment→Ontology mapping).
  - 3.4.3. Vectorizer (BGE-M3 → Qdrant, text-unit + summary vectors).
  - 3.4.4. Ánh xạ ontology bottom-up (concept rarity, D-13).
- **3.5. Truy hồi 3-stage / hybrid 4-pass (Phase 3)**
  - 3.5.1. Query planner (trích theme/procedure/jurisdiction/temporal; D-25 bỏ confirmation loop).
  - 3.5.2. Stage 1 — định tuyến qua summary embedding (D-08).
  - 3.5.3. Stage 2 — traversal đồ thị [:IMPLEMENTS|AMENDS*1..4] + lọc jurisdiction/temporal (D-09).
  - 3.5.4. Stage 3 & Hybrid search 4-pass (Structured cite, Dense Floor D-10, RRF; Pass -1 D-11).
  - 3.5.5. Context assembler & answer generator (sort tier, cap 6000 token, prompt caching D-15, chống hallucination D-14/16/17).
  - 3.5.6. Verifier agent — Generator→Verifier→prune (D-18).
- **3.6. Đa nhà cung cấp LLM** — claude / claude-fallback / gemini qua Vertex ADC (D-24).
- **3.7. Demo & khả năng chống chịu** *(tùy chọn)* — pre-cache + Gemini fallback.

---

## CHƯƠNG 4 — ĐÁNH GIÁ THỰC NGHIỆM & BÀN LUẬN  🟡
*(~14–20 trang; thiết kế viết ngay, số liệu chờ freeze GT)*

- **4.1. Kiến trúc đánh giá E0–E3** (triết lý "Claim → Evidence"; D-22). 🟢
- **4.2. Bộ dữ liệu kiểm thử & phương pháp xây dựng GT** 🟢
  - 4.2.1. Nguyên tắc & quy trình soạn GT (150 câu, provenance A+B, pre-register; `GT_AUTHORING_GUIDE.md`).
  - 4.2.2. Phân bố theo gap / theme / độ khó (gap1-4 ×25, negative 14, underspecified 8, composite 8, register 19).
  - 4.2.3. Chỉ số đánh giá (F1 Khoản/Điều, Norm Recall, Faithfulness, negative_correct; `cit_matches`).
- **4.3. E0 — Nền tin cậy** 🟡 — reproducibility (N=3, σ), significance (paired bootstrap 95% CI + Wilcoxon), metric validity.
- **4.4. E1 — Ablation double dissociation** 🟡 — no-theme/no-jurisdiction/no-implements/no-amends/no-temporal; mỗi cơ chế sụp đúng gap của nó & ổn định ở gap khác (cắt cấp cạnh giải confound Gap3/4).
- **4.5. E2 — Baseline ladder & đánh giá con người** 🟡 — closed-book / BM25 / naive RAG / oracle; human-eval (rubric E2C, nhóm A pháp lý + nhóm B người dùng) validated qua kappa (Landis-Koch).
- **4.6. E3 — Phân loại lỗi & kết quả âm** 🟡 — taxonomy (retrieval/generation/over-cite/negative-fail); negative results trung thực (D-12/19/20/24) như đóng góp khoa học.
- **4.7. Bàn luận** 🟡 — hệ hơn baseline có ý nghĩa thống kê & LLM-agnostic (Claude ≈ Gemini); điểm mạnh (Gap 4 temporal) & điểm yếu thật (multi-juris, NormR 0.766).

---

## CHƯƠNG 5 — KẾT LUẬN & HƯỚNG PHÁT TRIỂN  🟡
*(~3–4 trang)*

- **5.1. Kết luận** — tóm tắt đóng góp (không bình luận thêm — theo §1(5) QĐ 2284).
- **5.2. Hạn chế** — quy mô corpus/GT, NormR Gemini, multi-juris, chưa BELONGS_TO (P-03).
- **5.3. Hướng phát triển** — mở rộng domain/jurisdiction, temporal versioning đầy đủ (D-03), finetune embedding (teacher reranker D-20), cross-encoder.

---

## PHẦN CUỐI QUYỂN

- **Danh mục tài liệu tham khảo** — **A. Văn bản QPPL** (xếp theo tier 1→4, đúng format QĐ 2284 §2.6.1) + **B. Tài liệu tham khảo** (APA v6+, ABC theo họ, tách Việt/nước ngoài).
- **Phụ lục** — (A) danh sách 32 Norm & corpus; (B) schema ontology đầy đủ; (C) mẫu câu hỏi GT + đáp án; (D) rubric E2C; (E) bảng kết quả chi tiết per-câu.

---

## LỘ TRÌNH VIẾT (thứ tự đề xuất)

1. Chương 1 (Mở đầu) → 2. Chương 3 (Thiết kế) → 3. Chương 2 (Tổng quan, tra APA song song) → 4. Chương 4 phần thiết kế (4.1–4.2) → **[chờ GT freeze + chạy đo]** → 5. Chương 4 phần kết quả (4.3–4.7) → 6. Chương 5 → 7. Tóm tắt/Abstract + TLTK + Phụ lục.

> Phần 🟡 kết quả là đường găng: phụ thuộc [B] review GT → freeze → chạy E1/E2/E3 trên `test_set_v2`. Trong lúc chờ, viết trọn phần 🟢 và khung 🟡.
