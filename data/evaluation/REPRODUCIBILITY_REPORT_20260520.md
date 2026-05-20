# Reproducibility Report — N=3 runs same code state

Mục đích: đo variance của metrics across N runs cùng code state + --no-llm-cache → claim 'F1 = mean ± σ' thay vì single-run.

## Per-run aggregate

| Run | F1 Khoản | F1 Điều | NormR | Latency (s) | Faith existence | Faith support | Faith faithful |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1. `results_graphrag_20260520-205113.json` | 0.554 | 0.588 | 0.926 | 22.79 | 0.891 | 0.951 | 0.843 |
| 2. `results_graphrag_20260520-210859.json` | 0.548 | 0.583 | 0.936 | 22.95 | 0.979 | 1.000 | 0.979 |
| 3. `results_graphrag_20260520-211930.json` | 0.515 | 0.530 | 0.929 | 23.02 | 0.924 | 1.000 | 0.924 |

## Aggregate (mean ± σ, 95% CI)

| Metric | Mean | σ | Min | Max | 95% CI |
|---|---:|---:|---:|---:|---|
| F1 Khoản | **0.539** | 0.021 | 0.515 | 0.554 | [0.515, 0.563] |
| F1 Điều | **0.567** | 0.032 | 0.530 | 0.588 | [0.530, 0.603] |
| Norm Recall | **0.931** | 0.005 | 0.926 | 0.936 | [0.925, 0.936] |
| Latency (s) | **22.921** | 0.117 | 22.792 | 23.021 | [22.789, 23.053] |
| Faith existence | **0.932** | 0.045 | 0.891 | 0.979 | [0.881, 0.982] |
| Faith support | **0.984** | 0.028 | 0.951 | 1.000 | [0.951, 1.016] |
| Faith faithful | **0.916** | 0.069 | 0.843 | 0.979 | [0.838, 0.993] |

## Per-question F1 variance (top 10 σ desc)

| ID | Mean F1 | σ | Min | Max | Values |
|---|---:|---:|---:|---:|---|
| Q008 | 0.583 | **0.220** | 0.333 | 0.750 | 0.67, 0.75, 0.33 |
| Q020 | 0.778 | **0.192** | 0.667 | 1.000 | 1.00, 0.67, 0.67 |
| Q024 | 0.778 | **0.192** | 0.667 | 1.000 | 0.67, 1.00, 0.67 |
| Q019 | 0.190 | **0.165** | 0.000 | 0.286 | 0.29, 0.29, 0.00 |
| Q013 | 0.624 | **0.157** | 0.500 | 0.800 | 0.80, 0.57, 0.50 |
| Q018 | 0.148 | **0.128** | 0.000 | 0.222 | 0.00, 0.22, 0.22 |
| Q011 | 0.730 | **0.110** | 0.667 | 0.857 | 0.67, 0.67, 0.86 |
| Q010 | 0.389 | **0.096** | 0.333 | 0.500 | 0.50, 0.33, 0.33 |
| Q017 | 0.455 | **0.079** | 0.364 | 0.500 | 0.50, 0.36, 0.50 |
| Q021 | 0.524 | **0.041** | 0.500 | 0.571 | 0.50, 0.57, 0.50 |

**Interpretation**:
- σ thấp ≈ 0 → câu deterministic (LLM stochastic không ảnh hưởng)
- σ cao → câu có F1 swing across runs → cần cẩn thận khi attribute regression cho code change vs LLM noise
