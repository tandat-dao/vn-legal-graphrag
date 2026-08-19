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

**Cổng 8000 — bản trước cải tiến:**

```bash
env UI_REFERS_MODE= UI_RERANK_MODE= UI_CHUYEN_TIEP= SF_DENSE_POOL_MIN=50 SF_RARITY_ALPHA=1.5 ./scripts/chay-demo.sh live 8000
```

**Cổng 8001 — bản sau cải tiến, đủ ba cơ chế:**

```bash
env UI_REFERS_MODE=khoan UI_RERANK_MODE=trong-norm UI_CHUYEN_TIEP=1 SF_DENSE_POOL_MIN=100 SF_RARITY_ALPHA=0 ./scripts/chay-demo.sh live 8001
```

> **Phải đặt đủ năm biến, không được thiếu cái nào.** Ba cơ chế đóng góp
> +0,016 · +0,047 · +0,053; bật lẻ một cái chỉ thể hiện một phần mức cải tiến.
> Hai biến `SF_*` được đọc lúc nạp module nên **phải đặt trước khi khởi động
> server**, không đặt được từ giao diện.
>
> Cũng phải đặt tường minh ở **cả hai lệnh**. Bỏ trống ở lệnh đầu thì biến được
> kế thừa sang tiến trình sau và cả hai cổng cùng chạy bản mới.

Mười lăm câu demo đã được nạp sẵn kết quả cho **đúng hai cấu hình này**. Đổi bất
kỳ biến nào là cache trượt và mỗi câu chạy tươi khoảng 50 giây.

> **Chỉ dùng A3 để đối chiếu trước/sau.** Đo ngày 19/08: bảy trên mười lăm câu
> cho trích dẫn khác nhau giữa hai bản, nhưng chỉ A3 cho khác biệt sạch và giải
> thích được trong một câu. Sáu câu còn lại đổi theo hướng khó biện giải nhanh —
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
