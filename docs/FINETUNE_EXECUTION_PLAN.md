# Kế hoạch Thực thi — Bổ sung Mô hình Sinh Cục bộ vào Chương 4

**Phiên bản 2.3.3 | Ngày: 30/07/2026**

> **Thay đổi v2.3.2 → v2.3.3:** viết lại **§TASK-FT-06** cho khớp hiện thực
> (`finetune/kaggle_ft06.py` + `finetune/notebooks/ft06_eval.ipynb`). (1) **bốn ô →
> sáu ô, 548 → 822 lượt sinh**: hàng "cục bộ gốc" báo **cả hai** biến thể 0-shot và
> 2-shot (few-shot là biến thật với nó — `format_ok` 0.083 → 0.833), còn hàng "đã
> tinh chỉnh" chỉ chạy **0-shot** vì bộ huấn luyện FT-04 dựng bằng chính
> `build_messages` nên chèn ví dụ minh hoạ là tạo lệch train/eval; kèm bảng sáu ô và
> thứ tự chạy (ô giá trị nhất trước, đẩy HF sau từng ô). (2) thêm **hai cổng chặn A
> (chat template hai GGUF phải trùng khít) và B (đọc prompt đã render)** vào quy
> trình — **B chính là món nợ của FT-03**, kiểm tra hạ tầng #2 mà
> `gate_base_model.md` §5 ghi ⚠️ CÒN TREO và §7 xếp là việc $0 chặn cứng. (3) ghi rõ
> **nguồn ngữ cảnh là cặp file `20260710-085236`** và lý do phải đúng cặp đó. (4) nơi
> chạy: **Kaggle T4**, không phải GPU thuê. (5) nhắc `presence_penalty` mặc định của
> `replay.py` là 1.0 nên phải truyền tường minh 0.
>
> **Thay đổi v2.3.1 → v2.3.2:** sửa **năm chỗ kế hoạch lạc hậu so với mã đang chạy**.
> (1) §TASK-FT-02 ghi `temperature 0` — **sai**, `replay.py` chạy bộ tham số Qwen
> 2507 (0.7/0.8/20/0) và tính tất định đến từ seed + bản dựng + phần cứng, không từ
> greedy; (2) §TASK-FT-05 đổi `notebooks/train_qlora.ipynb` → `train_qlora.py` +
> `run.sh` + `upload_dataset.sh`, và nêu rõ `run.sh` phải truyền tường minh
> `--lora-r 16 --lora-alpha 32` vì mặc định script là 32/64; (3) §TASK-FT-03 bỏ
> "llama-server" → llama-cpp-python in-process; (4) **thống nhất mẫu số** 137 / 127 /
> 123 (§9.4); (5) §TASK-FT-04 bổ sung tỉ lệ mẫu từ chối **9%, chia 70/30** — quyết
> định này trước đó chỉ sống trong `build_dataset.py` và `dataset_stats.md` §4.2.
>
> **Thay đổi v2.3 → v2.3.1:** **chốt N=1 cho cả bốn ô của FT-06** (548 lượt sinh —
> v2.3.3 nâng lên sáu ô / 822 lượt),
> thay đoạn để ngỏ trước đó. Căn cứ mới: tính tất định đã đo được ở phiên 1 FT-03
> (hai lần chạy cùng seed → `answer` trùng khít từng ký tự 15/15 câu), cộng lý do
> kỹ thuật vì sao KHÔNG lồng nhiều seed vào `replay.py`. Xem **§TASK-FT-06**.
>
> **Thay đổi v2.2 → v2.3:** **chốt một mô hình duy nhất** và rút gọn FT-03. Gate
> trước đó bị gán thêm việc “chọn giữa 2–3 ứng viên” — việc đó sinh ra toàn bộ
> vấn đề độ phân giải thống kê và selection-on-test. Bỏ nó, mọi thứ tan. Xem **§9.5**.
>
> **Thay đổi v2.1 → v2.2:** sửa tiêu chí tuyển mô hình ở FT-03 (bỏ mệnh đề về
> số tham số), thêm ràng buộc system prompt vào FT-04, thêm log trần token vào
> FT-02, chốt `max_seq_length` cho FT-05. Xem **§9.4**.
>
> **Thay đổi v2.0 → v2.1:** chốt ba quyết định còn treo ở §7 của
> `finetune/reports/api_contract.md`, và bổ sung bốn ràng buộc rút ra từ phát
> hiện của TASK-FT-00. Tổng hợp ở **§9**; các mục liên quan đã được sửa tại chỗ.
>
> **Thay đổi v1.0 → v2.0:** thu hẹp phạm vi. Bỏ toàn bộ chỉ số mới
> (latency, RAM, tốc độ sinh, chi phí, riêng tư) và bỏ TASK-FT-07. Chỉ dùng
> đúng bốn thang đo đã có trong Bảng 4.5 của báo cáo.
>
> **Mục tiêu duy nhất:** bổ sung hai cấu hình mô hình sinh — **cục bộ chưa
> tinh chỉnh** và **cục bộ đã tinh chỉnh** — vào khung đánh giá hiện có của
> khóa luận.
>
> Tài liệu này viết cho Claude Code thực thi.

---

## 1. Định vị trong báo cáo — đọc kỹ mục này trước

### 1.1 Vì sao KHÔNG được thêm vào Bảng 4.5

Bảng 4.2 của báo cáo phát biểu rõ nguyên tắc của bốn hệ tham chiếu:

> *"Tất cả các hệ chạy trên cùng bộ câu hỏi và cùng mô hình sinh […], do đó
> sự chênh lệch đo được thuộc về khác biệt ở cơ chế truy hồi chứ không phải
> ở mô hình sinh."*

Closed-book, Naive RAG, BM25, Oracle đều **giữ nguyên mô hình sinh, thay đổi
cơ chế truy hồi**. Mô hình cục bộ là chiều ngược lại: **giữ nguyên truy hồi,
thay đổi mô hình sinh**.

Nhét nó vào Bảng 4.5 sẽ phá vỡ chính câu lập luận trên và làm hỏng một bảng
đang chặt chẽ. **Đây là trục trực giao, phải có mục riêng.**

### 1.2 Khung định vị đề xuất: mục 4.7

Câu hỏi mà mục mới trả lời nảy sinh tự nhiên từ Bảng 4.2: *nếu mọi kết luận
đều được rút ra khi cố định mô hình sinh là Gemini 2.5 Pro, thì kết luận đó
có phụ thuộc vào việc chọn mô hình sinh nào không?*

Đây **không phải một câu hỏi nghiên cứu thứ tư**. Nó là phép kiểm tra tính
vững của Câu hỏi 1: nếu ưu thế của GraphRAG so với Naive RAG vẫn giữ khi đổi
sang một mô hình cục bộ nhỏ, thì ưu thế đó thuộc về kiến trúc chứ không phải
thuộc về năng lực của một mô hình thương mại cụ thể.

Tên mục đề xuất: **4.7 Ảnh hưởng của mô hình sinh**. Đặt sau 4.6 để không
phải đánh số lại toàn chương. Nếu chấp nhận đánh số lại, vị trí hợp lý hơn
là ngay sau 4.2 vì nó củng cố Câu hỏi 1.

### 1.3 Liên hệ với mục 5.4

Mục 5.4 hiện có gạch đầu dòng *"Tinh chỉnh mô hình nhúng hoặc mô hình sinh
đặc thù cho miền pháp luật"* trong Hướng phát triển. Việc này chuyển một
phần của gạch đầu dòng đó từ **hướng phát triển** thành **kết quả thực
nghiệm**. Khi viết xong mục 4.7, phải sửa lại 5.4 cho khỏi mâu thuẫn.

---

## 2. Ma trận thí nghiệm

Vì mục đích là kiểm tra tính vững của Câu hỏi 1, **ma trận phải có đủ cả hai
cột**. Đây không còn là phần mở rộng tùy chọn như ở v1.0 — cột Naive RAG
chính là thứ tạo ra ý nghĩa cho mục 4.7.

| Mô hình sinh | Naive RAG | GraphRAG | Δ |
|---|---|---|---|
| Gemini 2.5 Pro | 0.435 ✓ đã có | 0.578 ✓ đã có | +0.143 ✓ đã có |
| Cục bộ, chưa tinh chỉnh | cần chạy | cần chạy | cần tính |
| Cục bộ, đã tinh chỉnh | cần chạy | cần chạy | cần tính |

Bốn ô cần chạy. Kết luận mong muốn: **cột Δ giữ dấu dương ở cả ba hàng.**

Nếu Δ dương ở cả ba hàng → ưu thế kiến trúc không phụ thuộc mô hình sinh,
Câu hỏi 1 được củng cố. Nếu Δ triệt tiêu ở hàng cục bộ → đó cũng là một phát
hiện đáng viết: ưu thế của đồ thị cần một mô hình sinh đủ mạnh mới hiện thực
hóa được, và điều đó bổ sung vào mục 5.3.

---

## 3. Thang đo — chỉ dùng thứ đã có

Đúng bốn cột của Bảng 4.5, không thêm gì:

| Thang đo | Nguồn |
|---|---|
| F1 cấp Khoản | `src/evaluation/metrics.py` |
| F1 cấp Điều | `src/evaluation/metrics.py` |
| Norm Recall | `src/evaluation/metrics.py` |
| Từ chối đúng (x/14) | `src/evaluation/metrics.py` |

**Không đo:** latency, RAM, tốc độ sinh, chi phí, tính riêng tư. Những thứ
này không có trong khung đánh giá của khóa luận và việc thêm chúng chỉ làm
loãng mục 4.7.

**Tùy chọn, không bắt buộc:** *tỉ lệ tồn tại* (Bảng 4.7). Đây là thang đo đã
có sẵn trong báo cáo, tất định, không cần mô hình chấm, tính ra gần như miễn
phí từ dữ liệu đã có. Lý do đáng cân nhắc: mô hình nhỏ có nguy cơ bịa trích
dẫn cao hơn hẳn, mà Gemini đang ở 99.9% — nếu mô hình cục bộ tụt sâu thì đó
là thông tin thật. Nhưng nếu không muốn mở rộng mục 4.4 thì bỏ qua cũng được.

**Không đo tỉ lệ hậu thuẫn** cho các cấu hình cục bộ: nó cần mô hình chấm,
tốn API, và mục 4.4 đã ghi rõ thang đo này chỉ nên đọc tương đối.

### 3.1 Một chỉ số nội bộ, không đưa vào báo cáo

`format_ok_rate` — tỉ lệ câu trả lời parse ra được ít nhất một trích dẫn hợp
lệ. **Không phải cột trong bảng của khóa luận.** Đây là công cụ chẩn đoán nội
bộ, chỉ dùng ở TASK-FT-03 để phân biệt hai trường hợp rất khác nhau khi F1
thấp: *mô hình không biết luật* hay *mô hình biết nhưng viết sai định dạng
nên bộ chấm không đọc được*. Không có nó thì không diễn giải nổi một con số 0,
và có nguy cơ viết sai nguyên nhân vào báo cáo.

**Định nghĩa vận hành (chốt ở v2.1):** tính **chỉ trên tập câu có
`ground_truth_citations` khác rỗng** (123/137). Đó là tập duy nhất mà một trích
dẫn được *kỳ vọng*; trên đó, 0 citation là thất bại thật. Nếu tính máy móc trên
cả 137 thì Gemini ra ~0.86 dù không sai định dạng lần nào, vì 19 câu từ chối hoặc
ngoài phạm vi trả 0 citation một cách đúng đắn (42/137 ở baseline).

---

## 4. Nguyên tắc nền: phát lại, không chạy lại

`results_graphrag_*.json` và `results_baseline_*.json` đã lưu đầy đủ chuỗi
`context` mà mô hình sinh thực sự nhận (đã kiểm chứng: 137/137 item có key
`context`, byte-identical với input thật).

Hệ quả:

- **Không cần Neo4j, không cần Qdrant, không cần chạy lại truy hồi.** Đúng
  với thực tế máy hiện tại.
- **Không gọi API nào.**
- Truy hồi bị khoá tuyệt đối giữa các hàng của ma trận → chênh lệch đo được
  thuần túy thuộc về mô hình sinh. Đây chính là điều kiện mà mục 4.7 cần.

Nếu ở bước nào Claude Code thấy cần khởi động Neo4j/Qdrant hoặc gọi Vertex
AI, **hướng đi đã sai** — dừng và báo.

---

## 5. QUY TẮC TUYỆT ĐỐI CHO CLAUDE CODE

1. **KHÔNG sửa bất cứ file nào trong `src/`.** Tiền lệ: `ui/` cũng theo quy
   tắc này. Mọi code mới nằm trong `finetune/`.
2. **KHÔNG sửa, ghi đè, xoá file nào trong `data/evaluation/`.** Chỉ đọc.
   File mới ghi vào `finetune/results/`.
3. **KHÔNG sửa `data/raw/`.**
4. **KHÔNG sửa `test_set_v2.json`** — đã FREEZE (SHA256 `bd2c5eaf…f146`).
5. **Tái dùng `src/evaluation/metrics.py`, không viết lại hàm chấm.**
   `cit_matches` là single source of truth. Viết lại metric thì số mới không
   so được với số trong Bảng 4.3 và 4.5.
6. **Không đoán chữ ký hàm hay cú pháp.** Đọc code thật, trích số dòng.
7. **Lỗi import thì cài package** (`pip install anthropic neo4j qdrant-client`),
   đừng chép code từ `src/` sang `finetune/`.
8. Commit: `[TASK-FT-XX] type: mô tả ngắn bằng tiếng Việt`.

---

## 6. Các TASK

### TASK-FT-00 — Hợp đồng API

Đọc và ghi lại vào `finetune/reports/api_contract.md`, kèm số dòng:

| Cần biết | Đọc ở đâu |
|---|---|
| Chữ ký + hành vi `build_messages` | `src/retrieval/context_assembler.py` |
| Cú pháp trích dẫn mà parser chấp nhận | `parse_citations` trong `src/retrieval/answer_generator.py` |
| Bề mặt chuỗi trích dẫn Gemini thực sự sinh | field `answer` của ~30 item trong results JSON |
| Chữ ký `cit_matches`, `aggregate` | `src/evaluation/metrics.py` |
| Schema item results JSON | `src/evaluation/run_evaluation.py` |
| Khuôn header block ngữ cảnh | đối chiếu `assemble_context` với `context` thật |

**DoD:** tài liệu trả lời được *"chuỗi trích dẫn đích trông chính xác thế nào"*
bằng ví dụ thật, không bằng mô tả.

> Các plan cũ ghi `"Nguồn: [Điều X Khoản Y {norm_id}]"` — đó là phỏng đoán từ
> tháng 6, có thể sai. Sai chỗ này thì mọi mẫu huấn luyện đều vô dụng.

---

### TASK-FT-01 — Ngân sách token & khôi phục `response_mode` ⚠️ GATE

**$0, không cần GPU, không cần weights.**

**A — Đo độ dài thật.** Nạp tokenizer của 2–3 mô hình ứng viên (chỉ tokenizer),
tokenize 137 chuỗi `context` của cả hai file, cộng system prompt do
`build_messages` sinh. Báo cáo p50 / p90 / p95 / max cho tổng thật.

**Tổng thật = system_prompt + khung user_prompt + question + context.** Số đo
ký tự đã có (api_contract.md §1.2–1.3, §5):

| Thành phần | Ký tự |
|---|---:|
| system_prompt, mode `general` | **11 264** |
| system_prompt, mode `irac` | **11 532** |
| khung cố định của user_prompt | 30 |
| context GraphRAG | mean 13 204, max 21 066 |
| context baseline | mean 5 641, max 5 769 |

⚠️ System prompt **lớn hơn nhiều** so với con số “~2117 token” trong ghi chú D-15
cũ của `CLAUDE.md` — đừng dùng lại con số đó. Vào đo với kỳ vọng **cửa sổ 16k
là sàn**, không phải 8k. Vẫn phải đo thật bằng tokenizer, không quy đổi ước lượng.

**B — Khôi phục `response_mode`.** Run gốc chạy `--response-mode auto`,
nghĩa là planner tự chọn general hay irac từng câu, và field đó **không được
lưu** vào results JSON. Giả định "tất cả general" là sai lệch có hệ thống vì
prompt hai mode khác nhau.

Khôi phục cơ khí: mode irac sinh 4 heading cố định (Vấn đề / Căn cứ pháp lý /
Phân tích / Kết luận) → regex trên field `answer` đã lưu. Ghi
`finetune/data/mode_map.json`. Báo cáo tỉ lệ.

**DoD:** có bảng phân phối token; có tỉ lệ mode; có kết luận dạng *"cần cửa
sổ ngữ cảnh ≥ N token, do đó mô hình phải thuộc lớp X"*.

---

### TASK-FT-02 — Bộ phát lại

`finetune/replay.py`:

```
Đọc results JSON nguồn (chỉ đọc)
  → mỗi item: lấy (id, question, context)
  → tra mode từ mode_map.json
  → dựng prompt bằng src…build_messages(question, context, mode)
  → gọi mô hình cục bộ (llama-cpp-python, GGUF)
  → parse bằng src…parse_citations
  → chấm bằng src.evaluation.metrics (KHÔNG tự viết)
  → ghi results JSON mới, ĐÚNG SCHEMA HIỆN TẠI, vào finetune/results/
```

**Yêu cầu bắt buộc:**

- **Schema đầu ra khớp chính xác** schema mà `metrics.aggregate` đang đọc.
  Kiểm bằng cách chạy thử. Nếu phải sửa `src/` để đọc được thì đã làm sai —
  sửa `replay.py`.
- **10 câu `context` rỗng — SAO CHÉP HẰNG SỐ, không đưa qua mô hình.**
  V106–V113, V115, V116 (`top_k_count=0`). TASK-FT-00 chứng minh:
  `pipeline.py:223` `if not norm_ids:` **return trước** `assemble_context` và
  `generate_answer` — Gemini **chưa từng được gọi** cho 10 câu này; `answer` là
  hằng số cứng ở `pipeline.py:233`. Nhánh này thuộc **truy hồi**, mà truy hồi đã
  bị đóng băng → đầu ra của nó cũng phải đóng băng. Ghi y nguyên hằng số ở mọi
  hàng của ma trận. *(Lý do loại phương án “đưa `context=""` vào mô hình cục bộ”:
  nó bất đối xứng với hàng Gemini — 14 câu qua mô hình so với 4 — làm cột
  “Từ chối đúng” hết so sánh được.)*
- **4 câu negative còn lại (V005, V105, V114, V117) phát lại bình thường** —
  chúng có đi qua mô hình sinh. Đây mới là phần “Từ chối đúng” thực sự đo
  hành vi mô hình.
- **`INCLUDE_SCHEMA_B` phải là `false`.** Biến môi trường này đổi hình dạng
  system prompt và được đọc **lúc import module**, không đọc lại mỗi lần gọi.
  Mẻ 10/07 chạy với `false`; để `true` là prompt không còn trùng khít.
- **Chốt `build_messages`** (không phải `build_prompt`), ánh xạ (system, user)
  vào chat template của mô hình. Chỉ lùi về `build_prompt` nếu mô hình chốt ở
  FT-03 không có system role — và khi đó **cả sáu ô dùng chung một lựa chọn**.
  Trộn hai cách giữa các ô là tự tạo confound.
- **Assert schema trước khi ghi.** `aggregate` dùng `.get()` cho
  `citation_score_dieu` → thiếu field này thì **cột F1 cấp Điều ra 0.000 im
  lặng**, một trong bốn cột báo cáo sai mà không có dấu hiệu gì. Mọi item ghi
  ra phải đủ `citation_score`, `citation_score_dieu`, `norm_recall`,
  `elapsed_seconds`, `gap_type`, `theme`; riêng câu `gap_type=="negative"` phải
  có `negative_correct` (thiếu → `KeyError`).
- **Không sinh `NaN`.** File gốc chứa 118 literal `NaN` ở
  `faithfulness.support_rate` → JSON không chuẩn. Ta không đo tỉ lệ hậu thuẫn
  cho hàng cục bộ → đặt `faithfulness: null`.
- **Tham số sinh:** theo khuyến nghị Qwen cho bản 2507 — `temperature=0.7`,
  `top_p=0.8`, `top_k=20`, `min_p=0`, **`presence_penalty=0`** (chốt ở FT-03,
  §TASK-FT-03). **KHÔNG dùng `temperature=0`** (bản trước của kế hoạch ghi vậy —
  sai): greedy trên model này sinh lặp vô tận, lặp ăn hết `max_new_tokens`, mà
  khối trích dẫn nằm **cuối** câu trả lời nên bị cắt → F1 = 0 vì lý do thuần kỹ
  thuật. Cả sáu ô của FT-06 dùng **giống hệt** bộ tham số này. ⚠️ `presence_penalty`
  mặc định trong `replay.py:166` là **1.0**, không phải 0 → `kaggle_ft06.py` truyền
  tường minh `--presence-penalty 0` ở mọi ô; bảy giá trị còn lại để mặc định lo.
- **Tất định:** đến từ **seed cố định + cùng bản dựng llama.cpp + cùng phần
  cứng**, KHÔNG phải từ `temperature=0`. Đã chứng minh, không phải giả định:
  phiên 1 FT-03 chạy lại cùng lệnh cho `answer` **trùng khít từng ký tự 15/15
  câu**. Lập luận **N=1 ở §TASK-FT-06 dựa vào chính điều này** — nếu về sau đổi
  phần cứng hoặc bản dựng llama.cpp thì tiền đề đó không còn, phải đo lại trước
  khi giữ N=1. Ghi seed vào output.
- **Resume được:** ghi từng item ngay khi xong, `--resume` bỏ qua item đã có.
- `format_ok` ghi vào output như field phụ (dùng nội bộ, xem §3.1).
- **`max_new_tokens = 2048` và PHẢI log mỗi lần chạm trần.** Gemini trả lời rất
  ngắn (p50 = 257 token, max 1 313 — token_budget.md §2.6), nhưng khối trích dẫn
  nằm **ở cuối** câu trả lời. Mô hình nhỏ thường dài dòng hơn; nếu bị cắt thì
  khối trích dẫn mất → `parse_citations` trả `[]` → F1 = 0 vì lý do thuần kỹ
  thuật. Ghi field `hit_token_cap` (bool) cho mọi item. **Nếu tỉ lệ chạm trần
  khác 0 thì mọi con số của ô đó phải đọc lại trước khi đưa vào bảng.**
- CLI: `--input`, `--model`, `--out`, `--limit`, `--n-shot`, `--resume`, `--seed`.

**Test:** mock mô hình trả chuỗi cố định; xác nhận schema hợp lệ, item ngữ
cảnh rỗng được xử lý đúng, `format_ok` đúng ở cả ca parse được lẫn không.

**DoD:** `--limit 5` sinh ra file mà `metrics.aggregate` đọc được không cần
sửa `src/`.

---

### TASK-FT-03 — GATE: đo mô hình chưa tinh chỉnh ⚠️ GATE

**KHÔNG TRAIN TRƯỚC KHI QUA GATE NÀY.**

#### Tiêu chí tuyển ứng viên (sửa ở v2.2)

`token_budget.md` chứng minh đúng **hai** ràng buộc kỹ thuật:

1. **Cửa sổ ngữ cảnh gốc ≥ 32k** (nhu cầu thực ≈ 13 300 token; 8k loại dứt khoát —
   66% câu GraphRAG không vừa)
2. **Tokenizer ≥ 2.8 ký tự/token tiếng Việt**

> ⚠️ **Không có ràng buộc nào về số tham số.** Kết luận “phải thuộc lớp 7–8B”
> ở §0 và §4 của `token_budget.md` là kết luận về **danh sách ứng viên đã chọn**
> (toàn model đời 2024), không phải về ràng buộc. Một model 4B đời mới thoả
> cả hai. Nhầm chỗ này kéo theo rủi ro bộ nhớ T4 ở FT-05 một cách không cần thiết.

#### Mô hình đã CHỐT (v2.3)

| | |
|---|---|
| **Model ID** | `Qwen/Qwen3-4B-Instruct-2507` |
| Cửa sổ gốc | 262 144 token (nhu cầu thực ≈ 13 300) |
| Thinking | **Chỉ non-thinking** — không sinh `<think>`, không cần `enable_thinking=False` |
| GGUF | Unsloth có sẵn, đường QLoRA → merge → GGUF Q4_K_M đã ổn định |

**Không còn danh sách ứng viên, không còn vòng sàng lọc.** Lý do bỏ (§9.5):
việc chọn mô hình sinh ra toàn bộ vấn đề độ phân giải thống kê (n≈12 không phân
biệt được 10% với 30%) và selection-on-test, trong khi **không phục vụ mục đích
nào của mục 4.7**. Mục 4.7 cần ĐO ĐƯỢC Δ, không cần mô hình cục bộ điểm cao.

> **FT-03 KHÔNG phải selection-on-test.** Vì không chọn gì cả, nó chỉ là **chạy
> sớm 15 trong số 137 câu mà hàng “cục bộ chưa tinh chỉnh” đằng nào cũng phải
> chạy đủ**. Xem trước một phần của thí nghiệm thật, không lọc, không phải khai
> báo gì. Đây cũng là lý do không cần bộ dev 26 câu.

**Mọi model ID phải verify trên model card trước khi tải.** Tên ghép theo trí nhớ
rất dễ sai (ví dụ: `Qwen3.5-4B` **không có** hậu tố `-Instruct`).

#### Một cạm bẫy duy nhất

**Dùng bản Instruct, KHÔNG dùng bản base.** Hàng “cục bộ chưa tinh chỉnh” phải là
model biết follow instruction; bản base ra 0 vì lý do tầm thường và không đo được gì.
*(Cạm bẫy hybrid-thinking biến mất vì bản 2507 chỉ có non-thinking.)*

#### Quy trình

1. Chọn 15 câu phân tầng: 3 mỗi nhóm thách thức + 3 bẫy phủ định.
2. Chạy qua `replay.py`, **bốn biến thể**: {zero-shot, few-shot 2 ví dụ} ×
   {`presence_penalty=1.0`, `presence_penalty=0`}.
   *(Lý do thử pp=0: tác vụ là CHÉP NGUYÊN VĂN slug từ ngữ cảnh, mà presence
   penalty phạt đúng token đã xuất hiện — tức phạt đúng hành vi ta cần.)*
3. Kiểm ba thứ về hạ tầng: đường **llama-cpp-python in-process**
   (`Llama.create_chat_completion`) có chạy không — **không có llama-server, không
   có HTTP**; `usage.prompt_tokens` lấy từ **trả về của chính hàm đó**; prompt render qua
   chat template có đúng không (`--dump-prompt`, nhìn bằng mắt); số token prompt
   tự đếm có khớp `usage.prompt_tokens` của server không.
4. Báo cáo `format_ok_rate`, F1 cấp Khoản thô, và hai chỉ báo chẩn đoán dưới đây.

#### Hai chỉ báo chẩn đoán

`format_ok` là sàn rất thấp (chỉ cần 1 khối parse được, đúng sai không tính) nên
một mình nó không phân biệt được hai kiểu hỏng rất khác nhau. Thêm:

| Chỉ báo | Định nghĩa |
|---|---|
| `soft_article_hit` | **Bộ trích LỎNG**: quét văn bản thô tìm mọi cụm `Điều \d+`, `Khoản \d+`, và chuỗi giống slug `[a-z0-9-]{15,}` — **bất kể có trong ngoặc vuông hay không** — rồi đối chiếu với ngữ cảnh đưa vào |
| `no_loop` | Không chạm trần token (đã có: `hit_token_cap`) |

⚠️ **Bộ trích lỏng là bắt buộc**, không được dùng `pred_citations`: khi
`format_ok = 0` thì không có trích dẫn nào để kiểm → chỉ báo undefined đúng lúc
cần nó nhất.

| `soft_article_hit` | `format_ok` | Chẩn đoán |
|---|---|---|
| cao | thấp | Biết điều luật nào, không biết viết cú pháp → **đúng thứ tinh chỉnh sửa được** |
| thấp | thấp | Không định vị được điều luật trong ngữ cảnh 12k → **ngoại lệ duy nhất được leo thang lên 8B** |
| — | — | `no_loop` thấp → lỗi tham số sinh, chưa kết luận gì. Sửa `presence_penalty` rồi đo lại |

#### Đọc kết quả


| format_ok_rate (few-shot) | Hành động |
|---|---|
| > 50% | Đi tiếp bình thường. |
| 10–50% | Đi tiếp. Ghi rõ trong mục 4.7 rằng một phần chênh lệch đến từ tuân thủ định dạng. |
| < 10% | Mô hình chưa tinh chỉnh không dùng nổi định dạng → hàng "cục bộ chưa tinh chỉnh" sẽ ≈ 0. **Vẫn đi tiếp** — đó chính là kết quả cho thấy tinh chỉnh là *điều kiện cần* để mô hình nhỏ tham gia được kiến trúc. |

Gate này không để huỷ kế hoạch, mà để **biết trước sẽ viết gì** trước khi
tốn công huấn luyện.

**Đầu ra:** `finetune/reports/gate_base_model.md` + chốt mô hình.

---

### TASK-FT-04 — Chuẩn bị dữ liệu huấn luyện

**Nguồn:** `thangvip/vietnamese-legal-qa` — 9.715 dòng / 29.145 cặp QA,
141 giá trị `doc_name`. Trường: `doc_name`, `doc_type_name` (**chỉ một giá
trị "Luật"** → toàn bộ là cấp luật), `article_content` (17 → 436k ký tự),
`generated_qa_pairs` (list 3 phần tử: `question`, `answer`, `question_type`,
`difficulty`).

Đáp án trong bộ dữ liệu trích dẫn **trong văn xuôi** ("Theo Khoản 1 Điều 5
Luật…"), **không** ở dạng mà `parse_citations` đọc được. Đây là điểm phải sửa.

#### Nguyên tắc cốt lõi

> **Dạy mô hình CHÉP TỪ NGỮ CẢNH, đừng dạy nó NHỚ.**

Slug sinh ra ở bước 3 là slug tổng hợp, không có trong corpus 32 văn bản.
Không sao — **miễn là slug đó xuất hiện trong header ngữ cảnh của mẫu huấn
luyện**. Khi ấy việc mô hình học là *"tìm block đúng, chép slug ở header ra
khối trích dẫn"*, và kỹ năng đó chuyển giao sang 32 văn bản thật dù mô hình
chưa từng thấy slug nào của đề tài.

Nếu slug chỉ có ở đầu ra mà không có ở đầu vào, ta đang dạy mô hình bịa slug
từ trí nhớ. **Đây là lỗi thiết kế nghiêm trọng nhất có thể mắc ở task này.**

#### Năm bước

1. **Lọc rò rỉ.** Đọc frontmatter `id` + `title` của `data/raw/*.md` → danh
   sách 32 văn bản. Drop mọi dòng có `doc_name` khớp (chuẩn hoá bỏ dấu,
   lowercase, so số hiệu). Thêm lớp nữa: n-gram overlap giữa `question` và
   137 câu trong `test_set_v2.json`. **Ghi lại số bị drop và lý do** — đoạn
   này viết được thành một câu trong phần phương pháp.
2. **Lọc độ dài.** Bỏ `article_content` > 50k và < 200 ký tự.
3. **Suy slug / Điều / Khoản (cơ khí, không dùng LLM).** Slug từ `doc_name`
   theo convention `[loai-van-ban]-[slug-ten]-[nam]`; số Điều regex từ đầu
   `article_content`; Khoản/Điểm regex từ prose của `answer`. Hàm slug nằm
   riêng ở `finetune/slug.py`, **có unit test**.
4. **Gộp đa điều.** Một điều đơn lẻ (~2–3k ký tự) quá ngắn so với ngữ cảnh
   thật (mean 13,2k) và **không có nhiễu** → mô hình sẽ học thói quen "ngữ
   cảnh chỉ có một điều, cứ trích điều đó", rồi gặp ngữ cảnh 13k với 10–20
   block thì trích thừa. Gộp 4–6 điều cùng `doc_name`, đặt điều gold lẫn giữa
   distractor ở vị trí ngẫu nhiên. Độ dài mục tiêu lấy từ TASK-FT-01.

   ⚠️ **Sinh ở CẢ HAI khuôn header, tỉ lệ xấp xỉ cân bằng.** TASK-FT-00 phát
   hiện hai khuôn khác hẳn nhau:

   ```
   GraphRAG:  --- [Tier {N} | Hiệu lực: {YYYY-MM-DD}] Điều …, Khoản …. ({slug}) ---
   Baseline:  --- Văn bản: {slug}, chunk {i} ---
   ```

   GraphRAG đặt slug **trong ngoặc đơn cuối header**; baseline đặt **sau
   `Văn bản: `**. Nếu chỉ dạy khuôn GraphRAG, mô hình tinh chỉnh sẽ đọc cột
   Naive RAG kém hơn **vì lý do định dạng**, làm Δ ở hàng đó phồng lên giả
   tạo → ta sẽ kết luận “đồ thị giúp” trong khi một phần là “mô hình quen khuôn
   header của đồ thị”. Đây đúng loại confound làm hỏng mục 4.7.
   *(Hàng “cục bộ chưa tinh chỉnh” không dính vấn đề này vì không huấn luyện gì.)*

   Khuôn GraphRAG còn có biến thể hết hiệu lực
   (`Hiệu lực: D → D (HẾT HIỆU LỰC)`, 45/2199 header thực tế) và khối
   `[AMENDMENT WARNING — …]` xen giữa header và nội dung (có ở 104/137 item).
   Không bắt buộc tái tạo hai thứ này trong dữ liệu huấn luyện, nhưng nếu
   tái tạo thì phải đúng nguyên văn khuôn ở api_contract.md §6.
5. **Nối khối trích dẫn** đúng cú pháp đích (api_contract.md §3.2) vào cuối
   đáp án. Đa dạng hoá câu mở đầu — gần như đáp án nào cũng bắt đầu bằng
   "Theo…", mô hình sẽ nhiễm tic đó.

   Cú pháp đích (đã xác minh trên 401/401 khối thực tế):

   ```
   [Điều {số}, Văn bản {slug}]
   [Điều {số}, Khoản {số}, Văn bản {slug}]
   [Điều {số}, Khoản {số}, Điểm {chữ}, Văn bản {slug}]
   [Phụ lục {ký hiệu}, Văn bản {slug}]
   ```

   Phân cách `, ` (phẩy + một khoảng trắng); `Văn bản` luôn **cuối**; giá trị là
   **slug**, không phải số hiệu pháp lý.

   Hai ràng buộc từ TASK-FT-00, **có bằng chứng**:
   - **Không dạy `Tiết`** — 0/401 khối thực tế dùng, và không `pred_citations`
     nào có `tiet` khác `None`.
   - **Không dùng `Mục` / `Dòng` / `Phần`** — parser không nhận, bỏ qua **im
     lặng**, và có thể khiến hai khối khác nhau trở nên trùng rồi bị dedupe
     (ca thật: V119, V131). Chỉ dùng 6 từ khoá parser hiểu:
     `Điều`, `Phụ lục`, `Khoản`, `Điểm`, `Tiết`, `Văn bản`.

#### Ràng buộc bắt buộc: dựng mẫu bằng chính `build_messages` (v2.2)

System prompt thật là **3 936 token** (`general`) / **4 034** (`irac`) — chiếm **46%
ngân sách ở câu trung vị** (token_budget.md §2.2). Nếu huấn luyện với một system
prompt rút gọn tự chế rồi đánh giá với khối 3 936 token, mô hình **chưa từng thấy
tác vụ mà nó bị chấm**.

Cách bảo đảm: FT-04 dựng mẫu bằng chính
`src…build_messages(question, packed_context, mode)` — **cùng hàm mà FT-02 dùng** —
chứ không tự ghép chuỗi. Khi đó train và eval đồng nhất **theo xây dựng**, không
phải theo cẩn thận.

Hệ quả: seq length mẫu train = 3 936 + context + answer → khớp
`max_seq_length = 16384` ở FT-05.

Độ dài context mục tiêu (token Qwen2.5, token_budget.md §2.7.2):

| Khuôn | p50 | p95 | max |
|---|---:|---:|---:|
| GraphRAG | ~4 200 | ~7 600 | ~8 000 |
| Baseline | ~1 800 | | ~2 450 |

*Ghi chú mode:* 13/127 câu eval là `irac`. Dữ liệu huấn luyện có thể chỉ dùng
`general` — tỉ lệ `irac` quá nhỏ để đáng công dựng đáp án theo cấu trúc 4 heading.
Ghi vào giới hạn §8.

#### Tỉ lệ mẫu TỪ CHỐI: 9%, chia 70/30

Bộ nguồn `thangvip` **không có mẫu từ chối nào**. 5 000 mẫu toàn câu trả lời được
sẽ dạy mô hình "luôn luôn trả lời" — phiên 1 FT-03 đã đo đúng hướng đó:
`tu_choi_dung` tụt **0.667 → 0.333** khi bật few-shot toàn ví dụ trả lời được. Nên
phải có mẫu từ chối. Câu hỏi là **bao nhiêu**.

| | |
|---|---|
| Tỉ lệ | **9%** — 450/5 000 (`FRAC_REFUSAL = 0.09` trong `build_dataset.py`) |
| Chia | **70/30** — 315 `refusal_no_basis` / 135 `refusal_out_of_scope` |

**Vì sao 9% chứ không phải 20%** (mẻ đầu đặt 0.20 = 1 000 mẫu): chỉ **4/127** câu
đi qua mô hình sinh nằm ở nhánh phủ định — 10/14 câu bẫy do nhánh truy hồi rỗng
quyết định, mô hình chưa từng được gọi (§9.1) — trong khi **F1 cấp Khoản đo trên
123 câu**. Dành 20% ngân sách huấn luyện cho hành vi từ chối là **đem 123 câu ra
đánh cược để bảo vệ 4 câu**. Đây là bất đối xứng rủi ro, không phải tinh chỉnh
tham số.

**Vì sao vẫn nghiêng về `no_basis`:** V005 — ca `no_basis` duy nhất trong eval — là
ca mà **cả Gemini cũng trả lời quá đà** (`negative_correct=False`), tức hành vi khó,
cần nhiều mẫu. Ba ca `out_of_scope` ngược lại: được chi phối bởi **danh sách chặn
tường minh** ở `src/retrieval/context_assembler.py:368-373` (system prompt liệt kê
thẳng chủ đề ngoài phạm vi kèm nguyên văn câu phải trả lời) nên cần ít mẫu hơn.

⚠️ 9% là **giả định có lập luận, không phải số đo**. Nếu hàng "cục bộ đã tinh chỉnh"
cho `tu_choi_dung` tụt so với hàng chưa tinh chỉnh thì đây là biến đầu tiên phải xem
lại. Chi tiết + số đo thực tế: `finetune/reports/dataset_stats.md` §4.2.

**DoD:** `slug.py` có ≥10 ca test; 0 mẫu còn khớp danh sách chặn (assert
trong test); phân phối độ dài khớp xấp xỉ TASK-FT-01; **in 20 mẫu ngẫu nhiên
đầy đủ để người đọc kiểm tay trước khi huấn luyện** — không được bỏ qua.

---

### TASK-FT-05 — Huấn luyện QLoRA

**Chạy ở Kaggle Notebooks (T4 16GB, 30 giờ/tuần miễn phí).** GPU 1650 Ti 4GB
không train được ở độ dài chuỗi này.

Hiện thực **không phải notebook** như bản trước ghi (`finetune/notebooks/train_qlora.ipynb`)
mà là ba file script:

| File | Vai trò |
|---|---|
| `finetune/train_qlora.py` | script huấn luyện — tự render chat template, `train_on_responses_only`, audit độ dài, `--val-dataset` / `--val-limit` |
| `finetune/run.sh` | 7 chặng trên RunPod: `preflight → install → data → train → merge → gguf → publish`, tự huỷ pod ở mọi đường thoát |
| `finetune/upload_dataset.sh` | chạy **trên máy người dùng**: đẩy `train.jsonl`/`val.jsonl` + `.sha256` lên HF dataset repo (`.gitignore` chặn `*.jsonl` nên pod không lấy được qua git) |

Nội dung: nạp mô hình đã chốt ở FT-03 → nạp train/val jsonl → QLoRA
**`r=16`, `alpha=32`** (`run.sh` truyền **tường minh** `--lora-r 16 --lora-alpha 32`
— mặc định trong `train_qlora.py` là 32/64, nên không truyền là chạy sai kế hoạch mà
không có dấu hiệu gì) → `lr=2e-4`, 2 epoch, **`max_seq_length = 16384`**
(đã chốt ở FT-01 — không hardcode 8192, cũng không cần 32k) → log train/val loss
(`eval_strategy="epoch"`, `--val-limit 64`, ghi `eval_history` vào
`train_result.json`) → merge LoRA → export GGUF Q4.

**Dry-run trên Kaggle phải bỏ chặng preflight** (`STAGES=install,train`): preflight
chặn `sm < 80`, mà Kaggle chỉ có T4 = `sm75`. Hệ quả phải ghi nhận: dry-run Kaggle
**không kiểm được đường bf16/FlashAttention-2** — `sm75` không có bf16 gốc nên script
tự chuyển sang fp16. Nó chứng minh "đường code chạy hết", không chứng minh đường số
học thật của RTX 4090.

**Bật dynamic padding / length-grouped batching.** Mẫu p50 chỉ ~8 000 token; trả phí
16k cho mọi mẫu là lãng phí và làm căng bộ nhớ vô cớ.

**Nhất quán lượng tử hoá:** train 4-bit rồi đánh giá bf16 (hoặc ngược lại)
gây tụt chất lượng âm thầm không giải thích được. Chốt **một artifact GGUF Q4
duy nhất** dùng cho mọi phép đo.

---

### TASK-FT-06 — Chạy đủ sáu ô

**Chạy ở Kaggle Notebooks (T4)** — cùng nền đã dùng cho FT-03 và FT-05, nên bản dựng
llama.cpp và phần cứng khớp với phiên gate. Hiện thực: `finetune/kaggle_ft06.py`
(năm chặng `--stage`) + `finetune/notebooks/ft06_eval.ipynb` (bốn ô mỏng).

Khối lượng: **sáu ô × 137 câu = 822 lượt sinh** (không phải 548 như bản trước).

#### Sáu ô, không phải bốn

| # | Mô hình | `--n-shot` | Khuôn ngữ cảnh | `--tag` |
|---:|---|---:|---|---|
| 1 | đã tinh chỉnh | 0 | GraphRAG | `ft06-ft-s0` |
| 2 | đã tinh chỉnh | 0 | Naive RAG | `ft06-ft-s0` |
| 3 | gốc | 2 | GraphRAG | `ft06-base-s2` |
| 4 | gốc | 2 | Naive RAG | `ft06-base-s2` |
| 5 | gốc | 0 | GraphRAG | `ft06-base-s0` |
| 6 | gốc | 0 | Naive RAG | `ft06-base-s0` |

**Thứ tự có chủ ý:** ô giá trị nhất trước. Session Kaggle đứt bất cứ lúc nào và
`/kaggle/working` bị xoá theo session — hàng "đã tinh chỉnh" là hàng mới duy nhất
của mục 4.7 nên nó chạy trước, và kết quả được đẩy lên HF `session3_ft06/` **ngay
sau từng ô** thay vì đợi tới cuối.

**Vì sao hàng FT chỉ chạy 0-shot.** Bộ huấn luyện FT-04 dựng bằng **chính**
`build_messages` (README `finetune/` §FT-04 điểm 1), tức mô hình đã được dạy đúng
khuôn `(system, user)` hai lượt. Chèn thêm hai cặp minh hoạ định dạng vào lúc đánh
giá là tạo **lệch train/eval** — đo một cấu hình mà tinh chỉnh chưa từng thấy, rồi
gán chênh lệch cho "tinh chỉnh". 0-shot là cấu hình khớp với cách nó được huấn luyện.

**Vì sao hàng gốc chạy CẢ HAI.** Với mô hình gốc, few-shot là **biến thật, đã đo**:
`format_ok` nhảy 0.083 → 0.833 khi bật `--n-shot 2` (`gate_base_model.md` §1). Báo
đúng một biến thể là chọn hậu nghiệm — 0-shot làm hàng gốc trông tệ hơn thực tế,
2-shot làm nó trông tốt hơn cấu hình mà hàng FT được đo. Báo cả hai, để người đọc
thấy trần và sàn của "chưa tinh chỉnh".

#### Nguồn ngữ cảnh — cặp file 20260710-085236

```
data/evaluation/results_graphrag_20260710-085236.json
data/evaluation/results_baseline_20260710-085236.json
```

**Phải là cặp file của CÙNG một mẻ chạy**, và đúng mẻ này: nó chính là mẻ sinh ra
**0.578** (GraphRAG) và **0.435** (Naive RAG) ở hàng Gemini của ma trận §2. Trộn hai
timestamp khác nhau là đổi luôn vế trái của cột Δ — số cục bộ khi đó so với một cấu
hình truy hồi khác cái hàng Gemini đã dùng, mà không có gì trong file kết quả báo
động điều đó.

#### Hai cổng chặn trước khi tiêu 822 lượt

**CỔNG CHẶN A — chat template** (`--stage gate-template`). Đọc
`tokenizer.chat_template` nhúng trong **cả hai** file GGUF, so độ dài + sha256, ghi cả
hai ra `finetune/reports/ft06_chat_template_{base,ft}.jinja`. Khác nhau → **dừng
(exit 2)**: hai hàng của ma trận sẽ nhận prompt khác nhau và cột Δ không còn đo mô
hình sinh mà đo cả khác biệt prompt. Cổng này là mới ở FT-06 vì FT-05 đi qua đường
merge LoRA → convert → quantize, mỗi chặng đều có thể ghi lại metadata.

**CỔNG CHẶN B — prompt đã render** (`--stage gate-prompt`). Đây là **món nợ của
FT-03**: `gate_base_model.md` §5 ghi kiểm tra hạ tầng #2 là ⚠️ CÒN TREO — hai file
`--dump-prompt` đã sinh nhưng *chưa ai mở ra nhìn bằng mắt*, mà "nhìn bằng mắt" mới
là nội dung của kiểm tra. §7 xếp nó là việc **$0 và chặn cứng** phải làm trước FT-06.
Chặng này đóng nợ đó: sinh prompt cho cả bốn tổ hợp `{graphrag, baseline} × {0, 2}`,
kiểm tự động năm mục (render bằng chat template thật chứ không phải nhánh lùi
`render-loi:` · 200 ký tự đầu system prompt khớp `build_messages` · số lượt vai 2 hay
6 · kết thúc bằng `TRẢ LỜI:` rồi tới thẻ mở vai assistant · số thẻ mở vai assistant 1
hay 3), rồi in 40 dòng đầu + 20 dòng cuối mỗi file để người đọc nhìn tận mắt. Bất kỳ
mục FAIL → **exit 2**.

#### Số lần chạy: N=1 cho cả sáu ô — CHỐT, không để ngỏ

**Hai căn cứ:**

**(a) Tiền lệ trong chính báo cáo.** Bảng 4.3 dùng N=3 cho GraphRAG và Naive RAG,
nhưng **Bảng 4.5 báo cáo Oracle / BM25 / Closed-book ở một lần chạy**. Mục 4.7 là
cùng loại bảng với 4.5 (so cấu hình, không so σ) nên theo đúng tiền lệ đó.

**(b) Tính tất định đã được chứng minh, không phải giả định.** Phiên 1 của FT-03:
hai lần chạy cùng seed, cùng build, cùng phần cứng cho `answer` **trùng khít từng
ký tự trên 15/15 câu** (`finetune/reports/gate_base_model.md`). Khi lặp lại cho ra
đúng cùng một chuỗi thì σ giữa các lần chạy **bằng 0 theo cấu tạo** — chạy thêm hai
lần nữa chỉ chép lại cùng một file. Đây là khác biệt thật so với hàng Gemini: Gemini
không tất định (đã ghi nhận ở D-24, "Q018 win là non-determinism"), nên N=3 ở Bảng
4.3 giải quyết một vấn đề mà hàng cục bộ không có.

**Vì sao KHÔNG lồng nhiều seed vào `replay.py`.** Cách rẻ nhất về mặt code — chạy 3
seed rồi ghi cả 3 vào cùng một results JSON — làm **hỏng im lặng** hai con số của
bảng, không raise gì:

| Đại lượng | Đúng | Sau khi lồng 3 seed |
|---|---:|---:|
| mẫu số `format_ok_rate` | 123 | 369 |
| `negative_count` (nhãn cột "Từ chối đúng") | 14 | **42** |

`metrics.aggregate` đếm **phẳng theo item**: `negs = [q for q in per_question if
q["gap_type"] == "negative"]` rồi `negative_count = len(negs)`
(`src/evaluation/metrics.py:226-229`), và con số đó được in thẳng vào nhãn cột
(`metrics.py:304-308`). Cột sẽ hiện "Từ chối đúng (42 câu)" trong khi bộ test chỉ có
14 câu phủ định — sai mà **không có dấu hiệu gì**, đúng loại lỗi mà §TASK-FT-02 đã
phải dựng assert schema để chặn.

**Nếu về sau muốn σ:** nâng N=3 cho **riêng hàng "cục bộ đã tinh chỉnh"** bằng **ba
lần chạy ĐỘC LẬP** (ba lệnh, ba file results, ba lần `aggregate`, rồi báo mean ± σ
như `build_reproducibility_report.py` đang làm) — **không sửa code**. Chi phí: hàng
FT là ô 1 + ô 2 = 274 lượt, nên +2 × 274 = **548 lượt** phụ. Với mô hình tất định thì
khoản chi đó mua được σ = 0,
nên chỉ làm nếu có lý do khác (ví dụ đổi phần cứng giữa chừng, hoặc bản llama.cpp
khác) khiến tính tất định không còn được bảo đảm.

Chạy `metrics.aggregate` trên kết quả, lập bảng theo đúng bốn cột ở §3.

---

### TASK-FT-07 — Viết mục 4.7 và sửa 5.4

1. Lập bảng ma trận §2 với bốn cột thang đo.
2. Viết mục 4.7 theo khung ở §1.2: nêu rõ đây là **trục trực giao** với Bảng
   4.2, không phải hệ tham chiếu thứ năm.
3. **Sửa mục 5.4** — gạch đầu dòng "tinh chỉnh mô hình sinh" không còn thuần
   là hướng phát triển.
4. Nếu Δ suy giảm ở hàng cục bộ → bổ sung một gạch đầu dòng vào **5.3**.

---

## 7. Ba kịch bản — cả ba đều viết được

| Kịch bản | Diễn giải |
|---|---|
| Δ dương ở cả ba hàng | Ưu thế kiến trúc không phụ thuộc mô hình sinh → củng cố Câu hỏi 1 |
| Δ dương nhưng thu hẹp ở hàng cục bộ | Ưu thế đồ thị cần mô hình sinh đủ mạnh mới hiện thực hóa hết → bổ sung 5.3 |
| Δ triệt tiêu ở hàng cục bộ | Giới hạn thật của kiến trúc khi hạ cấp mô hình sinh → bổ sung 5.3 |

Báo cáo đã có truyền thống ghi nhận kết quả âm một cách trung thực (bộ lọc
địa phương ở mục 4.3, chênh lệch BM25 ở mục 4.5, thiên lệch bộ chấm ở 5.3).
Hai kịch bản sau nằm gọn trong truyền thống đó.

---

## 8. Giới hạn phải ghi trong mục 4.7

1. **Bộ dữ liệu huấn luyện chỉ có văn bản cấp luật** (`doc_type_name` một giá
   trị "Luật") — không có nghị định, thông tư, văn bản địa phương. Tinh chỉnh
   này dạy được **định dạng trích dẫn và từ vựng pháp lý cấp luật**, không dạy
   suy luận đa tầng hay ràng buộc địa phương. Điều đó có lợi cho lập luận: nó
   tách bạch đóng góp của tinh chỉnh khỏi đóng góp của kiến trúc.
2. **Đáp án trong bộ dữ liệu do mô hình ngôn ngữ sinh tự động**, không phải
   người viết.
3. **`response_mode` khôi phục bằng regex**, không phải giá trị gốc.
4. **Truy hồi bị đóng băng theo một mẻ chạy cụ thể.** Đây là điểm mạnh (cô
   lập biến sạch) nhưng cũng là giới hạn: không đo được tương tác giữa mô hình
   cục bộ và truy hồi động.
5. **Cột “Từ chối đúng” không phải thuộc tính thuần của mô hình sinh.** 10/14
   câu bẫy phủ định được quyết định bởi nhánh `if not norm_ids` của truy hồi,
   không qua mô hình sinh; chỉ 4 câu còn lại đo hành vi mô hình. **Điều này đúng
   cho cả hàng Gemini đã có trong Bảng 4.5** (13/14 = 10 câu “miễn phí” + 3/4 câu
   thực đo). Một câu ghi chú trong mục 4.7 là đủ; cột vẫn so sánh được giữa các
   hàng vì cùng cấu trúc.

---

## 9. Quyết định chốt sau TASK-FT-00 (v2.1)

Nguồn: `finetune/reports/api_contract.md` — đã đối chiếu code thật và 137 item
của cả hai file 10/07. Round-trip `parse_citations(answer) == pred_citations`
đúng 0 sai lệch trên cả hai file → hợp đồng đích đáng tin.

### 9.1 Ba quyết định đã chốt

| # | Câu hỏi | Quyết định | Sửa ở mục |
|---|---|---|---|
| 1 | 10 câu ngữ cảnh rỗng | **Sao chép hằng số** ở mọi hàng (phương án a) | TASK-FT-02, §8.5 |
| 2 | `format_ok_rate` tính trên tập nào | **123 câu có GT khác rỗng** | §3.1 |
| 3 | `build_messages` hay `build_prompt` | **`build_messages`**, cố định qua cả sáu ô | TASK-FT-02 |

**Luận cứ cho (1):** nguyên tắc nền của toàn bộ thí nghiệm là *đóng băng truy
hồi, chỉ đổi mô hình sinh*. Nhánh `if not norm_ids` nằm trong truy hồi → đầu ra
của nó cũng phải đóng băng. Đây không phải “bỏ qua phép đo” mà là tái tạo
trung thực điều kiện gốc.

> **Sửa lỗi của v2.0:** bản trước mô tả 10 câu này là “truy hồi cố ý trả rỗng để
> hệ từ chối trả lời” và lấy đó làm lý do giữ chúng để đo “mô hình nhỏ có bịa
> khi ngữ cảnh rỗng không”. Sai: mô hình sinh chưa từng được gọi ở nhánh này.

### 9.2 Bốn ràng buộc bổ sung

1. **System prompt 11 264 ký tự** (`general`), không phải ~2117 token như ghi
   chú D-15 cũ → kỳ vọng cửa sổ **16k là sàn**. (TASK-FT-01)
2. **`INCLUDE_SCHEMA_B=false`** khi phát lại — đọc lúc import, đổi sau khi
   import không có tác dụng. (TASK-FT-02)
3. **Assert schema + không sinh `NaN`** — thiếu `citation_score_dieu` làm cột F1
   cấp Điều ra 0.000 im lặng. (TASK-FT-02)
4. **Huấn luyện trên cả hai khuôn header** — nếu không, Δ ở hàng “cục bộ đã
   tinh chỉnh” phồng lên giả tạo vì mô hình quen khuôn GraphRAG. (TASK-FT-04)

### 9.3 Ghi chú cho TASK-FT-01

api_contract.md §5.3 đo được **13/137** answer có heading `### Vấn đề` (số liệu
thô). Xác nhận lại con số này và kiểm xem còn dấu hiệu nào khác của mode `irac`
không, trước khi chốt `mode_map.json`. Lưu ý `build_messages` có **fallback im
lặng**: giá trị `mode` lạ không raise mà âm thầm về `general`.

### 9.4 Sửa sau TASK-FT-01 (v2.2)

Nguồn: `finetune/reports/token_budget.md`.

**Số đã chốt:**

| Đại lượng | Giá trị |
|---|---|
| `max_seq_length` (FT-05) | **16 384** |
| System prompt | 3 936 token (`general`) / 4 034 (`irac`) |
| Ký tự/token tiếng Việt (Qwen2.5) | 2.87 |
| `response_mode` | graphrag **13 `irac` / 114 `general` trên 127 câu đi qua mô hình sinh** (10 câu còn lại ngữ cảnh rỗng, chưa từng gọi mô hình → không có mode); baseline **137 `general`, tất định theo code** |

#### Quy ước mẫu số — dùng thống nhất từ đây

Kế hoạch trước dùng lẫn 137 và 127 cho cùng một đại lượng. Chốt:

| Mẫu số | Nghĩa | Dùng ở đâu |
|---:|---|---|
| **137** | **tổng bộ câu hỏi** `test_set_v2.json` | khối lượng chạy (137 × 6 ô = 822), `negative_count` = 14 |
| **127** | **số câu ĐI QUA MÔ HÌNH SINH** = 137 − 10 câu ngữ cảnh rỗng (V106–V113, V115, V116; `pipeline.py:223` return trước `generate_answer`) | mọi phát biểu về hành vi mô hình sinh: tỉ lệ `irac`, số câu phủ định thực đo (4/127) |
| **123** | số câu có `ground_truth_citations` **khác rỗng** | **chỉ** mẫu số của `format_ok_rate` (§3.1) |

Hệ quả cụ thể: "13/127 câu eval là `irac`" (§TASK-FT-04) là **đúng** — 13 câu `irac`
trong 127 câu đi qua mô hình. Con số thô "13/137" ở §9.3 là số **đếm trên file** trước
khi loại 10 câu ngữ cảnh rỗng; hai con số không mâu thuẫn, chỉ khác mẫu số, và từ nay
**phát biểu bằng 127**.

**Bốn sửa đổi:**

1. **FT-03** — bỏ mệnh đề “phải thuộc lớp 7–8B”. Chỉ có hai ràng buộc thật (cửa
   sổ ≥ 32k, tokenizer ≥ 2.8 ký tự/token), cả hai đều không phải hàm của số tham
   số. Ứng viên chính: `Qwen/Qwen3-4B-Instruct-2507`.
2. **FT-04** — dựng mẫu huấn luyện bằng chính `build_messages`, để system prompt
   khi train trùng khít khi eval.
3. **FT-02** — `max_new_tokens = 2048` + log `hit_token_cap`.
4. **FT-05** — `max_seq_length = 16384` + dynamic padding.

**Một rủi ro đã giảm nhưng chưa biến mất:** T4 là `sm75`, không có
FlashAttention-2 (đòi `sm80`+). Ở 4B + dynamic padding thì khả thi hơn nhiều so
với 7B, nhưng **vẫn chưa đo**. *(v2.3.3: đoạn "vì đã thuê GPU cho FT-06 thì thuê
luôn cho FT-05" không còn đúng — FT-06 chạy trên Kaggle T4, không thuê GPU. Ràng buộc
`sm75` vì thế vẫn còn, và FT-05 đã ghi nhận nó: dry-run Kaggle không kiểm được đường
bf16/FlashAttention-2, script tự chuyển sang fp16.)*

**Một giới hạn giữ nguyên:** `response_mode` của cột GraphRAG là **suy luận bằng
regex**, không phải giá trị gốc. Bằng chứng rất mạnh (phân bố lưỡng cực tuyệt
đối, 0 false positive ở phép thử âm tính) nhưng không loại được false negative
của lối thoát `irac` không heading. Giữ §8.3.

### 9.5 Rút gọn FT-03 (v2.3)

**Vấn đề:** gate vốn có **một** mục đích — chạy thử rẻ để *biết trước sẽ viết gì*
trước khi tiêu tiền huấn luyện. Nó bị gán thêm việc thứ hai: **chọn giữa 2–3 ứng
viên**. Toàn bộ phức tạp phát sinh — khoảng tin cậy Wilson, yêu cầu nâng lên 30 câu
phân tầng, đi tìm bộ dev 26 câu, lo selection-on-test — **đều sinh ra từ việc thứ
hai**, không phải việc thứ nhất.

**Quyết định:** chốt `Qwen/Qwen3-4B-Instruct-2507`, bỏ vòng sàng lọc. Hệ quả:

| Vấn đề trước đó | Trạng thái |
|---|---|
| n≈12 không phân biệt được 10% với 30% | Biến mất — không còn phải phân biệt |
| Selection-on-test | Biến mất — không chọn gì thì không có selection |
| Cần bộ dev 26 câu | Không cần nữa |
| Nâng lên 30 câu phân tầng | Không cần — giữ 15 |

**Lý do học thuật, không chỉ là tiện:** mục 4.7 cần **đo được Δ**, không cần mô
hình cục bộ điểm cao. Mô hình càng nhỏ mà Δ vẫn dương thì lập luận càng mạnh.
Tối ưu F1 tuyệt đối của hàng cục bộ là **tối ưu nhầm đại lượng**.

**Ngoại lệ duy nhất được leo thang lên 8B:** `format_ok` **và** `soft_article_hit`
**cùng ở sàn** — tức 4B không định vị nổi điều luật trong ngữ cảnh 12k chứ không
chỉ viết sai cú pháp. Lý do khi đó không phải “8B tốt hơn” mà là “8B là mức nhỏ
nhất còn đo được Δ”. Lưu ý chi phí kèm theo: FT-06 ở 8B ước ~15–16 giờ, **vượt
trần 12 giờ/phiên của Kaggle** → phải hai phiên kèm `--resume`.

**Công dụng mới của bộ dev 26 câu:** không dùng cho gate, nhưng 3 file graphrag có
`context` đầy đủ (`20260520-210859`, `20260520-211930`, `20260528-142757`, 26/26
item) dùng được làm **tập kiểm tra trong lúc huấn luyện** ở FT-05. Đã xác minh:
0 trùng id, 0 trùng câu hỏi, 0 gần trùng (Jaccard cao nhất 0.68) với 137 câu.
*Lưu ý khi dùng:* 26/26 câu thuộc riêng lĩnh vực đất đai, và 37% tuple GT
(Điều, Khoản, văn bản) có giao với 137 câu — đủ sạch để theo dõi loss, không đủ
sạch để báo như kết quả.

---

## Phụ lục — Thứ tự thực thi

```
FT-00  hợp đồng API          ─┐
FT-01  ngân sách token ⚠️GATE ─┼─ làm được ngay, $0, không GPU
FT-02  bộ phát lại           ─┘
          │
FT-03  GATE mô hình gốc ⚠️  ── chốt mô hình + biết trước sẽ viết gì
          │
FT-04  chuẩn bị dữ liệu     ── $0
          │
FT-05  huấn luyện QLoRA     ── Kaggle T4
          │
FT-06  chạy sáu ô           ── Kaggle T4
          │
FT-07  viết 4.7 + sửa 5.4
```

FT-00 → FT-02 làm song song được. FT-04 làm song song với FT-03 được, nhưng
**không huấn luyện trước khi FT-03 xong**.
