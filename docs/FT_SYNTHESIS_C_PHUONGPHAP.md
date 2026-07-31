# TỔNG HỢP FINE-TUNE — PHẦN C: PHƯƠNG PHÁP VÀ TRIỂN KHAI

> **Phạm vi.** Thuật lại **phương pháp** đã dùng, theo thứ tự đã làm, kèm lý do
> chọn. Đây là nguyên liệu cho phần mô tả phương pháp của mục 4.7 và các bổ sung
> vào chương 3.
>
> **Quan hệ với hai phần kia.**
> - **PHẦN A** (`FT_SYNTHESIS_A_SOLIEU.md`) — bảng giá trị chính xác, nguồn file.
>   Mọi con số trong tài liệu này **phải đối chiếu lại với Phần A** trước khi đưa
>   vào khóa luận; các con số ở đây là để hiểu mạch, Phần A là nguồn thẩm quyền.
> - **PHẦN B** (`FT_SYNTHESIS_B_KHOKHAN.md`) — khó khăn, lập luận quyết định, bài
>   học. Tài liệu này chỉ trỏ chéo, không lặp lại.
>
> Ký hiệu **⚠️KIỂM** đánh dấu con số cần xác nhận từ Phần A.

---

## 1. Thiết kế thực nghiệm

### 1.1 Câu hỏi cần trả lời

Bảng 4.2 giữ **mô hình sinh** cố định (Gemini 2.5 Pro) và đổi **cơ chế truy hồi**,
cho kết luận GraphRAG 0,617 so với Naive RAG 0,436. Mục 4.7 đảo trục: giữ **truy
hồi** cố định, đổi **mô hình sinh**, để trả lời *"kết luận của Câu hỏi 1 có phụ
thuộc vào việc chọn Gemini không?"*

Ma trận đích: ba mô hình sinh × hai hệ truy hồi. Đại lượng quan tâm là **cột Δ**
(chênh lệch GraphRAG − Naive **trong cùng một hàng**), không phải F1 tuyệt đối của
từng hàng. Đây là trục **trực giao** với Bảng 4.2, không phải một hệ tham chiếu
thứ năm của Bảng 4.5.

### 1.2 Chiến lược ba phiên

| Phiên | Nhiệm vụ | Vai trò trong lập luận |
|---|---|---|
| **1 — Cổng** | 15 câu, mô hình gốc, 4 cấu hình | Chẩn đoán: mô hình 4B có đủ năng lực không? Lỗi thuộc loại nào? |
| **2 — Huấn luyện** | QLoRA trên 4.690 mẫu | Tạo mô hình hàng thứ ba của ma trận |
| **3 — Đánh giá** | 137 câu × 6 ô = 822 lượt | Điền ma trận |

Phiên 1 là **cổng chặn** theo nghĩa chặt: nếu chẩn đoán cho thấy mô hình không định
vị được điều luật, kế hoạch sẽ chuyển sang mô hình 8B thay vì fine-tune. Kết quả
cổng quyết định toàn bộ hướng đi (xem Phần B §3.1).

### 1.3 Nguyên tắc nền: phát lại, không chạy lại

Toàn bộ khâu đánh giá dựa trên một phát hiện: các file `results_*.json` của mẻ
chạy tháng 7 đã lưu **nguyên văn chuỗi ngữ cảnh** mà Gemini nhận, byte-identical.

Vì thế quy trình đánh giá là:

```
results_*.json (tháng 7)  →  đọc chuỗi context đã lưu
                          →  ghép thành prompt bằng CHÍNH hàm của hệ đang chạy
                          →  đưa cho mô hình cục bộ (llama.cpp)
                          →  chấm bằng CHÍNH src/evaluation/metrics.py
```

Không khởi động Neo4j, không khởi động Qdrant, không gọi API. Nguyên tắc kiểm tra
tự thân: *"nếu thấy cần khởi động cơ sở dữ liệu là đã sai hướng."*

Hệ quả phương pháp — quan trọng hơn hệ quả chi phí: truy hồi không chỉ được "giữ
giống" mà được **đóng băng tuyệt đối**. Cả sáu ô nhận cùng một chuỗi ký tự đầu vào,
nên mọi chênh lệch chỉ có thể đến từ mô hình sinh. Đây là điều kiện làm cho thực
nghiệm **có hiệu lực nội tại** (xem Phần B §2.1).

**Hai vế lấy ngữ cảnh từ hai mẻ khác nhau — có chủ ý, và lý do phải nêu trong bài.**
Vế GraphRAG lấy mẻ **sau khi sửa** lỗi phân loại địa phương; vế Naive RAG giữ mẻ cũ.
Điều đó hợp lệ vì vế Naive RAG **không đi qua bộ lập kế hoạch truy vấn** — nơi chứa
lỗi đã sửa — nên nó không cần và không được phép chạy lại (chạy lại chỉ thêm nhiễu
của một mẻ mới). Kiểm chứng: bốn mẻ baseline đủ 137 câu có `context` trùng khít
137/137 với nhau. Truy hồi vẫn đóng băng ở cả sáu ô; điều đổi là **giá trị** của
ngữ cảnh phía GraphRAG, không phải cơ chế đông cứng nó. Chi tiết ở Phần B §2.1 và
`finetune/kaggle_ft06.py:110-136`.

⚠️**KIỂM** hai đường dẫn file nguồn và sha256 của chúng ở Phần A §6 — chúng là **giá
trị ghim thứ tám** của tuyên bố tái lập (Phần B §5.2).

---

## 2. Chọn mô hình sinh cục bộ

### 2.1 Tiêu chí

| Tiêu chí | Yêu cầu | Lý do |
|---|---|---|
| Mã nguồn mở, chạy được cục bộ | bắt buộc | mục đích là kiểm tính vững, không phụ thuộc API |
| Hỗ trợ tiếng Việt | bắt buộc | miền pháp luật Việt Nam |
| Cửa sổ ngữ cảnh ≥ 16K token | bắt buộc | system prompt ~3.936 token + ngữ cảnh GraphRAG tới ~8.774 token |
| Vừa một GPU tiêu dùng | bắt buộc | ngân sách |
| Đủ nhỏ để tinh chỉnh trong vài giờ | mong muốn | phạm vi khóa luận |

**Chọn:** Qwen3-4B-Instruct-2507.

### 2.2 Định dạng và lượng tử hoá

Suy luận qua **llama.cpp** với định dạng **GGUF**, lượng tử hoá **Q4_K_M**.

- GGUF gói cả trọng số **và chat template** vào một file — nên khuôn prompt đi kèm
  mô hình, không phụ thuộc môi trường. Điều này về sau trở thành một nhiễu cần
  loại trừ (Phần B §2.4).
- Q4_K_M đưa mô hình 4B về **~2,4 GB**, chạy được trên T4 16 GB và 4090 24 GB.
- llama.cpp cho **tính tất định theo seed** khi cùng bản dựng và cùng phần cứng —
  điều này được đo, không giả định, và trở thành cơ sở cho quyết định N=1
  (Phần B §2.5).

Hai công cụ llama.cpp khác nhau được dùng cho hai việc khác nhau, **cố ý**:

| Công cụ | Việc | Cần GPU |
|---|---|---|
| Bản dựng tĩnh CPU (`llama-quantize`) | **tạo** file GGUF từ trọng số bf16 | Không — lượng tử hoá là việc CPU |
| `llama-cpp-python` bản CUDA | **chạy suy luận, sinh số liệu** | Có |

### 2.3 Quy trình cổng — chẩn đoán bằng hai đại lượng tách rời

Phiên 1 chạy **15 câu** (chọn theo `finetune/data/gate_ids.json`) ở **bốn** cấu
hình: 0-shot và 2-shot, mỗi cái với `presence_penalty` ∈ {1.0, 0}.

Đo hai đại lượng **tách rời**:

- `soft_article_hit` — mô hình có **nhắc đúng** điều luật trong văn xuôi không?
- `format_ok_rate` — trích dẫn có **phân tích được** bằng bộ chấm không?

| Cấu hình | `format_ok` | F1 Khoản | NormR | `soft_article_hit` |
|---|---:|---:|---:|---:|
| 0-shot, pp=1.0 | 0,083 (1/12) | 0,200 | 0,200 | 1,000 |
| 0-shot, pp=0 | 0,167 (2/12) | 0,244 | 0,267 | 1,000 |
| 2-shot, pp=1.0 | 0,833 (10/12) | 0,531 | 0,633 | 1,000 |
| **2-shot, pp=0** | **0,833 (10/12)** | **0,600** | **0,700** | **1,000** |

**Kết luận cổng:** mô hình **định vị đúng** điều luật nhưng **không viết nổi cú
pháp trích dẫn**. Đây là loại lỗi fine-tune sửa được → **giữ 4B**, nhánh leo thang
8B không xảy ra, và mục tiêu fine-tune được định nghĩa lại thành *"dạy định dạng
đầu ra"* chứ không phải *"dạy kiến thức pháp luật"*.

Định nghĩa này chi phối mọi quyết định sau đó, kể cả việc chọn `lora_r` nhỏ.

**Chọn `presence_penalty` theo tiêu chí đăng ký trước** — xem Phần B §3.2.

---

## 3. Phương pháp tinh chỉnh: QLoRA

### 3.1 Vì sao QLoRA

| Phương án | Đánh giá |
|---|---|
| Huấn luyện toàn bộ tham số | Cần ~4 tham số × (trọng số + gradient + hai trạng thái Adam) → vượt xa 24 GB. Loại. |
| LoRA trên trọng số 16-bit | Trọng số gốc 4B ở bf16 ≈ 8 GB, cộng activation ở chuỗi 16K → sát trần. Rủi ro. |
| **QLoRA** (LoRA trên trọng số đã lượng tử 4-bit) | Trọng số gốc ≈ 2,5 GB, chỉ adapter được huấn luyện. **Chọn.** |

QLoRA hợp với tác vụ này vì mục tiêu là **định dạng đầu ra**, không phải kiến thức
mới. Cổng đã chứng minh mô hình *biết* điều luật (`soft_article_hit` = 1,000); cần
dạy nó *viết đúng khuôn*. Đó là thứ một adapter hạng thấp làm được.

### 3.2 Cấu hình

Bảng này **đã được đối chiếu** với `adapter_config.json` của `checkpoint-588` và với
log huấn luyện — không còn mục ⚠️KIỂM. Số dòng nguồn: Phần A §2.1, §2.3, §5.

| Nhóm | Tham số | Giá trị |
|---|---|---|
| Mô hình gốc | kho **thật đã nạp** | `unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit` — bản lượng tử-4-bit dựng sẵn. Lệnh truyền tên bản bf16 (`unsloth/Qwen3-4B-Instruct-2507`), thư viện **tự chuyển hướng**. Phải công bố chuỗi thật |
| Lượng tử hoá | 4-bit, nạp qua thư viện tăng tốc | `load_in_4bit = True` — chính cờ này kích hoạt việc chuyển hướng kho ở trên |
| LoRA | `r` | 16 |
| | `alpha` | 32 |
| | `dropout` / `bias` | 0.0 / `none` |
| | số layer được vá | **36** (36 QKV + 36 O + 36 MLP) |
| | số mô-đun đích mỗi layer | **7** (`q,k,v,o,gate,up,down`) |
| | tham số huấn luyện được | **33.030.144 / 4.055.498.240 = 0,81%** |
| Chuỗi | `max_seq_length` | **16.384** — ghim, không hạ |
| Tối ưu | learning rate | 2e-4 |
| | scheduler | cosine + warmup (`warmup_ratio` 0,03) |
| | epochs | 2 |
| | batch size mỗi thiết bị | 1 |
| | gradient accumulation | 16 (batch hiệu dụng 16) |
| | bước tối ưu hoá | **588** (294 mỗi epoch) |
| Bộ nhớ | `gradient_checkpointing` | bật |
| | `packing` | **tắt** |
| Kiểu số | bf16 | bật — bf16 **gốc** của phần cứng, yêu cầu sm ≥ 80 (xem §5.1) |
| Loss | `train_on_responses_only` | **bật** — che 98,5% token |

**Kiểm chéo số học đáng nêu trong bài.** Bảy mô-đun đích của Qwen3-4B cộng lại có
57.344 chiều vào+ra mỗi layer, nên số tham số adapter phải bằng
`36 × 57.344 × r`. Với `r = 16` phép nhân cho **33.030.144** — **trùng khít** con số
mà công cụ huấn luyện in ra. Đây là xác nhận thứ ba cho `r`, độc lập với cờ CLI và
với cấu hình adapter đã lưu.

Ba lựa chọn đáng giải thích trong bài:

**`r = 16` chứ không lớn hơn.** Vì tác vụ là học định dạng. Cổng cho
`soft_article_hit` = 1,000, tức năng lực nội dung đã có; adapter chỉ cần đủ sức
đổi cách trình bày. Hạng thấp cũng giảm rủi ro quên kiến thức nền.

**`packing = False`.** Ghép nhiều mẫu ngắn vào một chuỗi sẽ làm ranh giới prompt /
đáp án bị trộn, và cơ chế che prompt (dưới đây) mất chính xác. Đánh đổi: chậm hơn,
nhưng loss được tính đúng chỗ.

**`train_on_responses_only`.** Loss chỉ tính trên phần **đáp án**, phần prompt bị
che. Đây là lựa chọn cốt lõi: mỗi mẫu dài trung bình **7.530 token** (đo bằng
tokenizer thật lúc huấn luyện) nhưng đáp án chỉ khoảng 190 token. Nếu tính loss trên
cả prompt, tín hiệu huấn luyện sẽ bị gần 4.000 token system prompt lặp lại 4.690 lần
nhấn chìm — mô hình học tái tạo chỉ dẫn thay vì học trả lời.

Tỉ lệ che là **đại lượng cần kiểm mỗi lần chạy**: quá thấp nghĩa là ranh giới
prompt/đáp án bắt sai. **Giá trị thật đo được ở phiên 2: che 5.623 trên 5.707 token
= 98,5%** — đúng dải kỳ vọng, ranh giới bắt đúng.

### 3.3 Tập validation

Mục đích **không** phải chọn siêu tham số (chỉ chạy một lần) mà là **phát hiện quá
khớp giữa hai epoch**.

| Hạng mục | Giá trị |
|---|---|
| Nguồn | `finetune/data/val.jsonl`, 310 mẫu |
| Số mẫu dùng | 64 (xáo theo seed trước khi cắt) |
| Chiến lược | đánh giá cuối mỗi epoch — 2 lần, ở bước 294 và bước 588 |
| Cách che | dùng chung cơ chế `train_on_responses_only` |
| Độ dài mẫu val (tokenizer thật) | p50 6.542 · mean 7.286 · p95 10.956 · max 12.062 · vượt trần **0/64** |
| Kết quả | `eval_loss` **0,3129** (epoch 1) → **0,3082** (epoch 2) — cải thiện 1,5% |

Kết quả đó là bằng chứng **tác vụ bão hoà rất nhanh**: epoch thứ hai tiêu gần một
nửa tổng thời gian tính toán để đổi lấy 1,5%. Không có dấu hiệu quá khớp (eval_loss
vẫn giảm), nhưng cũng không có dấu hiệu còn dư địa. Đọc cùng Phần B §7.3.

Ba chi tiết ảnh hưởng tới tính hợp lệ:

- **Xáo trước khi cắt.** `val.jsonl` tách theo `doc_name`, nên 64 dòng đầu có thể
  rơi hết vào vài văn bản. Xáo theo seed giữ tính tất định mà vẫn phủ đều.
- **Che giống tập huấn luyện.** Nếu `eval_loss` tính trên cả prompt còn
  `train_loss` chỉ tính trên đáp án thì hai con số không so được với nhau.
- **Kiểm độ dài riêng cho tập val.** Mẫu val vượt trần cũng bị cắt đuôi âm thầm,
  làm `eval_loss` sai mà không báo lỗi.

---

## 4. Xử lý dữ liệu

### 4.1 Nguồn

| Hạng mục | Giá trị |
|---|---|
| Bộ dữ liệu hỏi–đáp pháp luật tiếng Việt | `thangvip/vietnamese-legal-qa` (HuggingFace) — quy mô gốc 9.715 dòng / 29.145 cặp hỏi–đáp / 141 văn bản. **Giấy phép: KHÔNG CÓ TRONG REPO** (Phần A §3.1) |
| Kho văn bản luật | kho ngữ liệu của chính hệ thống (đất đai, hộ tịch, nuôi con nuôi) |
| Tổng mẫu sinh ra | 5.000 (train 4.690 / val 310) |
| Seed | 42 |

**Điểm quan trọng:** dữ liệu huấn luyện **không** lấy trực tiếp từ bộ hỏi–đáp
ngoài. Bộ ngoài cung cấp **cặp câu hỏi–điều luật**; ngữ cảnh và đáp án được **dựng
lại** bằng chính kho văn bản và chính hàm dựng prompt của hệ thống. Nếu không làm
vậy, mô hình sẽ học một khuôn đầu vào khác khuôn nó gặp lúc suy luận.

### 4.2 Đường dựng một mẫu

```
(1) Lấy cặp câu hỏi – điều luật gold từ bộ dữ liệu ngoài
     ↓
(2) Chọn khuôn ngữ cảnh: GraphRAG hoặc baseline (50/50)
     ↓
(3) Dựng chuỗi ngữ cảnh từ kho văn bản, ĐÚNG khuôn của hệ đang chạy
     — kể cả header [Tier N | Hiệu lực: ...] và mã văn bản
     ↓
(4) Dựng đáp án: văn xuôi tiếng Việt + khối trích dẫn ở CUỐI,
     theo cú pháp đã chốt ở hợp đồng API
     ↓
(5) Ghép thành messages bằng CHÍNH build_messages của hệ thống
     — cùng system prompt, cùng cấu trúc vai
     ↓
(6) assert: mọi trích dẫn phân tích ngược được; mã văn bản trong
     trích dẫn CÓ MẶT trong ngữ cảnh của chính mẫu đó
     ↓
(7) Đo độ dài bằng tokenizer thật; loại mẫu vượt 16.384
```

Bước (5) là ràng buộc quan trọng nhất về mặt phương pháp: **tái dùng, không sao
chép**. Hệ quả là dữ liệu huấn luyện là 0-shot (vì `build_messages` không kèm
few-shot), và điều đó **buộc** hàng đã tinh chỉnh phải được đánh giá ở 0-shot
(Phần B §2.2).

Bước (6) là cơ chế chống bịa: nếu mã văn bản trong trích dẫn không có trong ngữ
cảnh của chính mẫu đó, ta đang dạy mô hình **nhớ mã từ trí nhớ** thay vì **chép mã
từ ngữ cảnh**.

### 4.3 Mẫu từ chối

Hệ thống phải biết từ chối khi không đủ căn cứ. Hai loại được dựng, mỗi loại có
cách xây riêng:

| Loại | Cách dựng | Điều kiện học được |
|---|---|---|
| `refusal_no_basis` | đóng gói 4–6 điều **cùng văn bản** nhưng **loại điều gold ra** | ngữ cảnh có tài liệu liên quan nhưng không đủ căn cứ |
| `refusal_out_of_scope` | câu hỏi thuộc lĩnh vực ngoài kho ngữ liệu, ngữ cảnh đóng gói từ văn bản **khác lĩnh vực** | tái tạo đúng cấu hình các câu bẫy trong bộ đánh giá |

Đáp án của mẫu từ chối là **chuỗi hằng số nguyên văn** khớp chuỗi mà system prompt
yêu cầu — nếu lệch một ký tự thì bộ chấm không nhận.

**Tỉ lệ:** 9,0% (450 trên 5.000), giữ 70/30 nghiêng về `no_basis` — lập luận và
quá trình đi từ 20% xuống 9% ở Phần B §4.1 và §4.2.

### 4.4 Tách train / val

| Hạng mục | Giá trị |
|---|---|
| train | 4.690 |
| val | 310 |
| Tiêu chí tách | theo **`doc_name`** |

Tách theo văn bản, **không** tách ngẫu nhiên theo dòng. Lý do: nhiều mẫu cùng dẫn
một điều luật; tách ngẫu nhiên sẽ để cùng một điều luật xuất hiện ở cả hai tập, và
`eval_loss` sẽ đo khả năng nhớ chứ không đo khả năng khái quát.

Đây cũng là lý do khi cần hạ tỉ lệ mẫu từ chối, ta **sinh lại toàn bộ** chứ không
lọc bớt dòng: lọc dòng phá phân tách này (Phần B §4.1).

### 4.5 Bốn lớp kiểm

| Lớp | Kiểm gì | Bắt được gì |
|---|---|---|
| 1. Cú pháp | mọi trích dẫn phân tích ngược bằng `parse_citations` | dạy sai cú pháp |
| 2. Xuất xứ | mã văn bản có mặt trong ngữ cảnh của chính mẫu | dạy mô hình bịa từ trí nhớ |
| 3. Độ dài | không mẫu nào vượt `max_seq_length` | cắt đuôi mất trích dẫn |
| 4. **Đọc tay 20 mẫu** | nội dung có ý nghĩa, mẫu từ chối có thật sự khó | thứ ba lớp trên không bắt được |

Lớp 4 không tự động hoá được và đã phát hiện một vấn đề thật (Phần B §4.3, §4.2).

---

## 5. Triển khai huấn luyện

### 5.1 Môi trường

| Hạng mục | Giá trị |
|---|---|
| GPU | **NVIDIA GeForce RTX 4090**, 23,516 GB khả dụng, **sm89**, 1 card, Linux |
| Cổng chặn phần cứng | sm ≥ 80 — **chỉ vì bf16 gốc** (xem dưới) |
| Kiểu số thực tế | `bf16 gốc = True` |
| Attention backend thực tế | **Xformers 0.0.35 · FlashAttention-2 = False** |
| Bộ thư viện | Torch 2.10.0+cu128 · CUDA Toolkit 12.8 · Triton 3.6.0 · Transformers 5.5.0 · Unsloth 2026.7.5 |
| Thời gian chặng huấn luyện | **19.480 giây = 5 giờ 24 phút 40 giây** |
| Chi phí | **KHÔNG CÓ TRONG REPO** — không file nào ghi giá thuê |

**Ràng buộc sm ≥ 80 là ràng buộc phương pháp, không phải sở thích — và lý do là
bf16, chỉ bf16.** Kiến trúc cũ hơn không có bf16 **gốc**; huấn luyện ở fp16 với chuỗi
16K token có rủi ro tràn số trong tích luỹ gradient. Với chuỗi dài như ở đây thì bf16
mới là thứ quan trọng, và log xác nhận nó đã bật (`bf16 gốc = True`,
`finetune/logs/ft04-5k-2ep-20260729-2122.log:39`; `Bfloat16 = TRUE` ở `:43`).

> **Đính chính — KHÔNG được viện FlashAttention-2 làm lý do cho ràng buộc này.** Cùng
> dòng log `:43` ghi `FA [Xformers = 0.0.35. FA2 = False]`: lần chạy thật **không dùng
> FlashAttention-2**, nó dùng Xformers. Nếu bài viết nói ràng buộc sm ≥ 80 là *"bắt
> buộc cho bf16 **và FlashAttention-2**"* thì vế sau sai với chính lần chạy đã sinh ra
> số liệu. Phát biểu đúng: ràng buộc đến từ **bf16 gốc**; FA2 không tham gia.

Đây cũng là lý do phải thuê máy ngoài thay vì dùng môi trường miễn phí (T4 là sm75).

### 5.2 Bảy chặng

| Chặng | Việc | Cổng chặn |
|---|---|---|
| 0 preflight | kiểm GPU, sm, VRAM, đĩa, Python | `exit` nếu sm < 80 |
| 1 install | cài theo **bộ phiên bản ghim** | `assert torch.cuda.is_available()` và **không** phải bản CPU |
| 2 data | tải `train.jsonl` + `val.jsonl` | `sha256sum -c` |
| 3 train | QLoRA | `audit_lengths` dừng nếu có mẫu vượt trần |
| 4 merge | gộp adapter vào trọng số bf16 | |
| 5 gguf | convert bf16 → GGUF f16 → lượng tử Q4_K_M | in sha256 của file kết quả |
| 6 publish | đẩy artifact lên kho lưu trữ | |

Ba điểm phương pháp:

**Bộ phiên bản ghim, không dùng `-U`.** Toàn bộ thư viện cài với tệp ràng buộc
phiên bản. Nếu để trình quản lý gói tự chọn bản mới nhất, phiên 2 sẽ chạy trên một
bộ khác phiên 1 và 3 — và bộ ghim công bố trong khóa luận sẽ sai.

**Đẩy checkpoint lên kho lưu trữ định kỳ.** Cho phép chạy tiếp nếu phiên bị ngắt,
và giữ được adapter của epoch 1 để so với epoch 2.

**In sha256 của mọi artifact.** Bảy giá trị ghim — xem Phần B §5.2.

### 5.3 Mini-run trước khi chạy thật

Chạy thử **giữ nguyên `max_seq_length` = 16.384**, chỉ giới hạn số mẫu và số bước,
và **chọn 8 mẫu dài nhất** thay vì 8 mẫu đầu.

Lý do phương pháp: điều cần kiểm là **đỉnh bộ nhớ**, mà đỉnh đạt được ở mẫu dài
nhất và đạt ngay ở lô đầu tiên. Hạ độ dài chuỗi cho mini-run sẽ làm nó **không
kiểm được đúng thứ nó tồn tại để kiểm**.

Bốn cổng của mini-run: bf16 khả dụng · `over_limit` = 0 · tỉ lệ che trong dải kỳ
vọng · không tràn bộ nhớ.

---

## 6. Triển khai đánh giá

### 6.1 Sáu ô

| Ô | Mô hình sinh | `n_shot` | Nguồn ngữ cảnh | Card | F1 cấp Khoản |
|---:|---|---:|---|---:|---:|
| 1 | đã tinh chỉnh | 0 | GraphRAG | 0 | 0,402 |
| 2 | đã tinh chỉnh | 0 | baseline | 0 | 0,301 |
| 3 | gốc | 2 | GraphRAG | 0 | 0,511 |
| 4 | gốc | 2 | baseline | 1 | 0,239 |
| 5 | gốc | 0 | GraphRAG | 1 | 0,131 |
| 6 | gốc | 0 | baseline | 1 | 0,154 |

**822 lượt sinh** (137 × 6), **N = 1** cho hàng cục bộ. Tổng thời gian sáu ô
**11.313,56 giây ≈ 3 giờ 8 phút** (chạy hai luồng song song).

Hàng gốc chạy **cả hai** biến thể — quyết định này đã cứu kết quả khỏi bị đọc sai
(Phần B §2.3). Hàng đã tinh chỉnh chỉ chạy 0-shot (Phần B §2.2). Cơ sở chọn N = 1
ở Phần B §2.5.

Hàng Gemini **không** N = 1 vì mô hình đó có yếu tố ngẫu nhiên không tắt được: nó
báo trung bình ± độ lệch chuẩn qua **3 mẻ** phía GraphRAG và **4 mẻ** phía Naive RAG
(F1 cấp Khoản **0,617 ± 0,001** so với **0,436 ± 0,008**). Số mẻ khác nhau giữa hai vế
là một điểm cần xác nhận trước khi vào khoá luận — Phần A §6.1.

**Tám tham số sinh giống hệt nhau ở cả sáu ô.** Đây là điều kiện để cột Δ có nghĩa,
và là lý do một câu chạm trần token **không** được chạy lại riêng với trần cao hơn.

⚠️**KIỂM mọi con số trong bảng trên với Phần A §6.1** trước khi đưa vào bài.

### 6.2 Hai cổng chặn trước khi sinh lượt nào

| Cổng | Kiểm gì | Chặn điều gì |
|---|---|---|
| **A** | chat template nhúng trong hai file GGUF có trùng khít không (độ dài + sha256 + diff) | hai hàng ma trận nhận prompt khác nhau → Δ đo lẫn khác biệt template |
| **B** | xuất prompt đã render ra và **đọc bằng mắt** | hỏng âm thầm: system prompt bị cắt, vai few-shot sai, ví dụ mẫu dạy sai định dạng |

Cổng A trùng khít; cổng B đạt năm mục. Chi tiết và lý do dấu "đạt" tự động chưa đủ:
Phần B §2.4 và §6.

**Cổng B phải chạy LẠI khi nguồn ngữ cảnh đổi, không được tái dùng bản dump cũ.**
Prompt thực sự đi vào mô hình đổi ở 17 câu, nên bản dump của lượt trước không nói gì
về prompt của lượt này. File dump được ghi ra **tên mới** để không đè bản cũ — bản cũ
là bằng chứng "đã đọc bằng mắt" của lượt trước và phải giữ. Cổng A thì không cần chạy
lại vì nó kiểm hai file GGUF, mà hai file đó không đổi (vẫn đúng sha256 đã ghim); chạy
lại chỉ để xác nhận.

### 6.3 Ghim phần cứng

Môi trường đánh giá cấp **hai** GPU T4. Với cấu hình đẩy toàn bộ layer lên GPU,
llama.cpp **tự chia layer qua cả hai card** — không nhanh hơn (model chỉ 2,4 GB)
nhưng đổi thứ tự phép rút gọn.

Rủi ro không phải "sai" mà là **không nhất quán giữa các ô**. Cách xử: **ghim tường
minh mỗi ô vào đúng một card**, qua biến môi trường của từng tiến trình con. Không
ô nào chia layer qua hai card; không hai ô nào chạy cùng lúc trên cùng một card.

Đây là **giá trị ghim thứ bảy** của tuyên bố tái lập (Phần B §5.2).

Bản ghi trạng thái lần chạy (`ft06b_run_status.json`) là nguồn đúng cho giá trị này —
**không** dùng `ft06b_gpu_info.json`, vì file đó ghi cấu hình **dự kiến** ở chặng
chuẩn bị chứ không phải cấu hình đã chạy (Phần A §4.6).

### 6.4 Thang đo

Tất cả do `src/evaluation/metrics.py` tính — **tái dùng, không viết lại**.

| Thang đo | Đo gì | Lưu ý khi đọc |
|---|---|---|
| **F1 cấp Khoản** | trích dẫn đúng tới cấp Khoản | thang đo chính của mục 4.7 |
| F1 cấp Điều | đúng tới cấp Điều | nới lỏng hơn |
| Norm Recall | độ phủ chuẩn hoá | |
| Từ chối đúng (x/14) | câu bẫy được từ chối đúng | **mẫu số hiệu dụng khác nhau giữa hai cột** — Phần B §7.1 |
| `format_ok_rate` | tỉ lệ trả lời phân tích được | **đọc trước khi tin F1** |
| `soft_article_hit` | có nhắc đúng điều luật trong văn xuôi | tách năng lực nội dung khỏi năng lực định dạng |
| `n_hit_token_cap` | số câu chạm trần sinh | > 0 thì F1 của ô đó thấp vì lý do kỹ thuật |
| `latency_mean_s` | độ trễ | **không so được** với Bảng 4.5 — Phần B §7.2 |

**`format_ok_rate` phải đọc trước F1.** Ô 5 có `format_ok` = **0,065**, nghĩa là chỉ
**8 trên 123** câu phân tích được, và F1 của ô đó là so hai con số gần bằng không.
Đó là lý do Δ âm ở hàng gốc 0-shot không phải phản chứng (Phần B §7.4).

---

## 7. Chuỗi tái lập đầy đủ

Để dựng lại kết quả mục 4.7 từ đầu, cần đúng tám giá trị ghim (Phần B §5.2) và
chuỗi bước sau:

```
[1] clone repo tại commit đã ghim
[2] tải GGUF mô hình gốc tại revision đã ghim, đối chiếu sha256
[3] tải train/val.jsonl, đối chiếu sha256
        (hoặc sinh lại: build_dataset.py, seed 42, FRAC_REFUSAL 0.09)
[4] cài thư viện theo bộ phiên bản ghim
[5] huấn luyện QLoRA — GPU sm ≥ 80, nạp ĐÚNG kho lượng tử-4-bit đã công bố
        (KHÔNG phải kho bf16 mà cờ --base-model ghi)
[6] merge → convert → lượng tử Q4_K_M bằng bản dựng llama.cpp đã ghim
        → đối chiếu sha256 với giá trị công bố
[7] lấy hai file nguồn ngữ cảnh, đối chiếu sha256 của cả hai
[8] chạy 6 ô bằng replay.py, mỗi ô ghim một GPU, tám tham số sinh như đã ghim
[9] chấm bằng metrics.py, dựng ma trận
```

Bước [3] có hai đường vì bộ dữ liệu vừa được ghim bằng sha256 vừa **sinh lại được**
từ seed — hai đường phải cho cùng kết quả, và đó là một phép kiểm tái lập bổ sung.

Bước [5] có một cái bẫy đã gặp thật: công cụ huấn luyện **tự chuyển hướng** tên kho
mô hình gốc sang bản lượng tử-4-bit của chính nó, không báo gì. Chạy đúng lệnh đã
công bố mà không biết điều này thì nạp một bộ trọng số khác. Xem Phần B §2.4.

Bước [7] tồn tại vì hai vế của ma trận lấy ngữ cảnh từ **hai mẻ khác nhau, có chủ ý**
(§1.3). Không đối chiếu sha256 ở đây thì không có cách nào biết mình đang phát lại
đúng ngữ cảnh nào.

Điều **không** tái lập được: bốn con số của phiên 1 do một bản vá nằm ngoài git
sinh ra, đã sửa nhưng cần khai báo (Phần B §5.1); và hai hiện vật định lượng của
phiên huấn luyện phải khôi phục từ log + checkpoint vì bước lưu trữ đã hỏng âm thầm
(Phần B §5.4).
