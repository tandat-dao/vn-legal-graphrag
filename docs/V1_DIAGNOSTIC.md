# Chẩn đoán v1 (mẻ pre-registered, Gemini, 137 câu, N=1)

> Mẻ v1 = kết quả pre-registered honest (GT freeze `gt-v2-freeze`). Dùng để **chẩn đoán** → thiết kế v2.
> KHÔNG tune trên bộ này. v2 sẽ báo là "cải tiến hậu kiểm".

## 1. Bậc thang E2a (F1 Khoản)

| Hệ | F1 Khoản | F1 Điều | NormR |
|---|---|---|---|
| oracle (trần) | 0.858 | 0.858 | 0.955 |
| bm25 | 0.571 | 0.593 | 0.808 |
| **graphrag** | **0.567** | **0.587** | **0.743** |
| baseline (naive RAG) | 0.438 | 0.457 | 0.577 |
| closed-book | 0.102 | 0.102 | 0.102 |

- ✅ graphrag > naive RAG (+0.129 F1). closed-book ≈0 → **retrieval là cần thiết**.
- ⚠️ bm25 (lexical) ngang graphrag trên tổng. Trần oracle 0.858 → **dư địa lớn**.

## 2. Double-dissociation (Δ F1 Khoản so với FULL; âm = cơ chế có ích)

| ablation | gap1 | gap2 | gap3 | gap4 | mục tiêu |
|---|---|---|---|---|---|
| no-theme | −0.010 | +0.029 | 0.000 | +0.010 | gap1 ❌ vô hiệu |
| no-jurisdiction | +0.009 | **+0.243** | +0.001 | −0.006 | gap2 ❌ **phản tác dụng** |
| no-implements | −0.025 | +0.048 | **−0.052** | −0.033 | gap3 ✅ |
| no-amends | 0.000 | −0.002 | −0.003 | **−0.029** | gap4 ✅ |
| no-temporal | 0.000 | 0.000 | 0.000 | +0.009 | gap4 ⚠️ yếu (amends gánh) |
| no-traversal | +0.012 | +0.052 | **−0.110** | **−0.141** | tổng ✅ mạnh |

- ✅ **Gap 3 + Gap 4 ĐỨNG:** traversal (implements/amends) chứng minh cần thiết; no-traversal sập mạnh đúng gap3/gap4.
- ❌ **Gap 1 + Gap 2 HỎNG:** theme vô hiệu; jurisdiction phản tác dụng (tắt → gap2 +0.243).

## 3. E3 taxonomy lỗi (graphrag)

| Loại | Tổng | Nặng ở gap |
|---|---|---|
| over_cite | 161 (74 câu) | gap3(53), gap1(41), gap2(40) — **ambiguous, có thể GT-artifact (D-19)** |
| generation_fail (có context, không cite) | 72 | gap3(32), gap1(22) |
| retrieval_fail (không có trong context) | 32 | **gap2(24)** |
| negative_fail | 1 | — |

**Suy ra bản chất từng gap:**
- **Gap 2 = lỗi RETRIEVAL** (retrieval_fail 24/32 dồn ở gap2 + jurisdiction backfire) → sửa bộ lọc địa phương.
- **Gap 1 & Gap 3 = lỗi GENERATION** (retrieval OK, retrieval_fail chỉ 1; generation_fail cao) → hệ lấy đúng context nhưng **under-cite** → sửa prompt/generation.
- **over_cite** = phần lớn nghi GT-artifact → [A] soi mẫu trước, KHÔNG fix mù.

## 4. Danh sách fix v2 (ưu tiên)

1. **[Retrieval] Jurisdiction filter over-filter** — nguyên nhân Gap 2 sập. Bằng chứng kép: no-jurisdiction +0.243 + retrieval_fail gap2=24. **Ưu tiên #1, high-confidence.**
2. **[Generation] Under-citation** — generation_fail 72 (gap3/gap1): context có nhưng không cite đủ khoản. Sửa prompt (một phần là đặc tính Gemini under-cite, D-24). **Ưu tiên #2.**
3. **[Điều tra] over-cite 161** — xác định thật/GT-artifact trước khi coi là lỗi. **Không fix mù.**
4. **[Xem lại] Theme mechanism** — ablation cho thấy gần như vô hiệu; gap1 thực chất là lỗi generation, không phải theme. Cân nhắc vai trò theme filter.

## 5. Kỷ luật cho v2
- Fix tổng quát (không dò từng câu). Dev trên **subset gap2** (retrieval) + subset gap1/gap3 (generation).
- Khi khá hơn → chạy full 137 + N=3 → headline. Báo minh bạch "hậu kiểm so với v1".
- v1 giữ nguyên làm đường nền pre-registered.
