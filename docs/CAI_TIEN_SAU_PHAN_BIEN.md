# Cải tiến sau phản biện

**12–19/08/2026** · Nguồn sự thật: `baocao.pdf`; số nào không có trong báo cáo
đều được ghi rõ là đo mới.

> Báo cáo chốt **chín thực thể, mười quan hệ**, kho **32 văn bản, ba lĩnh vực**.
> Đợt này thêm **quan hệ thứ mười một**, mở kho lên **36 văn bản, bốn lĩnh vực**,
> và thêm **một hàng vào Bảng 4.13**. Mọi phép đo vẫn chạy trên đúng kho 32 văn
> bản của báo cáo.

---

## 1. VẤN ĐỀ TRƯỚC CẢI TIẾN

**Đúng văn bản, sai điều khoản.** Norm Recall đã 0,829 — hệ hầu như luôn tìm
đúng *văn bản*. Nhưng Luật Đất đai có gần 300 điều; đúng luật mà sai điều thì vô
nghĩa. Bao phủ điều khoản chỉ **0,737**.

**Câm với ba nhóm câu.** Câu có mốc quá khứ, câu không nêu tỉnh, và mọi thủ tục
hộ tịch ngoài sáu thủ tục được lập chỉ mục — hệ trả rỗng, không phải trả lời kém.

**Không biết quy định đã đổi.** Trả lời theo văn bản hiện hành, không cảnh báo
người có hồ sơ cũ.

**Hai nghi vấn phương pháp chưa có câu trả lời bằng số.** Tóm tắt do người viết
có phải "cái nạng" không? Khâu chuẩn bị văn bản tự động hoá được không?

**Chỉ ba lĩnh vực, hai mô hình sinh.** Chưa chứng minh kiến trúc dùng được cho
lĩnh vực mới, và câu hỏi nghiên cứu số 4 của báo cáo — *"ưu thế có phụ thuộc mô
hình sinh không?"* — mới trả lời được một phần.

---

## 2. CƠ CHẾ MỚI VÀ NGHIÊN CỨU MỚI

### 2.1. Lần theo dẫn chiếu — quan hệ thứ mười một

Văn bản luật liên tục trỏ sang nhau: *"theo khoản 2 Điều 196"*, *"trường hợp
không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này"*. Những câu trỏ này
**không mang nội dung**, nên tìm kiếm theo độ giống từ ngữ không bao giờ với tới
điều khoản được trỏ đến — dù người đọc buộc phải mở sang đó mới hiểu.

Đọc toàn kho, nhận diện mọi câu dẫn chiếu, phân giải xem nó trỏ tới đâu. Được
**3919 quan hệ** trên kho đo, **5366** sau khi thêm lao động.

Ba ca phải xử lý riêng: dẫn chiếu nêu tên luật mà kho có hai bản (chọn bản có
hiệu lực tại thời điểm ban hành); dẫn chiếu nội bộ *"khoản 1 Điều này"* (phải
biết đang đứng ở đâu); và địa chỉ nằm trong ghi chú sửa đổi (trỏ tới văn bản
sửa, không phải dẫn chiếu — phải loại).

### 2.2. Cross-encoder xếp lại trong từng văn bản

Cơ chế này **đã từng bị bác bỏ** khi cho nó tham gia *chọn văn bản* — nó kéo lên
đoạn trùng từ ngữ nhưng sai văn bản. Lần này chỉ cho nó **xếp lại bên trong văn
bản đã chọn**. Cùng mô hình, khác vị trí, kết quả từ âm thành **+0,047**.

### 2.3. Mở rộng vùng tìm kiếm

Nâng số ứng viên ở bước tìm kiếm ngữ nghĩa, bỏ hệ số chấm theo độ hiếm khái
niệm: **+0,053**.

### 2.4. Phát hiện quy định đã thay đổi

**Hiệu lực hồi tố** là nguyên tắc luật hình sự — ngoài phạm vi. **Điều khoản
chuyển tiếp** mới là thứ người dân gặp. Khi tập ứng viên có văn bản hết hiệu
lực, hệ tìm văn bản thay thế, nạp điều khoản chuyển tiếp, sinh cảnh báo đặt
trước câu trả lời. Hệ **không tự kết luận** người dùng thuộc quy định nào — việc
đó phụ thuộc hồ sơ cụ thể.

### 2.5. Ba nghiên cứu kiểm chứng

**Tóm tắt do máy sinh.** Cho mô hình viết lại toàn bộ tóm tắt rồi đo lại.

**Bộ chấm độc lập.** Chấm lại 295 trích dẫn bằng hai bộ chấm khác ngoài bộ chấm
của báo cáo.

**Mô hình sinh cục bộ 30B.** Thêm một hàng vào Bảng 4.13 — mô hình hỗn hợp
chuyên gia, kích hoạt ~3 tỉ tham số mỗi token nên chi phí suy luận ngang mô hình
4 tỉ.

---

## 3. KẾT QUẢ

### 3.1. Truy hồi: 0,737 → 0,853

| bước cộng dồn | bao phủ | mức tăng | thắng/thua |
|---|---|---|---|
| trước cải tiến | 0,737 | — | — |
| + dẫn chiếu | 0,753 | +0,016 | 9 / 3 |
| + cross-encoder | 0,800 | +0,063 | 17 / 5 |
| + mở vùng tìm kiếm | **0,853** | **+0,116** | **26 / 4** |

Cùng mức tăng đó, cắt theo loại câu hỏi:

| thách thức | số câu | tăng trong nhóm | đóng góp vào tổng |
|---|---|---|---|
| Đa lĩnh vực | 32 | **+0,216** | +0,056 |
| Đa tầng văn bản | 30 | **+0,153** | +0,037 |
| Đa địa phương | 31 | +0,069 | +0,017 |
| Đa phiên bản | 30 | +0,019 | +0,005 |
| | **123** | | **+0,116** |

> Cột "tăng trong nhóm" **không cộng thẳng được** — đa lĩnh vực +0,216 nghe lớn
> nhưng chỉ trên 32 câu. Phải nhân theo tỉ lệ số câu mới ra +0,116.

**74/123 câu (60%) đã đạt bao phủ 1,00 từ trước.** Trên 49 câu thật sự còn chỗ
tăng: **chữa được 26 câu (53%), nâng trung bình +0,317**.

### 3.2. Ba lỗi khiến hệ trả rỗng — đã sửa

Mốc lọc hiệu lực lấy nhầm năm xảy ra sự việc; câu không nêu tỉnh bị chốt cứng
"toàn quốc"; thủ tục ngoài danh mục làm bỏ trống lĩnh vực. Cả ba nhóm nay trả
lời được.

### 3.3. Tóm tắt máy sinh: 0 câu thua, 120/121 câu y hệt

Khâu này tự động hoá được, và tín hiệu định tuyến không phụ thuộc văn phong
người viết.

### 3.4. Bộ chấm độc lập: điểm ổn định 79–88%

| bộ chấm | quan hệ với mô hình sinh | tỉ lệ hậu thuẫn |
|---|---|---|
| Gemini 2.5 Pro *(số báo cáo, Bảng 4.7)* | **trùng** | **88,1%** |
| Qwen3-4B-Instruct | khác nhà | 83,7% |
| Gemini 2.5 Flash | cùng nhà, khác mô hình | 79,0% |

Bộ chấm **gần mô hình sinh nhất lại chấm chặt nhất** — ngược hướng mà thiên lệch
tự đề cao dự đoán. Lo ngại nêu ở mục 4.4.1 của báo cáo không được số liệu ủng hộ.

### 3.5. Mô hình sinh: thêm hàng thứ năm vào Bảng 4.13

| mô hình sinh | Naive RAG | GraphRAG | chênh lệch |
|---|---|---|---|
| Gemini 2.5 Pro | 0,435 | 0,617 | +0,182 |
| **Cục bộ 30B, hai ví dụ mẫu** ⟵ **mới** | **0,317** | **0,583** | **+0,266** |
| Cục bộ 4B gốc, hai ví dụ mẫu | 0,239 | 0,511 | +0,272 |
| Cục bộ 4B tinh chỉnh, không ví dụ mẫu | 0,301 | 0,402 | +0,101 |
| Cục bộ 4B gốc, không ví dụ mẫu | 0,154 | 0,131 | **−0,022** |

Mô hình cục bộ đạt **0,583** so với Gemini 0,617 — kém 0,034 mà chạy được tại
chỗ. Với hệ xử lý dữ liệu công dân, đó là giá trị thực tế.

> **Không nói "thắng trên mọi cấu hình".** Hàng cuối là **−0,022** (báo cáo phân
> tích ở mục 4.7.6). Ưu thế giữ ở **bốn trên năm** cấu hình.

### 3.6. Lĩnh vực mới: 3 giờ 10 phút, không sửa logic truy hồi

Kho 32 → **36 văn bản**, 4 549 → **7 208 điều khoản**, ba → **bốn lĩnh vực**. Hai
quan hệ *hướng dẫn thi hành* và **1 447 cạnh dẫn chiếu** tự hình thành. Bộ trích
xuất viết cho đất đai chạy thẳng trên văn bản lao động không sửa dòng nào.

Mười ba câu demo cũ cho kết quả **khớp y hệt** trước khi nạp; ba câu ngoài phạm
vi vẫn từ chối đúng.

---

## 4. NHỮNG ĐIỀU RÚT RA

**Vị trí của một thành phần quan trọng ngang bản thân nó.** Cross-encoder từng
bị bác bỏ, đổi chỗ trong đường ống thì thành dương. Kết luận "kỹ thuật X không
hiệu quả" thường thực ra là "X đặt sai chỗ".

**Bao phủ tốt hơn không tự thành câu trả lời tốt hơn.** Bao phủ tăng +0,116
nhưng F1 sinh không nhúc nhích: hệ trích 2,71 điều khoản trong khi đáp án chuẩn
chỉ cần 1,57. Đo được dư địa: nếu chọn lọc trích dẫn tối ưu, F1 lên **0,742**
— lớn hơn toàn bộ mức cải thiện đợt này. **Nút thắt đã dịch từ truy hồi sang
chọn trích dẫn.**

**Mô hình càng yếu, đồ thị càng có giá trị.** Mô hình 4 tỉ tham số hưởng lợi hơn
gấp đôi về tương đối. Mô hình nhỏ không có tri thức pháp luật Việt Nam sẵn nên
ngữ cảnh có cấu trúc là toàn bộ nguồn tri thức của nó.

**Tinh chỉnh đánh đổi năng lực phân biệt lấy tuân thủ định dạng.** Bản tinh chỉnh
làm bộ sinh tệ đi (0,402 so với 0,511) *và* làm bộ chấm mất tính phê phán (99,7%
hậu thuẫn). Hai lần độc lập, cùng một hiện tượng.

**Tổng quát hoá không đồng đều giữa các khâu.** Truy hồi dùng được cho lĩnh vực
mới không sửa dòng nào — nhưng **khâu sinh phải khai báo phạm vi**: prompt ghi
cứng "lao động" là ngoài phạm vi nên hệ từ chối dù ngữ cảnh đủ căn cứ. Phát biểu
"không sửa gì cả" là quá tay.

---

## 5. TRÌNH BÀY VÀ DEMO

**Ví dụ chính.** *"Hạn mức giao đất ở do cơ quan nào quy định, con số hiện nay ở
TP.HCM ở văn bản nào?"* — bản cũ dẫn **Luật Đất đai 2013 Điều 103** (*"đất có
vườn, ao"*: vừa hết hiệu lực vừa sai chủ đề, nhưng rất giống câu hỏi về từ ngữ);
bản mới dẫn **Luật Đất đai 2024 Điều 196 Khoản 2**. Chữa được vì Quyết định
69/2024 của TP.HCM, ngay Điều 1, có câu *"theo khoản 2 Điều 196"* — cơ chế lần
theo dẫn chiếu đi đúng dây đó. Đo cụ thể: 19 → 22 đơn vị, **thêm 3, không mất
cái nào**.

**Chạy đối chiếu hai cổng:**

```bash
env UI_REFERS_MODE= ./scripts/chay-demo.sh live 8000          # trước
env UI_REFERS_MODE=khoan ./scripts/chay-demo.sh live 8001     # sau
```

Phải đặt biến tường minh cho **cả hai** — bỏ trống ở lệnh đầu thì biến lây sang
tiến trình sau và cả hai cổng cùng chạy bản mới. Mười lăm câu demo đã nạp sẵn
kết quả cho cả hai cấu hình.

**Bốn điều phải nêu rõ:**

Kết quả chính của khóa luận là **GraphRAG so với RAG thuần** (Bảng 4.4: +0,187,
CI 95% [0,108; 0,264], p = 0,00003, 67/32/24). Kết quả đợt cải tiến là **bản mới
so với chính hệ cũ** (26/4). Hai thứ khác nhau.

Mức tăng bị pha loãng bởi trần — nêu kèm mẫu số: *"trên 49 câu còn chỗ cải
thiện, chữa được một nửa, +0,317"*.

Ưu thế kiến trúc giữ ở **bốn trên năm** cấu hình, không phải tất cả.

Bao phủ tăng **không** đồng nghĩa câu trả lời tốt hơn.

**Tránh khi demo:** câu có đáp án nằm trong **bảng biểu** (bộ sinh chưa nhận bảng
là căn cứ) và câu về **điều kiện nhận con nuôi** (hệ lấy nhầm điều về con nuôi
nước ngoài).
