> Tài liệu này định nghĩa **kiến trúc hoàn chỉnh của khâu đánh giá** (evaluation) cho hệ thống.
> Nó là bản thiết kế (design spec) để [A], [B] và Claude trong các session tương lai cùng dựa theo khi triển khai.
> Thay đổi **hiếm khi** — chỉ khi triết lý đánh giá hoặc cấu trúc khối E0–E3 thay đổi.
> Để theo dõi task/tiến độ triển khai, xem `PROJECT_STATUS.md`. Để biết kiến trúc hệ thống, xem `PROJECT_CONTEXT.md`.

# Kiến trúc Đánh giá — Ontology-Driven GraphRAG cho Pháp luật Việt Nam
**Phiên bản 1.0 | Khởi tạo 2026-06-29**

---

## 0. Triết lý — "Claim → Evidence"

Evaluation cũ (đến v2.17) trả lời câu hỏi: *"Hệ thống của tôi có tốt không?"* — bằng cách so sánh Full GraphRAG vs Naive RAG.

Evaluation mới trả lời câu hỏi mạnh hơn:

> **"Hệ thống tốt VÌ ĐÚNG NHỮNG LÝ DO mà luận văn claim không?"**

Khác biệt cốt lõi:
- So sánh "Full vs Naive" chỉ chứng minh *toàn bộ* hệ thống hơn baseline — **không** chứng minh từng thành phần KG giải đúng gap của nó.
- Đánh giá toàn diện phải **cô lập từng cơ chế** và gắn nó với từng contribution claim.

**Nguyên tắc chọn tiêu chí:** mỗi tiêu chí phải hoặc **(a)** chặn một đường phản biện cụ thể, hoặc **(b)** cô lập một loại lỗi cụ thể. Tiêu chí không làm được cả hai → là trang trí, loại bỏ.

### Contribution claims cần chứng minh (từ PROJECT_CONTEXT §1)

| Claim | Phát biểu | Thành phần KG |
|---|---|---|
| **Gap 1 — Đa lĩnh vực** | Cùng một kiến trúc duy trì độ chính xác **ổn định** trên 3 lĩnh vực dị cấu trúc | `Theme` + `[:INCLUDES]` |
| **Gap 2 — Đa địa phương** | Graph routing ngăn retrieval nhầm giữa 2 địa phương nội dung gần giống | `Jurisdiction` + `[:APPLIES_TO]` |
| **Gap 3 — Đa tầng** | `[:IMPLEMENTS]` traversal tăng Recall trên câu hỏi tổng hợp đa tầng | `[:IMPLEMENTS]` + Stage 2 |
| **Gap 4 — Đa phiên bản** | CTV + `[:AMENDS]` phân biệt văn bản còn/hết hiệu lực, tracking sửa đổi | `CTV` + `[:AMENDS]` + `[:AMENDED_BY]` |

---

## 1. Tổng quan 4 khối E0–E3

Bốn khối là **4 mắt xích của một chuỗi thuyết phục**, thứ tự là cố ý — mỗi lớp làm lớp sau đáng tin:

```
E0. Tiền đề   → "Con số này có nghĩa không?"            (độ tin cậy của phép đo)
E1. Cơ chế    → "Từng thành phần KG có giải đúng gap?"   (ablation — cô lập cơ chế)
E2. Hệ thống  → "Cả hệ thống có vượt mọi đối thủ?"       (baseline ladder + answer quality)
E3. Giới hạn  → "Sai ở đâu, đã thử gì không được?"        (error analysis + trung thực)
```

**E1 làm E2 đáng tin:** khi E1 đã cho thấy tắt jurisdiction → Gap 2 sụp, thì lúc E2 nói "Full thắng baseline ở Gap 2", phản biện "may rủi" không còn chỗ đứng.

### Phân biệt then chốt — baseline ≠ ablation ≠ upper bound

| Loại | Là gì | Muốn thấy | Thuộc khối |
|---|---|---|---|
| **External baseline** | Hệ thống *khác* | mình **thắng** | E2 |
| **Internal ablation** | Mình *trừ một phần* | phần đó **sụp** | E1 |
| **Upper bound / skyline** | Bản *lý tưởng hóa* | mình **tiến gần** | E2 (oracle) |

> `dense-only`, `no-jurisdiction`... là **ablation** (E1), KHÔNG phải baseline. Baseline ở E2 là hệ thống *không phải của ta*.

---

## E0 — Tiền đề: Độ tin cậy của phép đo

Mục đích: chặn câu phản biện chí mạng *"con số của anh/chị không có nghĩa."* Mỗi tiêu chí chặn một đường tấn công.

| Tiêu chí | Chặn phản biện | Vì sao chọn (không phải cái khác) | Trạng thái |
|---|---|---|---|
| **Reproducibility N=3** (mean ± σ) | "chạy lại ra số khác?" | LLM stochastic dù temp=0 (P-09: F1 swing 0.33↔0.75). 1 run → không phân biệt cải tiến vs noise | ✅ đã có (REPRODUCIBILITY_REPORT) |
| **Significance** (paired bootstrap 95% CI + Wilcoxon) | "N nhỏ, Δ có thật?" | Bootstrap → CI trên độ lớn Δ. **Wilcoxon** (phi tham số) vì F1 bị chặn [0,1], lệch, không chuẩn → t-test không hợp lệ. **Paired** vì cùng bộ câu → loại phương sai "câu dễ/khó" | ✅ đã có (D-21, expanded_eval) |
| **GT provenance** | "ai xác nhận ground truth?" | GT pháp lý mang tính diễn giải → nếu không document ai + quy trình nào, evaluation thành **vòng tròn**. ĐIỂM YẾU NHẤT hiện tại | ⚠️ cần viết |
| **Metric validity** | "vì sao đo cái này?" | Đơn vị có nghĩa pháp lý = *vị trí trích dẫn* (Điều/Khoản/VB), không phải trùng từ ngữ → F1 cấp Khoản + semantic match, KHÔNG ROUGE/BLEU | ⚠️ cần viết |

**Việc cần làm chính:** không phải code mới, mà **viết phần methodology** giải thích metric design + GT provenance.

---

## E1 — Cơ chế: Ablation từng thành phần (phần thiếu, quan trọng nhất)

Mỗi ablation = Full GraphRAG **tắt đúng một thành phần**. Đây là khối phải **build mới** (cốt lõi: `AblationConfig` cờ tắt từng thành phần trong `run_pipeline`).

### Logic: leave-one-out, không phải add-one-in

Claim có dạng *"thành phần X **cần thiết** cho gap N"*. "Cần thiết" = lấy X đi → N sụp (necessity). Add-one-in chỉ chứng minh sufficiency (thêm X thì tốt lên) — không trả lời "có *cần* không".

### Ma trận double dissociation (đọc cả hàng lẫn cột)

| Ablation \ đo trên | Gap 1 | Gap 2 | Gap 3 | Gap 4 |
|---|:---:|:---:|:---:|:---:|
| **no-theme** (tắt `[:INCLUDES]` routing) | ↓↓ | ≈ | ≈ | ≈ |
| **no-jurisdiction** (tắt `[:APPLIES_TO]`) | ≈ | ↓↓ | ≈ | ≈ |
| **no-traversal** (tắt Stage 2 `[:IMPLEMENTS\|AMENDS]`) | ≈ | ≈ | ↓↓ | ≈ |
| **no-temporal** (tắt CTV valid_from/to filter) | ≈ | ≈ | ≈ | ↓↓ |
| **dense-only / no-hybrid** (tắt toàn bộ KG / 4-pass) | mốc "không graph" cho mọi gap |||| 
| **Full GraphRAG** | cao | cao | cao | cao |

**Tiêu chí vàng:** mỗi ablation phải **sụp đúng gap tương ứng (p<0.05) VÀ không đổi ở gap khác** (double dissociation). Chỉ "tắt X → tổng F1 giảm" là KHÔNG đủ — nó chỉ chứng minh X có ích chung chung, không chứng minh X giải *đúng* gap N. Nếu ablation làm sụp cả gap khác → có confound, phải giải thích.

> **Lưu ý Gap 1:** `no-theme` chứng minh Gap 1 ở chiều **chống cross-domain contamination** (tắt routing → câu Hộ tịch kéo nhầm chunk Đất đai → sụp). Đây chỉ là **một nửa** bằng chứng Gap 1. Nửa kia (độ nhất quán xuyên lĩnh vực) là phép *đo lường*, không phải ablation → nằm ở **E2b**.

---

## E2 — Hệ thống: So sánh tổng thể. Chia 2 phần.

### E2a — Baseline ladder (muốn thắng)

Ba baseline cũ (BM25 → Naive RAG → dense-only) chỉ nằm trên **một trục** (độ tinh vi retrieval) → chỉ chứng minh "graph là retrieval tốt". Để chứng minh đúng claim *"ontology-driven là cách làm đúng"*, cần baseline trên **trục khác**:

| Baseline | Chặn câu hỏi | Chi phí | Ưu tiên |
|---|---|---|---|
| Naive RAG (chunk 512) | "hơn RAG cơ bản?" | đã có | ✅ giữ |
| BM25 (keyword thuần) | "hơn IR truyền thống?" | thấp | ✅ thêm |
| **Closed-book LLM** (không retrieval) | "có **cần retrieval** không?" | ~$0 | ★ bắt buộc |
| **Auto-GraphRAG** (MS GraphRAG/LightRAG, graph tự sinh) | "có **cần ontology** thủ công không?" | **cao** | ★ giá trị học thuật cao nhất |
| **Oracle retrieval** (cho GT chunks) | TRẦN — lỗi do retrieval hay generation? | thấp | ★ bắt buộc (chẩn đoán) |
| Long-context dump | "RAG có lỗi thời?" | trung bình | ⏳ nếu còn thời gian |

**Vì sao closed-book không lấy lệ:** nó **chắc chắn sụp ở Gap 2 & Gap 4** (LLM không thể biết quy định địa phương / hiệu lực thời điểm từ pretraining) → vừa chặn phản biện vừa làm nổi bật 2 gap mạnh nhất. **Vì sao auto-GraphRAG là killer:** từ khóa luận văn là "Ontology-Driven" → câu đối ứng tự nhiên là "sao không để LLM tự sinh graph?". Cảnh báo fair-comparison: corpus nhỏ có thể làm auto-graph yếu *không công bằng* → cần thảo luận khi triển khai.

**Metric E2a:**
- **Citation-level** (giữ): F1 Khoản (strict) + F1 Điều (loose) + Norm Recall + Negative correctness + Latency P50/P95. *Hai cấp F1 vì tách 2 loại lỗi: F1 Điều = định tuyến văn bản; F1 Khoản = pinpoint chi tiết.*
- **Answer-level**: **BỎ BERTScore** → thay bằng **người chấm + máy chấm** (xem E2c).
- Báo cáo **per-gap VÀ per-domain**.

### E2b — Độ nhất quán xuyên lĩnh vực (Gap 1 — mảnh chính)

> CHỈ làm được khi có corpus đa-lĩnh-vực của [B]. Là bằng chứng *cốt lõi* của Gap 1.

Đo F1 **từng lĩnh vực** (Đất đai / Hộ tịch / Nuôi con nuôi) → cho thấy **phương sai liên-domain thấp**, không lĩnh vực nào sụp. "Ổn định xuyên lĩnh vực dị cấu trúc" = phương sai nhỏ. Đây là phép *đo lường* (không phải ablation) → thuộc E2. Kết hợp `no-theme` (E1) → Gap 1 đủ hai chân: *chống nhiễu* (E1) + *khái quát hóa ổn định* (E2b).

### E2c — Answer quality: Người chấm + Máy chấm (thay BERTScore)

**Vì sao bỏ BERTScore:** nó đo *"giống câu tham chiếu không"* (proxy gián tiếp), thưởng cho giống bề mặt. QA pháp lý cần *"đúng và hữu ích không"* (tiêu chí trực tiếp) — chiều mà BERTScore mù.

**Quan hệ người–máy là CHỦ–TỚ, không song song:**
```
Người chấm = chuẩn vàng, ĐẮT → chạy trên MẪU NHỎ (~20–30 câu)
Máy chấm (LLM-judge) = rẻ, chạy TOÀN BỘ → NHƯNG phải validated với người trước
```
Chạy LLM-judge trên đúng mẫu người đã chấm → đo agreement (Cohen's kappa). Chỉ **sau khi** máy đồng thuận đủ với người mới được tin con số máy trên câu người không chấm. Thiếu bước này = **vòng tròn** (dùng LLM chấm hệ thống LLM).

> **D-19 là tiền lệ cảnh báo:** support-judge từng thất bại (không bắt over-cite, flag oan). → bước validation không phải thủ tục; nếu lần này máy đồng thuận cao với người → đóng góp khoa học thật (tương phản D-19). Nếu không → finding trung thực.

**Điều kiện để người chấm có sức nặng:**
| Yêu cầu | Vì sao |
|---|---|
| Rubric có **thang neo** (định nghĩa 3 vs 5 điểm) | tránh mỗi người hiểu một kiểu |
| **Chấm mù + xáo trộn** (không biết câu nào của hệ nào) | tránh thiên vị; bắt buộc cho phần so sánh hệ thống |
| **≥2 người chấm + kappa** | 1 người = ý kiến cá nhân; ≥2 + agreement = đo được khách quan |
| Lý tưởng **chuyên gia pháp luật độc lập** | người-trong-nhóm chấm bài của chính mình = điểm yếu → ghi Limitations nếu không có chuyên gia |

**Chiều rubric đề xuất** (thang Likert 5): Factual Correctness · Completeness · Citation Accuracy · Clarity · Hallucination (binary).

---

## E3 — Giới hạn: Phân tích lỗi & trung thực

Biến "điểm yếu" thành đóng góp khoa học — phân tích lỗi trung thực là dấu hiệu nghiên cứu chín.

| Hạng mục | Vì sao | Trạng thái |
|---|---|---|
| **Failure taxonomy** (retrieval-fail / generation-fail / GT-artifact) | "F1=0.55" không cho biết sửa gì; phân loại → bản đồ hành động | ✅ đã có (ROOT_CAUSE H2–H5) |
| **Negative results** (D-12, D-19, D-20) | tài sản MẠNH NHẤT — chứng minh quyết định dựa trên bằng chứng, không cherry-pick | ✅ giữ làm mục chính thức |
| **Faithfulness + Term grounding** | chống hallucination (orthogonal với F1) | ✅ đã có |
| **Case studies** (Q022/Q024/Q026) | minh họa cơ chế thất bại cụ thể | ✅ đã có |
| **Error severity** (lỗi pháp lý nặng vs nhẹ) | F1 coi mọi lỗi như nhau; pháp luật thì không (sai thẩm quyền ≠ sai diện tích) | ▸ tham vọng — có thể đẩy Future Work |

---

## 2. Gói bằng chứng cho từng Gap (cách hội đồng đọc)

Mỗi claim có **gói bằng chứng đa nguồn** — tấn công gap nào cũng có >1 nguồn:

| Gap | Ablation (E1) | So sánh (E2) | Bổ trợ |
|---|---|---|---|
| **1 — Đa lĩnh vực** | `no-theme` → contamination | **E2b: phương sai per-domain thấp** | — |
| **2 — Đa địa phương** | `no-jurisdiction` → sụp | thắng Naive RAG + **closed-book sụp** (LLM không biết HCM vs ĐN) | case study cross-juris |
| **3 — Đa tầng** | `no-traversal` → sụp | thắng dense-only (miss tổng hợp đa tầng) | NormR là metric đắt giá |
| **4 — Đa phiên bản** | `no-temporal` → sụp | baseline + closed-book **mù hoàn toàn** temporal | Δ lớn nhất (đo được +0.522, D-21) |

> Với Gap 2 & 4, **closed-book sụp** là bằng chứng bổ sung mạnh: cho thấy đây là tri thức LLM *không thể có sẵn* (quy định địa phương / hiệu lực thời điểm) → buộc phải đến từ kiến trúc retrieval.

---

## 3. Ánh xạ sang code module (reuse vs build)

```
src/evaluation/
├── run_evaluation.py        ← thêm ablation systems vào --systems (BUILD: wiring)
├── ablation_config.py       ← MỚI: AblationConfig (cờ tắt từng thành phần KG) — cốt lõi E1
├── metrics.py               ← giữ (F1 Khoản/Điều, NormR, cit_matches)
├── retrieval_eval.py        ← E1 retrieval-level Recall@k/MRR (đã có)
├── faithfulness.py          ← E3 (đã có)
├── expanded_eval.py         ← E0 significance + E2 citation behavior (đã có, D-21)
├── build_ablation_matrix.py ← E1 bảng dissociation (đã có — mở rộng cho 5 ablation × 4 gap)
├── human_eval.py            ← MỚI: rubric scoring + kappa + LLM-judge validation (E2c)
└── error_analysis.py        ← MỚI: gộp ROOT_CAUSE thành module tái chạy (E3)
```

**Nguyên tắc:** KHÔNG viết lại 5 pipeline riêng cho ablation — thêm `AblationConfig` (cờ) vào `run_pipeline()`, rồi `run_evaluation --systems` nhận tên ablation. Phần lớn hạ tầng đã có; việc thật cần build: `ablation_config.py` + `human_eval.py` + `error_analysis.py`.

---

## 4. Thứ tự ưu tiên & phụ thuộc

| # | Việc | Cần corpus B? | Cần API? | Ghi chú |
|---|---|:---:|:---:|---|
| 1 | Viết E0 methodology (GT provenance + metric validity) | ✗ | ✗ | làm NGAY, chỉ viết |
| 2 | Thiết kế `ablation_config.py` (cờ tắt thành phần) | ✗ (code) | ✗ | làm NGAY; *chạy* mới cần corpus |
| 3 | Closed-book + BM25 + Oracle baseline | một phần | ít | phần lớn làm được ngay trên Đất đai |
| 4 | Thiết kế rubric + `human_eval.py` (E2c) | ✗ | ✗ | làm NGAY |
| 5 | **Chạy ablation suite E1** (double dissociation) | ✓ | ✓ | **blocker chính** — chờ B |
| 6 | E2b consistency (per-domain variance) | ✓ | ✓ | chỉ có nghĩa khi đa-domain |
| 7 | Auto-GraphRAG baseline | ✓ | ✓✓ | đắt nhất; nếu hụt → Limitations |
| 8 | Canonical rerun cùng phiên (bỏ confound lệch ngày) | ✓ | ✓ | dọn confound 05-19 vs 05-28 |

**Tinh thần:** evaluation toàn diện KHÔNG phải đo *mọi thứ*, mà **biết rõ cái gì bắt buộc, cái gì đánh đổi, và trung thực về ranh giới** (auto-GraphRAG + error severity là đánh đổi chính đáng có thể đẩy Future Work nếu thiếu thời gian — miễn nói rõ tại sao).

**Liên hệ:** D-21 (Tier 0 đã xong) · D-22 (quyết định tái cấu trúc E0–E3 này) · `project_eval_tier1_deferred` (ablation full chờ corpus B).
