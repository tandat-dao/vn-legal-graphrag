# Quy ước chú giải GT v4 — "chuỗi dẫn chiếu"

**Trạng thái:** đang soạn · **Tập:** `data/evaluation/test_set_v4.json`

---

## 1. VÌ SAO CÓ TẬP NÀY

Tập GT v2 (137 câu) đã bị dùng làm **tập phát triển** cho đợt cải tiến sau phản
biện, nên không còn dùng làm tập kiểm thử được nữa. Tập v4 là tập kiểm thử mới.

Ngoài ra v2 dùng **quy ước tập tối thiểu**: chỉ ghi điều khoản trả lời trực
tiếp. Quy ước đó phạt hệ thống khi nó trích cả **tiền đề pháp lý** mà điều
khoản đáp án phụ thuộc vào.

Ví dụ đã đo được (câu V025 của v2):

> Câu hỏi: *đăng ký lại khai sinh nhưng không còn bản sao Giấy khai sinh cũ,
> cần giấy tờ gì?*
>
> Thông tư 04/2020 Điều 9 Khoản 3 mở đầu bằng: *"Trường hợp người yêu cầu đăng
> ký lại khai sinh **không có giấy tờ quy định tại khoản 1 và khoản 2 Điều
> này**  thì…"*
>
> GT v2 chỉ ghi **Khoản 3**. Hệ trích cả **Khoản 1, 2, 3** → bị tính là trích
> thừa, F1 tụt từ 0,57 xuống 0,36.

Nhưng Khoản 3 **tự định nghĩa phạm vi áp dụng của nó bằng cách dẫn tới Khoản 1
và Khoản 2** — không đọc hai khoản kia thì không biết Khoản 3 áp dụng khi nào.
Trích cả ba là **đúng hơn về mặt pháp lý**, không phải thừa.

---

## 2. QUY ƯỚC

Trích dẫn đáp án gồm hai phần:

### (a) Điều khoản trả lời trực tiếp
Điều khoản chứa nội dung trả lời câu hỏi. Luôn có.

### (b) Tiền đề bắt buộc — ĐIỂM MỚI so với v2
Điều khoản mà điều khoản (a) **dẫn chiếu tường minh** VÀ **không đọc thì không
áp dụng được (a)**. Ba dạng:

| dạng | ví dụ |
|---|---|
| Xác định phạm vi áp dụng | *"Trường hợp không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này thì…"* |
| Định nghĩa đối tượng / điều kiện | *"Đối tượng quy định tại khoản 3 Điều 45 được…"* |
| Nêu ngoại lệ | *"…trừ trường hợp quy định tại khoản 2 Điều này"* |

### (c) Giới hạn — để quy ước không vô hạn

- **Độ sâu đúng 1 bước.** Không lần tiếp tiền đề của tiền đề.
- **Không** tính dẫn chiếu chỉ mang tính chỉ dẫn: *"thực hiện theo quy định của
  pháp luật về đất đai"*, *"theo quy định của Chính phủ"*.
- **Không** tính dẫn chiếu tới văn bản **ngoài kho** (ghi vào `notes` thay vì
  `ground_truth_citations`).
- **Không** tính dẫn chiếu tới thủ tục khác mà câu hỏi không hỏi tới.

### (d) Nguyên tắc quyết định khi phân vân

> Hỏi: *nếu người dân chỉ đọc điều khoản (a) mà không đọc điều khoản kia, họ có
> áp dụng sai không?* Có → đưa vào. Không → bỏ.

---

## 3. HỆ QUẢ KHI SO SÁNH VỚI v2

**Không so trực tiếp số F1 giữa v2 và v4 được** — hai quy ước chú giải khác
nhau thì hai thước đo khác nhau. Trong báo cáo phải nói rõ.

Cách trình bày đúng: chạy **cùng một hệ thống** trên cả hai tập, và nêu rằng
chênh lệch phản ánh **quy ước chú giải**, không phải năng lực hệ thống.

---

## 4. RỦI RO NHIỄM — GHI RÕ ĐỂ HỘI ĐỒNG BIẾT

Tập này do trợ lý máy soạn, mà chính trợ lý đó đã tinh chỉnh hệ thống trên tập
v2. Đó là rủi ro nhiễm thật. Các biện pháp đã áp dụng:

- Câu hỏi **suy ra từ cấu trúc kho** (các cạnh `REFERS_TO` đích danh khoản), có
  hệ thống, không chọn theo chỗ hệ mạnh.
- **Không chạy hệ thống trong lúc soạn.** Đáp án đặt bằng cách đọc văn bản luật
  và lần dẫn chiếu một cách máy móc theo §2.
- Mọi trích dẫn đáp án đã được **kiểm tồn tại thật trong đồ thị**.
- Cờ `review.da_duyet = false` ở mọi câu.

**Vẫn cần người rà lại trước khi dùng làm số chính thức**, đặc biệt các câu
thuộc lĩnh vực hộ tịch / nuôi con nuôi (lĩnh vực của [B]).
