# TASK-17 Dry Run Report — Đất đai (19 câu)

**Ngày chạy mới nhất:** 2026-05-17 14:33:30 (v3 — sau khi áp dụng `force_jurisdiction` + verify GT + thêm killer gap3)
**Test set:** `data/evaluation/test_set_dat_dai.json` (19 câu Q001-Q019)
**Hệ thống:** GraphRAG (`run_pipeline`) vs Baseline Naive RAG (`run_baseline_query`)

> ⚠️ Đây là dry run trên SUBSET Đất đai. Báo cáo chính thức TASK-17 chỉ hoàn tất sau khi TASK-15 thêm Hộ tịch + Nuôi con nuôi để đủ ≥ 30 câu.

## Lịch sử các đợt chạy

| Đợt | Ngày | F1 Khoản G/B | F1 Điều G/B | Norm Recall G/B | Thay đổi |
|---|---|---|---|---|---|
| v1 | 2026-05-17 13:12 | 0.125 / 0.257 | — | 0.479 / 0.802 | Bản đầu, 16 câu, không có cấp Điều, không bypass confirmation |
| v2 | 2026-05-17 14:02 | 0.115 / 0.238 | 0.192 / 0.426 | 0.408 / 0.430 | 19 câu (thêm Q017-Q019); fix GT Q004/Q011/Q013; thêm metric cấp Điều |
| **v3** | **2026-05-17 14:33** | **0.127 / 0.239** | **0.248 / 0.378** | **0.522 / 0.675** | **+ `force_jurisdiction` bypass Confirmation Loop** |

## Kết quả v3 (mới nhất)

| Metric | GraphRAG | Baseline | Δ (G-B) |
|---|---:|---:|---:|
| Citation Precision (Khoản) | 0.130 | 0.219 | -0.089 |
| Citation Recall (Khoản) | 0.132 | 0.304 | -0.173 |
| Citation F1 (Khoản — strict) | 0.127 | 0.239 | -0.112 |
| Citation Precision (Điều) | 0.226 | 0.327 | -0.102 |
| Citation Recall (Điều) | 0.361 | 0.578 | -0.217 |
| Citation F1 (Điều — định tuyến VB) | 0.248 | 0.378 | -0.130 |
| Norm-level Recall (Văn bản) | 0.522 | 0.675 | -0.154 |
| Latency mean (s) | 16.16 | 18.96 | -2.80 |
| Negative correct rate (2 câu) | 1.000 | 1.000 | 0 |

### Theo gap_type

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 | 3 | 0.000 | 0.083 | **0.206** | 0.083 | **0.667** | 0.333 |
| gap2 | 6 | 0.000 | 0.268 | 0.111 | 0.515 | 0.333 | 1.000 |
| gap3 | 8 | 0.053 | 0.086 | 0.178 | 0.230 | **0.490** | 0.479 |
| negative | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Phát hiện then chốt

### 1. GraphRAG THẮNG trên 3/6 killer gap3 — proof of value

| ID | Topic | G F1(Đ) | B F1(Đ) | Winner |
|---|---|---:|---:|---|
| **Q011** | Bóc tách + nghĩa vụ tài chính chuyển đất lúa | **0.18** | 0.00 | **G** |
| **Q012** | Tiền SDĐ chuyển vườn ao → ở (NQ 254 + NĐ 50) | **0.40** | 0.00 | **G** |
| Q013 | Tranh chấp phân cấp huyện-xã (Đ236 + NĐ 151) | 0.00 | 0.29 | B |
| **Q017** | Lex posterior chain chuyển NN→ở từ 2026 | **0.44** | 0.00 | **G** |
| Q018 | Multi-jurisdiction conflict HCM vs ĐN | 0.00 | 0.50 | B |
| Q019 | Deep amendment chain (Luật + 3 NĐ) | 0.20 | 0.31 | B |

**Q017 (Lex posterior chain) — Killer question mở khóa thesis claim:**
GraphRAG đúng được 3/6 citation đa tầng (Luật + NQ QH + 2 NĐ) bao gồm cả văn bản amendment mới. Baseline chỉ trả 1 chunk lạc văn bản. Đây chứng minh ontology + cạnh `[:IMPLEMENTS|AMENDS*1..4]` của GraphRAG nắm được mối quan hệ multi-tier mà naive vector không thấy.

### 2. GraphRAG THẮNG ở gap1 (single-domain) ở cấp Điều và Norm Recall

- gap1 F1 Điều: G 0.206 vs B 0.083 (G +2.5x)
- gap1 Norm Recall: G 0.667 vs B 0.333 (G +2x)

Stage 1 routing theo summary embedding + Theme filter định tuyến đúng văn bản nguồn tốt hơn naive top-K.

### 3. GraphRAG THUA nặng ở gap2 (multi-jurisdiction)

- gap2 F1 Khoản: G 0.000 vs B 0.268
- gap2 Norm Recall: G 0.333 vs B 1.000

**Cần điều tra:** jurisdiction filter có thể quá restrictive khi câu hỏi rõ ràng nói tỉnh (TP.HCM hoặc ĐN). Cụ thể Q009-Q010 (bảng giá HCM/ĐN) GraphRAG retrieve 0 chunks dù force_jurisdiction. Có thể missing field khác (procedure?).

### 4. Confirmation Loop residual: 5/17 câu vẫn fail dù force

Q001, Q009, Q010, Q013, Q014 vẫn `confirmation_needed=True` sau force. Lý do: `query_planner` còn thiếu trường khác (procedure / temporal). 

Hiện chấp nhận đây là failure mode → ghi nhận trong thesis Limitations.

## Implication cho TASK-18 (Discussion)

Luận điểm chính có thể defend:

1. **GraphRAG vượt baseline khi câu hỏi đòi hỏi đa tầng amendment** (Q017 đại diện). Đây là sweet spot của ontology + AMENDS edges, không thể đạt được bằng pure vector search.
2. **GraphRAG vượt baseline khi định tuyến văn bản (gap1)** — Stage 1 summary embedding + Theme filter chính xác hơn naive top-K vector.
3. **GraphRAG thua baseline ở câu lookup tĩnh trong văn bản nhỏ** — vì baseline chunks 512 ký tự khớp nguyên block Điều của QĐ nhỏ → dễ trích citation chuẩn.
4. **GraphRAG cần cải tiến UX cho jurisdiction-aware retrieval** — Confirmation Loop hiện ép user xác nhận quá nhiều, trên benchmark gây F1=0 cho 5 câu.

## Implication cho TASK-15 (test set)

- Bias hiện tại: 6/19 câu là "small QĐ lookup" (Q001, Q002, Q007, Q008, Q009, Q010) — baseline ăn cấu trúc heading.
- Thiếu câu temporal (CTV valid_from/valid_to) — domain GraphRAG có lợi thế chưa được test.
- Khi [B] nộp Hộ tịch + NCN, nên cân bằng để gap2/gap3 chiếm ≥ 50%.

## Implication cho Phase 3 (đã đóng băng v1.8)

KHÔNG reopen Phase 3. Các findings:
- Concept mapping coarse (Đ1 vs Đ3) — Future Work
- Confirmation Loop ép user — Future Work (tuy nhiên đã bypass cho eval qua `force_jurisdiction`)
- Jurisdiction filter có thể loose hơn cho gap2 — Future Work

## Cách reproduce

```bash
# Chạy v3 (force_jurisdiction từ test_set)
python -m src.evaluation.run_evaluation \
    --test-set data/evaluation/test_set_dat_dai.json

# Chỉ 1 hệ thống
python -m src.evaluation.run_evaluation \
    --test-set data/evaluation/test_set_dat_dai.json \
    --systems graphrag
```

Yêu cầu trước: TASK-08 (Qdrant `legal_texts`) + TASK-16 ingest (Qdrant `baseline_legal_texts`) + Neo4j graph đã build.
