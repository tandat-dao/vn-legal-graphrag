# TASK-FT-01 — Ngân sách token & khôi phục `response_mode`

**Ngày:** 2026-07-28 · **Trạng thái:** ⚠️ GATE — đã qua
**Phạm vi:** $0, không GPU, không gọi API mô hình. Chỉ tải file tokenizer từ HuggingFace.
Không sửa `src/`, chỉ đọc `data/evaluation/`.

**Sinh ra bởi:**
- [`finetune/measure_token_budget.py`](../measure_token_budget.py) → [`token_budget.json`](token_budget.json)
- [`finetune/recover_response_mode.py`](../recover_response_mode.py) → [`../data/mode_map.json`](../data/mode_map.json)

```bash
python -m finetune.recover_response_mode
python -m finetune.measure_token_budget --dump-raw
```

Cần thêm `transformers` (đã có sẵn 4.57.1) ngoài `anthropic` / `neo4j` / `qdrant-client`
mà TASK-FT-00 đã cài. Không cần torch, không cần weights — chỉ tải file tokenizer.

---

## 0. Kết luận một dòng

> **Cần cửa sổ ngữ cảnh ≥ 16 384 token, do đó mô hình phải thuộc lớp 7–8B instruct
> có cửa sổ gốc ≥ 32k VÀ tokenizer hiệu quả với tiếng Việt (BPE ≥ 128k hoặc
> SentencePiece mở rộng tiếng Việt).** 8k bị loại dứt khoát: 84/127 câu GraphRAG
> vượt 8 192 token ngay ở tokenizer tốt nhất trong nhóm khả thi.

Hai ứng viên đạt yêu cầu: **Qwen2.5-7B-Instruct** và **Llama-3.1-8B-Instruct**.
Hai ứng viên bị loại, mỗi cái vì một lý do khác nhau — chi tiết §2.5.

---

## 1. Phương pháp

### 1.1 Đo TỔNG thật, không đo riêng context

Theo §9.2 kế hoạch. Chuỗi đưa vào tokenizer dựng bằng chính
`src.retrieval.context_assembler.build_messages(question, context, mode)` — tức là
**đúng chuỗi mà mô hình sinh đã nhận** ở mẻ 10/07, không phải bản dựng lại gần đúng:

```
tổng = system_prompt(mode) + "CONTEXT:\n" + context + "\n\nCÂU HỎI: " + question + "\n\nTRẢ LỜI:"
```

`mode` lấy từ `mode_map.json` (§3), **không** giả định tất cả `general`.

Hai cách tính, báo cáo cả hai:

| Cách | Nghĩa |
|---|---|
| `raw` | `len(tok(system)) + len(tok(user))` — ngân sách nội dung thuần |
| `chat` | `len(tok.apply_chat_template([system, user], add_generation_prompt=True))` |

Chênh lệch `chat − raw` là token đánh dấu vai trò. Đo được **bất biến theo độ dài
nội dung** (script `assert` lại trên câu cuối của mỗi mẻ, cả 4 tokenizer đều pass):

| Tokenizer | overhead |
|---|---:|
| Qwen2.5 | 13 |
| Llama-3.1 | 15 |
| Phi-3.5 | 5 |
| VinaLlama | 18 |

Nhỏ tới mức không ảnh hưởng quyết định. Các bảng dưới dùng `chat`.

### 1.2 Tập câu được đo

Chỉ đo **127/137** câu GraphRAG thực sự đi qua mô hình sinh. Loại 10 câu
`top_k_count == 0` (V106–V113, V115, V116) vì theo §9.1 chúng được **sao chép hằng
số**, không tốn token nào. Baseline đo đủ **137/137** (không câu nào rỗng context).

### 1.3 Ứng viên

Kế hoạch không nêu tên mô hình; việc **chốt mô hình thuộc TASK-FT-03**. Ở đây chỉ
cần bracket khoảng token nên chọn 4 tokenizer ungated, phủ hết các họ tokenizer
thực tế sẽ gặp:

| Nhãn | Repo | Tokenizer | Cửa sổ gốc |
|---|---|---|---:|
| Qwen2.5-7B-Instruct | `Qwen/Qwen2.5-7B-Instruct` | BPE 151 643 | 32 768 |
| Llama-3.1-8B-Instruct | `NousResearch/Meta-Llama-3.1-8B-Instruct` | BPE 128 000 | 131 072 |
| Phi-3.5-mini-instruct | `microsoft/Phi-3.5-mini-instruct` | SentencePiece 32 000 | 131 072 |
| VinaLlama-7B-chat | `vilm/vinallama-7b-chat` | SP 46 303, mở rộng tiếng Việt | **4 096** |

*Cửa sổ gốc đọc từ `max_position_embeddings` trong `config.json` của từng repo.*

Đã thử và **bỏ** vì repo gated (403, cần đăng nhập HF): `Viet-Mistral/Vistral-7B-Chat`.
`SeaLLMs/SeaLLMs-v3-7B-Chat` dùng **cùng tokenizer với Qwen2.5** (vocab 151 643) →
số đo trùng cột Qwen, không thêm thông tin.

---

## 2. Phần A — Ngân sách token

### 2.1 Bảng chính: tổng prompt (token, cách `chat`)

**GraphRAG — 127 câu**

| Mô hình | mean | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-7B | 8 610 | 8 170 | 11 087 | 11 596 | **12 011** |
| Llama-3.1-8B | 8 074 | 7 682 | 10 256 | 10 624 | **10 958** |
| Phi-3.5-mini | 17 583 | 16 684 | 22 970 | 23 418 | **23 783** |
| VinaLlama-7B | 7 784 | 7 435 | 9 792 | 10 106 | **10 380** |

**Baseline (Naive RAG) — 137 câu**

| Mô hình | mean | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|
| Qwen2.5-7B | 5 852 | 5 797 | 6 139 | 6 220 | 6 432 |
| Llama-3.1-8B | 5 626 | 5 589 | 5 853 | 5 910 | 6 004 |
| Phi-3.5-mini | 12 014 | 11 991 | 12 267 | 12 301 | 12 345 |
| VinaLlama-7B | 5 678 | 5 643 | 5 834 | 5 856 | 5 954 |

Baseline gọn hơn nhiều và **gần như không có đuôi** (p50 ≈ max) vì chunk cố định
512 ký tự × top-k cố định. GraphRAG mới là ràng buộc quyết định.

### 2.2 Bóc tách thành phần (Qwen2.5, GraphRAG)

| Thành phần | mean | p50 | p95 | max |
|---|---:|---:|---:|---:|
| system_prompt | 3 946 | 3 936 | 4 034 | 4 034 |
| context | 4 602 | 4 188 | 7 601 | 8 028 |
| phần còn lại (khung + câu hỏi) | 49 | | | 89 |

`system_prompt` chỉ nhận đúng **hai giá trị**: **3 936** token (mode `general`) và
**4 034** token (mode `irac`) — khớp với việc chỉ có 2 khối mode.

> ⚠️ **System prompt chiếm 46% ngân sách ở câu trung vị.** Đây là hằng số, trả cho
> mọi câu. Với 127 + 137 lượt phát lại × 2 mô hình, riêng system prompt là ~4M token.

### 2.3 Sửa lại con số cũ trong `CLAUDE.md`

| Nguồn | Giá trị | Trạng thái |
|---|---:|---|
| Ghi chú D-15 (`CLAUDE.md`) | ~2 117 token | **SAI — bỏ** |
| Đo thật (Qwen2.5) | **3 936 / 4 034** | dùng cái này |
| Đo thật (Llama-3.1) | 3 866 / 3 951 | |
| Đo thật (Phi-3.5) | 7 962 / 8 113 | |

Chênh **≈ 1,9 lần**. Con số D-15 là token Anthropic của một phiên bản prompt cũ hơn;
prompt hiện tại dài 11 264 ký tự (`general`).

Đồng thời, hằng số `CHARS_PER_TOKEN = 3.5` trong
[context_assembler.py:31](../../src/retrieval/context_assembler.py#L31) **đánh giá thấp**
số token thật với tokenizer hiện đại:

| Tokenizer | ký tự/token thật (context GraphRAG) |
|---|---:|
| VinaLlama (SP mở rộng VN) | 3.54 |
| Llama-3.1 | 3.19 |
| Qwen2.5 | **2.87** |
| Phi-3.5 | **1.39** |

Hệ quả: `assemble_context(max_tokens=6000)` thực chất cắt ở **~8 028 token Qwen**,
không phải 6 000. Không phải lỗi cần sửa (ngưỡng chỉ để chặn tràn), nhưng FT-05
**không được** dùng 3.5 để suy ngược `max_seq_length`.

### 2.4 Số câu KHÔNG vừa cửa sổ W (đã tính cả phần sinh ra)

Đếm trên `prompt + answer thực tế`, tức yêu cầu tối thiểu để phát lại trọn vẹn.

**GraphRAG (n = 127)**

| Mô hình | > 8 192 | > 12 288 | > 16 384 | > 32 768 |
|---|---:|---:|---:|---:|
| Qwen2.5-7B | **84** | 1 | 0 | 0 |
| Llama-3.1-8B | 54 | 0 | 0 | 0 |
| Phi-3.5-mini | 127 | 126 | 89 | 0 |
| VinaLlama-7B | 42 | 0 | 0 | 0 |

**Baseline (n = 137)**

| Mô hình | > 8 192 | > 12 288 | > 16 384 |
|---|---:|---:|---:|
| Qwen2.5 / Llama-3.1 / VinaLlama | 0 | 0 | 0 |
| Phi-3.5-mini | 137 | 102 | 0 |

**Đây là bằng chứng loại 8k:** với Qwen2.5, **66% câu GraphRAG** không vừa cửa sổ 8k.
Cắt bớt để vừa sẽ thay đổi chính cái ta đang đo (ngữ cảnh) → phá nguyên tắc §4.

### 2.5 Cửa sổ tối thiểu và phán quyết từng ứng viên

`cửa sổ tối thiểu = max(prompt) + max(answer)` trên tập GraphRAG:

| Mô hình | max prompt | max answer | **cần** | cửa sổ gốc | Phán quyết |
|---|---:|---:|---:|---:|---|
| Qwen2.5-7B | 12 011 | 1 313 | **13 324** | 32 768 | ✅ **đạt** |
| Llama-3.1-8B | 10 958 | 1 177 | **12 135** | 131 072 | ✅ **đạt** |
| Phi-3.5-mini | 23 783 | 2 709 | **26 492** | 131 072 | ⚠️ vừa cửa sổ, **loại vì chi phí** |
| VinaLlama-7B | 10 380 | 1 064 | **11 444** | **4 096** | ❌ **loại — cửa sổ không đủ** |

Hai ca loại minh hoạ hai ràng buộc độc lập, không thể suy ra nhau:

- **VinaLlama** có tokenizer **hiệu quả nhất** cho tiếng Việt (3.54 ký tự/token,
  context p50 chỉ 3 404 token) nhưng nền Llama-2 chỉ **4 096** vị trí → không chứa
  nổi cả system prompt lẫn context. *Tokenizer tốt không cứu được cửa sổ ngắn.*
- **Phi-3.5** có cửa sổ 128k nhưng SentencePiece 32k vocab băm tiếng Việt ra
  **1.39 ký tự/token** → tốn **gấp ~2 lần** token cho cùng nội dung. Vẫn chạy được,
  nhưng huấn luyện QLoRA ở `max_seq_length` ~24k trên T4 16GB là không khả thi.
  *Cửa sổ dài không cứu được tokenizer kém.*

### 2.6 Câu trả lời của Gemini ngắn hơn nhiều so với cấu hình

| Mô hình (tokenizer) | mean | p50 | p95 | max |
|---|---:|---:|---:|---:|
| Qwen2.5 | 328 | 257 | 778 | 1 313 |
| Llama-3.1 | 292 | 220 | 696 | 1 177 |
| Phi-3.5 | 664 | 500 | 1 645 | 2 709 |
| VinaLlama | 266 | 199 | 648 | 1 064 |

`MAX_ANSWER_TOKENS = 3000` ([answer_generator.py:76](../../src/retrieval/answer_generator.py#L76))
chưa bao giờ bị chạm tới. Đặt `max_new_tokens` ~1 536 cho mô hình cục bộ là dư —
nhưng đó là quyết định của FT-02, ghi ở đây làm dữ kiện.

### 2.7 Kết luận phần A

1. **`max_seq_length` cho FT-05 = 16 384.** Bao trọn 127/127 câu GraphRAG kèm phần
   sinh ra ở cả Qwen2.5 lẫn Llama-3.1, với biên an toàn cho dữ liệu huấn luyện tổng
   hợp của FT-04. **Không hardcode 8192** (kế hoạch §TASK-FT-05 đã cảnh báo đúng);
   cũng không cần 32k.
2. **Độ dài mục tiêu cho mẫu huấn luyện FT-04** (phần context, token Qwen2.5):
   khuôn GraphRAG p50 ≈ **4 200**, p95 ≈ **7 600**, max ≈ **8 000**;
   khuôn baseline p50 ≈ **1 800**, max ≈ **2 450**. Quy ra ký tự: ~2.9 ký tự/token
   cho khuôn GraphRAG.
3. ⚠️ **Rủi ro chưa kiểm chứng cho FT-05:** T4 là kiến trúc `sm75`, **không chạy được
   FlashAttention-2** (đòi `sm80`+). QLoRA 7B ở `max_seq_length=16384` trên T4 16GB
   chỉ với SDPA + gradient checkpointing là **rất sát trần bộ nhớ**. Chưa đo, không
   thể khẳng định từ dữ liệu ở đây. Nêu ra để FT-05 kiểm trước khi tốn 30 giờ Kaggle.

---

## 3. Phần B — Khôi phục `response_mode`

### 3.1 Hai đường khác nhau cho hai hệ thống

Kế hoạch §TASK-FT-01B giả định phải suy bằng regex cho cả hai. Đọc code thì
**baseline không cần suy**:

| Hệ | Cơ chế | Dòng | Kết quả |
|---|---|---|---|
| baseline | `resolved_mode = "general" if response_mode == "auto" else ...` | [run_evaluation.py:93](../../src/evaluation/run_evaluation.py#L93) | **general cho cả 137, tất định** |
| graphrag | truyền `None` → planner quyết | [run_evaluation.py:62](../../src/evaluation/run_evaluation.py#L62) → [pipeline.py:179](../../src/pipeline.py#L179) | phải suy từ `answer` |

Nghĩa là **chỉ một nửa ma trận cần khôi phục**. Cột baseline là giá trị chắc chắn.

Đã kiểm: **không có** `data/evaluation/.planner_cache/` lẫn `.llm_cache/` trên máy →
không tồn tại nguồn ground-truth nào tốt hơn.

### 3.2 Tiêu chí suy luận và bằng chứng

Khối prompt `irac` ([context_assembler.py:264-280](../../src/retrieval/context_assembler.py#L264-L280))
ép đúng 4 heading H3: *Vấn đề / Căn cứ pháp lý / Phân tích / Kết luận*.
Regex nới lỏng có chủ ý (H2–H4, không phân biệt hoa-thường, khoảng trắng tự do) để
**không bỏ sót** biến thể.

**Phân bố số heading khớp — hoàn toàn lưỡng cực:**

| Số heading | GraphRAG | Baseline |
|---:|---:|---:|
| 0 | 124 | 137 |
| 1–3 | **0** | **0** |
| 4 | **13** | 0 |

Không có ca biên nào để phải phân xử. Ngưỡng 4/4 không nhạy cảm.

**13 câu `irac`:** V005, V031, V051, V071, V125, V126, V127, V129, V131, V132, V136,
V141, V147 → **13/137 = 9.5%**. Xác nhận đúng con số thô ghi ở `api_contract.md` §5.3.

### 3.3 Đã tìm thêm dấu hiệu khác, theo yêu cầu §9.3

Quét 124 câu GraphRAG nhóm `general` bằng các dấu hiệu thay thế:

| Dấu hiệu | Số câu bắt được trong nhóm `general` |
|---|---:|
| **bất kỳ** heading markdown (`##`…`######`) | **0** |
| `**Vấn đề` / `**Kết luận` / `**Căn cứ pháp lý` in đậm | 0 |
| `Kết luận:` đầu dòng | 0 |
| "cần thêm thông tin" / "để tư vấn cụ thể" | 0 |

Kết quả mạnh hơn mong đợi: **124 câu general không chứa một heading markdown nào**.
Không tồn tại dạng `irac` "suy biến" (bỏ heading, giữ cấu trúc) để có thể bỏ sót.

**Phép thử âm tính.** Chạy đúng bộ regex đó lên 137 answer **baseline** — đã biết
chắc 100% là `general` theo code — cho **0 false positive**. Regex không bắt nhầm.

**Một dấu hiệu đã bị loại sau khi thử.** Cụm "cần thêm thông tin / để tư vấn cụ thể"
xuất hiện ở 2 câu **baseline** (V003, V137) tức trong output mode `general` — vì khối
`general` ([context_assembler.py:261](../../src/retrieval/context_assembler.py#L261))
cũng bảo gợi ý người dùng cung cấp địa phương. Cụm này **không phân biệt được mode**,
đã loại khỏi tiêu chí, chỉ giữ làm kiểm tra chéo.

### 3.4 Rủi ro còn lại — false negative, không đo trực tiếp được

Khối `irac` có **lối thoát**: *"Nếu câu hỏi KHÔNG cung cấp đủ tình tiết để phân tích:
KHÔNG bịa tình tiết — chuyển sang trình bày quy định chung"*
([context_assembler.py:280](../../src/retrieval/context_assembler.py#L280)).
Câu đi lối này sẽ là mode `irac` mà **không có heading** → bị xếp nhầm thành `general`.

Ba lý do để tin rủi ro này nhỏ, **là lập luận chứ không phải phép đo**:

1. Lối thoát chỉ kích hoạt khi câu hỏi **thiếu tình tiết**; nhưng planner chỉ chọn
   `irac` khi câu hỏi **có tình tiết cụ thể**
   ([query_planner.py:104-107](../../src/retrieval/query_planner.py#L104-L107)) —
   hai điều kiện gần như loại trừ nhau.
2. Không câu general nào chứa ngôn ngữ đặc trưng của lối thoát (§3.3).
3. Không có dạng trung gian nào trong dữ liệu: 0 câu có 1–3 heading, 0 câu có heading
   markdown bất kỳ.

Giới hạn §8.3 của kế hoạch ("`response_mode` khôi phục bằng regex, không phải giá trị
gốc") **vẫn phải giữ nguyên** trong mục 4.7.

### 3.5 Ghi chú về 10 câu hằng số

Trong `mode_map.json`, V106–V113/V115/V116 mang giá trị `"general"`. Đó là **giá trị
vô nghĩa**: answer của chúng là hằng số cứng của pipeline, không mang tín hiệu định
dạng nào. Theo §9.1 chúng được sao chép hằng số nên FT-02 **không bao giờ đọc** mode
của chúng. Ghi ra chỉ để mode_map phủ đủ 137 id.

### 3.6 Kết luận phần B

| Hệ | n | `irac` | `general` | Độ tin cậy |
|---|---:|---:|---:|---|
| graphrag | 137 | 13 (9.5%) | 124 | suy luận — lưỡng cực sạch, 0 false positive ở phép thử âm tính |
| baseline | 137 | 0 | 137 | **tất định theo code** |

Giả định "tất cả general" mà kế hoạch cảnh báo là **sai lệch có hệ thống** đúng như dự
đoán — nhưng chỉ ở phía GraphRAG, và chỉ với 13/127 câu thực sự gửi mô hình (10.2%).

---

## 4. Tác động lên các task sau

| Task | Số cần dùng |
|---|---|
| FT-02 | mode lấy từ `mode_map.json`; baseline luôn `general`. `max_new_tokens` ≥ 1 536 là dư. |
| FT-03 | Ứng viên phải có cửa sổ gốc ≥ 32k **và** ≥ 2.8 ký tự/token tiếng Việt. Qwen2.5-7B, Llama-3.1-8B đạt. |
| FT-04 | Context mục tiêu: khuôn GraphRAG p50 ≈ 4 200 token / p95 ≈ 7 600; khuôn baseline p50 ≈ 1 800. |
| FT-05 | `max_seq_length = 16384`. Kiểm khả thi bộ nhớ T4 trước (§2.7.3). |

---

## 5. Chưa xác định

1. **Khả thi QLoRA 16k trên T4** — chưa đo, xem §2.7.3. Đây là rủi ro thật cho FT-05.
2. **Chốt mô hình** — thuộc FT-03. Ở đây chỉ thu hẹp còn 2 ứng viên đạt ràng buộc kỹ
   thuật; chất lượng tiếng Việt/pháp lý chưa đo.
3. **False negative của mode `irac`** — §3.4. Có lập luận, không có phép đo trực tiếp.
   Không có cách kiểm nếu không có planner cache.
