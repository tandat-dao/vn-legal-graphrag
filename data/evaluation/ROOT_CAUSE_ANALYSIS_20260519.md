# Root-cause Analysis — F1 Gap 0.89→0.44 (canonical run 20260519-161509)

> Phân tích thực nghiệm trên 24 câu non-negative để xác định nguyên nhân khoảng cách
> giữa Norm Recall (0.891) và F1 Khoản (0.440). Mục đích: tránh quyết định fix
> dựa trên suy đoán, đảm bảo phương pháp luận khoa học cho luận văn.

## Bối cảnh

- Ý kiến A (Claude ban đầu): "F1 thấp do retrieval pull đúng Norm nhưng sai Khoản" → đề xuất regex `Khoản X Điều Y` → LCCID filter.
- Ý kiến B (Gemini phản biện): "Thuần do giới hạn chunking" → ghi vào Limitations, không fix.

Cả hai đều là **suy đoán không có dữ liệu**. Phần này phản bác cả hai bằng đo lường.

## Phương pháp

Mỗi pred citation được phân loại vào 1 trong các nguyên nhân (multi-label cho phép):

| Nhãn | Định nghĩa |
|---|---|
| H2_dieu | Pred đúng `van_ban` (Norm) nhưng sai `dieu` so với mọi GT của cùng `van_ban` |
| H2_khoan | Pred đúng `van_ban` + `dieu` nhưng sai `khoan` |
| H3_excess | Pred có nhiều citation hơn GT (over-citing: `max(0, pred_count - gt_count)`) |
| H4_artifact | GT có `khoan=None` (wildcard) và pred có nhiều Khoản cùng Điều → metric greedy 1-1 chỉ match được 1 |
| H5 | Citation parser sinh giá trị không hợp lệ: `_default`, Roman (I,II,III), hoặc Phụ lục-path |

## Kết quả (24 câu non-negative)

| Nhãn | Tổng | Mức độ |
|---|---:|---|
| **H3 (LLM over-cite)** | **47 excess** | **Dominant** |
| **H2_dieu (sai Điều của đúng Norm)** | **20** | Lớn |
| **H4 (metric artifact)** | 9 cases | Trung bình |
| **H5 (parser/Phụ lục)** | 8 instances / 4 cases | Khu trú |
| **H2_khoan (sai Khoản của đúng Điều)** | **4** | **Nhỏ** ← đây là cause Claude giả thuyết |

## Diễn giải

### 1. "Regex Khoản+Điều" (Claude) — REFUTED

H2_khoan chỉ 4 instances. Ngay cả fix hoàn hảo cũng chỉ cải thiện 4/84 ≈ 5% issues. Không phải dominant cause.

### 2. "Thuần do chunking" (Gemini) — REFUTED

Nếu chunking là nguyên nhân duy nhất, H2_khoan phải lớn (chunk lớn → khó target Khoản). H2_khoan chỉ 4. Chunking góp phần, nhưng không phải nguyên nhân chính.

### 3. Nguyên nhân thực sự

**A. LLM over-cite (H3=47)** — biggest precision killer. LLM cite trung bình ~2 citation dư mỗi câu. Q025: cite Điều 116 K5 **hai lần liên tiếp** trong cùng answer.

**B. Retrieval Điều-level routing (H2_dieu=20)** — Hybrid search rank chunks theo embedding similarity với toàn câu hỏi, không có signal mạnh để chọn đúng Điều khi câu hỏi không nêu Điều cụ thể (Q024: "căn cứ cho phép CMĐSDĐ" → pulled Điều 44/227/123 thay vì Điều 116).

**C. Phụ lục citation format mismatch (H5=8)** — Data files NQ HĐND tỉnh và một số QĐ có cấu trúc Phụ lục/Mục thay vì Điều. LLM cite `[Phụ lục I, ...]` hoặc `[Phụ lục, Khoản 2, ...]` → parser sinh `dieu='_default'` hoặc `dieu='I'`. GT trong test set viết theo cú pháp `dieu='1'` Arabic. **Đây là format mismatch chứ không hẳn parser bug** — cả hai bên đều "đúng theo logic riêng" nhưng không align.

**D. Temporal layer downstream issue (Q022, Q023)** — Stage 1 retrieve ĐÚNG cả 2 regime (verified empirically: QĐ 18 rank #1 với score 0.699 cho Q022; Luật 2013 rank #1 với score 0.741 cho Q023). Nhưng final pred chỉ có new regime. Bottleneck nằm ở Stage 2/Stage 3/LLM, **không phải temporal logic cơ bản** như Gemini suspect.

### 4. Đề xuất fix dựa trên evidence (priority desc)

| Fix | Impact ước tính | Risk | Cần ablation? |
|---|---|---|---|
| Dedupe trong `parse_citations` (Q025-type duplicates) | Nhỏ-Trung bình, ~5-10 instances | Cực thấp | Không (idempotent) |
| Prompt rule "cite parsimoniously, 1 cite per claim" | **Trung bình-Lớn**, có thể giảm 30-50% H3 | Trung bình (LLM behavior change) | **Có — full eval re-run** |
| Re-rank Điều theo Q-context (boost Điều mentioned) | Lớn cho H2_dieu | Cao | **Có** |
| Phụ lục citation: align GT vs parser format | 8 instances | Thấp nếu chỉ realign GT; cao nếu sửa parser | Tùy hướng chọn |
| Stage 2/3 debug Q022/Q023 (instrument context dump) | Temporal cases | Thấp (instrumentation only) | Không |

### 5. KHÔNG ưu tiên (do evidence không support)

- ~~Regex `Khoản X Điều Y` → LCCID filter~~ (H2_khoan = 4 instances, low impact, high overfit risk)
- ~~Báo cáo "Limitations: chunking" không kèm fix~~ (chunking không phải dominant — báo cáo sẽ misleading)

## Bài học phương pháp luận

- **Đừng act trên suy đoán**. Cả "regex sẽ lift 0.44→0.6+" lẫn "thuần do chunking" đều là claim không có evidence.
- **Phân loại nguyên nhân là thinking tool quan trọng hơn aggregate F1**. Aggregate giấu pattern; per-instance classification phơi pattern ra.
- **Lệch giữa system data structure và test set GT** là một category bị bỏ qua hoàn toàn trong cả 2 phân tích ban đầu (H5 Phụ lục mismatch).

---

## Phụ lục — Instrumentation downstream (20260519-2000)

Sau khi root-cause analysis xác định "Stage 1 OK" cho Q022/Q023, chạy instrumentation
([src/evaluation/instrument_retrieval.py](../../src/evaluation/instrument_retrieval.py))
để dump Stage 2 + Stage 3 (hybrid_search) cho 4 failure cases. Output: 
[RETRIEVAL_DEBUG_20260519-200009/SUMMARY.md](RETRIEVAL_DEBUG_20260519-200009/SUMMARY.md).

### Kết quả định vị bottleneck per-câu

| Q | Top-25 hybrid có expected component? | Pred citation đúng? | Bottleneck thực sự |
|---|---|---|---|
| Q022 | ✅ QĐ 18 rank #5 + QĐ 69 rank #2 (cả 2 regime) | ❌ chỉ cite QĐ 69 mới | **LLM behavior** — bỏ qua VB cũ trong context |
| Q023 | ✅ Luật 2013 Điều 100 rank #8 (đúng GT) | ❌ chỉ cite Luật 2024 | **LLM behavior** — span-regime ignored |
| Q024 | ❌ Điều 116 KHÔNG có trong top-15 | ❌ cite Điều 44/227/123 | **Hybrid retrieval** — legal terminology mismatch |
| Q026 | ✅ NĐ 49 Điều 13 K1 rank #5/6 | ❌ cite Khoản 11/12 | **LLM behavior** — wrong Khoản of right Điều |

### Diễn giải

**3/4 cases là LLM behavior**, không phải retrieval. Context có đủ thông tin, LLM
không cite đúng. Cụ thể:

- **Q022/Q023 (temporal span-regime)**: context có CẢ regime cũ + mới. LLM chỉ cite
  regime mới trong final answer — mặc dù answer text có nhắc đến cả hai. Đây là
  **citation behavior bug**, không phải retrieval bug.
- **Q026 (AMENDED_BY)**: context có đúng Điều 13 Khoản 1 (rank #5-6 trong top-25). LLM
  cite Khoản 11/12 — có thể vì Khoản 11/12 cũng được sửa bởi NĐ 49 và xuất hiện
  trong cùng câu trả lời.

**Q024 (legal terminology mismatch)**: câu hỏi "căn cứ cho phép chuyển mục đích sử
dụng đất" semantic-match Điều 44 NĐ 102 ("Căn cứ giao đất, cho thuê đất, cho phép
chuyển mục đích...") tốt hơn Điều 116 Luật ĐĐ 2024. Đây không phải chunking limit —
là vấn đề **embedding model không phân biệt được tier 1 (Luật) vs tier 2 (NĐ) khi
title quá similar**.

### Reframe ưu tiên fix (sau instrumentation)

| Vấn đề | Số case ảnh hưởng (est.) | Approach |
|---|---|---|
| **LLM span-regime cite** (Q022, Q023) | 4-8 temporal cases | Prompt rule: "khi context có 2 regime, cite cả 2 với note hiệu lực" |
| **LLM over-cite redundant Khoản** (Q026 + H3 phần lớn) | ~15-20 cases | Prompt rule: "cite Khoản cụ thể nhất, không cite redundant" |
| **Embedding tier mismatch** (Q024) | ~3-5 cases | Add tier prior trong hybrid scoring khi câu hỏi mention "Luật"/"Nghị định" |
| ~~Regex Khoản+Điều~~ | 0 (đã refute bởi data) | — |
| ~~Chunking limit~~ | 0 (đã refute bởi data) | — |

→ **Prompt tuning là priority #1** với impact tiềm năng lớn nhất (10+ cases). Risk
trung bình → cần ablation full eval re-run. Đây là kết luận khác hoàn toàn so với
hypothesis ban đầu của cả tôi và Gemini.
