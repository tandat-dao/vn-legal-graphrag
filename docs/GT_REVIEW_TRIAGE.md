# Phân loại phản hồi review GT của [B] — vòng 1

> Nguồn: `~/Downloads/GT_REVIEW_ket_qua (1).json` (B chấm 150 câu). 27 câu `fix`, 123 `ok`.
> (13 câu V105–V117 mang chk=false nhưng v=ok = câu **negative** — đúng thiết kế, KHÔNG lỗi.)
> Phân theo mảng: **17 hộ tịch (B) · 9 đất đai (A) · 1 nuôi con nuôi (B)**.

---

## NHÓM 1 — Out of Scope (13 câu, TẤT CẢ hộ tịch/B) — CẦN A+B QUYẾT

Câu đúng & cite đúng, nhưng hỏi về thủ tục KHÔNG nằm trong 6 thủ tục đã khai báo
(`VALID_PROCEDURES` hộ tịch chỉ có `dang-ky-khai-sinh` + `cap-ban-sao-trich-luc-ho-tich`).
Chủ đề vượt scope: **đăng ký kết hôn, xác nhận tình trạng hôn nhân, khai tử, nhận cha-mẹ-con**.

| Câu | Chủ đề OOS |
|---|---|
| V009, V010, V121, V134 | Lệ phí đăng ký kết hôn |
| V034, V059, V060, V123, V138 | Giấy xác nhận tình trạng hôn nhân |
| V063, V064, V128 | Đăng ký khai tử (quá hạn) |
| V065 | Đăng ký nhận cha, mẹ, con |

**Quyết định cần chốt:** (A) **Bỏ** 13 câu → còn 137, rebalance gap2; hay (B) **Mở rộng scope** hộ tịch trong Chương 1 (corpus đã chứa biểu phí NQ HĐND trả lời được các câu này — chúng là ca Gap-2 hợp lệ).

---

## NHÓM 2 — Trùng lặp → chuyển nhãn gap1 (2 câu)

Cùng vấn đề, khác cách dùng từ so với câu đã có. B đề xuất giữ nhưng gắn nhãn **gap1** (test đa lĩnh vực/paraphrase).

| Câu | Mảng | Trùng với | Xử lý |
|---|---|---|---|
| V135 | đất đai/A | V013 (lệ phí trực tuyến GCN Đồng Nai) | đổi gap_type → gap1 |
| V136 | hộ tịch/B | V023 | đổi gap_type → gap1 |

---

## NHÓM 3 — Lỗi dữ liệu corpus (sửa raw + re-ingest)

| Câu | Mảng | Lỗi | Trạng thái |
|---|---|---|---|
| **V054** | đất đai/A | NĐ112/2024 **Điều 10** bị NĐ226/2025 (Đ5 K2) sửa TOÀN BỘ, nhưng body thiếu `<!-- amended_by -->` → không sinh Amendment node; GT cite bản CŨ. **ĐÃ VERIFY.** | A sửa: thêm annotation + sửa GT cite sang bản 226/2025 |
| V071 | hộ tịch/B | NĐ123/2015 Điều 4 cắt xén đúng chỗ cần | B sửa raw |
| (chung) | hộ tịch/B | NĐ87/2020 & NĐ123/2015: hiệu lực 09/01/2025 ghi nhầm 09/01/2019 | **Raw local của A đã sửa** (phiên trước). B đang giữ bản cũ → khi B push cần reconcile, KHÔNG để regress |

---

## NHÓM 4 — Sửa citation GT (thiếu / thừa / sai)

### Đất đai (A) — 6 câu
| Câu | Vấn đề B nêu |
|---|---|
| V021 | Đáp án SAI: 100m² đầu tính 100%, 50m² sau mới 80% (đang tính gộp) |
| V096 | Đáp án + cite THIẾU điểm d, đ, e, g, h |
| V101 | Điều 139 K1 chỉ áp dụng vi phạm TRƯỚC 01/7/2014; câu hỏi không nêu mốc → thêm mốc thời gian HOẶC bổ sung K5 |
| V119 | Cite không chứa chi tiết "nộp trực tuyến: 0%" |
| V129 | Cite SAI: Điều 139 K1 không liên quan → phải K3 điểm a |
| V131 | Cite THỪA điểm a, b (Điều 10 K2 NQ254/2025) |
| V147 | Same V101 — thiếu K5 Điều 139 |

### Hộ tịch / NCN (B) — 3 câu
| Câu | Mảng | Vấn đề |
|---|---|---|
| V079 | hộ tịch | Thiếu cite Điều 35 (yếu tố nước ngoài) |
| V080 | ncn | Thiếu cite khoản 2 (yếu tố nước ngoài) |
| V126 | hộ tịch | Cite không chứa "đăng ký đúng hạn được miễn" |

---

## PHÂN CÔNG SỬA

- **A (Claude hỗ trợ):** toàn bộ đất đai — V054 (data+GT), V021, V096, V101/V147, V119, V129, V131, V135 (relabel).
- **B:** toàn bộ hộ tịch/ncn — V071, V079, V080, V126, V136 (relabel), NĐ87/NĐ123 date reconcile, + nhóm OOS sau khi A+B chốt.
- **A+B cùng chốt:** Nhóm 1 (OOS drop vs widen).

Sau khi sửa hết → chạy lại `verify_gt.py` → freeze + pre-register.
