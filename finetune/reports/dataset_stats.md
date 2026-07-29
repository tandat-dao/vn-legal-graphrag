# TASK-FT-04 — Bộ dữ liệu huấn luyện

**Sinh bởi:** `python -m finetune.build_dataset` · seed `42` · tất định (cùng seed → cùng bộ)

**Nguồn:** `thangvip/vietnamese-legal-qa` — 9 715 dòng / 29 145 cặp QA, 141 `doc_name`, `doc_type_name` một giá trị "Luật".

---

## 0. Một dòng

> **5 000 mẫu** — 2529 khuôn GraphRAG / 2471 khuôn baseline (50.6% / 49.4%); **450 mẫu từ chối (9.0%)**; train 4690 / val 310 tách theo `doc_name`.
> 100% khối trích dẫn round-trip đúng qua `parse_citations`.

---

## 1. Số bị drop, theo từng lý do

Đếm trên **dòng** với các lý do ở cấp văn bản/điều, trên **cặp QA** với các lý do ở cấp câu hỏi.

| Lý do | Số bị drop | Giải thích |
|---|---:|---|
| `doc_ngoai_pham_vi` | 5 408 | văn bản thuộc lĩnh vực system prompt liệt kê là NGOÀI PHẠM VI → chuyển hết sang pool mẫu từ chối, không dùng làm mẫu trả lời được |
| `khong_suy_duoc_slug` | 2 331 | không suy được slug theo convention — toàn bộ là bản "Dự thảo Luật …" (không số hiệu, không năm) |
| `leak_question_ngram` | 2 247 | câu hỏi trùng 5-gram hoặc Jaccard ≥ 0.6 với 137 câu `test_set_v2.json` |
| `qa_khong_suy_duoc_dieu` | 1 733 | đáp án nhắc Điều khác Điều nguồn → không chắc trích dẫn thuộc về đâu |
| `article_qua_ngan` | 210 | `article_content` < 200 ký tự, hoặc không phân rã được Điều/Khoản |
| `leak_doc_corpus` | 133 | `doc_name` khớp một trong 32 văn bản của corpus (so tên đã bỏ dấu + so số hiệu) |
| `article_qua_dai` | 53 | `article_content` > 50 000 ký tự |
| `doc_thieu_dieu_de_dong_goi` | 19 | văn bản có < 4 điều dùng được → không đóng gói được 4-6 điều |
| `qa_co_ngoac_vuong` | 9 | prose chứa `[` hoặc `]` → `parse_citations` bắt nhầm thành khối, phá round-trip |

Còn lại: **90 văn bản**, **16 962 cặp QA** dùng được (11 554 trong phạm vi corpus / 5 408 ngoài phạm vi).

### 1.1 Lọc rò rỉ — danh sách chặn

Đọc frontmatter `id` + `title` của `data/raw/*.md` → **32 văn bản**. Hai khoá so khớp độc lập:

1. **số hiệu pháp lý** trong `title` (`31/2024/QH15`, `102/2024/NĐ-CP`…)
2. **tên văn bản đã bỏ số/năm**, chuẩn hoá bỏ dấu + lowercase (`luat dat dai`, `luat ho tich`, `luat nuoi con nuoi`)

Bộ nguồn CÓ chứa văn bản của corpus — lọc này không phải thủ tục cho có:

| `doc_name` trong bộ nguồn | Khớp với |
|---|---|
| Luật Hộ tịch của Quốc hội, số 60/2014/QH13 | `luat-ho-tich-2014` |
| Luật Nuôi con nuôi của Quốc hội, số 52/2010/QH12 | `luat-nuoi-con-nuoi-2010` |
| Luật sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15… | `luat-dat-dai-2024` (số hiệu) |

Lớp n-gram **cố ý bảo thủ**: 5-gram bắt cả cụm rập khuôn của văn phong pháp lý ("cơ quan nào có thẩm quyền", "mức thu phí thẩm định hồ sơ") nên drop cả những câu hỏi thực ra độc lập. Chấp nhận đánh đổi đó — pool còn dư nhiều lần so với nhu cầu, mất dữ liệu rẻ hơn hẳn so với rò rỉ.

---

## 2. Phân phối độ dài — đối chiếu `token_budget.md`

Đếm bằng tokenizer `Qwen/Qwen2.5-7B-Instruct` — **cùng tokenizer** mà `token_budget.md` §2.7.2 dùng để chốt mốc. System prompt đo lại ở đây: **3 936 token** (khớp 3 936 của token_budget.md §2.2).

### 2.1 Phần `context`

| Khuôn | n | mean | p50 | p95 | max |
|---|---:|---:|---:|---:|---:|
| GraphRAG — sinh ra | 2529 | 4 745 | 4 495 | 7 225 | 8 774 |
| Baseline — sinh ra | 2471 | 1 768 | 1 781 | 2 301 | 2 829 |
| GraphRAG — **mục tiêu** (§2.7.2) | 127 | – | ~4 200 | ~7 600 | ~8 000 |
| Baseline — **mục tiêu** (§2.7.2) | 137 | – | ~1 800 | – | ~2 450 |

### 2.2 Đáp án và tổng chuỗi huấn luyện

| Đại lượng | n | mean | p50 | p95 | max |
|---|---:|---:|---:|---:|---:|
| đáp án (phần sinh ra) | 5000 | 213 | 176 | 512 | 1 019 |
| tổng = system + user + đáp án | 5000 | 7 498 | 6 818 | 11 001 | 12 950 |

`max_seq_length = 16 384` (chốt ở FT-01 §2.7.1): **0 mẫu vượt trần** (0.00%).

---

## 3. Tỉ lệ hai khuôn header

| Khuôn | n | tỉ lệ |
|---|---:|---:|
| `graphrag` | 2 529 | 50.6% |
| `baseline` | 2 471 | 49.4% |

Khuôn nguyên văn (api_contract.md §6):

```
GraphRAG:  --- [Tier N | Hiệu lực: YYYY-MM-DD] Điều …, Khoản …. (slug) ---
Baseline:  --- Văn bản: slug, chunk i ---
```

Chỉ dạy khuôn GraphRAG thì mô hình đã tinh chỉnh sẽ đọc cột Naive RAG kém hơn **vì lý do định dạng**, làm Δ ở hàng đó phồng lên giả tạo (kế hoạch §9.2(4)).

Hai biến thể của khuôn GraphRAG cũng được tái tạo, **chỉ trên block distractor** nên không bao giờ mâu thuẫn đáp án gold:

- `Hiệu lực: D → D (HẾT HIỆU LỰC)` — 5% ngữ cảnh (thực tế 45/2 199 header)
- khối `[AMENDMENT WARNING — …]` — 40% ngữ cảnh (thực tế 104/137 item)

---

## 4. Mẫu từ chối

| Loại | n | tỉ lệ | Chuỗi đáp án |
|---|---:|---:|---|
| `refusal_no_basis` | 315 | 6.3% | nguyên văn quy tắc bắt buộc `context_assembler.py:379` |
| `refusal_out_of_scope` | 135 | 2.7% | nguyên văn `answer` của V105 / V114 / V117 (= `context_assembler.py:373`) |
| **cộng** | **450** | **9.0%** | |

### 4.1 Vì sao HAI chuỗi chứ không phải một

Ba câu bẫy phủ định thật sự đi qua mô hình sinh — V105, V114, V117 — có `answer` **byte-identical** với nhau (api_contract.md §3 ví dụ G), nên chỉ cho **một** chuỗi, và đó là chuỗi *rào phạm vi corpus*. Nhưng cách dựng ở kế hoạch mục D (bỏ điều gold, giữ tài liệu liên quan) lại là ca *thiếu căn cứ*, mà system prompt bắt trả lời bằng chuỗi **khác** (`context_assembler.py:379`). Dán chuỗi "ngoài phạm vi" vào ca đó là dạy sai ánh xạ, nên bộ này dùng đúng chuỗi cho đúng điều kiện.

> ⚠️ **Sửa lỗi id trong đề bài FT-04.** Bản giao việc ghi *"lấy nguyên văn từ V005, V114, V117 — ba câu đã từ chối đúng; bỏ V105 (ca trả lời quá đà)"*. Dữ liệu thật ngược lại: **V005** mới là ca trả lời quá đà (IRAC 4 heading, ~2 400 ký tự, **4 citation** trong khi `ground_truth_citations` rỗng → `negative_correct=False`), còn **V105** byte-identical với V114/V117. Mô tả khớp chính xác, chỉ hai id bị hoán. Bộ này dùng V105/V114/V117 và bỏ V005.

| Loại | Cách dựng | Điều kiện học được |
|---|---|---|
| `refusal_no_basis` | đúng kế hoạch mục D: đóng gói 4-6 điều **cùng văn bản** nhưng **loại điều gold ra** | "ngữ cảnh có tài liệu liên quan nhưng không chứa căn cứ" — tín hiệu quan sát được |
| `refusal_out_of_scope` | câu hỏi lấy từ văn bản thuộc lĩnh vực NGOÀI phạm vi; ngữ cảnh đóng gói từ một văn bản **KHÁC** | tái tạo đúng cấu hình V114/V117: hỏi lệ phí trước bạ / thuế TNCN trong khi truy hồi trả về đất đai |

Ngữ cảnh RỖNG thì quá dễ, không dạy được gì — cả hai loại đều có ngữ cảnh đầy đủ. Có `assert` chặn: với `refusal_no_basis`, điều gold phải **thật sự vắng mặt** trong ngữ cảnh.

Văn bản thuộc lĩnh vực ngoài phạm vi bị **loại hẳn khỏi pool trả lời được** (5 408 cặp QA, xem §1). Nếu không, cùng một bề mặt đầu vào sẽ mang hai nhãn trái nhau — lúc thì trả lời có trích dẫn, lúc thì từ chối — và giám sát mâu thuẫn kiểu đó không học được gì.

**Không** dùng hằng số `src/pipeline.py:233` ("Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này.") — đó là nhánh truy hồi rỗng, mô hình sinh **chưa từng được gọi** (api_contract.md §7.1), khác ca hoàn toàn.

### 4.2 Vì sao hạ từ 20% xuống 9%

Mẻ trước đặt `FRAC_REFUSAL = 0.20` → 1 000 mẫu từ chối. Mẻ này **450 mẫu (9.0%)**, giữ nguyên tỉ lệ 70/30 giữa hai loại (315 `no_basis` / 135 `out_of_scope`).

**Lý do — đếm lại xem 20% đó bảo vệ được bao nhiêu câu:**

Chỉ **4/127** câu eval thật sự đi qua mô hình sinh ở nhánh phủ định. 10/14 câu bẫy do nhánh truy hồi RỖNG quyết định (`if not norm_ids`, `pipeline.py:223` return trước `generate_answer`) — mô hình chưa từng được gọi, và `replay.py` sao chép hằng số cho đúng 10 câu đó ở mọi hàng của ma trận. Trong khi **F1 cấp Khoản đo trên 123 câu**. Dành 20% ngân sách huấn luyện cho hành vi từ chối là đem 123 câu ra đánh cược để bảo vệ 4 câu.

**Vì sao vẫn nghiêng 70/30 về `no_basis`:** V005 — ca `no_basis` DUY NHẤT trong eval — là ca mà **cả Gemini cũng trả lời quá đà** (4 citation trong khi `ground_truth_citations` rỗng → `negative_correct=False`, xem §4.1). Đó là hành vi khó, cần nhiều mẫu. Ba ca `out_of_scope` ngược lại: được chi phối bởi **danh sách chặn tường minh** ở `src/retrieval/context_assembler.py:368-373` — system prompt liệt kê thẳng chủ đề ngoài phạm vi và đọc sẵn nguyên văn câu phải trả lời — nên cần ít mẫu hơn để học.

Đánh đổi phải ghi vào giới hạn: 9% là **giả định**, không phải số đo. Nếu hàng "cục bộ đã tinh chỉnh" cho `tu_choi_dung` tụt so với hàng chưa tinh chỉnh thì đây là biến đầu tiên phải xem lại.

---

## 5. Khối trích dẫn

| Hình dạng | n |
|---|---:|
| `[Điều \| Khoản \| Văn bản]` | 4 682 |
| `[Điều \| Văn bản]` | 775 |
| `[Điều \| Khoản \| Điểm \| Văn bản]` | 267 |

Số citation mỗi mẫu trả lời được: mean 1.26, max 2. Số block mỗi ngữ cảnh: mean 17.5, p50 13, max 67.

Ràng buộc đã áp (api_contract.md §3.2, có bằng chứng trên 401/401 khối thật):

- phân cách `, `; `Văn bản` **luôn cuối**; giá trị là **slug**, không phải số hiệu
- **không** dạy `Tiết` (0/401 khối thật dùng)
- **không** dùng `Mục` / `Dòng` / `Phần` (parser bỏ qua im lặng, ca thật V119/V131)
- chỉ 6 từ khoá parser hiểu: `Điều`, `Phụ lục`, `Khoản`, `Điểm`, `Tiết`, `Văn bản`

---

## 6. Kiểm tra bắt buộc (DoD)

| # | Kiểm tra | Kết quả |
|---|---|---|
| 1 | `finetune/slug.py` ≥ 10 unit test | ✅ 22 ca, `tests/test_finetune_slug.py` |
| 2 | 0 mẫu còn khớp danh sách chặn | ✅ assert trên toàn bộ mẫu |
| 3 | 100% khối trích dẫn parse được **và** round-trip đúng (Điều, Khoản, Điểm, slug) | ✅ 5 000 / 5 000 |
| 3b | slug của mọi citation có mặt trong `context` của chính mẫu đó | ✅ assert — chống dạy mô hình bịa slug từ trí nhớ |
| 4 | phân phối độ dài đối chiếu `token_budget.md` | ✅ §2 |
| 5 | 20 mẫu đầy đủ để kiểm tay | ✅ `samples_20.txt` |

---

## 7. Giới hạn — phải ghi vào mục 4.7

1. **Chỉ văn bản cấp luật.** `doc_type_name` một giá trị "Luật" → không có nghị định, thông tư, văn bản địa phương. Dạy được **định dạng trích dẫn và từ vựng pháp lý cấp luật**, không dạy suy luận đa tầng hay ràng buộc địa phương. Có lợi cho lập luận: tách bạch đóng góp của tinh chỉnh khỏi đóng góp của kiến trúc.
2. **Đáp án do mô hình ngôn ngữ sinh tự động**, không phải người viết. Phần prose giữ nguyên của bộ nguồn; chỉ câu mở đầu bị đa dạng hoá cơ khí và khối trích dẫn được nối thêm.
3. **Slug là slug tổng hợp**, không có trong corpus 32 văn bản. Chủ ý: mẫu dạy *chép slug từ header ngữ cảnh*, không dạy *nhớ slug*. Điều kiện bắt buộc (đã assert) là slug phải xuất hiện trong ngữ cảnh của chính mẫu đó.
4. **Ngày hiệu lực trong header là tổng hợp** (`{năm ban hành}-01-01`), cũng như nội dung khối `[AMENDMENT WARNING]`. Chúng chỉ tái tạo **bề mặt chuỗi** của ngữ cảnh thật, không mang thông tin pháp lý đúng.
5. **Chỉ dùng mode `general`.** 13/127 câu eval là `irac` — quá nhỏ để đáng công dựng đáp án theo cấu trúc 4 heading (kế hoạch §TASK-FT-04, ghi chú mode).
6. **Phân phối độ dài ngữ cảnh chỉ khớp xấp xỉ.** Trung vị `article_content` của bộ nguồn chỉ 853 ký tự, nên phải ưu tiên chọn điều dài để lấp ngân sách trong trần 6 điều — xem §2.1 để biết lệch bao nhiêu.
7. **Mẫu `refusal_out_of_scope` khớp CẤU HÌNH chứ không khớp LĨNH VỰC.** Ở mẻ thật, V114/V117 hỏi lệ phí trước bạ / thuế TNCN trong khi ngữ cảnh là văn bản đất đai. Ở đây câu hỏi cũng thuộc lĩnh vực ngoài phạm vi và ngữ cảnh cũng là văn bản khác, nhưng ngữ cảnh là luật chuyên ngành bất kỳ chứ không phải đất đai / hộ tịch / nuôi con nuôi — bộ nguồn không có ba lĩnh vực đó sau khi lọc rò rỉ. Mô hình học được "câu hỏi ngoài ba lĩnh vực → từ chối", chưa được luyện trên đúng nền ngữ cảnh của lúc đánh giá.

---

## 8. Định dạng file đầu ra

| File | Nội dung |
|---|---|
| `finetune/data/train.jsonl` | mẫu huấn luyện — một khoá `messages` |
| `finetune/data/val.jsonl` | tách theo `doc_name`: văn bản ở val KHÔNG có ở train |
| `finetune/data/{train,val}_meta.jsonl` | metadata song song theo dòng (`kind`, `header_format`, `citations`, …) — **để ngoài** file huấn luyện, vì `load_rows` báo lỗi khi gặp khoá lạ |

Mỗi dòng:

```json
{"messages": [{"role": "system", "content": "<system prompt thật, 3 936 token>"}, {"role": "user", "content": "CONTEXT:\n…\n\nCÂU HỎI: …\n\nTRẢ LỜI:"}, {"role": "assistant", "content": "…"}]}
```

**Prompt dựng bằng chính `src…build_messages(question, packed_context, "general")`** — cùng hàm `finetune/replay.py` dùng lúc đánh giá. Train và eval đồng nhất **theo xây dựng**, không phải theo cẩn thận (kế hoạch §9.4(2)).

### 8.1 Vì sao đúng khoá `messages`

Đọc `finetune/train_qlora.py` — `load_rows` (dòng 69-91) nhận **đúng hai dạng**: `{"messages": [...]}`, hoặc ba trường rời `system` / `user` / `assistant`. Khoá khác thì `raise ValueError`. Nên bộ này ghi `messages`, một danh sách phẳng ba lượt.

Không cần tự tách `prompt` / `completion`: `train_qlora.py` **tự render** chat template thành cột `text` (TRL ≥ 0.24 không còn tự nhận diện dataset dạng messages) rồi gọi `train_on_responses_only` để che phần prompt khỏi hàm mất mát. Metadata phải nằm ở file riêng vì mọi khoá lạ đều làm `load_rows` gãy.

`audit_lengths` của script đó **dừng hẳn** nếu có mẫu vượt `--max-seq-length` (mặc định 16 384) — bộ này max **12 950 token**, còn dư biên. Số đo ở đây dùng tokenizer Qwen2.5; Qwen3 cùng họ BPE 151k nên lệch không đáng kể, nhưng con số chốt vẫn là cái script tự đo lúc chạy.
