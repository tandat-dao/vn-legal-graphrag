# TASK-17 Dry Run Report — Đất đai (16 câu)

**Ngày chạy:** 2026-05-17 13:26:14
**Test set:** `data/evaluation/test_set_dat_dai.json` (16 câu Đất đai, Q001-Q016)
**Hệ thống:** GraphRAG (`run_pipeline`) vs Baseline Naive RAG (`run_baseline_query`)

> ⚠️ Đây là dry run trên SUBSET Đất đai. Báo cáo chính thức của TASK-17 chỉ chạy được sau khi TASK-15 hoàn tất (thêm Hộ tịch + Nuôi con nuôi để đủ ≥ 30 câu).

## Mục đích dry run

Verify pipeline TASK-17:
1. Runner gọi cả 2 hệ thống không crash trên 16 câu
2. Metrics module (citation_score, norm_recall, aggregate) tính ra số liệu hợp lý
3. Markdown summary render đúng theo gap_type / theme

→ Cả 3 đạt. Pipeline TASK-17 hoạt động ổn định.

## Kết quả (xem `metrics_summary_20260517-132614.md` chi tiết)

| Metric | GraphRAG | Baseline | Δ |
|---|---:|---:|---:|
| Citation F1 (khoan) | 0.125 | 0.257 | **-0.132** |
| Norm-level Recall | 0.479 | 0.802 | **-0.323** |
| Latency mean (s) | 14.1 | 18.7 | +4.6 (G nhanh hơn) |
| Negative correct rate | 100% | 100% | 0 |

## Phát hiện (đầu vào cho TASK-18 / chương Discussion)

### 1. Confirmation Loop bị trigger 13/16 lần

`query_planner.py` yêu cầu user xác nhận `jurisdiction` cho mọi câu Đất đai không có địa phương rõ ràng (theo design Phase 3 — Đất đai KHÔNG auto-assign `toan-quoc`). 13/16 câu trong test set Đất đai có jurisdiction=`toan-quoc` hoặc không nêu địa phương cụ thể → đều bị confirmation.

**Workaround trong runner:** Khi `confirmation_needed=True`, runner tự augment câu hỏi với suffix jurisdiction từ test set (mô phỏng user trả lời) và rerun pipeline 1 lần. Latency cộng dồn.

**Vấn đề thật:** Đây là design choice cẩn thận của Phase 3 — nhưng trên benchmark, nó làm GraphRAG mất 1 LLM call so với baseline. Cần thảo luận trong thesis:
- Trade-off: an toàn tránh trả nhầm jurisdiction vs friction tăng latency
- Cân nhắc cho phép auto-assign `toan-quoc` khi câu hỏi không nêu địa phương VÀ procedure không phụ thuộc địa phương

### 2. GraphRAG citation F1 thấp hơn baseline trên Đất đai

Trên 16 câu Đất đai (chủ yếu gap2/gap3), GraphRAG F1=0.125 vs Baseline F1=0.257. Hai nguyên nhân chính:

**(a) Limitation đã biết (v1.8):** GraphRAG semantic_filter thường chọn Đ1 "Phạm vi điều chỉnh" thay vì Điều chuyên sâu vì cả 2 Điều cùng map về concept thô (ví dụ cả "han-muc"). Cụ thể bị trên: QĐ 69 Đ3 (hạn mức 160m²), QĐ 92 Đ3 (200-400m²), NQ 87 Đ6 (bảng giá).

**(b) Baseline ăn may cấu trúc heading:** Chunks 512 ký tự thường bắt nguyên block "## Điều X" trong markdown → LLM dễ trích `[Điều X, Khoản Y, Văn bản Z]` chính xác. GraphRAG retrieve theo TextUnit cấp Khoản nhưng context_path đôi khi không khớp ground truth Điều/Khoản chính xác.

### 3. GraphRAG nhanh hơn baseline trung bình (14s vs 19s)

Bù lại độ trễ confirmation, GraphRAG vẫn nhanh hơn do top-K nhỏ hơn (25 vs 10 nhưng context block ngắn hơn) và LLM call ít tokens hơn. p95 GraphRAG cao hơn (35s vs 31s) do retry confirmation cộng dồn.

### 4. Cả 2 hệ thống xử lý negative đúng 100% (2/2)

Q006 (phí công chứng) và Q016 (thuế TNCN) — cả GraphRAG và Baseline đều từ chối trả lời, không bịa citation.

## Implication cho TASK-15 (test set)

- Test set Đất đai có thể bias về câu `toan-quoc` (10/16) so với jurisdiction-specific. Khi mở rộng (Hộ tịch + Nuôi con nuôi), nên cân bằng để đo đa địa phương tốt hơn.
- Một số ground truth Khoản có thể sai/thiếu khi chấm — review thủ công trước khi báo cáo chính thức.

## Implication cho Phase 3 (đã đóng băng v1.8)

Không reopen Phase 3 trong scope khóa luận này. Các findings:
- Concept mapping coarse (Đ1 vs Đ3) — ghi vào Future Work
- Confirmation Loop ép user — ghi vào Future Work (UX trade-off)

## Cách reproduce

```bash
# Chạy lại dry run
python -m src.evaluation.run_evaluation \
    --test-set data/evaluation/test_set_dat_dai.json

# Chỉ 1 hệ thống
python -m src.evaluation.run_evaluation \
    --test-set data/evaluation/test_set_dat_dai.json \
    --systems graphrag
```

Yêu cầu trước: TASK-08 (Qdrant `legal_texts`) + TASK-16 ingest (Qdrant `baseline_legal_texts`) + Neo4j graph đã build.
