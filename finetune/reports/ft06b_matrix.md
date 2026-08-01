# TASK-FT-06 — Ma trận mục 4.7: ba mô hình sinh × hai khuôn ngữ cảnh

Sinh bởi `finetune/kaggle_ft06.py --stage table`. Mọi con số ở bảng 1 do
`src/evaluation/metrics.py::aggregate` tính (dòng 189-256) — script này KHÔNG
tự tính lại thang đo nào, và KHÔNG ghim số cứng chép từ báo cáo.

- Nguồn ngữ cảnh: `data/evaluation/results_graphrag_final1_20260729-022916.json` (GraphRAG) và
  `data/evaluation/results_baseline_20260710-085236.json` (Naive RAG) — **hai mẻ khác nhau, có chủ ý**.
  Vế Naive RAG không đi qua bộ lập kế hoạch truy vấn (`naive_rag.py:339,361`
  truyền `query_plan=None`) nên sửa đổi ở tầng đó không chạm tới nó và nó
  không cần chạy lại; vế GraphRAG lấy ngữ cảnh mới sau khi sửa (`V3_RESULTS.md`
  §1). Truy hồi vẫn đóng băng ở cả sáu ô — mỗi ô chỉ đổi mô hình sinh.
- Tham số sinh: bộ đã chốt ở `gate_base_model.md` §3 (temperature 0.7 · top_p 0.8
  · top_k 20 · min_p 0 · **presence_penalty 0** · seed 42 · max_new_tokens 2048
  · n_ctx 16384 · n_gpu_layers −1), giống hệt nhau ở cả sáu ô.
- `finetune/data/mode_map.json` ghim cố định (13 id `irac`), CHUNG cho lượt
  trước và lượt này — `mode` là đầu vào của khâu sinh, để nó trôi theo mẻ thì
  Δ trong cùng một hàng lẫn cả khác biệt chế độ.

## 1. Bốn thang đo của Bảng 4.5

| Mô hình sinh | Hệ truy hồi | N | F1 cấp Khoản | F1 cấp Điều | Norm Recall | Từ chối đúng | Δ (F1 Khoản) | Tỉ lệ G/N |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 2.5 Pro | Naive RAG | 4 ⚠️ | 0.436 ± 0.008 | 0.459 ± 0.008 | 0.585 ± 0.008 | 0.786 ± 0.000 | | |
| Gemini 2.5 Pro | GraphRAG | 3 | 0.617 ± 0.001 | 0.638 ± 0.003 | 0.829 ± 0.006 | 0.929 ± 0.000 | **+0.181** | 1.416 |
| Cục bộ gốc, 0-shot | Naive RAG | 1 | 0.154 | 0.170 | 0.265 | 0.929 (13/14) |  |  |
| Cục bộ gốc, 0-shot | GraphRAG | 1 | 0.131 | 0.131 | 0.134 | 0.929 (13/14) | **-0.022** | 0.854 |
| Cục bộ gốc, 2-shot | Naive RAG | 1 | 0.239 | 0.315 | 0.599 | 0.500 (7/14) |  |  |
| Cục bộ gốc, 2-shot | GraphRAG | 1 | 0.511 | 0.562 | 0.656 | 0.857 (12/14) | **+0.272** | 2.137 |
| Cục bộ đã tinh chỉnh, 0-shot | Naive RAG | 1 | 0.301 | 0.344 | 0.609 | 0.571 (8/14) |  |  |
| Cục bộ đã tinh chỉnh, 0-shot | GraphRAG | 1 | 0.402 | 0.449 | 0.567 | 0.929 (13/14) | **+0.101** | 1.336 |

### 1.1 Cơ sở của cột **Tỉ lệ G/N** — MỘT cơ sở duy nhất cho mọi hàng

Tỉ lệ = `aggregate.f1_mean` (GraphRAG) chia `aggregate.f1_mean` (Naive RAG),
**cả hai tính trên TOÀN BỘ 137 câu của file kết quả**, gồm cả 14 câu phủ định.
Hàng Gemini lấy trung bình `f1_mean` của các mẻ rồi mới chia.

Ghi rõ vì báo cáo trước **trộn hai cơ sở** trong cùng một bảng: tỉ lệ của hàng
Gemini tính trên 123 câu ghép cặp (đã loại câu phủ định), còn tỉ lệ của hàng
cục bộ tính trên aggregate đầy đủ. Hai cơ sở cho hai con số không so được với
nhau, mà bảng lại xếp chúng cạnh nhau như thể so được. Ở đây mọi hàng dùng
aggregate đầy đủ — chọn nó vì đó là đại lượng mà cả sáu ô cục bộ đều có sẵn,
không phải vì nó tốt hơn. Muốn dùng cơ sở 123 câu ghép cặp thì phải đổi cho
**cả bảng**, không đổi cho một hàng.

### 1.2 Vì sao N của hàng Gemini khác N của hàng cục bộ

Mô hình cục bộ chạy qua llama.cpp với `seed` cố định trên phần cứng đã ghim →
**tất định theo seed**: ở phiên 1, hai lần chạy cùng seed cho câu trả lời trùng
khít 15/15. Với một quá trình tất định thì N=1 đã là bức tranh đầy đủ, chạy
thêm chỉ tốn giờ GPU để chép lại cùng một file.

Gemini thì có yếu tố ngẫu nhiên không tắt được, nên hàng đó báo trung bình ±
độ lệch chuẩn qua nhiều lần **sinh trên CÙNG một ngữ cảnh đông cứng** — ba mẻ
`final1/2/3` có `context` trùng khít 137/137, tức độ lệch chuẩn ở đây đo đúng
một thứ: dao động của mô hình sinh, không lẫn dao động của truy hồi.

### 1.3 Hàng Gemini · GraphRAG — ba mẻ, giá trị lẻ

| Mẻ | F1 cấp Khoản | F1 cấp Điều | Norm Recall | Từ chối đúng |
|---|---:|---:|---:|---:|
| `data/evaluation/results_graphrag_final1_20260729-022916.json` | 0.6162 | 0.6394 | 0.8273 | 0.929 (13/14) |
| `data/evaluation/results_graphrag_final2_20260729-032225.json` | 0.6172 | 0.6345 | 0.8358 | 0.929 (13/14) |
| `data/evaluation/results_graphrag_final3_20260729-041450.json` | 0.6180 | 0.6392 | 0.8236 | 0.929 (13/14) |

Trung bình ± độ lệch chuẩn trên 3 mẻ (chính là hàng Gemini ·
GraphRAG của bảng 1). Ba giá trị lẻ in ở đây để kiểm lại được bằng tay.

Độ lệch chuẩn ở đây là **độ lệch chuẩn MẪU** (`statistics.stdev`, chia n−1).
`docs/V3_RESULTS.md` dùng độ lệch chuẩn tổng thể (chia n), nên chữ số cuối có
thể lệch — vd Norm Recall 0.006 ở đây so với 0.005 ở đó. Cùng dữ liệu, khác
quy ước; ghi ra để không ai đi tìm một sai lệch không tồn tại.

### 1.4 Hàng Gemini · Naive RAG — MỌI mẻ tìm thấy, không chọn lọc

Quét `data/evaluation/results_baseline_*.json`: tìm thấy **13** file.

| Mẻ | số câu | F1 cấp Khoản | F1 cấp Điều | Norm Recall | Từ chối đúng |
|---|---:|---:|---:|---:|---:|
| `data/evaluation/results_baseline_20260517-184216.json` | 19 | 0.3890 | 0.3890 | 0.6798 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260517-220253.json` | 19 | 0.4277 | 0.4277 | 0.8553 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260517-221821.json` | 19 | 0.4277 | 0.4277 | 0.8553 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260517-222919_v9_final.json` | 19 | 0.3891 | 0.3891 | 0.7193 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260517-224158_runB_schemaBOnly.json` | 19 | 0.3617 | 0.3617 | 0.7632 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260519-131935.json` | 26 | 0.2848 | 0.2848 | 0.7372 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260519-161509.json` | 26 | 0.2848 | 0.2848 | 0.7372 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260519-204426.json` | 26 | 0.2948 | 0.2948 | 0.6987 | 1.000 (2/2) |
| `data/evaluation/results_baseline_20260709-073933.json` | 137 | 0.4381 | 0.4566 | 0.5773 | 0.786 (11/14) |
| `data/evaluation/results_baseline_20260710-001154.json` | 137 | 0.4325 | 0.4640 | 0.5809 | 0.786 (11/14) |
| `data/evaluation/results_baseline_20260710-085236.json` | 137 | 0.4270 | 0.4484 | 0.5943 | 0.786 (11/14) |
| `data/evaluation/results_baseline_20260710-104109.json` | 137 | 0.4456 | 0.4657 | 0.5882 | 0.786 (11/14) |
| `data/evaluation/results_baseline_reused_20260517-181339.json` | 19 | 0.4035 | 0.4035 | 0.7763 | 1.000 (2/2) |

**Trung bình ± độ lệch chuẩn trên TOÀN BỘ các mẻ tìm được** (N=13, số câu gặp phải: [19, 26, 137]): F1 Khoản 0.385 ± 0.060 · F1 Điều 0.392 ± 0.067 · NormR 0.705 ± 0.098.

**Con số đó KHÔNG dùng được** và không phải cái nằm ở bảng 1: nó gộp nhiều bộ
câu hỏi khác nhau vào một trung bình. In ra vì đề bài yêu cầu liệt kê hết,
không giấu mẻ nào.

Hàng "Gemini 2.5 Pro · Naive RAG" của bảng 1 lấy các mẻ có **cùng 137 câu**
với `data/evaluation/results_baseline_20260710-085236.json` — 4 mẻ, N=4:

- `data/evaluation/results_baseline_20260709-073933.json`
- `data/evaluation/results_baseline_20260710-001154.json`
- `data/evaluation/results_baseline_20260710-085236.json`
- `data/evaluation/results_baseline_20260710-104109.json`

F1 Khoản 0.436 ± 0.008 · F1 Điều 0.459 ± 0.008 · NormR 0.585 ± 0.008.

> ### ⚠️ HÀNG NAIVE RAG PHẢI ĐƯỢC XÁC NHẬN TRƯỚC KHI VÀO KHOÁ LUẬN
>
> `docs/V3_RESULTS.md` §3 viết "trung bình từng câu qua cả **3 mẻ của mỗi hệ**"
> nhưng **không ghi ba mẻ baseline nào**. Script này KHÔNG tự chọn ba mẻ — tự
> chọn là dựng lại đúng cái mập mờ đang cần gỡ, và ba mẻ khác nhau cho ba con
> số khác nhau ở mẫu số của cột Tỉ lệ G/N.
>
> Cái nó làm là một phép **lọc theo số câu** (137 câu), không phải phép
> chọn mẻ: hiện lọc ra 4 mẻ chứ không phải 3. Nếu ba mẻ đúng là ba
> trong số đó thì con số ở bảng 1 sẽ đổi. Người phụ trách phải chỉ đúng ba mẻ.
>
> Ký hiệu ⚠️ ở cột N của hàng đó nhắc lại đúng điều này.

## 2. Sức khoẻ từng ô — đọc TRƯỚC khi tin bảng 1

| Ô | Mô hình | n_shot | Hệ | `format_ok_rate` | `n_hit_token_cap` | `soft_article_hit` | qua mô hình | file |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | ft | 0 | graphrag | 0.756 (mẫu số 123) | 0 | 0.980 | 127/137 | `finetune/results/results_graphrag_ft06b-ft-s0.json` |
| 2 | ft | 0 | baseline | 0.894 (mẫu số 123) | 1 | 0.965 | 137/137 | `finetune/results/results_baseline_ft06b-ft-s0.json` |
| 3 | base | 2 | graphrag | 0.854 (mẫu số 123) | 0 | 1.000 | 127/137 | `finetune/results/results_graphrag_ft06b-base-s2.json` |
| 4 | base | 2 | baseline | 0.894 (mẫu số 123) | 0 | 0.946 | 137/137 | `finetune/results/results_baseline_ft06b-base-s2.json` |
| 5 | base | 0 | graphrag | 0.065 (mẫu số 123) | 0 | 0.991 | 127/137 | `finetune/results/results_graphrag_ft06b-base-s0.json` |
| 6 | base | 0 | baseline | 0.211 (mẫu số 123) | 0 | 0.928 | 137/137 | `finetune/results/results_baseline_ft06b-base-s0.json` |

### ⚠️ CẢNH BÁO — có ô chạm trần token

- **ô 2: ft n_shot=0 baseline**: 1 câu chạm trần (`V020`)

Khối trích dẫn nằm **CUỐI** câu trả lời, nên chạm trần `max_new_tokens` là
mất citation vì lý do **thuần kỹ thuật** — không phải vì mô hình không biết
luật. **Mọi con số của những ô này ở bảng 1 phải đọc lại** trước khi đưa vào
khoá luận (`gate_base_model.md` §4.2).

## 3. Ghim phần cứng — giá trị ghim thứ bảy

Kaggle cấp **T4 x2**. Với `--n-gpu-layers -1` và hai card nhìn thấy được,
llama.cpp tự chia layer qua cả hai. Q4_K_M chỉ 2,4 GB nên chia **không nhanh
hơn**, mà đổi thứ tự rút gọn → có thể lệch số học; và cái nguy hiểm thật là
**không nhất quán giữa các ô**, khi đó cột Δ đo lẫn cả khác biệt phần cứng.
Nên mọi lời gọi `replay.py` ghim đúng **một** card qua `CUDA_VISIBLE_DEVICES`
của subprocess.

```
index, name, memory.total [MiB]
0, Tesla T4, 15360 MiB
1, Tesla T4, 15360 MiB
```

- số card nhìn thấy được: **2**
- chế độ đã dùng: **song song, hai luồng, mỗi luồng một card** (ghi nhận lúc: run — thực tế)

| Ô | Mô hình | n_shot | Hệ | `CUDA_VISIBLE_DEVICES` |
|---:|---|---:|---|---:|
| 1 | ft | 0 | graphrag | 0 |
| 2 | ft | 0 | baseline | 0 |
| 3 | base | 2 | graphrag | 0 |
| 4 | base | 2 | baseline | 1 |
| 5 | base | 0 | graphrag | 1 |
| 6 | base | 0 | baseline | 1 |

**Ghi vào khoá luận cùng với sáu giá trị ghim kia.** Không ô nào chia layer qua hai card; không hai ô nào chạy cùng lúc trên cùng một card.

## 4. Đối chiếu `elapsed_seconds` giữa hai card

Trung bình **mỗi câu đi qua mô hình** (loại 10 câu hằng số của cột GraphRAG —
chúng có `elapsed = 0.0` nên nếu tính vào thì hai cột lệch nhau chỉ vì số câu
hằng số khác nhau, không vì phần cứng).

| Cặp ô (cùng model + cùng n_shot) | GraphRAG s/câu | Naive s/câu | Lệch | Card | Kết luận |
|---|---:|---:|---:|---|---|
| ô 1+2 · ft n_shot=0 | 13.05 | 8.97 | 45% | 0 vs 0 | cùng card — lệch không quy về throttle |
| ô 3+4 · base n_shot=2 | 18.84 | 10.31 | 83% | 0 vs 1 | ⚠️ **LỆCH 83% > 25% TRÊN HAI CARD KHÁC NHAU** |
| ô 5+6 · base n_shot=0 | 22.67 | 12.72 | 78% | 1 vs 1 | cùng card — lệch không quy về throttle |

### ⚠️ CẢNH BÁO — nghi một card bị throttle

- **ô 3+4 · base n_shot=2**: 18.84 s/câu (card 0) vs 10.31 s/câu (card 1) — lệch 83%

Hai ô cùng model + cùng `n_shot` chỉ khác nguồn ngữ cảnh thì khối lượng tính
toán mỗi câu KHÔNG chênh tới mức này (prompt GraphRAG dài hơn Naive nên chênh
vài phần trăm là bình thường; hai chục phần trăm thì không). Trên hai card
khác nhau, cách giải thích đơn giản nhất là **một card bị throttle** — hệ quả:
`latency_mean_s` của Bảng 4.13 **không so được** giữa các hàng, phải ghi chú
hoặc chạy lại cả hai ô của cặp trên cùng một card (`--cells` + bỏ `--parallel`).

## 5. Tập câu ĐỔI NGỮ CẢNH giữa hai lượt

So `context` từng câu giữa `data/evaluation/results_graphrag_20260710-085236.json` (cũ) và
`data/evaluation/results_graphrag_final1_20260729-022916.json` (mới): **17 câu** khác nhau.

Con số này do chặng `table` **tự tính lại** từ hai file, không chép từ báo
cáo nào. Vế Naive RAG không có mục tương ứng: nó không đi qua bộ lập kế
hoạch truy vấn (`naive_rag.py:339,361`) nên không câu nào đổi ngữ cảnh.

| id | `theme` | `gap_type` | `jurisdiction` | ký tự ngữ cảnh (cũ → mới) |
|---|---|---|---|---:|
| V006 | ho-tich | gap2 | tp-hcm | 10,193 → 12,027 |
| V007 | ho-tich | gap2 | dong-nai | 10,193 → 13,734 |
| V008 | ho-tich | gap2 | dong-nai | 10,213 → 12,666 |
| V019 | ho-tich | gap2 | dong-nai | 9,813 → 13,968 |
| V024 | ho-tich | gap3 | toan-quoc | 5,691 → 10,196 |
| V040 | ho-tich | gap4 | toan-quoc | 11,537 → 11,021 |
| V043 | dat-dai | gap4 | toan-quoc | 6,770 → 10,368 |
| V044 | dat-dai | gap4 | tp-hcm | 11,412 → 3,356 |
| V050 | dat-dai | gap4 | toan-quoc | 14,109 → 13,639 |
| V061 | ho-tich | gap3 | dong-nai | 8,962 → 12,752 |
| V062 | ho-tich | gap2 | tp-hcm | 9,861 → 10,370 |
| V067 | ho-tich | gap2 | dong-nai | 8,183 → 13,059 |
| V091 | ho-tich | gap1 | dong-nai | 9,796 → 13,337 |
| V095 | ho-tich | gap1 | toan-quoc | 9,654 → 7,831 |
| V126 | ho-tich | gap2 | tp-hcm | 11,457 → 13,304 |
| V127 | nuoi-con-nuoi | gap3 | toan-quoc | 10,945 → 6,790 |
| V143 | ho-tich | gap4 | toan-quoc | 10,897 → 12,744 |

Theo lĩnh vực: **dat-dai** 3 · **ho-tich** 13 · **nuoi-con-nuoi** 1

### 5.1 Ghép cặp trên ĐÚNG tập câu đó

Chỉ 17 câu trên. Hai cột khác nhau ĐÚNG MỘT thứ: ngữ cảnh mà mô hình
sinh nhận được. Cùng mô hình, cùng tham số sinh, cùng `mode`, cùng phần cứng.

**Câu hỏi bảng này trả lời: cải thiện truy hồi có CHUYỂN GIAO sang mô hình
sinh yếu hơn không?**

| Mô hình sinh | N (cũ/mới) | F1 Khoản cũ | F1 Khoản mới | Δ | F1 Điều cũ | F1 Điều mới | NormR cũ | NormR mới |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Gemini 2.5 Pro | 1/3 | 0.378 | 0.647 | **+0.270** | 0.378 | 0.647 | 0.441 | 0.824 |
| Cục bộ gốc, 2-shot | 1/1 | 0.361 | 0.469 | **+0.108** | 0.361 | 0.527 | 0.412 | 0.559 |
| Cục bộ đã tinh chỉnh, 0-shot | 1/1 | 0.239 | 0.224 | **-0.016** | 0.239 | 0.263 | 0.265 | 0.471 |

### 5.2 Câu bị GIẢM F1 giữa hai ngữ cảnh

Mọi câu có F1 cấp Khoản mới < cũ, cho cả ba hàng. Câu giảm ở **CẢ BA** hàng
được đánh dấu `⛔`: ba mô hình sinh rất khác nhau cùng tụt ở cùng một câu thì
cách giải thích tiết kiệm nhất là **ngữ cảnh mới của câu đó xấu đi**, tức hiện
tượng của TRUY HỒI, không phải của mô hình sinh.

| id | Gemini 2.5 Pro (cũ → mới) | Cục bộ gốc, 2-shot (cũ → mới) | Cục bộ đã tinh chỉnh, 0-shot (cũ → mới) | ghi chú |
|---|---:|---:|---:|---|
| V040 | 1.000 → 1.000 | 1.000 → 0.667 ↓ | 0.667 → 1.000 |  |
| V043 | 1.000 → 0.000 ↓ | 1.000 → 0.000 ↓ | 0.667 → 0.667 |  |
| V044 | 0.800 → 0.333 ↓ | 0.000 → 0.000 | 0.000 → 0.000 |  |
| V061 | 0.500 → 1.000 | 0.667 → 0.667 | 0.667 → 0.000 ↓ |  |
| V095 | 1.000 → 0.889 ↓ | 1.000 → 1.000 | 1.000 → 0.667 ↓ |  |
| V143 | 0.333 → 0.215 ↓ | 1.000 → 0.000 ↓ | 0.000 → 0.000 |  |

Số câu giảm: **Gemini 2.5 Pro** 4/17 · **Cục bộ gốc, 2-shot** 3/17 · **Cục bộ đã tinh chỉnh, 0-shot** 2/17 · **giảm ở cả ba hàng** 0

Đọc bảng này cùng 5.1: 5.1 nói cả tập đi lên hay đi xuống, 5.2 nói cái giá
phải trả — một thay đổi truy hồi cải thiện tổng thể vẫn có thể làm hỏng vài
câu, và những câu đó là chỗ phải xem bằng mắt.
