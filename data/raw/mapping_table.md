# Bảng ánh xạ văn bản pháp luật — Ontology GraphRAG

**Cập nhật:** 2026-04-19
**Trạng thái:** Đang điền — lĩnh vực Hộ tịch (khai sinh) đã có văn bản; các lĩnh vực khác cần bổ sung.

---

## Hướng dẫn đọc bảng

| Cột | Ý nghĩa |
|---|---|
| Thủ tục | Tên thủ tục hành chính (slug từ VALID_PROCEDURES) |
| Văn bản | Tên đầy đủ và số hiệu |
| id | Slug định danh duy nhất theo convention CLAUDE.md |
| Tier | 1=Luật, 2=Nghị định, 3=Thông tư, 4=Quyết định UBND |
| Implements | id của văn bản cha trong chuỗi pháp lý |
| Jurisdiction | toan-quoc / tp-hcm / dong-nai |
| Điều/Khoản cần lấy | Các Điều, Khoản cụ thể sẽ đưa vào data/raw/ |
| Ghi chú | Nhận xét pháp lý, phạm vi áp dụng, lưu ý đặc biệt |

**Quy tắc `implements`:**
- Luật gốc → `null`
- Nghị định hướng dẫn Luật → `id-cua-luat`
- Nghị định sửa đổi Nghị định khác → `id-cua-nghi-dinh-bi-sua`
- Thông tư hướng dẫn Nghị định → `id-cua-nghi-dinh`

---

## 1. Lĩnh vực Hộ tịch — Thủ tục: Đăng ký khai sinh

**Jurisdiction:** toan-quoc (thủ tục thống nhất toàn quốc,
không có văn bản địa phương khác biệt nội dung)

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| dang-ky-khai-sinh | Luật Hộ tịch 2014 (60/2014/QH13) | luat-ho-tich-2014 | 1 | null | toan-quoc | [CẦN ĐIỀN] | Văn bản gốc, nền tảng toàn bộ lĩnh vực |
| dang-ky-khai-sinh | Nghị định 123/2015/NĐ-CP | nghi-dinh-123-2015-nd-cp | 2 | luat-ho-tich-2014 | toan-quoc | [CẦN ĐIỀN] | Quy định chi tiết thi hành Luật Hộ tịch |
| dang-ky-khai-sinh | Nghị định 87/2020/NĐ-CP | nghi-dinh-87-2020-nd-cp | 2 | luat-ho-tich-2014 | toan-quoc | [CẦN ĐIỀN] | Quy định Cơ sở dữ liệu hộ tịch điện tử và đăng ký hộ tịch trực tuyến. Implements trực tiếp Luật Hộ tịch 2014 — độc lập với NĐ 123/2015. |
| dang-ky-khai-sinh | Nghị định 07/2025/NĐ-CP | nghi-dinh-07-2025-nd-cp | 2 | nghi-dinh-123-2015-nd-cp | toan-quoc | [CẦN ĐIỀN] | Sửa đổi Điều 2 của NĐ 123/2015 — không yêu cầu nộp bản giấy Giấy chứng sinh nếu đã có dữ liệu điện tử. |
| dang-ky-khai-sinh | Nghị định 18/2026/NĐ-CP | nghi-dinh-18-2026-nd-cp | 2 | nghi-dinh-123-2015-nd-cp | toan-quoc | [CẦN ĐIỀN] | Sửa đổi Điều 2, Điều 24, Điều 26 của NĐ 123/2015 — thẻ CCCD thay thế giấy tờ hộ tịch; đơn giản hóa đăng ký lại khai sinh. |
| dang-ky-khai-sinh | Thông tư 01/2022/TT-BTP | thong-tu-01-2022-tt-btp | 3 | nghi-dinh-87-2020-nd-cp | toan-quoc | [CẦN ĐIỀN] | Hướng dẫn thi hành trực tiếp NĐ 87/2020 — miễn giấy tờ tùy thân (có số định danh); giá trị pháp lý bản điện tử; liên thông thủ tục khai sinh. |

---

## 2. Lĩnh vực Hộ tịch — Thủ tục: Cấp bản sao trích lục hộ tịch

**Jurisdiction:** toan-quoc

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| cap-ban-sao-trich-luc-ho-tich | Luật Hộ tịch 2014 (60/2014/QH13) | luat-ho-tich-2014 | 1 | null | toan-quoc | [CẦN ĐIỀN] | Cùng văn bản gốc với khai sinh — chỉ lấy Điều liên quan thủ tục này |
| cap-ban-sao-trich-luc-ho-tich | [CẦN ĐIỀN — văn bản nào áp dụng?] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | toan-quoc | [CẦN ĐIỀN] | [CẦN ĐIỀN] |

---

## 3. Lĩnh vực Đất đai — Thủ tục: Chuyển mục đích sử dụng đất đối với cá nhân từ đất nông nghiệp (trừ đất lâm nghiệp) sang đất ở, gồm đất ở tại nông thôn, đất ở tại đô thị 

**Jurisdiction:** toan-quoc + tp-hcm + dong-nai

Chỉ xử lý các trường hợp chuyển mục đích sử dụng đất nông nghiệp (trừ đất lâm nghiệp) sang đất ở, gồm đất ở tại nông thôn, đất ở tại đô thị. Không xét các trường hợp chuyển mục đích khác (ví dụ: đất lâm nghiệp sang đất ở để tránh liên đới tới các văn bản luật chuyên ngành khác). 

Các câu hỏi benchmark cũng chỉ xoay quanh trường hợp chuyển mục đích sử dụng đất nông nghiệp (trừ đất lâm nghiệp) sang đất ở, gồm đất ở tại nông thôn, đất ở tại đô thị.

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| chuyen-muc-dich-su-dung-dat | Luật Đất đai 2024 (31/2024/QH15) | luat-dat-dai-2024 | 1 | null | toan-quoc | Chương I; Mục 1 Ch.II; Mục 1 Ch.III; Mục 3 Ch.III; Ch.V; Ch.IX; Mục 2 Ch.X; Mục 3 Ch.X; Mục 1 Ch.XI; Mục 2 Ch.XI; Mục 1 Ch.XIII; Mục 2 Ch.XIII; Ch.XIV | Chain root. Nguồn nội dung: VBHN 44/VBHN-VPQH (16/03/2026) |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 254/2025/QH15 | nghi-quyet-254-2025-qh15 | 1 | null | toan-quoc | Chương II | NQ Quốc hội — quy định chuyển tiếp/bổ sung cho Luật Đất đai. Hiệu lực: 01/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị định 102/2024/NĐ-CP | nghi-dinh-102-2024-nd-cp | 2 | luat-dat-dai-2024 | toan-quoc | Chương I; Mục 1 Ch.VI; Ch.IX | Quy định chi tiết thi hành Luật Đất đai. Nguồn nội dung: VBHN 46/VBHN-BNNMT (03/04/2026) |
| chuyen-muc-dich-su-dung-dat | Nghị định 151/2025/NĐ-CP | nghi-dinh-151-2025-nd-cp | 2 | null | toan-quoc | Chương I; Mục 1 Ch.II; Mục 3 Ch.II; Mục 4 Ch.II; Phụ lục I: Mục I Phần III, Mục VI Nội dung C Phần V, Mục VII Nội dung C Phần V | Nguồn nội dung: VBHN 41/VBHN-BNNMT (02/04/2026) |
| chuyen-muc-dich-su-dung-dat | Nghị định 49/2026/NĐ-CP | nghi-dinh-49-2026-nd-cp | 2 | nghi-quyet-254-2025-qh15 | toan-quoc | Chương III; Chương IV; Chương V | Hiệu lực: 31/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị định 50/2026/NĐ-CP | nghi-dinh-50-2026-nd-cp | 2 | nghi-quyet-254-2025-qh15 | toan-quoc | Chương II | Hiệu lực: 31/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị định 112/2024/NĐ-CP | nghi-dinh-112-2024-nd-cp | 2 | null | toan-quoc | Chương I; Chương II | ⚠️ Hết hiệu lực một phần (sửa đổi bởi NĐ 226/2025). Hiệu lực: 11/09/2024 |
| chuyen-muc-dich-su-dung-dat | Nghị định 226/2025/NĐ-CP | nghi-dinh-226-2025-nd-cp | 2 | null | toan-quoc | Khoản 2 Điều 5 | Sửa đổi, bổ sung NĐ 112/2024. Hiệu lực: 15/08/2025 |
| chuyen-muc-dich-su-dung-dat | Quyết định 69/2024/QĐ-UBND TP.HCM | quyet-dinh-69-2024-qd-ubnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Hạn mức giao đất ở cho cá nhân. ⚠️ Chỉ áp dụng cho TP.HCM cũ (chưa có QĐ mới cho TP.HCM mở rộng). Hiệu lực: 30/09/2024 |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 87/2025/NQ-HĐND TP.HCM | nghi-quyet-87-2025-nq-hdnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Bảng giá đất TP.HCM. Hiệu lực: 01/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 02/2023/NQ-HĐND TP.HCM | nghi-quyet-02-2023-nq-hdnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Phí thẩm định hồ sơ TP.HCM. Hiệu lực: 01/06/2023 |
| chuyen-muc-dich-su-dung-dat | Quyết định 52/2016/QĐ-UBND TP.HCM | quyet-dinh-52-2016-qd-ubnd-tp-hcm | 4 | null | tp-hcm | Phụ lục 16 | Mức thu phí và lệ phí. ⚠️ Hết hiệu lực một phần (phần cần lấy vẫn còn hiệu lực). Hiệu lực: 01/01/2017 |
| chuyen-muc-dich-su-dung-dat | Quyết định 92/2025/QĐ-UBND Đồng Nai | quyet-dinh-92-2025-qd-ubnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Hạn mức giao đất ở cho cá nhân. Hiệu lực: 11/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 28/2025/NQ-HĐND Đồng Nai | nghi-quyet-28-2025-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Bảng giá đất Đồng Nai. Hiệu lực: 01/01/2026 |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 22/2024/NQ-HĐND Đồng Nai | nghi-quyet-22-2024-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Phí thẩm định hồ sơ Đồng Nai. Hiệu lực: 09/12/2024 |
| chuyen-muc-dich-su-dung-dat | Nghị quyết 21/2024/NQ-HĐND Đồng Nai | nghi-quyet-21-2024-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Lệ phí cấp GCN quyền sử dụng đất Đồng Nai. Hiệu lực: 09/12/2024 |

---

## 4. Lĩnh vực Đất đai — Thủ tục: Cấp sổ đỏ lần đầu

**Jurisdiction:** toan-quoc + tp-hcm + dong-nai
**Ghi chú phạm vi:** Chỉ xét hộ gia đình/cá nhân có giấy
tờ theo Điều 137 Luật Đất đai 2024.

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| cap-so-do-lan-dau | Luật Đất đai 2024 (31/2024/QH15) | luat-dat-dai-2024 | 1 | null | toan-quoc | Chương I; Mục 1 Ch.II; Mục 2 Ch.II; Mục 3 Ch.II; Mục 1 Ch.III; Mục 3 Ch.III; Mục 1 Ch.IV; Mục 1 Ch.X; Mục 2 Ch.X; Mục 3 Ch.X; Mục 1 Ch.XI; Mục 2 Ch.XI; Ch.XIV; Mục 1 Ch.XV; Mục 2 Ch.XV | Chain root. Nguồn nội dung: VBHN 44/VBHN-VPQH (16/03/2026) |
| cap-so-do-lan-dau | Nghị quyết 254/2025/QH15 | nghi-quyet-254-2025-qh15 | 1 | null | toan-quoc | Chương II | NQ Quốc hội — quy định chuyển tiếp/bổ sung cho Luật Đất đai. Hiệu lực: 01/01/2026 |
| cap-so-do-lan-dau | Nghị định 102/2024/NĐ-CP | nghi-dinh-102-2024-nd-cp | 2 | luat-dat-dai-2024 | toan-quoc | Chương I; Chương II; Mục 4 Ch.VII; Ch.IX; Ch.X | Nguồn nội dung: VBHN 46/VBHN-BNNMT (03/04/2026) |
| cap-so-do-lan-dau | Nghị định 101/2024/NĐ-CP | nghi-dinh-101-2024-nd-cp | 2 | null | toan-quoc | Chương I; Mục 1 Ch.II; Mục 1 Ch.III; Mục 2 Ch.III; Mục 5 Ch.III; Ch.IV; Ch.V | Nguồn nội dung: VBHN 51/VBHN-BNNMT (29/04/2026) |
| cap-so-do-lan-dau | Nghị định 151/2025/NĐ-CP | nghi-dinh-151-2025-nd-cp | 2 | null | toan-quoc | Chương I; Mục 3 Ch.II; Mục 4 Ch.II; Ch.III; Phụ lục I: Mục II Nội dung C Phần V | Nguồn nội dung: VBHN 41/VBHN-BNNMT (02/04/2026) |
| cap-so-do-lan-dau | Nghị định 50/2026/NĐ-CP | nghi-dinh-50-2026-nd-cp | 2 | nghi-quyet-254-2025-qh15 | toan-quoc | Chương II | Hiệu lực: 31/01/2026 |
| cap-so-do-lan-dau | Quyết định 69/2024/QĐ-UBND TP.HCM | quyet-dinh-69-2024-qd-ubnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Hạn mức giao đất ở cho cá nhân. ⚠️ Chỉ áp dụng cho TP.HCM cũ. Hiệu lực: 30/09/2024 |
| cap-so-do-lan-dau | Nghị quyết 87/2025/NQ-HĐND TP.HCM | nghi-quyet-87-2025-nq-hdnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Bảng giá đất TP.HCM. Hiệu lực: 01/01/2026 |
| cap-so-do-lan-dau | Nghị quyết 02/2023/NQ-HĐND TP.HCM | nghi-quyet-02-2023-nq-hdnd-tp-hcm | 4 | null | tp-hcm | Toàn bộ văn bản | Phí thẩm định hồ sơ TP.HCM. Hiệu lực: 01/06/2023 |
| cap-so-do-lan-dau | Quyết định 52/2016/QĐ-UBND TP.HCM | quyet-dinh-52-2016-qd-ubnd-tp-hcm | 4 | null | tp-hcm | Phụ lục 16 | Mức thu phí và lệ phí. ⚠️ Hết hiệu lực một phần (phần cần lấy vẫn còn hiệu lực). Hiệu lực: 01/01/2017 |
| cap-so-do-lan-dau | Quyết định 92/2025/QĐ-UBND Đồng Nai | quyet-dinh-92-2025-qd-ubnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Hạn mức giao đất ở cho cá nhân. Hiệu lực: 11/01/2026 |
| cap-so-do-lan-dau | Nghị quyết 28/2025/NQ-HĐND Đồng Nai | nghi-quyet-28-2025-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Bảng giá đất Đồng Nai. Hiệu lực: 01/01/2026 |
| cap-so-do-lan-dau | Nghị quyết 22/2024/NQ-HĐND Đồng Nai | nghi-quyet-22-2024-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Phí thẩm định hồ sơ Đồng Nai. Hiệu lực: 09/12/2024 |
| cap-so-do-lan-dau | Nghị quyết 21/2024/NQ-HĐND Đồng Nai | nghi-quyet-21-2024-nq-hdnd-dong-nai | 4 | null | dong-nai | Toàn bộ văn bản | Lệ phí cấp GCN quyền sử dụng đất Đồng Nai. Hiệu lực: 09/12/2024 |

---

## 5. Lĩnh vực HN&GĐ — Thủ tục: Đăng ký nuôi con nuôi trong nước

**Jurisdiction:** toan-quoc

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| dang-ky-nuoi-con-nuoi | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | toan-quoc | [CẦN ĐIỀN] | [CẦN ĐIỀN] |

---

## 6. Lĩnh vực HN&GĐ — Thủ tục: Đăng ký lại nuôi con nuôi trong nước

**Jurisdiction:** toan-quoc

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| dang-ky-lai-nuoi-con-nuoi | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | toan-quoc | [CẦN ĐIỀN] | [CẦN ĐIỀN] |

---

## Checklist hoàn thành TASK-03

- [ ] Tất cả 6 thủ tục có ít nhất 1 hàng văn bản
- [ ] Cột `implements` đã được điền (không còn [CẦN ĐIỀN])
      cho lĩnh vực Hộ tịch / khai sinh
- [ ] Cột `Điều/Khoản cần lấy` đã điền cho tất cả hàng
- [ ] crossref_decisions.md đã tạo
- [ ] Cả 2 thành viên đã review và đồng ý

---

[PHẦN NÀY DO CODING AGENT KHÔNG ĐIỀN — dành cho
project owner sau khi hoàn tất mapping]

## Cross-reference decisions

Xem file: data/raw/crossref_decisions.md
