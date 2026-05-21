# Retrieval Limitations — 2026-05-20

> Document các giới hạn retrieval đã được xác định qua thực nghiệm — dùng làm
> cơ sở cho chương Giới hạn (Limitations) + Thảo luận (Discussion) trong luận
> văn. Mỗi limitation kèm: (a) bằng chứng quan sát; (b) approach đã thử; (c) lý
> do thất bại; (d) implication cho future work.

## Limitation 1 — Embedding semantic blindness cho Q022 (legal label disambiguation)

### Bối cảnh

Q022: "Hồ sơ giao đất ở của tôi nộp tháng 6/2024 nhưng đến nay (tháng 10/2024)
vẫn chưa có quyết định cuối cùng, áp dụng hạn mức theo Quyết định 18/2016 hay
Quyết định 69/2024?"

Ground truth citations:
- `{dieu: '3', van_ban: 'quyet-dinh-69-2024-qd-ubnd-tp-hcm'}` (regime mới)
- `{dieu: '1', khoan: '1', diem: 'a', van_ban: 'quyet-dinh-18-2016-qd-ubnd-tp-hcm'}` (regime cũ)

### Quan sát empirical (cumulative qua 4 fix attempts)

| Fix attempt | Q022 F1 | Bottleneck |
|---|---|---|
| v2.3 canonical (no fix) | 0.00 | Hybrid drop QĐ 18 chunks |
| v2.4 (Prompt TEMPORAL #4) | 0.00 | Span-regime rule trigger nhưng top dense QĐ 18 ≠ GT |
| v2.5 (Dense Floor) | 0.00 | Top-1 dense per norm = "Điều 4 Hiệu lực thi hành" (KHÔNG phải GT Điều 1 K1 Điểm a) |
| v2.6 (Pass -1 Struct Cite) | 0.00 | Question không có "Khoản X Điều Y" pattern → Pass -1 no-op |
| **Label-keyword Boost attempt** | **0.50** ⚠️ | Pass -0.5 picked Điều 3 (different topic) instead of Điều 1 (GT) |

### Root cause của failure

Pure dense rank GT trong QĐ 18 ALONE: **#7 / 23 chunks**

Top-1 dense của QĐ 18 cho Q022 = "Điều 4 Hiệu lực thi hành" — chứa các từ
khóa "Quyết định 18/2016", "Quyết định 69/2024", "30/09/2024" giống Q022
question hơn GT "Điều 1 Quy định hạn mức đất ở".

Mô hình BGE-M3 weight question-text similarity với chunks chứa metadata văn
bản (date, number) mạnh hơn content keyword ("hạn mức đất ở"). Đây là
**embedding semantic blindness** — embedding không phân biệt được:
- "Hạn mức đất ở theo QĐ 18/2016" (Điều 1 — GT)
- "Hiệu lực thi hành của QĐ 18/2016" (Điều 4 — meta)

### Label-keyword Boost attempt + lý do thất bại

**Hypothesis**: lexical overlap giữa content tokens của question và Component
label có thể phân biệt được Điều CONTENT-RELEVANT vs META-related.

**Implementation**: Pass -0.5 fetch components có label-overlap ≥ 2 với content
tokens (sau khi filter stopwords + structural keywords), boost top-1 per norm
vào output.

**Empirical failure (ablation 8-câu 20260520-141825)**:

| Metric | +Pass -1 baseline | +Label-keyword | Δ |
|---|---|---|---|
| AVG F1 | 0.693 | 0.638 | **−0.055 (−7.9%)** |
| Win:Loss count | — | 1:4 | net negative |
| Win:Loss magnitude | — | +0.50 vs −0.95 | **1:2 net negative** |

**Regressions phát hiện**:
- Q001 (gap2 canary) 1.00 → 0.80
- Q002 (gap2 noise) 0.86 → 0.57 (cross-jurisdiction noise: "hạn mức" match QĐ TP.HCM + QĐ Đồng Nai)
- Q008 (gap2 noise) 0.86 → 0.67
- Q024 (gap3 canary) 0.67 → 0.40

**Diagnosis cụ thể Q022**: QĐ 18 có MULTIPLE Điều cùng chứa "hạn mức đất ở":
- Điều 1: "Quy định hạn mức đất ở đối với hộ gia đình, cá nhân và mục đích áp
  dụng hạn mức như sau" (GT)
- Điều 3: "Hạn mức đất ở áp dụng hỗ trợ người có công với cách mạng cải thiện
  nhà ở..." (different topic)

Label-overlap scoring (sau filter stopwords): Điều 1 score = 3, Điều 3 score
= 3 → TIE, ties broken bởi Cypher row order → Pass -0.5 picks Điều 3 (wrong)
instead of Điều 1 (GT).

Lexical overlap alone **CANNOT** distinguish 2 Điều cùng chủ đề ("hạn mức đất
ở") khác **target population** ("hộ gia đình, cá nhân" vs "người có công").

### Verdict & Implication

**Q022 documented as embedding limitation cho thesis Limitations chapter.**

Lý do **không fix triệt để**:
1. Embedding semantic blindness (BGE-M3 không phân biệt được population
   "hộ gia đình, cá nhân" vs "người có công" khi label cùng prefix "Hạn mức
   đất ở")
2. Label-keyword Boost cause cross-jurisdiction noise (4 regression cases)
3. Pass -1 Struct Cite no-op vì Q022 question không có "Khoản X Điều Y"
4. Dense Floor preserve top-1 dense per norm — không giúp khi GT dense rank > 1

**Future work** (xa khỏi scope luận văn hiện tại):
- **Cross-encoder re-ranking**: dùng cross-encoder (như BGE-Reranker) chấm
  điểm (question, label) pair với attention bidirectional → có thể phân biệt
  được semantic differences ở label level
- **Multi-query expansion**: rewrite question thành multiple sub-questions
  (VD: "ai được áp dụng hạn mức?" + "hạn mức bao nhiêu m²?") → dense match
  improve
- **Question-aware label filtering**: parse question để extract target
  population ("cá nhân thường" vs "người có công") → filter Components
  theo target trước khi rank

Tất cả 3 hướng đều cần work substantial hơn scope hiện tại. Chấp nhận Q022
F1=0 là limitation honest cho thesis.

---

## Limitation 2 — Data scope coverage gap (Q026 root cause)

(Already documented qua PROJECT_STATUS v2.6: NĐ 102/2024 KHÔNG có Điều 13
trong corpus do thu thập theo chương (D-01/D-05) — chương chứa Điều 13 không
thuộc scope CMĐSDĐ cá nhân.)

GT correction đã apply: Q026 cite AMENDING provision tại NĐ 49 Đ13 K1 thay vì
NĐ 102 (không tồn tại). Đã fix qua Pass -1 Structured Citation.

Future work: mở rộng corpus để include full Điều 13 của NĐ 102/2024 nếu cần
test cross-norm AMENDED_BY traversal triệt để hơn.

---

## Bài học methodology

**Gemini's "p-hacking warning" predicted noise — validated by ablation evidence.**

Phương pháp đúng:
1. **Propose** fix với reasoning rõ ràng
2. **Implement** với scope minimal + canary protection
3. **Ablate** trên test set diverse (target + canary + noise-risk)
4. **Decide** based on data, không argument
5. **Document** failures làm Limitations — giá trị khoa học cao hơn force-fit

Empirical evidence trumps a priori reasoning — both ways:
- Gemini's "regex là overfitting" predicted wrong (Pass -1 Struct Cite work)
- Gemini's "label-keyword là p-hacking" predicted right (noise > signal)

Quyết định dựa trên evidence per case, không dogma.
