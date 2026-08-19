# Cải tiến sau phản biện

**12–19/08/2026** · Nguồn sự thật: `baocao.pdf`; số nào không có trong báo cáo
đều được ghi rõ là đo mới.

> Báo cáo chốt **chín thực thể, mười quan hệ**, kho **32 văn bản, ba lĩnh vực**.
> Đợt này thêm **quan hệ thứ mười một**, mở kho lên **36 văn bản, bốn lĩnh vực**,
> và thêm **một hàng vào Bảng 4.13**. Việc mở rộng kho đã được kiểm chứng là
> **không làm thay đổi kết quả của ba lĩnh vực cũ** (§3.6), nên số liệu ở §3.1
> so sánh được với báo cáo.

---

## 1. VẤN ĐỀ TRƯỚC CẢI TIẾN

**Tìm đúng văn bản nhưng chỉ sai điều khoản.** Norm Recall đã đạt 0,829, tức hệ
hầu như luôn tìm đúng *văn bản*. Nhưng Luật Đất đai có gần 300 điều; tìm đúng
luật mà chỉ sai điều thì câu trả lời vẫn sai. Tỉ lệ lấy đúng điều khoản chỉ
**0,737**.

**Không trả lời được ba nhóm câu.** Câu có mốc thời gian quá khứ, câu không nêu
tỉnh, và mọi thủ tục hộ tịch nằm ngoài sáu thủ tục được lập chỉ mục. Với ba nhóm
này hệ trả về rỗng, tức là hỏng hoàn toàn chứ không phải trả lời kém.

**Không phát hiện được quy định đã thay đổi.** Hệ trả lời theo văn bản hiện
hành, không cảnh báo cho người nộp hồ sơ từ trước.

**Hai câu hỏi về phương pháp chưa có số liệu trả lời.** Phần tóm tắt văn bản do
người viết có ảnh hưởng bao nhiêu đến kết quả? Khâu chuẩn bị văn bản có tự động
hoá được không?

**Mới ba lĩnh vực và hai mô hình sinh.** Chưa chứng minh được kiến trúc dùng
cho lĩnh vực mới, và câu hỏi nghiên cứu số 4 của báo cáo — *"ưu thế của GraphRAG
có phụ thuộc vào việc chọn mô hình sinh hay không?"* — mới trả lời được một phần.

---

## 2. CƠ CHẾ MỚI VÀ NGHIÊN CỨU MỚI

### 2.1. Lần theo dẫn chiếu giữa các điều khoản — quan hệ thứ mười một

Văn bản luật thường xuyên trỏ sang nhau: *"theo khoản 2 Điều 196"*, *"trường hợp
không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này"*. Các câu trỏ này
không chứa nội dung, chỉ chứa địa chỉ. Vì vậy tìm kiếm dựa trên mức độ giống
nhau về từ ngữ không thể tìm ra điều khoản được trỏ tới, trong khi người đọc bắt
buộc phải mở sang đó mới hiểu đủ.

Cách làm: đọc toàn bộ kho văn bản, nhận diện mọi câu dẫn chiếu, xác định chúng
trỏ tới điều khoản cụ thể nào. Kết quả được **3919 quan hệ** trên kho dùng để
đo, **5366** sau khi thêm lĩnh vực lao động.

Ba trường hợp cần xử lý riêng: dẫn chiếu nêu tên luật mà kho có hai bản khác năm
(chọn bản có hiệu lực tại thời điểm văn bản dẫn chiếu được ban hành); dẫn chiếu
nội bộ dạng *"khoản 1 Điều này"* (cần biết đang ở điều nào); và địa chỉ nằm
trong ghi chú sửa đổi, vốn trỏ tới văn bản sửa chứ không phải dẫn chiếu, nên
phải loại bỏ.

### 2.2. Cross-encoder xếp lại thứ tự trong từng văn bản

Cơ chế này đã từng được thử và bị bác bỏ khi cho nó tham gia *chọn văn bản*: nó
đưa lên những đoạn trùng từ ngữ nhưng thuộc văn bản sai. Lần này chỉ dùng nó để
**xếp lại thứ tự bên trong văn bản đã được chọn**. Cùng một mô hình, đặt ở vị
trí khác trong đường xử lý, kết quả chuyển từ âm sang **+0,047**.

### 2.3. Mở rộng vùng tìm kiếm

Nâng số ứng viên lấy ra ở bước tìm kiếm ngữ nghĩa và bỏ hệ số chấm theo độ hiếm
của khái niệm: **+0,053**.

### 2.4. Phát hiện quy định đã thay đổi

Cần phân biệt hai khái niệm thường bị nhầm. **Hiệu lực hồi tố** là nguyên tắc
của luật hình sự, nằm ngoài phạm vi đề tài. **Điều khoản chuyển tiếp** là quy
định do chính văn bản đặt ra để xử lý hồ sơ nộp trước ngày có hiệu lực, và đây
mới là tình huống người dân gặp phải.

Khi tập văn bản ứng viên có văn bản đã hết hiệu lực, hệ tìm văn bản thay thế
theo mốc thời gian, nạp thêm điều khoản chuyển tiếp, và sinh một câu cảnh báo
đặt trước câu trả lời. Hệ không tự kết luận người dùng thuộc quy định cũ hay
mới, vì điều đó phụ thuộc vào hồ sơ cụ thể mà hệ không có.

### 2.5. Ba nghiên cứu kiểm chứng

**Tóm tắt do máy sinh.** Cho mô hình viết lại toàn bộ phần tóm tắt văn bản, rồi
đo lại toàn hệ.

**Bộ chấm độc lập.** Chấm lại 295 trích dẫn bằng hai bộ chấm khác ngoài bộ chấm
đã dùng trong báo cáo.

**Mô hình sinh cục bộ 30B.** Bổ sung một hàng vào Bảng 4.13 của báo cáo. Đây là
mô hình hỗn hợp chuyên gia, mỗi lượt chỉ kích hoạt khoảng 3 tỉ tham số nên chi
phí suy luận tương đương mô hình 4 tỉ.

---

## 3. KẾT QUẢ

### 3.1. Truy hồi: 0,737 → 0,853

| bước cộng dồn | tỉ lệ lấy đúng điều khoản | mức tăng | thắng/thua |
|---|---|---|---|
| trước cải tiến | 0,737 | — | — |
| + lần theo dẫn chiếu | 0,753 | +0,016 | 9 / 3 |
| + cross-encoder | 0,800 | +0,063 | 17 / 5 |
| + mở rộng vùng tìm kiếm | **0,853** | **+0,116** | **26 / 4** |

Cùng mức tăng đó, chia theo loại câu hỏi:

| thách thức | số câu | tăng trong nhóm | đóng góp vào tổng |
|---|---|---|---|
| Đa lĩnh vực | 32 | **+0,216** | +0,056 |
| Đa tầng văn bản | 30 | **+0,153** | +0,037 |
| Đa địa phương | 31 | +0,069 | +0,017 |
| Đa phiên bản | 30 | +0,019 | +0,005 |
| | **123** | | **+0,116** |

> Cột "tăng trong nhóm" không cộng thẳng lại được. Đa lĩnh vực đạt +0,216 nhưng
> chỉ trên 32 câu, nên phải nhân theo tỉ lệ số câu mới ra +0,116.

**74/123 câu (60%) đã lấy đúng hoàn toàn từ trước cải tiến**, không còn chỗ để
cải thiện. Trên 49 câu còn lại: **cải thiện được 26 câu (53%), mức tăng trung
bình +0,317**.

### 3.2. Ba lỗi khiến hệ trả về rỗng — đã sửa

Mốc lọc hiệu lực lấy nhầm năm xảy ra sự việc; câu không nêu tỉnh bị gán cứng
"toàn quốc"; thủ tục ngoài danh mục làm bộ lập kế hoạch bỏ trống lĩnh vực. Cả ba
nhóm câu nay đều trả lời được.

### 3.3. Tóm tắt do máy sinh: 0 câu thua, 120/121 câu cho kết quả y hệt

Khâu này tự động hoá được, và chất lượng định tuyến không phụ thuộc vào cách
diễn đạt của người viết tóm tắt.

### 3.4. Bộ chấm độc lập: điểm ổn định trong khoảng 79–88%

| bộ chấm | quan hệ với mô hình sinh | tỉ lệ hậu thuẫn |
|---|---|---|
| Gemini 2.5 Pro *(số của báo cáo, Bảng 4.7)* | **trùng** | **88,1%** |
| Qwen3-4B-Instruct | khác nhà phát triển | 83,7% |
| Gemini 2.5 Flash | cùng nhà, khác mô hình | 79,0% |

Bộ chấm gần mô hình sinh nhất lại chấm chặt nhất. Đây là chiều ngược với dự đoán
của hiện tượng thiên lệch tự đề cao, nên lo ngại nêu ở mục 4.4.1 của báo cáo
không được số liệu ủng hộ.

### 3.5. Mô hình sinh: thêm hàng thứ năm vào Bảng 4.13

| mô hình sinh | Naive RAG | GraphRAG | chênh lệch |
|---|---|---|---|
| Gemini 2.5 Pro | 0,435 | 0,617 | +0,182 |
| **Cục bộ 30B, hai ví dụ mẫu** ⟵ **mới** | **0,317** | **0,583** | **+0,266** |
| Cục bộ 4B gốc, hai ví dụ mẫu | 0,239 | 0,511 | +0,272 |
| Cục bộ 4B đã tinh chỉnh, không ví dụ mẫu | 0,301 | 0,402 | +0,101 |
| Cục bộ 4B gốc, không ví dụ mẫu | 0,154 | 0,131 | **−0,022** |

Mô hình cục bộ đạt **0,583** so với Gemini 0,617, kém 0,034 nhưng chạy được ngay
tại chỗ. Với hệ thống xử lý dữ liệu công dân, đây là giá trị thực tế.

> Không phát biểu "GraphRAG thắng trên mọi cấu hình". Hàng cuối bảng là
> **−0,022**, được báo cáo phân tích ở mục 4.7.6. Ưu thế giữ được ở **bốn trên
> năm** cấu hình.

### 3.6. Lĩnh vực mới: đo được, không chỉ minh chứng

Kho tăng từ 32 lên **36 văn bản**, từ 4 549 lên **7 208 điều khoản**, từ ba lên
**bốn lĩnh vực**, trong 3 giờ 10 phút máy chạy. Hai quan hệ *hướng dẫn thi hành*
và **1 447 quan hệ dẫn chiếu** được tạo tự động. Bộ trích xuất viết cho lĩnh vực
đất đai chạy trên văn bản lao động mà không phải sửa dòng nào.

**Mở rộng kho có làm giảm chất lượng ba lĩnh vực cũ không?** Chạy lại đúng 123
câu đó trên kho 36 văn bản rồi so từng câu với kết quả trên kho 32:

| cấu hình | kho 32 | kho 36 | số câu lệch |
|---|---|---|---|
| trước cải tiến | 0,737 | 0,737 | 0 |
| + lần theo dẫn chiếu | 0,753 | 0,753 | 0 |
| + cross-encoder | 0,800 | 0,800 | 0 |
| + mở rộng vùng tìm kiếm | 0,853 | 0,853 | 0 |

**Không câu nào thay đổi.** Thêm một lĩnh vực và bốn văn bản không đánh đổi chất
lượng của ba lĩnh vực cũ.

**Hệ hoạt động tốt đến đâu trên lĩnh vực mới?** Soạn 12 câu chuẩn cho lao động
theo cùng quy ước chú giải, đọc thẳng văn bản luật và không chạy hệ trong lúc
soạn; 10 câu có đáp án nên chấm được:

| | trước cải tiến | sau cải tiến | mức tăng |
|---|---|---|---|
| ba lĩnh vực cũ (123 câu) | 0,737 | 0,853 | +0,116 |
| **lĩnh vực lao động (10 câu)** | **0,700** | **0,850** | **+0,150** · 3 thắng / 0 thua |

Hệ đạt trên lĩnh vực chưa từng được xây dựng cho **đúng mức nó đạt trên ba lĩnh
vực gốc**. Câu LD02 — điều khoản trả lời xác định phạm vi bằng cách dẫn sang
Điều 34 — tăng từ 0,50 lên **1,00**, tức cơ chế dẫn chiếu hoạt động đúng thiết
kế trên văn bản chưa từng thấy.

**Một câu không cải thiện, và nguyên nhân đáng chú ý.** Câu hỏi về thời hạn báo
trước khi nghỉ việc giữ mức 0,00: hệ lấy **Bộ luật Lao động 2012 Điều 37** thay
vì **Bộ luật Lao động 2019 Điều 35**. Bản 2012 đã hết hiệu lực từ 01/01/2021
nhưng vẫn thắng ở bước tìm kiếm ngữ nghĩa vì hai bộ luật cùng chủ đề và cách
diễn đạt gần giống nhau. Đây đúng là thách thức đa phiên bản, xuất hiện lại
trong chính lĩnh vực mới.

**Giới hạn của phép đo này:** 10 câu là mẫu nhỏ, và tập chuẩn do trợ lý máy soạn
từ chính kho văn bản nên cần người rà trước khi dùng làm số chính thức. Toàn bộ
12 câu đang mang cờ chưa duyệt.

**Không phá vỡ phần cũ:** 13 câu demo của lĩnh vực đất đai cho kết quả khớp hoàn
toàn với trước khi nạp; ba câu ngoài phạm vi vẫn từ chối đúng.

---

## 4. NHỮNG ĐIỀU RÚT RA

**Vị trí của một thành phần trong hệ quan trọng ngang bản thân thành phần đó.**
Cross-encoder từng bị bác bỏ, nhưng khi đổi vị trí trong đường xử lý thì cho kết
quả dương. Kết luận "kỹ thuật X không hiệu quả" nhiều khi thực chất là "X được
đặt sai chỗ".

**Lấy đúng điều khoản nhiều hơn không tự động làm câu trả lời tốt hơn.** Tỉ lệ
lấy đúng tăng +0,116 nhưng F1 của khâu sinh không thay đổi: hệ trích trung bình
2,71 điều khoản trong khi đáp án chuẩn chỉ cần 1,57. Đo được phần còn có thể cải
thiện: nếu chọn lọc trích dẫn tối ưu, F1 đạt **0,742**, lớn hơn toàn bộ mức cải
thiện của đợt này. Khâu hạn chế nhất đã chuyển từ truy hồi sang chọn trích dẫn.

**Mô hình sinh càng yếu thì đồ thị càng có giá trị.** Mô hình 4 tỉ tham số hưởng
lợi hơn gấp đôi so với mô hình thương mại nếu tính theo tỉ lệ. Mô hình nhỏ không
có sẵn tri thức pháp luật Việt Nam, nên ngữ cảnh có cấu trúc là nguồn tri thức
duy nhất của nó.

**Tinh chỉnh đổi năng lực phân biệt lấy khả năng tuân thủ định dạng.** Bản tinh
chỉnh làm khâu sinh kém đi (0,402 so với 0,511), đồng thời làm bộ chấm mất khả
năng phê phán (99,7% hậu thuẫn). Hai lần đo độc lập cho cùng một hiện tượng.

**Khả năng dùng cho lĩnh vực mới không đồng đều giữa các khâu.** Khâu truy hồi
dùng được ngay mà không sửa dòng nào, và đạt 0,850 trên lĩnh vực mới so với
0,853 trên ba lĩnh vực gốc. Nhưng khâu sinh phải khai báo thêm: prompt
ghi cố định "lao động" thuộc nhóm ngoài phạm vi, nên hệ từ chối trả lời dù ngữ
cảnh đã có đủ căn cứ. Phát biểu chính xác là *"khâu truy hồi không cần sửa, khâu
sinh cần khai báo phạm vi lĩnh vực mới"*.

---

## 5. TRÌNH BÀY VÀ DEMO

**Ví dụ chính.** Câu hỏi: *"Hạn mức giao đất ở cho cá nhân do cơ quan nào quy
định, và con số cụ thể hiện nay tại TP.HCM được quy định ở văn bản nào?"*

Bản trước cải tiến dẫn **Luật Đất đai 2013 Điều 103 Khoản 4**, nội dung thật là
*"xác định diện tích đất ở đối với trường hợp có vườn, ao"* — vừa hết hiệu lực
vừa sai chủ đề, nhưng về từ ngữ lại rất giống câu hỏi. Bản sau cải tiến dẫn
**Luật Đất đai 2024 Điều 196 Khoản 2**.

Nguyên nhân chữa được: Quyết định 69/2024 của TP.HCM, ngay Điều 1, có câu *"theo
khoản 2 Điều 196"*. Cơ chế lần theo dẫn chiếu đi theo quan hệ đó về đúng điều
luật gốc. Đo cụ thể: ngữ cảnh tăng từ 19 lên 22 đơn vị, tức **thêm 3 và không
mất đơn vị nào**.

**Chạy đối chiếu trên hai cổng:**

```bash
env UI_REFERS_MODE= ./scripts/chay-demo.sh live 8000          # trước cải tiến
env UI_REFERS_MODE=khoan ./scripts/chay-demo.sh live 8001     # sau cải tiến
```

Phải đặt biến môi trường tường minh ở **cả hai lệnh**. Nếu bỏ trống ở lệnh đầu,
biến sẽ được kế thừa sang tiến trình thứ hai và cả hai cổng đều chạy bản mới.
Mười lăm câu demo đã được nạp sẵn kết quả cho cả hai cấu hình.

**Bốn điều cần nêu rõ khi trình bày:**

Kết quả chính của khóa luận là so sánh **GraphRAG với RAG thuần** (Bảng 4.4:
+0,187, khoảng tin cậy 95% [0,108; 0,264], p = 0,00003, thắng/thua/hoà 67/32/24).
Kết quả của đợt cải tiến là so sánh **bản mới với chính hệ cũ** (26/4). Đây là
hai phép so khác nhau.

Mức tăng trên toàn hệ nhỏ hơn mức tăng thực của cơ chế, vì 60% số câu đã đạt
mức tối đa từ trước. Nên nêu kèm mẫu số: *"trên 49 câu còn khả năng cải thiện,
cải thiện được một nửa, mức tăng trung bình +0,317"*.

Ưu thế của kiến trúc giữ được ở **bốn trên năm** cấu hình mô hình sinh, không
phải toàn bộ.

Lấy đúng điều khoản nhiều hơn không đồng nghĩa với câu trả lời tốt hơn.

**Hai dạng câu cần tránh khi demo:** câu có đáp án nằm trong bảng biểu (khâu sinh
chưa nhận bảng làm căn cứ) và câu về điều kiện nhận con nuôi (hệ lấy nhầm điều
khoản về nuôi con nuôi có yếu tố nước ngoài).
