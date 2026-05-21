# Manual Evaluation — TASK-17 DoD #4

**Người chấm:** [A] — phụ trách Đất đai
**Ngày chấm:** 2026-05-17
**Data nguồn:** `results_graphrag_20260517-184216.json` + `results_baseline_20260517-184216.json` (v7 — sau fix #2 + #3)
**Số câu chấm:** 10/19 (đủ DoD ≥10)

**Mục tiêu:** Chấm thủ công Correctness + Faithfulness — vì F1 tự động chỉ đo trùng khớp citation, không phản ánh chất lượng nội dung lý luận pháp lý.

## Tiêu chí chấm điểm (1-5 scale)

### Correctness — Câu trả lời có ĐÚNG về mặt pháp lý không?
- **5** — Đúng hoàn toàn, đầy đủ chi tiết quan trọng, không có thông tin sai
- **4** — Đúng phần lớn (>80%), thiếu một vài chi tiết nhỏ
- **3** — Đúng một phần (50-80%), có một số chi tiết sai hoặc thiếu
- **2** — Sai nhiều hơn đúng (<50%), nhưng có ít nhất 1 ý đúng
- **1** — Sai hoàn toàn HOẶC từ chối trả lời khi đáng lẽ phải trả lời được

### Faithfulness — Câu trả lời có CÓ NGUỒN trong context không?
- **5** — Mọi claim đều có citation đúng văn bản đúng vị trí
- **4** — Phần lớn (>80%) claims có citation đúng
- **3** — 50-80% claims có citation; một số claim không có nguồn
- **2** — <50% claims có citation; nhiều phần bịa
- **1** — Bịa toàn bộ

### Negative case — Correctness = 5 nếu từ chối đúng, = 1 nếu bịa

## Bảng chấm điểm chi tiết

| ID | Gap | Topic (rút gọn) | G Cor | G Faith | B Cor | B Faith | Phát hiện chính |
|---|---|---|---:|---:|---:|---:|---|
| Q005 | gap1 | Cấp mới GCN cho biến động | 4 | 5 | 4 | 5 | Cả 2 đúng, cite Đ23 NĐ 101. G có thêm NĐ 151 phân cấp. |
| Q006 | negative | Phí công chứng | 5 | 5 | 5 | 5 | Cả 2 từ chối đúng (sau fix #2 prompt scope guard). |
| Q011 | gap3 | Bóc tách + nghĩa vụ tài chính | 4 | 5 | 4 | 5 | Cả 2 đầy đủ 2 nhóm nghĩa vụ. G cite Đ12 NĐ 112 thay Đ182 Luật (đúng hơn về nội dung). |
| **Q012** | gap3 | Tiền SDĐ chuyển vườn ao→ở | **5** | **5** | **2** | **3** | **G trình bày bảng 30/50/100% chi tiết. B miss hoàn toàn phần ưu đãi cốt lõi, chỉ nói "áp dụng 1 lần".** |
| Q013 | gap3 | Tranh chấp phân cấp huyện-xã | 5 | 5 | 3 | 4 | G trình bày đủ thẩm quyền + phân cấp NĐ 151 + 30 ngày khiếu nại + tòa/tỉnh. B lan man về hòa giải xã (Đ235), thiếu phần khiếu nại. |
| Q014 | gap1 | Định nghĩa cá nhân SXNN | 5 | 5 | 5 | 5 | Cả 2 đầy đủ định nghĩa + 3 trường hợp loại trừ. |
| Q016 | negative | Thuế TNCN | 5 | 5 | 5 | 5 | Cả 2 từ chối đúng. |
| **Q017** | gap3 | **Killer lex posterior chain** | **4** | **5** | **2** | **2** | **G trình bày bảng 30/50/100% + cảnh báo thiếu thẩm quyền. B sai văn bản (cite Luật 47/2024 không có trong corpus), thiếu phần ưu đãi.** |
| **Q018** | gap3 | **Multi-juris HCM vs ĐN** | **5** | **5** | **2** | **4** | **G trình bày BẢNG SO SÁNH 2 TỈNH với số tiền cụ thể. B nói thẳng "không có dữ liệu TP.HCM" — chỉ cover ĐN.** |
| Q019 | gap3 | Bóc tách + phân cấp 2 cấp | 3 | 4 | 3 | 5 | Cả 2 đều **MISS phần phân cấp 2 cấp** (yêu cầu trong câu hỏi). G chỉ cite NĐ 226 lặp lại. B có cite cả NĐ 112 + NĐ 226, ghi nhận lex posterior. |

## Tóm tắt số liệu

| Metric | GraphRAG | Baseline | Δ |
|---|---:|---:|---:|
| **Correctness mean** | **4.5** / 5 | 3.5 / 5 | **+1.0** ✅ |
| **Faithfulness mean** | **4.9** / 5 | 4.3 / 5 | **+0.6** ✅ |

**GraphRAG WIN cả 2 metric thủ công** — khẳng định lại findings của metric tự động (F1 + NormR).

## Phát hiện qualitative

### 1. GraphRAG vượt trội rõ rệt ở 3 câu killer

**Q012 (tiền SDĐ ưu đãi 30/50/100%):**
- G trình bày bảng đầy đủ với citation `[Điều 10, Khoản 2, Điểm c, NQ 254]`
- B chỉ nói "áp dụng 1 lần" mà KHÔNG nêu bảng ưu đãi cốt lõi
- Sai khác: G hiểu được NQ 254 Đ10.2.c là quy định ưu đãi, B chỉ retrieve được phần "áp dụng 1 lần" của NĐ 50/2026

**Q017 (killer lex posterior chain):**
- G trình bày khung pháp lý 4 lớp (Luật + NQ 254 + NĐ 102 + NĐ 50/2026) + bảng ưu đãi 30/50/100%
- B SAI VĂN BẢN: cite "Luật 47/2024/QH15" không có trong corpus (LLM bịa từ context fragment)
- Đây là sweet spot của ontology + AMENDS edges — baseline naive không hiểu chain

**Q018 (multi-juris HCM vs ĐN):**
- G trình bày BẢNG SO SÁNH chi tiết phí thẩm định 2 tỉnh với số tiền cụ thể (HCM: 420.000 đ/hồ sơ; ĐN: 880.000 đ trực tiếp / 836.000 đ trực tuyến)
- B nói thẳng "không có dữ liệu về TP.HCM" — chỉ cover ĐN
- Fix #3 multi-juris đã unlock đúng kịch bản này — baseline không có jurisdiction filter nên thua

### 2. Cả 2 đồng hạng ở các câu single-tier (gap1)

Q005, Q014 cả 2 đều 4-5/5 — câu hỏi lookup đơn giản trong 1 văn bản, naive top-K của baseline hoàn toàn đủ.

### 3. Negative correctness ngang nhau (5/5 sau fix #2)

Fix #2 (prompt scope guard) đã chính thức giải quyết regression — cả G và B từ chối đúng cho Q006, Q016. Trước fix #2, G bịa Đ27 hoặc Đ159 Luật ĐĐ.

### 4. Q019 cả 2 cùng MISS phần phân cấp 2 cấp

Đây là failure mode CHUNG: câu hỏi yêu cầu nối NĐ 112+226 (bóc tách kỹ thuật) với NĐ 151 (phân cấp thẩm quyền). Retrieval chỉ kéo được phần bóc tách, không kết nối được phần phân cấp.

**Nguyên nhân:** Concept mapping không liên kết 2 khái niệm "phương án bóc tách" với "thẩm quyền chuyển giao". Ghi nhận trong thesis Limitations + Future Work.

## Kết luận cho TASK-17 (DoD #4)

- **DoD ≥10 câu/hệ thống: ✓** (10 câu, cả 2 hệ thống)
- **Correctness scoring: ✓** GraphRAG 4.5 vs Baseline 3.5 — GraphRAG win +1.0
- **Faithfulness scoring: ✓** GraphRAG 4.9 vs Baseline 4.3 — GraphRAG win +0.6
- **Findings qualitative đầy đủ:** ✓ 3 killer wins + 1 chung failure

**Manual eval xác nhận và bổ trợ findings của metric tự động (F1, NormR).** GraphRAG đặc biệt vượt trội ở:
- Multi-tier amendment chain (Q017, Q012)
- Multi-jurisdiction comparison (Q018)
- Complex phân cấp (Q013)

Baseline cạnh tranh ở các câu single-tier lookup, nhưng FAIL nặng khi câu hỏi đòi hỏi tổng hợp đa nguồn.
