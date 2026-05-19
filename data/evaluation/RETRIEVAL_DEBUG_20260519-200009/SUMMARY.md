# Retrieval Instrumentation — Downstream Bottleneck Diagnostics

> Dump Stage 1/2/3 cho 4 câu thất bại để định vị bottleneck giữa retrieval
> đúng (Stage 1 verified) và pred citations sai (canonical run).

---

## Q022 — Hồ sơ giao đất ở của tôi nộp tháng 6/2024 nhưng đến nay (tháng 10/2024) vẫn chưa...

**Investigation:** Stage 1 OK (QĐ 18 rank #1). Tại đâu old regime bị drop?

**Query Plan:** theme=`dat-dai`, jurisdiction=`tp-hcm`, temporal=`None` (broad (case_status=do-dang))

**Stage 1 — Seed norms (top-10):** `['quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'quyet-dinh-92-2025-qd-ubnd-dong-nai', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'nghi-quyet-22-2024-nq-hdnd-dong-nai', 'nghi-dinh-101-2024-nd-cp', 'quyet-dinh-52-2016-qd-ubnd-tp-hcm', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-02-2023-nq-hdnd-tp-hcm']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['nghi-quyet-02-2023-nq-hdnd-tp-hcm', 'quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'nghi-dinh-112-2024-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'luat-dat-dai-2024', 'nghi-quyet-87-2025-nq-hdnd-tp-hcm', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp', 'nghi-quyet-254-2025-qh15', 'quyet-dinh-52-2016-qd-ubnd-tp-hcm']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2634 items, first 20: `['f248af9abbf4021b', '8027b8a88ab0b82d', '47b218c880c78b7d', '7b0e023121417e84', '0d2946259c452820', '798535dd26f5475a', '14230be052fc8297', '92972e314c19d492', '66fae46464f7136d', '3f2edd2dfacfc4b5', '3f51c5b3d127c128', '4921a9009f846f45', '7294b09c4298b250', 'b8d0447d8fba1a2f', 'ed6e59d1a8399ade', 'fa9d00b9b25f42e7', '54c2bf0584b8482b', 'afd6cf46954fa041', 'b1c2475a3f65a1b9', 'a2981829cc54de1a']`

### ✅ Tất cả expected norms có mặt trong top-25

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 9.5039 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 2 | 9.1212 | `quyet-dinh-69-2024-qd-ubnd-tp-hcm` | Điều 1. Phạm vi điều chỉnh | Điều 1. Phạm vi điều chỉnh Quyết định này quy định hạn mức g |
| 3 | 9.1015 | `nghi-dinh-151-2025-nd-cp` | Điều 18. Quy định liên quan đến thủ tục, hồ sơ đăng ký đất đ | Điều 18. Quy định liên quan đến thủ tục, hồ sơ đăng ký đất đ |
| 4 | 8.798 | `nghi-dinh-50-2026-nd-cp` | Điều 6. Tính tiền sử dụng đất đối với hộ gia đình, cá nhân k | Điều 6. Tính tiền sử dụng đất đối với hộ gia đình, cá nhân k |
| 5 | 8.7576 | `quyet-dinh-18-2016-qd-ubnd-tp-hcm` | Điều 1. Quy định hạn mức đất ở đối với hộ gia đình, cá nhân  | Điều 1. Quy định hạn mức đất ở đối với hộ gia đình, cá nhân  |
| 6 | 8.5379 | `nghi-quyet-02-2023-nq-hdnd-tp-hcm` | Điều 1. Quy định về thu phí thẩm định hồ sơ cấp giấy chứng n | Điều 1. Quy định về thu phí thẩm định hồ sơ cấp giấy chứng n |
| 7 | 8.4742 | `nghi-quyet-87-2025-nq-hdnd-tp-hcm` | Phụ lục I. Các vị trí khác đối với đất phi nông nghiệp. > Kh | Phụ lục I. Các vị trí khác đối với đất phi nông nghiệp. Khoả |
| 8 | 8.2213 | `luat-dat-dai-2024` | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 9 | 7.8677 | `nghi-dinh-49-2026-nd-cp` | Điều 15. Quy định trình tự, thủ tục hành chính về đất đai >  | Điều 15. Quy định trình tự, thủ tục hành chính về đất đai Kh |
| 10 | 7.7039 | `nghi-quyet-254-2025-qh15` | Điều 4. Quy định về giao đất, cho thuê đất, chuyển mục đích  | Điều 4. Quy định về giao đất, cho thuê đất, chuyển mục đích  |
| 11 | 7.6282 | `nghi-dinh-102-2024-nd-cp` | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ |
| 12 | 7.4375 | `nghi-dinh-112-2024-nd-cp` | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  |
| 13 | 6.8515 | `quyet-dinh-52-2016-qd-ubnd-tp-hcm` | Phụ lục 16. Mức thu lệ phí cấp Giấy chứng nhận quyền sử dụng | Phụ lục 16. Mức thu lệ phí cấp Giấy chứng nhận quyền sử dụng |
| 14 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 15 | 3.0909 | `nghi-dinh-226-2025-nd-cp` | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 |

---

## Q023 — Hồ sơ cấp Giấy chứng nhận quyền sử dụng đất nộp năm 2023 nhưng chưa giải quyết x...

**Investigation:** Stage 1 OK (Luật 2013 rank #1). Tại đâu old regime bị drop?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`None` (broad (case_status=do-dang))

**Stage 1 — Seed norms (top-10):** `['luat-dat-dai-2013', 'luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp', 'nghi-quyet-254-2025-qh15', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-112-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['nghi-dinh-112-2024-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'luat-dat-dai-2024', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp', 'nghi-quyet-254-2025-qh15']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2503 items, first 20: `['95806512220a11b4', '74c96fc15578d5fc', '5d8ca9376c007945', '0c926a19449ad5fc', 'eb9402ef11a4a1fc', 'ac66f6c43459afe7', '641860d85b264cff', 'a4c7d0e7e09dc54e', '45b5fceeab02047e', '0067338eef8415d9', 'b43cbbd705521f50', 'aa276d6d73db0fa4', '2a7eef685fd2a21e', 'a1cbd6343f615e7d', 'fe2ba1e0d53186d1', '98dead8156d96d13', '7d8dbae4e5ba2d0f', '4bd4e990662da615', '52f7b052eaa14279', '1980e84aa2ca8870']`

### ✅ Tất cả expected norms có mặt trong top-25

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 9.8105 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 2 | 8.2213 | `luat-dat-dai-2024` | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 3 | 7.8824 | `nghi-dinh-50-2026-nd-cp` | Điều 12. Xử lý chuyển tiếp về tiền sử dụng đất, tiền thuê đấ | Điều 12. Xử lý chuyển tiếp về tiền sử dụng đất, tiền thuê đấ |
| 4 | 7.8528 | `nghi-dinh-49-2026-nd-cp` | Điều 20. Quy định về đăng ký đất đai, cấp Giấy chứng nhận >  | Điều 20. Quy định về đăng ký đất đai, cấp Giấy chứng nhận Kh |
| 5 | 7.6282 | `nghi-dinh-102-2024-nd-cp` | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ |
| 6 | 7.4445 | `nghi-dinh-151-2025-nd-cp` | Phụ lục I - Phần V - Nội dung C - Mục VII. Trình tự, thủ tục | Phụ lục I - Phần V - Nội dung C - Mục VII. Trình tự, thủ tục |
| 7 | 7.4375 | `nghi-dinh-112-2024-nd-cp` | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  |
| 8 | 7.1641 | `luat-dat-dai-2013` | Điều 100. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 100. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 9 | 7.0088 | `nghi-quyet-254-2025-qh15` | Điều 10. Miễn, giảm tiền sử dụng đất, tiền thuê đất; nộp tiề | Điều 10. Miễn, giảm tiền sử dụng đất, tiền thuê đất; nộp tiề |
| 10 | 3.0909 | `nghi-dinh-226-2025-nd-cp` | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 |
| 11 | 9.6523 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 12 | 7.937 | `luat-dat-dai-2024` | Điều 138. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 138. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 13 | 7.8637 | `luat-dat-dai-2024` | Điều 137. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 137. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 14 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 15 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |

---

## Q024 — Năm 2024, Luật Đất đai 2024 quy định căn cứ cho phép chuyển mục đích sử dụng đất...

**Investigation:** Pred miss Điều 116 K5 entirely → hybrid search không rank Điều 116 K5 vào top-k?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`2024-12-31` (strict=2024-12-31)

**Stage 1 — Seed norms (top-10):** `['luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp', 'nghi-dinh-112-2024-nd-cp', 'luat-dat-dai-2013', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-quyet-254-2025-qh15', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'nghi-dinh-101-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['nghi-dinh-112-2024-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'luat-dat-dai-2024', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2113 items, first 20: `['95806512220a11b4', '74c96fc15578d5fc', '5d8ca9376c007945', '0c926a19449ad5fc', 'eb9402ef11a4a1fc', 'ac66f6c43459afe7', '641860d85b264cff', 'a4c7d0e7e09dc54e', '45b5fceeab02047e', '0067338eef8415d9', 'b43cbbd705521f50', 'aa276d6d73db0fa4', '2a7eef685fd2a21e', 'a1cbd6343f615e7d', 'fe2ba1e0d53186d1', '98dead8156d96d13', '7d8dbae4e5ba2d0f', '4bd4e990662da615', '52f7b052eaa14279', '1980e84aa2ca8870']`

### ✅ Tất cả expected norms có mặt trong top-25

### ❌ Component 'dieu-116-khoan-5' KHÔNG có trong top-25
→ Bottleneck nằm ở hybrid_search ranking — chunk này không score đủ cao.

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 7.9744 | `nghi-dinh-102-2024-nd-cp` | Điều 44. Căn cứ giao đất, cho thuê đất, cho phép chuyển mục  | Điều 44. Căn cứ giao đất, cho thuê đất, cho phép chuyển mục  |
| 2 | 7.5809 | `nghi-dinh-101-2024-nd-cp` | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 3 | 7.5195 | `luat-dat-dai-2024` | Điều 227. Trình tự, thủ tục cho phép chuyển mục đích sử dụng | Điều 227. Trình tự, thủ tục cho phép chuyển mục đích sử dụng |
| 4 | 7.4616 | `nghi-dinh-112-2024-nd-cp` | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d |
| 5 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 6 | 7.6282 | `nghi-dinh-102-2024-nd-cp` | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ |
| 7 | 7.5809 | `nghi-dinh-101-2024-nd-cp` | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 8 | 7.5809 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 9 | 7.4859 | `luat-dat-dai-2024` | Điều 121. Chuyển mục đích sử dụng đất > Khoản 1. > Điểm d. | Điều 121. Chuyển mục đích sử dụng đất Khoản 1. Điểm d. Chuyể |
| 10 | 7.4697 | `nghi-dinh-102-2024-nd-cp` | Điều 109. Hành vi vi phạm pháp luật về đất đai khi thi hành  | Điều 109. Hành vi vi phạm pháp luật về đất đai khi thi hành  |
| 11 | 7.4451 | `luat-dat-dai-2024` | Điều 123. Thẩm quyền giao đất, cho thuê đất, cho phép chuyển | Điều 123. Thẩm quyền giao đất, cho thuê đất, cho phép chuyển |
| 12 | 7.4375 | `nghi-dinh-112-2024-nd-cp` | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  |
| 13 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 14 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |

---

## Q026 — Khoản 1 Điều 13 Nghị định 102/2024/NĐ-CP đã được văn bản nào sửa đổi và hiệu lực...

**Investigation:** Pred has Khoản 11/12 thay vì Khoản 1 — H2_khoan. Top-k có Khoản 1 không?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`None` (no_temporal_context)

**Stage 1 — Seed norms (top-10):** `['nghi-dinh-102-2024-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-254-2025-qh15', 'luat-dat-dai-2024', 'quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'nghi-dinh-112-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['nghi-dinh-112-2024-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'luat-dat-dai-2024', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp', 'nghi-quyet-254-2025-qh15']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 0 items, first 20: `[]`

### ✅ Tất cả expected norms có mặt trong top-25

### ✅ Component 'dieu-13-khoan-1' có trong top-25:
  - rrf_score=0.0397 `Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2024/NĐ-CP ngày 30 tháng 7 năm 2024 của Chính phủ quy định chi tiết thi hành một số điều của Luật Đất đai (được sửa đổi, bổ sung tại Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP) > Khoản 12.` (norm=nghi-dinh-49-2026-nd-cp)
  - rrf_score=0.0394 `Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2024/NĐ-CP ngày 30 tháng 7 năm 2024 của Chính phủ quy định chi tiết thi hành một số điều của Luật Đất đai (được sửa đổi, bổ sung tại Nghị định số 151/2025/NĐ-CP, Nghị định số 226/2025/NĐ-CP) > Khoản 11.` (norm=nghi-dinh-49-2026-nd-cp)

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 0.04 | `nghi-dinh-49-2026-nd-cp` | Điều 16. Hiệu lực thi hành > Khoản 3. > Điểm d. | Điều 16. Hiệu lực thi hành Khoản 3. Điểm d. Khoản 4 Điều 77  |
| 2 | 0.0374 | `nghi-dinh-101-2024-nd-cp` | Điều 67. Hiệu lực thi hành > Khoản 3. > Điểm a. | Điều 67. Hiệu lực thi hành Khoản 3. Điểm a. Khoản 1 và 2 Điề |
| 3 | 0.0335 | `nghi-dinh-151-2025-nd-cp` | Điều 20. (được bãi bỏ) | Điều 20. (được bãi bỏ) <!-- amended_by: 49/2026/NĐ-CP, tiết  |
| 4 | 0.0329 | `nghi-dinh-102-2024-nd-cp` | Điều 106. (được bãi bỏ) | Điều 106. (được bãi bỏ) <!-- amended_by: 151/2025/NĐ-CP, điể |
| 5 | 0.0397 | `nghi-dinh-49-2026-nd-cp` | Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2 | Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2 |
| 6 | 0.0394 | `nghi-dinh-49-2026-nd-cp` | Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2 | Điều 13. Sửa đổi, bổ sung một số điều của Nghị định số 102/2 |
| 7 | 0.0362 | `nghi-dinh-101-2024-nd-cp` | Điều 67. Hiệu lực thi hành > Khoản 2. > Điểm d. | Điều 67. Hiệu lực thi hành Khoản 2. Điểm d. Nghị định số 10/ |
| 8 | 0.0343 | `nghi-dinh-101-2024-nd-cp` | Điều 67. Hiệu lực thi hành > Khoản 3. > Điểm b. | Điều 67. Hiệu lực thi hành Khoản 3. Điểm b. Điều 11 Nghị địn |
