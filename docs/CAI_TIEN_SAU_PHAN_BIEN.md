# Các cải tiến sau buổi phản biện

**Thời gian thực hiện:** 12–19/08/2026
**Nguồn sự thật:** `baocao.pdf`. Mọi con số trong tài liệu này hoặc trích từ báo
cáo, hoặc là kết quả đo mới được ghi rõ là mới. Chỗ nào vượt ra ngoài phạm vi
báo cáo đều được nêu tường minh.

> **Quan hệ với báo cáo.** Báo cáo chốt bản thể luận **chín thực thể, mười quan
> hệ**, kho **32 văn bản thuộc ba lĩnh vực**. Đợt cải tiến bổ sung **quan hệ thứ
> mười một** (dẫn chiếu điều khoản, §3.1), mở kho lên **36 văn bản, bốn lĩnh
> vực** (§7), và thêm **một hàng vào Bảng 4.13** của báo cáo (§6.3). Mọi phép đo
> ở §2 vẫn chạy trên **đúng kho 32 văn bản của báo cáo** để so sánh được với số
> liệu đã công bố.

---

## 1. GÓP Ý CỦA CÔ VÀ VIỆC ĐÃ LÀM

| góp ý của cô | việc đã làm | kết quả |
|---|---|---|
| Tự động hoá khâu chuẩn bị văn bản được không? | Cho máy sinh phần tóm tắt thay người viết (§3.5); dựng bộ chuyển văn bản từ nguồn công báo (§6.2) | Máy làm được, **không câu nào tệ đi**; tự động ~60% khâu nạp |
| Khâu người làm (viết tóm tắt) làm sao đảm bảo đúng? | Cùng thí nghiệm trên | Tín hiệu định tuyến **không phụ thuộc người viết** |
| Vấn đề hồi tố có nên xử lý sâu thêm? | Cơ chế phát hiện quy định đã thay đổi + nạp điều khoản chuyển tiếp (§3.4) | Chạy được, có cảnh báo cho người dùng |
| Thêm module về mô hình sinh cục bộ? | Bổ sung mô hình cục bộ 30B vào ma trận Bảng 4.13 (§6.3) | Mô hình cục bộ **gần bằng** mô hình thương mại |
| Thêm bước xử lý, lọc dữ liệu trước khi vào ngữ cảnh? | **Ba cơ chế mới** ở khâu truy hồi (§3.1–3.3) | **+0,116 độ bao phủ** |

---

## 2. KẾT QUẢ KHÂU TRUY HỒI

**Chỉ số:** độ bao phủ điều khoản — hệ có lấy được đúng điều khoản chứa đáp án
vào ngữ cảnh hay không. Đo tất định, không phụ thuộc mô hình sinh.
**Đo trên:** 123 câu có đáp án chuẩn, kho 32 văn bản của báo cáo, sau khi gộp
công việc hai thành viên (`v2_chot_sau_gop.json`).

**Độ bao phủ điều khoản đúng: 0,737 → 0,853**

| bước cộng dồn | độ bao phủ | mức tăng | thắng/thua |
|---|---|---|---|
| Hệ trước cải tiến | 0,737 | — | — |
| + Lần theo dẫn chiếu | 0,753 | +0,016 | 9 / 3 |
| + Xếp lại bằng cross-encoder | 0,800 | +0,063 | 17 / 5 |
| + Mở rộng vùng tìm kiếm | **0,853** | **+0,116** | **26 / 4** |

Bảng trên cắt mức tăng **theo cơ chế** — mỗi hàng bật thêm một cơ chế so với
hàng trên, tính trên cả 123 câu. Bảng dưới cắt **đúng mức tăng đó** theo **loại
câu hỏi**: cùng một cấu hình cuối, cùng một mốc, chỉ chia 123 câu thành bốn nhóm
rồi tính riêng.

| thách thức | số câu | mức tăng trong nhóm | đóng góp vào tổng |
|---|---|---|---|
| Đa lĩnh vực | 32 | **+0,216** | +0,056 |
| Đa tầng văn bản | 30 | **+0,153** | +0,037 |
| Đa địa phương | 31 | +0,069 | +0,017 |
| Đa phiên bản | 30 | +0,019 | +0,005 |
| **cộng có trọng số** | **123** | | **+0,116** |

> **Đọc bảng cho đúng.** Cột "mức tăng trong nhóm" **không cộng thẳng lại được**.
> Đa lĩnh vực +0,216 nghe rất lớn nhưng chỉ trên 32 câu, nên đóng góp vào tổng
> chỉ +0,056. Phải nhân với tỉ lệ số câu mới ra +0,116 — đúng bằng tổng của bảng
> cắt theo cơ chế. Hai bảng là hai lát cắt của **cùng một con số**.

### Vì sao chỉ 26 câu thắng trên 123 câu

Vì **74 câu (60%) đã đạt bao phủ 1,00 từ trước** — hệ vốn đã lấy đúng hết.

Chỉ **49 câu còn dưới 1,00**. Trên đúng nhóm này:

> **26/49 câu được cải thiện (53%), mức tăng trung bình +0,317.**

Con số +0,116 là mức tăng của **toàn hệ thống**; +0,317 cho biết **cơ chế có
thật sự hiệu lực hay không** khi gặp câu khó. Nêu cả hai mới đủ.

---

## 3. TỪNG CẢI TIẾN — GIẢI THÍCH

### 3.1. Lần theo dẫn chiếu giữa các điều khoản

**Vấn đề.** Văn bản luật liên tục trỏ sang nhau: *"theo khoản 2 Điều 196"*,
*"trường hợp không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này"*. Những
câu trỏ này **không mang nội dung**, nên tìm kiếm theo độ giống nhau về từ ngữ
không bao giờ với tới điều khoản được trỏ đến. Người đọc thì buộc phải mở sang
đó mới hiểu.

**Cách làm.** Đọc toàn kho, nhận diện mọi câu dẫn chiếu bằng biểu thức chính
quy, rồi phân giải xem nó trỏ tới điều khoản cụ thể nào. Kết quả: **3919 quan
hệ** trên kho 32 văn bản dùng để đo, **5366** sau khi thêm lĩnh vực lao động
(§7). Đây là **quan hệ thứ mười một**, bổ sung so với mười quan hệ trong báo cáo.

Ba trường hợp phải xử lý riêng:

- *"khoản 2 Điều 196 của Luật Đất đai"* — kho có **hai bản** Luật Đất đai (2013
  và 2024). Hệ chọn bản có hiệu lực **tại thời điểm văn bản dẫn chiếu ban hành**.
- *"khoản 1 và khoản 2 Điều này"* — trỏ sang khoản khác trong cùng điều, phải
  biết đang đứng ở điều nào.
- Địa chỉ nằm trong ghi chú sửa đổi trỏ tới **văn bản sửa**, không phải dẫn
  chiếu — phải loại bỏ.

### 3.2. Xếp lại thứ tự bằng cross-encoder

**Vấn đề.** Mô hình nhúng mã hoá câu hỏi và điều khoản thành vector rồi so
khoảng cách — nhanh nhưng thô: hai điều khoản cùng chủ đề trông rất giống nhau
dù chỉ một cái trả lời đúng.

**Cross-encoder** đọc *đồng thời* câu hỏi và điều khoản rồi chấm điểm. Chính xác
hơn nhiều nhưng chậm, không quét cả kho được.

**Điểm đáng chú ý.** Cơ chế này **đã từng bị thử và bác bỏ** trong quá trình làm
khóa luận (ghi trong nhật ký nội bộ, không đưa vào báo cáo vì là kết quả âm):
khi để nó tham gia *chọn văn bản*, nó kéo lên đoạn trùng từ ngữ nhưng sai văn
bản. Lần này chỉ cho nó **xếp lại bên trong từng văn bản đã chọn** — cùng một mô
hình, khác vị trí trong đường ống, kết quả từ âm thành **+0,047**.

*Vị trí của một thành phần trong hệ quan trọng ngang với bản thân thành phần đó.*

### 3.3. Mở rộng vùng tìm kiếm

Nâng số ứng viên ở bước tìm kiếm ngữ nghĩa và bỏ hệ số chấm theo độ hiếm khái
niệm: **+0,053**, nhóm câu đa lĩnh vực hưởng lợi nhiều nhất.

### 3.4. Phát hiện quy định đã thay đổi

**Đáp góp ý về hồi tố.** Cần phân biệt hai khái niệm hay bị gộp:

- **Hiệu lực hồi tố** là nguyên tắc của luật hình sự — ngoài phạm vi đề tài.
- **Điều khoản chuyển tiếp** là quy định do chính văn bản đặt ra để xử lý hồ sơ
  nộp trước ngày có hiệu lực. **Đây mới là thứ người dân gặp phải.**

Khi tập ứng viên có văn bản đã hết hiệu lực, hệ tìm văn bản thay thế theo mốc
thời gian, nạp điều khoản chuyển tiếp, và sinh câu cảnh báo đặt **trước** câu
trả lời. Hệ **không tự kết luận** trường hợp người dùng thuộc quy định cũ hay
mới — nó trình bày cả hai kèm căn cứ, vì việc đó phụ thuộc hồ sơ cụ thể.

### 3.5. Tự động hoá phần tóm tắt văn bản

Mỗi văn bản có đoạn tóm tắt 3–5 câu do người viết, dùng làm tín hiệu định tuyến.
Cho mô hình sinh lại toàn bộ tóm tắt rồi chạy lại phép đo:

**Kết quả: 0 câu thua, 120/121 câu y hệt.**

Khâu này **tự động hoá được**, và tín hiệu định tuyến **không phụ thuộc văn phong
người viết** — phần người làm không phải "cái nạng" nâng đỡ kết quả.

---

## 4. BỐN LỖI THẬT ĐÃ TÌM RA VÀ SỬA

**Bộ lập kế hoạch lấy năm xảy ra sự việc làm mốc lọc hiệu lực.** Câu *"lấn đất
từ 2010 … nay quy hoạch đã điều chỉnh"* bị chốt mốc 2010 → loại sạch Luật Đất
đai 2024. Hai câu trước đây **không tìm được văn bản nào**.

**Câu không nêu địa phương bị chốt cứng "toàn quốc"** → loại sạch văn bản cấp
tỉnh, trong khi nhiều câu có đáp án nằm đúng ở cấp tỉnh.

**Thủ tục ngoài danh mục làm bỏ trống lĩnh vực.** Hệ lập chỉ mục sâu cho sáu thủ
tục; gặp việc hộ tịch ngoài sáu thủ tục đó (giám hộ, khai tử, cải chính), mô
hình trả lĩnh vực rỗng → bước lọc đầu không trả gì → **hệ không trả lời được**.

**Thước đo dùng sai nhà cung cấp mô hình.** Công cụ đo bao phủ dùng một nhà cung
cấp cho bước lập kế hoạch trong khi hệ thật chạy nhà cung cấp khác → hai bên làm
việc trên **kế hoạch truy vấn khác nhau**. Đã đồng bộ và đo lại toàn bộ.

---

## 5. VÍ DỤ MINH HOẠ

> *"Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định, và con số cụ thể
> hiện nay tại TP.HCM được quy định ở văn bản nào?"*

**Trước cải tiến**, hệ dẫn **Luật Đất đai 2013, Điều 103 Khoản 4** — nội dung
thật là *"xác định diện tích đất ở đối với trường hợp có vườn, ao"*. Sai hai
lần: luật đã hết hiệu lực, và sai chủ đề. Nhưng về từ ngữ thì **rất giống** câu
hỏi.

**Sau cải tiến**, hệ dẫn **Luật Đất đai 2024, Điều 196 Khoản 2** — đúng điều
trao thẩm quyền cho UBND tỉnh.

**Vì sao chữa được?** Quyết định 69/2024 của TP.HCM, ngay Điều 1, có câu **"theo
khoản 2 Điều 196"**. Cơ chế lần theo dẫn chiếu đi đúng dây đó về điều luật gốc.

Đo cụ thể: bản cũ lấy 19 đơn vị nội dung, bản mới 22 — **thêm 3, không mất cái
nào**, và một trong ba là Điều 196 Khoản 2.

Đây đúng là bản chất của thách thức **đa tầng văn bản**: mối nối giữa luật và
quyết định cấp tỉnh nằm ở **một câu dẫn chiếu**, chỗ mà tìm kiếm ngữ nghĩa không
với tới vì nó không giống câu hỏi về từ ngữ.

---

## 6. PHẦN CỦA [B]

### 6.1. Kiểm chứng độ tin cậy của thước đo

**Vấn đề.** Báo cáo dùng **Gemini 2.5 Pro** chấm tính trung thực (Bảng 3.6),
**trùng mô hình sinh**. Báo cáo tự nêu hạn chế này ở mục 4.4.1: tỉ lệ hậu thuẫn
nên đọc như chỉ báo tương đối, con số thực nhiều khả năng thấp hơn 88,1%.

**Cách làm.** Chấm lại trên **cùng bộ kết quả đã lưu** (295 trích dẫn) bằng hai
bộ chấm khác:

| bộ chấm | quan hệ với mô hình sinh | tỉ lệ hậu thuẫn |
|---|---|---|
| Gemini 2.5 Pro *(số của báo cáo, Bảng 4.7)* | **trùng** | **88,1%** |
| Qwen3-4B-Instruct | khác nhà, khác kiến trúc | 83,7% |
| Gemini 2.5 Flash | cùng nhà, khác mô hình | 79,0% |

**Kết luận.** Điểm ổn định trong dải 79–88%, và bộ chấm **gần mô hình sinh nhất
lại chấm chặt nhất** — ngược hướng mà thiên lệch tự đề cao dự đoán. Lo ngại nêu
ở mục 4.4.1 không được số liệu ủng hộ.

**Phát hiện phụ.** Bản Qwen3-4B **đã tinh chỉnh** cho 99,7% — gần như không phê
phán gì. Nó được dạy *sinh câu trả lời có trích dẫn*, không được dạy *đánh giá
trích dẫn*. Bộ chấm cần độc lập không chỉ về nhà phát triển mà cả về **tác vụ
huấn luyện**.

### 6.2. Tự động hoá nạp ngữ liệu

Bộ chuyển văn bản từ nguồn công báo sang định dạng của hệ: ánh xạ cấu trúc HTML
thành cấp heading, suy bậc văn bản tự động, trích quan hệ giữa các văn bản, xuất
kèm danh sách phần cần người soát. **Tự động ~60%**; phần còn lại vẫn cần người:
viết tóm tắt, điền heading thiếu, ghi chú sửa đổi nội dòng.

### 6.3. Bổ sung mô hình cục bộ 30B vào Bảng 4.13 — trả lời câu hỏi nghiên cứu 4

Báo cáo, mục 1.2, đặt **câu hỏi nghiên cứu số 4**:

> *"Ưu thế của kiến trúc GraphRAG so với hệ Naive RAG có phụ thuộc vào việc chọn
> mô hình sinh hay không?"*

Báo cáo trả lời câu này bằng Bảng 4.13 với bốn hàng. Đợt này bổ sung **một hàng
thứ năm**: mô hình cục bộ 30B kiểu hỗn hợp chuyên gia (kích hoạt ~3 tỉ tham số
mỗi token, nên chi phí suy luận tương đương mô hình 4 tỉ).

| mô hình sinh | Naive RAG | GraphRAG | chênh lệch |
|---|---|---|---|
| Gemini 2.5 Pro | 0,435 | 0,617 | +0,182 |
| **Cục bộ 30B, hai ví dụ mẫu** ⟵ **mới** | **0,317** | **0,583** | **+0,266** |
| Cục bộ 4B gốc, hai ví dụ mẫu | 0,239 | 0,511 | +0,272 |
| Cục bộ 4B đã tinh chỉnh, không ví dụ mẫu | 0,301 | 0,402 | +0,101 |
| Cục bộ 4B gốc, không ví dụ mẫu | 0,154 | 0,131 | **−0,022** |

*Bốn hàng đầu tiên là số của báo cáo; hàng 30B là kết quả đo mới. Toàn bảng tính
trên trung bình 137 câu, đúng cơ sở của Bảng 4.13.*

**Hai kết luận:**

**Mô hình cục bộ đạt gần mức thương mại.** 30B đạt 0,583 so với Gemini 0,617 —
kém 0,034. Với hệ thống pháp luật xử lý dữ liệu công dân, chạy được tại chỗ là
giá trị thực tế, không chỉ học thuật.

**Ưu thế kiến trúc giữ vững ở bốn trên năm cấu hình**, trải từ mô hình thương
mại quy mô lớn tới mô hình 4 tỉ tham số chạy cục bộ, ở cả bản gốc lẫn bản tinh
chỉnh. Hàng duy nhất âm là mô hình gốc **không có ví dụ mẫu** — cấu hình yếu
nhất, nơi mô hình chưa xuất được đúng định dạng trích dẫn nên điểm không phản
ánh năng lực truy hồi (báo cáo phân tích ở mục 4.7.6).

> **Không được phát biểu "GraphRAG thắng trên mọi cấu hình".** Báo cáo ghi rõ có
> một hàng âm. Nói quá lên là chỗ hội đồng kiểm tra được ngay.

**Về việc tinh chỉnh.** Kết quả mới **củng cố** kết luận âm đã có trong báo cáo
mục 4.7.5: bản tinh chỉnh không vượt được bản gốc hai ví dụ mẫu (0,402 so với
0,511). Ghép với phát hiện ở §6.1 — bản tinh chỉnh làm bộ chấm cho 99,7% — ta có
**hai lần độc lập cùng một hiện tượng**: tinh chỉnh theo tác vụ sinh đánh đổi
năng lực phân biệt lấy tuân thủ định dạng.

**Một món hời chưa nhặt.** Toàn bộ lỗi định dạng của 30B là một kiểu duy nhất:
thiếu tiền tố "Văn bản" trong khối trích dẫn. Mười hai câu mất trắng vì cú pháp
thuần tuý. Sửa một dòng prompt là lấy lại được.

### 6.4. Lĩnh vực lao động

Thêm 4 văn bản cho thủ tục chấm dứt hợp đồng lao động và trợ cấp thôi việc: Bộ
luật Lao động 2012 (đã hết hiệu lực) và 2019, Nghị định 145/2020 (hướng dẫn chi
tiết), Nghị định 293/2025 (lương tối thiểu vùng). Kết quả đo ở §7.

---

## 7. KẾT QUẢ NẠP LĨNH VỰC MỚI — ĐO THẬT

| chỉ số | trước | sau |
|---|---|---|
| Văn bản | 32 | **36** |
| Điều khoản | 4 549 | **7 208** |
| Cạnh dẫn chiếu | 3 919 | **5 366** |
| Lĩnh vực | 3 | **4** |

**Thời gian: 3 giờ 10 phút máy chạy**, trong đó 3 giờ là gán khái niệm cho 2 659
điều khoản mới. Chỉ **một lần lỗi hạn ngạch** trong hơn 2 600 lượt gọi.

**Các quan hệ tự hình thành, không khai báo tay:** 2 cạnh *hướng dẫn thi hành*
(hai nghị định trỏ về Bộ luật Lao động 2019 — quan hệ đa tầng của lĩnh vực mới),
và **1 447 cạnh dẫn chiếu**. Bộ trích xuất viết cho đất đai và hộ tịch chạy
thẳng trên văn bản lao động **không sửa dòng nào**.

**Không phá vỡ cái cũ:** 13 câu demo đất đai cho số trích dẫn **khớp y hệt**
trước khi nạp, không văn bản lao động nào lọt vào, ba câu ngoài phạm vi vẫn từ
chối đúng.

**Câu hỏi lao động chạy được:**

> *"Tôi làm ở công ty được 6 năm rồi xin nghỉ việc, có được trợ cấp thôi việc
> không, tính thế nào?"*

Hệ nhận đúng lĩnh vực, lấy **Bộ luật Lao động 2019 Điều 46** cộng **Nghị định
145/2020 Điều 8** — đúng chuỗi đa tầng — và bản cải tiến lần thêm sang Điều 34,
36 qua chuỗi dẫn chiếu.

### Một sắc thái phải nói đúng

Khẳng định *"không sửa dòng logic truy hồi nào"* là **đúng**. Nhưng **khâu sinh
phải khai báo thêm**: prompt bộ sinh có danh sách chủ đề ngoài phạm vi, trong đó
ghi cứng "lao động", và câu từ chối liệt kê đúng ba lĩnh vực cũ. Trước khi sửa,
hệ **từ chối** câu hỏi lao động dù ngữ cảnh đã đủ căn cứ.

Phát biểu chính xác: **truy hồi tổng quát hoá không cần sửa; khâu sinh cần khai
báo phạm vi lĩnh vực mới.** Nói "không sửa gì cả" là quá tay.

### Hạn chế còn lại

Câu có đáp án nằm trong **bảng biểu** (bảng lương tối thiểu bốn vùng) vẫn bị trả
"không đủ thông tin" dù bảng nằm ở vị trí đầu ngữ cảnh. Bộ sinh chưa nhận bảng
là căn cứ. Tránh dạng câu này khi trình diễn.

---

## 8. BỔ SUNG PHỤC VỤ ĐÁNH GIÁ VÀ DEMO

**Tập kiểm thử mới (32 câu)** theo quy ước chú giải "chuỗi dẫn chiếu": đáp án gồm
điều khoản trả lời trực tiếp **cộng điều khoản mà nó dẫn chiếu tường minh** — vì
không đọc phần được dẫn chiếu thì không biết điều khoản chính áp dụng khi nào.

**Bổ sung nhóm câu demo cho thách thức đa lĩnh vực.** Toàn bộ 13 câu demo cũ đều
thuộc đất đai, nên không câu nào chứng minh được khả năng đa lĩnh vực. Đã thêm
hai câu chạy qua kho hộ tịch:

- *"Đăng ký lại khai sinh mà không còn bản sao giấy khai sinh cũ thì cần giấy tờ
  gì?"* — Thông tư 04/2020 Điều 9 Khoản 3 mở đầu bằng *"trường hợp không có giấy
  tờ quy định tại khoản 1 và khoản 2 Điều này"*. Bản cũ chỉ lấy Khoản 3; bản cải
  tiến lấy đủ **Khoản 1 + 2 + 3**.
- *"Tôi là bà nội… thủ tục đăng ký giám hộ đương nhiên làm như thế nào?"* — minh
  hoạ cùng lúc bản vá bộ lập kế hoạch **và** chuỗi dẫn chiếu: Luật Hộ tịch Điều
  21 Khoản 2 nói *trình tự thực hiện theo khoản 2 Điều 20*, nên bản cũ dừng ở
  Điều 21 — điều **không chứa nội dung trình tự nào**.

---

## 9. CÁCH CHẠY DEMO SO SÁNH

Hai bản chạy song song trên hai cổng, chỉ khác một biến:

```bash
env UI_REFERS_MODE= ./scripts/chay-demo.sh live 8000          # trước cải tiến
env UI_REFERS_MODE=khoan ./scripts/chay-demo.sh live 8001     # sau cải tiến
```

Phải đặt biến **tường minh cho cả hai** — bỏ trống ở lệnh đầu thì biến lây sang
tiến trình thứ hai và cả hai cổng cùng chạy bản mới.

Cả 15 câu demo đã nạp sẵn kết quả cho **cả hai cấu hình**, chạy được kể cả khi
mạng chập chờn.

**Năm câu cho kết quả khác nhau** — dùng làm cặp đối chiếu:

| câu | trước cải tiến | sau cải tiến |
|---|---|---|
| A3 (hạn mức do ai quy định) | dẫn Luật Đất đai **2013** | dẫn Luật Đất đai **2024** Đ196 K2 |
| C1 (hạn mức tối đa) | dẫn quyết định **đã hết hiệu lực** | dẫn căn cứ luật hiện hành |
| B2 (hồ sơ nộp cuối 2024) | chỉ có luật | thêm nghị định hướng dẫn |
| B4 (chuyển 3ha đất lúa) | dẫn điều về *thu hồi đất* | dẫn điều về *điều kiện chuyển mục đích* |
| A2 (Đồng Nai) | thừa điều về *cách tính tiền* | chỉ giữ điều về hạn mức |

Câu **A3** cho khác biệt rõ nhất, nên dùng làm ví dụ chính.

---

## 10. BỐN ĐIỀU CẦN NÊU RÕ KHI TRÌNH BÀY

**Phân biệt hai phép so sánh.** Kết quả chính của khóa luận là **hệ GraphRAG so
với RAG thuần** — Bảng 4.4 của báo cáo: chênh lệch **+0,187**, khoảng tin cậy 95%
**[0,108; 0,264]**, Wilcoxon **p = 0,00003**, thắng/thua/hoà **67/32/24**. Kết
quả của đợt cải tiến là **bản mới so với chính hệ đã có**: 26 thắng / 4 thua.
Hai con số đo hai thứ khác nhau.

**Mức tăng bị pha loãng bởi trần.** 60% số câu đã đạt bao phủ tối đa từ trước.
Khi trình bày nên nói: *"trên 49 câu hệ chưa lấy đủ điều khoản, cải tiến chữa
được một nửa, nâng bao phủ trung bình +0,317"*.

**Ưu thế kiến trúc giữ ở bốn trên năm cấu hình, không phải tất cả.** Xem §6.3.

**Bao phủ tăng không đồng nghĩa câu trả lời tốt hơn.** Xem §11.

---

## 11. HƯỚNG PHÁT TRIỂN TIẾP

Đợt cải tiến nâng đáng kể khả năng **lấy đúng điều khoản**. Bước tiếp theo là
**tiết chế việc chọn trích dẫn** ở khâu sinh: hệ trích trung bình 2,71 điều
khoản trong khi đáp án chuẩn chỉ cần 1,57.

Đã đo được dư địa: nếu chọn lọc trích dẫn tối ưu, F1 tăng từ 0,571 lên **0,742**
— lớn hơn toàn bộ mức cải thiện đạt được trong đợt này.

Kết quả ở §6.3 cho thấy hai hướng bổ khuyết nhau: mô hình thương mại trích thừa
(mua độ bao phủ bằng độ chính xác), mô hình cục bộ 30B trích cân nhất bảng nhưng
thiếu độ bao phủ ở thách thức đa tầng. Kết hợp hai đặc tính này là hướng cụ thể.

Ba việc nhỏ có giá trị biên cao: **vá tiền tố "Văn bản"** cho mô hình 30B (12
câu mất trắng vì cú pháp), **dạy bộ sinh đọc bảng biểu** (§7), và **rà tập chuẩn
lĩnh vực nuôi con nuôi** — nơi kiến trúc gần như không mang lại cải thiện, và
hiện tượng này nhất quán qua bốn mô hình rất khác nhau nên nguyên nhân nằm ở
ngữ liệu chứ không ở mô hình.
