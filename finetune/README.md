# `finetune/` — Bổ sung mô hình sinh cục bộ vào Chương 4

Kế hoạch: [`docs/FINETUNE_EXECUTION_PLAN.md`](../docs/FINETUNE_EXECUTION_PLAN.md) (v2.3).

Nguyên tắc nền: **đóng băng truy hồi, chỉ đổi mô hình sinh.** Các file
`data/evaluation/results_*.json` đã lưu chuỗi `context` byte-identical với cái mô
hình sinh thực sự nhận → không cần Neo4j, không cần Qdrant, không gọi API.
Nếu ở bước nào thấy cần khởi động DB hoặc gọi Vertex AI thì **hướng đi đã sai**.

## Thư mục

| Đường dẫn | Nội dung |
|---|---|
| `replay.py` | Bộ phát lại (FT-02): đọc results JSON → dựng prompt → gọi mô hình → chấm bằng `src.evaluation.metrics` |
| `select_gate_ids.py` | Chọn 15 câu phân tầng cho gate FT-03 → `data/gate_ids.json` |
| `measure_token_budget.py` | FT-01A: đo ngân sách token thật |
| `recover_response_mode.py` | FT-01B: khôi phục `response_mode` → `data/mode_map.json` |
| `data/` | `mode_map.json`, `gate_ids.json` (`*.jsonl` bị gitignore) |
| `results/` | Đầu ra replay (`*_mock_*.json` và `*.partial.jsonl` bị gitignore) |
| `reports/` | `api_contract.md` (FT-00), `token_budget.md` (FT-01) |
| `models/` | Weights GGUF — **gitignore toàn bộ** |

## Trạng thái

| Task | Trạng thái |
|---|---|
| FT-00 hợp đồng API | ✅ `reports/api_contract.md` |
| FT-01 ngân sách token + `response_mode` | ✅ `reports/token_budget.md` |
| FT-02 bộ phát lại | ✅ `replay.py`, 48 test |
| **FT-03 gate** | 🟡 **code xong, chờ chạy trên Kaggle** |
| FT-04 → FT-07 | ⬜ chưa bắt đầu |

---

## FT-03 — Phiên 1: bốn lệnh sẽ chạy trên Kaggle

**Mô hình đã chốt (§9.5):** `Qwen/Qwen3-4B-Instruct-2507` — cửa sổ gốc 262 144
token, chỉ non-thinking, Unsloth có GGUF sẵn. **Không còn vòng sàng lọc ứng viên.**

⚠️ **Dùng bản Instruct, KHÔNG dùng bản base.** Hàng "cục bộ chưa tinh chỉnh" phải là
model biết follow instruction; bản base ra 0 vì lý do tầm thường, không đo được gì.

### Bộ 15 câu — dùng CHUNG cho cả bốn lần chạy

Sinh bởi `python -m finetune.select_gate_ids` → [`data/gate_ids.json`](data/gate_ids.json).
Tất định: cùng đầu vào cho cùng 15 id.

```
V078 V082 V132   gap1  (dat-dai / ho-tich / nuoi-con-nuoi)
V001 V006 V021   gap2
V023 V026 V030   gap3
V040 V043 V042   gap4
V005 V105 V117   negative  ← chỉ lấy từ 4 câu ĐÃ qua mô hình sinh
```

Mỗi nhóm phủ đủ 3 `theme` và 3 mức `difficulty`.

> **Bẫy phủ định:** V106–V113/V115/V116 bị loại. Chúng có `top_k_count=0`, `answer`
> là hằng số cứng ở `pipeline.py:233` — Gemini chưa từng được gọi. Đưa vào gate chỉ
> tốn chỗ mà không đo được gì về mô hình cục bộ.

> **Mẫu số `format_ok_rate` là 12, không phải 15.** 3 câu bẫy phủ định có
> `ground_truth_citations` rỗng nên bị loại khỏi mẫu số (kế hoạch §3.1).

### Bốn lệnh

Cùng **một** bộ 15 câu, cùng **một** model, cùng seed. Chỉ đổi hai trục:
`{--n-shot 0, --n-shot 2}` × `{presence_penalty 1.0, presence_penalty 0}`.

```bash
export GGUF=finetune/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
export SRC=data/evaluation/results_graphrag_20260710-085236.json
export IDS=$(python -c "import json;print(json.load(open('finetune/data/gate_ids.json',encoding='utf-8'))['ids_csv'])")

# 1) zero-shot, presence_penalty mặc định 1.0
python -m finetune.replay --input "$SRC" --model "$GGUF" --ids "$IDS" \
  --n-shot 0 --presence-penalty 1.0 --tag gate-s0-pp10 \
  --dump-prompt finetune/results/prompt_gate-s0-pp10.txt

# 2) few-shot 2 ví dụ, presence_penalty 1.0
python -m finetune.replay --input "$SRC" --model "$GGUF" --ids "$IDS" \
  --n-shot 2 --presence-penalty 1.0 --tag gate-s2-pp10 \
  --dump-prompt finetune/results/prompt_gate-s2-pp10.txt

# 3) zero-shot, presence_penalty 0
python -m finetune.replay --input "$SRC" --model "$GGUF" --ids "$IDS" \
  --n-shot 0 --presence-penalty 0 --tag gate-s0-pp00

# 4) few-shot 2 ví dụ, presence_penalty 0
python -m finetune.replay --input "$SRC" --model "$GGUF" --ids "$IDS" \
  --n-shot 2 --presence-penalty 0 --tag gate-s2-pp00
```

**Vì sao thử `presence_penalty=0`:** tác vụ là **chép nguyên văn slug từ ngữ cảnh**,
mà presence penalty phạt đúng token đã xuất hiện — tức phạt đúng hành vi ta cần.
Mặc định 1.0 lấy từ khuyến nghị Qwen (dải card cho phép 0–2) để dập lặp vô tận;
hai giá trị này là hai đầu của cùng một đánh đổi.

Các tham số sinh còn lại giữ mặc định = khuyến nghị Qwen cho bản 2507
(`generation_config.json`: `temperature=0.7, top_p=0.8, top_k=20`; README bổ sung
`min_p=0`). **Không greedy** — lặp vô tận sẽ ăn hết `max_new_tokens`, mà khối trích
dẫn nằm CUỐI câu trả lời nên bị cắt mất → F1 = 0 vì lý do thuần kỹ thuật.

⚠️ **Sau khi chốt thì bốn ô của ma trận FT-06 phải dùng GIỐNG HỆT một bộ tham số
sinh.** Khác nhau giữa các ô là tự tạo confound, đúng loại làm hỏng mục 4.7.

### Ba kiểm tra hạ tầng (§TASK-FT-03 quy trình 3)

1. **Đường llama-cpp có chạy không** — lần đầu chạy với weights thật. Trên Windows
   không có wheel dựng sẵn nên đường này mới chỉ test bằng module giả.
2. **Prompt render qua chat template có đúng không** — `--dump-prompt`, mở file ra
   **nhìn bằng mắt**. `replay.py` render bằng jinja2 từ chính
   `tokenizer.chat_template` nhúng trong GGUF; đây là *tái dựng trung thực từ cùng
   một template*, không đảm bảo byte-identical với chuỗi llama.cpp thực nạp.
3. **Số token tự đếm có khớp backend không** — mỗi item ghi `n_tokens_prompt`
   (ta đếm) và `n_tokens_prompt_backend` (`usage.prompt_tokens`), cùng
   `prompt_len_lech`. Metadata gom `prompt_len_lech_max`. Lệch lớn nghĩa là template
   ta tái dựng khác cái backend thực nạp → prompt không như ta tưởng.

### Đọc kết quả

Bốn con số cần lấy từ mỗi lần chạy (in ra cuối, và nằm trong khối `replay` của JSON):

| Chỉ số | Nghĩa |
|---|---|
| `format_ok_rate` | mẫu số **12**; sàn rất thấp — chỉ cần 1 khối parse được |
| `soft_article_hit_mean` | bộ trích **LỎNG**, độc lập `parse_citations` |
| `n_hit_token_cap` | khác 0 thì mọi con số của ô đó phải đọc lại |
| `f1_mean` | F1 cấp Khoản thô |

**Vì sao cần bộ trích lỏng:** khi `format_ok = 0` thì `pred_citations` rỗng → chỉ
báo dựa trên nó sẽ undefined **đúng lúc cần nó nhất**. Bộ lỏng quét văn bản thô tìm
`Điều \d+`, `Khoản \d+`, chuỗi giống slug `[a-z0-9-]{15,}` — bất kể có nằm trong
ngoặc vuông hay không — rồi đối chiếu với `context` của chính item đó.

**Trần tham chiếu:** trên chính 137 câu trả lời của Gemini, `soft_article_hit` =
**1.000** ở cả 118 câu có nhắc điều luật (646 cụm, 0 cụm ngoài ngữ cảnh). Nên mô
hình cục bộ tụt sâu dưới 1.0 là bịa vị trí thật, không phải nhiễu đo.

| `soft_article_hit` | `format_ok` | Chẩn đoán |
|---|---|---|
| cao | thấp | Biết điều luật nào, không biết viết cú pháp → **đúng thứ tinh chỉnh sửa được** |
| thấp | thấp | Không định vị nổi điều luật trong ngữ cảnh 12k → **ngoại lệ duy nhất được leo thang lên 8B** (§9.5) |
| — | — | `n_hit_token_cap` cao → lỗi tham số sinh, **chưa kết luận gì**; sửa `presence_penalty` rồi đo lại |

Gate này **không để huỷ kế hoạch** mà để biết trước sẽ viết gì trước khi tốn công
huấn luyện. Kể cả `format_ok_rate < 10%` vẫn đi tiếp — đó chính là kết quả cho thấy
tinh chỉnh là *điều kiện cần* để mô hình nhỏ tham gia được kiến trúc.

**Đầu ra phiên 1:** `reports/gate_base_model.md`.

---

## Verify không cần GPU

Backend `mock` chạy hết đường đi schema mà không cần weights:

```bash
python -m finetune.replay --input "$SRC" --model mock --ids "$IDS" --tag smoke
python -m finetune.replay --input "$SRC" --model mock:empty --limit 5   # format_ok=0
python -m finetune.replay --input "$SRC" --model mock:cap   --limit 3   # hit_token_cap
python -m pytest tests/test_finetune_replay.py -q
```

`--ids` và `--limit` **loại trừ nhau** — `--limit` cắt N câu đầu (không phân tầng),
`--ids` chọn đúng danh sách; dùng cả hai thì không rõ ý định nên báo lỗi.

## Quy tắc

1. **Không sửa `src/`.** Nếu thấy cần sửa `src/` để đọc được đầu ra thì `replay.py`
   sai, không phải `src/` sai.
2. **Không sửa, ghi đè, xoá gì trong `data/evaluation/`.** Chỉ đọc.
3. **Tái dùng `src/evaluation/metrics.py`** — `cit_matches` là single source of
   truth. Viết lại metric thì số mới không so được với Bảng 4.3 và 4.5.
4. **`INCLUDE_SCHEMA_B` phải là `false`** — đọc lúc import module, đổi sau khi import
   không có tác dụng. `replay.py` tự set và assert lại.
5. **Không sinh `NaN`** — file gốc có 118 literal `NaN` ở `faithfulness.support_rate`
   khiến JSON không chuẩn. Hàng cục bộ không đo tỉ lệ hậu thuẫn → `faithfulness: null`.
6. **Không đụng `_FEWSHOT`.** Ngữ cảnh trong hai ví dụ là *nguồn để chép mã định
   danh*: mô hình phải học "chép slug từ ngoặc đơn cuối header", bỏ header đi là bỏ
   mất nguồn và vô tình dạy nó bịa mã từ trí nhớ. Hai ví dụ hiện ~120 token mỗi cái,
   không phải khối 4–6k, nên lo ngại tràn token không áp dụng.
