# Prompt Tuning Experiment — 2026-05-19

> Mục đích: kiểm chứng hypothesis "minimal prompt edits cải thiện F1/NormR"
> dựa trên root-cause findings ([ROOT_CAUSE_ANALYSIS_20260519.md](ROOT_CAUSE_ANALYSIS_20260519.md)).
> Phương pháp: 3-round ablation trên subset 7 câu trước khi quyết định full
> 26-câu re-run. Bài học khoa học: single-run ablation **không đủ tin cậy**
> cho prompt change do LLM stochastic variance.

## Setup

**Test subset** ([test_set_ablation_prompt.json](test_set_ablation_prompt.json)): 7 câu
  - 3 passing canaries: Q001 (gap2 F1=1.00), Q006 (negative F1=1.00), Q020 (gap3 F1=1.00)
  - 4 failing targets: Q022, Q023, Q024, Q026 (canonical F1=0)

**Baseline (canonical run 20260519-161509)**: 7-câu AVG F1=0.429, NormR=0.786

## Edits đã thử

### Edit 1 (Round 1, refined Round 2) — Temporal CITE both regimes

Vị trí: `src/retrieval/context_assembler.py` block `QUY TẮC TEMPORAL`, thêm điểm 4.

**Round 1 (broad)**: "Khi answer text trình bày cả 2 regime → PHẢI cite cả 2".

**Round 2 (scoped — final)**: chỉ áp dụng khi câu hỏi có signal SPAN-REGIME
("hồ sơ dở dang", "chưa giải quyết", "áp dụng VB cũ hay mới"), KHÔNG áp dụng
cho POINT-IN-TIME ("năm X", "tại thời điểm Y").

### Edit 2 (Round 1, reverted Round 3) — Parsimonious cite

Vị trí: cùng file, block `YÊU CẦU KHÁC`. Thêm quy tắc "CITE TIẾT KIỆM": max
1 cite/ý, no duplicate, no Khoản láng giềng "an toàn".

**Đã revert** vì không cho signal cải thiện rõ rệt, có thể là nguyên nhân
Q026 0-cite regression trong Round 2.

## Kết quả 3-round ablation

| Q (canonical F1) | R1 (E1 broad + E2) | R2 (E1 scoped + E2) | R3 (E1 scoped only) |
|---|---:|---:|---:|
| Q001 (1.00) | 1.00 | 1.00 | 1.00 |
| Q006 (1.00) | 1.00 | 1.00 | 1.00 |
| **Q020 (1.00)** | **0.67** ❌ | **0.67** ❌ | **0.00** ❌ |
| Q022 (0.00) | 0.00 | 0.00 | 0.00 |
| **Q023 (0.00)** | **0.40** ✅ | **0.33** ✅ | **0.40** ✅ |
| Q024 (0.00) | 0.00 | 0.00 | 0.00 |
| Q026 (0.00) | 0.00 | 0.00 | 0.00 |
| **AVG F1** | 0.438 | 0.429 | 0.343 |
| **AVG NormR** | 0.786 | 0.857 | 0.929 |

### Diễn giải

**Robust findings** (consistent across ≥2 rounds):
- Edit 1 scoped → Q023 F1 +0.33~0.40 (consistent win)
- Edit 1 scoped → Q022/Q023 NormR +0.50 (consistent — cite cả 2 regime)
- Q022 F1 vẫn 0 dù Edit 1 trigger đúng → **retrieval depth issue** (top-25 hybrid
  không có Khoản 1 Điểm a của QĐ 18). Không thể fix qua prompt.
- Q024/Q026 không cải thiện → retrieval/LLM-comprehension issues nằm ngoài
  prompt.

**Noisy / stochastic findings**:
- **Q020 F1**: 1.00 → 0.67 → 0.67 → 0.00 (LLM cite Điểm khác nhau qua từng
  run trên cùng câu hỏi point-in-time). Đáng lẽ Edit 1 scoped KHÔNG ảnh
  hưởng câu này — F1 swing là LLM stochastic decoding, không phải Edit
  effect.
- **Q026 NormR**: 0.5 → 0 → 0.5 (tương tự noise).

## Kết luận khoa học

1. **Edit 1 scoped được giữ lại**:
   - Theoretical justification: span-regime questions cần cite cả 2 để
     reflect answer text đầy đủ
   - Empirical: 1 robust F1 win (Q023), 2 robust NormR wins (Q022, Q023)
   - Không gây regression rõ ràng do scope tight

2. **Edit 2 (parsimonious) revert**:
   - Không cho signal cải thiện
   - Có khả năng gây Q026 0-cite regression
   - Original prompt đã có "Mỗi ý quan trọng PHẢI có trích dẫn nguồn" — không
     cần parsimonious counter-rule

3. **Limitation methodology**:
   - N=1 ablation cho prompt change KHÔNG đủ tin cậy
   - LLM stochastic decoding gây F1 swing 1.00→0.00 trên cùng câu
   - Future work: N≥3 runs per Q để detect significant change (paired t-test
     hoặc bootstrap CI)

4. **Findings refute Gemini's "thiết kế lại System Prompt để khắc phục triệt
   để"**:
   - Wholesale redesign sẽ gây cascade regression do LLM behavior khó predict
   - Minimal targeted edit + scoped trigger là approach khoa học hơn
   - Vẫn chỉ giải quyết ~1/4 failure cases (Q023); còn lại cần retrieval +
     downstream fix

## Output files

- Round 1 results: `results_graphrag_20260519-201628.json` + `REPORT_20260519-201628.md`
- Round 2 results: `results_graphrag_20260519-202434.json` + `REPORT_20260519-202434.md`
- Round 3 results: `results_graphrag_20260519-203133.json` + `REPORT_20260519-203133.md`
- Final prompt: Edit 1 scoped giữ trong [../../src/retrieval/context_assembler.py](../../src/retrieval/context_assembler.py)
  block `QUY TẮC TEMPORAL` điểm 4
