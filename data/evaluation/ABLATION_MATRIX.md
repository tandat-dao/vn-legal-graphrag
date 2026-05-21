# Ablation Matrix — Cumulative Fix Impact (26 câu Đất đai)

Bảng tổng hợp impact của từng fix layer, đo trên cùng test set (`test_set_dat_dai.json`), cùng embedding (BGE-M3), cùng LLM (Claude Sonnet 4.6), cùng eval-mode (force_jurisdiction + bypass_completeness). **Chỉ khác retrieval/parsing logic**.

**Reproducibility note**: v2.6 final config có N=3 runs cùng code state với `--no-llm-cache` để measure variance. Các config trước (v2.3-v2.5) là N=1 — variance không đo nhưng cùng order of magnitude (xem REPRODUCIBILITY_REPORT_20260520.md).

## Aggregate metrics

| # | Configuration | F1 Khoản | F1 Điều | NormR | Latency (s) | Neg. correct | Δ vs Baseline | Δ vs Prev |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Baseline (Naive RAG) | **0.295** | 0.295 | 0.699 | 18.29 | 100% | — | — |
| 2 | v2.3 GraphRAG canonical | **0.440** | 0.453 | 0.891 | 2.85 | 100% | +49.1% | +0.145 |
| 3 | + parse_citations dedupe | **0.461** | 0.476 | 0.891 | 2.85 | 100% | +56.3% | +0.021 |
| 4 | + Prompt TEMPORAL #4 | **0.466** | 0.483 | 0.869 | 22.53 | 100% | +58.0% | +0.005 |
| 5 | + Dense Floor (Pass 0) | **0.485** | 0.519 | 0.917 | 23.03 | 100% | +64.6% | +0.019 |
| 6 | + Structured Cite (Pass -1) [N=3 mean] | **0.539** ±0.021 | 0.567 | 0.931 | 22.92 | 100% | +82.8% | +0.054 |

**Headline**:
- Baseline → v2.6 GraphRAG: F1 **0.295 → 0.539** (+82.8%)
- v2.3 canonical → v2.6 (4 fix layers cumulative): F1 **0.440 → 0.539** (+22.6%)

> **Latency note**: v2.3 canonical 2.85s là **cache artifact** (cache hit từ debugging session). v2.4+ runs với `--no-llm-cache` cho số real ~22-28s. Khi viết thesis dùng số v2.4+ làm honest latency.

## Per-Gap F1 Khoản

| Configuration | gap1 (n) | gap2 (n) | gap3 (n) | negative (n) |
|---|---:|---:|---:|---:|
| _(n câu)_ | _3_ | _6_ | _15_ | _2_ |
| Baseline (Naive RAG) | 0.194 | 0.485 | 0.145 | 1.000 |
| v2.3 GraphRAG canonical | 0.350 | 0.543 | 0.341 | 1.000 |
| + parse_citations dedupe | 0.350 | 0.543 | 0.378 | 1.000 |
| + Prompt TEMPORAL #4 | 0.383 | 0.632 | 0.345 | 1.000 |
| + Dense Floor (Pass 0) | 0.362 | 0.599 | 0.396 | 1.000 |
| + Structured Cite (Pass -1) [N=3 mean] | 0.343 | 0.618 | 0.485 | 1.000 |