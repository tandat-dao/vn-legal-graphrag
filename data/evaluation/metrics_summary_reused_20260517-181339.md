# Metrics Summary — TASK-17

- Test set: `data/evaluation/test_set_dat_dai.json`
- Run timestamp: 20260517-181339-reused
- Số câu hỏi: 19

## Overall

| Metric | GraphRAG | Baseline | Δ (G-B) |
|---|---:|---:|---:|
| Citation Precision (Khoản) | 0.224 | 0.347 | -0.123 |
| Citation Recall (Khoản) | 0.651 | 0.589 | 0.062 |
| Citation F1 (Khoản — strict) | 0.288 | 0.403 | -0.115 |
| Citation Precision (Điều) | 0.247 | 0.347 | -0.100 |
| Citation Recall (Điều) | 0.677 | 0.589 | 0.089 |
| Citation F1 (Điều — đo định tuyến văn bản) | 0.312 | 0.403 | -0.092 |
| Norm-level Recall (Văn bản) | 0.715 | 0.776 | -0.061 |
| Latency mean (s) | 21.002 | 20.311 | 0.691 |
| Latency p95 (s) | 30.310 | 25.960 | 4.350 |
| Negative correct rate (2 câu) | 0.000 | 1.000 | -1.000 |

## Theo gap_type

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 | 3 | 0.378 | 0.250 | 0.378 | 0.250 | 1.000 | 1.000 |
| gap2 | 6 | 0.439 | 0.597 | 0.439 | 0.597 | 1.000 | 1.000 |
| gap3 | 8 | 0.213 | 0.167 | 0.270 | 0.167 | 0.573 | 0.469 |
| negative | 2 | 0.000 | 1.000 | 0.000 | 1.000 | 0.000 | 1.000 |

## Theo theme

| Theme | N | G F1 | B F1 | G NormRecall | B NormRecall |
|---|---:|---:|---:|---:|---:|
| dat-dai | 19 | 0.288 | 0.403 | 0.715 | 0.776 |
