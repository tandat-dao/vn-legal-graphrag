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

## 3. Lĩnh vực Đất đai — Thủ tục: Chuyển mục đích sử dụng đất

**Jurisdiction:** toan-quoc + tp-hcm + dong-nai

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| chuyen-muc-dich-su-dung-dat | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | toan-quoc | [CẦN ĐIỀN] | [CẦN ĐIỀN] |
| chuyen-muc-dich-su-dung-dat | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | tp-hcm | [CẦN ĐIỀN] | Văn bản địa phương TP.HCM |
| chuyen-muc-dich-su-dung-dat | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | dong-nai | [CẦN ĐIỀN] | Văn bản địa phương Đồng Nai |

---

## 4. Lĩnh vực Đất đai — Thủ tục: Cấp sổ đỏ lần đầu

**Jurisdiction:** toan-quoc + tp-hcm + dong-nai
**Ghi chú phạm vi:** Chỉ xét hộ gia đình/cá nhân có giấy
tờ theo Điều 137 Luật Đất đai 2024.

| Thủ tục | Văn bản | id | Tier | Implements | Jurisdiction | Điều/Khoản cần lấy | Ghi chú |
|---|---|---|---|---|---|---|---|
| cap-so-do-lan-dau | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | toan-quoc | [CẦN ĐIỀN] | [CẦN ĐIỀN] |
| cap-so-do-lan-dau | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | tp-hcm | [CẦN ĐIỀN] | Văn bản địa phương TP.HCM |
| cap-so-do-lan-dau | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | [CẦN ĐIỀN] | dong-nai | [CẦN ĐIỀN] | Văn bản địa phương Đồng Nai |

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
