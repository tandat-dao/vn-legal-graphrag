# TASK-FT-03 — GATE: mô hình cục bộ CHƯA tinh chỉnh

**Mô hình:** `Qwen/Qwen3-4B-Instruct-2507` → GGUF `Q4_K_M` (chốt ở kế hoạch §9.5, không có vòng sàng lọc ứng viên)
**Phiên 1:** Kaggle, 29/07/2026 · 15 câu (`finetune/data/gate_ids.json`) · seed 42 · `n_ctx = 16384` · `max_new_tokens = 2048`
**Nguồn ngữ cảnh:** `data/evaluation/results_graphrag_20260710-085236.json` (chỉ đọc)

### Hiện vật GGUF gốc — giá trị ghim

| | |
|---|---|
| repo | `bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF` |
| file | `Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf` |
| `revision` | `ae44f08e1392f39c0e474af10c3ff8355c8b6688` |
| `sha256` | `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e` |

**Đây là lần đầu hai giá trị này được ghi vào repo.** Phiên 1 đọc chúng từ
`/kaggle/working/base_manifest.json`, mà file đó **chưa từng được commit**; và ô 15
của notebook FT-03 chỉ in kết luận *"OK, sha256 khớp bản đã ghi"* chứ **không in chuỗi
hash**, nên output notebook cũng không khôi phục lại được. Trước đó báo cáo này chỉ ghi
**tên** model.

Xuất xứ của từng giá trị:

- **`revision`** — khôi phục từ **output đã lưu** của ô 15 notebook FT-03, hai chỗ độc
  lập: URL `HEAD …/resolve/ae44f08e…/Qwen_…-Q4_K_M.gguf` và đường cache
  `…/snapshots/ae44f08e…/Qwen_…-Q4_K_M.gguf`. Chính ô đó chạy
  `assert h == old["sha256"]` rồi báo khớp → revision này đã qua cổng sha256 ở phiên 1.
- **`sha256`** — đọc trực tiếp từ **metadata LFS của HF tại đúng revision trên**, nguồn
  thẩm quyền hơn `base_manifest.json` (hash do chính Hub lưu cho blob, đọc lại được bất
  cứ lúc nào mà không phải tải 2,5 GB):

  ```python
  HfApi().list_repo_tree("bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF",
      revision="ae44f08e1392f39c0e474af10c3ff8355c8b6688",
      expand=True, recursive=True)   # -> f.lfs.sha256 của file Q4_K_M
  ```

Hệ quả vận hành: `finetune/kaggle_ft06.py` ghim cả bốn giá trị làm **mặc định** nên
chặng `prep` không còn bước tay nào. Ba đường ghi đè vẫn còn cho phiên sau (`--base-revision`
/ `--base-sha256`, `FT06_BASE_*`, `base_manifest.json`), và script cảnh báo nếu giá trị
ghi đè không bắt đầu bằng `2fde00ce`.

> **Kết luận một dòng:** `soft_article_hit = 1.000` ở cả bốn ô trong khi `format_ok`
> zero-shot chỉ 0.083 → mô hình **định vị được điều luật, không viết nổi cú pháp
> trích dẫn** — đúng thứ tinh chỉnh sửa được. **GIỮ 4B**, nhánh leo thang 8B KHÔNG
> xảy ra. Chốt `presence_penalty = 0` cho cả bốn ô của FT-06.

---

## 1. Ma trận 2×2 đầy đủ

Hai trục: `{--n-shot 0, --n-shot 2}` × `{presence_penalty 1.0, presence_penalty 0}`.
Cùng một bộ 15 câu, cùng một model, cùng seed — chỉ đổi hai trục đó.

| Ô | `format_ok` | F1 Khoản | F1 Điều | NormR | cụm | `tu_choi_dung` | `hit_token_cap` | prompt max | `prompt_len_lech` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s0 · pp1.0 | 0.083 (1/12) | 0.200 | 0.200 | 0.200 | 68 | 0.667 (2/3) | 0 | 11 211 | 22 |
| s0 · pp0   | 0.167 (2/12) | 0.244 | 0.244 | 0.267 | 69 | 0.667 (2/3) | 0 | 11 211 | 22 |
| s2 · pp1.0 | 0.833 (10/12) | 0.531 | 0.531 | 0.633 | 67 | 0.333 (1/3) | 0 | 11 623 | 56 |
| s2 · pp0   | 0.833 (10/12) | **0.600** | **0.600** | **0.700** | 78 | 0.333 (1/3) | 0 | 11 623 | 56 |

**`soft_article_hit = 1.000` ở CẢ BỐN Ô** — 13/15 câu có nhắc điều luật, và mọi
cụm nhắc tới đều có mặt trong ngữ cảnh đưa vào. Không ô nào bịa vị trí.

Ghi chú cột:

- **`format_ok`** — mẫu số **12**, không phải 15 (kế hoạch §3.1: chỉ tính trên câu
  có `ground_truth_citations` khác rỗng; 3 câu bẫy phủ định bị loại khỏi mẫu số).
- **cụm** — số cụm `Điều \d+` / `Khoản \d+` / chuỗi giống slug mà **bộ trích LỎNG**
  bắt được, độc lập hoàn toàn với `parse_citations`. Đây là mẫu số của
  `soft_article_hit`; nó biến thiên 67–78 giữa các ô vì độ dài câu trả lời khác nhau.
- **`tu_choi_dung`** — mẫu số **3** (V005, V105, V117), là ba câu phủ định ĐÃ đi
  qua mô hình sinh. V106–V113/V115/V116 không có trong bộ gate: chúng có
  `top_k_count = 0`, `answer` là hằng số cứng ở `pipeline.py:233`.
- **prompt max / `prompt_len_lech`** — xem §5.

---

## 2. Kết luận cổng

Đọc theo bảng chẩn đoán ở §TASK-FT-03 của kế hoạch:

| `soft_article_hit` | `format_ok` | Chẩn đoán |
|---|---|---|
| **cao (1.000)** | **thấp (0.083 zero-shot)** | ← ô của ta: biết điều luật nào, không biết viết cú pháp |
| thấp | thấp | không định vị nổi điều luật trong ngữ cảnh 12k → ngoại lệ duy nhất được leo lên 8B |

Ô rơi vào hàng thứ nhất. Nghĩa là **thiếu hụt nằm ở định dạng đầu ra, không nằm ở
năng lực định vị trong ngữ cảnh 12k** — đúng loại thiếu hụt mà QLoRA trên 5 000 mẫu
có khối trích dẫn chuẩn sửa được.

**Quyết định:** GIỮ `Qwen3-4B-Instruct-2507`. **Nhánh leo thang lên 8B không xảy ra**
— điều kiện kích hoạt của nó (kế hoạch §9.5) là `format_ok` **và**
`soft_article_hit` **cùng ở sàn**, mà `soft_article_hit` ở trần.

Theo bảng "Đọc kết quả" (`format_ok_rate` few-shot = 0.833 > 50%): **đi tiếp bình
thường**, không cần ghi chú đặc biệt về tuân thủ định dạng ở hàng few-shot.

Gate này không để huỷ kế hoạch mà để **biết trước sẽ viết gì** trước khi tốn công
huấn luyện. Cái biết được: hàng "cục bộ chưa tinh chỉnh" sẽ **không** ≈ 0, và câu
chuyện của mục 4.7 là *tinh chỉnh chuyển năng lực định vị sẵn có thành trích dẫn
máy đọc được*, chứ không phải *tinh chỉnh dạy mô hình đọc luật*.

---

## 3. Chốt `presence_penalty = 0`

**Theo quy tắc ĐĂNG KÝ TRƯỚC:** *chọn giá trị nhỏ nhất mà `hit_token_cap = 0`.*
`hit_token_cap = 0` ở cả bốn ô → giá trị nhỏ nhất trong hai giá trị thử là **0**.

**KHÔNG chọn theo "điểm cao hơn."** pp=0 đúng là cho F1 cao hơn (0.600 vs 0.531 ở
2-shot), nhưng lấy đó làm căn cứ là **chọn tham số dựa trên chính điểm của tập đo** —
15 câu này nằm trong 137 câu mà hàng "cục bộ chưa tinh chỉnh" đằng nào cũng phải
chạy đủ ở FT-06, nên chọn theo điểm là selection-on-test thật sự, khác hẳn với việc
FT-03 chỉ *chạy sớm* một phần của thí nghiệm.

Cơ chế đứng sau quy tắc đăng ký trước: `presence_penalty` chỉ tồn tại để dập lặp vô
tận (lặp ăn hết `max_new_tokens` → khối trích dẫn nằm CUỐI câu trả lời bị cắt → F1 = 0
vì lý do thuần kỹ thuật). Khi không có bằng chứng lặp thì không có lý do trả giá cho
nó, mà giá ở đây rất cụ thể: tác vụ là **chép nguyên văn slug từ ngữ cảnh**, còn
presence penalty phạt đúng token đã xuất hiện — tức phạt đúng hành vi ta cần.

Các tham số sinh còn lại giữ khuyến nghị Qwen cho bản 2507 (`temperature=0.7`,
`top_p=0.8`, `top_k=20`, `min_p=0`). **Bốn ô của FT-06 phải dùng GIỐNG HỆT bộ tham số
này** — khác nhau giữa các ô là tự tạo confound.

---

## 4. Ba dè dặt phải ghi vào khóa luận

**(1) Hiệu ứng của `presence_penalty` lên `format_ok` chưa thiết lập được.**
Ở zero-shot, 1/12 so với 2/12 là chênh **đúng một câu**. Khoảng tin cậy Wilson 95%:
[0.015, 0.354] so với [0.047, 0.448] — chồng lấn gần như hoàn toàn. Cái đứng vững
không phải độ lớn mà là **hướng nhất quán ở cả bốn ô** (pp=0 ≥ pp=1.0 trên mọi thang
đo) **cộng với một cơ chế hợp lý** (§3). Trong báo cáo viết là *"hướng nhất quán trên
cỡ mẫu nhỏ"*, không viết là *"pp=0 cải thiện định dạng"*.

**(2) `hit_token_cap = 0` trên 15 câu × 1 seed là nền mỏng cho một sự kiện hiếm.**
Lặp vô tận là hiện tượng đuôi phân phối; không quan sát thấy nó trong 60 lượt sinh
(15 câu × 4 ô) chỉ đặt cận trên lỏng lẻo cho tần suất của nó. Đọc là **"không thấy
bằng chứng lặp"**, KHÔNG phải "đã loại trừ lặp". Hệ quả vận hành: `hit_token_cap`
vẫn phải được log và kiểm ở cả 548 lượt của FT-06 — nếu tỉ lệ chạm trần khác 0 thì
mọi con số của ô đó phải đọc lại trước khi vào bảng.

**(3) Mẫu số là 12, không phải 15.** Mọi tỉ lệ `format_ok` ở đây tính trên 12 câu có
`ground_truth_citations` khác rỗng. Ba câu bẫy phủ định nằm ở cột `tu_choi_dung`
(mẫu số 3) và không tham gia `format_ok`. Nhầm mẫu số làm mọi khoảng tin cậy hẹp đi
giả tạo.

---

## 5. Ba kiểm tra hạ tầng (§TASK-FT-03 quy trình 3)

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | Đường llama-cpp chạy được với weights thật | ✅ **ĐẠT** |
| 2 | Prompt render qua chat template đúng | ⚠️ **CÒN TREO** — chưa đọc bằng mắt |
| 3 | Số token prompt tự đếm khớp backend | ✅ **ĐẠT** |

**(1) Đường llama-cpp — ĐẠT.** Đây là lần đầu đường này chạy với weights thật: trên
Windows không có wheel dựng sẵn cho `llama-cpp-python` nên trước đó nó mới chỉ được
test bằng module giả (`tests/test_finetune_replay.py`). 60/60 lượt sinh hoàn tất,
schema đầu ra `metrics.aggregate` đọc được không cần sửa `src/`.

**(2) Prompt render — CÒN TREO, phải làm TRƯỚC FT-06.** Hai file `--dump-prompt` đã
được sinh (`prompt_gate-s0-pp10.txt`, `prompt_gate-s2-pp10.txt`) nhưng **chưa ai mở
ra nhìn bằng mắt** — mà "nhìn bằng mắt" mới là nội dung của kiểm tra này. Đây là
việc $0 và là điều kiện chặn: nếu template render sai thì cả 548 lượt của FT-06 chạy
trên một prompt khác cái ta tưởng.
*Nhắc:* `render_prompt` là **tái dựng trung thực từ cùng một template**
(jinja2 trên `tokenizer.chat_template` nhúng trong GGUF), không đảm bảo
byte-identical với chuỗi llama.cpp thực nạp — xem §6.

**(3) `prompt_len_lech` — ĐẠT.** Lệch giữa số token ta tự đếm và `usage.prompt_tokens`
của backend: **22 ở 0-shot, 56 ở 2-shot, và `min == max` trong từng cấu hình** (mọi
câu trong cùng một ô lệch đúng bằng nhau).

> ⚠️ **Tiêu chí đúng là "bất biến trong cùng một cấu trúc tin nhắn", KHÔNG phải
> "bằng nhau giữa 0-shot và 2-shot".** Lệch là phụ trội cố định của việc đánh dấu
> vai trò/ranh giới lượt; 2-shot có thêm hai cặp user/assistant nên phụ trội tăng —
> 56 > 22 là **đúng như kỳ vọng**. Cái sẽ báo động là lệch **biến thiên theo câu**
> trong cùng một ô: khi đó template ta tái dựng khác cái backend thực nạp ở chỗ phụ
> thuộc nội dung, và prompt không như ta tưởng. Điều đó không xảy ra ở cả bốn ô.

---

## 6. Xuất xứ mã sinh ra các số này

Số liệu phiên 1 sinh bởi commit **`eecdc7b7`** **CỘNG** một bản vá `render_prompt` vá
tại chỗ bằng cell notebook trên Kaggle (template Qwen3 truy cập `message.tool_calls`
và mở đầu bằng `{%- if tools %}`; với `StrictUndefined` thì thiếu khoá là
`UndefinedError`). Nghĩa là **tại thời điểm chạy, mã sinh ra các số này không khớp
bất kỳ commit nào.**

Bản vá đó **nay đã được commit** vào `finetune/replay.py` (`[TASK-FT-02] fix: đưa bản
vá render chat template Qwen3 vào git`), nên FT-06 sẽ chạy trên một cây mã tái dựng
được.

**Bản vá KHÔNG ảnh hưởng phần sinh văn bản.** `LlamaCppBackend.generate` gọi
`self._llm.create_chat_completion(messages=…)`, và llama.cpp áp chat template bằng
**engine C++ của chính nó** — đường jinja2 của `render_prompt` là một đường độc lập,
chỉ phục vụ `--dump-prompt` và việc tự đếm token (cột `prompt_len_lech` ở §5). Trước
bản vá, `render_prompt` trả `None` và `count_prompt_tokens` lùi về nhánh xấp xỉ; sau
bản vá nó trả chuỗi render được. F1 / `format_ok` / `soft_article_hit` /
`tu_choi_dung` không đi qua đường đó.

---

## 7. Việc còn lại trước FT-06

1. **Mở hai file `--dump-prompt` ra đọc bằng mắt** (§5.2). Chặn cứng, $0.
2. Giữ nguyên bộ tham số sinh đã chốt ở §3 cho cả bốn ô.
3. Log `hit_token_cap` trên toàn bộ 548 lượt (§4.2).
