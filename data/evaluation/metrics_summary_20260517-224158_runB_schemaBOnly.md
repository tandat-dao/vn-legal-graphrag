# Metrics Summary — TASK-17

- Test set: `data/evaluation/test_set_dat_dai.json`
- Run timestamp: 20260517-224158
- Số câu hỏi: 19

## Overall

| Metric | GraphRAG | Baseline | Δ (G-B) |
|---|---:|---:|---:|
| Citation Precision (Khoản) | 0.310 | 0.304 | 0.005 |
| Citation Recall (Khoản) | 0.636 | 0.587 | 0.049 |
| Citation F1 (Khoản — strict) | 0.380 | 0.362 | 0.018 |
| Citation Precision (Điều) | 0.323 | 0.304 | 0.019 |
| Citation Recall (Điều) | 0.662 | 0.587 | 0.075 |
| Citation F1 (Điều — đo định tuyến văn bản) | 0.397 | 0.362 | 0.035 |
| Norm-level Recall (Văn bản) | 0.877 | 0.763 | 0.114 |
| Latency mean (s) | 23.828 | 17.779 | 6.049 |
| Latency p95 (s) | 35.480 | 26.010 | 9.470 |
| Negative correct rate (2 câu) | 1.000 | 1.000 | 0.000 |

## Theo gap_type

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 | 3 | 0.350 | 0.194 | 0.350 | 0.194 | 1.000 | 1.000 |
| gap2 | 6 | 0.432 | 0.400 | 0.432 | 0.400 | 1.000 | 0.833 |
| gap3 | 8 | 0.196 | 0.236 | 0.237 | 0.236 | 0.708 | 0.562 |
| negative | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Theo theme

| Theme | N | G F1 | B F1 | G NormRecall | B NormRecall |
|---|---:|---:|---:|---:|---:|
| dat-dai | 19 | 0.380 | 0.362 | 0.877 | 0.763 |
