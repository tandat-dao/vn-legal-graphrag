# Expanded Evaluation Report (Tier 0, $0 offline)

- **GraphRAG run**: `20260528-142757` — N=26
- **Baseline run**: `20260519-204426` — N=26
- Test set: `data/evaluation/test_set_dat_dai.json`
- Bootstrap: 10000 resamples, seed=42 (deterministic)

## 1. Overall comparison

| Metric | GraphRAG | Baseline | Δ (G−B) |
|---|---:|---:|---:|
| Citation F1 — Khoản (strict) | 0.517 | 0.236 | 0.281 |
| Citation Precision — Khoản | 0.453 | 0.205 | 0.248 |
| Citation Recall — Khoản | 0.717 | 0.383 | 0.333 |
| Citation F1 — Điều (routing) | 0.534 | 0.236 | 0.298 |
| Norm-level Recall | 0.931 | 0.674 | 0.257 |
| Faithfulness (faithful_rate) | 0.992 | N/A | N/A |
| Latency mean (s) | 19.292 | 18.290 | 1.003 |
| Latency p95 (s) | 35.680 | 31.120 | 4.560 |

> Citation metrics tính trên câu có GT (loại negative). Faithfulness chỉ có ở GraphRAG run.

## 2. Statistical significance (paired, per-question)

Paired bootstrap 95% CI của mean(Δ) + Wilcoxon signed-rank (two-sided). CI không chứa 0 ⇒ khác biệt vững ở mức 95%.

| Metric | n | mean Δ | 95% CI | Wilcoxon p | sig | Win/Loss/Tie |
|---|---:|---:|---|---:|:--:|---:|
| F1 Khoản | 24 | 0.281 | [0.154, 0.417] | 0.001 | *** | 18/3/3 |
| F1 Điều | 24 | 0.298 | [0.174, 0.430] | 0.000 | *** | 18/3/3 |
| Norm Recall | 24 | 0.257 | [0.108, 0.424] | 0.007 | ** | 10/1/13 |

> Ký hiệu: `***` p<0.001, `**` p<0.01, `*` p<0.05, `ns` không ý nghĩa.

## 3. Citation behavior (over/under-citation)

| Metric | GraphRAG | Baseline |
|---|---:|---:|
| Mean predicted citations / Q | 3.708 | 3.583 |
| Mean GT citations / Q | 2.333 | 2.375 |
| Mean precision | 0.453 | 0.205 |
| Mean recall | 0.717 | 0.383 |
| Recall − Precision gap | 0.263 | 0.178 |
| Over-citation rate (% Q with unmatched preds) | 0.792 | 0.958 |

> P–R gap > 0 ⇒ recall vượt precision (xu hướng cite thừa). Over-citation rate cao ⇒ nhiều câu kéo citation ngoài GT.

## 4. Per-gap breakdown (F1 Khoản)

| Gap | N | G F1(Kh) | B F1(Kh) | Δ | G F1(Đ) | G NormR |
|---|---:|---:|---:|---:|---:|---:|
| Gap1 đa lĩnh vực | 3 | 0.328 | 0.194 | 0.133 | 0.328 | 1.000 |
| Gap2 địa phương | 6 | 0.726 | 0.485 | 0.241 | 0.726 | 1.000 |
| Gap3 đa tầng | 8 | 0.364 | 0.209 | 0.155 | 0.415 | 0.854 |
| Gap4 phiên bản | 7 | 0.594 | 0.071 | 0.522 | 0.594 | 0.929 |
| Negative | 2 | 1.000 | 1.000 | 0.000 | 1.000 | 1.000 |

## 5. Per-jurisdiction breakdown (Gap 2 focus)

| Jurisdiction | N | G F1(Kh) | B F1(Kh) | Δ | G NormR | B NormR |
|---|---:|---:|---:|---:|---:|---:|
| dong-nai | 3 | 0.786 | 0.407 | 0.379 | 1.000 | 1.000 |
| multi-juris | 1 | 0.200 | 0.444 | -0.244 | 1.000 | 0.500 |
| toan-quoc | 16 | 0.517 | 0.238 | 0.279 | 0.927 | 0.667 |
| tp-hcm | 6 | 0.595 | 0.365 | 0.230 | 0.917 | 0.667 |

## 6. Interpretation

- **Headline**: GraphRAG F1 Khoản 0.517 vs baseline 0.236 (Δ 0.281), 95% CI [0.154, 0.417] → **statistically significant**; win/loss/tie = 18/3/3.
- **Citation behavior**: baseline over-citation rate 0.958 vs GraphRAG 0.792; GraphRAG mean preds 3.708 vs baseline 3.583.
- **Per-gap**: strongest = Gap2 địa phương (F1 0.726); weakest = Gap1 đa lĩnh vực (F1 0.328).
