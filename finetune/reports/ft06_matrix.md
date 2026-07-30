# TASK-FT-06 — Ma trận mục 4.7: ba mô hình sinh × hai khuôn ngữ cảnh

Sinh bởi `finetune/kaggle_ft06.py --stage table`. Mọi con số ở bảng 1 do
`src/evaluation/metrics.py::aggregate` tính (dòng 195-260) — script này KHÔNG
tự tính lại thang đo nào.

- Nguồn ngữ cảnh: `data/evaluation/results_graphrag_20260710-085236.json` và `data/evaluation/results_baseline_20260710-085236.json` — **cùng một mẻ chạy**,
  chính mẻ sinh ra 0.578 / 0.435 ở hàng Gemini. Truy hồi đóng băng ở cả sáu ô.
- Tham số sinh: bộ đã chốt ở `gate_base_model.md` §3 (temperature 0.7 · top_p 0.8
  · top_k 20 · min_p 0 · **presence_penalty 0** · seed 42 · max_new_tokens 2048
  · n_ctx 16384 · n_gpu_layers −1), giống hệt nhau ở cả sáu ô.
- N=1 cho mọi ô cục bộ — chốt ở kế hoạch §TASK-FT-06 (tính tất định đã đo).

## 1. Bốn thang đo của Bảng 4.5

| Mô hình sinh | Hệ truy hồi | F1 cấp Khoản | F1 cấp Điều | Norm Recall | Từ chối đúng (x/14) | Δ (F1 Khoản) |
|---|---|---:|---:|---:|---:|---:|
| Gemini 2.5 Pro | Naive RAG | 0.435 | — | — | — | |
| Gemini 2.5 Pro | GraphRAG | 0.578 | — | — | — | **+0.143** |
| Cục bộ gốc, 0-shot | Naive RAG | 0.154 | 0.170 | 0.265 | 0.929 (13/14) |  |
| Cục bộ gốc, 0-shot | GraphRAG | 0.136 | 0.136 | 0.137 | 0.929 (13/14) | **-0.018** |
| Cục bộ gốc, 2-shot | Naive RAG | 0.239 | 0.315 | 0.599 | 0.500 (7/14) |  |
| Cục bộ gốc, 2-shot | GraphRAG | 0.493 | 0.536 | 0.630 | 0.857 (12/14) | **+0.254** |
| Cục bộ đã tinh chỉnh, 0-shot | Naive RAG | 0.301 | 0.344 | 0.609 | 0.571 (8/14) |  |
| Cục bộ đã tinh chỉnh, 0-shot | GraphRAG | 0.402 | 0.445 | 0.541 | 0.929 (13/14) | **+0.102** |

Hàng Gemini lấy từ báo cáo (kế hoạch §2). Ba cột còn lại của hàng đó để `—` có
chủ ý: chúng không nằm trong ba con số mà kế hoạch ghim, và điền bằng số lấy từ
chỗ khác (khác N, khác cách gộp) là trộn hai đại lượng. Lấy ở `docs/V2_RESULTS.md`
khi cần, và ghi rõ nguồn.

## 2. Sức khoẻ từng ô — đọc TRƯỚC khi tin bảng 1

| Ô | Mô hình | n_shot | Hệ | `format_ok_rate` | `n_hit_token_cap` | `soft_article_hit` | qua mô hình | file |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 1 | ft | 0 | graphrag | 0.732 (mẫu số 123) | 0 | 0.972 | 127/137 | `finetune/results/results_graphrag_ft06-ft-s0.json` |
| 2 | ft | 0 | baseline | 0.894 (mẫu số 123) | 1 | 0.965 | 137/137 | `finetune/results/results_baseline_ft06-ft-s0.json` |
| 3 | base | 2 | graphrag | 0.813 (mẫu số 123) | 0 | 1.000 | 127/137 | `finetune/results/results_graphrag_ft06-base-s2.json` |
| 4 | base | 2 | baseline | 0.894 (mẫu số 123) | 0 | 0.946 | 137/137 | `finetune/results/results_baseline_ft06-base-s2.json` |
| 5 | base | 0 | graphrag | 0.073 (mẫu số 123) | 0 | 0.991 | 127/137 | `finetune/results/results_graphrag_ft06-base-s0.json` |
| 6 | base | 0 | baseline | 0.211 (mẫu số 123) | 0 | 0.928 | 137/137 | `finetune/results/results_baseline_ft06-base-s0.json` |

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
| ô 1+2 · ft n_shot=0 | 12.47 | 8.63 | 44% | 0 vs 0 | cùng card — lệch không quy về throttle |
| ô 3+4 · base n_shot=2 | 18.33 | 9.45 | 94% | 0 vs 1 | ⚠️ **LỆCH 94% > 25% TRÊN HAI CARD KHÁC NHAU** |
| ô 5+6 · base n_shot=0 | 20.90 | 11.64 | 79% | 1 vs 1 | cùng card — lệch không quy về throttle |

### ⚠️ CẢNH BÁO — nghi một card bị throttle

- **ô 3+4 · base n_shot=2**: 18.33 s/câu (card 0) vs 9.45 s/câu (card 1) — lệch 94%

Hai ô cùng model + cùng `n_shot` chỉ khác nguồn ngữ cảnh thì khối lượng tính
toán mỗi câu KHÔNG chênh tới mức này (prompt GraphRAG dài hơn Naive nên chênh
vài phần trăm là bình thường; hai chục phần trăm thì không). Trên hai card
khác nhau, cách giải thích đơn giản nhất là **một card bị throttle** — hệ quả:
`latency_mean_s` của Bảng 4.13 **không so được** giữa các hàng, phải ghi chú
hoặc chạy lại cả hai ô của cặp trên cùng một card (`--cells` + bỏ `--parallel`).
