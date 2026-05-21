# Comparison: results_graphrag_20260519-212405.json → results_graphrag_20260520-merged_pass-neg1.json

**System:** graphrag  
**N câu chung:** 26  
**Test set:** `data/evaluation/test_set_dat_dai.json`

## Aggregate

| Metric | Old | New | Δ |
|---|---:|---:|---:|
| F1 Khoản | 0.485 | 0.549 | +0.064 |
| F1 Điều | 0.519 | 0.564 | +0.044 |
| Norm Recall | 0.917 | 0.917 | +0.000 |
| Latency mean (s) | 23.03 | 28.48 | +5.45 |

## Improvements (5 câu, ΔF1 > 0.05)

| ID | gap | old F1 | new F1 | ΔF1 | old NR | new NR | ΔNR | preds |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Q026 | gap3 | 0.00 | 1.00 | **+1.00** | 0.50 | 1.00 | +0.50 | 2→1 |
| Q019 | gap3 | 0.00 | 0.29 | **+0.29** | 0.25 | 0.25 | +0.00 | 5→2 |
| Q008 | gap2 | 0.57 | 0.86 | **+0.29** | 1.00 | 1.00 | +0.00 | 4→4 |
| Q025 | gap3 | 0.50 | 0.67 | **+0.17** | 1.00 | 1.00 | +0.00 | 3→2 |
| Q009 | gap2 | 0.33 | 0.40 | **+0.07** | 1.00 | 1.00 | +0.00 | 5→4 |

## Regressions (1 câu, ΔF1 < -0.05)

| ID | gap | old F1 | new F1 | ΔF1 | old NR | new NR | ΔNR | preds |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Q017 | gap3 | 0.50 | 0.33 | **-0.17** | 0.75 | 0.75 | +0.00 | 6→6 |

## Unchanged (20 câu, |ΔF1| ≤ 0.05)

_(IDs: Q001, Q002, Q003, Q004, Q005, Q006, Q007, Q010, Q011, Q012, Q013, Q014, Q015, Q016, Q018, Q020, Q021, Q022, Q023, Q024)_
