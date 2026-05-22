# Ablation Matrix — Cumulative Fix Impact (26 câu Đất đai)

Bảng tổng hợp impact của từng fix layer, đo trên cùng test set (`test_set_dat_dai.json`), cùng embedding (BGE-M3), cùng LLM (Claude Sonnet 4.6), cùng eval-mode (force_jurisdiction + bypass_completeness). **Chỉ khác retrieval/parsing logic**.

**Reproducibility note**: v2.6 final config có N=3 runs cùng code state với `--no-llm-cache` để measure variance. Các config trước (v2.3-v2.5) là N=1 — variance không đo nhưng cùng order of magnitude (xem REPRODUCIBILITY_REPORT_20260520.md).

**v2.8 note (2026-05-21)**: Hai thay đổi label-only (KHÔNG re-run pipeline):
1. Tách Gap 4 (đa phiên bản) từ Gap 3. 7 câu temporal (Q020-Q026) thuộc gap4: Q020-Q023, Q025, Q026 + **Q024** (bản chất point-in-time CTV retrieval, chỉ trích 1 tier nên không thoả ràng buộc gap3 ≥2 tier).
2. Baseline + GraphRAG re-aggregate F1 từ `pred_citations + GT v2.8 hiện tại` qua `--reuse-results`. Baseline tăng nhẹ (0.295 → 0.333) vì Q026 GT đã được rút gọn còn 1 citation (commit 705a02c) — baseline trích đúng citation từ refusal answer (xem §"Q026 Evaluation Artifact" trong CHAPTER_4_EXPERIMENTS).

## Aggregate metrics

| # | Configuration | F1 Khoản | F1 Điều | NormR | Latency (s) | Neg. correct | Δ vs Baseline | Δ vs Prev |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Baseline (Naive RAG) | **0.333** | 0.333 | 0.718 | 18.29 | 100% | — | — |
| 2 | v2.3 GraphRAG canonical † | 0.440 | 0.453 | 0.891 | 2.85 | 100% | +32.1% | +0.107 |
| 3 | + parse_citations dedupe † | 0.461 | 0.476 | 0.891 | 2.85 | 100% | +38.4% | +0.021 |
| 4 | + Prompt TEMPORAL #4 † | 0.466 | 0.483 | 0.869 | 22.53 | 100% | +39.9% | +0.005 |
| 5 | + Dense Floor (Pass 0) † | 0.485 | 0.519 | 0.917 | 23.03 | 100% | +45.6% | +0.019 |
| 6 | + Structured Cite (Pass -1) [N=3 mean] | **0.539** ±0.021 | 0.567 ±0.032 | 0.931 ±0.005 | 22.92 ±0.12 | 100% | **+61.8%** | +0.054 |

† Các config v2.3-v2.5 là N=1 và F1 chưa re-aggregate với GT v2.8 hiện tại. Δ vs Baseline cho các row này so với baseline v2.8 (0.333) — order-of-magnitude vẫn đúng nhưng số chính xác cần re-run nếu cần benchmark nghiêm ngặt. Row 6 (current state) là N=3 mean đã re-aggregate.

**Headline (v2.8)**:
- Baseline → v2.6 GraphRAG: F1 **0.333 → 0.539** (+61.8%)
- v2.3 canonical → v2.6 (4 fix layers cumulative): F1 **0.440 → 0.539** (+22.6%)

> **Latency note**: v2.3 canonical 2.85s là **cache artifact** (cache hit từ debugging session). v2.4+ runs với `--no-llm-cache` cho số real ~22-28s. Khi viết thesis dùng số v2.4+ làm honest latency.

## Per-Gap F1 Khoản (v2.8 — 4 gap, current GT, Q024 ∈ gap4)

Phân bổ: gap1=3, gap2=6, gap3=8, gap4=7, negative=2 (total=26).

| Configuration | gap1 (n=3) | gap2 (n=6) | gap3 (n=8) | gap4 (n=7) | negative (n=2) |
|---|---:|---:|---:|---:|---:|
| Baseline (Naive RAG) | 0.194 | 0.485 | 0.209 | 0.214 | 1.000 |
| + Structured Cite (Pass -1) [N=3 mean] | **0.343** ±0.013 | **0.618** ±0.041 | **0.412** ±0.013 | **0.568** ±0.031 | 1.000 |
| Δ % vs Baseline | +76.8% | +27.4% | +97.1% | +165.4% | tied |

(Các intermediate config v2.3-v2.5 omitted ở per-gap table — cần re-run để re-aggregate với GT v2.8 + nhãn gap4 mới.)

### Phân tích tác động per-gap (v2.8)

**Gap 1 (đa lĩnh vực, n=3)**: Baseline → v2.6: 0.194 → 0.343 (+76.8%). KG theme filter giúp định tuyến đúng văn bản thuộc Đất đai. Trong scope hiện tại chỉ 1 theme nên advantage không có cơ hội thể hiện đầy đủ — sẽ rõ hơn khi mở rộng sang Hộ tịch + Nuôi con nuôi.

**Gap 2 (đa địa phương, n=6)**: Baseline → v2.6: 0.485 → 0.618 (+27.4%). Baseline còn relatively strong (0.485) do keyword địa danh "TP.HCM"/"Đồng Nai" đủ specific để dense embedding cũng routing được. KG advantage hẹp ở gap này.

**Gap 3 (đa tầng văn bản, n=8)**: Baseline → v2.6: 0.209 → 0.412 (+97.1%). KG traversal `[:IMPLEMENTS|AMENDS*1..4]` cho phép retrieve toàn bộ chuỗi Luật → NĐ → TT → QĐ khi câu hỏi cần tổng hợp đa tầng. Baseline (chunked 512 chars) không có signal về tier → recall thấp.

**Gap 4 (đa phiên bản, n=7)**: Baseline → v2.6: **0.214 → 0.568 (+165.4%)**. Differentiator mạnh nhất giữa GraphRAG và Baseline (2.65×). Architectural components đóng góp:
- **CTV versioning** (valid_from/valid_to): cho phép point-in-time retrieval (Q020-Q024)
- **`[:AMENDS]` edge**: chains amending norms (Q025-Q026)
- **`[:AMENDED_BY]` edge**: surfaces amendment metadata cho Component bị sửa
- **TemporalIntent extraction** (query_planner): map "Năm 2024", "trước 01/07/2025" → time filter

Baseline F1 0.214 (n=7) bao gồm **Q026 evaluation artifact** (citation match từ refusal answer, F1=1.0). Loại bỏ artifact: baseline gap4 thực = (1.5 − 1.0)/7 = **0.071** → improvement thực = **(0.568 − 0.071)/0.071 = +700%**. Xem §"Q026 Evaluation Artifact" trong CHAPTER_4_EXPERIMENTS.

> **Interpretation**: Gap 4 là **differentiator mạnh nhất** giữa GraphRAG và Baseline (+165% cap-based, +700% artifact-adjusted), vượt Gap 3 (+97%), Gap 1 (+77%), và Gap 2 (+27%). Temporal versioning là đóng góp kiến trúc quan trọng nhất của KG — năng lực mà flat chunked RAG không thể replicate.
