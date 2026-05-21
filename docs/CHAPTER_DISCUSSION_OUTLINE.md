# Chương Thảo luận — Dàn ý chi tiết (TASK-18 skeleton)

**Trạng thái:** Dàn ý + luận điểm định tính cố định + bảng định lượng RỖNG chờ data full (sau khi [B] nộp Hộ tịch + Nuôi con nuôi).

**Nguồn evidence hiện có:**
- 26 câu Đất đai (Q001-Q026) — [test_set_dat_dai.json](../data/evaluation/test_set_dat_dai.json)
- Kết quả v2.8: [results_graphrag_20260520-211930.json](../data/evaluation/results_graphrag_20260520-211930.json) (hoặc kết quả chạy mới nhất)
- Manual eval 10 câu: [MANUAL_EVAL.md](../data/evaluation/MANUAL_EVAL.md)
- Dry run report: [DRY_RUN_REPORT.md](../data/evaluation/DRY_RUN_REPORT.md)

---

## 1. Tổng quan kết quả

### 1.1 Thiết kế thực nghiệm

Hai hệ thống được đánh giá song song trên cùng test set:
- **GraphRAG (đề xuất)**: ontology-driven, Stage 1 summary embedding + Theme filter → Stage 2 Cypher traversal (IMPLEMENTS|AMENDS) → Stage 3 hybrid search (dense + keyword + rarity boost) → context assembly → LLM generation
- **Baseline (Naive RAG)**: fixed chunking (512 ký tự, overlap 50) + pure vector top-k → LLM generation

Cùng dữ liệu (`data/raw/*.md`), cùng embedding (BGE-M3), cùng LLM (Claude Sonnet 4.6) — **CHỈ KHÁC retrieval module**, đảm bảo so sánh khoa học.

### 1.2 Bảng kết quả tổng (chờ điền — full 30+ câu)

| Metric | GraphRAG | Baseline | Δ (G-B) | p-value (nếu tính) |
|---|---:|---:|---:|---:|
| Citation Precision (Khoản) | — | — | — | — |
| Citation Recall (Khoản) | — | — | — | — |
| Citation F1 (Khoản — strict) | — | — | — | — |
| Citation Precision (Điều) | — | — | — | — |
| Citation Recall (Điều) | — | — | — | — |
| Citation F1 (Điều — định tuyến VB) | — | — | — | — |
| Norm-level Recall (Văn bản) | — | — | — | — |
| Latency mean (s) | — | — | — | — |
| Latency p95 (s) | — | — | — | — |
| Negative correct rate | — | — | — | — |

**Subset Đất đai 26 câu (v2.8 — đã có):**

| Metric | GraphRAG | Baseline | Δ |
|---|---:|---:|---:|
| F1 Khoản | 0.539 | 0.295 | **+0.244 (+82.8%)** ✅ |
| F1 Điều | 0.567 | 0.295 | **+0.272 (+92.2%)** ✅ |
| Norm Recall | 0.931 | 0.699 | **+0.232 (+33.2%)** ✅ |
| Negative correct | 1.000 | 1.000 | tied ✅ |
| Faithful rate | 0.916 | — | — |

### 1.3 Bảng theo lĩnh vực (chờ điền)

| Theme | N | G F1(Kh) | B F1(Kh) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|
| dat-dai | 26 | 0.539 | 0.295 | 0.931 | 0.699 |
| ho-tich | — | — | — | — | — |
| nuoi-con-nuoi | — | — | — | — | — |

### 1.4 Bảng theo gap_type (chờ điền)

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 (đa lĩnh vực) | 3 | 0.343 | 0.194 | 0.343 | 0.194 | 1.000 | 0.667 |
| gap2 (đa địa phương) | 6 | 0.618 | 0.485 | 0.618 | 0.485 | 1.000 | 0.833 |
| gap3 (đa tầng VB) | 9 | 0.453 | 0.186 | 0.518 | 0.186 | 0.889 | 0.593 |
| gap4 (đa phiên bản) | 6 | 0.534 | 0.083 | 0.556 | 0.083 | 0.889 | 0.556 |
| negative (ngoài scope) | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

---

## 2. Luận điểm 1 — GraphRAG vượt trội ở chuỗi văn bản sửa đổi (lex posterior)

### 2.1 Vấn đề nghiên cứu

Pháp luật Việt Nam có cấu trúc đa tầng: Luật → Nghị quyết Quốc hội → Nghị định → Thông tư → Quyết định UBND. Các văn bản mới (NQ QH, NĐ sửa đổi) thường BỔ SUNG hoặc THAY THẾ một phần văn bản cũ (Luật, NĐ gốc). Người dùng cuối thường không biết chuỗi sửa đổi này.

**Câu hỏi mẫu (Q017):** "Cá nhân chuyển MĐSDĐ NN→ở từ 2026 cần áp dụng quy định nào về thẩm quyền và cách tính tiền SDĐ?"
- Đáp án đúng: Luật ĐĐ Đ121.1.b + Luật Đ156.1 + NQ 254/2025 Đ4 + NQ 254 Đ10.2.c + NĐ 102 Đ44a + NĐ 50/2026 Đ6

### 2.2 Cơ chế kỹ thuật của GraphRAG giải quyết

Ontology có cạnh `[:AMENDS]` riêng biệt với `[:IMPLEMENTS]`. Stage 2 Cypher mở rộng pattern `[:IMPLEMENTS|AMENDS*1..4]` undirected → khi seed là Luật ĐĐ, traversal tự động kéo:
- NĐ 102 (implements Luật)
- NQ 254 (amends Luật)
- NĐ 50/2026 (implements NQ 254 — chain qua 2 cạnh)

**Lex posterior rules trong prompt LLM** (`context_assembler.build_prompt`) hướng dẫn LLM ưu tiên văn bản mới hơn khi mâu thuẫn.

### 2.3 Evidence định lượng (đã có cho Q017)

| Câu | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|
| Q017 (lex posterior chain) | **0.60** | 0.00 | 0.50 | 0.25 |

Baseline F1=0 không phải do bịa, mà do **không retrieve được NQ 254 + NĐ 50/2026** (chỉ kéo Luật ĐĐ). Đây là failure mode rõ ràng của naive top-K.

### 2.4 Evidence định tính

Trích MANUAL_EVAL.md Q017:
- G: "trình bày khung pháp lý 4 lớp (Luật + NQ 254 + NĐ 102 + NĐ 50/2026) + bảng ưu đãi 30/50/100%"
- B: "SAI VĂN BẢN: cite Luật 47/2024/QH15 không có trong corpus (LLM bịa từ context fragment)"

### 2.5 Tổng quát hoá (chờ data full)

Bảng các câu lex posterior chain (sẽ điền sau khi có Hộ tịch + NCN):

| ID | Domain | Văn bản tier 1 (cũ) | Văn bản amendment | G NormR | B NormR |
|---|---|---|---|---:|---:|
| Q017 | dat-dai | Luật ĐĐ 2024 | NQ 254/2025/QH15 | 0.50 | 0.25 |
| Q012 | dat-dai | Luật ĐĐ 156 | NĐ 50/2026 | 1.00 | 0.33 |
| Q011 | dat-dai | NĐ 112/2024 | NĐ 226/2025 | 0.67 | 0.67 |
| (đợi B) | ho-tich | — | — | — | — |
| (đợi B) | nuoi-con-nuoi | — | — | — | — |

---

## 3. Luận điểm 2 — Định tuyến đa địa phương (jurisdiction-aware routing)

### 3.1 Vấn đề nghiên cứu

Cùng một thủ tục pháp lý, các tỉnh quy định khác nhau (VD: hạn mức giao đất ở TP.HCM 160m² vs Đồng Nai 200-400m²). Baseline naive không phân biệt được khi truy vấn, dễ trộn lẫn quy định 2 tỉnh.

**Câu hỏi mẫu (Q018):** "Cá nhân tại TP.HCM và cá nhân tại Đồng Nai cùng cấp GCN lần đầu thì nghĩa vụ tài chính khác nhau ở đâu?"

### 3.2 Cơ chế kỹ thuật của GraphRAG

- **Stage 2 jurisdiction filter** (`subgraph_extractor._JURISDICTION_ALLOW`): hard filter qua `[:APPLIES_TO]` edge để loại bỏ văn bản không thuộc tỉnh.
- **Key `multi-juris`** (mới thêm trong fix #3): cho phép truy xuất cả 3 jurisdictions (toan-quoc + tp-hcm + dong-nai) — phục vụ câu so sánh chéo.
- **Stage 1 summary embedding**: routing theo theme + jurisdiction trong payload metadata.

### 3.3 Evidence định lượng (gap2 — 6 câu đã có)

| Phase đánh giá | G NormR | B NormR | Cải thiện |
|---|---:|---:|---|
| Trước fix #3 | 0.333 | 1.000 | Baseline thắng nặng |
| Sau fix #3 multi-juris | **1.000** | 0.833 | **GraphRAG thắng** |

### 3.4 Evidence định tính (MANUAL_EVAL Q018)

- G: "trình bày BẢNG SO SÁNH chi tiết phí thẩm định 2 tỉnh với số tiền cụ thể (HCM: 420.000 đ/hồ sơ; ĐN: 880.000 đ trực tiếp / 836.000 đ trực tuyến)"
- B: "nói thẳng 'không có dữ liệu về TP.HCM' — chỉ cover ĐN"

→ Đây là evidence rõ ràng: GraphRAG **CHỦ ĐỘNG** retrieve từ cả 2 tỉnh nhờ ontology, baseline bị động theo cosine similarity rank.

### 3.5 Bảng câu gap2 đầy đủ (chờ điền)

| ID | Topic | Tỉnh | G NormR | B NormR | G F1(Kh) | B F1(Kh) |
|---|---|---|---:|---:|---:|---:|
| Q001 | Hạn mức giao đất | HCM | 1.0 | 1.0 | 1.0 | 0.86 |
| Q002 | Hạn mức giao đất | ĐN | 1.0 | 1.0 | 0.0 | 0.75 |
| Q007 | Phí thẩm định | HCM | 1.0 | 1.0 | — | — |
| Q008 | Phí thẩm định | ĐN | 1.0 | 1.0 | — | — |
| Q009 | Bảng giá đất | HCM | 1.0 | 1.0 | — | — |
| Q010 | Bảng giá đất | ĐN | 1.0 | 1.0 | — | — |
| Q018 | So sánh HCM vs ĐN | multi | **1.0** | **0.5** | 0.22 | 0.50 |
| (đợi B Hộ tịch — ho-tich đã set jurisdiction=toan-quoc, không có cặp đa tỉnh) | — | — | — | — | — | — |

---

## 4. Luận điểm 3 — Hallucination control + scope guard

### 4.1 Vấn đề nghiên cứu

LLM có xu hướng "bịa" câu trả lời khi context chứa keyword tương tự nhưng không đúng chủ đề. VD: hỏi về phí công chứng, LLM lấy chunks chứa "phí" trong Luật ĐĐ → bịa citation Đ27 Luật ĐĐ.

### 4.2 Giải pháp đã triển khai

**Fix #2 prompt scope guard** (`context_assembler.build_prompt`):
- Liệt kê tường minh chủ đề OOD (phí công chứng, thuế TNCN, dân sự...)
- Câu trả lời chuẩn cho LLM dùng nhất quán: "Câu hỏi này không thuộc phạm vi tài liệu pháp luật mà hệ thống đang lập chỉ mục..."

### 4.3 Evidence định lượng (negative — 2 câu đã có)

| Đợt | G negative correct rate | B negative correct rate |
|---|---:|---:|
| Trước fix #2 (v5) | 0.000 (bịa Đ27, Đ159) | 1.000 |
| Sau fix #2 (v7) | **1.000** | 1.000 |

### 4.4 Evidence định tính

Q006 + Q016 (phí công chứng, thuế TNCN): **cả 2 hệ thống trả lời CHÍNH XÁC giống nhau** câu chuẩn → fix #2 đã chuẩn hóa hành vi.

### 4.5 Bảng negative đầy đủ (chờ điền — đợi [B] thêm câu negative ngoài Đất đai)

| ID | Topic | Domain ngoài scope | G refuse | B refuse |
|---|---|---|---|---|
| Q006 | Phí công chứng | Luật Công chứng | ✓ | ✓ |
| Q016 | Thuế TNCN | Luật Thuế | ✓ | ✓ |
| (đợi B) | — | — | — | — |

---

## 5. Limitations + Failure Cases

### 5.1 Concept mapping coarse — chọn nhầm Điều chuyên sâu vs Điều chung

**Phát hiện:** Q002, Q003 và một số câu gap2: GraphRAG retrieve được đúng VĂN BẢN nhưng chọn nhầm Đ1 "Phạm vi điều chỉnh" hoặc Đ2 "Đối tượng áp dụng" thay vì Đ chuyên sâu (VD Đ3 hạn mức giao đất).

**Nguyên nhân:** `ontology_mapper` (TASK-07) gắn cả Đ1 và Đ3 cùng concept `han-muc` (cùng văn bản về hạn mức). Stage 1 summary routing chọn Đ chung trước vì similarity score cao hơn.

**Tác động:** Norm Recall = 1.0 (đúng văn bản) nhưng F1 Khoản giảm vì sai Khoản.

**Future Work:** Fine-tune concept_mapper với negative examples (Đ1 KHÔNG phải concept `han-muc-cu-the`); thêm rule penalize Đ1/Đ2 chung trong rarity calculation.

### 5.2 Câu hỏi cross-cluster — concept mapping không liên kết 2 cluster ý

**Q019 đại diện:** "Phương án bóc tách tầng đất mặt cần được cấp nào phê duyệt" — đòi hỏi nối "phương án bóc tách" (cluster NĐ 112+226) với "thẩm quyền chuyển giao" (cluster NĐ 151).

**Phát hiện:** Cả GraphRAG và Baseline đều miss phần phân cấp 2 cấp. Cả 2 chỉ retrieve phần bóc tách.

**Nguyên nhân:** Ontology concept "phương án bóc tách" và "thẩm quyền chuyển giao" được map vào 2 cluster khác nhau, không có cạnh liên kết. Naive vector cũng không capture được semantic bridge.

**Future Work:** Thêm cạnh `[:RELATED_TO]` giữa các Component có cross-reference text-level; hoặc dùng LLM-based query decomposition để tách câu phức thành sub-queries.

### 5.3 Confirmation Loop production — UX trade-off

`query_planner` ép xác nhận jurisdiction + procedure cho câu Đất đai → chặn 5/17 câu sau force_jurisdiction. Trong eval đã bypass; production chấp nhận friction để tránh trả nhầm.

**Future Work:** Cho phép auto-assign `toan-quoc` cho câu Đất đai không có địa phương + procedure rộng; cập nhật VALID_PROCEDURES thêm các thủ tục độc lập (hạn mức giao đất, bảng giá, tranh chấp).

### 5.4 Latency GraphRAG cao hơn baseline ~20% (20s vs 17s)

Do retrieval đa stage (planner LLM + Stage 1 Qdrant + Stage 2 Neo4j + Stage 3 hybrid). Trade-off chấp nhận cho quality. Có thể tối ưu bằng:
- Parallelize Stage 1 + Stage 2
- Cache planner output cho câu trùng intent

---

## 6. Future Work

1. **Mở rộng corpus** sang các lĩnh vực khác (lao động, hôn nhân, thừa kế) — kiểm chứng khả năng generalization của ontology.
2. **Temporal retrieval** chính thức: hiện CTV có `valid_from`/`valid_to` nhưng eval chưa có câu temporal — bổ sung test set với câu "trước/sau ngày X".
3. **Concept mapping fine-tuning**: như Limitations 5.1, cần training data có Đ1/Đ2 negative examples.
4. **Cross-cluster linking**: như Limitations 5.2, thêm cạnh hoặc query decomposition.
5. **UX cải tiến Confirmation Loop**: như Limitations 5.3, smart default + procedure mở rộng.
6. **Anthropic prompt caching** (5-min TTL): tích hợp `cache_control: ephemeral` cho phần system rules để giảm input token cost ~90%.

---

## 7. Kết luận

(Sẽ viết sau khi có data full — dựa trên các bảng định lượng đã điền và các luận điểm 1-3 đã có evidence.)

Tinh thần kết luận:
- **GraphRAG vượt trội cho câu hỏi pháp lý đa tầng + đa địa phương** — sweet spot của ontology + AMENDS edges + multi-juris filter.
- **Baseline cạnh tranh ở câu single-tier lookup** — vì chunks 512 ký tự ăn cấu trúc heading văn bản.
- **Cả 2 cùng refuse out-of-scope** sau prompt scope guard — không có trade-off hallucination/refuse.
- **3 hướng cải tiến rõ** (Limitations 5.1, 5.2, 5.3) cho Future Work.
