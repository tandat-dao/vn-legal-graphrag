# Metrics Summary — TASK-17

- Test set: `data/evaluation/test_set_dat_dai.json`
- Run timestamp: 20260517-222919
- Số câu hỏi: 19

## Overall

| Metric | GraphRAG | Baseline | Δ (G-B) |
|---|---:|---:|---:|
| Citation Precision (Khoản) | 0.355 | 0.347 | 0.008 |
| Citation Recall (Khoản) | 0.629 | 0.569 | 0.060 |
| Citation F1 (Khoản — strict) | 0.420 | 0.389 | 0.031 |
| Citation Precision (Điều) | 0.374 | 0.347 | 0.027 |
| Citation Recall (Điều) | 0.655 | 0.569 | 0.086 |
| Citation F1 (Điều — đo định tuyến văn bản) | 0.442 | 0.389 | 0.053 |
| Norm-level Recall (Văn bản) | 0.864 | 0.719 | 0.145 |
| Latency mean (s) | 19.670 | 16.021 | 3.649 |
| Latency p95 (s) | 31.570 | 23.780 | 7.790 |
| Negative correct rate (2 câu) | 1.000 | 1.000 | 0.000 |

## Theo gap_type

| Gap | N | G F1(Kh) | B F1(Kh) | G F1(Đ) | B F1(Đ) | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|---:|
| gap1 | 3 | 0.395 | 0.217 | 0.395 | 0.217 | 1.000 | 0.667 |
| gap2 | 6 | 0.471 | 0.438 | 0.471 | 0.438 | 1.000 | 0.833 |
| gap3 | 8 | 0.247 | 0.264 | 0.299 | 0.264 | 0.677 | 0.583 |
| negative | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

## Theo theme

| Theme | N | G F1 | B F1 | G NormRecall | B NormRecall |
|---|---:|---:|---:|---:|---:|
| dat-dai | 19 | 0.420 | 0.389 | 0.864 | 0.719 |
