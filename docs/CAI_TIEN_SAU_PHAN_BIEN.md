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

**Tìm đúng điều nhưng sai khoản.** Đo trên cùng một thang: hệ lấy đúng **Điều**
chứa đáp án ở mức 0,806, nhưng lấy đúng **Khoản** chỉ **0,737**. Một điều luật
có thể gồm hàng chục khoản quy định những trường hợp khác nhau, nên chỉ vào đúng
điều mà sai khoản thì người dùng vẫn nhận câu trả lời sai.

**Ba nhóm câu bị bộ lọc làm hỏng, theo hai kiểu khác nhau.**

*Trả về rỗng hoàn toàn:* câu có mốc thời gian quá khứ (mốc lọc hiệu lực lấy nhầm
năm xảy ra sự việc nên loại sạch văn bản mới), và các thủ tục hộ tịch nằm ngoài
sáu thủ tục được lập chỉ mục (đã kiểm ba ca: giám hộ, khai tử, cải chính). Hai
nhóm này hệ không tìm được văn bản nào, tức hỏng hoàn toàn chứ không phải trả
lời kém.

*Loại mất văn bản chứa đáp án:* câu không nêu tỉnh bị gán cứng "toàn quốc" nên
văn bản cấp tỉnh bị lọc ra, trong khi nhiều câu về lệ phí và hạn mức có đáp án
nằm đúng ở cấp tỉnh. Nhóm này vẫn có ngữ cảnh, nhưng thiếu đúng phần cần.

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

**Kiểm định ý nghĩa thống kê** (cùng phương pháp Bảng 4.4 của báo cáo — bootstrap
ghép cặp 10 000 lần, seed 42, và Wilcoxon signed-rank):

| đại lượng | giá trị |
|---|---|
| chênh lệch trung bình Δ | **+0,116** |
| khoảng tin cậy 95% | **[+0,064; +0,171]** |
| Wilcoxon signed-rank (p) | **0,000069** |
| thắng / thua / hoà | 26 / 4 / 93 |

Khoảng tin cậy không chứa 0, nên mức tăng không phải dao động ngẫu nhiên.

### Mức tăng có phải chỉ vì nạp thêm ngữ cảnh?

Đây là câu hỏi phải tự đặt ra: nếu cấu hình mới đơn giản là đưa nhiều chữ hơn
vào ngữ cảnh thì bao phủ tăng là đương nhiên, và không nói lên gì về cơ chế.

| bước | đơn vị vào ngữ cảnh | thêm bao nhiêu | mức tăng |
|---|---|---|---|
| trước cải tiến | 16,9 | — | — |
| + lần theo dẫn chiếu | 20,2 | +3,3 | +0,016 |
| + cross-encoder | **20,2** | **+0,0** | **+0,047** |
| + mở rộng vùng tìm kiếm | 20,5 | +0,3 | +0,053 |

**Đóng góp lớn nhất đến từ bước không thêm một đơn vị nào.** Cross-encoder chỉ
xếp lại thứ tự các đơn vị đã chọn, nên +0,047 của nó hoàn toàn không thể giải
thích bằng lượng ngữ cảnh.

Với bước lần theo dẫn chiếu — bước duy nhất thực sự nạp thêm — đã chạy **nhánh
đối chứng**: thêm **đúng bằng số đơn vị đó** nhưng chọn theo điểm xếp hạng thông
thường thay vì theo quan hệ dẫn chiếu.

| cách chọn đơn vị thêm vào | bao phủ | mức tăng |
|---|---|---|
| không thêm | 0,761 | — |
| thêm theo điểm xếp hạng *(đối chứng)* | 0,775 | +0,014 |
| **thêm theo quan hệ dẫn chiếu** | **0,797** | **+0,037** |

Cùng lượng ngữ cảnh, chọn theo dẫn chiếu hơn chọn theo điểm xếp hạng **+0,023**.
Phần chênh này là đóng góp của **cơ chế**, không phải của lượng chữ.

> Nhánh đối chứng đo ở đợt trước trên 121 câu và dùng bộ lập kế hoạch khác, nên
> con số tuyệt đối không so thẳng được với bảng ở trên; nó dùng để trả lời câu
> hỏi "cơ chế hay lượng ngữ cảnh", không dùng làm số công bố.

### 3.2. Ba lỗi khiến hệ trả về rỗng — đã sửa

Mốc lọc hiệu lực lấy nhầm năm xảy ra sự việc; câu không nêu tỉnh bị gán cứng
"toàn quốc"; thủ tục ngoài danh mục làm bộ lập kế hoạch bỏ trống lĩnh vực. Cả ba
nhóm câu nay đều trả lời được.

### 3.3. Tóm tắt do máy sinh: 0 câu thua, 118/121 câu cho kết quả y hệt

Khâu này tự động hoá được, và chất lượng định tuyến không phụ thuộc vào cách
diễn đạt của người viết tóm tắt.

*So ghép cặp trên 121 câu, bốn cấu hình truy hồi: 118 câu cho kết quả y hệt,
3 câu tóm tắt máy **tốt hơn**, 0 câu tệ hơn. Đo ở đợt trước, chưa chạy lại trên
cấu hình hiện tại; kết luận định tính không đổi.*

### 3.4. Bộ chấm độc lập: xác nhận cảnh báo của chính báo cáo

Mô hình sinh câu trả lời là Gemini 2.5 Pro, và bộ chấm của báo cáo **cũng chính
là Gemini 2.5 Pro** (Bảng 3.6). Báo cáo đã tự nêu rủi ro ở mục 4.4.1: điểm có
thể lệch theo hướng dễ dãi với đầu ra của chính mô hình, *"con số thực tế nhiều
khả năng thấp hơn 88,1%"*.

Chấm lại cùng bộ kết quả bằng hai bộ chấm khác:

| bộ chấm | quan hệ với mô hình sinh | tỉ lệ hậu thuẫn |
|---|---|---|
| Gemini 2.5 Pro *(số của báo cáo, Bảng 4.7)* | **chính là mô hình sinh** | **88,1%** |
| Qwen3-4B-Instruct | khác nhà phát triển, khác kiến trúc | 83,7% |
| Gemini 2.5 Flash | cùng nhà, khác mô hình | 79,0% |

**Số liệu xác nhận dự đoán của báo cáo, không bác bỏ nó.** Bộ chấm chính là mô
hình sinh cho điểm **cao nhất**; hai bộ chấm không phải nó đều cho điểm **thấp
hơn**, kém 4,4 và 9,1 điểm phần trăm. Đây đúng chiều mà hiện tượng thiên lệch tự
đề cao dự đoán.

Giá trị của phép đo mới nằm ở chỗ **định lượng được mức lệch** và cho thấy điểm
không sụp đổ: kể cả với bộ chấm hoàn toàn độc lập, tỉ lệ vẫn ở mức 79–84%. Khi
trình bày nên nêu **79,0%** làm cận dưới thận trọng thay vì chỉ nêu 88,1%.

**Phát hiện phụ.** Bản Qwen3-4B đã tinh chỉnh cho 99,7% — gần như không phê phán
gì. Nó được dạy sinh câu trả lời có trích dẫn, không được dạy đánh giá trích
dẫn. Bộ chấm cần độc lập cả về tác vụ huấn luyện, không chỉ về nhà phát triển.

### 3.5. Mô hình sinh: thêm hàng thứ năm vào Bảng 4.13

| mô hình sinh | Naive RAG | GraphRAG | chênh lệch |
|---|---|---|---|
| Gemini 2.5 Pro | 0,435 | 0,617 | +0,182 |
| **Cục bộ 30B, hai ví dụ mẫu** ⟵ **mới** | **0,317** | **0,583** | **+0,266** |
| Cục bộ 4B gốc, hai ví dụ mẫu | 0,239 | 0,511 | +0,272 |
| Cục bộ 4B đã tinh chỉnh, không ví dụ mẫu | 0,301 | 0,402 | +0,101 |
| Cục bộ 4B gốc, không ví dụ mẫu | 0,154 | 0,131 | **−0,022** |

*Bốn hàng lấy nguyên từ Bảng 4.13 của báo cáo. Hàng 30B do **[B] đo**, nhóm chưa
đo lại độc lập. Toàn bảng tính trên trung bình 137 câu, đúng cơ sở của Bảng 4.13
— khác cơ sở ghép cặp 123 câu ở §3.1, nên hai bảng không so thẳng với nhau.*

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

**Giới hạn của phép đo này:** 10 câu là mẫu nhỏ so với 123 câu của ba lĩnh vực
gốc, nên con số 0,850 nên đọc như một chỉ báo chứ không phải phép đo có cùng độ
tin cậy. Tập chuẩn do nhóm soạn theo cùng quy ước chú giải, **cả hai thành viên
đã rà và duyệt toàn bộ 12 câu**, và 22/22 trích dẫn đáp án đã được kiểm tồn tại
thật trong đồ thị.

**Không phá vỡ phần cũ.** Bằng chứng là phép kiểm thoái lui ở bảng trên — 123
câu, 0 câu lệch. Ba câu demo ngoài phạm vi cũng vẫn từ chối đúng sau khi nạp.

*Một phép kiểm yếu cần nói rõ:* ngay sau khi nạp có đối chiếu 13 câu demo đất
đai và thấy **số lượng** trích dẫn không đổi, nhưng phép kiểm đó không so nội
dung. Đo lại ngày 19/08 cho thấy một số câu **có** đổi trích dẫn dù số lượng giữ
nguyên. Kết luận "không phá vỡ phần cũ" vì vậy dựa vào phép kiểm thoái lui 123
câu, không dựa vào phép đối chiếu 13 câu đó.

---

## 4. NHỮNG ĐIỀU RÚT RA

**Vị trí của một thành phần trong hệ quan trọng ngang bản thân thành phần đó.**
Cross-encoder từng bị bác bỏ, nhưng khi đổi vị trí trong đường xử lý thì cho kết
quả dương. Kết luận "kỹ thuật X không hiệu quả" nhiều khi thực chất là "X được
đặt sai chỗ".

**Lấy đúng điều khoản nhiều hơn không tự động làm câu trả lời tốt hơn.** Tỉ lệ
lấy đúng tăng +0,116 nhưng F1 của khâu sinh không thay đổi. Nguyên nhân: hệ trích
trung bình **2,71** điều khoản trong khi đáp án chuẩn chỉ cần **1,57** *(đo trên
tập kiểm thử mới, 28 câu)*. Nếu chọn lọc trích dẫn tối ưu, F1 đạt **0,742** so
với 0,571 hiện tại *(đo trên mẫu 55 câu của tập v2)* — phần cải thiện tiềm năng
này lớn hơn toàn bộ mức cải thiện của đợt này. Khâu hạn chế nhất đã chuyển từ
truy hồi sang chọn trích dẫn.

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

> Mục này mô tả **hai kịch bản khác nhau**. Phần ngay dưới là kịch bản **mở hai
> cổng đối chiếu trước/sau**. Phần *"Ba câu trình bày trên cổng 8001"* là kịch
> bản **chỉ mở một cổng** — đây là kịch bản đã chọn cho ngày bảo vệ. Thứ tự câu
> ở hai kịch bản khác nhau vì mục đích khác nhau: đối chiếu cần câu có khác biệt
> giải thích được trong một câu, trình bày một cổng cần phủ đủ bốn thách thức.

**Ví dụ chính (kịch bản đối chiếu) — câu A4.** *"Hồi trước nghe nói ở TP.HCM một hộ được tới 300 mét
vuông đất ở, sao giờ nghe nói chỉ còn 250? Người ta đổi quy định hồi nào vậy?"*

Câu này tự nó hỏi về một **sự thay đổi quy định**, nên tính năng mới trả lời
đúng thứ người hỏi cần. Bản sau cải tiến hiện thêm **khối cảnh báo** ngay trước
câu trả lời:

> *Quy định về nội dung này đã thay đổi: Quyết định 18/2016 hết hiệu lực từ
> 30/09/2024, được thay thế bởi Quyết định 69/2024 (hiệu lực từ 30/09/2024).*

Bản trước cải tiến vẫn trả lời đúng nội dung nhưng **không có khối cảnh báo
này**.

**Phải nói rõ chiều ngược lại.** Bản trước dùng ba trích dẫn, bản sau chỉ hai:
bản trước có thêm một lưu ý phân biệt mức 250 m² của quy định cũ (áp cho khu quy
hoạch phát triển đô thị) với mức 250 m² của quy định mới (áp cho khu vực nông
thôn). Lưu ý đó **đúng và hữu ích**, và bản sau bỏ mất. Vậy phép đổi ở đây là
được khối cảnh báo tất định, mất một lưu ý phân biệt — không phải thắng sạch.

**Một lỗi của câu này đã sửa ngày 19/08.** Trước đó bản sau viết *"sắp có hiệu
lực"* cho mốc 30/09/2024 vốn đã qua gần hai năm, mâu thuẫn ngay với khối cảnh báo
phía trên ghi *"hết hiệu lực từ 30/09/2024"*. Nguyên nhân: lời nhắc nhắc tới
*"thời điểm câu hỏi"* ở nhiều chỗ nhưng **không chỗ nào nói thời điểm đó là khi
nào**, nên mô hình phải suy ngày hiện tại từ tri thức huấn luyện. Đã cấp ngày
tường minh cho lời nhắc — xem *"Cấp ngày hiện tại cho lời nhắc"* bên dưới.

**Ví dụ dự phòng (kịch bản đối chiếu) — câu A3.** *"Hạn mức giao đất ở cho cá nhân do cơ quan nào quy
định, và con số cụ thể hiện nay tại TP.HCM…"* Bản trước dẫn **Luật Đất đai 2013
Điều 103 Khoản 4** — luật đã hết hiệu lực, và điều đó nói về *"đất có vườn, ao"*,
không liên quan hạn mức. Bản sau dẫn **Luật Đất đai 2024 Điều 195, 196** — đúng
điều trao thẩm quyền cho UBND tỉnh. Nguyên nhân chữa được: Quyết định 69/2024
ngay Điều 1 có câu *"theo khoản 2 Điều 196"*, cơ chế lần theo dẫn chiếu đi theo
quan hệ đó.

> **A3 có một điểm trừ nhìn thấy được.** Bản sau nêu thiếu mức **200 m²** cho
> thị trấn các huyện, trong khi bản trước nêu đủ ba mức. Đã kiểm: điều khoản đó
> **có trong ngữ cảnh** ở cả hai bản, nên đây là bộ sinh bỏ sót khi phải xử lý
> nhiều ngữ cảnh hơn, không phải lỗi truy hồi. Nếu dùng A3 thì nên chủ động nói
> ra trước khi bị hỏi.

### Hạn chế của cảnh báo thay đổi

Cơ chế phát hiện thay đổi hiện dựa trên việc **tập văn bản ứng viên có chứa văn
bản đã hết hiệu lực hay không**, chứ chưa xét văn bản đó có liên quan tới nội
dung câu hỏi không. Vì vậy có câu nhận cảnh báo **lạc đề** — ví dụ câu hỏi hạn
mức ở Đồng Nai lại nhận cảnh báo về Luật Đất đai 2013. Tránh các câu hỏi về Đồng
Nai khi muốn trình diễn tính năng này; dùng câu A4 hoặc câu về TP.HCM.

**Ngày bảo vệ chỉ ba bước:** mở máy → mở Docker Desktop → gõ một lệnh.

```bash
cd ~/Documents/University/2526_Sem2/Thesis/vn-legal-graphrag && ./scripts/bao-ve.sh
```

Mặc định **chỉ mở cổng 8001** — cổng trình bày. Thêm `--doi-chieu` để mở kèm cổng
8000. Mở một cổng nhanh hơn thật: hai tiến trình cùng nạp mô hình thì tranh CPU,
đo thấy mỗi câu chậm thêm 5–8 giây.

Kiểm lại bất cứ lúc nào bằng `python scripts/nghiem_thu_demo.py` — bản nghiệm thu
kiểm sáu điều, mỗi điều là một thứ đã hỏng thật: cấu hình cổng, câu chạy không
lỗi, mọi câu trúng bộ nhớ đệm, không còn lỗi thì, mọi trích dẫn tra được nguyên
văn, và ba câu trình bày đúng số trích dẫn đã đo. Lưu ý: **đừng hỏi câu nào trong
lúc nó chạy** — máy chủ chỉ nhận một câu tại một thời điểm nên bạn sẽ bị chặn.

Kịch bản tự làm hết: khởi động container, chờ Neo4j nhận truy vấn, kiểm dữ liệu
đủ hay không, mở hai cổng với đúng cấu hình, **tự kiểm lại hai cổng có khác cấu
hình thật không**, rồi mở trình duyệt.

| cổng | bản | cấu hình |
|---|---|---|
| 8000 | trước cải tiến | tắt cả ba cơ chế, tham số mặc định của báo cáo |
| 8001 | sau cải tiến | đủ ba cơ chế + cảnh báo quy định đã thay đổi |

> Cấu hình sau cải tiến cần **năm biến môi trường** đặt đúng. Thiếu một biến thì
> demo chỉ thể hiện một phần mức cải tiến mà **nhìn giao diện không phát hiện
> được** — vì vậy chúng được gói trong kịch bản thay vì gõ tay. Hai biến `SF_*`
> phải đặt trước khi khởi động server vì chúng được đọc lúc nạp module.

Mười lăm câu demo đã nạp sẵn kết quả cho đúng hai cấu hình này. Nếu tự chạy tay
và đổi bất kỳ biến nào thì cache trượt, mỗi câu mất khoảng 50 giây.

Kịch bản còn **chạy trước một câu ở mỗi cổng** rồi mới báo sẵn sàng. Mô hình nhúng
và cross-encoder chỉ nạp ở lần hỏi đầu tiên của tiến trình, nên nếu không hâm thì
câu hỏi đầu tiên trước hội đồng đúng là câu chậm nhất buổi. Từ lúc gõ lệnh tới
lúc sẵn sàng: khoảng 50 giây.

### Ba câu trình bày trên cổng 8001

Nếu chỉ trình bày một cổng thì dùng 8001 và ba câu dưới đây — ba câu này phủ cả
bốn thách thức, và mỗi câu mất 15–25 giây.

| # | câu | cho thấy điều gì | tỉ lệ đúng trước → sau |
|---|---|---|---|
| 1 | *Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định, và con số cụ thể hiện nay tại TP.HCM được quy định ở văn bản nào?* | đa tầng văn bản: Luật trao quyền → Quyết định tỉnh ra số | 0,286 → **0,750** |
| 2 | *Hồi trước nghe nói ở TP.HCM một hộ được tới 300 mét vuông đất ở, sao giờ nghe nói chỉ còn 250?…* | đa phiên bản + khối cảnh báo | 0,667 → **0,800** |
| 3 | *Đăng ký lại khai sinh mà không còn bản sao giấy khai sinh cũ thì cần giấy tờ gì?* | đa lĩnh vực (hệ tự sang hộ tịch) + lần theo dẫn chiếu | không có trong tập chuẩn |

Câu 3 là ví dụ rõ nhất của quan hệ dẫn chiếu: Thông tư 04/2020 Điều 9 Khoản 3 mở
đầu bằng *"trường hợp không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này"*.
Bản trước dẫn Khoản 3 chung chung; bản sau dẫn đúng **Điểm a** và kéo thêm Nghị
định 123/2015 Điều 26 Khoản 1 điểm c. Đã đối chiếu với văn bản gốc: đúng cả bốn
trích dẫn.

**Câu cần tránh, đã đo ngày 19/08:**

*Câu B1* (*"…theo quy định cũ (Quyết định 18/2016) và quy định hiện hành (Quyết
định 69/2024) khác nhau như thế nào?"*) — hệ trả lời *"Tôi không có thông tin về
Quyết định 69/2024"* dù câu hỏi nêu đích danh. Lỗi này có ở **cả hai cổng**,
không do đợt cải tiến.

*Hai câu bẫy ngoài phạm vi* (lệ phí trước bạ, thuế thu nhập cá nhân) — mất 70–76
giây vì kéo về nhiều văn bản nên cross-encoder chạy nhiều lượt. Kết quả vẫn đúng
là từ chối trả lời; nếu dùng thì nói trước là sẽ lâu.

### Cấp ngày hiện tại cho lời nhắc

Lời nhắc của khâu sinh nhắc tới *"thời điểm câu hỏi"* ở bốn chỗ nhưng không định
nghĩa nó, nên mô hình suy ngày hiện tại từ tri thức huấn luyện và gọi mốc đã qua
là *"sắp có hiệu lực"*. Đã bổ sung một khối nêu rõ hôm nay là ngày nào và chiều
so sánh: mốc trước ngày đó là *đã* có / *đã* hết hiệu lực, chỉ mốc sau mới được
viết *sắp*.

Đo trên 15 câu demo, sinh lại toàn bộ:

| | không cấp ngày | có cấp ngày |
|---|---|---|
| số lỗi thì | 6 (ở 4 câu) | **0** |
| F1 Khoản, 14 câu có đáp án chuẩn | 0,576 | 0,568 |
| ba câu trình bày | — | **trích dẫn không đổi một cái nào** |

Lỗi thì hết sạch; F1 phẳng trong dao động của mẫu 14 câu. Một câu tụt 0,286 →
0,000 (hồ sơ dở dang): mô hình vẫn nêu *Điều 138 Luật Đất đai 2024* trong câu văn
nhưng không đóng vào thẻ trích dẫn nên thước đo không đếm — lập luận đúng hơn
trước, chỉ mất phần máy đọc. Câu đó không nằm trong ba câu trình bày.

**Hai điều kiện thiết kế, cả hai đều bắt buộc:**

*Mặc định TẮT.* Không truyền ngày thì lời nhắc **giống hệt từng ký tự** bản đã
dùng để đo — đã đối chiếu bằng cách nạp song song bản mã trước và sau khi sửa rồi
băm cả hai lời nhắc, cùng mã băm ở cả hai chế độ trả lời. Khóa bộ nhớ đệm băm
trên toàn bộ lời nhắc, nên nếu bật mặc định thì mọi kết quả đã công bố trượt cache
và không tái lập được. Bốn kiểm thử khoá điều kiện này.

*Ngày ghi cứng, không lấy ngày hệ thống.* Ngày nằm trong lời nhắc nên nằm trong
khóa cache: lấy `date` thì hâm cache hôm nay, hôm sau demo là trượt sạch và phải
gọi mô hình trực tiếp. Giá trị đặt một chỗ duy nhất trong `scripts/bao-ve.sh`, và
`precache_demo` đọc **cùng biến môi trường** nên hai bên không thể lệch nhau.

Chỉ đặt cho **cổng 8001** — cổng trình bày. Cổng 8000 giữ nguyên lời nhắc cũ nên
bộ nhớ đệm sẵn có của nó vẫn trúng.

> **Hệ quả phải nói rõ nếu mở hai cổng để đối chiếu:** ngày là khác biệt **thứ
> tư**, ngoài ba cơ chế. Cổng 8000 sẽ viết *"sắp có hiệu lực"* cho mốc đã qua,
> cổng 8001 thì không. Chỗ khác biệt đó là công của việc cấp ngày, **không phải**
> công của ba cơ chế truy hồi.

**Một lỗi tính tất định đã sửa ngày 19/08.** Truy vấn duyệt đồ thị ở Giai đoạn 2
không có `ORDER BY`, nên Neo4j trả cùng tập văn bản với thứ tự khác nhau giữa hai
lần chạy; phần nạp điều khoản chuyển tiếp ăn theo thứ tự đó nên cùng một câu hỏi
lúc cho 24 khối ngữ cảnh, lúc 25. Hệ quả: khởi động lại máy có thể rơi vào biến
thể chưa nạp sẵn kết quả. Đã sửa **bên trong phần chuyển tiếp**, không đụng vào
đường truy hồi đã dùng để đo — kiểm lại 15/15 câu không đổi trích dẫn nào.

> **Nếu mở hai cổng thì chỉ dùng A3 để đối chiếu.** Đo lại ngày 19/08 sau khi sửa
> lỗi tính tất định: **mười trên mười lăm** câu cho trích dẫn khác nhau giữa hai
> bản (câu 2, 3, 4, 5, 6, 8, 9, 10, 14, 15), nhưng chỉ A3 cho khác biệt sạch và
> giải thích được trong một câu. Chín câu còn lại đổi theo hướng khó biện giải nhanh —
> có câu bản mới bỏ bớt nghị định hướng dẫn, có câu thêm văn bản của tỉnh khác,
> có câu chỉ khác ở cách hiển thị nhãn phụ lục. Đừng ứng biến sang câu khác khi
> đang trình bày.

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

Tỉ lệ hậu thuẫn 88,1% trong báo cáo do **chính mô hình sinh** chấm. Hai bộ chấm
độc lập cho 83,7% và 79,0%. Nên nêu **79,0% làm cận dưới thận trọng** và nói rõ
điều này trước, vì báo cáo đã tự cảnh báo ở mục 4.4.1 và hội đồng có thể hỏi
tới.

**Hai dạng câu cần tránh khi demo:** câu có đáp án nằm trong bảng biểu (khâu sinh
chưa nhận bảng làm căn cứ) và câu về điều kiện nhận con nuôi (hệ lấy nhầm điều
khoản về nuôi con nuôi có yếu tố nước ngoài).
