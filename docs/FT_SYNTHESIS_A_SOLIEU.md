# TỔNG HỢP FINE-TUNE — PHẦN A: SỐ LIỆU

> **Phạm vi.** Nguyên liệu số cho mục 4.7, Bảng 4.13 và phần trả lời hội đồng.
> Mọi con số dưới đây đọc từ file trong repo, kèm đường dẫn nguồn.
>
> **Quy ước nguồn.** Số liệu đánh giá tính lại từ `finetune/results/*.json` qua
> `src/evaluation/metrics.py::aggregate`, không chép từ bảng viết sẵn. Chỗ nào hai
> nguồn cho hai giá trị khác nhau, cả hai đều được ghi kèm nguồn — xem §0.
>
> **Lập luận phương pháp, khó khăn và cách giải quyết:** xem PHẦN B
> (`docs/FT_SYNTHESIS_B_KHOKHAN.md`). Tài liệu này không lặp lại nội dung đó.

---

## 0. Chỗ hai nguồn lệch nhau — đọc trước

> **Lượt đánh giá được báo cáo là `ft06b`.** Nguồn ngữ cảnh: `data/evaluation/results_graphrag_final1_20260729-022916.json`
> (cột GraphRAG) và `data/evaluation/results_baseline_20260710-085236.json` (cột Naive RAG)
> — **hai mẻ khác nhau, có chủ ý**. Lý do đầy đủ ở `finetune/reports/ft06b_matrix.md`
> đầu file và ở khối chú thích `finetune/kaggle_ft06.py:110-136`: vế Naive RAG không đi
> qua bộ lập kế hoạch truy vấn (`naive_rag.py:339,361` truyền `query_plan=None`) nên sửa
> đổi ở tầng đó không chạm tới nó và nó không cần chạy lại; vế GraphRAG lấy ngữ cảnh mới
> sau khi sửa (`docs/V3_RESULTS.md` §1). Truy hồi vẫn đóng băng ở cả sáu ô — mỗi ô chỉ
> đổi mô hình sinh.

| # | Đại lượng | Nguồn A | Nguồn B | Ghi chú |
|---:|---|---|---|---|
| 1 | Δ F1 Khoản của hàng Gemini | **+0.181317** — hiệu hai `aggregate.f1_mean` tính trên **toàn bộ 137 câu** (gồm 14 câu phủ định); cơ sở của `ft06b_matrix.md` §1 | **+0.187**, CI [0.108, 0.264], p = 0.00003 \*\*\*, W/L/T 67/32/24 — **ghép cặp từng câu trên 123 câu** (đã loại câu phủ định), `docs/V3_RESULTS.md` §3 | Không mâu thuẫn — **hai cơ sở khác nhau**. Bảng ma trận dùng cơ sở A vì đó là đại lượng mà **cả sáu ô cục bộ đều có sẵn** (`ft06b_matrix.md` §1.1); mức ý nghĩa thống kê chỉ tồn tại ở cơ sở B. Không được trộn hai cơ sở trong cùng một bảng |
| 2 | Δ F1 Khoản của Bảng 4.3 + mức ý nghĩa | **+0.156**, CI [0.070, 0.242], p = 0.001 \*\*\* — `CLAUDE.md` §TRẠNG THÁI HIỆN TẠI · **+0.143**, CI [0.061, 0.225], p = 0.0015 \*\* — `docs/V2_RESULTS.md` §1 | **+0.187**, CI [0.108, 0.264], p = 0.00003 \*\*\* — `docs/V3_RESULTS.md` §3 | `V3_RESULTS.md` là bộ số **thay thế** `V2_RESULTS.md` sau khi sửa lỗi phân loại địa phương (§1 của file đó) → **B là số đo mới nhất**; `CLAUDE.md` và `V2_RESULTS.md` chưa cập nhật |
| 3 | Tên kho mô hình gốc dùng để huấn luyện | `unsloth/Qwen3-4B-Instruct-2507` — `finetune/run.sh:50` truyền `--base-model` | **`unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit`** — `base_model_name_or_path` trong `adapter/…/checkpoint-588/adapter_config.json` | **Kho thật đã nạp là B.** Unsloth tự chuyển hướng tên kho sang bản **lượng tử-4-bit dựng sẵn** của chính họ khi `load_in_4bit=True`. Đây là **giá trị ghim** — người tái lập tải kho A sẽ nạp trọng số bf16 gốc, không phải trọng số 4-bit đã dựng sẵn, và ra kết quả khác. Xem §2.1 |
| 4 | Phân bố độ dài mẫu huấn luyện | tokenizer **Qwen2.5-7B** lúc dựng dữ liệu — `finetune/reports/dataset_stats.md` §2: mean 7 498 · p50 6 818 · p95 11 001 · max 12 950 | tokenizer **Qwen3 thật** lúc huấn luyện — `finetune/logs/ft04-5k-2ep-20260729-2122.log:51-60`: mean 7 530 · p50 6 869 · p95 11 009 · max 12 968 | **Đã đối chiếu được** (log phiên 2 nay có trong repo). Lệch ≤ 0.5 % ở mọi phân vị — đúng kỳ vọng nêu ở `dataset_stats.md` §8.1 (cùng họ BPE 151k). `over_limit = 0` ở cả train lẫn val, **đọc trực tiếp**, không còn phải suy |
| 5 | Thông lượng token/s của phiên huấn luyện | log in **`nan tok/s`** — `…2122.log:374` | **≈ 3 625.9 tok/s** — TÍNH LẠI: `total_tokens 35 316 237 × 2 epoch ÷ train_runtime 19 480 s` | Không phải mô hình chạy hỏng: `train_qlora.py:342` in `st.metrics.get("train_tokens_per_second", float("nan"))`, mà `transformers 5.5.0` **không đặt khoá đó** trong `st.metrics` → rơi vào giá trị mặc định `nan`. Giá trị TÍNH LẠI dùng ba con số đều đọc trực tiếp từ log (dòng 59, 87, 370) — xem §5.4 |

---

## 1. TÓM TẮT MỘT TRANG

| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| Mô hình gốc (kho **thật đã nạp** để huấn luyện) | `unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit` | `adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` (`base_model_name_or_path`) |
| Mô hình gốc (tên **truyền vào CLI**) | `unsloth/Qwen3-4B-Instruct-2507` — Unsloth tự chuyển hướng sang kho 4-bit ở dòng trên | `finetune/run.sh:50`; `finetune/train_qlora.py:42`; xem §0 mục 3 và §2.1 |
| Mô hình gốc (hàng "chưa tinh chỉnh", GGUF) | `bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF` :: `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | `finetune/reports/ft06b_artifacts.json` |
| Phương pháp | QLoRA 4-bit + LoRA, `train_on_responses_only` | `finetune/train_qlora.py:231-248`, `326-335` |
| LoRA r / alpha / dropout | 16 / 32 / 0.0 — **xác minh bằng `adapter_config.json`** | `adapter_config.json` (`r`, `lora_alpha`, `lora_dropout`) |
| Số layer được vá / loại mô-đun | **36 layer** — 36 QKV + 36 O + 36 MLP | `…2122.log:47` |
| Tham số huấn luyện được / tổng | **33 030 144 / 4 055 498 240 = 0.81 %** | `…2122.log:90` |
| `max_seq_length` | 16 384 | `finetune/run.sh:66`; `finetune/train_qlora.py:53` |
| Số mẫu tổng | 5 000 | `finetune/reports/dataset_stats.md` §0; `finetune/build_dataset.py:88` |
| Số mẫu train / val | 4 690 / 310 | đếm dòng `finetune/data/train.jsonl`, `finetune/data/val.jsonl` |
| Số mẫu val thực dùng khi eval | 64 | `finetune/run.sh:287`; `finetune/train_qlora.py:49-51`; `…2122.log:62` |
| Epoch | 2 | `finetune/run.sh:67`; `…2122.log:87` |
| Số bước tối ưu | **588** (294 mỗi epoch) — **số đo**, không phải suy | `…2122.log:87`, `:369`, `:377-378` |
| Thời gian huấn luyện | **19 480 s = 5 giờ 24 phút 40 giây** | `…2122.log:370`, `:373` (`train_runtime`), tiến trình `:367` |
| `train_loss` | **0.4054** | `…2122.log:370`, `:373` |
| `eval_loss` epoch 1 / epoch 2 | **0.3129 / 0.3082** | `…2122.log:377-378` (bảng `--- EVAL LOSS THEO EPOCH ---`) |
| Tỉ lệ token bị che | **5 623 / 5 707 = 98.5 %** | `…2122.log:84` |
| Thông lượng | **≈ 3 625.9 tok/s** — **TÍNH LẠI** (log ghi `nan`) | §0 mục 5; §5.4 |
| GGUF đã tinh chỉnh | `ft04-5k-2ep-20260729-2122-Q4_K_M.gguf` | `finetune/reports/ft06b_artifacts.json` |
| **F1 Khoản — ô 1** (ft, 0-shot, GraphRAG) | **0.401703** | `aggregate` trên `finetune/results/results_graphrag_ft06b-ft-s0.json` |
| **F1 Khoản — ô 2** (ft, 0-shot, Naive) | **0.300765** | `finetune/results/results_baseline_ft06b-ft-s0.json` |
| **F1 Khoản — ô 3** (base, 2-shot, GraphRAG) | **0.510879** | `finetune/results/results_graphrag_ft06b-base-s2.json` |
| **F1 Khoản — ô 4** (base, 2-shot, Naive) | **0.239092** | `finetune/results/results_baseline_ft06b-base-s2.json` |
| **F1 Khoản — ô 5** (base, 0-shot, GraphRAG) | **0.131387** | `finetune/results/results_graphrag_ft06b-base-s0.json` |
| **F1 Khoản — ô 6** (base, 0-shot, Naive) | **0.153771** | `finetune/results/results_baseline_ft06b-base-s0.json` |
| Δ F1 Khoản — hàng ft 0-shot | **+0.100938** | tính từ ô 1 − ô 2 |
| Δ F1 Khoản — hàng base 2-shot | **+0.271788** | tính từ ô 3 − ô 4 |
| Δ F1 Khoản — hàng base 0-shot | **−0.022384** | tính từ ô 5 − ô 6 |
| Δ F1 Khoản — hàng Gemini | **+0.181317** (cơ sở aggregate 137 câu, dùng cho ma trận) | §6.1; §0 mục 1 |
| Tổng lượt sinh | 822 = 6 ô × 137 câu | `docs/FINETUNE_EXECUTION_PLAN.md:635` |
| Số lần chạy mỗi ô — hàng cục bộ | N = 1 (tất định theo seed) | `docs/FINETUNE_EXECUTION_PLAN.md:731-745`; `ft06b_matrix.md` §1.2 |
| Số lần chạy — hàng Gemini | GraphRAG N = 3 (`final1/2/3`) · Naive N = 4 (bốn mẻ đủ 137 câu) | `ft06b_matrix.md` §1.3, §1.4 |

---

## 2. PHƯƠNG PHÁP TINH CHỈNH

### 2.1 Bảng tham số — trích số dòng

| Tham số | Giá trị đã chạy | Nơi đặt | Ghi chú |
|---|---|---|---|
| `--base-model` (tên truyền vào) | `unsloth/Qwen3-4B-Instruct-2507` | `run.sh:50` (`BASE_MODEL`) → `run.sh:284`; mặc định script `train_qlora.py:42` | ⚠️ **KHÔNG phải kho thật đã nạp** — xem dòng dưới |
| **Kho thật đã nạp** | **`unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit`** | `adapter_config.json` → `base_model_name_or_path` | Với `load_in_4bit = True`, Unsloth **tự chuyển hướng** tên kho sang bản lượng tử-4-bit (bitsandbytes NF4) mà họ dựng sẵn, thay vì tải trọng số bf16 rồi tự lượng tử hoá. Người tái lập phải dùng **chuỗi này**, không dùng chuỗi ở dòng trên |
| Lượng tử hoá | `load_in_4bit = True` | `train_qlora.py:234` | QLoRA; `dtype = None` (`train_qlora.py:235`) để Unsloth tự chọn. Đây chính là cờ kích hoạt việc chuyển hướng kho ở dòng trên |
| `r` | **16** | `run.sh:290` truyền `--lora-r 16`; **xác minh** `adapter_config.json` → `"r": 16` | mặc định script là **32** (`train_qlora.py:63`) — cấu hình adapter đã lưu chốt lại giá trị thật là 16 |
| `lora_alpha` | **32** | `run.sh:291` truyền `--lora-alpha 32`; **xác minh** `adapter_config.json` → `"lora_alpha": 32` | mặc định script là **64** (`train_qlora.py:64`) |
| `lora_dropout` | **0.0** | `train_qlora.py:240`; **xác minh** `adapter_config.json` → `"lora_dropout": 0.0` | hardcode trong script, không có cờ CLI |
| `bias` | `"none"` | `train_qlora.py:241`; **xác minh** `adapter_config.json` → `"bias": "none"` | hardcode |
| `target_modules` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` (**7 module**) | `train_qlora.py:243-244`; **xác minh** `adapter_config.json` → `target_modules` đúng 7 tên đó (thứ tự trong file là `k, o, down, q, gate, v, up` — tập hợp trùng khít) | hardcode |
| `use_rslora` | `False` | `train_qlora.py:246`; **xác minh** `adapter_config.json` → `"use_rslora": false` | hardcode |
| `use_dora` | `False` | `adapter_config.json` → `"use_dora": false` | không đặt trong script → mặc định thư viện |
| `peft_version` | **0.20.0** | `adapter_config.json` → `"peft_version": "0.20.0"` | khớp bộ ghim `peft==0.20.0` (§4.6) |
| `init_lora_weights` / `task_type` | `true` / `CAUSAL_LM` | `adapter_config.json` | mặc định thư viện |
| `random_state` | 42 | `train_qlora.py:247` (= `--seed`, mặc định 42 tại `train_qlora.py:67`) | |
| `use_gradient_checkpointing` | `"unsloth"` | `train_qlora.py:245` | |
| `learning_rate` | **2e-4** | `train_qlora.py:62` (mặc định, `run.sh` KHÔNG truyền lại) | kế hoạch §TASK-FT-05 chốt `lr=2e-4` (`FINETUNE_EXECUTION_PLAN.md:609`) |
| `lr_scheduler_type` | `"cosine"` | `train_qlora.py:171` | ta đặt |
| `warmup_ratio` | **0.03** | `train_qlora.py:170` | ta đặt |
| `optim` | `"adamw_8bit"` | `train_qlora.py:172` | ta đặt |
| `weight_decay` | **0.01** | `train_qlora.py:173` | ta đặt |
| `num_train_epochs` | **2** | `run.sh:67` (`EPOCHS=2`) → `run.sh:287` | `SMOKE=1` hạ về 1 (`run.sh:69`) — lần chạy thật không dùng |
| `per_device_train_batch_size` | **1** | `train_qlora.py:165` | 1 mẫu = 1 chuỗi, không padding |
| `per_device_eval_batch_size` | **1** | `train_qlora.py:207-209` | đặt qua `pick_field`, chỉ khi có val |
| `gradient_accumulation_steps` | **16** | `train_qlora.py:65` (mặc định `--grad-accum`), dùng ở `train_qlora.py:166` | |
| Batch hiệu dụng | **16** = 1 × 16 | tính từ hai dòng trên | |
| `max_seq_length` | **16 384** | `run.sh:66` → `run.sh:288`; mặc định script cũng 16 384 (`train_qlora.py:53`) | tên tham số tự dò `max_length` / `max_seq_length` (`train_qlora.py:182`) |
| `packing` | **False** | `train_qlora.py:176` | không gộp mẫu |
| `bf16` / `fp16` | `bf16 = (compute_cap ≥ 8)`, `fp16 = not bf16` | `train_qlora.py:223`, `175` | chọn theo compute capability, KHÔNG dùng `torch.cuda.is_bf16_supported()` (`train_qlora.py:224-225`) |
| `train_on_responses_only` | **BẬT** (mặc định) | `train_qlora.py:326-328`; mốc cắt `train_qlora.py:36-37` | tắt bằng `--no-response-only` — không dùng |
| `eval_strategy` | `"epoch"` | `train_qlora.py:201-203` | |
| `logging_steps` | 5 | `train_qlora.py:177` | |
| `save_steps` | 50 | `train_qlora.py:66` → `174` | |
| `save_total_limit` | 2 | `train_qlora.py:175` | |
| `report_to` | `"none"` | `train_qlora.py:179` | |
| `seed` (trainer) | 42 | `train_qlora.py:180` | |
| `hub_strategy` | `"checkpoint"` | `train_qlora.py:212` | |
| `--val-limit` | 64 | `run.sh:287` | mặc định script cũng 64 (`train_qlora.py:49`) |

### 2.2 Giá trị mặc định của thư viện, KHÔNG do ta đặt

| Tham số | Trạng thái |
|---|---|
| `adam_beta1` / `adam_beta2` / `adam_epsilon` | không xuất hiện trong `build_sft_kwargs` (`train_qlora.py:161-214`) → mặc định `SFTConfig`/`TrainingArguments` |
| `max_grad_norm` | không đặt → mặc định thư viện |
| `dataloader_*`, `group_by_length` | không đặt → mặc định thư viện. **Lưu ý:** kế hoạch §TASK-FT-05 (`FINETUNE_EXECUTION_PLAN.md:620-621`, `899`) yêu cầu "bật dynamic padding / length-grouped batching", nhưng `build_sft_kwargs` **không đặt `group_by_length`**; thay vào đó dùng `batch_size=1` để loại padding (`train_qlora.py:18`, `164`) |
| `neftune_noise_alpha`, `label_smoothing_factor` | không đặt → mặc định thư viện |
| `lora_alpha`-scaling nội bộ Unsloth | không can thiệp |

### 2.3 Cấu trúc adapter — đọc từ log và `adapter_config.json`

| Đại lượng | Giá trị | Nguồn |
|---|---|---|
| Số layer được vá LoRA | **36 layer**, gồm **36 QKV + 36 O + 36 MLP** | `finetune/logs/ft04-5k-2ep-20260729-2122.log:47` — *"Unsloth 2026.7.5 patched 36 layers with 36 QKV layers, 36 O layers and 36 MLP layers."* (dòng này lặp lại nguyên văn ở `:395` khi chặng merge nạp lại mô hình) |
| Số tham số huấn luyện được / tổng | **33 030 144 / 4 055 498 240 — 0.81 %** | `…2122.log:90` — *"Trainable parameters = 33,030,144 of 4,055,498,240 (0.81% trained)"* |
| `r` / `alpha` thực nạp | **16 / 32** | `adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` |
| Số bước tối ưu thật | **588** (`Total steps = 588`, và eval mốc `step 294` / `step 588`) | `…2122.log:87`, `:377-378` |
| Tỉ lệ token bị che | **5 623 / 5 707 token = 98.5 %** | `…2122.log:84` — *"che 5623/5707 token (98.5%) — con lai la dap an"*; script in ở `train_qlora.py:331-335` |

#### Kiểm chéo độc lập cho `r` — phép nhân phải khớp

Bảy mô-đun đích của Qwen3-4B cộng lại có **57 344** chiều vào+ra mỗi layer. Một adapter
LoRA hạng `r` trên một mô-đun `d_in → d_out` thêm `r × (d_in + d_out)` tham số, nên tổng
tham số huấn luyện được phải bằng:

```
36 layer × 57 344 × r  =  36 × 57 344 × 16  =  33 030 144
```

**Trùng khít** con số `33,030,144` mà log in ở dòng 90. Đây là **xác nhận thứ ba** cho
`r = 16`, độc lập với `run.sh:290` (cờ CLI) và với `adapter_config.json` (cấu hình đã
lưu): nếu `r` thật là 32 thì log phải in 66 060 288. Ba nguồn cùng chỉ về 16.

*(Cảnh báo cách đọc: phép nhân này giả định `lora_dropout` không thêm tham số và không có
`modules_to_save` — `adapter_config.json` xác nhận cả hai: `"modules_to_save": null`.)*

---

## 3. DỮ LIỆU

### 3.1 Nguồn

| Mục | Giá trị | Nguồn |
|---|---|---|
| Bộ dữ liệu | `thangvip/vietnamese-legal-qa` (HuggingFace) | `finetune/build_dataset.py:82`; `finetune/reports/dataset_stats.md` (dòng nguồn) |
| Quy mô gốc | 9 715 dòng / 29 145 cặp QA / 141 `doc_name` | `finetune/reports/dataset_stats.md` (dòng nguồn); `docs/FINETUNE_EXECUTION_PLAN.md:447-448` |
| `doc_type_name` | một giá trị duy nhất — "Luật" | `finetune/reports/dataset_stats.md` (dòng nguồn) |
| Giấy phép | **KHÔNG CÓ TRONG REPO** — không file nào ghi giấy phép của bộ nguồn. Đã tìm: `finetune/README.md`, `finetune/reports/dataset_stats.md`, `finetune/reports/dataset_build.json`, `finetune/build_dataset.py`, `docs/FINETUNE_EXECUTION_PLAN.md` | |
| Seed | 42 | `finetune/build_dataset.py:87` |
| Tất định | cùng seed → cùng bộ | `finetune/reports/dataset_stats.md` (dòng "Sinh bởi") |

### 3.2 Đường dựng mẫu — từng bước kèm hàm và số dòng

| Bước | Nội dung | Hàm · file:dòng |
|---:|---|---|
| 0 | Nạp bộ nguồn từ HF | `build()` — `finetune/build_dataset.py:667` |
| 1a | Đọc frontmatter `id` + `title` của `data/raw/*.md` → danh sách chặn 32 văn bản | `load_blocklist()` — `build_dataset.py:238` |
| 1b | Lọc rò rỉ ở cấp văn bản (so tên đã bỏ dấu + so số hiệu) | `doc_bi_ro_ri()` — `build_dataset.py:277`; phụ trợ `normalize_doc_name`, `extract_so_hieu` — `finetune/slug.py:76`, `:86` |
| 1c | Lọc rò rỉ ở cấp câu hỏi: 5-gram / Jaccard ≥ 0.6 với 137 câu `test_set_v2.json` | `load_test_question_ngrams()` — `build_dataset.py:295`; `question_bi_ro_ri()` — `build_dataset.py:307` |
| 2 | Lọc độ dài `article_content`: < 200 hoặc > 50 000 ký tự | hằng `MIN_ARTICLE_CHARS` / `MAX_ARTICLE_CHARS` — `build_dataset.py:104-105` |
| 3a | Suy slug từ `doc_name` theo convention (cơ khí, không LLM) | `doc_name_to_slug()` — `finetune/slug.py:127`; `build_slug_map()` — `slug.py:183` |
| 3b | Suy số Điều / Khoản / Điểm | `parse_article()` — `build_dataset.py:334`; regex `_DIEU_HEAD_RE`/`_KHOAN_RE`/`_DIEM_RE` — `build_dataset.py:168-170`; `suy_citation()` — `build_dataset.py:375` |
| 4a | Gộp 4–6 điều cùng `doc_name`, đặt điều gold lẫn giữa distractor | `chon_pack()` — `build_dataset.py:597`; hằng `MIN_PACK`/`MAX_PACK` — `build_dataset.py:107-108` |
| 4b | Dựng ngữ cảnh khuôn GraphRAG | `pack_graphrag()` — `build_dataset.py:488`; block text `_block_text_graphrag()` — `:454`; khối cảnh báo sửa đổi `_amendment_warning()` — `:473` |
| 4c | Dựng ngữ cảnh khuôn baseline | `pack_baseline()` — `build_dataset.py:541` |
| 5a | Nối khối trích dẫn đúng cú pháp đích vào cuối đáp án | `fmt_citation()` — `build_dataset.py:411`; `dung_answer()` — `:625` |
| 5b | Đa dạng hoá câu mở đầu (chống tic "Theo…") | `da_dang_hoa_mo_dau()` — `build_dataset.py:437`; danh sách `_OPENERS` — `:427` |
| 6 | **Dựng prompt bằng CHÍNH hàm của hệ đang chạy** | `to_record()` — `build_dataset.py:632`, gọi `build_messages(s.question, s.context, RESPONSE_MODE)` tại **`build_dataset.py:643`** |
| 7 | Tách train/val theo `doc_name` | `tach_train_val()` — `build_dataset.py:921-936` |
| 8 | Ghi `*.jsonl` + `*_meta.jsonl` | `ghi_jsonl()` — `build_dataset.py:939` |

**Tái dùng từ hệ đang chạy:**

| Thứ được tái dùng | Hàm | File gốc | Nơi import |
|---|---|---|---|
| System prompt + khung user prompt | `build_messages(question, context, mode)` | `src/retrieval/context_assembler.py` | `finetune/build_dataset.py:62` (import), `:643` (gọi) |
| Cùng hàm đó dùng lúc đánh giá | `build_chat_messages` gọi `build_messages` | `finetune/replay.py` | `finetune/kaggle_ft06.py:768` (cổng chặn B import `build_chat_messages` để dựng lại và đối chiếu) |
| Bộ chấm | `parse_citations`, `cit_matches`, `aggregate` | `src/retrieval/answer_generator.py`, `src/evaluation/metrics.py` | `build_dataset.py:897` (round-trip), `replay.py` (chấm) |

`RESPONSE_MODE = "general"` cho toàn bộ 5 000 mẫu — `build_dataset.py:102`.

**Cấu trúc `user_prompt`** (`finetune/reports/api_contract.md` §1.2, dựng tại `src/retrieval/context_assembler.py:408-413`):

```
CONTEXT:
{context}

CÂU HỎI: {question}

TRẢ LỜI:
```

Khung cố định = **30 ký tự** (`api_contract.md` §1.2).
`len(system_prompt)` = **11 264 ký tự** (`general`) / **11 532** (`irac`) — `api_contract.md` §1.3.

**Cú pháp trích dẫn đích** (`api_contract.md` §3.2):

```
[Điều {số}, Văn bản {slug}]
[Điều {số}, Khoản {số}, Văn bản {slug}]
[Điều {số}, Khoản {số}, Điểm {chữ}, Văn bản {slug}]
[Phụ lục {ký hiệu}, Văn bản {slug}]
[Phụ lục {ký hiệu}, Khoản {số}, Điểm {chữ}, Văn bản {slug}]
```

**Khuôn header ngữ cảnh** (`api_contract.md` §6.1 / §6.3):

```
GraphRAG:  --- [Tier {N} | Hiệu lực: {YYYY-MM-DD}] {Điều …}, {Khoản …}. ({norm_slug}) ---
Baseline:  --- Văn bản: {norm_id}, chunk {idx} ---
```

### 3.3 Bảng thành phần

| Đại lượng | Giá trị | Nguồn |
|---|---:|---|
| Tổng mẫu | 5 000 | `build_dataset.py:88` (`N_TOTAL`); `dataset_stats.md` §0 |
| Train | **4 690** | đếm dòng `finetune/data/train.jsonl` |
| Val | **310** | đếm dòng `finetune/data/val.jsonl` |
| Tỉ lệ val mục tiêu | 0.05 (`FRAC_VAL`) | `build_dataset.py:101` |
| Tỉ lệ val thực tế | 310 / 5 000 = **6.20 %** | tính từ hai dòng trên |
| Cách tách | theo trường **`doc_name`** — văn bản ở val KHÔNG có ở train | `tach_train_val()` — `build_dataset.py:921-936`; `dataset_stats.md` §8 |
| Mẫu trả lời được (`answerable`) | **4 550** | 5 000 − 450, `dataset_stats.md` §4 |
| `refusal_no_basis` | **315** — 6.3 % | `dataset_stats.md` §4 |
| `refusal_out_of_scope` | **135** — 2.7 % | `dataset_stats.md` §4 |
| Tổng mẫu từ chối | **450** — 9.0 % | `dataset_stats.md` §4; `FRAC_REFUSAL = 0.09` — `build_dataset.py:99` |
| Tỉ lệ chia hai loại từ chối | 70 / 30 | `build_dataset.py:745-747`; `dataset_stats.md` §4.2 |
| Khuôn `graphrag` | **2 529** — 50.6 % | `dataset_stats.md` §3 |
| Khuôn `baseline` | **2 471** — 49.4 % | `dataset_stats.md` §3 |
| Tỉ lệ mục tiêu hai khuôn | 0.50 (`FRAC_GRAPHRAG`) | `build_dataset.py:100` |
| Biến thể "HẾT HIỆU LỰC" trên block distractor | 5 % (`P_HET_HIEU_LUC = 0.05`; thực tế nguồn 45/2 199 header) | `build_dataset.py:130`; `dataset_stats.md` §3 |
| Khối `[AMENDMENT WARNING]` | 40 % (`P_AMENDMENT = 0.40`; thực tế nguồn 104/137 item) | `build_dataset.py:131`; `dataset_stats.md` §3 |
| Văn bản còn lại sau lọc | **90** | `finetune/reports/dataset_build.json` (`n_doc_sau_loc`) |
| Cặp QA dùng được | **16 962** (11 554 trong phạm vi / 5 408 ngoài phạm vi) | `dataset_build.json` (`n_qa_dung_duoc`, `n_qa_trong_pham_vi`, `n_qa_ngoai_pham_vi`) |

**Số bị drop, theo lý do** — `finetune/reports/dataset_build.json` (khoá `drops`), đối chiếu `dataset_stats.md` §1 (hai nguồn khớp):

| Lý do | Số bị drop |
|---|---:|
| `doc_ngoai_pham_vi` | 5 408 |
| `khong_suy_duoc_slug` | 2 331 |
| `leak_question_ngram` | 2 247 |
| `qa_khong_suy_duoc_dieu` | 1 733 |
| `article_qua_ngan` | 210 |
| `leak_doc_corpus` | 133 |
| `article_qua_dai` | 53 |
| `doc_thieu_dieu_de_dong_goi` | 19 |
| `qa_co_ngoac_vuong` | 9 |

Danh sách chặn: **32 văn bản** đọc từ `data/raw/*.md` — liệt kê đầy đủ ở `dataset_build.json` (khoá `blocklist`). Ba văn bản của corpus **thật sự có mặt** trong bộ nguồn và đã bị chặn (`dataset_stats.md` §1.1): Luật Hộ tịch 60/2014/QH13, Luật Nuôi con nuôi 52/2010/QH12, Luật sửa đổi bổ sung Luật Đất đai 31/2024/QH15.

**Hình dạng khối trích dẫn** (`dataset_stats.md` §5):

| Hình dạng | n |
|---|---:|
| `[Điều, Khoản, Văn bản]` | 4 682 |
| `[Điều, Văn bản]` | 775 |
| `[Điều, Khoản, Điểm, Văn bản]` | 267 |

Số citation mỗi mẫu trả lời được: mean **1.26**, max **2**. Số block mỗi ngữ cảnh: mean **17.5**, p50 **13**, max **67** (`dataset_stats.md` §5).

### 3.4 Bảng độ dài token

**Nguồn A — đo lúc dựng dữ liệu, tokenizer `Qwen/Qwen2.5-7B-Instruct`** (`finetune/reports/dataset_stats.md` §2):

| Đại lượng | n | mean | p50 | p95 | max | tổng |
|---|---:|---:|---:|---:|---:|---:|
| context — khuôn GraphRAG | 2 529 | 4 745 | 4 495 | 7 225 | 8 774 | KHÔNG CÓ TRONG REPO |
| context — khuôn baseline | 2 471 | 1 768 | 1 781 | 2 301 | 2 829 | KHÔNG CÓ TRONG REPO |
| đáp án (phần sinh ra) | 5 000 | 213 | 176 | 512 | 1 019 | KHÔNG CÓ TRONG REPO |
| **tổng chuỗi** = system + user + đáp án | 5 000 | **7 498** | **6 818** | **11 001** | **12 950** | KHÔNG CÓ TRONG REPO |

- System prompt đo lại tại `dataset_stats.md` §2: **3 936 token** — khớp `token_budget.md` §2.2.
- **Số mẫu vượt trần `max_seq_length = 16 384`: 0 (0.00 %)** — `dataset_stats.md` §2.2.
- Cột "tổng" (`total_tokens`) chỉ được `audit_lengths` ghi ra `length_stats.json` — file thiếu, xem dưới.

**Mục tiêu độ dài đã đặt trước** (`token_budget.md` §2.7.2, nhắc lại ở `dataset_stats.md` §2.1):

| Khuôn | n tham chiếu | p50 mục tiêu | p95 mục tiêu | max mục tiêu |
|---|---:|---:|---:|---:|
| GraphRAG | 127 | ~4 200 | ~7 600 | ~8 000 |
| Baseline | 137 | ~1 800 | – | ~2 450 |

**Nguồn B — đo lúc huấn luyện bằng tokenizer thật** (`audit_lengths()`, `train_qlora.py:107-135`). File `length_stats.json` / `val_length_stats.json` vẫn không có trong repo, nhưng **cùng bảng đó được in nguyên vẹn ra log huấn luyện** — `finetune/logs/ft04-5k-2ep-20260729-2122.log`, khối `--- PHAN BO DO DAI MAU (tokenizer that, chuoi that) ---`:

| Tập | dòng log | n_samples | p50 | mean | p95 | max | limit | over_limit | total_tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **train** | `:51-60` | 4 690 | 6 869 | 7 530 | 11 009 | 12 968 | 16 384 | **0** | **35 316 237** |
| **val** (64 mẫu đã cắt) | `:64-73` | 64 | 6 542 | 7 286 | 10 956 | 12 062 | 16 384 | **0** | **466 358** |

**Đối chiếu hai nguồn — lệch không đáng kể:**

| Đại lượng | Qwen2.5 (dựng dữ liệu, 5 000 mẫu) | Qwen3 thật (huấn luyện, 4 690 mẫu train) | Lệch |
|---|---:|---:|---:|
| mean | 7 498 | 7 530 | +0.43 % |
| p50 | 6 818 | 6 869 | +0.75 % |
| p95 | 11 001 | 11 009 | +0.07 % |
| max | 12 950 | 12 968 | +0.14 % |

Kỳ vọng nêu ở `dataset_stats.md` §8.1 (Qwen2.5 và Qwen3 cùng họ BPE 151k) **được số đo xác nhận** — không còn là lập luận suông. Hai cột không cùng mẫu số (5 000 so với 4 690) nên đây là đối chiếu **phân bố**, không phải phép trừ từng mẫu.

`over_limit = 0` ở cả train lẫn val nay **đọc trực tiếp** (`:58`, `:71`), không còn phải suy từ việc `audit_lengths` không kích `SystemExit` (`train_qlora.py:130-131`).

**Số liệu ngân sách token đối chiếu, đo trên 137 câu eval thật** (`finetune/reports/token_budget.md` §2.1, tokenizer Qwen2.5-7B):

| Tập | n | mean | p50 | p90 | p95 | max |
|---|---:|---:|---:|---:|---:|---:|
| GraphRAG | 127 | 8 610 | 8 170 | 11 087 | 11 596 | **12 011** |
| Baseline | 137 | 5 852 | 5 797 | 6 139 | 6 220 | **6 432** |

Bóc tách (Qwen2.5, GraphRAG — `token_budget.md` §2.2): `system_prompt` mean 3 946 / p50 3 936 / max 4 034; `context` mean 4 602 / p50 4 188 / p95 7 601 / max 8 028; phần còn lại mean 49 / max 89.

*Kiểm chéo (tính từ hai nguồn):* max prompt backend đo được ở ô 1 và ô 5 là **12 011** token (§6.2), **trùng khít** con số 12 011 mà `token_budget.md` §2.1 đo trước đó bằng tokenizer Qwen2.5 trên cùng 127 câu.

### 3.5 Bảng kiểm tự động

`kiem_tra()` — `finetune/build_dataset.py:887-915`. Chạy trên **toàn bộ 5 000 mẫu**.

| # | Assert | Điều kiện | Số mẫu đã kiểm | Kết quả |
|---:|---|---|---:|---|
| 1 | `build_dataset.py:890` | `doc_bi_ro_ri(doc_name, …) is None` — không mẫu nào còn khớp danh sách chặn 32 văn bản | 5 000 | ✅ `dataset_stats.md` §6 mục 2 |
| 2 | `build_dataset.py:897` | `parse_citations(answer) == citations` — round-trip đúng cả Điều, Khoản, Điểm, slug | 5 000 | ✅ **5 000 / 5 000** — `dataset_stats.md` §6 mục 3 |
| 3 | `build_dataset.py:902` | mẫu `answerable` phải parse ra ≥ 1 citation | 4 550 | ✅ |
| 4 | `build_dataset.py:904` | `citation["van_ban"] == slug` của mẫu | 4 550 | ✅ |
| 5 | `build_dataset.py:907` | **slug phải có mặt trong `context` của chính mẫu đó** (chống dạy bịa slug từ trí nhớ) | 4 550 | ✅ `dataset_stats.md` §6 mục 3b |
| 6 | `build_dataset.py:911` | `f"Điều {dieu}."` phải có mặt trong `context` | 4 550 | ✅ |
| 7 | `build_dataset.py:915` | mẫu từ chối phải parse ra **đúng 0** citation | 450 | ✅ |
| 8 | `build_dataset.py:71` | `context_assembler.INCLUDE_SCHEMA_B is False` (kiểm lúc import) | — | ✅ |
| 9 | `train_qlora.py:124-131` | `over_limit == 0`, nếu không thì `SystemExit` | 4 690 + 64 | ✅ **0/4690** và **0/64** — `…2122.log:58`, `:60`, `:71`, `:73` |

Kiểm thủ công bổ sung: 20 mẫu đầy đủ xuất ra `finetune/reports/samples_20.txt` (319 152 byte) — `dataset_stats.md` §6 mục 5.

Unit test: `finetune/slug.py` có **22 ca** ở `tests/test_finetune_slug.py` (`dataset_stats.md` §6 mục 1); `replay.py` 48 test, `build_dataset.py` 49 test (`finetune/README.md` §Trạng thái).

**sha256 của hai file dữ liệu** (`finetune/data/train.jsonl.sha256`, `finetune/data/val.jsonl.sha256`):

```
615ad1e7a3ad0dfa991147ae503e6078f138bce90e6a45252bc0189535c79b20  train.jsonl
2361e15b7f195e3c7929599d57ad94f5d215343565af8f11cb3d5fe178b93ead  val.jsonl
```

---

## 4. TRIỂN KHAI

### 4.1 Hai môi trường

| Mục | Phiên 2 — huấn luyện | Phiên 3 — đánh giá |
|---|---|---|
| Nền | RunPod Community Cloud | Kaggle Notebooks |
| GPU dự kiến / yêu cầu | RTX 4090, preflight chặn `sm < 80` và VRAM < 22 000 MB | — |
| GPU thực tế | **NVIDIA GeForce RTX 4090 · sm89 · Num GPUs = 1 · Max memory 23.516 GB · Linux** — `…2122.log:39`, `:41` | **Tesla T4 × 2, 15 360 MiB mỗi card** |
| bf16 | **bf16 gốc = True** (`…2122.log:39`); `Bfloat16 = TRUE` (`:43`) | không áp dụng |
| Attention backend | **Xformers 0.0.35 · FA2 = False** — `…2122.log:43` | không áp dụng |
| Bộ thư viện lúc chạy | Torch **2.10.0+cu128** · CUDA **8.9** · CUDA Toolkit **12.8** · Triton **3.6.0** (`:42`) · Transformers **5.5.0** · Unsloth **2026.7.5** (`:40`) | xem §4.6 |
| Nguồn | `finetune/run.sh:6`, `:132-143`; `finetune/logs/ft04-5k-2ep-20260729-2122.log:39-43` | `finetune/reports/ft06b_gpu_info.json`; `ft06b_matrix.md` §3; `finetune/reports/ft06b_run_status.json` |
| Ràng buộc đĩa | ≥ 50 GB trống (`run.sh:145-146`) | — |
| Ràng buộc Python | đúng 3.12 (`run.sh:150-151`, vì wheel là cp312) | cp312 (`ft06b_artifacts.json`) |
| Thời gian | chặng `train` = **19 480 s ≈ 5 giờ 24 phút 40 giây** (`…2122.log:370`, `:373`); tổng cả bảy chặng **KHÔNG CÓ TRONG REPO** (log không in mốc thời gian đầu/cuối) | tổng `total_elapsed_s` sáu ô = **11 313.56 s ≈ 3 giờ 8 phút** (cộng từ sáu results JSON, §6.2) |
| Chi phí | **KHÔNG CÓ TRONG REPO** — không file nào ghi giá thuê. `run.sh:129` chỉ nêu chi phí một lần preflight hỏng ≈ $0.003 | Kaggle miễn phí (30 giờ/tuần — `FINETUNE_EXECUTION_PLAN.md:594`) |

### 4.2 Bảy chặng của `finetune/run.sh`

Danh sách chặng: `preflight,install,data,train,merge,gguf,publish` — `run.sh:98`.

| # | Chặng | Dòng | Làm gì | Đầu ra |
|---:|---|---|---|---|
| 0 | `preflight` | `run.sh:130-156` | Kiểm `compute_cap ≥ 80`, VRAM ≥ 22 000 MB, đĩa trống ≥ 50 GB, Python = 3.12, có `HF_TOKEN` | thoát `exit 1` nếu hỏng, trong ~30 giây |
| 1 | `install` | `run.sh:159-225` | Cài `huggingface_hub==1.25.1` + `hf_xet`; ghi `constraints.txt` 6 dòng ghim phiên bản; cài unsloth/trl/peft/transformers/accelerate/bitsandbytes/datasets theo `-c`; cài `llama-cpp-python==0.3.16`; clone llama.cpp tag `b10165` lấy script convert; tải + đối chiếu sha256 tarball `llama-quantize`; cổng cuối kiểm `torch` là bản CUDA | `$WORK/constraints.txt`, `$WORK/llama.cpp`, `$WORK/llama-bin/llama-quantize` |
| 2 | `data` | `run.sh:231-244` | Tải `train.jsonl`, `val.jsonl` + hai file `.sha256` từ HF dataset repo; `sha256sum -c`; `wc -l` | `$WORK/data/{train,val}.jsonl` |
| 3 | `train` | `run.sh:254-300` | Dò checkpoint trên HF để `--resume`; gọi `python train_qlora.py` với `--lora-r 16 --lora-alpha 32 --val-limit 64 --epochs 2 --max-seq-length 16384`; đẩy adapter lên HF | `$WORK/adapter/` (gồm `train_result.json`, `length_stats.json`, `val_length_stats.json`, `rendered_samples.txt`) |
| 4 | `merge` | `run.sh:303-317` | Nạp adapter ở `load_in_4bit=False`, `save_pretrained_merged(save_method="merged_16bit")` | `$WORK/merged/` |
| 5 | `gguf` | `run.sh:320-390` | `convert_hf_to_gguf.py --outtype f16` → `llama-quantize … Q4_K_M` → xoá bản f16 (~8 GB); in sha256; smoke test nạp thật + sinh thật bằng `llama-cpp-python` trên CPU, `max_tokens=128`, assert độ dài > 50 ký tự | `$WORK/gguf/{RUN_NAME}-Q4_K_M.gguf`, `$WORK/smoke_out.json` |
| 6 | `publish` | `run.sh:393-405` | Tính `.sha256`, đẩy GGUF + `.sha256` lên HF | `gguf/{RUN_NAME}-Q4_K_M.gguf` trên HF |

Ngoài bảy chặng: `cleanup()` (`run.sh:105-125`) chạy ở **mọi đường thoát** — đẩy log lên HF rồi tự huỷ pod sau 60 giây nếu `SELFDESTRUCT=1`.

### 4.3 Năm chặng của `finetune/kaggle_ft06.py`

Danh sách chặng: `prep`, `gate-template`, `gate-prompt`, `run`, `table` — `kaggle_ft06.py:9-13`.

| # | Chặng | Hàm · dòng | Làm gì | Đầu ra |
|---:|---|---|---|---|
| 1 | `prep` | `stage_prep()` — `kaggle_ft06.py:578` | Tải wheel `llama-cpp-python` và đối chiếu sha256 **trước khi** `pip install`; tải hai file GGUF (base theo `revision` ghim, ft); đối chiếu sha256 cả hai; tạo symlink vào `finetune/models/`; in `nvidia-smi` | `finetune/reports/ft06b_artifacts.json`, `finetune/reports/ft06b_gpu_info.json` |
| 2 | `gate-template` | `stage_gate_template()` — `:700` | Đọc `tokenizer.chat_template` nhúng trong **cả hai** GGUF; so độ dài + sha256; in `difflib` nếu khác; **`exit 2`** nếu khác (`:730`) | `finetune/reports/ft06b_chat_template_base.jinja`, `…_ft.jinja` |
| 3 | `gate-prompt` | `stage_gate_prompt()` — `:840` | Sinh prompt cho bốn tổ hợp `{graphrag, baseline} × {0-shot, 2-shot}`; chạy 5 kiểm tự động (§4.5); in 40 dòng đầu + 20 dòng cuối mỗi file; **`exit 2`** nếu bất kỳ mục FAIL | 4 file `ft06b_prompt_{system}_s{n}.txt`, 4 file `results_{system}_ft06b-gate-prompt-s{n}.json` |
| 4 | `run` | `stage_run()` — `:1229`; song song `_run_song_song()` — `:1146` | Sáu ô, mỗi ô một lệnh `python -m finetune.replay`, ghim `CUDA_VISIBLE_DEVICES` của subprocess; `--resume`; đẩy HF ngay sau từng ô | 6 file `results_{system}_ft06b-*.json` + 6 `.partial.jsonl`, `ft06b_run_status*.json`, `ft06b_gpu{0,1}.log` |
| 5 | `table` | `stage_table()` — `:1933` | Gom sáu file kết quả, gọi `metrics.aggregate`, dựng bảng; hàng Gemini **cũng tính từ file kết quả**, không ghim hằng số | `finetune/reports/ft06b_matrix.md` |

Tham số sinh: script **KHÔNG truyền lại bảy trong tám giá trị** (đã là mặc định của `replay.py`); **ngoại lệ duy nhất** là `--presence-penalty 0` truyền tường minh tại `kaggle_ft06.py:898` (chặng gate-prompt) và `:1291` (chặng run), vì mặc định của `replay.py` là **1.0** (`replay.py:166`) — lý do ghi ở `kaggle_ft06.py:42`.

Nguồn ngữ cảnh là **tham số**, không ghim cứng: `SRC_GRAPHRAG` / `SRC_BASELINE` (`kaggle_ft06.py:137-139`) đổi được qua cờ `--src-graphrag` / `--src-baseline` (`:2104`, `:2109`). Ba lý do cho phép hai vế dùng hai mẻ khác nhau ghi ở `kaggle_ft06.py:110-136`.

Phân luồng GPU: `LANES = {0: [1, 3, 2], 1: [5, 4, 6]}` — `kaggle_ft06.py:331-334`.

### 4.4 Cổng chặn A — chat template

| Mục | Giá trị | Nguồn |
|---|---|---|
| Điều kiện qua | `sha256(template_base) == sha256(template_ft)` | `kaggle_ft06.py:730`; hỏng → `exit 2` |
| Độ dài template base | **4 040 ký tự** | đo trên `finetune/reports/ft06b_chat_template_base.jinja` |
| Độ dài template ft | **4 040 ký tự** | đo trên `finetune/reports/ft06b_chat_template_ft.jinja` |
| sha256 cả hai | `40c21f34cf67d8c760ef72f8ad3ae5afad514299d4b06e91dd9a8d705af7b541` | tính lại trên hai file `.jinja` |
| Kết quả | **TRÙNG KHÍT** (byte-identical, hai file giống nhau hoàn toàn) | như trên |

*Lượt `ft06b` không đổi file GGUF nào (cả hai vẫn đúng sha256 đã ghim ở §4.6) nên cổng này chỉ chạy lại để xác nhận, và cho đúng cùng một chuỗi sha256 với lượt trước.*

### 4.5 Cổng chặn B — prompt đã render

Năm kiểm tự động, hàm `_kiem_mot_prompt()` — `kaggle_ft06.py:763-838`:

| # | Kiểm tra | Điều kiện | Dòng |
|---:|---|---|---|
| 1 | Render bằng chat template GGUF thật | header chứa `render=gguf-chat-template-jinja2`, KHÔNG phải nhánh lùi `render-loi:` | `:772-776` |
| 2 | System prompt còn nguyên đầu | 200 ký tự đầu sau `<\|im_start\|>system` khớp `build_chat_messages(...)[0]` | `:778-812` |
| 3 | Số lượt vai | = **2** khi `n_shot = 0`, = **6** khi `n_shot = 2` | `:814-818` |
| 4 | Kết thúc prompt | nội dung cuối trước thẻ mở vai assistant là `"TRẢ LỜI:"` | `:820-830` |
| 5 | Số thẻ mở vai assistant | = **1** khi `n_shot = 0`, = **3** khi `n_shot = 2` | `:832-836` |

**Cổng chặn B được chạy LẠI cho lượt `ft06b`, không tái dùng bản dump cũ.** Lý do in ngay trong chặng (`kaggle_ft06.py:844-847`): nguồn ngữ cảnh phía GraphRAG đã đổi nên prompt thực sự đi vào mô hình cũng đổi ở 17 câu; bản dump của lượt trước không nói gì về prompt của lượt này. File dump ghi ra **tên mới** (`ft06b_prompt_*`) để không đè bản cũ.

Bằng chứng đã chạy — bốn file prompt và bốn results JSON tương ứng (câu **V001** cho cả bốn):

| Tổ hợp | File prompt | Kích thước file | `n_tokens_prompt` (tự đếm) | `n_tokens_prompt_backend` | `prompt_len_lech` |
|---|---|---:|---:|---:|---:|
| graphrag · 0-shot | `finetune/reports/ft06b_prompt_graphrag_s0.txt` | 37 402 B | **10 144** | 10 122 | 22 |
| graphrag · 2-shot | `finetune/reports/ft06b_prompt_graphrag_s2.txt` | 38 566 B | **10 556** | 10 500 | 56 |
| baseline · 0-shot | `finetune/reports/ft06b_prompt_baseline_s0.txt` | 22 513 B | **6 182** | 6 160 | 22 |
| baseline · 2-shot | `finetune/reports/ft06b_prompt_baseline_s2.txt` | 23 677 B | **6 594** | 6 538 | 56 |

Cả bốn file results gate-prompt đều `format_ok_rate = 1.0`, `f1_mean = 1.0`, `n_hit_token_cap = 0` (`aggregate` trên `finetune/results/results_*_ft06b-gate-prompt-s*.json`).

*V001 nằm ngoài 17 câu đổi ngữ cảnh, nên bốn con số độ dài prompt ở bảng trên **trùng khít** bản dump của lượt trước. Đó là kết quả mong đợi, không phải dấu hiệu bản dump bị tái dùng — bốn file `ft06b_prompt_*.txt` là file mới, sinh trong lượt này.*

### 4.6 Bảy giá trị ghim — chuỗi đầy đủ

| # | Đối tượng | Chuỗi đầy đủ | File ghi |
|---:|---|---|---|
| 1 | Tarball llama.cpp (CPU-only static, dùng để **lượng tử hoá**) | tag `b10165`; file `llamacpp-b10165-cpu-static-x64.tar.gz`; sha256 `9f8e92b8a69b3c8399e6f42324430f8a0faaf1bba707deeee7c8cb96bbd9c6d5` | `finetune/run.sh:53`, `:58`, `:59` |
| 2 | Wheel `llama-cpp-python` (dùng để **chạy suy luận, sinh số liệu**) | repo `dangnguyen254/thesis-graphrag-gguf`; file `runtime/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl`; sha256 `a3cb84bddb15c1759a0ece5ec8ef9d10d1419f926c895064d1a91ec517fd0da7` | `finetune/reports/ft06b_artifacts.json`; `finetune/kaggle_ft06.py:225`; `finetune/run.sh:54` (`LCP_VERSION=0.3.16`) |
| 3 | GGUF mô hình gốc + revision | repo `bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF`; file `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf`; revision `ae44f08e1392f39c0e474af10c3ff8355c8b6688`; sha256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e` | `finetune/reports/ft06b_artifacts.json`; `finetune/kaggle_ft06.py:242-251`; `finetune/reports/gate_base_model.md` §Hiện vật GGUF gốc; `../results/__huggingface_repos__.json` (xác nhận độc lập cùng `commitHash`) |
| 3b | **Kho mô hình gốc dùng để HUẤN LUYỆN** (khác giá trị 3 — đó là bản GGUF của hàng "chưa tinh chỉnh") | `unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit` — **KHÔNG** phải `unsloth/Qwen3-4B-Instruct-2507` như cờ CLI ghi | `adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` → `base_model_name_or_path`; xem §0 mục 3 |
| 4 | Commit code | **phiên 3:** `2a712adf7707164b7302afa42cf98ea06c99b417` (nhánh `dev/fine-tune`) · **phiên 1:** `eecdc7b7dc533f2c564d74e795704fb4dcbb81a2` **cộng** một bản vá `render_prompt` chưa từng nằm trong commit nào | phiên 3: `../results/repo/.git/refs/heads/dev/fine-tune` + `../results/repo/.git/logs/HEAD` (clone lúc epoch 1785391123 = 2026-07-30T05:58:43Z); phiên 1: `finetune/reports/gate_base_model.md` §6 |
| 5 | Dữ liệu huấn luyện | `train.jsonl` sha256 `615ad1e7a3ad0dfa991147ae503e6078f138bce90e6a45252bc0189535c79b20` · `val.jsonl` sha256 `2361e15b7f195e3c7929599d57ad94f5d215343565af8f11cb3d5fe178b93ead` | `finetune/data/train.jsonl.sha256`, `finetune/data/val.jsonl.sha256` |
| 6 | GGUF đã tinh chỉnh | repo `dangnguyen254/thesis-graphrag-gguf`; file `gguf/ft04-5k-2ep-20260729-2122-Q4_K_M.gguf`; sha256 `c115e6a79299d1fe0e41eb5f6720955108df1e869676dc96f0b7ba61c37ce5d0` | `finetune/reports/ft06b_artifacts.json`; `finetune/kaggle_ft06.py:232` |
| 7 | Ghim GPU (mỗi ô một card) | ô 1 → `CUDA_VISIBLE_DEVICES=0` · ô 2 → `0` · ô 3 → `0` · ô 4 → `1` · ô 5 → `1` · ô 6 → `1` | `finetune/reports/ft06b_run_status.json` (khoá `gpu` của từng ô — **ghi lúc chạy**); `finetune/reports/ft06b_matrix.md` §3; lệnh thật in trong `finetune/logs/ft06b_gpu{0,1}.log` |
| 8 | **Nguồn ngữ cảnh + sha256 của nó** | GraphRAG `data/evaluation/results_graphrag_final1_20260729-022916.json` sha256 `7deda57ef145b8a779483a2132cd1d929dc6244807bf7a113bd29f6c1092b7f8` · Naive `data/evaluation/results_baseline_20260710-085236.json` sha256 `37fca8d026443e4cfc5f759f6f98712f638468a58d9a177adbd01dba30bcb38c` | `finetune/reports/ft06b_run_status.json` (`src_file`, `src_sha256` của cả sáu ô); cũng lưu trong `replay.src_sha256` của từng file kết quả |

> **Cảnh báo về `ft06b_gpu_info.json`.** File đó ghi `"che_do": "tuần tự, mọi ô trên card 0"`, `"song_song": false`, `ghim_cuda_visible_devices` = card 0 cho cả sáu ô — nhưng khoá `"nguon": "prep — dự kiến"` nói rõ đó là **dự kiến lúc chặng `prep`**, không phải cái đã chạy. Cái đã chạy nằm ở `ft06b_run_status.json`: card 0 cho ô 1/2/3, card 1 cho ô 4/5/6, đúng như `ft06b_matrix.md` §3 ghi (*"ghi nhận lúc: run — thực tế"*). **Dùng `ft06b_run_status.json`, không dùng `ft06b_gpu_info.json`, cho giá trị ghim thứ bảy.**

Bộ ghim phiên bản gói (phiên 3) — `../results/ft06_constraints.txt`, đối chiếu `finetune/run.sh:174-181`:

```
torch==2.10.0
torchvision==0.25.0
torchaudio==2.10.0
transformers==5.5.0
trl==0.24.0
peft==0.20.0
unsloth==2026.7.5
huggingface_hub==1.25.1
llama_cpp_python==0.3.16
```

*(`run.sh:174-181` ghim 6 dòng đầu, không có `torchvision`/`torchaudio`/`llama_cpp_python`.)*

---

## 5. KẾT QUẢ HUẤN LUYỆN

> **Nguồn của toàn bộ §5:** `finetune/logs/ft04-5k-2ep-20260729-2122.log` (1 807 dòng) —
> log đầy đủ của phiên 2, nay đã có trong repo. Mỗi giá trị dưới đây kèm **số dòng**.
> Bổ sung: `adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` cho
> cấu hình adapter (§2.1, §2.3).
>
> Ba file `adapter/train_result.json`, `adapter/length_stats.json`,
> `adapter/val_length_stats.json` **vẫn không có trong repo** — nhưng nội dung của chúng
> được in nguyên vẹn ra log, nên §5 không còn chỗ trống nào ngoài chuỗi `log_history`
> đầy đủ (§5.5) và `total_flos`.

### 5.1 Bảng kết quả huấn luyện

| Đại lượng | Giá trị | Dòng log |
|---|---:|---|
| `train_loss` (= `training_loss`) | **0.4054** | `:370`, nhắc lại `:373` |
| `train_runtime` | **19 480 s** (log in `1.948e+04`) = **5 giờ 24 phút 40 giây** | `:370`, `:373`; thanh tiến trình `:367` in `5:24:40` |
| `train_samples_per_second` | **0.482** | `:370` |
| `train_steps_per_second` | **0.03** | `:370` |
| `eval_loss` sau **epoch 1** (step 294) | **0.3129** | `:377` |
| `eval_loss` sau **epoch 2** (step 588) | **0.3082** | `:378`; cùng giá trị in ở `:366`, `:369` |
| Mức cải thiện eval_loss | **−0.0047** tuyệt đối = **1.50 %** tương đối | tính từ hai dòng trên |
| `eval_runtime` / `eval_samples_per_second` (epoch 2) | 41.94 s / 1.526 | `:366` |
| Tổng số bước | **588** | `:87` (`Total steps = 588`) |
| Số mẫu / epoch / batch hiệu dụng | 4 690 / 2 / **16** (= 1 × 16 × 1) | `:87-89` |
| Tỉ lệ token bị che | **5 623 / 5 707 = 98.5 %** | `:84` |
| Tham số huấn luyện được / tổng | **33 030 144 / 4 055 498 240 = 0.81 %** | `:90` |
| Số layer được vá | **36** (36 QKV + 36 O + 36 MLP) | `:47` |
| `total_flos` | **KHÔNG CÓ TRONG REPO** — `st.metrics` có khoá này nhưng script chỉ in bốn giá trị ở `:370`, không in `total_flos`; `train_result.json` (nơi ghi trọn `st.metrics`) không có trong repo | — |

*Kiểm chéo hai giá trị thông lượng của HF Trainer, cả hai khớp:*
`4 690 × 2 ÷ 19 480 = 0.4815` ≈ `train_samples_per_second 0.482` ·
`588 ÷ 19 480 = 0.03019` ≈ `train_steps_per_second 0.03`.

### 5.2 Bộ phiên bản tại thời điểm chạy — đọc từ log, không từ file ghim

| Hạng mục | Giá trị | Dòng log |
|---|---|---|
| GPU | **NVIDIA GeForce RTX 4090**, `sm89`, **Num GPUs = 1**, Max memory **23.516 GB**, Platform Linux | `:39`, `:41` |
| bf16 gốc | **True** (`bf16 goc = True` ở `:39`; `Bfloat16 = TRUE` ở `:43`) | `:39`, `:43` |
| Attention backend | **Xformers 0.0.35**, **FA2 = False** | `:43` |
| Torch | **2.10.0+cu128** | `:42` |
| CUDA (compute capability) | **8.9** | `:42` |
| CUDA Toolkit | **12.8** | `:42` |
| Triton | **3.6.0** | `:42` |
| Transformers | **5.5.0** | `:40` |
| Unsloth | **2026.7.5** | `:40`, `:47` |

Bốn dòng `:40-43` chính là khối banner của Unsloth; chúng lặp lại nguyên văn ở `:388-391`
khi chặng `merge` nạp lại mô hình — nên đây là hai lần ghi độc lập cho cùng bộ phiên bản.

**Đối chiếu với bộ ghim §4.6:** `torch==2.10.0` ✅ · `transformers==5.5.0` ✅ ·
`unsloth==2026.7.5` ✅. Ba dòng còn lại của bộ ghim (`trl`, `peft`, `huggingface_hub`)
không in ra log; `peft` được xác nhận gián tiếp qua `adapter_config.json` →
`"peft_version": "0.20.0"` ✅.

### 5.3 Audit độ dài — số đo bằng tokenizer thật

| Tập | dòng | n_samples | p50 | mean | p95 | max | limit | over_limit | total_tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| train | `:51-60` | 4 690 | 6 869 | 7 530 | 11 009 | 12 968 | 16 384 | **0** | **35 316 237** |
| val (64/310 đã cắt) | `:62-73` | 64 | 6 542 | 7 286 | 10 956 | 12 062 | 16 384 | **0** | **466 358** |

Dòng `:60` in `OK: 0/4690 mau vuot tran.` và `:73` in `OK: 0/64 mau vuot tran.` — cổng
`audit_lengths` (`train_qlora.py:124-131`) đã qua ở cả hai tập. Đối chiếu với bản đo bằng
tokenizer Qwen2.5 lúc dựng dữ liệu: xem §3.4 (lệch ≤ 0.75 %).

### 5.4 Thông lượng — TÍNH LẠI vì log ghi `nan`

Dòng `:374` in `thong luong ~ nan tok/s`. **Đây không phải triệu chứng mô hình chạy
hỏng.** `train_qlora.py:342` gọi `st.metrics.get("train_tokens_per_second", float("nan"))`,
và `transformers 5.5.0` không đặt khoá `train_tokens_per_second` vào `st.metrics`, nên
giá trị mặc định `nan` được in ra. Ba giá trị khác trên cùng dòng `:370` (`train_runtime`,
`train_samples_per_second`, `train_steps_per_second`) đều bình thường và khớp nhau (§5.1).

**Phép tính lại:**

```
total_tokens (train, đo bằng tokenizer thật)  = 35 316 237      (log :59)
× số epoch                                    = 2               (log :87)
= khối lượng token thật đã đi qua             = 70 632 474
÷ train_runtime                               = 19 480 s        (log :370)
= 3 625.9 token/giây
```

> **Ghi rõ khi trích dẫn: đây là giá trị TÍNH LẠI, không phải số đo do thư viện báo.**
> Ba đầu vào đều đọc trực tiếp từ log. Hai giới hạn của phép tính: (a) nó đếm **mọi**
> token của chuỗi, kể cả 98.5 % token bị che khỏi hàm mất mát — chúng vẫn tốn tính toán
> ở lượt truyền xuôi nên đưa vào là đúng, nhưng con số này **không** phải "token có
> tín hiệu huấn luyện mỗi giây"; (b) `train_runtime` gồm cả hai lần eval (≈ 42 s mỗi
> lần, `:366`), tức thông lượng huấn luyện thuần cao hơn khoảng 0.4 %.

### 5.5 Bảng loss theo mốc bước

`logging_steps = 5` (`train_qlora.py:177`), và log **có** in chuỗi đó: 117 dòng dạng
`{'loss': …, 'grad_norm': …, 'learning_rate': …, 'epoch': …}` xen giữa thanh tiến trình,
từ `:94` (`loss 1.183`, step 5) tới hết. Vài mốc đầu để thấy dạng đường cong:

| step | loss | grad_norm | learning_rate | dòng |
|---:|---:|---:|---:|---|
| 5 | 1.183 | 1.395 | 4.444e-05 | `:94` |
| 10 | 0.9717 | 0.6951 | 1.0e-04 | `:95` |
| 15 | 0.7609 | 0.4246 | 1.556e-04 | `:96` |
| 20 | 0.676 | 0.3893 | 2.0e-04 | `:97` |
| 25 | 0.6033 | 0.343 | 1.999e-04 | `:98` |
| 30 | 0.5537 | 0.3607 | 1.998e-04 | `:99` |

Bốn mốc đầu cho thấy `warmup_ratio = 0.03` hoạt động đúng: learning rate leo từ
4.444e-05 lên đúng 2e-04 ở step 20 (≈ 3 % của 588 bước là 17.6 bước) rồi bắt đầu
giảm theo cosine.

**Không xuất CSV.** Chuỗi đầy đủ nằm lẫn trong dòng thanh tiến trình `tqdm` của log,
phải bóc bằng regex mới dựng được bảng — việc đó chưa làm, và bảng loss theo bước
không phải số liệu mà mục 4.7 cần.

### 5.6 Số bước — nay là SỐ ĐO, không còn là phép suy

| Đại lượng | Giá trị | Nguồn |
|---|---:|---|
| Bước tối ưu tổng, 2 epoch | **588** | `…2122.log:87` — số đo |
| Bước tối ưu mỗi epoch | **294** | `…2122.log:377` (`step 294` tại `epoch 1.00`) — số đo |
| Lượt forward/backward tổng | 4 690 × 2 = **9 380** | tính từ `Num examples` và `Num Epochs` (`:87`), batch = 1 |
| Số lần eval | **2** | `…2122.log:377-378` — hai dòng |
| Số mẫu eval mỗi lần | **64** | `…2122.log:62`, `:80` (`Eval: 64 mau, strategy=epoch`) |

> Bản trước của tài liệu này suy ra `≈ 586` bước bằng phép chia `⌊4 690 ÷ 16⌋ × 2`.
> Số thật là **588**: HF Trainer làm tròn **lên** (`⌈4 690 ÷ 16⌉ = 294`), không làm tròn
> xuống. Chênh 2 bước. Giữ ghi chú này lại vì nó chỉ đúng cách một phép suy hợp lý vẫn
> lệch — và đó là lý do phải ghim log, không ghim suy luận.

---

## 6. KẾT QUẢ ĐÁNH GIÁ — SÁU Ô

Mọi con số ở §6 tính bằng `src/evaluation/metrics.py::aggregate` chạy trực tiếp trên các file `finetune/results/results_*_ft06b-*.json` và `data/evaluation/results_*.json` — **không chép từ bảng viết sẵn**, kể cả từ `ft06b_matrix.md`.

Nguồn ngữ cảnh (trường `replay.nguon` / `replay.src_file` của từng file kết quả):

| Cột | File nguồn | sha256 |
|---|---|---|
| GraphRAG (ô 1, 3, 5) | `data/evaluation/results_graphrag_final1_20260729-022916.json` | `7deda57ef145b8a779483a2132cd1d929dc6244807bf7a113bd29f6c1092b7f8` |
| Naive RAG (ô 2, 4, 6) | `data/evaluation/results_baseline_20260710-085236.json` | `37fca8d026443e4cfc5f759f6f98712f638468a58d9a177adbd01dba30bcb38c` |

Hai mẻ khác nhau, có chủ ý — lý do ở §0 (đầu tài liệu) và `ft06b_matrix.md` đầu file.

### 6.1 Ma trận đầy đủ

| Ô | Mô hình sinh | Hệ truy hồi | N | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng | Δ (F1 Khoản) |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| — | Gemini 2.5 Pro | Naive RAG | 4 ⚠️ | 0.435819 ± 0.008 | 0.458698 ± 0.008 | 0.585158 ± 0.008 | 0.785714 (11/14) | |
| — | Gemini 2.5 Pro | GraphRAG | 3 | **0.617136 ± 0.001** | 0.637692 ± 0.003 | 0.828873 ± 0.006 | 0.928571 (13/14) | **+0.181317** |
| 6 | Cục bộ gốc, 0-shot | Naive RAG | 1 | 0.153771 | 0.170195 | 0.264599 | 0.928571 (13/14) | |
| 5 | Cục bộ gốc, 0-shot | GraphRAG | 1 | 0.131387 | 0.131387 | 0.133820 | 0.928571 (13/14) | **−0.022384** |
| 4 | Cục bộ gốc, 2-shot | Naive RAG | 1 | 0.239092 | 0.315247 | 0.599148 | 0.500000 (7/14) | |
| 3 | Cục bộ gốc, 2-shot | GraphRAG | 1 | **0.510879** | 0.561974 | 0.655718 | 0.857143 (12/14) | **+0.271788** |
| 2 | Cục bộ đã tinh chỉnh, 0-shot | Naive RAG | 1 | 0.300765 | 0.344317 | 0.609489 | 0.571429 (8/14) | |
| 1 | Cục bộ đã tinh chỉnh, 0-shot | GraphRAG | 1 | **0.401703** | 0.448905 | 0.566910 | 0.928571 (13/14) | **+0.100938** |

*Sáu hàng cục bộ khớp `finetune/reports/ft06b_matrix.md` §1 tới ba chữ số thập phân (bảng đó làm tròn: 0.402 / 0.301 / 0.511 / 0.239 / 0.131 / 0.154).*

**Hàng Gemini · GraphRAG — ba mẻ, giá trị lẻ** (`aggregate` trên từng file):

| Mẻ | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng |
|---|---:|---:|---:|---:|
| `results_graphrag_final1_20260729-022916.json` | 0.616235 | 0.639367 | 0.827251 | 0.928571 (13/14) |
| `results_graphrag_final2_20260729-032225.json` | 0.617178 | 0.634488 | 0.835766 | 0.928571 (13/14) |
| `results_graphrag_final3_20260729-041450.json` | 0.617996 | 0.639222 | 0.823601 | 0.928571 (13/14) |
| **trung bình ± σ mẫu** | **0.617136 ± 0.001** | **0.637692 ± 0.003** | **0.828873 ± 0.006** | 0.928571 ± 0.000 |

Ba mẻ này là **ba lần SINH trên cùng một ngữ cảnh đông cứng** (`context` trùng khít 137/137 — `kaggle_ft06.py:125-131`), nên σ ở đây đo đúng một thứ: dao động của mô hình sinh, không lẫn dao động của truy hồi. σ là **độ lệch chuẩn MẪU** (`statistics.stdev`, chia n−1); `docs/V3_RESULTS.md` §2 dùng độ lệch chuẩn tổng thể (chia n) nên chữ số cuối lệch — NormR 0.006 ở đây so với 0.005 ở đó. Cùng dữ liệu, khác quy ước.

**Hàng Gemini · Naive RAG — bốn mẻ đủ 137 câu:**

| Mẻ | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng |
|---|---:|---:|---:|---:|
| `results_baseline_20260709-073933.json` | 0.438149 | 0.456647 | 0.577251 | 0.785714 (11/14) |
| `results_baseline_20260710-001154.json` | 0.432507 | 0.464022 | 0.580900 | 0.785714 (11/14) |
| `results_baseline_20260710-085236.json` | 0.426975 | 0.448386 | 0.594282 | 0.785714 (11/14) |
| `results_baseline_20260710-104109.json` | 0.445645 | 0.465736 | 0.588200 | 0.785714 (11/14) |
| **trung bình ± σ mẫu** | **0.435819 ± 0.008** | **0.458698 ± 0.008** | **0.585158 ± 0.008** | 0.785714 ± 0.000 |

> ### ⚠️ HÀNG NAIVE RAG PHẢI ĐƯỢC XÁC NHẬN TRƯỚC KHI VÀO KHOÁ LUẬN
>
> `docs/V3_RESULTS.md` §3 viết *"trung bình từng câu qua cả **3 mẻ của mỗi hệ**"* nhưng
> **không ghi ba mẻ baseline nào**. Chặng `table` KHÔNG tự chọn ba mẻ — nó lọc theo số
> câu (137), và phép lọc đó ra **4** mẻ chứ không phải 3. Nếu ba mẻ đúng là ba trong số
> đó thì mẫu số của Δ và của cột tỉ lệ sẽ đổi. **Người phụ trách phải chỉ đúng ba mẻ.**
> Ký hiệu ⚠️ ở cột N của hàng đó nhắc lại đúng điều này. Chi tiết + toàn bộ 13 mẻ
> baseline tìm được: `ft06b_matrix.md` §1.4.

**Cơ sở của Δ và của cột tỉ lệ — MỘT cơ sở duy nhất cho mọi hàng:** `aggregate.f1_mean`
tính trên **toàn bộ 137 câu** của file kết quả, gồm cả 14 câu phủ định. Hàng Gemini lấy
trung bình `f1_mean` của các mẻ **rồi mới** trừ/chia. Chọn cơ sở này vì đó là đại lượng
mà cả sáu ô cục bộ đều có sẵn — không phải vì nó tốt hơn cơ sở 123 câu ghép cặp. Muốn
đổi sang cơ sở ghép cặp thì phải đổi cho **cả bảng** (`ft06b_matrix.md` §1.1). Mức ý
nghĩa thống kê (+0.187, CI [0.108, 0.264], p = 0.00003) chỉ tồn tại ở cơ sở ghép cặp —
xem §0 mục 1.

**Precision / Recall tách riêng** (cấp Khoản, từ `aggregate`):

| Ô | precision_mean | recall_mean | f1_mean | precision_dieu | recall_dieu | f1_dieu |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.435523 | 0.401460 | 0.401703 | 0.490268 | 0.444647 | 0.448905 |
| 2 | 0.333333 | 0.340511 | 0.300765 | 0.388078 | 0.382117 | 0.344317 |
| 3 | 0.557664 | 0.524574 | 0.510879 | 0.611192 | 0.574453 | 0.561974 |
| 4 | 0.267397 | 0.290024 | 0.239092 | 0.350122 | 0.366058 | 0.315247 |
| 5 | 0.135036 | 0.138686 | 0.131387 | 0.135036 | 0.138686 | 0.131387 |
| 6 | 0.151460 | 0.177616 | 0.153771 | 0.167275 | 0.195864 | 0.170195 |
| Gemini graphrag (`final1`) | 0.600878 | 0.702798 | 0.616235 | 0.621802 | 0.731387 | 0.639367 |
| Gemini naive (`085236`) | 0.433484 | 0.513139 | 0.426975 | 0.452340 | 0.539294 | 0.448386 |

*(Hai hàng Gemini in giá trị của **một** mẻ để đối chiếu được với file; hàng của bảng §6.1 là trung bình nhiều mẻ.)*

> **Cảnh báo khi trình bày precision** (`docs/V3_RESULTS.md` §2): `metrics.py` tính `precision = 0` khi hệ không đưa ra trích dẫn nào — quy ước mặc định của scikit-learn. Naive RAG bỏ trống 31/123 câu còn GraphRAG chỉ 5/123, nên quy ước này **phạt baseline nặng hơn**. F1 không bị ảnh hưởng. **Lấy F1 làm thang so sánh, đừng xây lập luận trên precision.**

### 6.2 Sức khoẻ từng ô

| Ô | Mô hình | n_shot | Hệ | `format_ok_rate` | **mẫu số** | `format_ok` đếm | `n_hit_token_cap` | `soft_article_hit` | Qua mô hình / tổng | Sao chép hằng số | `total_elapsed_s` | Card |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ft | 0 | graphrag | **0.756098** | **123** | 93 | 0 | 0.980351 | **127/137** | 10 | 1 656.88 | 0 |
| 2 | ft | 0 | baseline | **0.894309** | **123** | 110 | **1** (`V020`) | 0.965290 | **137/137** | 0 | 1 229.49 | 0 |
| 3 | base | 2 | graphrag | **0.853659** | **123** | 105 | 0 | 1.000000 | **127/137** | 10 | 2 393.09 | 0 |
| 4 | base | 2 | baseline | **0.894309** | **123** | 110 | 0 | 0.945519 | **137/137** | 0 | 1 412.73 | 1 |
| 5 | base | 0 | graphrag | **0.065041** | **123** | 8 | 0 | 0.991437 | **127/137** | 10 | 2 879.36 | 1 |
| 6 | base | 0 | baseline | **0.211382** | **123** | 26 | 0 | 0.927839 | **137/137** | 0 | 1 742.01 | 1 |

Tổng `total_elapsed_s` sáu ô = **11 313.56 s ≈ 3 giờ 8 phút** (hai luồng song song, nên thời gian tường thấp hơn).

- **Mẫu số `format_ok_rate` là 123 ở cả sáu ô** — số câu có `ground_truth_citations` khác rỗng (`FINETUNE_EXECUTION_PLAN.md` §3.1 và §9.4).
- 10 câu sao chép hằng số của cột GraphRAG: **V106, V107, V108, V109, V110, V111, V112, V113, V115, V116** (`frozen_copy = true`, `elapsed_seconds = 0.0`) — giống hệt ở cả ba ô GraphRAG.
- `soft_article_hit` mẫu số (số cụm bắt được) và số câu có nhắc: ô 1 = 343 cụm / 95 câu; ô 2 = 417 / 117; ô 3 = 519 / 114; ô 4 = 501 / 123; ô 5 = 420 / 114; ô 6 = 413 / 121 (khoá `soft_article_mentions_tong`, `soft_article_hit_do_duoc`).

**Prompt token đo được mỗi ô:**

| Ô | tự đếm min | tự đếm max | backend min | backend max | `prompt_len_lech` (mọi câu) |
|---:|---:|---:|---:|---:|---:|
| 1 | 5 368 | 12 033 | 5 346 | 12 011 | 22 |
| 2 | 5 471 | 6 454 | 5 449 | 6 432 | 22 |
| 3 | 5 780 | 12 445 | 5 724 | 12 389 | 56 |
| 4 | 5 883 | 6 866 | 5 827 | 6 810 | 56 |
| 5 | 5 368 | 12 033 | 5 346 | 12 011 | 22 |
| 6 | 5 471 | 6 454 | 5 449 | 6 432 | 22 |

`prompt_len_lech` **bất biến trong từng ô** (một giá trị duy nhất): 22 ở mọi cấu hình 0-shot, 56 ở mọi cấu hình 2-shot. Chênh 2-shot − 0-shot = **34** token ở cả hai khuôn.

*Ba ô GraphRAG có prompt **ngắn nhất** đi từ 5 429 (lượt trước) xuống 5 368 token: đó là hệ quả trực tiếp của việc đổi nguồn ngữ cảnh — 17 câu nhận ngữ cảnh khác. Cột Naive không đổi một token nào, đúng như dự đoán ở §0.*

**Câu trả lời sai ở cột "Từ chối đúng":**

| Ô | Số đúng | id trả lời sai |
|---:|---:|---|
| 1 | 13/14 | `V105` |
| 2 | 8/14 | `V005`, `V105`, `V107`, `V109`, `V113`, `V115` |
| 3 | 12/14 | `V005`, `V105` |
| 4 | 7/14 | `V005`, `V105`, `V107`, `V109`, `V113`, `V115`, `V116` |
| 5 | 13/14 | `V105` |
| 6 | 13/14 | `V107` |
| Gemini graphrag (`final1`) | 13/14 | `V005` |
| Gemini baseline (`085236`) | 11/14 | `V005`, `V107`, `V116` |

**Độ trễ mỗi câu** (`ft06b_matrix.md` §4; tính lại khớp — trung bình `elapsed_seconds` **chỉ trên câu đi qua mô hình**, loại 10 câu hằng số):

| Cặp ô | GraphRAG s/câu | Naive s/câu | Lệch | Card | Cảnh báo |
|---|---:|---:|---:|---|---|
| ô 1 + 2 · ft 0-shot | 13.046307 | 8.974372 | 45 % | 0 vs 0 | cùng card |
| ô 3 + 4 · base 2-shot | 18.843228 | 10.311934 | 83 % | 0 vs 1 | ⚠️ vượt ngưỡng 25 % trên hai card khác nhau |
| ô 5 + 6 · base 0-shot | 22.672134 | 12.715372 | 78 % | 1 vs 1 | cùng card |

`latency_mean_s` từ `aggregate` (tính trên **cả 137 câu**, gồm 10 câu `elapsed = 0.0`): ô 1 = 12.094022 · ô 2 = 8.974372 · ô 3 = 17.467810 · ô 4 = 10.311934 · ô 5 = 21.017234 · ô 6 = 12.715372.
`latency_p95_s`: ô 1 = 20.367 · ô 2 = 16.157 · ô 3 = 41.28 · ô 4 = 19.314 · ô 5 = 42.135 · ô 6 = 24.401.

*Cảnh báo 83 % ở cặp 3+4 là **dương tính giả**: hai cặp chạy trên cùng một card lệch 45 % và 78 %, tức 83 % nằm trong dải quan sát được ngay trên một card. Ngưỡng 25 % đặt sai — lập luận đầy đủ ở Phần B §7.2.*

### 6.3 Tỉ lệ Δ TƯƠNG ĐỐI (GraphRAG / Naive), 3 chữ số thập phân

Tính từ giá trị `aggregate` chưa làm tròn.

| Hàng | F1 Khoản G / N | **Tỉ lệ F1 Khoản** | Tỉ lệ F1 Điều | Tỉ lệ NormR |
|---|---|---:|---:|---:|
| Gemini 2.5 Pro | 0.617136 / 0.435819 | **1.416** | 1.390 | 1.417 |
| Cục bộ đã tinh chỉnh, 0-shot | 0.401703 / 0.300765 | **1.336** | 1.304 | 0.930 |
| Cục bộ gốc, 2-shot | 0.510879 / 0.239092 | **2.137** | 1.783 | 1.094 |
| Cục bộ gốc, 0-shot | 0.131387 / 0.153771 | **0.854** | 0.772 | 0.506 |

Δ tuyệt đối tương ứng:

| Hàng | Δ F1 Khoản | Δ F1 Điều | Δ NormR |
|---|---:|---:|---:|
| Gemini 2.5 Pro | +0.181317 | +0.178994 | +0.243715 |
| Cục bộ đã tinh chỉnh, 0-shot | +0.100938 | +0.104588 | **−0.042579** |
| Cục bộ gốc, 2-shot | +0.271788 | +0.246727 | +0.056569 |
| Cục bộ gốc, 0-shot | **−0.022384** | **−0.038808** | **−0.130779** |

**Cách đọc cột tỉ lệ.** Δ dương ở ba trên bốn hàng, và hàng thứ tư (gốc 0-shot) là hiệu
ứng sàn chứ không phải phản chứng — `format_ok_rate` của ô đó chỉ **0.065**, tức 8 trên
123 câu phân tích được, thang đo không còn phân giải. Hàng **gốc 2-shot có tỉ lệ cao
nhất (2.137)**; đọc con số đó phải kèm cảnh báo: **mẫu số của nó rất thấp (0.239092)**
nên tỉ lệ nhạy với nhiễu — một thay đổi nhỏ ở mẫu số kéo tỉ lệ đi rất xa. Không được
diễn giải nó thành *"mô hình yếu hưởng lợi nhiều hơn"*. Lập luận đầy đủ ở Phần B §7.4.

### 6.4 Phân tách theo `gap_type` và `theme` — ô 1 và ô 3

**Ô 1 — ft, 0-shot, GraphRAG** (`aggregate.by_gap` / `by_theme` trên `results_graphrag_ft06b-ft-s0.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.432292 | 0.476042 | 0.703125 |
| gap2 | 31 | 0.247312 | 0.268817 | 0.467742 |
| gap3 | 30 | 0.335556 | 0.368889 | 0.400000 |
| gap4 | 30 | 0.348889 | 0.462222 | 0.522222 |
| negative | 14 | 0.928571 | 0.928571 | 0.928571 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.349180 | 0.519126 |
| ho-tich | 39 | 0.444444 | 0.602564 |
| nuoi-con-nuoi | 29 | 0.324138 | 0.534483 |
| `None` | 8 | 0.875000 | 0.875000 |

**Ô 3 — base, 2-shot, GraphRAG** (`results_graphrag_ft06b-base-s2.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.505208 | 0.598958 | 0.828125 |
| gap2 | 31 | 0.594163 | 0.594163 | 0.629032 |
| gap3 | 30 | 0.336825 | 0.370159 | 0.461111 |
| gap4 | 30 | 0.443333 | 0.543333 | 0.600000 |
| negative | 14 | 0.857143 | 0.857143 | 0.857143 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.485636 | 0.603825 |
| ho-tich | 39 | 0.624786 | 0.743590 |
| nuoi-con-nuoi | 29 | 0.310345 | 0.586207 |
| `None` | 8 | 0.875000 | 0.875000 |

**Đối chiếu — hàng Gemini, ĐÚNG file cấp ngữ cảnh cho ba ô GraphRAG** (`aggregate` trên `data/evaluation/results_graphrag_final1_20260729-022916.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.533408 | 0.581399 | 0.859375 |
| gap2 | 31 | 0.667775 | 0.667775 | 0.838710 |
| gap3 | 30 | 0.540904 | 0.584238 | 0.805556 |
| gap4 | 30 | 0.580899 | 0.592011 | 0.755556 |
| negative | 14 | 0.928571 | 0.928571 | 0.928571 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.593019 | 0.759563 |
| ho-tich | 39 | 0.729630 | 0.935897 |
| nuoi-con-nuoi | 29 | 0.406705 | 0.775862 |
| `None` | 8 | 1.000000 | 1.000000 |

*Đây là **một mẻ** (`final1`); `docs/V3_RESULTS.md` §4 và §5 báo trung bình ba mẻ nên chữ số lẻ lệch chút — vd `V3_RESULTS.md` §4 ghi gap2 0.667 (ở đây 0.667775), §5 ghi ho-tich 0.707 (ở đây 0.729630, mẻ `final1` cao hơn trung bình). Cùng dữ liệu, khác số mẻ.*

**Và hàng Gemini · Naive RAG, đúng file cấp ngữ cảnh cho ba ô Naive** (`results_baseline_20260710-085236.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.489732 | 0.518899 | 0.750000 |
| gap2 | 31 | 0.404455 | 0.468971 | 0.612903 |
| gap3 | 30 | 0.366044 | 0.366044 | 0.469444 |
| gap4 | 30 | 0.276825 | 0.276825 | 0.444444 |
| negative | 14 | 0.785714 | 0.785714 | 0.785714 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.340581 | 0.547814 |
| ho-tich | 39 | 0.489361 | 0.615385 |
| nuoi-con-nuoi | 29 | 0.401209 | 0.586207 |
| `None` | 8 | 0.875000 | 0.875000 |

Nhóm `theme = None` (8 câu) là phần con của 14 câu negative — nhóm negative có 14 câu, trong đó 6 câu vẫn mang `theme` cụ thể.

### 6.5 Câu chạm trần token

| id | Ô | Mô hình · n_shot · hệ | `n_tokens_out` | `n_tokens_prompt` (tự đếm) | `n_tokens_prompt_backend` | Độ dài `answer` |
|---|---:|---|---:|---:|---:|---:|
| **V020** | **2** | ft · 0-shot · baseline | **2 048** (= `max_new_tokens`) | 6 082 | 6 060 | **6 276 ký tự** |

Đây là **câu duy nhất** chạm trần trong toàn bộ 822 lượt sinh: năm ô còn lại đều có `n_hit_token_cap = 0` và `ids_hit_token_cap = []`. Nguồn: trường `hit_token_cap` của từng item + khoá `replay.ids_hit_token_cap`; cảnh báo in ở `finetune/reports/ft06b_matrix.md` §2 và `finetune/logs/ft06b_gpu0.log`.

*V020 thuộc **cột Naive**, mà cột đó không đổi nguồn ngữ cảnh — nên đây đúng là cùng một ca đã gặp ở lượt trước, không phải ca mới.*

---

## 7. ĐỐI CHIẾU BA PHIÊN

| Hàng | Phiên 1 — cổng FT-03 | Phiên 2 — huấn luyện FT-05 | Phiên 3 — đánh giá FT-06 |
|---|---|---|---|
| Ngày | 29/07/2026 | 29/07/2026 *(suy từ `RUN_NAME` = `ft04-5k-2ep-20260729-2122`)* | 30/07/2026 |
| Nền | Kaggle | RunPod Community Cloud | Kaggle Notebooks |
| Mô hình | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (bartowski) | huấn luyện từ **`unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit`** (Unsloth chuyển hướng từ tên `unsloth/Qwen3-4B-Instruct-2507` truyền vào CLI — §0 mục 3) | base GGUF (bartowski) **+** `ft04-5k-2ep-20260729-2122-Q4_K_M.gguf` |
| Số câu | **15** (`finetune/data/gate_ids.json`) | — (4 690 mẫu train / 64 mẫu val) | **137** × 6 ô = **822 lượt** |
| Số ô | 4 (2 × 2) | 1 lần chạy | 6 |
| Phần cứng | Kaggle GPU — **loại card KHÔNG CÓ TRONG REPO** (`gate_base_model.md` chỉ ghi "Kaggle") | **NVIDIA GeForce RTX 4090 · sm89 · 1 card · 23.516 GB** (`…2122.log:39`, `:41`) | **Tesla T4 × 2**, 15 360 MiB mỗi card |
| Commit code | `eecdc7b7dc533f2c564d74e795704fb4dcbb81a2` **+ bản vá ngoài git** | **KHÔNG CÓ TRONG REPO** — log không in commit hash | `2a712adf7707164b7302afa42cf98ea06c99b417` |
| Thời gian chạy | **KHÔNG CÓ TRONG REPO** | chặng `train` **19 480 s = 5 giờ 24 phút 40 giây** (`…2122.log:370`); tổng bảy chặng không có | 11 313.56 s tổng sáu ô (2 luồng song song) |
| Kết quả lưu ở | `finetune/reports/gate_base_model.md` (**4 file results JSON KHÔNG CÓ TRONG REPO**) | `finetune/logs/ft04-5k-2ep-20260729-2122.log` (`train_result.json` vẫn không có) | 6 file `finetune/results/results_*_ft06b-*.json` |

### 7.1 Tám tham số sinh — từng phiên

| # | Tham số | Phiên 1 (4 ô) | Phiên 2 (huấn luyện) | Phiên 3 (6 ô) | Khác nhau? |
|---:|---|---|---|---|---|
| 1 | `temperature` | 0.7 | không áp dụng | 0.7 | — |
| 2 | `top_p` | 0.8 | không áp dụng | 0.8 | — |
| 3 | `top_k` | 20 | không áp dụng | 20 | — |
| 4 | `min_p` | 0.0 | không áp dụng | 0.0 | — |
| 5 | `presence_penalty` | **1.0 ở 2 ô · 0 ở 2 ô** (đây là trục thí nghiệm) | không áp dụng | **0 ở cả 6 ô** | ⚠️ **KHÁC** — phiên 1 quét hai giá trị để chốt; phiên 3 dùng giá trị đã chốt |
| 6 | `seed` | 42 | 42 (`train_qlora.py:67`, `:180`, `:247`) | 42 | — |
| 7 | `max_new_tokens` | 2 048 | không áp dụng | 2 048 | — |
| 8 | `n_ctx` | 16 384 | (`max_seq_length` = 16 384, xác nhận `…2122.log:57` `limit 16,384`) | 16 384 | — |
| + | `n_gpu_layers` | **KHÔNG CÓ TRONG REPO** (không ghi ở `gate_base_model.md`) | không áp dụng | **−1** (mọi layer lên GPU) | ⚠️ không đối chiếu được |
| + | `greedy` | `false` (suy từ temperature 0.7) | không áp dụng | `false` (khoá `gen_params.greedy`) | — |

Nguồn: phiên 1 — `finetune/reports/gate_base_model.md` dòng 4 và §1, §3; phiên 3 — khoá `replay.gen_params` của cả sáu file results, trùng khít nhau từng giá trị:

```json
{"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0,
 "presence_penalty": 0.0, "seed": 42, "max_new_tokens": 2048, "greedy": false}
```

Kèm `n_ctx = 16384`, `include_schema_b = false`, `prompt_builder = "build_messages"` — cũng giống hệt ở cả sáu ô.

Trong phiên 3, **chỉ hai giá trị khác nhau giữa các ô**: `model` (base / ft) và `n_shot` (0 / 2).

### 7.2 Độ dài prompt 2-shot: phiên 1 so với phiên 3 — KHÔNG đối chiếu được ở cấp câu

| Nguồn | Đại lượng | 0-shot | 2-shot | Chênh |
|---|---|---:|---:|---:|
| Phiên 1 — `gate_base_model.md` §1 | **prompt max** trên 15 câu, khuôn GraphRAG | **11 211** | **11 623** | **412** |
| Phiên 3 — cổng chặn B, `results_graphrag_ft06b-gate-prompt-s{0,2}.json` | prompt của **câu V001**, khuôn GraphRAG | **10 144** | **10 556** | **412** |
| Phiên 3 — cổng chặn B, khuôn baseline | prompt của câu V001 | **6 182** | **6 594** | **412** |
| Phiên 3 — ô 1 / ô 5 và ô 3, `finetune/logs/ft06b_gpu{0,1}.log` | prompt của câu V001 trong lần chạy đủ 137 câu | **10 144** | **10 556** | **412** |

**Kết luận của phép kiểm:**

1. **KHÔNG so được trực tiếp.** Phiên 1 chỉ ghi lại **giá trị lớn nhất trên bộ 15 câu**, phiên 3 ghi giá trị **của câu V001**. Bốn file results JSON của phiên 1 — nguồn duy nhất có độ dài prompt từng câu — **KHÔNG CÓ TRONG REPO** (`finetune/results/` chỉ chứa file `ft06-*` và `ft06b-*`; đã kiểm toàn bộ thư mục). Không có file dump prompt của phiên 1 (`prompt_gate-s0-pp10.txt`, `prompt_gate-s2-pp10.txt` nêu ở `gate_base_model.md` §5 và `finetune/README.md`) trong repo.
2. **Cái so được, và nó khớp:** phụ trội của việc thêm hai cặp ví dụ là **đúng 412 token** ở cả ba phép đo độc lập — phiên 1 (trên giá trị max), phiên 3 khuôn GraphRAG, phiên 3 khuôn baseline. Cùng với `prompt_len_lech` bất biến 22 (0-shot) và 56 (2-shot) ở cả hai phiên (`gate_base_model.md` §5 mục 3 ghi đúng 22 và 56), đây là bằng chứng khuôn prompt không đổi giữa hai phiên. *(Con số 412 và 34 là phép trừ trên các giá trị đã đọc từ file, không phải số đọc trực tiếp.)*
3. Con số **10 556** mà `docs/FT_SYNTHESIS_B_KHOKHAN.md:509-512` mô tả là "trùng khít con số của phiên cổng FT-03" **không đối chiếu được** với `gate_base_model.md`, vì báo cáo đó chỉ ghi 11 623 (max). Chỗ này cần một nguồn khác nếu muốn phát biểu trong khoá luận.

---

## 8. ĐỐI CHIẾU VỚI BẢNG 4.5 CỦA KHÓA LUẬN

**Bảng 4.5 (bốn hệ tham chiếu) — KHÔNG CÓ TRONG REPO ở dạng bốn thang đo đầy đủ.**
Đã tìm ở: `docs/` (không có thư mục `docs/thesis/` — `ls docs/thesis` → không tồn tại), `thesis/` (thư mục rỗng), `docs/V2_RESULTS.md`, `docs/PROJECT_STATUS.md`, `docs/EVALUATION_ARCHITECTURE.md`, `CLAUDE.md`. Bản khoá luận `baocao.docx` nằm **ngoài repo** (`../baocao.docx`).

**Bốn thang đo đầy đủ cho hai hệ GraphRAG và Naive RAG** — tính lại bằng `aggregate` trên chính hai file cấp ngữ cảnh cho sáu ô:

| Hệ (Gemini 2.5 Pro) | Mẻ | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng |
|---|---|---:|---:|---:|---:|
| GraphRAG | `results_graphrag_final1_20260729-022916.json` | **0.616235** | **0.639367** | **0.827251** | **0.928571 (13/14)** |
| Naive RAG | `results_baseline_20260710-085236.json` | **0.426975** | **0.448386** | **0.594282** | **0.785714 (11/14)** |

Nếu Bảng 4.13 cần giá trị trung bình nhiều mẻ (khớp hàng Gemini của ma trận §6.1):
GraphRAG **0.617136 ± 0.001 / 0.637692 ± 0.003 / 0.828873 ± 0.006 / 13-14** (N=3) ·
Naive RAG **0.435819 ± 0.008 / 0.458698 ± 0.008 / 0.585158 ± 0.008 / 11-14** (N=4 ⚠️, xem cảnh báo §6.1).

Số phụ của hai file: `total_elapsed_s` graphrag `final1` = 722.23 (chạy song song nên thấp hơn tổng `elapsed_seconds` 3 526.30) · baseline 3 440.7; `latency_mean_s` graphrag 25.739416 · baseline 25.113504; số câu có GT khác rỗng = **123** ở cả hai; số câu trong 123 đó thực sự sinh ra ≥ 1 citation: graphrag **117**, baseline **92**.

**Ba bậc còn lại của bậc thang — chỉ có ở bộ số v2, CHƯA chạy lại sau khi sửa lỗi phân loại địa phương** (`docs/V2_RESULTS.md` §2; `docs/V3_RESULTS.md` §7.1 vẫn dùng cùng giá trị đó):

| Hệ | F1 Khoản | NormR | F1 Điều | Từ chối đúng |
|---|---:|---:|---:|---:|
| oracle (trần) | 0.858 | 0.955 | KHÔNG CÓ | KHÔNG CÓ |
| bm25 | 0.571 | 0.808 | KHÔNG CÓ | KHÔNG CÓ |
| closed-book | 0.102 | 0.102 | KHÔNG CÓ | KHÔNG CÓ |

> **Ba bậc này KHÔNG so trực tiếp được với hai hàng trên.** Chúng đo trên mẻ v1/v2, còn hai hàng trên là mẻ v3 (sau khi sửa `query_planner`). Lỗi đã sửa nằm trong `query_planner`, mà `bm25` / `closed-book` / `oracle` không đi qua tầng đó — nên **kỳ vọng** chúng không đổi, nhưng **kỳ vọng không phải số đo**. Nếu Bảng 4.13 xếp cả năm hệ cạnh nhau thì phải hoặc chạy lại ba bậc này, hoặc ghi chú rõ chúng thuộc mẻ khác.
>
> **Oracle / BM25 / closed-book cũng KHÔNG CÓ F1 Điều và Từ chối đúng trong repo.** Hai cột đó phải lấy từ **Bảng 4.5 của `baocao.docx`**, hoặc tính lại từ results JSON của mẻ v1 nếu file còn trong `data/evaluation/`.

---

## 9. BẢNG SỐ SẴN DÙNG

Mỗi dòng một con số. Cột "Nguồn" là file đọc ra nó.

### 9.1 Ma trận sáu ô

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 0.402 | F1 Khoản — ft, 0-shot, GraphRAG (ô 1) | `finetune/results/results_graphrag_ft06b-ft-s0.json` → `aggregate.f1_mean` |
| 0.449 | F1 Điều — ô 1 | như trên, `f1_dieu_mean` |
| 0.567 | Norm Recall — ô 1 | như trên, `norm_recall_mean` |
| 13/14 = 0.929 | Từ chối đúng — ô 1 | như trên, `negative_correct_rate` |
| 0.301 | F1 Khoản — ft, 0-shot, Naive (ô 2) | `finetune/results/results_baseline_ft06b-ft-s0.json` |
| 0.344 | F1 Điều — ô 2 | như trên |
| 0.609 | Norm Recall — ô 2 | như trên |
| 8/14 = 0.571 | Từ chối đúng — ô 2 | như trên |
| 0.511 | F1 Khoản — base, 2-shot, GraphRAG (ô 3) | `finetune/results/results_graphrag_ft06b-base-s2.json` |
| 0.562 | F1 Điều — ô 3 | như trên |
| 0.656 | Norm Recall — ô 3 | như trên |
| 12/14 = 0.857 | Từ chối đúng — ô 3 | như trên |
| 0.239 | F1 Khoản — base, 2-shot, Naive (ô 4) | `finetune/results/results_baseline_ft06b-base-s2.json` |
| 0.315 | F1 Điều — ô 4 | như trên |
| 0.599 | Norm Recall — ô 4 | như trên |
| 7/14 = 0.500 | Từ chối đúng — ô 4 | như trên |
| 0.131 | F1 Khoản — base, 0-shot, GraphRAG (ô 5) | `finetune/results/results_graphrag_ft06b-base-s0.json` |
| 0.131 | F1 Điều — ô 5 | như trên |
| 0.134 | Norm Recall — ô 5 | như trên |
| 13/14 = 0.929 | Từ chối đúng — ô 5 | như trên |
| 0.154 | F1 Khoản — base, 0-shot, Naive (ô 6) | `finetune/results/results_baseline_ft06b-base-s0.json` |
| 0.170 | F1 Điều — ô 6 | như trên |
| 0.265 | Norm Recall — ô 6 | như trên |
| 13/14 = 0.929 | Từ chối đúng — ô 6 | như trên |

### 9.2 Cột Δ và tỉ lệ tương đối

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| +0.101 | Δ F1 Khoản — hàng ft 0-shot | ô 1 − ô 2 |
| +0.272 | Δ F1 Khoản — hàng base 2-shot | ô 3 − ô 4 |
| −0.022 | Δ F1 Khoản — hàng base 0-shot | ô 5 − ô 6 |
| +0.181 | Δ F1 Khoản — hàng Gemini (**cơ sở aggregate 137 câu**, dùng cho ma trận) | 0.617136 − 0.435819 |
| +0.187 | Δ F1 Khoản — hàng Gemini (**cơ sở ghép cặp 123 câu**, có mức ý nghĩa) | `docs/V3_RESULTS.md` §3 |
| 1.336 | Tỉ lệ GraphRAG/Naive — hàng ft 0-shot | tính từ ô 1 / ô 2 |
| 2.137 | Tỉ lệ GraphRAG/Naive — hàng base 2-shot (**mẫu số thấp → nhạy nhiễu**) | ô 3 / ô 4 |
| 0.854 | Tỉ lệ GraphRAG/Naive — hàng base 0-shot (**hiệu ứng sàn**) | ô 5 / ô 6 |
| 1.416 | Tỉ lệ GraphRAG/Naive — Gemini | 0.617136 / 0.435819 |
| −0.043 | Δ Norm Recall — hàng ft 0-shot (**âm**) | ô 1 − ô 2 |
| −0.109 | Δ F1 Khoản: ft 0-shot GraphRAG so với base 2-shot GraphRAG (**tinh chỉnh thua**) | 0.401703 − 0.510879 |

### 9.3 Sức khoẻ và mẫu số

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 137 | Tổng số câu bộ test `test_set_v2.json` | mọi file results, `aggregate.count` |
| 127 | Số câu **đi qua mô hình sinh** ở cột GraphRAG | `replay.n_qua_mo_hinh` (ô 1, 3, 5) |
| 137 | Số câu đi qua mô hình sinh ở cột Naive | `replay.n_qua_mo_hinh` (ô 2, 4, 6) |
| 10 | Số câu **sao chép hằng số** ở cột GraphRAG | `replay.n_sao_chep_hang_so`; ids `V106`–`V113`, `V115`, `V116` |
| 123 | **Mẫu số của `format_ok_rate`** ở cả sáu ô | `replay.format_ok_mau_so` |
| 14 | Số câu `gap_type = negative` (mẫu số cột Từ chối đúng) | `aggregate.negative_count` |
| 4 | Số câu negative thực sự đi qua mô hình sinh ở cột GraphRAG | 14 − 10, `dataset_stats.md` §4.2 |
| 822 | Tổng lượt sinh (6 ô × 137) | `FINETUNE_EXECUTION_PLAN.md:635` |
| 0.065 | `format_ok_rate` thấp nhất (ô 5) | `results_graphrag_ft06b-base-s0.json` |
| 0.894 | `format_ok_rate` cao nhất (ô 2 và ô 4) | hai file baseline tương ứng |
| 0.756 | `format_ok_rate` ô 1 | `results_graphrag_ft06b-ft-s0.json` |
| 0.854 | `format_ok_rate` ô 3 | `results_graphrag_ft06b-base-s2.json` |
| 1.000 | `soft_article_hit` ô 3 (giá trị cao nhất) | như trên |
| 0.928 | `soft_article_hit` ô 6 (giá trị thấp nhất) | `results_baseline_ft06b-base-s0.json` |
| 1 | Số câu chạm trần token trong 822 lượt (`V020`, ô 2) | `replay.ids_hit_token_cap` |
| 2 048 | `n_tokens_out` của `V020` = `max_new_tokens` | item `V020` trong `results_baseline_ft06b-ft-s0.json` |
| 11 313.56 s | Tổng `total_elapsed_s` sáu ô ≈ 3 giờ 8 phút | cộng từ sáu file kết quả |

### 9.4 Cấu hình huấn luyện

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 5 000 | Tổng mẫu huấn luyện | `finetune/build_dataset.py:88` |
| 4 690 | Số mẫu train | đếm dòng `finetune/data/train.jsonl` |
| 310 | Số mẫu val | đếm dòng `finetune/data/val.jsonl` |
| 64 | Số mẫu val dùng khi eval mỗi epoch | `finetune/run.sh:287` |
| 450 | Số mẫu từ chối (9.0 %) | `dataset_stats.md` §4 |
| 315 | `refusal_no_basis` | `dataset_stats.md` §4 |
| 135 | `refusal_out_of_scope` | `dataset_stats.md` §4 |
| 2 529 | Mẫu khuôn GraphRAG (50.6 %) | `dataset_stats.md` §3 |
| 2 471 | Mẫu khuôn baseline (49.4 %) | `dataset_stats.md` §3 |
| 16 | LoRA `r` | `finetune/run.sh:290`; `adapter_config.json` → `"r"` |
| 32 | LoRA `alpha` | `finetune/run.sh:291`; `adapter_config.json` → `"lora_alpha"` |
| 0.0 | LoRA dropout | `finetune/train_qlora.py:240`; `adapter_config.json` → `"lora_dropout"` |
| 7 | Số `target_modules` | `finetune/train_qlora.py:243-244`; `adapter_config.json` → `"target_modules"` |
| 36 | Số layer được vá (36 QKV + 36 O + 36 MLP) | `…2122.log:47` |
| 33 030 144 | Tham số huấn luyện được | `…2122.log:90` |
| 4 055 498 240 | Tổng tham số | `…2122.log:90` |
| 0.81 % | Tỉ lệ tham số huấn luyện được | `…2122.log:90` |
| 2e-4 | Learning rate | `finetune/train_qlora.py:62`; xác nhận `…2122.log:97` (đạt đúng 2e-04 sau warmup) |
| 0.03 | `warmup_ratio` | `finetune/train_qlora.py:170` |
| 0.01 | `weight_decay` | `finetune/train_qlora.py:173` |
| 2 | Số epoch | `finetune/run.sh:67`; `…2122.log:87` |
| 588 | Tổng số bước tối ưu (294 mỗi epoch) | `…2122.log:87`, `:377-378` |
| 1 | `per_device_train_batch_size` | `finetune/train_qlora.py:165`; `…2122.log:88` |
| 16 | `gradient_accumulation_steps` (batch hiệu dụng = 16) | `finetune/train_qlora.py:65`; `…2122.log:88-89` |
| 16 384 | `max_seq_length` | `finetune/run.sh:66`; `…2122.log:57` |
| 42 | Seed (dữ liệu, LoRA init, trainer, sinh văn bản) | `build_dataset.py:87`; `train_qlora.py:67`; `replay` `gen_params.seed` |
| 0.4054 | `train_loss` | `…2122.log:370`, `:373` |
| 0.3129 / 0.3082 | `eval_loss` epoch 1 / epoch 2 | `…2122.log:377-378` |
| 1.50 % | Mức cải thiện eval_loss giữa hai epoch | tính từ hai dòng trên |
| 19 480 s | `train_runtime` = 5 giờ 24 phút 40 giây | `…2122.log:370`, `:373` |
| 0.482 / 0.03 | `train_samples_per_second` / `train_steps_per_second` | `…2122.log:370` |
| 3 625.9 tok/s | Thông lượng — **TÍNH LẠI** (log ghi `nan`) | §5.4 |
| 98.5 % | Tỉ lệ token bị che (5 623 / 5 707) | `…2122.log:84` |
| 35 316 237 | `total_tokens` tập train (tokenizer thật) | `…2122.log:59` |
| 466 358 | `total_tokens` tập val 64 mẫu | `…2122.log:72` |
| `unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit` | **Kho mô hình gốc thật đã nạp** | `adapter_config.json` → `base_model_name_or_path` |

### 9.5 Độ dài chuỗi

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 3 936 | System prompt, mode `general` (token Qwen2.5) | `token_budget.md` §2.2; xác nhận lại ở `dataset_stats.md` §2 |
| 4 034 | System prompt, mode `irac` (token Qwen2.5) | `token_budget.md` §2.2 |
| 11 264 | System prompt `general` (ký tự) | `api_contract.md` §1.3 |
| 11 532 | System prompt `irac` (ký tự) | `api_contract.md` §1.3 |
| 30 | Khung cố định của user prompt (ký tự) | `api_contract.md` §1.2 |
| 46 % | Tỉ trọng system prompt trong ngân sách ở câu trung vị | `token_budget.md` §2.2 |
| 12 950 | Độ dài token lớn nhất của mẫu huấn luyện (Qwen2.5) | `dataset_stats.md` §2.2 |
| **12 968** | Độ dài token lớn nhất, **tokenizer Qwen3 thật** | `…2122.log:56` |
| 7 498 / 6 818 / 11 001 | mean / p50 / p95 độ dài tổng chuỗi huấn luyện (Qwen2.5) | `dataset_stats.md` §2.2 |
| **7 530 / 6 869 / 11 009** | mean / p50 / p95, **tokenizer Qwen3 thật**, 4 690 mẫu train | `…2122.log:53-55` |
| **7 286 / 6 542 / 10 956 / 12 062** | mean / p50 / p95 / max tập val 64 mẫu, tokenizer thật | `…2122.log:66-69` |
| 0 | Số mẫu huấn luyện vượt trần 16 384 | `dataset_stats.md` §2.2; **xác nhận** `…2122.log:58`, `:71` |
| 12 011 | Prompt dài nhất trên 127 câu GraphRAG (Qwen2.5) | `token_budget.md` §2.1 |
| 12 011 | Prompt dài nhất backend đo được ở ô 1 / ô 5 | `n_tokens_prompt_backend` trong hai file results |
| 6 432 | Prompt dài nhất backend ở ô 2 / ô 6 | như trên |
| 12 389 | Prompt dài nhất backend ở ô 3 (2-shot) | `results_graphrag_ft06b-base-s2.json` |
| 10 144 | Prompt câu V001, GraphRAG, 0-shot | cổng chặn B + log phiên 3 |
| 10 556 | Prompt câu V001, GraphRAG, 2-shot | cổng chặn B + log phiên 3 |
| 412 | Phụ trội token của hai ví dụ few-shot (ổn định qua ba phép đo) | tính từ §7.2 |
| 22 / 56 | `prompt_len_lech` ở 0-shot / 2-shot, bất biến trong từng ô | mọi file results; `gate_base_model.md` §5 |

### 9.6 Cổng FT-03 (phiên 1) — 15 câu, mẫu số `format_ok` = 12

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 0.083 (1/12) | `format_ok` — 0-shot, pp = 1.0 | `gate_base_model.md` §1 |
| 0.167 (2/12) | `format_ok` — 0-shot, pp = 0 | như trên |
| 0.833 (10/12) | `format_ok` — 2-shot, pp = 1.0 **và** pp = 0 | như trên |
| 0.200 / 0.244 / 0.531 / 0.600 | F1 Khoản bốn ô (theo thứ tự trên) | như trên |
| 0.200 / 0.267 / 0.633 / 0.700 | Norm Recall bốn ô | như trên |
| 1.000 | `soft_article_hit` ở **cả bốn ô** | `gate_base_model.md` §1 |
| 0 | `hit_token_cap` ở cả bốn ô (60 lượt sinh) | như trên |
| 13/15 | Số câu có nhắc điều luật | `gate_base_model.md` §1 |
| 67–78 | Dải số cụm bắt được (mẫu số `soft_article_hit`) | như trên |
| 2/3 → 1/3 | `tu_choi_dung` tụt khi bật few-shot | như trên |
| [0.015, 0.354] vs [0.047, 0.448] | KTC Wilson 95 % của 1/12 vs 2/12 | `gate_base_model.md` §4 |
| 15/15 | Số câu `answer` trùng khít từng ký tự khi chạy lại cùng seed | `finetune/README.md` §Kết quả phiên 1; `FINETUNE_EXECUTION_PLAN.md:739-742` |

### 9.7 Hàng Gemini và Bảng 4.5

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 0.616235 | F1 Khoản GraphRAG, mẻ `final1_20260729-022916` (**đúng file cấp ngữ cảnh cho ô 1/3/5**) | `aggregate` trên `data/evaluation/results_graphrag_final1_20260729-022916.json` |
| 0.639367 | F1 Điều GraphRAG, mẻ đó | như trên |
| 0.827251 | Norm Recall GraphRAG, mẻ đó | như trên |
| 13/14 | Từ chối đúng GraphRAG, mẻ đó | như trên |
| 0.426975 | F1 Khoản Naive, mẻ `20260710-085236` (**đúng file cấp ngữ cảnh cho ô 2/4/6**) | `data/evaluation/results_baseline_20260710-085236.json` |
| 0.448386 | F1 Điều Naive, mẻ đó | như trên |
| 0.594282 | Norm Recall Naive, mẻ đó | như trên |
| 11/14 | Từ chối đúng Naive, mẻ đó | như trên |
| 0.617136 ± 0.001 | F1 Khoản GraphRAG, mean ± σ mẫu, **N=3** (`final1/2/3`) | `aggregate` trên ba file; khớp `docs/V3_RESULTS.md` §2 (0.617 ± 0.001) |
| 0.637692 ± 0.003 | F1 Điều GraphRAG, N=3 | như trên |
| 0.828873 ± 0.006 | Norm Recall GraphRAG, N=3 | như trên; `V3_RESULTS.md` §2 ghi ± 0.005 vì dùng σ tổng thể |
| 0.435819 ± 0.008 | F1 Khoản Naive, mean ± σ mẫu, **N=4 ⚠️** | `aggregate` trên bốn mẻ baseline đủ 137 câu — xem cảnh báo §6.1 |
| 0.458698 ± 0.008 | F1 Điều Naive, N=4 ⚠️ | như trên |
| 0.585158 ± 0.008 | Norm Recall Naive, N=4 ⚠️ | như trên |
| +0.187 | Δ F1 Khoản, cơ sở ghép cặp 123 câu | `docs/V3_RESULTS.md` §3 |
| [0.108, 0.264] | CI 95 % của Δ F1 Khoản (bootstrap 10 000, seed 42) | `docs/V3_RESULTS.md` §3 |
| 0.00003 | Wilcoxon p (\*\*\*) | `docs/V3_RESULTS.md` §3 |
| 67 / 32 / 24 | Win / Loss / Tie trên 123 câu | `docs/V3_RESULTS.md` §3 |
| 0.858 / 0.955 | F1 Khoản / NormR — oracle (**mẻ v2, chưa chạy lại**) | `docs/V2_RESULTS.md` §2; xem cảnh báo §8 |
| 0.571 / 0.808 | F1 Khoản / NormR — bm25 (**mẻ v2, chưa chạy lại**) | như trên |
| 0.102 / 0.102 | F1 Khoản / NormR — closed-book (**mẻ v2, chưa chạy lại**) | như trên |

---

## KIỂM CUỐI

### A. File đã đọc

**Kế hoạch và tài liệu**

| File | Đọc phần nào |
|---|---|
| `docs/FINETUNE_EXECUTION_PLAN.md` (v2.3.4, 970 dòng) | toàn bộ |
| `docs/FT_SYNTHESIS_B_KHOKHAN.md` | toàn bộ (để xác định ranh giới) |
| `docs/V3_RESULTS.md` (176 dòng) | toàn bộ — **bộ số thay thế V2 cho Chương 4/5** |
| `docs/V2_RESULTS.md` | toàn bộ (chỉ để đối chiếu lịch sử, không lấy số) |
| `finetune/README.md` (286 dòng) | toàn bộ |
| `CLAUDE.md` | phần trạng thái + Decision Log |

**Báo cáo `finetune/reports/`**

| File | Đọc phần nào |
|---|---|
| `api_contract.md` (668 dòng) | §1.2, §1.3, §3.2, §6.1, §6.3 + mục lục đầy đủ |
| `token_budget.md` (349 dòng) | toàn bộ |
| `token_budget.json` (9 954 dòng) | **chỉ kiểm tra sự tồn tại và kích thước** (277 551 B) — số liệu đã có bản tổng hợp ở `token_budget.md` |
| `dataset_stats.md` (205 dòng) | toàn bộ |
| `dataset_build.json` (243 dòng) | toàn bộ |
| `gate_base_model.md` (213 dòng) | toàn bộ |
| `ft06b_matrix.md` (261 dòng) | toàn bộ |
| `ft06b_gpu_info.json` | toàn bộ (và **loại bỏ** khỏi giá trị ghim thứ bảy — xem cảnh báo §4.6) |
| `ft06b_artifacts.json` | toàn bộ |
| `ft06b_run_status.json`, `…_gpu0.json`, `…_gpu1.json` | toàn bộ |
| `ft06b_chat_template_base.jinja`, `…_ft.jinja` | độ dài + sha256 (tính lại) |
| `ft06b_prompt_{graphrag,baseline}_s{0,2}.txt` | kích thước file; nội dung đối chiếu qua results JSON tương ứng |
| `samples_20.txt` | chỉ kích thước (319 152 B) |

**Kết quả `finetune/results/` — 10 file JSON `ft06b-*`, tất cả đã chạy qua `metrics.aggregate`**

`results_graphrag_ft06b-ft-s0.json` · `results_baseline_ft06b-ft-s0.json` · `results_graphrag_ft06b-base-s2.json` · `results_baseline_ft06b-base-s2.json` · `results_graphrag_ft06b-base-s0.json` · `results_baseline_ft06b-base-s0.json` · `results_graphrag_ft06b-gate-prompt-s0.json` · `results_graphrag_ft06b-gate-prompt-s2.json` · `results_baseline_ft06b-gate-prompt-s0.json` · `results_baseline_ft06b-gate-prompt-s2.json`

**Nguồn ngữ cảnh `data/evaluation/` — 7 file JSON, đều chạy qua `metrics.aggregate`**

`results_graphrag_final{1,2,3}_20260729-*.json` · `results_baseline_2026070{9,}…json` (bốn mẻ đủ 137 câu: `20260709-073933`, `20260710-001154`, `20260710-085236`, `20260710-104109`)

**Log huấn luyện phiên 2**

`finetune/logs/ft04-5k-2ep-20260729-2122.log` (1 807 dòng) — đọc dòng 30-100, 355-400; đếm 117 dòng `{'loss': …}`

**Cấu hình adapter**

`adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` — toàn bộ 54 dòng

**Mã nguồn**

| File | Đọc phần nào |
|---|---|
| `finetune/train_qlora.py` | toàn bộ (373 dòng) |
| `finetune/run.sh` | toàn bộ (407 dòng) |
| `finetune/kaggle_ft06.py` | dòng 1-145 (chú thích nguồn ngữ cảnh + hằng số), 208-260 (hiện vật ghim), 331-336 (`LANES`), 700-760 (cổng A), 763-900 (cổng B); grep toàn bộ cấu trúc chặng |
| `finetune/build_dataset.py` | hằng số (76-182), `to_record` (632-650), `build`/`make` (656-800), `kiem_tra` (887-915), `tach_train_val` (921-936); danh sách hàm đầy đủ |
| `finetune/replay.py` | `GenParams` (155-175) |
| `finetune/slug.py` | danh sách hàm |
| `src/evaluation/metrics.py` | `aggregate` (189-260) |

**Dữ liệu và hiện vật khác**

`finetune/data/train.jsonl` (đếm dòng) · `finetune/data/val.jsonl` (đếm dòng) · `finetune/data/train.jsonl.sha256` · `finetune/data/val.jsonl.sha256` · `finetune/logs/ft04-5k-2ep-20260729-2122.log` · `finetune/logs/ft06b_gpu0.log` · `finetune/logs/ft06b_gpu1.log` · `data/evaluation/results_graphrag_final{1,2,3}_20260729-*.json` · `data/evaluation/results_baseline_{20260709-073933,20260710-001154,20260710-085236,20260710-104109}.json` · `adapter/ft04-5k-2ep-20260729-2122/checkpoint-588/adapter_config.json` · `../results/ft06_constraints.txt` · `../results/__huggingface_repos__.json` · `../results/repo/.git/{refs,logs,packed-refs}` · git log của repo chính.

### B. File KHÔNG tìm được

| File | Đã tìm ở | Ảnh hưởng tới mục nào |
|---|---|---|
| `adapter/train_result.json` | `finetune/{results,reports,logs,models,data,notebooks}/`, gốc repo, `../results/`; `find . -iname "train_result*.json"` | **Chỉ còn mất `total_flos`** — mọi giá trị khác của file này đều được in ra log (§5.1) |
| `adapter/length_stats.json`, `adapter/val_length_stats.json` | như trên; `find . -iname "*length_stats*.json"` | **Không ảnh hưởng nữa** — cùng bảng đó in nguyên vẹn ra log, `…2122.log:51-73` (§5.3) |
| `trainer.state.log_history` dạng cấu trúc | chỉ nằm trong `trainer_state.json` (không có) | §5.5 — chuỗi loss lẫn trong dòng `tqdm` của log, phải bóc bằng regex mới dựng bảng; chưa làm |
| 4 file results JSON của phiên 1 (FT-03) | `finetune/results/` (chỉ có file `ft06-*` và `ft06b-*`) | §7.2 — không so được độ dài prompt ở cấp câu |
| `finetune/results/prompt_gate-s0-pp10.txt`, `prompt_gate-s2-pp10.txt` | `finetune/results/`, `finetune/reports/` | §7.2 |
| Commit code của phiên 2 | log huấn luyện không in commit hash; không file nào khác ghi | §7 — giá trị ghim thứ tư thiếu cho phiên 2 |
| Chi phí thuê máy phiên 2 | không file nào trong repo ghi giá | §4.1 |
| Bảng 4.5 với bốn thang đo đầy đủ | `docs/` (không có `docs/thesis/`), `thesis/` (rỗng), `docs/V2_RESULTS.md`, `docs/V3_RESULTS.md` | §8 — F1 Điều và Từ chối đúng của oracle/bm25/closed-book |
| Số liệu v3 cho oracle / bm25 / closed-book | `docs/V3_RESULTS.md` (chỉ có số v2 ở §7.1) | §8 — ba bậc đó chưa chạy lại sau khi sửa `query_planner` |
| Giấy phép bộ dữ liệu `thangvip/vietnamese-legal-qa` | `finetune/README.md`, `dataset_stats.md`, `dataset_build.json`, `build_dataset.py`, kế hoạch | §3.1 |

### C. Mọi chỗ hai nguồn lệch nhau

Năm chỗ, liệt kê đầy đủ ở **§0**:

1. Δ hàng Gemini: **+0.181317** (cơ sở aggregate 137 câu, dùng cho ma trận) so với **+0.187** (cơ sở ghép cặp 123 câu, `V3_RESULTS.md` §3) — hai cơ sở khác nhau, không mâu thuẫn.
2. Δ và mức ý nghĩa của Bảng 4.3: `CLAUDE.md` +0.156 / p = 0.001; `V2_RESULTS.md` +0.143 / p = 0.0015; `V3_RESULTS.md` **+0.187 / p = 0.00003** — **V3 là số mới nhất**.
3. Tên kho mô hình gốc: `run.sh` truyền `unsloth/Qwen3-4B-Instruct-2507`, `adapter_config.json` ghi `unsloth/qwen3-4b-instruct-2507-unsloth-bnb-4bit` — **kho thật là bản 4-bit**.
4. Phân bố độ dài mẫu: Qwen2.5 (dựng dữ liệu) so với Qwen3 thật (huấn luyện) — nay **đã đối chiếu được**, lệch ≤ 0.75 %.
5. Thông lượng: log ghi `nan`, giá trị **TÍNH LẠI** ≈ 3 625.9 tok/s.

Chỗ **không** lệch, đã kiểm chéo và khớp: sáu con số `aggregate` của `ft06b_matrix.md` §1 khớp kết quả tính lại tới ba chữ số; `ft06b_run_status.json` khớp cả sáu ô; ba cặp độ trễ ở `ft06b_matrix.md` §4 khớp phép tính lại; `0.617 ± 0.001` của `V3_RESULTS.md` §2 khớp `aggregate` chạy lại trên ba mẻ `final1/2/3`; **`36 × 57 344 × 16 = 33 030 144` khớp số tham số huấn luyện được in ở log** (§2.3); `train_samples_per_second` và `train_steps_per_second` khớp phép chia tay (§5.1); `dataset_build.json` khớp `dataset_stats.md` §1; system prompt 3 936 token khớp giữa `token_budget.md` §2.2 và `dataset_stats.md` §2; max prompt 12 011 token khớp giữa `token_budget.md` §2.1 và backend phiên 3; sha256 chat template `40c21f34…` khớp giữa hai file `.jinja` và giữa hai lượt đánh giá.

### D. Chỗ phải dừng vì không đủ dữ kiện

| # | Việc | Lý do dừng |
|---:|---|---|
| 1 | §5 — `total_flos` | `st.metrics` có khoá này nhưng script không in nó ra log; `train_result.json` (nơi ghi trọn `st.metrics`) không có trong repo |
| 2 | §5.5 — bảng loss theo bước dạng bảng đầy đủ và file CSV | 117 mốc loss có trong log nhưng lẫn trong dòng `tqdm`; phải bóc bằng regex, và mục 4.7 không cần bảng đó |
| 3 | §4.1 — chi phí thuê máy phiên 2 | Không file nào trong repo ghi |
| 4 | §7 — commit code của phiên 2, loại card của phiên 1 | Log huấn luyện không in commit hash; `gate_base_model.md` chỉ ghi "Kaggle" |
| 5 | §7.2 — so độ dài prompt 2-shot phiên 1 với phiên 3 **ở cấp câu** | Phiên 1 chỉ ghi giá trị max trên 15 câu; 4 file results và 2 file dump prompt của phiên 1 không có trong repo. Chỉ so được phụ trội few-shot (412 token, khớp) |
| 6 | §8 — F1 Điều và Từ chối đúng cho oracle / bm25 / closed-book; và số v3 cho ba bậc đó | Repo chỉ có hai trong bốn thang đo, và chỉ ở mẻ v2 |
| 7 | §6.1 — chỉ đúng **ba** mẻ baseline mà `V3_RESULTS.md` §3 dùng | Báo cáo đó không ghi tên mẻ; phép lọc theo số câu ra 4 mẻ. Người phụ trách phải chỉ định |
| 8 | §3.1 — giấy phép bộ dữ liệu nguồn | Không ghi ở bất kỳ file nào |
