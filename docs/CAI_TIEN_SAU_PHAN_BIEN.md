# Các cải tiến sau buổi phản biện

**Thời gian thực hiện:** 12–18/08/2026 (gồm cả bước gộp công việc hai thành viên)
**Đo trên:** 123 câu hỏi có đáp án chuẩn (bộ v2), mô hình Gemini 2.5 Pro
**Số liệu:** đo lại sau khi gộp nhánh của [A] và [B] (18/08) — `v2_chot_sau_gop.json`
**Chỉ số:** độ bao phủ điều khoản — hệ có lấy được đúng điều khoản chứa đáp án
vào ngữ cảnh hay không. Đo tất định, không phụ thuộc mô hình sinh.

> **Quan hệ với báo cáo.** Báo cáo chốt bản thể luận **chín thực thể, mười quan
> hệ**, kho **32 văn bản thuộc ba lĩnh vực**. Đợt cải tiến này bổ sung **quan hệ
> thứ mười một** (dẫn chiếu điều khoản, §3.1) và mở kho lên **36 văn bản, bốn
> lĩnh vực** (§7). Mọi phép đo ở §2 vẫn thực hiện trên **đúng kho 32 văn bản của
> báo cáo** để so sánh được với số liệu đã công bố; lĩnh vực lao động chỉ dùng
> chứng minh tính tổng quát hoá, không đưa vào bộ đánh giá.

---

## 1. GÓP Ý CỦA CÔ VÀ VIỆC ĐÃ LÀM

| góp ý của cô | việc đã làm | kết quả |
|---|---|---|
| Tự động hoá khâu chuẩn bị văn bản được không? | Cho máy sinh phần tóm tắt văn bản thay người viết | Máy làm được, **không câu nào tệ đi** |
| Khâu người làm (viết tóm tắt) làm sao đảm bảo đúng? | Cùng thí nghiệm trên | Tín hiệu định tuyến **không phụ thuộc người viết** |
| Vấn đề hồi tố có nên xử lý sâu thêm? | Xây cơ chế phát hiện quy định đã thay đổi + nạp điều khoản chuyển tiếp | Đã chạy được, có cảnh báo cho người dùng |
| Thêm module cải tiến mô hình sinh? | [B] tinh chỉnh mô hình cục bộ + kiểm chứng bộ chấm | Xem §6 |
| Thêm bước xử lý, lọc dữ liệu trước khi đưa vào ngữ cảnh? | **Ba cơ chế mới** ở khâu truy hồi | **+0,116 độ bao phủ** |

---

## 2. KẾT QUẢ TỔNG HỢP

**Độ bao phủ điều khoản đúng: 0,737 → 0,853**

| bước cộng dồn | độ bao phủ | mức tăng | thắng/thua |
|---|---|---|---|
| Hệ trước cải tiến | 0,737 | — | — |
| + Lần theo dẫn chiếu | 0,753 | +0,016 | 9 / 3 |
| + Xếp lại bằng cross-encoder | 0,800 | +0,063 | 17 / 5 |
| + Mở rộng vùng tìm kiếm | **0,853** | **+0,116** | **26 / 4** |

Theo từng thách thức:

| thách thức | mức tăng |
|---|---|
| Đa lĩnh vực | **+0,216** |
| Đa tầng văn bản | **+0,153** |
| Đa địa phương | +0,069 |
| Đa phiên bản | +0,019 |

### Vì sao chỉ 26 câu thắng trên 123 câu

Vì **74 câu (60%) đã đạt bao phủ 1,00 từ trước** — hệ vốn đã lấy đúng hết, không
còn chỗ để cải thiện.

Chỉ có **49 câu còn dưới 1,00**. Trên đúng nhóm này:

> **26/49 câu được cải thiện (53%), mức tăng trung bình +0,317.**

Con số +0,116 là mức tăng của **toàn hệ thống**; con số +0,317 cho biết **cơ chế
có thật sự hiệu lực hay không** khi gặp câu khó. Hai con số trả lời hai câu hỏi
khác nhau, nên nêu cả hai.

---

## 3. TỪNG CẢI TIẾN — GIẢI THÍCH

### 3.1. Lần theo dẫn chiếu giữa các điều khoản

**Vấn đề.** Văn bản luật liên tục trỏ sang nhau: *"theo khoản 2 Điều 196"*,
*"trường hợp không có giấy tờ quy định tại khoản 1 và khoản 2 Điều này"*. Những
câu trỏ này **không mang nội dung**, nên tìm kiếm theo độ giống nhau về từ ngữ
không bao giờ với tới điều khoản được trỏ đến. Người đọc thì bắt buộc phải mở
sang đó mới hiểu.

**Cách làm.** Đọc toàn bộ kho văn bản, nhận diện mọi câu dẫn chiếu bằng biểu
thức chính quy, rồi phân giải xem nó trỏ đến điều khoản cụ thể nào. Kết quả tạo
ra **3919 quan hệ mới** trên kho 3 lĩnh vực dùng để đo (32 văn bản), và **5366** sau khi thêm lĩnh vực lao động (§7) — **quan hệ thứ mười một**, bổ sung so với mười quan hệ đã công bố trong báo cáo.

Ba trường hợp phải xử lý riêng:

- *"khoản 2 Điều 196 của Luật Đất đai"* — nêu tên văn bản, nhưng kho có **hai
  bản** Luật Đất đai (2013 và 2024). Hệ chọn bản đang có hiệu lực **tại thời
  điểm văn bản dẫn chiếu được ban hành**.
- *"khoản 1 và khoản 2 Điều này"* — trỏ sang khoản khác trong cùng điều, phải
  biết đang đứng ở điều nào.
- Địa chỉ nằm trong ghi chú sửa đổi (`<!-- amended_by -->`) trỏ tới **văn bản
  sửa**, không phải dẫn chiếu — phải loại bỏ.

**Khi truy hồi**, sau khi chọn xong các điều khoản liên quan, hệ đi thêm một
bước theo các quan hệ này để nạp cả những điều khoản được trỏ tới.

### 3.2. Xếp lại thứ tự bằng cross-encoder

**Vấn đề.** Mô hình nhúng mã hoá cả câu hỏi và điều khoản thành vector rồi so
khoảng cách. Cách này nhanh nhưng thô: hai điều khoản cùng chủ đề trông rất
giống nhau dù chỉ một cái trả lời đúng câu hỏi.

**Cross-encoder** đọc *đồng thời* câu hỏi và điều khoản rồi chấm điểm mức liên
quan. Chính xác hơn nhiều, nhưng chậm nên không dùng để quét cả kho được.

**Điểm đáng chú ý.** Cơ chế này **đã từng bị thử và bác bỏ** trong quá trình làm
khóa luận (ghi trong nhật ký quyết định của nhóm, không đưa vào báo cáo vì là kết
quả âm): khi để nó tham gia *chọn văn bản*, nó kéo lên những đoạn trùng từ ngữ
nhưng sai văn bản, làm kết quả tệ đi.

Lần này đặt nó ở vị trí khác: **chỉ xếp lại thứ tự bên trong từng văn bản đã
được chọn**, không cho nó động đến việc chọn văn bản nào. Cùng một mô hình,
khác vị trí trong đường ống, kết quả từ âm thành **+0,047**.

Đây là một kết luận có giá trị phương pháp: *vị trí của một thành phần trong hệ
quan trọng ngang với bản thân thành phần đó.*

### 3.3. Mở rộng vùng tìm kiếm

Nâng số ứng viên lấy ra ở bước tìm kiếm ngữ nghĩa, và bỏ hệ số chấm theo độ
hiếm của khái niệm. Hai điều chỉnh này cộng lại cho **+0,053**, riêng nhóm câu
đa lĩnh vực hưởng lợi nhiều nhất.

### 3.4. Phát hiện quy định đã thay đổi

**Đáp góp ý về hồi tố của cô.**

Cần phân biệt hai khái niệm hay bị gộp:

- **Hiệu lực hồi tố** là nguyên tắc của luật hình sự (Điều 7 Bộ luật Hình sự) —
  ngoài phạm vi đề tài.
- **Điều khoản chuyển tiếp** là quy định do chính văn bản đặt ra để xử lý hồ sơ
  nộp trước ngày văn bản có hiệu lực. **Đây mới là thứ người dân gặp phải.**

**Cách làm.** Khi tập văn bản ứng viên có văn bản đã hết hiệu lực, hệ tìm văn
bản thay thế theo mốc thời gian, nạp thêm điều khoản chuyển tiếp, và sinh một
câu cảnh báo đặt **trước** câu trả lời.

Hệ **không tự kết luận** trường hợp của người dùng thuộc quy định cũ hay mới —
nó trình bày cả hai và nêu rõ căn cứ, vì việc xác định đó phụ thuộc hồ sơ cụ thể
mà hệ không có.

### 3.5. Tự động hoá phần tóm tắt văn bản

**Đáp hai góp ý đầu của cô.**

Mỗi văn bản trong kho có một đoạn tóm tắt 3–5 câu do người viết, dùng làm tín
hiệu định tuyến ở bước đầu tiên. Cô đặt hai câu hỏi: khâu này tự động hoá được
không, và làm sao biết phần người viết là đúng?

**Thí nghiệm.** Cho mô hình sinh lại toàn bộ tóm tắt từ chính nội dung văn bản,
rồi chạy lại phép đo với tóm tắt máy.

**Kết quả: 0 câu thua, 120/121 câu cho kết quả y hệt.**

Hai kết luận:

1. Khâu này **tự động hoá được** — trả lời trực tiếp góp ý thứ nhất.
2. Tín hiệu định tuyến **không phụ thuộc vào chất lượng văn phong của người
   viết** — nghĩa là phần người làm không phải "cái nạng giấu mặt" nâng đỡ kết
   quả. Trả lời góp ý thứ hai.

---

## 4. BỐN LỖI THẬT ĐÃ TÌM RA VÀ SỬA

Quá trình đo đạc làm lộ ra bốn lỗi mà trước đây không ai phát hiện:

**Bộ lập kế hoạch lấy năm xảy ra sự việc làm mốc lọc hiệu lực.** Câu *"lấn đất
từ 2010 … nay quy hoạch đã điều chỉnh"* bị chốt mốc 2010 → loại sạch Luật Đất
đai 2024. Hai câu hỏi trước đây **không tìm được văn bản nào**.

**Câu không nêu địa phương bị chốt cứng là "toàn quốc"** → loại sạch văn bản cấp
tỉnh, trong khi nhiều câu (lệ phí, hạn mức) có đáp án nằm đúng ở cấp tỉnh.

**Thủ tục ngoài danh mục làm bộ lập kế hoạch bỏ trống lĩnh vực.** Hệ lập chỉ mục
sâu cho 6 thủ tục; gặp việc hộ tịch nằm ngoài 6 thủ tục đó (đăng ký giám hộ,
khai tử, cải chính hộ tịch), mô hình trả về lĩnh vực rỗng → bước lọc đầu tiên
không trả về gì → **hệ không trả lời được**. Đã sửa: lĩnh vực xác định độc lập
với thủ tục.

**Thước đo dùng sai nhà cung cấp mô hình.** Công cụ đo độ bao phủ dùng Claude
cho bước lập kế hoạch, trong khi hệ thật chạy Gemini → hai bên làm việc trên
**kế hoạch truy vấn khác nhau**, nên con số đo được không phản ánh đúng ngữ cảnh
mà mô hình sinh thực nhận. Đã đồng bộ và đo lại toàn bộ.

---

## 5. VÍ DỤ MINH HOẠ

> **Câu hỏi:** *"Hạn mức giao đất ở cho cá nhân do cơ quan nào quy định, và con
> số cụ thể hiện nay tại TP.HCM được quy định ở văn bản nào?"*

**Trước cải tiến**, hệ dẫn **Luật Đất đai 2013, Điều 103 Khoản 4** — nội dung
thật của điều này là *"xác định diện tích đất ở đối với trường hợp có vườn,
ao"*. Sai hai lần: luật đã hết hiệu lực, và không liên quan tới hạn mức giao
đất. Nhưng về mặt từ ngữ thì nó **rất giống** câu hỏi.

**Sau cải tiến**, hệ dẫn **Luật Đất đai 2024, Điều 196 Khoản 2** — đúng điều
luật trao thẩm quyền cho UBND tỉnh quy định hạn mức.

**Vì sao cải tiến chữa được?** Quyết định 69/2024 của TP.HCM, ngay Điều 1 "Phạm
vi điều chỉnh", có câu **"theo khoản 2 Điều 196"**. Cơ chế lần theo dẫn chiếu đi
đúng dây đó về tới điều luật gốc.

Đo cụ thể: bản cũ lấy 19 đơn vị nội dung, bản mới lấy 22 — **thêm 3, không mất
cái nào**, và một trong ba chính là Điều 196 Khoản 2.

**Đây đúng là bản chất của thách thức đa tầng văn bản:** mối nối giữa luật và quyết
định cấp tỉnh nằm ở **một câu dẫn chiếu**, chỗ mà tìm kiếm theo ngữ nghĩa không
với tới vì nó không giống câu hỏi về mặt từ ngữ. Phải có quan hệ trong đồ thị
mới lần ra được.

---

## 6. PHẦN CỦA [B]

### 6.1. Kiểm chứng độ tin cậy của thước đo

**Vấn đề.** Báo cáo dùng Gemini 2.5 Pro để chấm tính trung thực, **trùng mô hình
sinh câu trả lời**. Nghiên cứu về thiên lệch tự đề cao chỉ ra mô hình có xu hướng
chấm đầu ra của chính nó cao hơn. Báo cáo đã tự nêu hạn chế này ở mục 4.4.1.

**Cách làm.** Chấm lại trên **cùng một bộ kết quả đã lưu** (118 câu, 295 trích
dẫn) bằng hai bộ chấm khác:

| bộ chấm | quan hệ với mô hình sinh | tỉ lệ hậu thuẫn |
|---|---|---|
| Gemini 2.5 Pro | **trùng** | 88,1% |
| Qwen3-4B-Instruct | khác nhà, khác kiến trúc | 83,7% |
| Gemini 2.5 Flash | cùng nhà, khác mô hình | 79,0% |

**Kết luận.** Điểm ổn định trong dải 79–88%, và bộ chấm **gần mô hình sinh nhất
lại chấm chặt nhất** — ngược hẳn hướng mà thiên lệch tự đề cao dự đoán. Nghi ngờ
đó không được số liệu ủng hộ.

**Phát hiện phụ đáng giá.** Bản Qwen3-4B **đã tinh chỉnh** trên dữ liệu hỏi đáp
pháp luật cho tỉ lệ 99,7% — gần như không phê phán gì. Nó được dạy *sinh câu trả
lời có trích dẫn*, không được dạy *đánh giá trích dẫn*. Bài học: bộ chấm cần độc
lập không chỉ về nhà phát triển mà cả về **tác vụ huấn luyện**.

### 6.2. Tự động hoá nạp ngữ liệu

Script chuyển văn bản từ vbpl.vn sang định dạng pipeline: ánh xạ class ngữ nghĩa
của HTML thành cấp heading, suy bậc văn bản tự động từ loại văn bản, trích quan hệ
giữa các văn bản từ tab lược đồ, xuất kèm danh sách phần cần người soát.

**Tự động hoá ~60%.** Phần còn lại vẫn cần người: viết tóm tắt, điền heading bị
thiếu do HTML nguồn, và ghi chú sửa đổi nội dòng.

### 6.3. Lĩnh vực lao động — chứng minh tổng quát hoá

Thêm 4 văn bản cho thủ tục chấm dứt hợp đồng lao động và trợ cấp thôi việc: Bộ
luật Lao động 2012 (đã hết hiệu lực) và 2019, Nghị định 145/2020 (hướng dẫn chi
tiết), Nghị định 293/2025 (lương tối thiểu vùng).

---

## 7. KẾT QUẢ NẠP LĨNH VỰC MỚI — ĐO THẬT

Nạp lĩnh vực lao động vào đồ thị demo, đo trên máy thật:

| chỉ số | trước | sau |
|---|---|---|
| Văn bản | 32 | **36** |
| Điều khoản | 4 549 | **7 208** |
| Cạnh dẫn chiếu | 3 919 | **5 366** |
| Lĩnh vực | 3 | **4** |

**Thời gian: 3 giờ 10 phút máy chạy**, trong đó 3 giờ là gán khái niệm bằng mô
hình cho 2 659 điều khoản mới. Chỉ **một lần lỗi hạn ngạch API** trong hơn 2 600
lượt gọi, và cơ chế thử lại xử lý đúng.

**Các quan hệ tự hình thành, không khai báo tay:**

- 2 cạnh *hướng dẫn thi hành* mới: NĐ 145/2020 và NĐ 293/2025 trỏ về Bộ luật Lao
  động 2019 — quan hệ đa tầng của lĩnh vực mới
- 1 447 cạnh *dẫn chiếu* mới trong kho lao động. Bộ trích xuất viết cho đất đai
  và hộ tịch chạy thẳng trên văn bản lao động **không sửa một dòng nào**

**Kiểm chứng không phá vỡ cái cũ:** 13 câu demo đất đai cho số trích dẫn **khớp y
hệt** trước khi nạp, không văn bản lao động nào lọt vào, và ba câu ngoài phạm vi
vẫn từ chối đúng.

**Câu hỏi lao động chạy được:**

> *"Tôi làm ở công ty được 6 năm rồi xin nghỉ việc, có được trợ cấp thôi việc
> không, tính thế nào?"*

Hệ nhận đúng lĩnh vực, lấy **Bộ luật Lao động 2019 Điều 46** cộng **Nghị định
145/2020 Điều 8** hướng dẫn chi tiết — đúng chuỗi đa tầng — và bản cải tiến lần
thêm sang Điều 34, 36 qua chuỗi dẫn chiếu.

### Một sắc thái phải nói đúng

Khẳng định *"không sửa dòng logic truy hồi nào"* là **đúng**. Nhưng **khâu sinh
thì phải khai báo thêm**: prompt của bộ sinh có danh sách chủ đề ngoài phạm vi,
trong đó ghi cứng "lao động", và câu từ chối liệt kê đúng ba lĩnh vực cũ. Trước
khi sửa, hệ **từ chối** câu hỏi lao động dù ngữ cảnh đã có đủ căn cứ.

Nên phát biểu chính xác là: **truy hồi tổng quát hoá không cần sửa; khâu sinh cần
khai báo phạm vi lĩnh vực mới.** Nói "không sửa gì cả" là quá tay, và hội đồng
kiểm tra được.

### Hạn chế còn lại

Câu hỏi có đáp án nằm trong **bảng biểu** (bảng lương tối thiểu 4 vùng) vẫn bị
trả "không đủ thông tin", dù bảng nằm ở vị trí đầu tiên trong ngữ cảnh. Bộ sinh
chưa nhận bảng markdown là căn cứ. Tránh dạng câu này khi trình diễn.

---

## 8. BỔ SUNG PHỤC VỤ ĐÁNH GIÁ VÀ DEMO

**Tập kiểm thử mới (32 câu)** cùng quy ước chú giải "chuỗi dẫn chiếu": đáp án
gồm điều khoản trả lời trực tiếp **cộng những điều khoản mà nó dẫn chiếu tường
minh** — vì không đọc phần được dẫn chiếu thì không biết điều khoản chính áp
dụng trong trường hợp nào.

**Bổ sung nhóm câu demo cho thách thức đa lĩnh vực.** Toàn bộ 13 câu demo cũ đều thuộc lĩnh vực
đất đai, nên **không câu nào chứng minh được khả năng đa lĩnh vực**. Đã thêm hai
câu chạy qua kho hộ tịch:

- *"Đăng ký lại khai sinh mà không còn bản sao giấy khai sinh cũ thì cần giấy tờ
  gì?"* — Thông tư 04/2020 Điều 9 Khoản 3 mở đầu bằng *"trường hợp không có giấy
  tờ quy định tại khoản 1 và khoản 2 Điều này"*. Bản cũ chỉ lấy Khoản 3; bản cải
  tiến lấy đủ **Khoản 1 + 2 + 3**.
- *"Tôi là bà nội… thủ tục đăng ký giám hộ đương nhiên làm như thế nào?"* — minh
  hoạ cùng lúc bản vá lỗi bộ lập kế hoạch **và** chuỗi dẫn chiếu: Luật Hộ tịch
  Điều 21 Khoản 2 nói *trình tự thực hiện theo khoản 2 Điều 20*, nên bản cũ dừng
  ở Điều 21 — điều vốn **không chứa nội dung trình tự nào**.

---

## 9. CÁCH CHẠY DEMO SO SÁNH

Hai bản chạy song song trên hai cổng, chỉ khác đúng một biến:

```bash
env UI_REFERS_MODE= ./scripts/chay-demo.sh live 8000          # trước cải tiến
env UI_REFERS_MODE=khoan ./scripts/chay-demo.sh live 8001     # sau cải tiến
```

Cả 15 câu demo đã được nạp sẵn kết quả cho **cả hai cấu hình**, nên chạy được
kể cả khi mạng chập chờn.

**Năm câu cho kết quả khác nhau giữa hai bản** — dùng làm cặp đối chiếu:

| câu | trước cải tiến | sau cải tiến |
|---|---|---|
| A3 (hạn mức do ai quy định) | dẫn Luật Đất đai **2013** | dẫn Luật Đất đai **2024** Đ196 K2 |
| C1 (hạn mức tối đa) | dẫn QĐ 18/2016 **đã hết hiệu lực** | dẫn căn cứ luật hiện hành |
| B2 (hồ sơ nộp cuối 2024) | chỉ có luật | thêm nghị định hướng dẫn |
| B4 (chuyển 3ha đất lúa) | dẫn điều về *thu hồi đất* | dẫn điều về *điều kiện chuyển mục đích* |
| A2 (Đồng Nai) | thừa điều về *cách tính tiền* | chỉ giữ điều về hạn mức |

Câu **A3** cho khác biệt rõ nhất và nên dùng làm ví dụ chính.

---

## 10. HAI ĐIỀU CẦN NÊU RÕ KHI TRÌNH BÀY

**Phân biệt hai phép so sánh.** Kết quả chính của khóa luận là **hệ GraphRAG so
với RAG thuần** — theo Bảng 4.4 của báo cáo: chênh lệch **+0,187**, khoảng tin cậy
95% **[0,108; 0,264]**, Wilcoxon **p = 0,00003**, thắng/thua/hoà **67/32/24**. Kết quả của đợt
cải tiến là **bản mới so với chính hệ đã có**: 26 thắng / 4 thua. Hai con số đo
hai thứ khác nhau, đừng để bị nhầm là cùng một bảng.

**Mức tăng bị pha loãng bởi trần.** 60% số câu đã đạt bao phủ tối đa từ trước
nên cải tiến không thể tác động. Khi trình bày nên nói: *"trên 49 câu hệ chưa
lấy đủ điều khoản, cải tiến chữa được một nửa, nâng bao phủ trung bình
+0,317"* — mẫu số đó mới phản ánh đúng hiệu lực của cơ chế.

---

## 11. HƯỚNG PHÁT TRIỂN TIẾP

Đợt cải tiến này đã nâng đáng kể khả năng **lấy đúng điều khoản**. Bước tiếp
theo là **tiết chế việc chọn trích dẫn** ở khâu sinh: hệ hiện trích trung bình
2,71 điều khoản trong khi đáp án chuẩn chỉ cần 1,57.

Đã đo được dư địa của hướng này: nếu chọn lọc trích dẫn tối ưu, chỉ số F1 tăng
từ 0,571 lên **0,742**. Đây là mục tiêu định lượng rõ ràng cho giai đoạn tiếp
theo, và lớn hơn toàn bộ mức cải thiện đạt được trong đợt này.
