# TỔNG HỢP FINE-TUNE — PHẦN B: KHÓ KHĂN PHƯƠNG PHÁP VÀ CÁCH GIẢI QUYẾT

> **Phạm vi.** Tài liệu này ghi lại các vấn đề **phương pháp** gặp phải khi thực
> hiện TASK-FT-00 đến FT-06, và lập luận đã dùng để giải quyết. Chủ đích là làm
> nguyên liệu viết mục 4.7, mục 5.3 (Hạn chế) và phần trả lời câu hỏi hội đồng.
>
> **Cố ý loại trừ.** Mọi khó khăn thuộc vận hành hạ tầng — thuê GPU, thiết bị
> CUDA lỗi trên máy chủ cho thuê, xung đột phiên bản gói, giao diện Kaggle, quản
> lý phiên terminal. Chúng đã tiêu tốn thời gian thật nhưng không mang giá trị
> học thuật và không nên xuất hiện trong khóa luận.
>
> Số liệu chính xác, tham số và bảng kết quả xem **PHẦN A** (`FT_SYNTHESIS_A_SOLIEU.md`).

---

## 0. Bối cảnh: vì sao mục 4.7 tồn tại

Mục 4.1.3 của khóa luận phát biểu:

> *"Tất cả các hệ chạy trên cùng bộ câu hỏi và cùng mô hình sinh (cấu hình chi
> tiết ở Bảng 3.6), do đó sự chênh lệch đo được thuộc về khác biệt ở cơ chế truy
> hồi chứ không phải ở mô hình sinh."*

Câu này giữ mô hình sinh **cố định** và đổi cơ chế truy hồi. Nó chứng minh
GraphRAG hơn Naive RAG **khi mô hình sinh là Gemini 2.5 Pro**. Nhưng nó không
loại trừ được một phản biện hiển nhiên: *nếu lợi ích đó chỉ là hiện vật của việc
chọn Gemini thì sao?*

Mục 4.7 làm chiều ngược lại — giữ **truy hồi** cố định, đổi **mô hình sinh**. Đây
là một trục trực giao với Bảng 4.2, không phải một hệ tham chiếu thứ năm của Bảng
4.5. Đại lượng cần quan tâm là **cột Δ**, không phải F1 tuyệt đối của các hàng
cục bộ.

Nguyên tắc ghi trong kế hoạch: *"Cột Δ là thứ duy nhất quan trọng. KHÔNG tối ưu
F1 tuyệt đối của hàng cục bộ."* Toàn bộ các quyết định dưới đây bám vào nguyên
tắc đó.

---

## 1. Xác minh thước đo trước khi sinh dữ liệu

### 1.1 Cú pháp trích dẫn: tài liệu dự án ghi sai

**Vấn đề.** Bộ chấm điểm (`src/evaluation/metrics.py`) chỉ nhận trích dẫn ở một
cú pháp duy nhất. Khi đối chiếu, phát hiện một số tài liệu và ghi chú cũ trong dự
án mô tả cú pháp đó **không chính xác**.

**Tại sao nghiêm trọng.** Dữ liệu huấn luyện dạy mô hình *viết* trích dẫn. Nếu
dạy theo cú pháp sai, mô hình sẽ học đúng thứ mà bộ chấm từ chối — và F1 sẽ bằng
0 vì lý do thuần hình thức, không vì mô hình không biết luật. Sai sót này sẽ chỉ
lộ ra **sau** khi đã sinh 5.000 mẫu và huấn luyện xong.

**Cách giải quyết.** Việc đầu tiên của cả kế hoạch (FT-00) là đọc `metrics.py`
để lấy cú pháp thật, rồi xác lập nó thành **hợp đồng** (`reports/api_contract.md`)
mà mọi bước sau phải tuân. Cú pháp chốt:

```
[Điều 5, Khoản 1, Điểm a, Văn bản nghi-quyet-28-2025-nq-hdnd-dong-nai]
```

Kèm một `assert` chạy trên toàn bộ 5.000 mẫu: mỗi trích dẫn phải **phân tích
ngược** được bằng chính `parse_citations` của bộ chấm.

**Bài học học thuật.** Xác minh dụng cụ đo trước khi tạo dữ liệu. Tài liệu nội bộ
không phải nguồn thẩm quyền; mã đang chạy mới là.

### 1.2 Đo độ dài chuỗi thay vì tin ghi chú

**Vấn đề.** Ghi chú cũ ước lượng system prompt vào khoảng một nửa độ dài thật.
Đo bằng chính tokenizer của mô hình cho ra **3.936 token chỉ riêng phần chỉ dẫn**.

**Hệ quả.** Cửa sổ ngữ cảnh dự tính ban đầu là 8.192 token. Với system prompt gần
4.000 token cộng ngữ cảnh GraphRAG có thể lên 8.774 token, mẫu dài nhất đạt
12.968 token — 8.192 là **không đủ**, và hậu quả của việc không đủ là chuỗi bị
**cắt đuôi âm thầm**. Khối trích dẫn nằm ở **cuối** câu trả lời, nên cắt đuôi
đúng bằng mất toàn bộ trích dẫn.

**Cách giải quyết.** Nâng `max_seq_length` và `n_ctx` lên 16.384 và **ghim, không
hạ**. Thêm bước kiểm bắt buộc (`audit_lengths`) chạy trước mỗi lần huấn luyện, in
phân bố p50/p95/max và **dừng chương trình** nếu có mẫu vượt trần. Kết quả cả hai
lần chạy thật: `over_limit = 0` — đọc trực tiếp từ log huấn luyện
(`finetune/logs/ft04-5k-2ep-20260729-2122.log:58` cho tập train, `:71` cho tập val).

Bản đo bằng **tokenizer thật lúc huấn luyện** xác nhận ước lượng ban đầu: mẫu dài
nhất **12.968 token** (`…2122.log:56`), p95 **11.009**, p50 **6.869**, mean **7.530**.
Trần 8.192 nằm giữa p50 và p95 — tức nếu giữ nó thì một phần đáng kể của tập huấn
luyện đã bị cắt đuôi mà không báo lỗi. *(Tỉ lệ chính xác không tính được: log chỉ in
phân vị, không in số mẫu vượt một ngưỡng tuỳ chọn.)*

**Bài học học thuật.** Một tham số cấu hình chọn theo ước lượng có thể phá hỏng
kết quả theo cách không phát ra tín hiệu lỗi. Đo, rồi ghim, rồi kiểm lại ở mỗi
lần chạy.

---

## 2. Thiết kế thực nghiệm: cô lập đúng một biến

### 2.1 Kiến trúc "phát lại, không chạy lại"

**Vấn đề.** Để đổi mô hình sinh mà giữ truy hồi cố định, về nguyên tắc phải chạy
lại toàn bộ đường ống: khởi động Neo4j, khởi động Qdrant, truy hồi lại 137 câu
cho cả hai hệ. Việc đó vừa tốn kém vừa **không đảm bảo** ngữ cảnh sinh ra giống
lần trước — chỉ số embedding, thứ tự trả về, ngưỡng cắt đều có thể lệch.

**Phát hiện then chốt.** Các file `results_*.json` của mẻ chạy tháng 7 đã lưu
**nguyên văn chuỗi ngữ cảnh** mà Gemini nhận, ở dạng byte-identical.

**Cách giải quyết.** Dựng bộ phát lại (`finetune/replay.py`): đọc chuỗi ngữ cảnh
từ file, đưa cho mô hình cục bộ, chấm bằng **đúng** `metrics.py`. Không cần Neo4j,
không cần Qdrant, không gọi API. Nguyên tắc vận hành ghi thành câu kiểm tra:
*"Nếu thấy cần khởi động cơ sở dữ liệu là đã sai hướng."*

**Giá trị phương pháp.** Đây là điều kiện làm cho thực nghiệm 4.7 **có hiệu lực**,
không chỉ làm cho nó rẻ. Truy hồi không chỉ được "giữ giống" mà được **đóng băng
tuyệt đối**: cả sáu ô của ma trận nhận cùng một chuỗi ký tự đầu vào. Mọi chênh
lệch đo được vì thế chỉ có thể đến từ mô hình sinh.

**Ràng buộc kéo theo, và cách nó được nới đúng chỗ.** Ghi chú ban đầu đòi hai file
nguồn phải thuộc **cùng một mẻ chạy**. Điều đó về sau **không còn đúng**, và lý do
được viết ra thay vì bỏ qua: vế Naive RAG **không đi qua bộ lập kế hoạch truy vấn**
(`naive_rag.py:339` và `:361` truyền `query_plan=None`), nên bản sửa nằm trọn trong
`query_planner` **không thể** chạm tới ngữ cảnh baseline. Điều này được **đối chiếu
trực tiếp, không suy luận**: bốn mẻ baseline đủ 137 câu có `context` trùng khít
137/137 với nhau, một ngoại lệ duy nhất (`20260710-001154` để rỗng câu V022) không
rơi vào mẻ đang dùng.

Nên nguồn hiện tại là **hai mẻ khác nhau, có chủ ý**: GraphRAG lấy `final1` (sau khi
sửa), Naive RAG giữ `20260710-085236`. Truy hồi vẫn đóng băng tuyệt đối ở cả sáu ô —
mỗi ô chỉ đổi mô hình sinh. Lập luận đầy đủ ba ý nằm trong mã, ở
`finetune/kaggle_ft06.py:110-136`, không nằm trong một tài liệu có thể trôi khỏi mã.

Phần "chọn mẻ nào trong ba mẻ `final1/2/3`" là **tuỳ ý mà vô hại**: ba mẻ đó là ba lần
**sinh** trên cùng một ngữ cảnh đông cứng (`context` trùng khít 137/137), và `replay.py`
chỉ đọc `id`, `question`, `context`, `ground_truth_citations`, `top_k_count` — trường
`answer` của Gemini bị bỏ hoàn toàn. Lấy mẻ nào cũng ra prompt y hệt.

### 2.2 Hàng đã tinh chỉnh buộc phải chạy 0-shot

**Vấn đề.** Cổng FT-03 cho thấy hai ví dụ mẫu (few-shot) nâng `format_ok` của mô
hình gốc từ 0,083 lên 0,833. Câu hỏi tự nhiên: vậy hàng đã tinh chỉnh cũng nên
chạy 2-shot cho công bằng?

**Lập luận đã dùng để trả lời "không".** Dữ liệu FT-04 dựng bằng `build_messages`
**không kèm** few-shot, nên phân phối lúc huấn luyện là 0-shot. Đánh giá ở 2-shot
là **lệch train/eval** — mô hình gặp một cấu trúc đầu vào chưa từng thấy khi
huấn luyện. Chính ràng buộc "dùng lại `build_messages` của hệ đang chạy" được
dựng để chặn đúng loại lệch này.

**Quyết định.** Hàng đã tinh chỉnh chạy **0-shot, bắt buộc**. Phép so sánh cốt
lõi là **FT@0-shot đối lại base@2-shot** — tức so mô hình đã tinh chỉnh với cấu
hình **mạnh nhất** của mô hình gốc, không phải với cấu hình yếu nhất của nó.

### 2.3 Hàng gốc chạy cả hai biến thể, và vì sao điều đó cứu kết quả

**Vấn đề.** Kế hoạch ban đầu định nghĩa ma trận 2×2 = bốn ô (548 lượt sinh). Với
hàng gốc thì báo 0-shot hay 2-shot?

**Lập luận.** Chỉ báo 0-shot thì hội đồng hỏi *"sao không thử few-shot?"*. Chỉ báo
2-shot thì mất mốc so sánh trực tiếp với hàng FT (vốn chạy 0-shot). Nên báo **cả
hai** — ma trận thành sáu ô, 822 lượt sinh.

**Điều này đã cứu kết quả.** Hàng gốc 0-shot cho Δ = **−0,022** — một giá trị
**âm**. Nếu ma trận chỉ có bốn ô và hàng gốc là 0-shot, kết luận của cả mục 4.7
sẽ trông như bị phản bác. Có cả hai biến thể mới thấy được nguyên nhân thật là
**hiệu ứng sàn**: ô đó có `format_ok_rate` = 0,065, tức chỉ 8 trên 123 câu trả
lời phân tích được. So 0,131 với 0,154 là so hai con số gần bằng không — thang đo
**không có phân giải** ở đó.

**Bài học học thuật.** Chi thêm chi phí để có một điểm dữ liệu giúp *phân biệt các
cách giải thích* thường đáng hơn là chi để tăng độ chính xác của một điểm đã có.

### 2.4 Loại trừ nhiễu do khuôn prompt (cổng chặn A)

**Vấn đề phát hiện muộn.** Mô hình gốc dùng bản lượng tử hoá của `bartowski`,
quant từ `Qwen/Qwen3-4B-Instruct-2507`. Mô hình đã tinh chỉnh huấn luyện từ
**`unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit`** rồi convert sang GGUF. Chat
template được **nhúng trong file GGUF**. Nếu hai template khác nhau dù chỉ một token,
hai hàng của ma trận nhận **prompt khác nhau**, và cột Δ đo lẫn cả khác biệt template.

> **Tên kho phải ghi cho đúng.** Lệnh huấn luyện truyền `--base-model
> unsloth/Qwen3-4B-Instruct-2507`, nhưng `adapter_config.json` của checkpoint ghi
> `base_model_name_or_path = "unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit"`: khi
> `load_in_4bit = True`, Unsloth **tự chuyển hướng** sang bản lượng tử-4-bit dựng sẵn
> của họ, thay vì tải trọng số bf16 rồi tự lượng tử hoá. Người tái lập tải kho ghi ở
> cờ CLI sẽ nạp một bộ trọng số khác và ra kết quả khác — nên **chuỗi phải công bố là
> chuỗi trong `adapter_config.json`**, kèm ghi chú về việc chuyển hướng. Đây cũng là
> lý do khoảng cách "trọng số không được đối chiếu bit-đối-bit" ở §9 mục 9 là thật:
> hai hàng của ma trận xuất phát từ hai bản sao khác nhau của cùng một mô hình.

Dấu hiệu cảnh báo có thật: log huấn luyện in
`Unsloth: Restored added_tokens_decoder metadata in tokenizer_config.json` — công
cụ huấn luyện **có** can thiệp vào metadata tokenizer.

**Cách giải quyết.** Dựng một cổng chặn chạy **trước** khi sinh bất kỳ lượt nào:
đọc chuỗi template nhúng trong cả hai file GGUF, so sánh độ dài, so sánh sha256,
và in `difflib` nếu khác. Kết quả: **trùng khít**. Nhiễu không tồn tại.

**Bài học học thuật.** Nhận diện nhiễu **trước** khi đo. Nếu để tới lúc phân tích
mới phát hiện, không có cách nào tách nó ra khỏi con số đã có.

### 2.5 Số lần chạy: chọn thiết kế đơn giản vì thiết kế phức tạp hỏng âm thầm

**Vấn đề.** Bảng 4.3 của khóa luận dùng N=3 kèm độ lệch chuẩn cho GraphRAG và
Naive RAG. Nên mục 4.7 cũng N=3?

**Khảo sát chi phí.** Ba seed rẻ **chỉ khi** vòng lặp seed nằm **trong** vòng lặp
câu hỏi (một prompt, ba lần sinh, tái dùng KV cache). Kiểm mã cho thấy `replay.py`
nhận **một** seed cho cả mẻ và lặp theo câu hỏi. Sửa để lồng seed vào trong đòi
**14 điểm sửa**, và trong đó **hai điểm hỏng âm thầm**:

| Điểm hỏng | Hậu quả |
|---|---|
| Mẫu số `format_ok_rate` | 123 → 369 |
| `aggregate` đếm câu phủ định | 14 → 42, nên cột "Từ chối đúng" thành x/42 |

Không hàm nào raise. Bảng vẫn in ra những con số trông hợp lý.

Chạy ba lần riêng thay vì lồng thì phải trả tiền prefill ba lần: ~10 giờ thay vì
~7,9 giờ theo dự toán ban đầu, và không có bằng chứng nào trong mã hay tài liệu
rằng KV cache được tái dùng giữa các lượt gọi liên tiếp.

**Cơ sở để chọn N=1.** (a) Tiền lệ có sẵn: Bảng 4.5 của khóa luận báo Oracle,
BM25, Closed-book ở **một** lần chạy. (b) **Tính tất định đã được đo**: hai lần
chạy cùng seed, cùng bản dựng, cùng phần cứng cho câu trả lời **trùng khít từng
ký tự** trên 15/15 câu.

**Quyết định.** N=1 cho cả sáu ô, ghi rõ trong bài, và không sửa `replay.py`.

**Bài học học thuật.** Khi phương án phức tạp hơn có chế độ hỏng **không phát tín
hiệu**, phương án đơn giản hơn thường đúng — kể cả khi nó cho ít thông tin hơn.
Một độ lệch chuẩn không ai kiểm được tệ hơn việc không có độ lệch chuẩn.

---

## 3. Chẩn đoán trước khi can thiệp

### 3.1 Tách hai kiểu thất bại: "không biết luật" và "không viết nổi cú pháp"

**Vấn đề.** Mô hình 4 tỉ tham số có đủ năng lực cho tác vụ này không? Nếu không
thì phải leo thang lên 8B — đắt hơn, chậm hơn, và có thể vượt trần VRAM.

**Cách chẩn đoán.** Cổng FT-03 chạy 15 câu ở bốn cấu hình và đo **hai** đại lượng
tách rời:

- `soft_article_hit` — mô hình có **nhắc đúng** điều luật trong văn xuôi không?
- `format_ok_rate` — trích dẫn có **phân tích được** bằng bộ chấm không?

**Kết quả quyết định:**

| Đại lượng | Giá trị |
|---|---|
| `soft_article_hit` | **1,000 ở cả bốn ô** |
| `format_ok_rate` (0-shot) | **0,083** |

**Diễn giải.** Mô hình **định vị đúng điều luật** trong ngữ cảnh nhưng **không
viết nổi cú pháp trích dẫn**. Đây là tin tốt: hiểu sai thì khó chữa, viết sai thì
dạy được — và đó chính xác là thứ fine-tune sửa được.

**Quyết định.** Giữ 4B, nhánh leo thang 8B **không xảy ra**. Mục tiêu fine-tune
được định nghĩa lại từ "làm mô hình hiểu luật" thành "làm mô hình viết đúng định
dạng".

**Bài học học thuật.** Đo hai đại lượng tách rời cho phép chẩn đoán nguyên nhân,
chứ không chỉ ghi nhận thất bại. Một chỉ số gộp (F1 = 0,200) sẽ dẫn tới kết luận
sai là "mô hình quá nhỏ".

### 3.2 Đăng ký trước tiêu chí chọn tham số

**Vấn đề.** `presence_penalty` là tham số sinh có thể đổi kết quả. Chọn giá trị
nào?

**Rủi ro.** Chọn "giá trị cho điểm cao hơn" là chọn tham số **sau khi** thấy kết
quả — một dạng p-hacking, và hội đồng có quyền hỏi *"nếu giá trị kia cho điểm cao
hơn thì em có chọn nó không?"*

**Cách giải quyết.** **Đăng ký trước** quy tắc chọn, trước khi chạy: *"chọn giá
trị nhỏ nhất mà `hit_token_cap = 0"* — tức tiêu chí là **không có câu nào bị cắt
đuôi**, một tiêu chí kỹ thuật độc lập với điểm số.

Kết quả: `presence_penalty = 0` thoả tiêu chí. Nó **tình cờ** cũng cho điểm cao
hơn (F1 0,600 so với 0,531), nhưng lập luận chọn không dựa vào điều đó và bài
viết phải nói rõ như vậy.

**Bài học học thuật.** Đăng ký trước tiêu chí quyết định giúp phân biệt "chọn theo
nguyên tắc" với "chọn theo kết quả". Đây là điểm dễ bị chất vấn nhất và cũng dễ
phòng nhất.

### 3.3 Trung thực về độ phân giải thống kê

**Vấn đề.** Hiệu ứng của `presence_penalty` lên `format_ok` là 1/12 so với 2/12 —
tức **một câu**.

**Cách xử lý.** Tính khoảng tin cậy Wilson: **[0,015; 0,354]** so với
**[0,047; 0,448]**. Hai khoảng **chồng lấn gần hoàn toàn**. Kết luận được phát
biểu là *"hướng nhất quán trên cỡ mẫu nhỏ"* — không phải *"đã thiết lập được hiệu
ứng"*. Thứ đứng vững là **hướng nhất quán ở cả bốn ô** cộng với **cơ chế hợp lý**,
không phải bản thân con số.

Cùng tinh thần, `hit_token_cap = 0` trên 15 câu × 1 seed được đọc là *"không thấy
bằng chứng lặp"*, **không** phải *"đã loại trừ lặp"* — nền quá mỏng cho một sự
kiện hiếm.

**Bài học học thuật.** Báo cáo giới hạn của chính mình trước khi bị hỏi. Một kết
luận phát biểu đúng mức mạnh hơn một kết luận phát biểu quá mức.

---

## 4. Khớp phân phối dữ liệu huấn luyện với thứ được đo

### 4.1 Tỉ lệ mẫu từ chối: từ 20% xuống 9%

**Vấn đề.** Bộ dữ liệu đầu tiên có **20%** mẫu từ chối (1.000 trên 5.000). Con số
đó chọn theo trực giác rằng "hành vi từ chối quan trọng, cần nhiều mẫu".

**Phân tích lại.** Đếm trên bộ đánh giá thật:

| Đại lượng | Số câu thực sự đo được |
|---|---|
| Câu phủ định đi qua **mô hình sinh** | **4** trên 127 (3,1%) |
| Câu đo **F1 cấp Khoản** | **123** |

10 trên 14 câu bẫy do **nhánh truy hồi rỗng** quyết định — mô hình sinh chưa từng
được gọi, câu trả lời là một chuỗi hằng số.

**Lập luận quyết định (bất đối xứng rủi ro).** Huấn luyện 20% mẫu từ chối là dạy
mô hình nghiêng về từ chối trên **một phần năm** dữ liệu, để bảo vệ **4** câu, và
đánh cược **123** câu còn lại. Tỉ lệ đó không đứng vững.

**Điểm cần nói rõ.** Căn cứ ban đầu cho 20% là quan sát `tu_choi_dung` tụt từ
0,667 xuống 0,333 khi thêm few-shot — nhưng đó là **2/3 xuống 1/3**, một câu lật
trên mẫu số 3. Lập luận cắt **không** dựa vào con số đó; nó dựa vào bất đối xứng
4 so với 123, và lập luận này đứng vững bất kể con số kia mạnh hay yếu.

**Cách thực hiện.** Sinh lại toàn bộ với `FRAC_REFUSAL = 0,09`, giữ N = 5.000 —
thay vì lọc bớt dòng khỏi file đã có. Lý do: bộ dữ liệu tách train/val theo
`doc_name` (chống rò rỉ văn bản giữa hai tập), nên lọc dòng sẽ phá phân tách đó
và phải lọc song song file metadata. Sinh lại có ít đường hỏng hơn.

**Bài học học thuật.** Phân phối dữ liệu huấn luyện phải khớp với **thứ được đo**,
không khớp với trực giác về "điều gì quan trọng". Và khi hai lập luận cùng dẫn tới
một quyết định, nên nêu lập luận **mạnh** làm căn cứ chính thức.

### 4.2 Phân loại V005 và một lệch train/eval được chấp nhận có ý thức

**Vấn đề.** Bộ dữ liệu có hai loại mẫu từ chối:

- `refusal_no_basis` — ngữ cảnh **có** tài liệu liên quan nhưng **không đủ** căn
  cứ để kết luận
- `refusal_out_of_scope` — câu hỏi thuộc lĩnh vực **ngoài** phạm vi kho ngữ liệu

Khi cắt tỉ lệ, cắt loại nào? Cần biết bộ đánh giá thật chứa loại nào.

**Cách xác định.** Đọc ngữ cảnh thật của bốn câu phủ định đi qua mô hình:

| Câu | Loại | Bằng chứng |
|---|---|---|
| V105, V114, V117 | `out_of_scope` | ngữ cảnh trả về toàn văn bản đất đai, câu hỏi về giấy phép xây dựng / lệ phí trước bạ / thuế TNCN |
| **V005** | **`no_basis`** | **22/22** khối ngữ cảnh đều là văn bản đất đai, có cả Điều 46 NĐ 102 về *điều kiện* chuyển mục đích — nhưng câu hỏi hỏi về *trình tự, hồ sơ* |

**Hai hệ quả trái chiều.**

1. Ba câu `out_of_scope` bị chi phối bởi một **danh sách chặn cứng tường minh**
   nằm ngay trong system prompt (`context_assembler.py:368-373`), kèm chuỗi trả
   lời bắt buộc nguyên văn. Mô hình không cần nhiều mẫu để tuân theo một quy tắc
   luôn hiện diện trong ngữ cảnh mỗi lượt.
2. V005 là ca `no_basis` **duy nhất**, và là câu phủ định duy nhất mà **cả Gemini
   2.5 Pro cũng trả lời quá đà** (`negative_correct = False`, sinh 4 trích dẫn
   trong khi đáp án chuẩn rỗng). Đây là ca khó nhất.

**Quyết định.** Giữ nghiêng về `no_basis` khi cắt (315 so với 135, tỉ lệ 70/30
không đổi).

**Phát hiện đi kèm — một lệch train/eval có thật.** Đọc mẫu `no_basis` trong bộ
huấn luyện cho thấy: câu hỏi thường **tự khai ra số Điều** đang thiếu (dạng *"Theo
Điều 66 của Luật X, …"*) trong khi ngữ cảnh không chứa Điều đó. Nên phân biệt
"trả lời được / phải từ chối" rút gọn thành **tra chuỗi**: dò số Điều được nêu,
không thấy thì từ chối.

Nhưng V005 **không** có cấu trúc đó — không nêu số Điều nào, ngữ cảnh **đúng chủ
đề**, và mô hình phải tự phán đoán rằng *"điều kiện + thẩm quyền"* chưa trả lời
được *"trình tự, hồ sơ"*. Đó là **phán đoán về tính đầy đủ của căn cứ**, không
phải tra cứu. Kỹ năng mà 315 mẫu đang dạy **không chuyển giao** sang ca này.

**Quyết định: ghi vào hạn chế, không thiết kế lại bộ sinh.** Lý do là chính lập
luận bất đối xứng rủi ro ở §4.1 — toàn bộ ảnh hưởng của thiết kế `no_basis` lên
bảng kết quả là **đúng một câu**. Dựng lại bộ sinh cho một câu là lặp lại đúng
sai lầm vừa sửa.

**Bài học học thuật.** Phát hiện một lệch train/eval và **quyết định có ý thức**
không sửa nó, kèm lập luận định lượng, mạnh hơn cả việc không phát hiện ra và
mạnh hơn cả việc sửa nó mà không cân chi phí. Điều bắt buộc là **ghi lại**.

### 4.3 Kiểm dữ liệu bằng mắt: việc không tự động hoá được

**Vấn đề.** Có `assert` tự động kiểm cú pháp trích dẫn, kiểm độ dài, kiểm mã văn
bản có mặt trong ngữ cảnh. Nhưng chúng không kiểm được **nội dung có ý nghĩa
không**.

**Cách giải quyết.** Xuất 20 mẫu đầy đủ (`reports/samples_20.txt`) và đọc tay, trả
lời ba câu hỏi:

1. Mã văn bản trong khối trích dẫn có xuất hiện trong ngữ cảnh của **chính mẫu
   đó** không? *(Nếu không → đang dạy mô hình bịa từ trí nhớ.)* → **Đạt**, kiểm
   được cả bằng máy: 15/15 mẫu có trích dẫn đều đạt, 5 mẫu từ chối có đúng 0 trích
   dẫn.
2. Mẫu từ chối loại "thiếu căn cứ" có thật sự khó không? → **Không** — xem §4.2.
3. Câu trả lời có bám vào điều luật trong ngữ cảnh, hay nói chung chung? →
   **Đạt**, xác nhận bằng đọc tay.

**Bài học học thuật.** Câu hỏi 1 và 3 nghe giống nhau nhưng thuộc hai hạng khác
nhau: câu 1 kiểm được bằng máy, câu 3 thì không. Biết ranh giới đó là biết bộ
kiểm thử của mình dừng ở đâu.

---

## 5. Tái lập: một kỷ luật chủ động, không phải một trạng thái

### 5.1 Bản vá sống ngoài git — phát hiện bằng kiểm chứng chéo

**Vấn đề.** Kết quả cổng FT-03 được sinh trên môi trường tính toán từ xa theo quy
trình: clone repo, **vá tại chỗ**, chạy. Bản vá — hai khoá bổ sung cho chat
template Qwen3 — **chưa từng nằm trong bất kỳ commit nào**. Nghĩa là bốn con số
của cổng do "commit `eecdc7b7` **cộng** một đoạn mã không tồn tại trong repo" sinh
ra.

**Cách phát hiện.** Đối chiếu log đã lưu với mã trong repo. Log cho thấy lần chạy
đầu báo `render-loi:UndefinedError` với prompt 10.133 token, các lần sau báo
`gguf-chat-template-jinja2` với 10.144 token — **mã đã đổi giữa hai lần**. Nhưng
`git log --all -S"reasoning_content"` trả về rỗng: chuỗi đó chưa từng xuất hiện
trong lịch sử repo.

**Đánh giá mức nghiêm trọng.** Bản vá chỉ đụng `render_prompt`, còn đường sinh văn
bản đi qua `create_chat_completion` dùng template C++ của llama.cpp — **độc lập
hoàn toàn**. Nên bốn con số **không bị ảnh hưởng**; thứ bị ảnh hưởng chỉ là cách
đếm độ dài prompt và chức năng xuất prompt. Đây **không** phải lỗ hổng số liệu,
mà là lỗ hổng **tái lập**: khóa luận sẽ ghim một commit hash, nhưng mã thật sinh
ra số là commit đó cộng thêm một thứ.

**Cách giải quyết.** Đưa bản vá vào git, và giữ điều kiện tự kiểm trong đoạn vá
tại chỗ để nó tự trở thành vô tác dụng khi mã đã có sẵn.

**Lặp lại lần hai.** Cùng loại lỗi tái diễn trong phiên huấn luyện: ba bản vá phát
sinh tại chỗ trên máy thuê (đường dẫn script, điều kiện nhận diện checkpoint,
thông điệp báo). Chúng cũng phải được đưa về git sau đó.

**Bài học học thuật.** Quy trình "clone rồi vá tại chỗ" **luôn** tạo ra khoảng
cách giữa mã được ghim và mã được chạy. Đó không phải sự cẩu thả một lần mà là
**thuộc tính cấu trúc của quy trình** — và cách chữa là đổi quy trình: logic nằm
trong script đã commit, môi trường chạy chỉ gọi script.

### 5.2 Tám giá trị ghim

Tuyên bố tái lập của mục 4.7 dựa trên tám giá trị, mỗi giá trị có nguồn xác minh
độc lập:

| # | Đối tượng | Vai trò |
|---|---|---|
| 1 | Tarball llama.cpp (tag `b10165`) | công cụ **tạo** file GGUF |
| 2 | Wheel `llama-cpp-python` 0.3.16 | công cụ **chạy suy luận, sinh số liệu** |
| 3 | File GGUF mô hình gốc + revision | mô hình gốc của hàng "chưa tinh chỉnh" |
| 3b | **Tên kho mô hình gốc dùng để huấn luyện** — bản lượng tử-4-bit, không phải bản bf16 mà cờ CLI ghi | điểm xuất phát của adapter |
| 4 | Commit code trên nhánh fine-tune | mã đã chạy |
| 5 | `train.jsonl` + `val.jsonl` | dữ liệu huấn luyện |
| 6 | File GGUF đã tinh chỉnh | mô hình kết quả |
| 7 | **Ghim GPU** — mỗi ô một card, tường minh | điều kiện phần cứng |
| 8 | **Hai file nguồn ngữ cảnh + sha256 của chúng** | đầu vào đông cứng của cả sáu ô |

Bốn điểm đáng nêu trong bài:

**Giá trị 1 và 2 là hai bản dựng llama.cpp khác nhau, và điều đó là cố ý.** Một
bản tĩnh chỉ dùng CPU để lượng tử hoá (việc này không cần GPU); một bản có CUDA
để chạy suy luận. Ghi cả hai kèm nói rõ cái nào dùng cho việc gì.

**Giá trị 3 phải khôi phục, không có sẵn.** sha256 của mô hình gốc chưa từng được
ghi vào repo — phiên FT-03 đọc nó từ một file manifest nằm trên môi trường tạm và
chỉ in *"sha256 khớp"* chứ không in chuỗi. Khôi phục bằng cách đọc **metadata LFS
của HuggingFace tại đúng revision đã ghim** — một nguồn thẩm quyền hơn cả manifest
cũ. Ghi vào repo lần này.

**Giá trị 7 là phát hiện muộn.** Môi trường đánh giá cấp **hai** card. Với cấu
hình đẩy toàn bộ layer lên GPU, llama.cpp **tự chia layer qua cả hai card**. Model
lượng tử hoá chỉ 2,4 GB nên chia **không nhanh hơn**, mà đổi thứ tự phép rút gọn.
Rủi ro thật không phải "sai" mà là **không nhất quán giữa các ô** — nếu một ô chạy
khi cả hai card rảnh và ô khác chạy khi một card đang bận, cấu hình chia layer
khác nhau, và cột Δ đo lẫn cả khác biệt phần cứng. Cách xử: **ghim tường minh mỗi
ô vào đúng một card**, kiểm soát chặt hơn cả việc để công cụ tự quyết.

**Giá trị 8 là giá trị phải ghim vì nó đã thay đổi thật.** Khi vế GraphRAG đổi sang
mẻ ngữ cảnh mới còn vế Naive giữ nguyên mẻ cũ, câu hỏi *"sáu ô này nhận đúng cái gì?"*
không còn trả lời được bằng một dấu thời gian duy nhất. Cách xử: ghi **đường dẫn kèm
sha256 của cả hai file nguồn vào chính file kết quả** (`replay.src_file`,
`replay.src_sha256`) và vào bản ghi trạng thái lần chạy. Một người đọc lại về sau
không phải tin lời tài liệu — họ tính lại sha256 và đối chiếu.

**Giá trị 3b là loại lỗi tái lập tinh vi nhất trong bộ này.** Bảy giá trị kia đều là
thứ ta *chủ động* ghi ra. Giá trị 3b là thứ **công cụ tự đổi sau lưng**: lệnh truyền
tên một kho, thư viện nạp một kho khác, và không có dòng log nào báo việc chuyển
hướng — nó chỉ hiện ra khi đọc `adapter_config.json` của checkpoint. Người tái lập
chạy đúng lệnh đã công bố vẫn có thể nạp sai trọng số. Xem §2.4.

### 5.3 Đặc tả sai được mã bắt lại

Trong quá trình triển khai, hai chỗ **đặc tả sai** đã bị phát hiện nhờ nguyên tắc
*"không đoán chữ ký hàm — đọc mã thật, trích số dòng"*:

| Đặc tả nói | Mã thật | Hậu quả nếu tin đặc tả |
|---|---|---|
| `presence_penalty` mặc định là 0, đừng truyền lại | mặc định là **1.0** | cả 822 lượt chạy sai bộ tham số đã chốt, **không có dấu hiệu nào** trong log |
| trường `system` trong file kết quả là chuỗi system prompt | là **tên hệ** (`"graphrag"`/`"baseline"`), dùng làm khoá tra bảng | phép kiểm cổng chặn luôn báo sai |

Chỗ thứ nhất đặc biệt đáng nêu: nó sẽ làm hàng gốc cho F1 0,531 thay vì 0,600 và
hàng FT cũng lệch, mà cột Δ vẫn ra một con số trông hợp lý.

**Bài học học thuật.** Một quy tắc quy trình đơn giản — *đọc mã, đừng đoán* — bắt
được lỗi mà không có kiểm thử tự động nào bắt được. Quy tắc rẻ, hậu quả bị chặn
thì đắt.

### 5.4 Bước lưu trữ báo thành công trong khi không lưu gì cả

**Vấn đề.** Cuối chặng huấn luyện, script đẩy thư mục adapter lên kho lưu trữ rồi
in xác nhận. Log ghi ba dòng liên tiếp:

```
Found 33 files to upload
Uploading... 33/33 files checked, 0/0 uploaded (0.00B transferred), 0 committed in 0 commit(s)
✓ Uploaded
OK: adapter da luu tren HF.
```

Dòng giữa nói đúng chuyện đã xảy ra: **33 file được kiểm, 0 file được tải lên, 0 lần
commit, 0 byte truyền**. Nhưng mã thoát là 0, dòng sau in dấu ✓ màu xanh, và câu tổng
kết khẳng định adapter đã lưu. Trên kho lưu trữ, thư mục `adapter/<RUN_NAME>/` chỉ có
đúng một file — `rendered_samples.txt`.

**Vì sao nó thoát ra được mọi lớp kiểm.** Ba dấu hiệu mà người vận hành thường dùng
để biết một bước đã chạy được — mã thoát, thông điệp xác nhận, màu sắc — đều **báo
thành công**. Dấu hiệu duy nhất nói sự thật là một con số nằm giữa một dòng thống kê
mà không ai đọc. Đây **cùng một họ** với ca *"lệnh tải về khớp 0 file mà vẫn báo
thành công"*: công cụ coi *"đã xử lý xong danh sách rỗng"* là **thành công**, còn
người dùng đọc dấu ✓ là *"đã có dữ liệu"*. Hai cách hiểu chữ "thành công" khác nhau,
và không lớp nào bắc cầu giữa chúng.

**Hệ quả thật, không phải giả định.** `adapter/train_result.json` và
`adapter/length_stats.json` — hai hiện vật định lượng của phiên huấn luyện — **không
tồn tại ở nơi lẽ ra chúng phải nằm**. Chúng phải được khôi phục từ hai nguồn khác:
thư mục `checkpoint-588` (do cơ chế lưu checkpoint định kỳ đẩy lên, độc lập với lần
đẩy hỏng này) cho `adapter_config.json`, và **log huấn luyện** cho toàn bộ số liệu
loss / runtime / audit độ dài. May mắn là log có đủ; nếu chặng đẩy log cũng hỏng
theo cùng kiểu thì phiên 2 sẽ mất trắng số liệu.

**Cách giải quyết.** Bước lưu trữ phải **kiểm hậu điều kiện**, không kiểm mã thoát:
đọc lại danh sách file trên kho sau khi đẩy và so với danh sách đã gửi; lệch thì
`exit` khác 0. Cùng nguyên tắc với `sha256sum -c` ở chặng `data` — chặng đó làm đúng,
chặng `publish` thì không.

**Bài học học thuật.** Một bước không có phép kiểm hậu điều kiện thì thông điệp thành
công của nó **không phải bằng chứng**. Điều này áp cho mọi bước ghi ra bên ngoài tiến
trình: đẩy file, ghi cơ sở dữ liệu, gọi dịch vụ. Và nó nối thẳng với §5.1: tuyên bố
tái lập ghim vào hiện vật, mà hiện vật thì phải **kiểm là đã có thật**, không phải
kiểm là *"lệnh tạo ra nó đã chạy"*.

---

## 6. Giới hạn của xác minh tự động

**Vấn đề.** Kế hoạch đặt ba bước kiểm hạ tầng trước khi sinh dữ liệu đánh giá.
Bước thứ hai là *"mở chuỗi prompt đã render ra và **đọc bằng mắt**"*, kèm ghi chú:
*"Không có kiểm thử tự động nào thay được."*

Khi chạy, script xuất prompt rồi tự kiểm và in **đạt**: đúng phương thức render,
đúng số lượt vai, kết thúc đúng chuỗi mong đợi.

**Vì sao dấu "đạt" đó chưa đủ.** Các phép kiểm đó bắt **hỏng có cấu trúc**. Nhưng
mục đích của bước này là bắt **hỏng âm thầm** — system prompt bị cắt đầu, vai
few-shot sai, ví dụ mẫu dạy sai định dạng. Loại hỏng đó **không làm sai cấu trúc
nào cả**.

**Cách giải quyết.** Đọc tay hai file prompt (cấu hình phức tạp nhất và đơn giản
nhất), kiểm năm mục:

| # | Mục | Kết quả |
|---|---|---|
| 1 | Khối phạm vi kho ngữ liệu + chuỗi từ chối nguyên văn còn trong system prompt | đạt — đây là khối quyết định **3 trên 4** câu từ chối |
| 2 | Hai lượt few-shot dùng **mã văn bản giả**, và mỗi mã có mặt trong header ngữ cảnh của **chính ví dụ đó**, toạ độ Điều/Khoản/Điểm **trùng khít** trích dẫn | đạt |
| 3 | Ngữ cảnh là văn bản luật thật, số khối khớp `top_k_count` của câu đó trong file nguồn | đạt (22/22) |
| 4 | Dấu tiếng Việt nguyên vẹn | đạt |
| 5 | Prompt kết thúc bằng câu hỏi → chỉ dẫn trả lời → thẻ mở lượt, **không có ký tự nào sau đó** | đạt |

**Mục 2 là phát hiện có giá trị nhất.** Ví dụ mẫu dùng mã văn bản **giả**
(`luat-vi-du-2019`) chứ không dùng mã thật. Ban đầu trông như lỗi; thực ra là
thiết kế đúng — nếu ví dụ dùng mã thật, mô hình có thể học phát ra chính mã đó
theo phản xạ bất kể ngữ cảnh chứa gì, đúng thất bại mà bộ dữ liệu dựng `assert`
để chặn. Mã giả buộc mô hình học **cơ chế sao chép mã từ header**, không học một
mã cụ thể. Điều kiện để lập luận này đúng — mã giả phải có mặt trong ngữ cảnh của
chính ví dụ đó — đã được xác minh.

**Mục 5 là phép kiểm quan trọng nhất.** Nếu có bất kỳ ký tự nào sau thẻ mở lượt
trả lời, mô hình sẽ **tiếp nối** một đoạn có sẵn thay vì **bắt đầu** câu trả lời,
và mọi câu trả lời lệch theo cách rất khó thấy.

**Một xác nhận ngoài dự kiến.** Prompt 2-shot dài **10.556 token** — **trùng khít**
con số của phiên cổng FT-03 một ngày trước, trên một mô hình khác. Hai lần dựng
prompt độc lập ra cùng con số là bằng chứng mạnh rằng khuôn prompt không đổi giữa
hai phiên.

**Bài học học thuật.** Kiểm thử tự động bắt được loại lỗi mà người viết nó **đã
nghĩ tới**. Với loại lỗi chưa nghĩ tới, cần một người đọc. Biết phân biệt hai
loại đó là biết bộ kiểm thử của mình bảo vệ được gì.

---

## 7. Đọc kết quả trung thực

### 7.1 Cột "Từ chối đúng" không so được giữa hai cột

**Vấn đề.** Bảng kết quả cho `Từ chối đúng` = 13/14 ở cột GraphRAG và 8/14 ở cột
Naive cho cùng mô hình đã tinh chỉnh. Đọc thẳng thì thành *"GraphRAG giúp từ chối
tốt hơn hẳn"*.

**Thực tế.** Số câu đi qua mô hình sinh khác nhau giữa hai cột:

| Cột | Câu đi qua mô hình | Câu do truy hồi quyết định |
|---|---|---|
| GraphRAG | 127/137 | **10** — nhánh ngữ cảnh rỗng, câu trả lời là chuỗi hằng số |
| Naive | 137/137 | 0 |

Nên phần lớn chênh lệch là khác biệt **đường ống**, không phải khác biệt **mô hình
sinh**. Mà mục 4.7 nói về mô hình sinh.

**Thêm một hiện vật.** Hàng gốc 0-shot cũng cho 0,929 (13/14) — nhưng ô đó gần
như không sinh nổi trích dẫn nào (`format_ok_rate` 0,065), và `negative_correct`
đúng khi **không có** trích dẫn. Nó "từ chối đúng" **do hỏng**, không do biết từ chối.

**Cách xử lý.** Nếu giữ cột này trong bảng thì bắt buộc kèm số câu đóng băng và
giải thích hiện vật trên. Nếu bỏ thì mất một thang đo mà Bảng 4.5 có.

### 7.2 Ngưỡng cảnh báo đặt sai gây dương tính giả

Script được yêu cầu cảnh báo nếu hai ô cùng mô hình, cùng cấu hình nhưng khác
nguồn ngữ cảnh lệch quá **25%** về thời gian mỗi câu. Nó đã cảnh báo.

Nhưng đọc lại toàn bộ ba cặp: hai cặp chạy trên **cùng một card** lệch **45%** và
**78%**. Vậy con số 83% của cặp còn lại nằm trong dải đã quan sát được ngay trên
một card. Nguyên nhân là prompt GraphRAG dài hơn prompt Naive khoảng 2,5 lần nên
giai đoạn nạp prompt chi phối — tỉ lệ 2:1 là điều **phải** xảy ra. Ngưỡng đúng
đáng lẽ quanh 150%.

**Kết luận: không có bằng chứng phần cứng bị hạ tần.** Nhưng cột độ trễ vẫn không
nên đưa vào mục 4.7, vì nó đo dưới tải song song hai card nên không so được với
cột độ trễ của Bảng 4.5 (Gemini qua API).

**Bài học học thuật.** Một ngưỡng cảnh báo đặt sai tạo ra kết luận sai theo cả hai
chiều. Cách kiểm là đối chiếu cảnh báo với **nhóm đối chứng** — ở đây là các cặp
chạy trên cùng một card.

### 7.3 Kết quả âm phải báo cáo

**Tinh chỉnh không thắng được hai ví dụ mẫu.**

| | F1 cấp Khoản (GraphRAG) | `format_ok_rate` |
|---|---:|---:|
| Đã tinh chỉnh, 0-shot | 0,402 | 0,756 |
| **Gốc, 2-shot** | **0,511** | **0,854** |

Mốc đặt ra trước khi huấn luyện — mô hình tinh chỉnh phải vượt mô hình gốc ở cấu
hình 2-shot — **không đạt**, và khoảng cách là **0,109** F1 cấp Khoản.

**Bằng chứng nhất quán từ đường huấn luyện.** `eval_loss` sau epoch 1 là 0,3129,
sau epoch 2 là 0,3082 (`finetune/logs/ft04-5k-2ep-20260729-2122.log:377-378`) —
cải thiện **1,5%** cho gần một nửa tổng thời gian tính toán (tổng
`train_runtime` 19 480 giây, tức 5 giờ 24 phút). Tác vụ **bão hoà rất nhanh**.

Một hiện vật thứ hai cùng chiều: adapter chỉ huấn luyện **33 030 144 trên
4 055 498 240 tham số — 0,81%** (`…2122.log:90`). Dung lượng đó đủ để dịch chuyển
cách trình bày, và kết quả cho thấy dịch chuyển đó **không bù được** hai ví dụ đặt
trực tiếp trong ngữ cảnh.

**Diễn giải.** Với tác vụ mà nội dung chính là học **định dạng đầu ra**, hai ví dụ
đặt trong ngữ cảnh hiệu quả hơn 5.000 mẫu huấn luyện. Đây là kết quả âm có giá
trị khoa học, và khóa luận vốn có tiền lệ báo cáo kết quả âm (Bảng 4.5 báo Oracle
và closed-book đúng tinh thần đó).

**Chỗ tinh chỉnh có thắng.** Từ chối đúng 13/14 so với 12/14 (GraphRAG) và 8/14 so
với 7/14 (Naive) — nhưng chênh **một câu** trên mẫu số 14 thì không kết luận được
gì, và phải nói thẳng như vậy.

### 7.4 Kết luận đứng vững, và ba cách đọc sai phải chặn trước

| Mô hình sinh | Naive | GraphRAG | Δ | Tỉ lệ GraphRAG/Naive |
|---|---:|---:|---:|---:|
| Gemini 2.5 Pro | 0,436 | 0,617 | **+0,181** | 1,416 |
| Cục bộ đã tinh chỉnh, 0-shot | 0,301 | 0,402 | **+0,101** | 1,336 |
| Cục bộ gốc, 2-shot | 0,239 | 0,511 | **+0,272** | 2,137 |
| Cục bộ gốc, 0-shot | 0,154 | 0,131 | −0,022 | 0,854 |

**Kết luận chính — và nó không đổi.** Δ **dương ở mọi cấu hình mà thang đo còn phân
giải**: ba trên bốn hàng, gồm cả hàng mô hình cục bộ đã tinh chỉnh và hàng mô hình
cục bộ gốc ở cấu hình mạnh nhất của nó. Kết luận của Câu hỏi 1 vì thế **không phụ
thuộc vào việc chọn Gemini**. Đây vẫn là phát biểu chính của mục 4.7.

**Ba cách đọc sai phải chặn trước khi hội đồng hỏi:**

**(1) Hàng gốc 0-shot có Δ âm — đó là hiệu ứng sàn, không phải phản chứng.** Ô đó
có `format_ok_rate` = **0,065**, tức chỉ 8 trên 123 câu trả lời phân tích được. So
0,131 với 0,154 là so hai con số gần bằng không; thang đo **không có phân giải** ở
đó nên nó không phát biểu được gì về chiều của Δ. Lập luận đầy đủ ở §2.3, và chính
đây là lý do hàng gốc được chạy **cả hai** biến thể.

**(2) Hàng gốc 2-shot có tỉ lệ cao nhất — nêu như quan sát, KHÔNG diễn giải.** Tỉ lệ
2,137 là con số lớn nhất bảng, và cám dỗ tự nhiên là đọc nó thành *"mô hình càng yếu
càng hưởng lợi từ GraphRAG"*. **Không được kết luận như vậy.** Mẫu số của tỉ lệ đó là
**0,239** — thấp nhất trong ba hàng có phân giải — nên tỉ lệ **rất nhạy với nhiễu**:
một dao động nhỏ ở mẫu số kéo tỉ lệ đi rất xa, trong khi cùng dao động đó gần như
không đụng tới các hàng có mẫu số lớn hơn. Muốn phát biểu về quan hệ *"quy mô mô hình
↔ mức hưởng lợi"* thì cần nhiều hơn ba điểm dữ liệu và cần khoảng tin cậy cho từng
tỉ lệ — không có cái nào trong hai thứ đó. Ghi lại như một **quan sát cần thận trọng**.

**(3) Cột tỉ lệ không thay được cột Δ.** Cột Δ là đại lượng mà thiết kế thực nghiệm
cô lập được (cùng ngữ cảnh, cùng tham số sinh, cùng phần cứng — chỉ khác hệ truy hồi).
Cột tỉ lệ là một phép chia thêm vào sau, và phép chia khuếch đại nhiễu của mẫu số.
Nguyên tắc ghi trong kế hoạch — *"cột Δ là thứ duy nhất quan trọng"* — vẫn là nguyên
tắc đúng.

**Nói gọn cho phần trả lời hội đồng.** Lợi ích của GraphRAG xuất hiện ở cả mô hình
sinh thương mại quy mô lớn lẫn mô hình 4 tỉ tham số chạy cục bộ, ở cả bản gốc lẫn bản
đã tinh chỉnh. Nó **thuộc về cơ chế truy hồi**, không thuộc về năng lực riêng của một
mô hình sinh cụ thể. Cấu hình duy nhất không cho Δ dương là cấu hình mà thang đo đã
mất phân giải, và điều đó được đo chứ không được suy.

### 7.5 Fine-tune có tác dụng không — phép so phải cô lập đúng một biến

§7.3 báo một kết quả âm: mô hình đã tinh chỉnh thua mô hình gốc ở cấu hình 2-shot.
Đọc riêng nó dễ dẫn tới kết luận *"fine-tune vô ích"*. Kết luận đó **sai**, và lý do
là phép so ở §7.3 **không cô lập được tác dụng của fine-tune**: `base@2-shot` khác
`FT@0-shot` ở **hai** thứ cùng lúc — mô hình **và** số ví dụ mẫu.

Phép so cô lập được là **cùng số ví dụ mẫu, khác mô hình**:

| | `format_ok_rate` GraphRAG | `format_ok_rate` Naive | F1 Khoản GraphRAG | F1 Khoản Naive |
|---|---:|---:|---:|---:|
| Gốc, 0-shot | 0,065 | 0,211 | 0,131 | 0,154 |
| **Đã tinh chỉnh, 0-shot** | **0,756** | **0,894** | **0,402** | **0,301** |
| Hệ số | **×11,6** | ×4,2 | ×3,1 | ×2,0 |

Fine-tune làm **đúng thứ nó được thiết kế để làm** — mục tiêu định nghĩa ở §3.1 là
*"dạy định dạng đầu ra"*, và tỉ lệ trả lời phân tích được tăng **11,6 lần** trên cột
GraphRAG. Đây là phép đo trực tiếp, không phải suy luận.

**Hai ô mà mô hình tinh chỉnh thắng cả `base@2-shot`:**

| | Gốc, 2-shot | Đã tinh chỉnh, 0-shot |
|---|---:|---:|
| F1 Khoản, cột **Naive** | 0,239 | **0,301** |
| Từ chối đúng, Naive | 7/14 | **8/14** |
| Từ chối đúng, GraphRAG | 12/14 | **13/14** |

Nó chỉ thua ở **cột GraphRAG**. Trên cột Naive nó thắng hoặc hoà ở mọi thang đo.

#### Giả thuyết cho việc thua riêng ở cột GraphRAG

Mẫu huấn luyện mang ngữ cảnh GraphRAG được **tổng hợp** bằng cách đóng gói 4–6 điều
từ kho văn bản (§4.2 của PHẦN C, bước 3). Ngữ cảnh GraphRAG **thật** do đường truy
hồi sinh ra thì khác hẳn: tới 22 khối, tiêu đề ghi cấp bậc văn bản và ngày hiệu lực,
có khối cảnh báo sửa đổi, có cả văn bản hết hiệu lực lẫn còn hiệu lực trộn lẫn.

Ngược lại, ngữ cảnh Naive gần như **giống nhau ở hai bên** — chỉ là các đoạn văn bản
cắt theo chunk.

Nếu giả thuyết đúng thì mọi quan sát khớp: mô hình học trên ngữ cảnh GraphRAG *sạch
hơn thực tế*, nên **thắng ở cột Naive và thua ở cột GraphRAG**. Nó cũng giải thích vì
sao `format_ok_rate` của hàng tinh chỉnh ở cột Naive (0,894) ngang `base@2-shot`
(0,894) trong khi ở cột GraphRAG (0,756) thì kém hơn (0,854).

**Kiểm được, không cần GPU:** so phân bố số khối và cấu trúc tiêu đề giữa ngữ cảnh
GraphRAG trong `finetune/data/train.jsonl` và ngữ cảnh GraphRAG thật trong file kết
quả. Chưa làm — ghi lại như việc còn mở.

#### Một ô chưa ai chạy: `FT@2-shot`

Ma trận không có ô này, vì lý do phương pháp ở §2.2 (dữ liệu huấn luyện là 0-shot,
đánh giá ở 2-shot là lệch train/eval). Lý do đó vẫn đúng. Nhưng nó có nghĩa là ta
**không biết** hai cách dạy định dạng có cộng dồn được không. Chi phí bổ sung khoảng
25 phút trên môi trường miễn phí; nếu chạy thì phải khai báo rõ là cấu hình lệch
train/eval và báo **riêng**, không đưa vào ma trận chính.

#### Phát biểu đúng cho khóa luận

> Trên tác vụ mà nội dung chính là học **định dạng đầu ra**, hai ví dụ đặt trong ngữ
> cảnh là một cách dạy **cạnh tranh được** với tinh chỉnh, và trên ngữ cảnh GraphRAG
> thì tốt hơn. Tinh chỉnh vẫn có tác dụng rõ rệt và đo được — tăng tỉ lệ trả lời đúng
> khuôn **11,6 lần** ở cùng điều kiện — nhưng dữ liệu huấn luyện tổng hợp có thể là
> lý do nó chưa phát huy hết trên ngữ cảnh truy hồi phức tạp.

Một khác biệt thực tế mà bảng không thể hiện: cấu hình 2-shot ngốn **412 token mỗi
câu hỏi, vĩnh viễn**, trong cửa sổ 16.384 mà ngữ cảnh đã chiếm gần 9.000. Tinh chỉnh
trả một lần 5 giờ 24 phút rồi thôi. Với 137 câu thì không đáng kể; ở quy mô vận hành
thì đó là thuế thường trực.

---

## 8. Hai chỗ tài liệu dự án cần sửa

Phát hiện trong quá trình làm, cần sửa trước khi bảo vệ:

**Mục 3.5.5 của khóa luận** viết *"Mô hình sinh chạy ở nhiệt độ 0 để câu trả lời
ổn định qua các lần chạy."* Câu này **không đúng** cho hai hàng cục bộ. Chúng chạy
ở `temperature 0.7 · top_p 0.8 · top_k 20` theo khuyến nghị của nhà phát hành mô
hình, vì giải mã tham lam (greedy) dễ rơi vào lặp vô tận — và khối trích dẫn nằm
ở **cuối** câu trả lời nên lặp đúng bằng mất trích dẫn.

Lập luận đúng để thay: **tính tất định đến từ seed cố định + cùng bản dựng thư
viện + cùng phần cứng**, đã chứng minh bằng thực nghiệm (hai lần chạy cho câu trả
lời trùng khít từng ký tự trên 15/15 câu). Đây cũng là cơ sở của quyết định N=1 ở
§2.5, nên hai chỗ phải nhất quán.

**Mục 5.4 (Hướng phát triển)** có gạch đầu dòng *"Tinh chỉnh mô hình nhúng hoặc
mô hình sinh đặc thù cho miền pháp luật."* Phần "mô hình sinh" nay đã **thực
hiện** và có kết quả, nên phải chuyển thành kết quả và trỏ về mục 4.7; phần "mô
hình nhúng" giữ nguyên là hướng phát triển.

---

## 9. Danh mục hạn chế để đưa vào mục 5.3

1. **N=1** cho cả sáu ô cục bộ — không có độ lệch chuẩn. Cơ sở: tiền lệ Bảng 4.5
   và tính tất định đã đo. (§2.5)
2. **Tham số sinh khác hàng Gemini** — hai hàng cục bộ ở nhiệt độ 0,7, không phải
   0. Có lý do kỹ thuật, nhưng là một khác biệt cần khai báo. (§8)
3. **Cột "Từ chối đúng" có mẫu số hiệu dụng khác nhau** giữa hai cột: 10/14 câu
   phủ định của cột GraphRAG do truy hồi quyết định. (§7.1)
4. **Hàng gốc 0-shot bị hiệu ứng sàn** — `format_ok_rate` 0,065, thang đo không
   có phân giải; Δ âm ở hàng này không phải bằng chứng chống kết luận. (§2.3, §7.4)
5. **Lệch train/eval ở mẫu từ chối `no_basis`** — mẫu huấn luyện dạy tra cứu, ca
   đánh giá duy nhất đòi phán đoán về tính đầy đủ căn cứ. Chấp nhận có ý thức.
   (§4.2)
6. **Một câu chạm trần `max_new_tokens`** (V020, ô 2) — mất trích dẫn vì lý do
   thuần kỹ thuật. Không chạy lại riêng câu đó để giữ điều kiện "sáu ô cùng tham
   số sinh".
7. **Cột độ trễ không so được** với Bảng 4.5 — đo dưới tải song song hai card.
   (§7.2)
8. **Tinh chỉnh không vượt được mô hình gốc ở cấu hình 2-shot.** (§7.3)
9. **Mô hình huấn luyện từ bản sao của nhà cung cấp công cụ**, còn mô hình gốc
   dùng bản lượng tử hoá từ bản phát hành chính thức. Chat template đã được xác
   minh trùng khít, nhưng bản thân trọng số không được đối chiếu bit-đối-bit.
   (§2.4)
10. **Tỉ lệ lợi ích tương đối của hàng gốc 2-shot có mẫu số thấp**, nên nhạy với
   nhiễu; không dùng nó để phát biểu về quan hệ giữa quy mô mô hình sinh và mức
   hưởng lợi từ GraphRAG. (§7.4)
11. **Cải thiện ở tầng truy hồi không tự động chuyển giao sang mô hình sinh nhỏ
   hơn** — quan sát sơ bộ, đáng khảo sát riêng, nằm ngoài phạm vi khoá luận.
12. **Một bước lưu trữ hiện vật huấn luyện đã hỏng âm thầm**, buộc phải khôi phục
   số liệu phiên 2 từ log và từ checkpoint thay vì từ hiện vật gốc. (§5.4)
