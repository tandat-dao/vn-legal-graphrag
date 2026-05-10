# Phase 2 Verification Report
**Ngày:** 2026-05-10
**Người thực hiện [A]:** Đào Nguyễn Tấn Đạt
**Người thực hiện [B]:** *(chờ ký xác nhận)*

---

## 1. Neo4j — Node Counts

Query: `MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY count DESC`

| Node type | Count |
|---|---|
| Component | 3014 |
| CTV | 3014 |
| TextUnit | 3014 |
| Norm | 17 |
| Jurisdiction | 3 |
| Theme | 1 |

**Nhận xét:** 6/6 loại node đều có count > 0. Theme hiện chỉ có 1 (`dat-dai`) do [B] chưa nộp file Hộ tịch + Nuôi con nuôi — sẽ tăng lên 3 sau khi [B] chạy `run_ingestion()`.

---

## 2. Neo4j — Edge Verification

### 2a. `[:IMPLEMENTS]` chain (tier 2 → tier 1)

Query: `MATCH (n:Norm {tier:2})-[:IMPLEMENTS]->(p:Norm {tier:1}) RETURN n.id, p.id LIMIT 5`

| Norm tier 2 | implements | Norm tier 1 |
|---|---|---|
| nghi-dinh-102-2024-nd-cp | → | luat-dat-dai-2024 |
| nghi-dinh-49-2026-nd-cp | → | nghi-quyet-254-2025-qh15 |
| nghi-dinh-50-2026-nd-cp | → | nghi-quyet-254-2025-qh15 |

**Kết quả:** ✅ 3 chains hợp lệ (tier 2 → tier 1).

### 2b. `[:APPLIES_TO]` jurisdiction (10 đầu)

Query: `MATCH (n:Norm)-[:APPLIES_TO]->(j:Jurisdiction) RETURN n.id, j.name LIMIT 10`

| Norm | Jurisdiction |
|---|---|
| nghi-quyet-254-2025-qh15 | toan-quoc |
| nghi-dinh-50-2026-nd-cp | toan-quoc |
| nghi-dinh-49-2026-nd-cp | toan-quoc |
| nghi-dinh-226-2025-nd-cp | toan-quoc |
| nghi-dinh-151-2025-nd-cp | toan-quoc |
| nghi-dinh-112-2024-nd-cp | toan-quoc |
| nghi-dinh-102-2024-nd-cp | toan-quoc |
| nghi-dinh-101-2024-nd-cp | toan-quoc |
| luat-dat-dai-2024 | toan-quoc |
| quyet-dinh-69-2024-qd-ubnd-tp-hcm | tp-hcm |

**Kết quả:** ✅ Jurisdiction đúng — văn bản quốc gia → `toan-quoc`, văn bản TP.HCM → `tp-hcm`.

---

## 3. Qdrant — Vector Counts

| content_type | Vector count | Neo4j node count | Khớp? |
|---|---|---|---|
| `text_unit` | 3014 | 3014 (TextUnit) | ✅ |
| `summary` | 17 | 17 (Norm) | ✅ |

---

## 4. Vector Search — Stage 1 (Summary Routing)

Query: `"phí chuyển mục đích sử dụng đất"` | Filter: `content_type="summary"`, `theme="dat-dai"` | Top-3

| Rank | Score | norm_id | tier | jurisdiction |
|---|---|---|---|---|
| 1 | 0.6381 | nghi-dinh-50-2026-nd-cp | 2 | toan-quoc |
| 2 | 0.5978 | nghi-quyet-02-2023-nq-hdnd-tp-hcm | 4 | tp-hcm |
| 3 | 0.5828 | nghi-quyet-22-2024-nq-hdnd-dong-nai | 4 | dong-nai |

**Kết quả:** ✅ Top-3 đều thuộc lĩnh vực Đất đai — ngữ nghĩa đúng (phí SDĐ liên quan đến NĐ 50, NQ TP.HCM, NQ Đồng Nai về bảng giá đất).

---

## 5. Vector Search — Stage 2 (Text Unit Retrieval)

Query: `"đăng ký khai sinh"` | Filter: `content_type="text_unit"`, `jurisdiction="toan-quoc"` | Top-3

| Rank | Score | norm_id | theme |
|---|---|---|---|
| 1 | 0.8229 | nghi-dinh-49-2026-nd-cp | dat-dai |
| 2 | 0.7982 | luat-dat-dai-2024 | dat-dai |
| 3 | 0.7954 | luat-dat-dai-2024 | dat-dai |

**Nhận xét:** ⏳ Kết quả trả về `dat-dai` vì [B] chưa nộp file Hộ tịch. DoD item "top-3 thuộc Hộ tịch" sẽ được re-verify sau khi [B] chạy `run_ingestion()` + `run_vectorization()`. Kỹ thuật search hoạt động đúng — filter `jurisdiction` và `content_type` đã lọc đúng.

---

## 6. Idempotency

| Script | Lần 1 | Lần 2 | Kết quả |
|---|---|---|---|
| `run_ingestion()` | 9063 nodes | 9063 nodes | ✅ |
| `run_vectorization()` | 3031 vectors | 3031 vectors | ✅ |

---

## 7. Kết luận

| DoD item | Trạng thái |
|---|---|
| 6 loại node count > 0 | ✅ |
| `[:IMPLEMENTS]` chain hợp lệ | ✅ |
| `[:APPLIES_TO]` jurisdiction đúng | ✅ |
| text_unit vector count = TextUnit count | ✅ |
| summary vector count = Norm count | ✅ |
| Stage 1 top-3 thuộc dat-dai | ✅ |
| Stage 2 top-3 thuộc Hộ tịch | ⏳ chờ [B] nộp data |
| Ký xác nhận [A] | ✅ Đào Nguyễn Tấn Đạt — 2026-05-10 |
| Ký xác nhận [B] | ⏳ chờ |

**Phase 2 [A] sẵn sàng cho Phase 3.** Phase 3 có thể bắt đầu với dữ liệu Đất đai. Verification sẽ được cập nhật sau khi [B] hoàn thành.
