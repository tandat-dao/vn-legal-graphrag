# Log chỉnh sửa giao diện `ui/`

Mỗi **phiên chỉnh sửa** ghi đúng một mục, mới nhất lên đầu. Mục đích không phải liệt kê diff
(`git log` đã làm việc đó) mà là giữ lại **lý do**: cái gì hỏng, vì sao sửa như vậy, và cách đã
kiểm chứng — để phiên sau không lặp lại một quyết định đã cân nhắc rồi.

Khuôn một mục:

```
## YYYY-MM-DD — tiêu đề ngắn
**Tệp:** …
### 1. Việc
- **Triệu chứng / yêu cầu:** …
- **Nguyên nhân:** (nếu là lỗi)
- **Sửa:** …
- **Kiểm chứng:** …
```

Spec là nguồn sự thật về *hiện trạng* (`UI_STYLE_SPEC.md`, `UI_DEMO_SPEC.md`); file này là *lịch sử*.
Sửa gì đụng tới spec thì cập nhật spec luôn, đừng để log thay spec.

---

## 2026-08-02 — Xương sống bảy bước: sửa đè số, đổi hệ màu; gọn lại chip câu hỏi

**Tệp:** `ui/static/index.html` · `ui/docs/UI_STYLE_SPEC.md`

### 1. Đường nối bảy bước đè lên số thứ tự

- **Triệu chứng:** đường dọc nối bảy bước chạy xuyên qua các chữ số.
- **Nguyên nhân:** `.buoc-cho { opacity: .6 }` đặt lên **cả thẻ**, mà `.so-buoc` là con của thẻ →
  nền trắng của vòng tròn cũng mờ theo, để lộ đường kẻ phía sau. Kèm theo, `opacity < 1` tạo
  stacking context mới nên số **không thể** tự nâng lên bằng `z-index`. Không phải lỗi xếp lớp.
- **Sửa:**
  - Chuyển mờ xuống nội dung: `.buoc-cho > :not(.so-buoc) { opacity: .6 }` — vòng tròn luôn đục.
  - Xếp lớp tường minh: đường kẻ `z-index: 0`, `.so-buoc` `z-index: 1`.
  - Căn lại tâm: đường kẻ `left: 21px → 22px`, `top: 38px → 39px` (tâm thật là x=23/y=39 vì thẻ có
    viền 1px). Hằng `38` trong JS tách thành `RAY_TOP = 39` cạnh `datTienDo`, có chú thích ràng
    buộc với CSS.
  - Thẻ 7 có `border-left: 3px` nên padding-box lệch thêm 2px → bù `.the-buoc-cuoi .so-buoc { left: -54px }`.
  - Cắt đuôi đường kẻ: `bottom: 22px → 0` + `.the-buoc:last-child::before` che bằng `--bg-page` từ
    tâm số 7 trở xuống (trước đó đường kẻ thòng xuống tận đáy thẻ 7 — thẻ cao nhất vì chứa câu trả lời).
- **Kiểm chứng:** chụp headless Chrome ở trạng thái nghỉ và trạng thái đang chạy bước 4.

> ⚠️ **Bẫy khi chụp headless:** dưới `--virtual-time-budget`, **transition CSS bị đóng băng** →
> đúng những thuộc tính có transition (nền vòng tròn, viền thẻ, chiều cao đoạn accent) trông như
> chưa đổi, dễ tưởng CSS không ăn. Phải chèn `*{transition:none!important}` mới chụp đúng.

### 2. Vòng tròn số và đường nối theo hai chế độ màu

- **Yêu cầu:** vòng tròn số mang màu chủ đạo của chế độ đang bật, đường nối mang màu còn lại.
- **Sửa:** thêm bộ vai trò thứ hai `--buoc-tron` / `--buoc-tron-chu` / `--buoc-ray` / `--buoc-ray-nhat`,
  chế độ B ghi đè **hoán vai** (A: tròn terracotta – ray navy; B: tròn navy – ray terracotta).
  Ba trạng thái giữ nguyên ý nghĩa nhưng nay cùng **một** màu, khác nhau ở độ đậm: chờ = pha loãng
  20% với nền trang · chạy = đặc + quầng 4px · xong = đặc.
  - Pha loãng bằng `color-mix` (Chrome ≥ 111), **có dòng khai báo dự phòng đứng trước** — không dùng
    alpha/opacity cho nền vòng tròn, vì đó chính là lỗi ở mục 1.
  - Chữ số lúc chờ ở chế độ A phải dùng mực trung tính `--gray-900`: terracotta-dk trên nền
    terracotta 20% chỉ đạt **3.1:1** (đo trên ảnh chụp), dưới ngưỡng 4.5:1 — chiếu máy chiếu là mất
    chữ. Chế độ B giữ navy vì đạt 8.9:1.
- **Kiểm chứng:** chụp cả hai chế độ; đo tương phản chữ số trên ảnh.

### 3. Chip câu hỏi mẫu bớt chói, còn 2 câu

- **Yêu cầu:** nền vàng đậm chói mắt và lộn xộn; chỉ để 2 câu ngoài, còn lại nằm trong bảng.
- **Sửa:** bỏ `bg-cta #FFC251`, chip thành pill viền nhạt (`--gray-50` + viền `--border-card`,
  hover viền `--accent`); `SO_CHIP_GOI_Y = 2` cắt danh sách chip; câu dài cắt bằng
  `text-overflow: ellipsis` + `title` = nguyên câu; thêm nhãn `THỬ NHANH` (`#nhan-goi-y`) đứng
  **ngoài** nút.
- **Ràng buộc phải giữ:** `textContent` của nút = **đúng** câu hỏi gửi vào pipeline (mục 6.0 của
  style spec) → chỉ được cắt bằng CSS, tuyệt đối không cắt chuỗi trong JS, không chèn ký tự trang
  trí vào trong nút. Bảng "Câu hỏi mẫu" vẫn liệt kê đủ mọi nhóm nên không câu nào biến mất.

### 4. Gỡ nhóm X khỏi `DEMO_QUESTIONS.md`

Bốn câu "quậy mô hình" (prompt injection, mồi văn bản không tồn tại, tiền đề sai, đòi đổi vai) là
câu để **chạy thử lúc kiểm tra**, không phải câu bày ra lúc bảo vệ — bảng câu hỏi mẫu là thứ hội
đồng nhìn thấy. Tệp còn ba nhóm A/B/C. Test parser dùng tệp giả riêng nên không đụng tới;
`test_tep_that_trong_repo_parse_duoc` chỉ đòi `>= 3` nhóm nên vẫn xanh (35 test pass).
