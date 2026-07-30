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

## 0. Bốn chỗ hai nguồn lệch nhau — đọc trước

| # | Đại lượng | Nguồn A | Nguồn B | Ghi chú |
|---:|---|---|---|---|
| 1 | Hàng Gemini, F1 Khoản GraphRAG / Naive | **0.578 / 0.435**, Δ **+0.143** — `finetune/reports/ft06_matrix.md` §1, hằng số ở `finetune/kaggle_ft06.py:81-83`, gốc `docs/V2_RESULTS.md` §1 (**mean N=3**) | **0.581423 / 0.426975**, Δ **+0.154448** — `aggregate` chạy lại trên **đúng cặp file đã đóng băng** `data/evaluation/results_{graphrag,baseline}_20260710-085236.json` (**N=1**) | Không mâu thuẫn: A là trung bình 3 lần chạy, B là chính lần chạy cấp ngữ cảnh cho sáu ô. **Số đo khớp điều kiện thí nghiệm của mục 4.7 là B**; số đã in trong `ft06_matrix.md` là A |
| 2 | Δ F1 Khoản của Bảng 4.3 + mức ý nghĩa | **+0.156**, CI [0.070, 0.242], p = 0.001 \*\*\* — `CLAUDE.md` §TRẠNG THÁI HIỆN TẠI | **+0.143**, CI [0.061, 0.225], p = 0.0015 \*\*, W/L/T 65/36/22 — `docs/V2_RESULTS.md` §1 | `V2_RESULTS.md` ghi rõ đây là **đính chính ngày 28/07/2026** và là bộ số dùng cho Chương 4 → **B là số đo mới nhất**; `CLAUDE.md` chưa cập nhật |
| 3 | LoRA `r` / `alpha` | mặc định **32 / 64** — `finetune/train_qlora.py:63-64` | truyền tường minh **16 / 32** — `finetune/run.sh:290-291`; kế hoạch §TASK-FT-05 (`docs/FINETUNE_EXECUTION_PLAN.md:607-608`) chốt 16/32 | Lệnh huấn luyện đi qua `run.sh` nên **giá trị đã chạy là 16 / 32**. **Chưa xác minh được bằng `adapter_config.json`** — file đó KHÔNG CÓ TRONG REPO (xem §5) |
| 4 | Phân bố độ dài mẫu huấn luyện | tokenizer **Qwen2.5-7B** lúc dựng dữ liệu — `finetune/reports/dataset_stats.md` §2 | tokenizer **Qwen3 thật** lúc huấn luyện (`audit_lengths`, `train_qlora.py:107-135`) → `length_stats.json` | `length_stats.json` **KHÔNG CÓ TRONG REPO** → chỉ có nguồn A. Lệch dự kiến nhỏ (`dataset_stats.md` §8.1: cùng họ BPE 151k) nhưng **chưa đo được** |

---

## 1. TÓM TẮT MỘT TRANG

| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| Mô hình gốc (huấn luyện từ) | `unsloth/Qwen3-4B-Instruct-2507` | `finetune/run.sh:50`; `finetune/train_qlora.py:42` |
| Mô hình gốc (hàng "chưa tinh chỉnh", GGUF) | `bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF` :: `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | `finetune/reports/ft06_artifacts.json` |
| Phương pháp | QLoRA 4-bit + LoRA, `train_on_responses_only` | `finetune/train_qlora.py:231-248`, `326-335` |
| LoRA r / alpha / dropout | 16 / 32 / 0.0 | `finetune/run.sh:290-291`; `finetune/train_qlora.py:239` |
| `max_seq_length` | 16 384 | `finetune/run.sh:66`; `finetune/train_qlora.py:53` |
| Số mẫu tổng | 5 000 | `finetune/reports/dataset_stats.md` §0; `finetune/build_dataset.py:88` |
| Số mẫu train / val | 4 690 / 310 | đếm dòng `finetune/data/train.jsonl`, `finetune/data/val.jsonl` |
| Số mẫu val thực dùng khi eval | 64 | `finetune/run.sh:287`; `finetune/train_qlora.py:49-51` |
| Epoch | 2 | `finetune/run.sh:67` |
| Số bước tối ưu | **KHÔNG CÓ TRONG REPO** (suy được từ `train_result.json` — thiếu) | xem §5 |
| Thời gian huấn luyện | **KHÔNG CÓ TRONG REPO** (`train_runtime` trong `train_result.json` — thiếu) | xem §5 |
| `eval_loss` epoch 1 / epoch 2 | 0.3129 / 0.3082 — **chỉ có ở tài liệu tóm tắt**, không có file gốc | `docs/FT_SYNTHESIS_B_KHOKHAN.md:576-577`; xem §5 |
| GGUF đã tinh chỉnh | `ft04-5k-2ep-20260729-2122-Q4_K_M.gguf` | `finetune/reports/ft06_artifacts.json` |
| **F1 Khoản — ô 1** (ft, 0-shot, GraphRAG) | **0.402433** | `aggregate` trên `finetune/results/results_graphrag_ft06-ft-s0.json` |
| **F1 Khoản — ô 2** (ft, 0-shot, Naive) | **0.300765** | `finetune/results/results_baseline_ft06-ft-s0.json` |
| **F1 Khoản — ô 3** (base, 2-shot, GraphRAG) | **0.492631** | `finetune/results/results_graphrag_ft06-base-s2.json` |
| **F1 Khoản — ô 4** (base, 2-shot, Naive) | **0.239092** | `finetune/results/results_baseline_ft06-base-s2.json` |
| **F1 Khoản — ô 5** (base, 0-shot, GraphRAG) | **0.136253** | `finetune/results/results_graphrag_ft06-base-s0.json` |
| **F1 Khoản — ô 6** (base, 0-shot, Naive) | **0.153771** | `finetune/results/results_baseline_ft06-base-s0.json` |
| Δ F1 Khoản — hàng ft 0-shot | **+0.101668** | tính từ ô 1 − ô 2 |
| Δ F1 Khoản — hàng base 2-shot | **+0.253540** | tính từ ô 3 − ô 4 |
| Δ F1 Khoản — hàng base 0-shot | **−0.017518** | tính từ ô 5 − ô 6 |
| Δ F1 Khoản — hàng Gemini | **+0.143** (mean N=3) / **+0.154448** (cặp file đã đóng băng) | §0 mục 1 |
| Tổng lượt sinh | 822 = 6 ô × 137 câu | `docs/FINETUNE_EXECUTION_PLAN.md:635`; `finetune/kaggle_ft06.py:216-223` |
| Số lần chạy mỗi ô | N = 1 | `docs/FINETUNE_EXECUTION_PLAN.md:731-745` |

---

## 2. PHƯƠNG PHÁP TINH CHỈNH

### 2.1 Bảng tham số — trích số dòng

| Tham số | Giá trị đã chạy | Nơi đặt | Ghi chú |
|---|---|---|---|
| `--base-model` | `unsloth/Qwen3-4B-Instruct-2507` | `run.sh:50` (`BASE_MODEL`) → `run.sh:284`; mặc định script `train_qlora.py:42` | |
| Lượng tử hoá | `load_in_4bit = True` | `train_qlora.py:234` | QLoRA; `dtype = None` (`train_qlora.py:235`) để Unsloth tự chọn |
| `r` | **16** | `run.sh:290` truyền `--lora-r 16` | mặc định script là **32** (`train_qlora.py:63`) — xem §0 mục 3 |
| `lora_alpha` | **32** | `run.sh:291` truyền `--lora-alpha 32` | mặc định script là **64** (`train_qlora.py:64`) |
| `lora_dropout` | **0.0** | `train_qlora.py:240` | hardcode trong script, không có cờ CLI |
| `bias` | `"none"` | `train_qlora.py:241` | hardcode |
| `target_modules` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` (**7 module**) | `train_qlora.py:243-244` | hardcode |
| `use_rslora` | `False` | `train_qlora.py:246` | hardcode |
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

### 2.3 Số liệu KHÔNG CÓ TRONG REPO

| Đại lượng | Nơi lẽ ra chứa nó | Đã tìm ở |
|---|---|---|
| Số layer được vá LoRA | log huấn luyện (dòng in của Unsloth) | `finetune/logs/` (chỉ có `ft06_gpu0.log`, `ft06_gpu1.log` — **log phiên 3, không phải phiên 2**), `finetune/results/`, `finetune/reports/`, thư mục gốc repo, `../results/` |
| Số tham số huấn luyện được / tổng | log huấn luyện | như trên |
| `r` / `alpha` thực nạp | `adapter/adapter_config.json` | `find . -iname "adapter_config.json"` → 0 kết quả trong repo |
| Số lượt forward/backward thật | `train_result.json` (`train_runtime`, `global_step`) | `find . -iname "train_result*.json"` → 0 kết quả |
| Tỉ lệ token bị che | log huấn luyện — script in ở `train_qlora.py:331-335` | như trên |

*(Việc truy tìm các file này trong Downloads/ổ đĩa ngoài repo đã được người dùng cho tạm gác lại.)*

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
| Cùng hàm đó dùng lúc đánh giá | `build_chat_messages` gọi `build_messages` | `finetune/replay.py` | `finetune/kaggle_ft06.py:661` (cổng chặn B dựng lại để đối chiếu) |
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

**Nguồn B — đo lúc huấn luyện bằng tokenizer thật:** `audit_lengths()` (`train_qlora.py:107-135`) ghi `length_stats.json` (train) và `val_length_stats.json` (val) với các khoá `n_samples`, `p50`, `p95`, `max`, `mean`, `total_tokens`, `over_limit`, `limit`.

> **Cả hai file KHÔNG CÓ TRONG REPO.** Đã tìm: `finetune/results/`, `finetune/reports/`, `finetune/logs/`, `finetune/models/`, thư mục gốc repo, và `../results/` (bản tải về của phiên 3). Lệnh: `find . -iname "*length_stats*.json"` → 0 kết quả.
> Hệ quả: **không đối chiếu được** giữa hai nguồn. `dataset_stats.md` §8.1 nêu kỳ vọng lệch nhỏ (Qwen2.5 và Qwen3 cùng họ BPE 151k), nhưng đó là lập luận chứ không phải số đo.
> Điều **biết chắc**: `audit_lengths` **dừng chương trình** (`SystemExit`, `train_qlora.py:130-131`) nếu có mẫu vượt trần, mà lần chạy thật đã đi tới bước merge/gguf → suy ra `over_limit = 0` ở cả train lẫn val. (Đây là suy luận từ hành vi mã, không phải số đọc từ file.)

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
| 9 | `train_qlora.py:124-131` | `over_limit == 0`, nếu không thì `SystemExit` | 4 690 + 64 | **KHÔNG ĐỌC ĐƯỢC** (thiếu `length_stats.json`) — xem §3.4 |

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
| GPU thực tế | **KHÔNG CÓ TRONG REPO** (nằm ở log huấn luyện — thiếu) | **Tesla T4 × 2, 15 360 MiB mỗi card** |
| Nguồn | `finetune/run.sh:6`, `:132-143` | `finetune/reports/ft06_gpu_info.json`; `ft06_matrix.md` §3 |
| Ràng buộc đĩa | ≥ 50 GB trống (`run.sh:145-146`) | — |
| Ràng buộc Python | đúng 3.12 (`run.sh:150-151`, vì wheel là cp312) | cp312 (`ft06_artifacts.json`) |
| Thời gian | **KHÔNG CÓ TRONG REPO** | tổng `total_elapsed_s` sáu ô = **10 638.06 s ≈ 2 giờ 57 phút** (cộng từ sáu results JSON, §6.2) |
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
| 1 | `prep` | `stage_prep()` — `kaggle_ft06.py:478` | Tải wheel `llama-cpp-python` và đối chiếu sha256 **trước khi** `pip install`; tải hai file GGUF (base theo `revision` ghim, ft); đối chiếu sha256 cả hai; tạo symlink vào `finetune/models/`; in `nvidia-smi` | `finetune/reports/ft06_artifacts.json`, `finetune/reports/ft06_gpu_info.json` |
| 2 | `gate-template` | `stage_gate_template()` — `:600` | Đọc `tokenizer.chat_template` nhúng trong **cả hai** GGUF (khoá `kaggle_ft06.py:96`); so độ dài + sha256; in `difflib` nếu khác; **`exit 2`** nếu khác | `finetune/reports/ft06_chat_template_base.jinja`, `…_ft.jinja` |
| 3 | `gate-prompt` | `stage_gate_prompt()` — `:719` | Sinh prompt cho bốn tổ hợp `{graphrag, baseline} × {0-shot, 2-shot}`; chạy 5 kiểm tự động (§4.5); in 40 dòng đầu + 20 dòng cuối mỗi file; **`exit 2`** nếu bất kỳ mục FAIL | 4 file `ft06_prompt_{system}_s{n}.txt`, 4 file `results_{system}_ft06-gate-prompt-s{n}.json` |
| 4 | `run` | `stage_run()` — `:923`; song song `_run_song_song()` — `:849` | Sáu ô, mỗi ô một lệnh `python -m finetune.replay`, ghim `CUDA_VISIBLE_DEVICES` của subprocess; `--resume`; đẩy HF ngay sau từng ô | 6 file `results_{system}_{tag}.json` + 6 `.partial.jsonl`, `ft06_run_status*.json`, `ft06_gpu{0,1}.log` |
| 5 | `table` | — | Gom sáu file kết quả, gọi `metrics.aggregate`, dựng bảng | `finetune/reports/ft06_matrix.md` |

Tham số sinh: script **KHÔNG truyền lại bảy trong tám giá trị** (đã là mặc định của `replay.py`); **ngoại lệ duy nhất** là `--presence-penalty 0` truyền tường minh tại `kaggle_ft06.py:761`, vì mặc định của `replay.py` là **1.0** (`replay.py:166`) — `kaggle_ft06.py:37-45`.

Phân luồng GPU: `LANES = {0: [1, 3, 2], 1: [5, 4, 6]}` — `kaggle_ft06.py:244-247`.

### 4.4 Cổng chặn A — chat template

| Mục | Giá trị | Nguồn |
|---|---|---|
| Điều kiện qua | `sha256(template_base) == sha256(template_ft)` | `kaggle_ft06.py:626`; hỏng → `exit 2` |
| Độ dài template base | **4 040 ký tự** | đo trên `finetune/reports/ft06_chat_template_base.jinja` |
| Độ dài template ft | **4 040 ký tự** | đo trên `finetune/reports/ft06_chat_template_ft.jinja` |
| sha256 cả hai | `40c21f34cf67d8c760ef72f8ad3ae5afad514299d4b06e91dd9a8d705af7b541` | tính lại trên hai file `.jinja` |
| Kết quả | **TRÙNG KHÍT** (byte-identical, hai file giống nhau hoàn toàn) | như trên |

### 4.5 Cổng chặn B — prompt đã render

Năm kiểm tự động, hàm `_kiem_mot_prompt()` — `kaggle_ft06.py:659-716`:

| # | Kiểm tra | Điều kiện | Dòng |
|---:|---|---|---|
| 1 | Render bằng chat template GGUF thật | header chứa `render=gguf-chat-template-jinja2`, KHÔNG phải nhánh lùi `render-loi:` | `:671-674` |
| 2 | System prompt còn nguyên đầu | 200 ký tự đầu sau `<\|im_start\|>system` khớp `build_chat_messages(...)[0]` | `:676-691` |
| 3 | Số lượt vai | = **2** khi `n_shot = 0`, = **6** khi `n_shot = 2` | `:693-696` |
| 4 | Kết thúc prompt | nội dung cuối trước thẻ mở vai assistant là `"TRẢ LỜI:"` | `:698-708` |
| 5 | Số thẻ mở vai assistant | = **1** khi `n_shot = 0`, = **3** khi `n_shot = 2` | `:710-714` |

Bằng chứng đã chạy — bốn file prompt và bốn results JSON tương ứng (câu **V001** cho cả bốn):

| Tổ hợp | File prompt | Kích thước file | `n_tokens_prompt` (tự đếm) | `n_tokens_prompt_backend` | `prompt_len_lech` |
|---|---|---:|---:|---:|---:|
| graphrag · 0-shot | `finetune/reports/ft06_prompt_graphrag_s0.txt` | 37 402 B | **10 144** | 10 122 | 22 |
| graphrag · 2-shot | `finetune/reports/ft06_prompt_graphrag_s2.txt` | 38 566 B | **10 556** | 10 500 | 56 |
| baseline · 0-shot | `finetune/reports/ft06_prompt_baseline_s0.txt` | 22 513 B | **6 182** | 6 160 | 22 |
| baseline · 2-shot | `finetune/reports/ft06_prompt_baseline_s2.txt` | 23 677 B | **6 594** | 6 538 | 56 |

Cả bốn file results gate-prompt đều `format_ok_rate = 1.0`, `f1_mean = 1.0`, `n_hit_token_cap = 0` (`aggregate` trên `finetune/results/results_*_ft06-gate-prompt-s*.json`).

### 4.6 Bảy giá trị ghim — chuỗi đầy đủ

| # | Đối tượng | Chuỗi đầy đủ | File ghi |
|---:|---|---|---|
| 1 | Tarball llama.cpp (CPU-only static, dùng để **lượng tử hoá**) | tag `b10165`; file `llamacpp-b10165-cpu-static-x64.tar.gz`; sha256 `9f8e92b8a69b3c8399e6f42324430f8a0faaf1bba707deeee7c8cb96bbd9c6d5` | `finetune/run.sh:53`, `:58`, `:59` |
| 2 | Wheel `llama-cpp-python` (dùng để **chạy suy luận, sinh số liệu**) | repo `dangnguyen254/thesis-graphrag-gguf`; file `runtime/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl`; sha256 `a3cb84bddb15c1759a0ece5ec8ef9d10d1419f926c895064d1a91ec517fd0da7` | `finetune/reports/ft06_artifacts.json`; `finetune/kaggle_ft06.py:143-147`; `finetune/run.sh:54` (`LCP_VERSION=0.3.16`) |
| 3 | GGUF mô hình gốc + revision | repo `bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF`; file `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf`; revision `ae44f08e1392f39c0e474af10c3ff8355c8b6688`; sha256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e` | `finetune/reports/ft06_artifacts.json`; `finetune/kaggle_ft06.py:177-180`; `finetune/reports/gate_base_model.md` §Hiện vật GGUF gốc; `../results/__huggingface_repos__.json` (xác nhận độc lập cùng `commitHash`) |
| 4 | Commit code | **phiên 3:** `2a712adf7707164b7302afa42cf98ea06c99b417` (nhánh `dev/fine-tune`) · **phiên 1:** `eecdc7b7dc533f2c564d74e795704fb4dcbb81a2` **cộng** một bản vá `render_prompt` chưa từng nằm trong commit nào | phiên 3: `../results/repo/.git/refs/heads/dev/fine-tune` + `../results/repo/.git/logs/HEAD` (clone lúc epoch 1785391123 = 2026-07-30T05:58:43Z); phiên 1: `finetune/reports/gate_base_model.md` §6 |
| 5 | Dữ liệu huấn luyện | `train.jsonl` sha256 `615ad1e7a3ad0dfa991147ae503e6078f138bce90e6a45252bc0189535c79b20` · `val.jsonl` sha256 `2361e15b7f195e3c7929599d57ad94f5d215343565af8f11cb3d5fe178b93ead` | `finetune/data/train.jsonl.sha256`, `finetune/data/val.jsonl.sha256` |
| 6 | GGUF đã tinh chỉnh | repo `dangnguyen254/thesis-graphrag-gguf`; file `gguf/ft04-5k-2ep-20260729-2122-Q4_K_M.gguf`; sha256 `c115e6a79299d1fe0e41eb5f6720955108df1e869676dc96f0b7ba61c37ce5d0` | `finetune/reports/ft06_artifacts.json`; `finetune/kaggle_ft06.py:150-154` |
| 7 | Ghim GPU (mỗi ô một card) | ô 1 → `CUDA_VISIBLE_DEVICES=0` · ô 2 → `0` · ô 3 → `0` · ô 4 → `1` · ô 5 → `1` · ô 6 → `1` | `finetune/reports/ft06_gpu_info.json` (`ghim_cuda_visible_devices`); `finetune/reports/ft06_matrix.md` §3; lệnh thật in trong `finetune/logs/ft06_gpu{0,1}.log` |

Bộ ghim phiên bản gói (phiên 3) — `../results/ft06_constraints.txt`, đối chiếu `finetune/kaggle_ft06.py:111-120` và `finetune/run.sh:174-181`:

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

> ### ⚠️ KHÔNG CÓ TRONG REPO
>
> Toàn bộ số liệu định lượng của phiên huấn luyện nằm trong bốn hiện vật, **không hiện vật nào có trong repo**:
>
> | File | Sinh bởi | Chứa gì |
> |---|---|---|
> | `adapter/train_result.json` | `train_qlora.py:360-368` | `loss` (= `training_loss`), toàn bộ `st.metrics` (gồm `train_runtime`, `train_samples_per_second`, `train_steps_per_second`, `total_flos`, `train_tokens_per_second`), `eval_history` (list `{epoch, step, eval_loss}`), `eval_loss_final`, `max_seq_length`, `max_steps`, `limit_samples`, `longest_first` |
> | `adapter/length_stats.json` | `train_qlora.py:107-135` | `n_samples`, `p50`, `p95`, `max`, `mean`, `total_tokens`, `over_limit`, `limit` cho tập train |
> | `adapter/val_length_stats.json` | `train_qlora.py:300-301` | như trên, cho tập val |
> | Hai file log huấn luyện | `run.sh:94` (`$WORK/${RUN_NAME}.log`), đẩy HF ở `run.sh:113` | dòng `XONG: loss=… runtime=…s` (`train_qlora.py:341`), thông lượng tok/s (`:342`), bảng `--- EVAL LOSS THEO EPOCH ---` (`:348-351`), tỉ lệ token bị che (`:333-335`), tên GPU + compute cap + `bf16 gốc` (`:226-228`) |
>
> **Đã tìm ở:** `finetune/results/`, `finetune/reports/`, `finetune/logs/`, `finetune/models/`, `finetune/data/`, `finetune/notebooks/`, thư mục gốc repo, và `../results/` (bản tải về của **phiên 3**).
> Lệnh đã chạy: `find . -iname "train_result*.json" -o -iname "*length_stats*.json" -o -iname "adapter_config.json" -o -iname "trainer_state.json"` → **0 kết quả**.
> Hai file duy nhất trong `finetune/logs/` là `ft06_gpu0.log` và `ft06_gpu1.log` — **log của phiên 3 (đánh giá)**, không phải phiên 2.

### 5.1 Hai con số duy nhất còn lại — không có file gốc

| Đại lượng | Giá trị | Nguồn | Cảnh báo |
|---|---:|---|---|
| `eval_loss` sau epoch 1 | **0.3129** | `docs/FT_SYNTHESIS_B_KHOKHAN.md:576` | Đây là **tài liệu tóm tắt**, không phải file kết quả. Không đối chiếu được với `train_result.json` |
| `eval_loss` sau epoch 2 | **0.3082** | `docs/FT_SYNTHESIS_B_KHOKHAN.md:577` | như trên |
| Mức cải thiện | −0.0047 tuyệt đối = **1.50 %** tương đối | tính từ hai dòng trên | |

### 5.2 Bảng loss theo mốc bước

`logging_steps = 5` (`train_qlora.py:177`) nghĩa là log_history CÓ ghi loss mỗi 5 bước, nhưng chuỗi đó chỉ tồn tại trong `trainer.state.log_history` và trong log huấn luyện — **KHÔNG CÓ TRONG REPO**. Không dựng được bảng loss theo bước, **không xuất CSV**.

### 5.3 Suy được từ cấu hình (KHÔNG phải số đo)

| Đại lượng | Cách suy | Giá trị |
|---|---|---:|
| Bước tối ưu mỗi epoch | ⌊4 690 mẫu ÷ 16 (batch hiệu dụng)⌋ | ≈ 293 |
| Bước tối ưu tổng, 2 epoch | ≈ 293 × 2 | ≈ 586 |
| Lượt forward/backward tổng | 4 690 × 2 epoch (batch = 1) | 9 380 |
| Số lần eval | `eval_strategy="epoch"` × 2 epoch | 2 |
| Số mẫu eval mỗi lần | `--val-limit 64` | 64 |

> Ba dòng đầu là **phép chia trên hai hằng số cấu hình**, không đọc từ `train_result.json`. Nếu HF Trainer làm tròn khác (drop_last, resume, …) thì con số thật lệch. **Chỉ dùng khi không lấy lại được file gốc, và phải ghi rõ là suy ra.**

---

## 6. KẾT QUẢ ĐÁNH GIÁ — SÁU Ô

Mọi con số ở §6 tính bằng `src/evaluation/metrics.py::aggregate` chạy trực tiếp trên sáu file `finetune/results/results_*.json`. Nguồn ngữ cảnh của cả sáu ô: `data/evaluation/results_graphrag_20260710-085236.json` (cột GraphRAG) và `data/evaluation/results_baseline_20260710-085236.json` (cột Naive) — trường `replay.nguon` của từng file kết quả.

### 6.1 Ma trận đầy đủ

| Ô | Mô hình sinh | Hệ truy hồi | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng | Δ (F1 Khoản) |
|---:|---|---|---:|---:|---:|---:|---:|
| — | Gemini 2.5 Pro *(cặp file đã đóng băng)* | Naive RAG | 0.426975 | 0.448386 | 0.594282 | 0.785714 (11/14) | |
| — | Gemini 2.5 Pro *(cặp file đã đóng băng)* | GraphRAG | 0.581423 | 0.598472 | 0.793187 | 0.928571 (13/14) | **+0.154448** |
| — | Gemini 2.5 Pro *(mean N=3, `V2_RESULTS.md`)* | Naive RAG | 0.435 | — | 0.588 | — | |
| — | Gemini 2.5 Pro *(mean N=3, `V2_RESULTS.md`)* | GraphRAG | 0.578 | — | 0.771 | — | **+0.143** |
| 6 | Cục bộ gốc, 0-shot | Naive RAG | 0.153771 | 0.170195 | 0.264599 | 0.928571 (13/14) | |
| 5 | Cục bộ gốc, 0-shot | GraphRAG | 0.136253 | 0.136253 | 0.137470 | 0.928571 (13/14) | **−0.017518** |
| 4 | Cục bộ gốc, 2-shot | Naive RAG | 0.239092 | 0.315247 | 0.599148 | 0.500000 (7/14) | |
| 3 | Cục bộ gốc, 2-shot | GraphRAG | 0.492631 | 0.536427 | 0.630170 | 0.857143 (12/14) | **+0.253540** |
| 2 | Cục bộ đã tinh chỉnh, 0-shot | Naive RAG | 0.300765 | 0.344317 | 0.609489 | 0.571429 (8/14) | |
| 1 | Cục bộ đã tinh chỉnh, 0-shot | GraphRAG | 0.402433 | 0.444769 | 0.541363 | 0.928571 (13/14) | **+0.101668** |

*Bốn hàng cục bộ khớp `finetune/reports/ft06_matrix.md` §1 tới ba chữ số thập phân (bảng đó làm tròn: 0.402 / 0.301 / 0.493 / 0.239 / 0.136 / 0.154).*
*Hai hàng Gemini: xem §0 mục 1. `ft06_matrix.md` §1 chỉ in hàng mean N=3 và để `—` ở ba cột còn lại.*

**Precision / Recall tách riêng** (cấp Khoản, từ `aggregate`):

| Ô | precision_mean | recall_mean | f1_mean | precision_dieu | recall_dieu | f1_dieu |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.435523 | 0.402676 | 0.402433 | 0.482968 | 0.442214 | 0.444769 |
| 2 | 0.333333 | 0.340511 | 0.300765 | 0.388078 | 0.382117 | 0.344317 |
| 3 | 0.534550 | 0.507056 | 0.492631 | 0.580779 | 0.549635 | 0.536427 |
| 4 | 0.267397 | 0.290024 | 0.239092 | 0.350122 | 0.366058 | 0.315247 |
| 5 | 0.142336 | 0.142336 | 0.136253 | 0.142336 | 0.142336 | 0.136253 |
| 6 | 0.151460 | 0.177616 | 0.153771 | 0.167275 | 0.195864 | 0.170195 |
| Gemini graphrag (085236) | 0.585366 | 0.605691 | 0.581423 | — | — | 0.598472 |

*(Hai cột `precision_dieu`/`recall_dieu` của hàng Gemini không in ở đây vì `aggregate` có tính, chi tiết xem lại file nguồn nếu cần.)*

### 6.2 Sức khoẻ từng ô

| Ô | Mô hình | n_shot | Hệ | `format_ok_rate` | **mẫu số** | `format_ok` đếm | `n_hit_token_cap` | `soft_article_hit` | Qua mô hình / tổng | Sao chép hằng số | `total_elapsed_s` | Card |
|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | ft | 0 | graphrag | **0.731707** | **123** | 90 | 0 | 0.972464 | **127/137** | 10 | 1 583.69 | 0 |
| 2 | ft | 0 | baseline | **0.894309** | **123** | 110 | **1** (`V020`) | 0.965290 | **137/137** | 0 | 1 182.74 | 0 |
| 3 | base | 2 | graphrag | **0.813008** | **123** | 100 | 0 | 1.000000 | **127/137** | 10 | 2 328.05 | 0 |
| 4 | base | 2 | baseline | **0.894309** | **123** | 110 | 0 | 0.945519 | **137/137** | 0 | 1 294.76 | 1 |
| 5 | base | 0 | graphrag | **0.073171** | **123** | 9 | 0 | 0.991361 | **127/137** | 10 | 2 653.86 | 1 |
| 6 | base | 0 | baseline | **0.211382** | **123** | 26 | 0 | 0.927839 | **137/137** | 0 | 1 594.96 | 1 |

- **Mẫu số `format_ok_rate` là 123 ở cả sáu ô** — số câu có `ground_truth_citations` khác rỗng (`FINETUNE_EXECUTION_PLAN.md` §3.1 và §9.4).
- 10 câu sao chép hằng số của cột GraphRAG: **V106, V107, V108, V109, V110, V111, V112, V113, V115, V116** (`frozen_copy = true`, `elapsed_seconds = 0.0`) — giống hệt ở cả ba ô GraphRAG.
- `soft_article_hit` mẫu số (số cụm bắt được) và số câu có nhắc: ô 1 = 331 cụm / 92 câu; ô 2 = 417 / 117; ô 3 = 522 / 111; ô 4 = 501 / 123; ô 5 = 422 / 113; ô 6 = 413 / 121 (khoá `soft_article_mentions_tong`, `soft_article_hit_do_duoc`).

**Prompt token đo được mỗi ô:**

| Ô | tự đếm min | tự đếm max | backend min | backend max | `prompt_len_lech` (mọi câu) |
|---:|---:|---:|---:|---:|---:|
| 1 | 5 429 | 12 033 | 5 407 | 12 011 | 22 |
| 2 | 5 471 | 6 454 | 5 449 | 6 432 | 22 |
| 3 | 5 841 | 12 445 | 5 785 | 12 389 | 56 |
| 4 | 5 883 | 6 866 | 5 827 | 6 810 | 56 |
| 5 | 5 429 | 12 033 | 5 407 | 12 011 | 22 |
| 6 | 5 471 | 6 454 | 5 449 | 6 432 | 22 |

`prompt_len_lech` **bất biến trong từng ô** (một giá trị duy nhất): 22 ở mọi cấu hình 0-shot, 56 ở mọi cấu hình 2-shot. Chênh 2-shot − 0-shot = **34** token ở cả hai khuôn.

**Câu trả lời sai ở cột "Từ chối đúng":**

| Ô | Số đúng | id trả lời sai |
|---:|---:|---|
| 1 | 13/14 | `V105` |
| 2 | 8/14 | `V005`, `V105`, `V107`, `V109`, `V113`, `V115` |
| 3 | 12/14 | `V005`, `V105` |
| 4 | 7/14 | `V005`, `V105`, `V107`, `V109`, `V113`, `V115`, `V116` |
| 5 | 13/14 | `V105` |
| 6 | 13/14 | `V107` |
| Gemini graphrag (085236) | 13/14 | `V005` |
| Gemini baseline (085236) | 11/14 | `V005`, `V107`, `V116` |

**Độ trễ mỗi câu** (`ft06_matrix.md` §4; tính lại khớp — trung bình `elapsed_seconds` **chỉ trên câu đi qua mô hình**, loại 10 câu hằng số):

| Cặp ô | GraphRAG s/câu | Naive s/câu | Lệch | Card | Cảnh báo |
|---|---:|---:|---:|---|---|
| ô 1 + 2 · ft 0-shot | 12.469992 | 8.633168 | 44 % | 0 vs 0 | cùng card |
| ô 3 + 4 · base 2-shot | 18.331134 | 9.450774 | 94 % | 0 vs 1 | ⚠️ vượt ngưỡng 25 % trên hai card khác nhau |
| ô 5 + 6 · base 0-shot | 20.896496 | 11.642044 | 79 % | 1 vs 1 | cùng card |

`latency_mean_s` từ `aggregate` (tính trên **cả 137 câu**, gồm 10 câu `elapsed = 0.0`): ô 1 = 11.559774 · ô 2 = 8.633168 · ô 3 = 16.993095 · ô 4 = 9.450774 · ô 5 = 19.371204 · ô 6 = 11.642044.
`latency_p95_s`: ô 1 = 20.163 · ô 2 = 15.579 · ô 3 = 42.316 · ô 4 = 17.336 · ô 5 = 40.939 · ô 6 = 22.338.

### 6.3 Tỉ lệ Δ TƯƠNG ĐỐI (GraphRAG / Naive), 3 chữ số thập phân

Tính từ giá trị `aggregate` chưa làm tròn.

| Hàng | F1 Khoản G / N | **Tỉ lệ F1 Khoản** | Tỉ lệ F1 Điều | Tỉ lệ NormR |
|---|---|---:|---:|---:|
| Gemini 2.5 Pro *(cặp file 085236, N=1)* | 0.581423 / 0.426975 | **1.362** | 1.335 | 1.335 |
| Gemini 2.5 Pro *(mean N=3, `V2_RESULTS.md`)* | 0.578 / 0.435 | **1.329** | — | 1.311 |
| Cục bộ đã tinh chỉnh, 0-shot | 0.402433 / 0.300765 | **1.338** | 1.292 | 0.888 |
| Cục bộ gốc, 2-shot | 0.492631 / 0.239092 | **2.060** | 1.702 | 1.052 |
| Cục bộ gốc, 0-shot | 0.136253 / 0.153771 | **0.886** | 0.801 | 0.520 |

Δ tuyệt đối tương ứng:

| Hàng | Δ F1 Khoản | Δ F1 Điều | Δ NormR |
|---|---:|---:|---:|
| Gemini *(cặp file 085236)* | +0.154448 | +0.150086 | +0.198905 |
| Cục bộ đã tinh chỉnh, 0-shot | +0.101668 | +0.100452 | **−0.068127** |
| Cục bộ gốc, 2-shot | +0.253540 | +0.221179 | +0.031022 |
| Cục bộ gốc, 0-shot | **−0.017518** | **−0.033942** | **−0.127129** |

### 6.4 Phân tách theo `gap_type` và `theme` — ô 1 và ô 3

**Ô 1 — ft, 0-shot, GraphRAG** (`aggregate.by_gap` / `by_theme` trên `results_graphrag_ft06-ft-s0.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.442708 | 0.486458 | 0.671875 |
| gap2 | 31 | 0.247312 | 0.247312 | 0.387097 |
| gap3 | 30 | 0.338889 | 0.372222 | 0.400000 |
| gap4 | 30 | 0.337778 | 0.451111 | 0.522222 |
| negative | 14 | 0.928571 | 0.928571 | 0.928571 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.349180 | 0.519126 |
| ho-tich | 39 | 0.447009 | 0.512821 |
| nuoi-con-nuoi | 29 | 0.324138 | 0.534483 |
| `None` | 8 | 0.875000 | 0.875000 |

**Ô 3 — base, 2-shot, GraphRAG** (`results_graphrag_ft06-base-s2.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.473958 | 0.567708 | 0.796875 |
| gap2 | 31 | 0.470507 | 0.470507 | 0.483871 |
| gap3 | 30 | 0.336825 | 0.370159 | 0.461111 |
| gap4 | 30 | 0.521111 | 0.587778 | 0.666667 |
| negative | 14 | 0.857143 | 0.857143 | 0.857143 |

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.491101 | 0.620219 |
| ho-tich | 39 | 0.552137 | 0.628205 |
| nuoi-con-nuoi | 29 | 0.310345 | 0.586207 |
| `None` | 8 | 0.875000 | 0.875000 |

**Đối chiếu — hàng Gemini, cùng nguồn ngữ cảnh** (`aggregate` trên `data/evaluation/results_graphrag_20260710-085236.json`):

| `gap_type` | n | F1 Khoản | F1 Điều | NormR |
|---|---:|---:|---:|---:|
| gap1 | 32 | 0.518824 | 0.551190 | 0.890625 |
| gap2 | 31 | 0.515086 | 0.515086 | 0.661290 |
| gap3 | 30 | 0.498386 | 0.541720 | 0.777778 |
| gap4 | 30 | 0.637778 | 0.637778 | 0.777778 |
| negative | 14 | 0.928571 | 0.928571 | 0.928571 |

*(Khớp `docs/V2_RESULTS.md` §3 dòng "FULL v2 per-gap: gap1 0.519 · gap2 0.515 · gap3 0.498 · gap4 0.638".)*

| `theme` | n | F1 Khoản | NormR |
|---|---:|---:|---:|
| dat-dai | 61 | 0.617412 | 0.789617 |
| ho-tich | 39 | 0.580342 | 0.743590 |
| nuoi-con-nuoi | 29 | 0.391708 | 0.810345 |
| `None` | 8 | 1.000000 | 1.000000 |

*(Khớp `docs/V2_RESULTS.md` §4.)*

Nhóm `theme = None` (8 câu) là phần con của 14 câu negative — nhóm negative có 14 câu, trong đó 6 câu vẫn mang `theme` cụ thể.

### 6.5 Câu chạm trần token

| id | Ô | Mô hình · n_shot · hệ | `n_tokens_out` | `n_tokens_prompt` (tự đếm) | `n_tokens_prompt_backend` | Độ dài `answer` |
|---|---:|---|---:|---:|---:|---:|
| **V020** | **2** | ft · 0-shot · baseline | **2 048** (= `max_new_tokens`) | 6 082 | 6 060 | **6 276 ký tự** |

Đây là **câu duy nhất** chạm trần trong toàn bộ 822 lượt sinh: năm ô còn lại đều có `n_hit_token_cap = 0` và `ids_hit_token_cap = []`. Nguồn: trường `hit_token_cap` của từng item + khoá `replay.ids_hit_token_cap`; cảnh báo in ở `finetune/reports/ft06_matrix.md` §2 và `finetune/logs/ft06_gpu0.log`.

---

## 7. ĐỐI CHIẾU BA PHIÊN

| Hàng | Phiên 1 — cổng FT-03 | Phiên 2 — huấn luyện FT-05 | Phiên 3 — đánh giá FT-06 |
|---|---|---|---|
| Ngày | 29/07/2026 | 29/07/2026 *(suy từ `RUN_NAME` = `ft04-5k-2ep-20260729-2122`)* | 30/07/2026 |
| Nền | Kaggle | RunPod Community Cloud | Kaggle Notebooks |
| Mô hình | `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (bartowski) | huấn luyện từ `unsloth/Qwen3-4B-Instruct-2507` | base GGUF (bartowski) **+** `ft04-5k-2ep-20260729-2122-Q4_K_M.gguf` |
| Số câu | **15** (`finetune/data/gate_ids.json`) | — (4 690 mẫu train / 64 mẫu val) | **137** × 6 ô = **822 lượt** |
| Số ô | 4 (2 × 2) | 1 lần chạy | 6 |
| Phần cứng | Kaggle GPU — **loại card KHÔNG CÓ TRONG REPO** (`gate_base_model.md` chỉ ghi "Kaggle") | RTX 4090 dự kiến (`run.sh:6`); **card thực tế KHÔNG CÓ TRONG REPO** | **Tesla T4 × 2**, 15 360 MiB mỗi card |
| Commit code | `eecdc7b7dc533f2c564d74e795704fb4dcbb81a2` **+ bản vá ngoài git** | **KHÔNG CÓ TRONG REPO** | `2a712adf7707164b7302afa42cf98ea06c99b417` |
| Thời gian chạy | **KHÔNG CÓ TRONG REPO** | **KHÔNG CÓ TRONG REPO** | 10 638.06 s tổng sáu ô (2 luồng song song) |
| Kết quả lưu ở | `finetune/reports/gate_base_model.md` (**4 file results JSON KHÔNG CÓ TRONG REPO**) | `train_result.json` — **KHÔNG CÓ TRONG REPO** | 6 file `finetune/results/results_*.json` |

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
| 8 | `n_ctx` | 16 384 | (`max_seq_length` = 16 384) | 16 384 | — |
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
| Phiên 3 — cổng chặn B, `results_graphrag_ft06-gate-prompt-s{0,2}.json` | prompt của **câu V001**, khuôn GraphRAG | **10 144** | **10 556** | **412** |
| Phiên 3 — cổng chặn B, khuôn baseline | prompt của câu V001 | **6 182** | **6 594** | **412** |
| Phiên 3 — ô 1 / ô 5 và ô 3, `finetune/logs/ft06_gpu{0,1}.log` | prompt của câu V001 trong lần chạy đủ 137 câu | **10 144** | **10 556** | **412** |

**Kết luận của phép kiểm:**

1. **KHÔNG so được trực tiếp.** Phiên 1 chỉ ghi lại **giá trị lớn nhất trên bộ 15 câu**, phiên 3 ghi giá trị **của câu V001**. Bốn file results JSON của phiên 1 — nguồn duy nhất có độ dài prompt từng câu — **KHÔNG CÓ TRONG REPO** (`finetune/results/` chỉ chứa file `ft06-*`; đã kiểm toàn bộ thư mục). Không có file dump prompt của phiên 1 (`prompt_gate-s0-pp10.txt`, `prompt_gate-s2-pp10.txt` nêu ở `gate_base_model.md` §5 và `finetune/README.md`) trong repo.
2. **Cái so được, và nó khớp:** phụ trội của việc thêm hai cặp ví dụ là **đúng 412 token** ở cả ba phép đo độc lập — phiên 1 (trên giá trị max), phiên 3 khuôn GraphRAG, phiên 3 khuôn baseline. Cùng với `prompt_len_lech` bất biến 22 (0-shot) và 56 (2-shot) ở cả hai phiên (`gate_base_model.md` §5 mục 3 ghi đúng 22 và 56), đây là bằng chứng khuôn prompt không đổi giữa hai phiên. *(Con số 412 và 34 là phép trừ trên các giá trị đã đọc từ file, không phải số đọc trực tiếp.)*
3. Con số **10 556** mà `docs/FT_SYNTHESIS_B_KHOKHAN.md:509-512` mô tả là "trùng khít con số của phiên cổng FT-03" **không đối chiếu được** với `gate_base_model.md`, vì báo cáo đó chỉ ghi 11 623 (max). Chỗ này cần một nguồn khác nếu muốn phát biểu trong khoá luận.

---

## 8. ĐỐI CHIẾU VỚI BẢNG 4.5 CỦA KHÓA LUẬN

**Bảng 4.5 (bốn hệ tham chiếu) — KHÔNG CÓ TRONG REPO ở dạng bốn thang đo đầy đủ.**
Đã tìm ở: `docs/` (không có thư mục `docs/thesis/` — `ls docs/thesis` → không tồn tại), `thesis/` (thư mục rỗng), `docs/V2_RESULTS.md`, `docs/PROJECT_STATUS.md`, `docs/EVALUATION_ARCHITECTURE.md`, `CLAUDE.md`. Bản khoá luận `baocao.docx` nằm **ngoài repo** (`../baocao.docx`).

**Cái repo CÓ** — `docs/V2_RESULTS.md` §2 "Bậc thang baseline (E2a)", **chỉ hai trong bốn thang đo**:

| Hệ | F1 Khoản | NormR | F1 Điều | Từ chối đúng |
|---|---:|---:|---:|---:|
| oracle (trần) | 0.858 | 0.955 | KHÔNG CÓ | KHÔNG CÓ |
| **GraphRAG v2** | **0.578** | 0.771 | KHÔNG CÓ | KHÔNG CÓ |
| bm25 | 0.571 | 0.808 | KHÔNG CÓ | KHÔNG CÓ |
| baseline (naive RAG) | 0.435 | 0.588 | KHÔNG CÓ | KHÔNG CÓ |
| closed-book | 0.102 | 0.102 | KHÔNG CÓ | KHÔNG CÓ |

*Nguồn: `docs/V2_RESULTS.md` §2. Ghi chú tại chỗ: "oracle/bm25/closed-book lấy từ mẻ v1 — Fix A không đụng các hệ này."*

**Bốn thang đo đầy đủ cho hai hệ GraphRAG và Naive RAG** — tính lại bằng `aggregate` trên chính cặp file mà sáu ô dùng làm nguồn ngữ cảnh:

| Hệ (Gemini 2.5 Pro, mẻ `20260710-085236`) | F1 Khoản | F1 Điều | Norm Recall | Từ chối đúng |
|---|---:|---:|---:|---:|
| GraphRAG | **0.581423** | **0.598472** | **0.793187** | **0.928571 (13/14)** |
| Naive RAG | **0.426975** | **0.448386** | **0.594282** | **0.785714 (11/14)** |

Số phụ của cặp file này: `total_elapsed_s` graphrag 3 012.8 · baseline 3 440.7; `latency_mean_s` graphrag 21.989927 · baseline 25.113504; số câu có GT khác rỗng = 123 ở cả hai; số câu trong 123 đó thực sự sinh ra ≥ 1 citation: graphrag **117**, baseline **92**.

> **Oracle / BM25 / closed-book: KHÔNG CÓ F1 Điều và Từ chối đúng trong repo.** Nếu Bảng 4.13 cần bốn cột cho cả năm hệ thì hai cột đó phải lấy từ **Bảng 4.5 của `baocao.docx`**, hoặc tính lại từ results JSON của mẻ v1 nếu file còn trong `data/evaluation/`.

---

## 9. BẢNG SỐ SẴN DÙNG

Mỗi dòng một con số. Cột "Nguồn" là file đọc ra nó.

### 9.1 Ma trận sáu ô

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| 0.402 | F1 Khoản — ft, 0-shot, GraphRAG (ô 1) | `finetune/results/results_graphrag_ft06-ft-s0.json` → `aggregate.f1_mean` |
| 0.445 | F1 Điều — ô 1 | như trên, `f1_dieu_mean` |
| 0.541 | Norm Recall — ô 1 | như trên, `norm_recall_mean` |
| 13/14 = 0.929 | Từ chối đúng — ô 1 | như trên, `negative_correct_rate` |
| 0.301 | F1 Khoản — ft, 0-shot, Naive (ô 2) | `finetune/results/results_baseline_ft06-ft-s0.json` |
| 0.344 | F1 Điều — ô 2 | như trên |
| 0.609 | Norm Recall — ô 2 | như trên |
| 8/14 = 0.571 | Từ chối đúng — ô 2 | như trên |
| 0.493 | F1 Khoản — base, 2-shot, GraphRAG (ô 3) | `finetune/results/results_graphrag_ft06-base-s2.json` |
| 0.536 | F1 Điều — ô 3 | như trên |
| 0.630 | Norm Recall — ô 3 | như trên |
| 12/14 = 0.857 | Từ chối đúng — ô 3 | như trên |
| 0.239 | F1 Khoản — base, 2-shot, Naive (ô 4) | `finetune/results/results_baseline_ft06-base-s2.json` |
| 0.315 | F1 Điều — ô 4 | như trên |
| 0.599 | Norm Recall — ô 4 | như trên |
| 7/14 = 0.500 | Từ chối đúng — ô 4 | như trên |
| 0.136 | F1 Khoản — base, 0-shot, GraphRAG (ô 5) | `finetune/results/results_graphrag_ft06-base-s0.json` |
| 0.136 | F1 Điều — ô 5 | như trên |
| 0.137 | Norm Recall — ô 5 | như trên |
| 13/14 = 0.929 | Từ chối đúng — ô 5 | như trên |
| 0.154 | F1 Khoản — base, 0-shot, Naive (ô 6) | `finetune/results/results_baseline_ft06-base-s0.json` |
| 0.170 | F1 Điều — ô 6 | như trên |
| 0.265 | Norm Recall — ô 6 | như trên |
| 13/14 = 0.929 | Từ chối đúng — ô 6 | như trên |

### 9.2 Cột Δ và tỉ lệ tương đối

| Giá trị | Ý nghĩa | Nguồn |
|---:|---|---|
| +0.102 | Δ F1 Khoản — hàng ft 0-shot | ô 1 − ô 2 |
| +0.254 | Δ F1 Khoản — hàng base 2-shot | ô 3 − ô 4 |
| −0.018 | Δ F1 Khoản — hàng base 0-shot | ô 5 − ô 6 |
| +0.143 | Δ F1 Khoản — hàng Gemini (mean N=3) | `docs/V2_RESULTS.md` §1 |
| +0.154 | Δ F1 Khoản — hàng Gemini (cặp file đã đóng băng) | `aggregate` trên `data/evaluation/results_*_20260710-085236.json` |
| 1.338 | Tỉ lệ GraphRAG/Naive — hàng ft 0-shot | tính từ ô 1 / ô 2 |
| 2.060 | Tỉ lệ GraphRAG/Naive — hàng base 2-shot | ô 3 / ô 4 |
| 0.886 | Tỉ lệ GraphRAG/Naive — hàng base 0-shot | ô 5 / ô 6 |
| 1.329 | Tỉ lệ GraphRAG/Naive — Gemini (mean N=3) | 0.578 / 0.435 |
| 1.362 | Tỉ lệ GraphRAG/Naive — Gemini (cặp file đã đóng băng) | 0.581423 / 0.426975 |
| −0.068 | Δ Norm Recall — hàng ft 0-shot (**âm**) | ô 1 − ô 2 |
| −0.091 | Δ F1 Khoản: ft 0-shot GraphRAG so với base 2-shot GraphRAG (**tinh chỉnh thua**) | 0.402433 − 0.492631 |

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
| 0.073 | `format_ok_rate` thấp nhất (ô 5) | `results_graphrag_ft06-base-s0.json` |
| 0.894 | `format_ok_rate` cao nhất (ô 2 và ô 4) | hai file baseline tương ứng |
| 0.732 | `format_ok_rate` ô 1 | `results_graphrag_ft06-ft-s0.json` |
| 0.813 | `format_ok_rate` ô 3 | `results_graphrag_ft06-base-s2.json` |
| 1.000 | `soft_article_hit` ô 3 (giá trị cao nhất) | như trên |
| 0.928 | `soft_article_hit` ô 6 (giá trị thấp nhất) | `results_baseline_ft06-base-s0.json` |
| 1 | Số câu chạm trần token trong 822 lượt (`V020`, ô 2) | `replay.ids_hit_token_cap` |
| 2 048 | `n_tokens_out` của `V020` = `max_new_tokens` | item `V020` trong `results_baseline_ft06-ft-s0.json` |

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
| 16 | LoRA `r` | `finetune/run.sh:290` |
| 32 | LoRA `alpha` | `finetune/run.sh:291` |
| 0.0 | LoRA dropout | `finetune/train_qlora.py:240` |
| 7 | Số `target_modules` | `finetune/train_qlora.py:243-244` |
| 2e-4 | Learning rate | `finetune/train_qlora.py:62` |
| 0.03 | `warmup_ratio` | `finetune/train_qlora.py:170` |
| 0.01 | `weight_decay` | `finetune/train_qlora.py:173` |
| 2 | Số epoch | `finetune/run.sh:67` |
| 1 | `per_device_train_batch_size` | `finetune/train_qlora.py:165` |
| 16 | `gradient_accumulation_steps` (batch hiệu dụng = 16) | `finetune/train_qlora.py:65` |
| 16 384 | `max_seq_length` | `finetune/run.sh:66` |
| 42 | Seed (dữ liệu, LoRA init, trainer, sinh văn bản) | `build_dataset.py:87`; `train_qlora.py:67`; `replay` `gen_params.seed` |

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
| 7 498 / 6 818 / 11 001 | mean / p50 / p95 độ dài tổng chuỗi huấn luyện | `dataset_stats.md` §2.2 |
| 0 | Số mẫu huấn luyện vượt trần 16 384 | `dataset_stats.md` §2.2 |
| 12 011 | Prompt dài nhất trên 127 câu GraphRAG (Qwen2.5) | `token_budget.md` §2.1 |
| 12 011 | Prompt dài nhất backend đo được ở ô 1 / ô 5 | `n_tokens_prompt_backend` trong hai file results |
| 6 432 | Prompt dài nhất backend ở ô 2 / ô 6 | như trên |
| 12 389 | Prompt dài nhất backend ở ô 3 (2-shot) | `results_graphrag_ft06-base-s2.json` |
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
| 0.581423 | F1 Khoản GraphRAG, mẻ `20260710-085236` | `aggregate` trên `data/evaluation/results_graphrag_20260710-085236.json` |
| 0.598472 | F1 Điều GraphRAG, mẻ đó | như trên |
| 0.793187 | Norm Recall GraphRAG, mẻ đó | như trên |
| 13/14 | Từ chối đúng GraphRAG, mẻ đó | như trên |
| 0.426975 | F1 Khoản Naive, mẻ đó | `data/evaluation/results_baseline_20260710-085236.json` |
| 0.448386 | F1 Điều Naive, mẻ đó | như trên |
| 0.594282 | Norm Recall Naive, mẻ đó | như trên |
| 11/14 | Từ chối đúng Naive, mẻ đó | như trên |
| 0.578 ± 0.004 | F1 Khoản GraphRAG, mean ± σ N=3 | `docs/V2_RESULTS.md` §1 |
| 0.435 ± 0.008 | F1 Khoản Naive, mean ± σ N=3 | `docs/V2_RESULTS.md` §1 |
| 0.771 ± 0.016 | Norm Recall GraphRAG, N=3 | `docs/V2_RESULTS.md` §1 |
| [0.061, 0.225] | CI 95 % của Δ F1 Khoản (bootstrap 10 000, seed 42) | `docs/V2_RESULTS.md` §1 |
| 0.0015 | Wilcoxon p | `docs/V2_RESULTS.md` §1 |
| 65 / 36 / 22 | Win / Loss / Tie trên 123 câu | `docs/V2_RESULTS.md` §1 |
| 0.858 / 0.955 | F1 Khoản / NormR — oracle | `docs/V2_RESULTS.md` §2 |
| 0.571 / 0.808 | F1 Khoản / NormR — bm25 | `docs/V2_RESULTS.md` §2 |
| 0.102 / 0.102 | F1 Khoản / NormR — closed-book | `docs/V2_RESULTS.md` §2 |

---

## KIỂM CUỐI

### A. File đã đọc

**Kế hoạch và tài liệu**

| File | Đọc phần nào |
|---|---|
| `docs/FINETUNE_EXECUTION_PLAN.md` (v2.3.4, 970 dòng) | toàn bộ |
| `docs/FT_SYNTHESIS_B_KHOKHAN.md` | toàn bộ (để xác định ranh giới) |
| `docs/V2_RESULTS.md` | toàn bộ |
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
| `ft06_matrix.md` (102 dòng) | toàn bộ |
| `ft06_gpu_info.json` | toàn bộ |
| `ft06_artifacts.json` | toàn bộ |
| `ft06_run_status.json`, `…_gpu0.json`, `…_gpu1.json` | toàn bộ |
| `ft06_chat_template_base.jinja`, `…_ft.jinja` | độ dài + sha256 (theo yêu cầu) |
| `ft06_prompt_{graphrag,baseline}_s{0,2}.txt` | kích thước file; nội dung đối chiếu qua results JSON tương ứng |
| `samples_20.txt` | chỉ kích thước (319 152 B) |

**Kết quả `finetune/results/` — 10 file JSON, tất cả đã chạy qua `metrics.aggregate`**

`results_graphrag_ft06-ft-s0.json` · `results_baseline_ft06-ft-s0.json` · `results_graphrag_ft06-base-s2.json` · `results_baseline_ft06-base-s2.json` · `results_graphrag_ft06-base-s0.json` · `results_baseline_ft06-base-s0.json` · `results_graphrag_ft06-gate-prompt-s0.json` · `results_graphrag_ft06-gate-prompt-s2.json` · `results_baseline_ft06-gate-prompt-s0.json` · `results_baseline_ft06-gate-prompt-s2.json`

**Mã nguồn**

| File | Đọc phần nào |
|---|---|
| `finetune/train_qlora.py` | toàn bộ (373 dòng) |
| `finetune/run.sh` | toàn bộ (407 dòng) |
| `finetune/kaggle_ft06.py` | dòng 1-115, 190-260, 659-720; grep toàn bộ cấu trúc chặng |
| `finetune/build_dataset.py` | hằng số (76-182), `to_record` (632-650), `build`/`make` (656-800), `kiem_tra` (887-915), `tach_train_val` (921-936); danh sách hàm đầy đủ |
| `finetune/replay.py` | `GenParams` (155-175) |
| `finetune/slug.py` | danh sách hàm |
| `src/evaluation/metrics.py` | `aggregate` (189-260) |

**Dữ liệu và hiện vật khác**

`finetune/data/train.jsonl` (đếm dòng) · `finetune/data/val.jsonl` (đếm dòng) · `finetune/data/train.jsonl.sha256` · `finetune/data/val.jsonl.sha256` · `finetune/logs/ft06_gpu0.log` · `finetune/logs/ft06_gpu1.log` · `data/evaluation/results_graphrag_20260710-085236.json` · `data/evaluation/results_baseline_20260710-085236.json` · `../results/ft06_constraints.txt` · `../results/__huggingface_repos__.json` · `../results/repo/.git/{refs,logs,packed-refs}` · git log của repo chính.

### B. File KHÔNG tìm được

| File | Đã tìm ở | Ảnh hưởng tới mục nào |
|---|---|---|
| `adapter/train_result.json` | `finetune/{results,reports,logs,models,data,notebooks}/`, gốc repo, `../results/`; `find . -iname "train_result*.json"` | **§5 gần như trống** — mất `train_loss`, `train_runtime`, `samples/s`, `steps/s`, `total_flos`, `eval_history` |
| `adapter/length_stats.json` | như trên; `find . -iname "*length_stats*.json"` | §3.4 chỉ có nguồn A (tokenizer Qwen2.5), không đối chiếu được với tokenizer thật |
| `adapter/val_length_stats.json` | như trên | như trên |
| Hai file log huấn luyện (`$WORK/{RUN_NAME}.log`) | `finetune/logs/` chỉ có `ft06_gpu{0,1}.log` (log **phiên 3**); `find . -iname "*.log"` → đúng hai file đó | §2.3 (số layer vá, số tham số huấn luyện, tỉ lệ token bị che), §4.1 (GPU thật, thời gian), §5 (loss theo bước) |
| `adapter/adapter_config.json` | `find . -iname "adapter_config.json"` → chỉ khớp hai dòng log HTTP 404 trong notebook cũ | §0 mục 3 — không xác nhận được `r`/`alpha` thực nạp |
| 4 file results JSON của phiên 1 (FT-03) | `finetune/results/` (chỉ có 10 file `ft06-*`) | §7.2 — không so được độ dài prompt ở cấp câu |
| `finetune/results/prompt_gate-s0-pp10.txt`, `prompt_gate-s2-pp10.txt` | `finetune/results/`, `finetune/reports/` | §7.2 |
| Bảng 4.5 với bốn thang đo đầy đủ | `docs/` (không có `docs/thesis/`), `thesis/` (rỗng), `docs/V2_RESULTS.md` | §8 — F1 Điều và Từ chối đúng của oracle/bm25/closed-book |
| Giấy phép bộ dữ liệu `thangvip/vietnamese-legal-qa` | `finetune/README.md`, `dataset_stats.md`, `dataset_build.json`, `build_dataset.py`, kế hoạch | §3.1 |

### C. Mọi chỗ hai nguồn lệch nhau

Bốn chỗ, liệt kê đầy đủ ở **§0**:

1. Hàng Gemini: 0.578 / 0.435 (mean N=3) so với 0.581423 / 0.426975 (cặp file đã đóng băng) — Δ +0.143 so với +0.154448.
2. Δ và mức ý nghĩa của Bảng 4.3: `CLAUDE.md` ghi +0.156 / p = 0.001 \*\*\*; `V2_RESULTS.md` đính chính ngày 28/07/2026 thành +0.143 / p = 0.0015 \*\* — **bản đính chính là số mới nhất**.
3. LoRA `r`/`alpha`: mặc định script 32/64 so với `run.sh` truyền 16/32 — giá trị đã chạy là 16/32, chưa xác minh được bằng `adapter_config.json`.
4. Phân bố độ dài mẫu huấn luyện: chỉ có bản đo bằng tokenizer Qwen2.5; bản đo bằng tokenizer thật (`length_stats.json`) thiếu.

Chỗ **không** lệch, đã kiểm chéo và khớp: sáu con số `aggregate` của `ft06_matrix.md` §1 khớp kết quả tính lại tới ba chữ số; `ft06_run_status.json` khớp cả sáu ô; ba cặp độ trễ ở `ft06_matrix.md` §4 khớp phép tính lại; per-gap và per-theme của mẻ Gemini khớp `V2_RESULTS.md` §3 và §4; `dataset_build.json` khớp `dataset_stats.md` §1; system prompt 3 936 token khớp giữa `token_budget.md` §2.2 và `dataset_stats.md` §2; max prompt 12 011 token khớp giữa `token_budget.md` §2.1 và backend phiên 3.

### D. Chỗ phải dừng vì không đủ dữ kiện

| # | Việc | Lý do dừng |
|---:|---|---|
| 1 | §5 — bảng `train_loss` / `eval_loss` theo epoch, `runtime`, `samples/s`, `steps/s`, `total_flos`, tỉ lệ token bị che | Bốn hiện vật nguồn đều không có trong repo (mục B). Hai giá trị `eval_loss` duy nhất còn lại (0.3129 / 0.3082) **chỉ tồn tại trong tài liệu tóm tắt Phần B**, không có file gốc để xác minh |
| 2 | §5 — bảng loss theo mốc ~50 bước và file CSV | Chuỗi `log_history` không có trong repo |
| 3 | §2 — số layer được vá, số tham số huấn luyện được so với tổng | Chỉ in ra log huấn luyện, log không có |
| 4 | §2 — xác nhận `r`/`alpha` thực nạp | `adapter_config.json` không có |
| 5 | §4.1 — loại GPU thật và thời gian của phiên 2, chi phí thuê | Không file nào trong repo ghi |
| 6 | §7 — commit code của phiên 2, loại card của phiên 1 | Không file nào trong repo ghi |
| 7 | §7.2 — so độ dài prompt 2-shot phiên 1 với phiên 3 **ở cấp câu** | Phiên 1 chỉ ghi giá trị max trên 15 câu; 4 file results và 2 file dump prompt của phiên 1 không có trong repo. Chỉ so được phụ trội few-shot (412 token, khớp) |
| 8 | §8 — F1 Điều và Từ chối đúng cho oracle / bm25 / closed-book | Repo chỉ có hai trong bốn thang đo cho ba hệ này |
| 9 | §3.1 — giấy phép bộ dữ liệu nguồn | Không ghi ở bất kỳ file nào |
