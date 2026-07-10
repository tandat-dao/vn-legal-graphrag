# KẾT QUẢ ĐÁNH GIÁ v2 — dữ liệu cho Chương 4

> **Chốt 2026-07-10.** Nguồn số liệu chính cho báo cáo. Mọi số dưới đây từ result JSON
> đã lưu trong `data/evaluation/` — có thể tính lại metric bất kỳ lúc nào ($0, không gọi API).

## 0. Thiết lập

| Mục | Giá trị |
|---|---|
| Test set | `test_set_v2.json` — **137 câu**, FREEZE (SHA256 `bd2c5eaf…f146`, tag `gt-v2-freeze`) |
| Hệ thống | GraphRAG **v2** (có Fix A: jurisdiction=None→mọi tỉnh, commit `3efd0e8`) |
| LLM | Gemini end-to-end (generator `gemini-2.5-pro`, planner `gemini-2.5-flash`); judge Claude Haiku cố định |
| Metric | F1 Khoản (nghiêm) / F1 Điều (routing) / Norm Recall; `cit_matches` |
| Lưu ý | mẻ đêm 09→10/07 dính Gemini 429 quota ở vài mẫu → đã lọc, chỉ dùng mẫu **0 lỗi 429** |

## 1. Headline + reproducibility (E0)

**N=3 (mean ± σ, mẫu sạch):**

| Hệ | F1 Khoản | NormR |
|---|---|---|
| **GraphRAG v2** | **0.578 ± 0.004** | 0.771 ± 0.016 |
| Baseline (naive RAG) | 0.435 ± 0.008 | — |

- graphrag 3 mẫu: 0.581 / 0.572 / 0.581 (`results_graphrag_{20260709-223945, 20260709-230729, 20260710-085236}.json`)
- baseline 3 mẫu: 0.433 / 0.427 / 0.446 (`results_baseline_{20260710-001154, -085236, -104109}.json`)
- σ cực nhỏ → **kết quả tái lập tốt** dù Gemini non-deterministic.
- *Footnote phương pháp:* mẫu graphrag #1 (223945) chạy với LLM-cache — phần lớn answer là replay generation gốc của run v1 (prompt identical vì retrieval không đổi ngoài 6 câu jur=None Fix A chạy tươi). Mỗi generation gốc vẫn là 1 lần rút mẫu độc lập từ phân phối answer của hệ v2 → hợp lệ làm 1/3 mẫu; 2 mẫu còn lại (230729, 085236) fresh hoàn toàn (`--no-llm-cache`).

**Significance (paired, per-question, 123 câu có GT — loại negative):**

| Metric | mean Δ (G−B) | 95% CI | Wilcoxon p | Win/Loss/Tie |
|---|---|---|---|---|
| **F1 Khoản** | **+0.156** | **[0.070, 0.242]** | **0.001 \*\*\*** | 62 / 32 / 29 |

→ **CI không chứa 0 ⇒ ưu thế GraphRAG có ý nghĩa thống kê ở mức 95%.** (bootstrap 10000 resample, seed=42)

## 2. Bậc thang baseline (E2a)

| Hệ | F1 Khoản | NormR | Vai trò |
|---|---|---|---|
| oracle (trần) | 0.858 | 0.955 | context = GT chunks |
| bm25 | 0.571 | 0.808 | lexical — mạnh bất ngờ |
| **GraphRAG v2** | **0.578** | 0.771 | hệ đề xuất |
| baseline (naive RAG) | 0.435 | — | đối thủ chính |
| closed-book | 0.102 | 0.102 | không retrieval → **chứng minh retrieval cần thiết** |

*(oracle/bm25/closed-book lấy từ mẻ v1 — Fix A không đụng các hệ này.)*

## 3. Double-dissociation (E1) — Δ F1 Khoản so với FULL (âm = cơ chế có ích)

FULL v2 per-gap: gap1 0.519 · gap2 0.515 · gap3 0.498 · gap4 0.638 (`results_graphrag_20260710-085236.json`)

| ablation | gap1 | gap2 | gap3 | gap4 | mục tiêu |
|---|---|---|---|---|---|
| no-theme | **−0.041** | +0.031 | +0.018 | +0.021 | gap1 ✓ |
| no-jurisdiction | −0.022 | **+0.182** | +0.019 | +0.005 | gap2 ❌ net-hại (xem Limitation) |
| no-implements | −0.056 | +0.054 | **−0.034** | −0.022 | gap3 ✓ |
| no-amends | −0.031 | +0.022 | +0.016 | **−0.018** | gap4 ✓ |
| no-temporal | −0.031 | +0.002 | +0.018 | +0.021 | gap4 ⚠️ yếu (amends gánh) |
| no-traversal | −0.019 | +0.067 | **−0.091** | **−0.130** | ✓✓ mạnh nhất |
| dense-only | −0.003 | +0.271 | −0.057 | −0.129 | tắt sạch KG |

- ✅ **Gap 3 + Gap 4**: traversal/implements/amends chứng minh cần thiết (no-traversal sập −0.091/−0.130 đúng gap3/4).
- ✅ **Gap 1**: no-theme −0.041.
- ⚠️ **Gap 2**: jurisdiction filter net-hại (+0.182) — xem §6.

## 4. Per-domain consistency (E2b, mảnh Gap 1)

| Domain | n | F1 | NormR |
|---|---|---|---|
| dat-dai | 61 | 0.617 | 0.790 |
| ho-tich | 39 | 0.580 | 0.744 |
| nuoi-con-nuoi | 29 | 0.392 | 0.810 |

σ(F1) liên-domain = **0.099**. dat-dai/ho-tich nhất quán; **nuoi-con-nuoi yếu hơn** (corpus nhỏ nhất, 4 Norm) — ghi Limitation.

## 5. Taxonomy lỗi (E3) — Fix A có tác dụng

| Loại | v1 | v2 |
|---|---|---|
| retrieval_fail | 32 | **21** (gap2: 24→**13** nhờ Fix A) |
| generation_fail | 72 | 76 (under-cite — Gemini-inherent) |
| over_cite | 161 | 169 (phần lớn GT-artifact — D-19) |
| negative_fail | 1 | 1 |

## 6. Fix A (cải tiến v2 hậu kiểm)

- Bug: `jurisdiction=None or "toan-quoc"` → câu underspecified loại sạch văn bản phí tỉnh → gap2 F1=0.
- Fix: None → mọi tỉnh. **gap2 0.454→0.517 (+0.063)**, jur=None 0.000→0.328, gap2 retrieval_fail 24→13.
- Sạch: 0 regress gap khác (RC full 137 xác nhận).
- Là **cải tiến hậu kiểm** so với v1 pre-registered (phát triển sau khi thấy v1, báo minh bạch).

## 7. Limitations & Negative results (đóng góp trung thực)

- **Gap 2 residual**: jurisdiction filter vẫn net-hại (+0.182) — phần jur-cụ-thể entangled (fee-doc component / Gemini noise), **không sửa được** bằng kiến trúc hiện tại → Future Work (finetune embedding cho biểu phí).
- **Under-citation**: recall bất biến qua 3 biến thể prompt → **Gemini-inherent + GT quá chi tiết**, prompt không sửa được.
- **bm25 ngang graphrag** trên tổng (lexical mạnh cho IR pháp luật) — ưu thế KG là **theo gap** (temporal/đa tầng), không phải trội đều.
- **3 negative result** đã thử-và-loại: (a) prompt thêm rule cite đủ — recall bất biến; (b) prompt gỡ rule gắt — recall bất biến; (c) temporal neo bản-cũ — trade-off regress Gap 4. Tất cả revert.

## 8. Tái lập
Mọi metric tính từ result JSON đã lưu (`--reuse-results` / `metrics.aggregate` / `expanded_eval` / `error_analysis`) — $0, không gọi API. Đổi tiêu chí đánh giá về sau: chỉ sửa code chấm + chạy lại phân tích.
