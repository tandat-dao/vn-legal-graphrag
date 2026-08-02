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

## 2026-08-03 — Demo live chạy nhầm nhà cung cấp; đồ thị không căn lại khi đổi kích thước

**Tệp:** `ui/adapters.py` · `ui/static/index.html` · `scripts/preflight.py` · `tests/test_preflight.py` · `ui/README.md`

Ba việc dưới đây phát hiện khi chạy thử một lượt đầu-cuối ở máy có đủ Neo4j + Qdrant +
credentials, tức đúng cấu hình của buổi bảo vệ.

### 1. `LiveAdapter` mặc định `claude` trong khi báo cáo đo bằng Gemini

- **Triệu chứng:** khởi động `DEMO_MODE=live` ra log `LiveAdapter: khởi tạo client
  (llm_mode=claude)`, request đi tới `api.anthropic.com`, và **giao diện hiện chip
  `LLM: claude` ngay ở bước 1** — hội đồng nhìn thấy được.
- **Nguyên nhân:** `adapters.py` lấy `os.getenv("LLM_MODE") or "claude"`, mà `LLM_MODE`
  **không** nằm trong `.env.example` nên máy nào không tự thêm dòng đó sẽ rơi về Claude.
  Bảng 3.6 của báo cáo ghi planner Gemini 2.5 Flash, generator Gemini 2.5 Pro.
- **Sửa:** đổi mặc định thành `gemini` ở cả `LiveAdapter` lẫn `preflight.kiem_env` (hai chỗ
  phải khớp nhau, không thì preflight báo xanh cho một cấu hình khác cái đang chạy).
- **Kiểm chứng:** chạy lại `DEMO_MODE=live` → log `llm_mode=gemini`; hỏi một câu thật, log
  request là `aiplatform.googleapis.com/.../gemini-2.5-flash` và `gemini-2.5-pro`, 24 event,
  2 trích dẫn, 23,9s.

### 2. Đồ thị bước 4 không căn lại khi cửa sổ đổi kích thước

- **Triệu chứng:** cắm máy chiếu hoặc phóng to cửa sổ sau khi đã hỏi → đồ thị giữ nguyên vùng
  vẽ cũ, chừa một mảng trống bên phải. Đo trên canvas: lấp **96% bề ngang ở cửa sổ 832px,
  tụt còn 63% sau khi kéo lên 1600px**.
- **Nguyên nhân:** `CY.resize() + CY.fit()` mới chỉ được gọi trong `datCoChu()` (đổi cỡ chữ).
  Không có handler nào cho `window.resize`, mà Cytoscape thì không tự đo lại container.
- **Sửa:** thêm listener `resize` gọi đúng cặp `CY.resize(); CY.fit(undefined, 14)` như
  `datCoChu`, debounce 150ms vì sự kiện bắn liên tục lúc kéo cạnh cửa sổ.
- **Kiểm chứng:** đo lại cùng cách — 94% ở 1280px, **97%** sau khi kéo lên 1600px.

### 3. Hai test preflight đỏ trên máy vừa clone

- **Triệu chứng:** `pytest tests/ -q` ở worktree sạch cho `2 failed, 603 passed`; cũng lệnh đó
  trên máy đã cấu hình thì xanh. README đang ghi 574 pass.
- **Nguyên nhân:** `kiem_env` tính "không có tệp `.env`" là lỗi chặn, mà `.env` bị gitignore.
  Hai test chỉ monkeypatch biến môi trường nên vẫn dính lỗi đó → kết quả phụ thuộc máy chạy.
- **Sửa:** helper `_goc_co_env` trỏ `preflight.GOC` sang `tmp_path` có sẵn `.env` giả. Thêm
  `test_env_mac_dinh_la_gemini` khóa mặc định mới ở mục 1.
- **Kiểm chứng:** xóa `.env` khỏi worktree rồi chạy lại → **606 passed, 2 skipped**.

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
