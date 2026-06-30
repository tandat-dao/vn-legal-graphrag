# Review Log — Cross-check Dữ liệu (TASK-05)

## Lần review: 2026-06-30 — Corpus B (Hộ tịch + Nuôi con nuôi)

**Phạm vi:** 13 file [B] mới thêm + các sửa đổi của [A] để pass validator/parser.
**Người review:** [A] + Claude. **Lưu ý:** sign-off độc lập của [B] được **miễn** theo
quyết định owner 2026-06-30 (đẩy nhanh để mở khóa multi-domain). → Đây KHÔNG phải
cross-check độc lập 2 người đúng nghĩa; ghi vào Limitations như một hạn chế quy trình.

### Kiểm tra đã thực hiện

| Hạng mục | Kết quả |
|---|---|
| `validate_metadata.py data/raw/` | ✅ PASS 32/32 (gồm: trường bắt buộc, theme/tier hợp lệ, `implements` trỏ đúng id, summary có mặt, id khớp tên file) |
| Parser (`tests/test_parser.py` + toàn suite) | ✅ 266 test PASS — toàn bộ 32 file parse không lỗi |
| Metadata corpus B (13 file) | ✅ 13/13 đầy đủ + id khớp filename |
| Graph sau re-ingest | ✅ 32 Norm (dat-dai 20, ho-tich 8, nuoi-con-nuoi 4), 4548 Component, 6394 MAPS_TO_CONCEPT |
| D-23 multi-parent IMPLEMENTS | ✅ verify data thật: NĐ 120 → [Luật Hộ tịch, Luật NCN]; TT 04 → [NĐ 123, Luật Hộ tịch] |

### Sửa đổi của [A] trên data [B] — ghi nhận quyết định (cần [B] biết)

1. **NQ 124/2016 TP.HCM (đa-theme):** tách 2 Norm theo theme — id `-datdai` (theme dat-dai)
   và `-hotich` (theme ho-tich). Hướng A của D-23 (KHÔNG implement `[:BELONGS_TO]`).
2. **`thong-tu-01-2022-tt-btp`:** YAML `amended_by_norms` hỏng → sửa thành list
   `["thong-tu-03-2023-tt-btp"]` (suy luận từ nội dung VBHN). **[B] nên xác nhận đúng ý.**
3. Cơ học (heading typo `KHoản`/`ĐIểm`/`#### Điều`, comment template sót, spacing) — đã sửa.

### Tồn đọng nhỏ (non-fatal)

- 1/1422 component gặp disconnect thoáng qua khi ontology-mapping (Gemini) → thiếu 1
  mapping concept (micro-feature, không ảnh hưởng retrieval). Re-ingest sẽ tự retry nếu cần.

### Kết luận

Dữ liệu corpus B **đạt yêu cầu** để ingest + dùng cho multi-domain. Gate TASK-05 PASS
ở mức [A]+Claude. Cần [B] xác nhận hậu kiểm 2 quyết định ở mục "Sửa đổi" khi có thời gian.

**Sign-off:** [A] ✅ (2026-06-30) · [B] ⏳ miễn tạm (hậu kiểm sau) · Claude ✅ verify tự động
