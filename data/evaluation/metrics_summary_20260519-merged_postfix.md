# Metrics Summary — TASK-17 (merged snapshot post-Cách-C-fix)

- Test set: `data/evaluation/test_set_dat_dai.json`
- Snapshot timestamp: 20260519-merged-postfix
- Số câu hỏi: 26
- **Lưu ý**: Snapshot ghép từ run v1 (Q001-Q025, pre-fix) + run v2 (Q026, post-Cách-C-fix). Cách C chỉ trigger khi LLM trả `theme=None` — đã verify Q001-Q025 không bị ảnh hưởng (cache hits identical).
- Anthropic 529 outage cùng ngày → một số run sau bị crash; snapshot này là tổ hợp các câu chạy thành công.

## Overall

| Metric | GraphRAG | Baseline | Δ (G-B) |
|---|---:|---:|---:|
| Citation Precision (Khoản) | 0.388 | 0.248 | +0.140 |
| Citation Recall (Khoản) | 0.649 | 0.428 | +0.221 |
| Citation F1 (Khoản — strict) | 0.440 | 0.285 | +0.155 |
| Citation Precision (Điều) | 0.399 | 0.248 | +0.151 |
| Citation Recall (Điều) | 0.668 | 0.428 | +0.240 |
| Citation F1 (Điều — đo định tuyến văn bản) | 0.453 | 0.285 | +0.168 |
| Norm-level Recall (Văn bản) | 0.891 | 0.737 | +0.154 |
| Latency mean (s) | 23.966 | 17.688 | +6.278 |
| Latency p95 (s) | 37.990 | 22.980 | +15.010 |
| Negative correct rate (2 câu) | 1.000 | 1.000 | +0.000 |

## Theo gap_type

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 | 3 | 0.350 | 0.194 | 0.350 | 0.194 | 1.000 | 1.000 |
| gap2 | 6 | 0.543 | 0.487 | 0.543 | 0.487 | 1.000 | 1.000 |
| gap3 | 15 | 0.341 | 0.126 | 0.365 | 0.126 | 0.811 | 0.544 |
| negative | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Theo theme

| Theme | N | G F1 | B F1 | G NormRecall | B NormRecall |
|---|---:|---:|---:|---:|---:|
| dat-dai | 26 | 0.440 | 0.285 | 0.891 | 0.737 |

## Q026 spotlight — AMENDED_BY exploitation (Ý 2)

- **Question**: Khoản 1 Điều 13 Nghị định 102/2024/NĐ-CP đã được văn bản nào sửa đổi và hiệu lực từ ngày nào?
- **Trước fix (v1)**: F1=0, NormRecall=0, `theme=None` → Stage 1 trả `[]` → pipeline short-circuit (1.77s).
- **Sau fix Cách C (v2)**: F1=0, NormRecall=0.50; backfill `theme='dat-dai'` từ token `102/2024/NĐ-CP`, pipeline retrieve 10 norms + 8 units, answer cite `nghi-dinh-49-2026-nd-cp` (1/2 amending norm — recall 0.5).
- **F1 vẫn = 0**: retrieval lấy nhầm Khoản 11/12 (đều có amended_by 49/2026) thay vì Khoản 1 → ground-truth `Khoản 1 Đ13` không match. Đây là vấn đề **retrieval depth** (Component-level pinpoint), không phải Query Planner. Đề xuất future work: regex extract `Khoản X Điều Y` từ câu hỏi để force LCCID filter.
