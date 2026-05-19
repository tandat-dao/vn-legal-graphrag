# Retrieval Instrumentation — Downstream Bottleneck Diagnostics

> Dump Stage 1/2/3 cho 4 câu thất bại để định vị bottleneck giữa retrieval
> đúng (Stage 1 verified) và pred citations sai (canonical run).

---

## Q022 — Hồ sơ giao đất ở của tôi nộp tháng 6/2024 nhưng đến nay (tháng 10/2024) vẫn chưa...

**Investigation:** Stage 1 OK (QĐ 18 rank #1). Tại đâu old regime bị drop?

**Query Plan:** theme=`dat-dai`, jurisdiction=`tp-hcm`, temporal=`None` (broad (case_status=do-dang))

**Stage 1 — Seed norms (top-10):** `['quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'quyet-dinh-92-2025-qd-ubnd-dong-nai', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'nghi-quyet-22-2024-nq-hdnd-dong-nai', 'nghi-dinh-101-2024-nd-cp', 'quyet-dinh-52-2016-qd-ubnd-tp-hcm', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-02-2023-nq-hdnd-tp-hcm']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['luat-dat-dai-2013', 'nghi-quyet-87-2025-nq-hdnd-tp-hcm', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'luat-dat-dai-2024', 'nghi-dinh-112-2024-nd-cp', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-101-2024-nd-cp', 'quyet-dinh-52-2016-qd-ubnd-tp-hcm', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'nghi-quyet-254-2025-qh15', 'nghi-quyet-02-2023-nq-hdnd-tp-hcm']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2634 items, first 20: `['df4a60a6ea8be15e', 'b5e5006cabb9f637', '7d42ed846739188d', '1ccc135c354d6f6e', '684b9e4bfdbbeae9', '44b308f1213b7db6', 'dcea1f594b36d8f5', 'c63898b2b6c4fd85', '339e882447712883', 'c8592771f660ca2d', '123a798f8b054e0d', '027b0789068d9ebb', '41e32312efe682fb', '8fde1c37b11e6502', '8fd8448b3213429c', 'a323025dc2edc69c', '1a07bd14f3feac7e', 'c31e991fd07578db', '4cb56f4ea7ad7079', 'e82bc0cfd1e2155a']`

### ✅ Tất cả expected norms có mặt trong top-25

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 9.1212 | `quyet-dinh-69-2024-qd-ubnd-tp-hcm` | Điều 1. Phạm vi điều chỉnh | Điều 1. Phạm vi điều chỉnh Quyết định này quy định hạn mức g |
| 2 | 7.7039 | `nghi-quyet-254-2025-qh15` | Điều 4. Quy định về giao đất, cho thuê đất, chuyển mục đích  | Điều 4. Quy định về giao đất, cho thuê đất, chuyển mục đích  |
| 3 | 8.6032 | `nghi-dinh-151-2025-nd-cp` | Điều 16. Trách nhiệm của cơ quan có chức năng quản lý đất đa | Điều 16. Trách nhiệm của cơ quan có chức năng quản lý đất đa |
| 4 | 9.5039 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 5 | 6.2753 | `nghi-dinh-49-2026-nd-cp` | Điều 16. Hiệu lực thi hành > Khoản 2. | Điều 16. Hiệu lực thi hành Khoản 2. Chương IV Nghị định này  |
| 6 | 5.3333 | `quyet-dinh-18-2016-qd-ubnd-tp-hcm` | Điều 4. Hiệu lực thi hành > Khoản 2. > Điểm a. | Điều 4. Hiệu lực thi hành Khoản 2. Điểm a. Quyết định số 70/ |
| 7 | 8.798 | `nghi-dinh-50-2026-nd-cp` | Điều 6. Tính tiền sử dụng đất đối với hộ gia đình, cá nhân k | Điều 6. Tính tiền sử dụng đất đối với hộ gia đình, cá nhân k |
| 8 | 8.2213 | `luat-dat-dai-2024` | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 9 | 6.9766 | `nghi-dinh-102-2024-nd-cp` | Điều 44a. Việc giao đất, cho thuê đất, điều chỉnh quyết định | Điều 44a. Việc giao đất, cho thuê đất, điều chỉnh quyết định |
| 10 | 3.6417 | `quyet-dinh-52-2016-qd-ubnd-tp-hcm` | Phụ lục 16. Mức thu lệ phí cấp Giấy chứng nhận quyền sử dụng | Phụ lục 16. Mức thu lệ phí cấp Giấy chứng nhận quyền sử dụng |
| 11 | 8.5379 | `nghi-quyet-02-2023-nq-hdnd-tp-hcm` | Điều 1. Quy định về thu phí thẩm định hồ sơ cấp giấy chứng n | Điều 1. Quy định về thu phí thẩm định hồ sơ cấp giấy chứng n |
| 12 | 8.4742 | `nghi-quyet-87-2025-nq-hdnd-tp-hcm` | Phụ lục I. Các vị trí khác đối với đất phi nông nghiệp. > Kh | Phụ lục I. Các vị trí khác đối với đất phi nông nghiệp. Khoả |
| 13 | 7.4375 | `nghi-dinh-112-2024-nd-cp` | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  |
| 14 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 15 | 3.0909 | `nghi-dinh-226-2025-nd-cp` | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 |

---

## Q023 — Hồ sơ cấp Giấy chứng nhận quyền sử dụng đất nộp năm 2023 nhưng chưa giải quyết x...

**Investigation:** Stage 1 OK (Luật 2013 rank #1). Tại đâu old regime bị drop?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`None` (broad (case_status=do-dang))

**Stage 1 — Seed norms (top-10):** `['luat-dat-dai-2013', 'luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp', 'nghi-quyet-254-2025-qh15', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-112-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['luat-dat-dai-2013', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'luat-dat-dai-2024', 'nghi-dinh-112-2024-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-254-2025-qh15']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2503 items, first 20: `['df4a60a6ea8be15e', 'b5e5006cabb9f637', '7d42ed846739188d', '1ccc135c354d6f6e', '684b9e4bfdbbeae9', '44b308f1213b7db6', 'dcea1f594b36d8f5', 'c63898b2b6c4fd85', '339e882447712883', 'c8592771f660ca2d', '123a798f8b054e0d', '027b0789068d9ebb', '41e32312efe682fb', '8fde1c37b11e6502', '8fd8448b3213429c', 'a323025dc2edc69c', '1a07bd14f3feac7e', 'c31e991fd07578db', '4cb56f4ea7ad7079', 'e82bc0cfd1e2155a']`

### ✅ Tất cả expected norms có mặt trong top-25

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 9.8105 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 2 | 7.937 | `luat-dat-dai-2024` | Điều 138. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 138. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 3 | 7.556 | `nghi-dinh-49-2026-nd-cp` | Điều 20. Quy định về đăng ký đất đai, cấp Giấy chứng nhận >  | Điều 20. Quy định về đăng ký đất đai, cấp Giấy chứng nhận Kh |
| 4 | 7.8824 | `nghi-dinh-50-2026-nd-cp` | Điều 12. Xử lý chuyển tiếp về tiền sử dụng đất, tiền thuê đấ | Điều 12. Xử lý chuyển tiếp về tiền sử dụng đất, tiền thuê đấ |
| 5 | 6.3322 | `nghi-quyet-254-2025-qh15` | Điều 11. Quy định về thực hiện quyền, chế độ sử dụng đất, đă | Điều 11. Quy định về thực hiện quyền, chế độ sử dụng đất, đă |
| 6 | 7.1641 | `luat-dat-dai-2013` | Điều 100. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 100. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 7 | 7.4445 | `nghi-dinh-151-2025-nd-cp` | Phụ lục I - Phần V - Nội dung C - Mục VII. Trình tự, thủ tục | Phụ lục I - Phần V - Nội dung C - Mục VII. Trình tự, thủ tục |
| 8 | 4.8553 | `nghi-dinh-102-2024-nd-cp` | Điều 7. Xác định loại đất đối với trường hợp không có giấy t | Điều 7. Xác định loại đất đối với trường hợp không có giấy t |
| 9 | 7.4375 | `nghi-dinh-112-2024-nd-cp` | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  | Điều 9. Xây dựng công trình phục vụ trực tiếp sản xuất nông  |
| 10 | 3.0909 | `nghi-dinh-226-2025-nd-cp` | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 | Điều 5. Sửa đổi, bổ sung một số điều của Nghị định số 112/20 |
| 11 | 9.6523 | `nghi-dinh-101-2024-nd-cp` | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 26. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 12 | 8.2213 | `luat-dat-dai-2024` | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 140. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 13 | 7.8637 | `luat-dat-dai-2024` | Điều 137. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ | Điều 137. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữ |
| 14 | 7.0088 | `nghi-quyet-254-2025-qh15` | Điều 10. Miễn, giảm tiền sử dụng đất, tiền thuê đất; nộp tiề | Điều 10. Miễn, giảm tiền sử dụng đất, tiền thuê đất; nộp tiề |
| 15 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |

---

## Q024 — Năm 2024, Luật Đất đai 2024 quy định căn cứ cho phép chuyển mục đích sử dụng đất...

**Investigation:** Pred miss Điều 116 K5 entirely → hybrid search không rank Điều 116 K5 vào top-k?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`2024-12-31` (strict=2024-12-31)

**Stage 1 — Seed norms (top-10):** `['luat-dat-dai-2024', 'nghi-dinh-102-2024-nd-cp', 'nghi-dinh-112-2024-nd-cp', 'luat-dat-dai-2013', 'nghi-dinh-50-2026-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-quyet-254-2025-qh15', 'quyet-dinh-69-2024-qd-ubnd-tp-hcm', 'nghi-dinh-101-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['luat-dat-dai-2013', 'nghi-dinh-102-2024-nd-cp', 'luat-dat-dai-2024', 'nghi-dinh-112-2024-nd-cp', 'nghi-dinh-101-2024-nd-cp']`

**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** 2113 items, first 20: `['df4a60a6ea8be15e', 'b5e5006cabb9f637', '7d42ed846739188d', '1ccc135c354d6f6e', '684b9e4bfdbbeae9', '44b308f1213b7db6', 'dcea1f594b36d8f5', 'c63898b2b6c4fd85', '339e882447712883', 'c8592771f660ca2d', '123a798f8b054e0d', '027b0789068d9ebb', '41e32312efe682fb', '8fde1c37b11e6502', '8fd8448b3213429c', 'a323025dc2edc69c', '1a07bd14f3feac7e', 'c31e991fd07578db', '4cb56f4ea7ad7079', 'e82bc0cfd1e2155a']`

### ✅ Tất cả expected norms có mặt trong top-25

### ✅ Component 'dieu-116-khoan-5' có trong top-25:
  - rrf_score=7.0776 `Điều 116. Căn cứ để giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất > Khoản 5.` (norm=luat-dat-dai-2024)

**Top-15 hybrid search results:**

| # | rrf_score | norm_id | component (label) | text preview |
|---|---|---|---|---|
| 1 | 7.9744 | `nghi-dinh-102-2024-nd-cp` | Điều 44. Căn cứ giao đất, cho thuê đất, cho phép chuyển mục  | Điều 44. Căn cứ giao đất, cho thuê đất, cho phép chuyển mục  |
| 2 | 7.0776 | `luat-dat-dai-2024` | Điều 116. Căn cứ để giao đất, cho thuê đất, cho phép chuyển  | Điều 116. Căn cứ để giao đất, cho thuê đất, cho phép chuyển  |
| 3 | 7.0863 | `nghi-dinh-101-2024-nd-cp` | Điều 23. Các trường hợp đăng ký biến động đất đai, tài sản g | Điều 23. Các trường hợp đăng ký biến động đất đai, tài sản g |
| 4 | 6.207 | `nghi-dinh-112-2024-nd-cp` | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d |
| 5 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 6 | 7.6282 | `nghi-dinh-102-2024-nd-cp` | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ | Điều 108. Căn cứ để giải quyết tranh chấp đất đai trong trườ |
| 7 | 7.5809 | `nghi-dinh-101-2024-nd-cp` | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 8 | 7.5809 | `nghi-dinh-101-2024-nd-cp` | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu | Điều 25. Cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu |
| 9 | 7.5195 | `luat-dat-dai-2024` | Điều 227. Trình tự, thủ tục cho phép chuyển mục đích sử dụng | Điều 227. Trình tự, thủ tục cho phép chuyển mục đích sử dụng |
| 10 | 7.4859 | `luat-dat-dai-2024` | Điều 121. Chuyển mục đích sử dụng đất > Khoản 1. > Điểm d. | Điều 121. Chuyển mục đích sử dụng đất Khoản 1. Điểm d. Chuyể |
| 11 | 7.4697 | `nghi-dinh-102-2024-nd-cp` | Điều 109. Hành vi vi phạm pháp luật về đất đai khi thi hành  | Điều 109. Hành vi vi phạm pháp luật về đất đai khi thi hành  |
| 12 | 7.4616 | `nghi-dinh-112-2024-nd-cp` | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d | Điều 10. Quy định bóc tách và sử dụng tầng đất mặt khi xây d |
| 13 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |
| 14 | 6.8446 | `luat-dat-dai-2013` | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ | Điều 103. Xác định diện tích đất ở đối với trường hợp có vườ |

---

## Q026 — Khoản 1 Điều 13 Nghị định 102/2024/NĐ-CP đã được văn bản nào sửa đổi và hiệu lực...

**Investigation:** Pred has Khoản 11/12 thay vì Khoản 1 — H2_khoan. Top-k có Khoản 1 không?

**Query Plan:** theme=`dat-dai`, jurisdiction=`toan-quoc`, temporal=`None` (no_temporal_context)

**Stage 1 — Seed norms (top-10):** `['nghi-dinh-102-2024-nd-cp', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'luat-dat-dai-2013', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-254-2025-qh15', 'luat-dat-dai-2024', 'quyet-dinh-18-2016-qd-ubnd-tp-hcm', 'nghi-dinh-112-2024-nd-cp']`

**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** `['luat-dat-dai-2013', 'nghi-dinh-226-2025-nd-cp', 'nghi-dinh-102-2024-nd-cp', 'luat-dat-dai-2024', 'nghi-dinh-112-2024-nd-cp', 'nghi-dinh-151-2025-nd-cp', 'nghi-dinh-101-2024-nd-cp', 'nghi-dinh-49-2026-nd-cp', 'nghi-dinh-50-2026-nd-cp', 'nghi-quyet-254-2025-qh15']`

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
