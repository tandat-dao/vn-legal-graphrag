# PRE-REGISTRATION & FREEZE — Bộ dữ liệu kiểm thử GT v2

> **Mục đích:** khóa (freeze) bộ ground truth và ĐĂNG KÝ TRƯỚC (pre-register) kế hoạch
> phân tích **trước khi chạy bất kỳ đánh giá nào**. Đây là điều kiện của E0 (nền tin cậy):
> chứng minh test set và giao thức đo KHÔNG bị chỉnh sau khi nhìn thấy kết quả.

---

## 1. Đối tượng freeze

| Mục | Giá trị |
|---|---|
| File | `data/evaluation/test_set_v2.json` |
| Số câu | **137** |
| SHA256 | `bd2c5eaf85fc35efb936cab48f3f223ae9e56d63df94aee592a1cc31d3dcf146` |
| Commit chứa GT | `56b8ff113551fe1bda81cce8acda726e58c3cce4` |
| Ngày freeze | 2026-07-08 |
| Verify | `python -m src.evaluation.verify_gt … --final` → PASS 137/137, mọi citation resolve trong corpus |

> Sau freeze, MỌI thay đổi GT phải: (a) tạo phiên bản mới (v3) + SHA mới, (b) ghi lý do,
> (c) chạy lại toàn bộ. KHÔNG sửa lén file đã freeze.

## 2. Phân bổ chốt (137 câu)

| Nhóm | Số câu |
|---|---|
| gap1 | 25 |
| gap2 | 19 |
| gap3 | 24 |
| gap4 | 25 |
| negative/obvious | 8 |
| negative/trap | 6 |
| underspecified | 6 |
| composite | 7 |
| register | 17 |
| **Tổng** | **137** |

Theme: dat-dai 61 · ho-tich 39 · nuoi-con-nuoi 29 · (null) 8. Độ khó: easy 32 · medium 55 · hard 50.

## 3. Xuất xứ & quy trình (provenance)

- Soạn theo `docs/GT_AUTHORING_GUIDE.md`. **[A]** phụ trách Đất đai, **[B]** phụ trách Hộ tịch & Nuôi con nuôi.
- **Review chéo vòng 1 (2026-07-08):** [B] chấm toàn bộ 150 câu (phiếu `GT_REVIEW_ket_qua.json`); 27 câu gắn `fix`. Xử lý (chi tiết `docs/GT_REVIEW_TRIAGE.md`):
  - Bỏ 13 câu OOS hộ tịch (ngoài 6 thủ tục khai báo). 150 → 137.
  - Relabel V135/V136 → gap1.
  - Sửa 9 câu đất đai (gồm lỗi data Điều 10 NĐ112 bị NĐ226/2025 sửa toàn bộ — thêm annotation + re-ingest).
  - Sửa 4 câu hộ tịch/ncn (bổ sung/siết citation).
  - V021 giữ nguyên (đối chiếu luật cho thấy khớp; ý kiến review dựa trên hiểu nhầm cơ chế).
- **Dev set cũ** (`test_set_dat_dai.json`, 26 câu) = DEV SET đã nhiễm (contaminated theo D-10/D-11) — KHÔNG dùng để báo số cuối.

## 4. Kế hoạch phân tích ĐĂNG KÝ TRƯỚC (chốt trước khi chạy)

**Hệ thống so sánh (E2a baseline ladder):** `graphrag` (đầy đủ) vs `closed-book`, `bm25`, `baseline` (naive RAG), `oracle` (trần).

**Ablation (E1, double dissociation):** `no-theme` (Gap 1), `no-jurisdiction` (Gap 2), `no-implements` (Gap 3), `no-amends` / `no-temporal` (Gap 4), `no-traversal`, `dense-only`. Kỳ vọng: mỗi cơ chế sụp ĐÚNG gap của nó và ổn định ở gap khác.

**Chỉ số (E0 metric validity):** F1 Khoản (nghiêm), F1 Điều (lỏng), Norm Recall, Faithfulness (tier 0/1/2), negative_correct. `cit_matches` là chuẩn khớp citation duy nhất.

**Ý nghĩa thống kê:** paired bootstrap 95% CI (10000 resample, seed=42) + Wilcoxon signed-rank. Với subset ~25/gap, ưu tiên **effect-size** hơn săn p<0.05.

**LLM:** đo trên cả `claude` và `gemini` (LLM-agnostic). Judge (faithfulness) CỐ ĐỊNH Claude Haiku — thước đo độc lập.

**Đánh giá người (E2c):** mẫu chung phân tầng, chấm mù đa hệ; nhóm A (pháp lý A1-A4) + nhóm B (người dùng B1-B2); validate LLM-judge qua kappa (Landis-Koch) trước khi mở rộng.

**Phân tích lỗi (E3):** taxonomy retrieval/generation/over-cite/negative-fail; báo cáo cả negative results (D-12/19/20/24).

## 5. Còn treo (ghi nhận, không chặn freeze)

- V149 chưa có dấu review của [B] (who="") — kiểm lại khi thuận tiện.
- [B] `git pull origin develop` để đồng bộ raw (ngày NĐ87/NĐ123, nội dung NĐ123 Đ4 đã đúng trên origin) — KHÔNG push bản local cũ.
- Đề nghị **[A]+[B] cùng xác nhận (co-sign)** bản freeze này trước khi chạy đo chính thức.
