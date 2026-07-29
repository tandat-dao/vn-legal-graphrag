# TASK-FT-00 — Hợp đồng API

**Ngày lập:** 2026-07-28
**Phạm vi:** CHỈ ĐỌC. Không sửa `src/`, không chạy Neo4j/Qdrant, không gọi API.
**Nguồn duy nhất:** code thật trong `src/` + hai file kết quả đã lưu.

Mọi khẳng định trong tài liệu này đều kèm `đường-dẫn:số-dòng`. Các số liệu đo được
sinh ra bằng cách đọc trực tiếp file JSON (đọc, không ghi). **Không** tham chiếu
`FINETUNING_PLAN_v2.md` hay `FINETUNING_BASELINE_PLAN.md` — cả hai đã lỗi thời.

**File dữ liệu đối chiếu:**

| File | n item | Ghi chú |
|---|---:|---|
| `data/evaluation/results_graphrag_20260710-085236.json` | 137 | `system="graphrag"`, `test_set="data/evaluation/test_set_v2.json"`, `total_elapsed_s=3012.8` |
| `data/evaluation/results_baseline_20260710-085236.json` | 137 | `system="baseline"`, cùng timestamp |

---

## 0. Kết luận kiểm chứng quan trọng nhất

Chạy `parse_citations(item["answer"])` bằng hàm THẬT trên toàn bộ 137 item của **cả hai**
file, so với `item["pred_citations"]` đã lưu:

```
results_graphrag_20260710-085236.json | n=137 | roundtrip mismatches: 0
results_baseline_20260710-085236.json | n=137 | roundtrip mismatches: 0
```

→ `pred_citations` trong file kết quả **chính xác** là output của `parse_citations` hiện tại
áp lên `answer` hiện tại. Parser chưa đổi kể từ mẻ chạy 10/07. Do đó mọi ví dụ nguyên văn ở §3
là hợp đồng đích đáng tin cậy để dựng mẫu huấn luyện.

---

## 1. `build_messages` — chữ ký + hành vi

**Vị trí:** [src/retrieval/context_assembler.py:288-415](../../src/retrieval/context_assembler.py#L288-L415)

```python
def build_messages(question: str, context: str, mode: str = "general") -> tuple[str, str]:
```

Trả về `(system_prompt, user_prompt)`. Không gọi mạng, không đụng Neo4j — hàm thuần chuỗi.

### 1.1 Tham số `mode`

- Danh sách hợp lệ: `VALID_RESPONSE_MODES = ("general", "irac")` — [context_assembler.py:255](../../src/retrieval/context_assembler.py#L255)
- Bảng tra: `_MODE_BLOCKS` — [context_assembler.py:282-285](../../src/retrieval/context_assembler.py#L282-L285)
- **Fallback im lặng:** [context_assembler.py:305](../../src/retrieval/context_assembler.py#L305) dùng
  `_MODE_BLOCKS.get(mode, _MODE_BLOCK_GENERAL)` → giá trị lạ (kể cả `None`, typo) **không raise**,
  âm thầm về `general`. Đã kiểm: `build_messages("q","c","KHONG-TON-TAI")` cho system y hệt `general`.
- Khối `general`: [context_assembler.py:257-262](../../src/retrieval/context_assembler.py#L257-L262)
- Khối `irac`: [context_assembler.py:264-280](../../src/retrieval/context_assembler.py#L264-L280) — ép 4 heading H3
  `### Vấn đề` / `### Căn cứ pháp lý` / `### Phân tích` / `### Kết luận`.

### 1.2 Cấu trúc `user_prompt` (CỐ ĐỊNH, đo được)

[context_assembler.py:408-413](../../src/retrieval/context_assembler.py#L408-L413):

```
CONTEXT:
{context}

CÂU HỎI: {question}

TRẢ LỜI:
```

Đo thực tế với `question="Câu hỏi thử"`, `context="CTX"` → `len(user_prompt) = 44` ký tự.
Suy ra phần khung cố định của user prompt = `44 - len(question) - len(context)` = **30 ký tự**
(`"CONTEXT:\n"` + `"\n\nCÂU HỎI: "` + `"\n\nTRẢ LỜI:"`).

### 1.3 Kích thước `system_prompt` (số đo thật, không ước lượng)

| mode | len(system_prompt) |
|---|---:|
| `general` (mặc định) | **11 264** ký tự |
| `irac` | **11 532** ký tự |

Đo bằng cách gọi hàm thật với `INCLUDE_SCHEMA_B` ở giá trị mặc định.

### 1.4 Biến môi trường ảnh hưởng hình dạng prompt

`INCLUDE_SCHEMA_B` — [context_assembler.py:23](../../src/retrieval/context_assembler.py#L23):

```python
INCLUDE_SCHEMA_B = os.getenv("INCLUDE_SCHEMA_B", "false").lower() == "true"
```

Mặc định **false**. Khi `true`, [context_assembler.py:306-320](../../src/retrieval/context_assembler.py#L306-L320)
chèn thêm khối yêu cầu 3 section H2 `## TRẢ LỜI` / `## CẢNH BÁO LEX` / `## PHẠM VI`.
Đọc lúc **import module**, không đọc lại mỗi lần gọi → đổi env sau khi import không có tác dụng.

Kiểm chứng trên dữ liệu: không có answer nào trong 137 item chứa heading `## TRẢ LỜI` → mẻ chạy
10/07 chạy với `INCLUDE_SCHEMA_B=false`. **Replay phải giữ false** để prompt trùng khít.

### 1.5 Hàm phụ

`build_prompt(question, context, mode)` — [context_assembler.py:418-425](../../src/retrieval/context_assembler.py#L418-L425):
wrapper nối `system + "\n\n" + user`. Dùng cho code path cũ không tách system/user.
Với llama.cpp (không có khái niệm system riêng của Anthropic) đây có thể là hàm tiện hơn,
nhưng **quyết định dùng hàm nào thuộc TASK-FT-02**, không chốt ở đây.

---

## 2. `parse_citations` — cú pháp parser chấp nhận

**Vị trí:** [src/retrieval/answer_generator.py:130-196](../../src/retrieval/answer_generator.py#L130-L196)

```python
def parse_citations(raw_answer: str) -> list[dict]:
```

### 2.1 Thuật toán (đọc từ code, không mô tả lại từ docstring)

1. **Bắt khối:** `_CITATION_BLOCK_RE = re.compile(r"\[([^\[\]]+)\]")` — [answer_generator.py:122](../../src/retrieval/answer_generator.py#L122).
   Bắt **mọi** cặp ngoặc vuông không lồng nhau. Không phân biệt markdown link, chú thích, v.v.
2. **Tách theo dấu phẩy:** [answer_generator.py:157](../../src/retrieval/answer_generator.py#L157) — `content.split(",")`.
3. **Phân loại từng phần** bằng `_CITATION_PART_RE` — [answer_generator.py:124-127](../../src/retrieval/answer_generator.py#L124-L127):

```python
_CITATION_PART_RE = re.compile(
    r"^(Điều|Phụ\s*lục|Khoản|Điểm|Tiết|Văn\s*bản)\s*(.*)$",
    re.IGNORECASE,
)
```

   - `re.IGNORECASE` → `điều`, `ĐIỀU`, `Văn Bản` đều khớp.
   - Dấu tiếng Việt **bắt buộc đúng**: `Dieu`, `Khoan`, `Van ban` KHÔNG khớp (regex có dấu).
   - Chuẩn hoá loại: [answer_generator.py:161](../../src/retrieval/answer_generator.py#L161)
     `pm.group(1).lower().replace(" ", "")` → `"Phụ lục"→"phụlục"`, `"Văn bản"→"vănbản"`.
   - Phần **không khớp prefix nào bị bỏ qua im lặng** (`continue`, [answer_generator.py:160](../../src/retrieval/answer_generator.py#L160)).
     Đây là nguồn mất thông tin thật — xem ví dụ E (§3).
4. **Thứ tự tự do:** vì phân loại theo prefix chứ không theo vị trí, mọi hoán vị đều hợp lệ.
5. **Điều kiện hợp lệ** — [answer_generator.py:179-182](../../src/retrieval/answer_generator.py#L179-L182):
   - phải có `Văn bản` (`van_ban is not None`), **và**
   - phải có `Điều` hoặc `Phụ lục` (`loai is not None`), **và**
   - nếu `loai == "dieu"` thì bắt buộc có số (`number` không rỗng).
   - Không thoả → khối bị bỏ, **không** raise.
6. **Dedupe** — [answer_generator.py:150, 184-187](../../src/retrieval/answer_generator.py#L184-L187):
   khoá `(loai, number, khoan, diem, tiet, van_ban)`; trùng thì chỉ giữ lần xuất hiện đầu.

### 2.2 Schema dict trả về

[answer_generator.py:188-195](../../src/retrieval/answer_generator.py#L188-L195) — **luôn đủ 6 key**, thiếu thì `None`:

```python
{"dieu": ..., "khoan": ..., "diem": ..., "tiet": ..., "van_ban": ..., "loai": ...}
```

- `loai ∈ {"dieu", "phu_luc"}`.
- Với `Phụ lục` không có ký hiệu: `number = "_default"` — [answer_generator.py:168](../../src/retrieval/answer_generator.py#L168).
  Ký hiệu Phụ lục được nhét vào field `dieu` (backward compat).
- Giá trị **không** được chuẩn hoá ở đây (giữ nguyên chữ hoa/thường, khoảng trắng);
  chuẩn hoá xảy ra ở tầng metric (`_norm_str`, §4.1).

---

## 3. Bề mặt chuỗi trích dẫn Gemini THỰC SỰ sinh — ví dụ nguyên văn

> Đây là mục quan trọng nhất của TASK-FT-00.
> Tất cả trích dẫn dưới đây **chép nguyên văn** từ field `answer` của
> `data/evaluation/results_graphrag_20260710-085236.json`. Không diễn giải, không tự bịa.

### 3.1 Thống kê toàn bộ 137 answer (đo, không đoán)

Tổng số khối `[...]` bắt được: **401**. Số khối chứa `Văn bản`: **401**.
Số khối **không** chứa `Văn bản`: **0** → trong mẻ này Gemini không dùng ngoặc vuông cho mục
đích nào khác ngoài trích dẫn.

Phân bố hình dạng (thứ tự prefix xuất hiện thực tế):

| n | Hình dạng |
|---:|---|
| 253 | `Điều \| Khoản \| Văn bản` |
| 99 | `Điều \| Khoản \| Điểm \| Văn bản` |
| 22 | `Phụ lục \| Văn bản` |
| 14 | `Điều \| Văn bản` |
| 5 | `Phụ lục \| Khoản \| Điểm \| Văn bản` |
| 2 | `Phụ lục \| ?? \| ?? \| Văn bản` |
| 2 | `Phụ lục \| Điểm \| ?? \| Văn bản` |
| 2 | `Phụ lục \| ?? \| ?? \| Khoản \| Văn bản` |
| 1 | `Phụ lục \| Khoản \| Văn bản` |
| 1 | `Phụ lục \| Điểm \| Văn bản` |

(`??` = thành phần parser không nhận, xem ví dụ E.)

**Nhận định rút ra:** Gemini luôn viết theo **thứ tự chuẩn giảm dần**
`Điều → Khoản → Điểm → Văn bản`, đặt `Văn bản` **cuối cùng**, dù parser cho phép đảo.
Không có khối nào dùng `Tiết` trong toàn bộ 137 answer; cũng không có `pred_citations`
nào có `tiet` khác `None`. → Mẫu huấn luyện **không cần** dạy `Tiết`.

### Ví dụ A — dạng phổ biến nhất, hai citation, có `Điểm` (V001)

*Câu hỏi:* `Gia đình tôi sống tại một xã thuộc huyện Củ Chi, TP.HCM. Hạn mức giao đất ở cho cá nhân ở khu vực này là bao nhiêu?`

Nguyên văn `answer`:

```
Theo quy định sẽ có hiệu lực từ ngày 30 tháng 9 năm 2024, hạn mức giao đất ở cho cá nhân tại các xã thuộc huyện Củ Chi, TP.HCM là không quá 250 m2 [Điều 3, Khoản 3, Văn bản quyet-dinh-69-2024-qd-ubnd-tp-hcm].

Lưu ý: Quy định trên tại Quyết định số 69/2024/QĐ-UBND sẽ thay thế cho quy định cũ tại Quyết định số 18/2016/QĐ-UBND. Theo quy định cũ, hạn mức áp dụng cho khu dân cư nông thôn tại các xã của huyện Củ Chi là không quá 300m2/hộ [Điều 1, Khoản 1, Điểm d, Văn bản quyet-dinh-18-2016-qd-ubnd-tp-hcm].
```

`pred_citations` tương ứng:

```json
[{"dieu": "3", "khoan": "3", "diem": null, "tiet": null, "van_ban": "quyet-dinh-69-2024-qd-ubnd-tp-hcm", "loai": "dieu"},
 {"dieu": "1", "khoan": "1", "diem": "d", "tiet": null, "van_ban": "quyet-dinh-18-2016-qd-ubnd-tp-hcm", "loai": "dieu"}]
```

Chú ý: số hiệu pháp lý `69/2024/QĐ-UBND` chỉ nằm trong **văn xuôi**; trong ngoặc vuông luôn là slug.

### Ví dụ B — một citation `Điều/Khoản/Điểm`, câu trả lời ngắn nhất có trích dẫn (V133, 154 ký tự)

*Câu hỏi:* `Nhà tui ở xã Phú Lý trên Đồng Nai, nghe nói nhà nước chỉ cho mỗi người chừng đó đất thổ cư thôi — vậy tối đa tui được giao bao nhiêu mét vuông đất ở?`

```
Tại xã Phú Lý, tỉnh Đồng Nai, hạn mức giao đất ở được quy định là không quá 300 m2 [Điều 3, Khoản 2, Điểm a, Văn bản quyet-dinh-92-2025-qd-ubnd-dong-nai].
```

```json
[{"dieu": "3", "khoan": "2", "diem": "a", "tiet": null, "van_ban": "quyet-dinh-92-2025-qd-ubnd-dong-nai", "loai": "dieu"}]
```

### Ví dụ C — `Phụ lục` (V015)

*Câu hỏi:* `Hộ gia đình, cá nhân ở Đồng Nai nộp hồ sơ trực tiếp xin cấp Giấy chứng nhận quyền sử dụng đất lần đầu (chỉ đất) thì phí thẩm định hồ sơ là bao nhiêu?`

```
Phí thẩm định hồ sơ xin cấp Giấy chứng nhận quyền sử dụng đất lần đầu (chỉ đất) cho hộ gia đình, cá nhân ở Đồng Nai khi nộp hồ sơ trực tiếp là 880.000 đồng/hồ sơ [Phụ lục I, Văn bản nghi-quyet-22-2024-nq-hdnd-dong-nai].
```

```json
[{"dieu": "I", "khoan": null, "diem": null, "tiet": null, "van_ban": "nghi-quyet-22-2024-nq-hdnd-dong-nai", "loai": "phu_luc"}]
```

Ký hiệu Phụ lục (`I`) rơi vào field `dieu`, `loai="phu_luc"`.

### Ví dụ D — chế độ `irac`, 4 heading H3, cùng một citation lặp 3 lần → dedupe còn 1 (V147)

*Câu hỏi:* `Miếng đất nhà tui có lấn ra lề đường một khúc, giờ làm sổ cho phần đó được không?`

```
### Vấn đề
Xác định khả năng được cấp Giấy chứng nhận quyền sử dụng đất đối với phần diện tích đất lấn ra lề đường.

### Căn cứ pháp lý
Theo quy định của pháp luật, trường hợp sử dụng đất do lấn, chiếm lề đường sau khi Nhà nước đã công bố chỉ giới xây dựng thì Nhà nước sẽ thu hồi đất và không cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất đối với diện tích đất đã lấn, chiếm.

Tuy nhiên, pháp luật cũng có quy định ngoại lệ đối với trường hợp vi phạm xảy ra trước ngày 01 tháng 7 năm 2014. Cụ thể, nếu đã có điều chỉnh quy hoạch sử dụng đất, quy hoạch xây dựng được cơ quan có thẩm quyền phê duyệt mà nay diện tích đất lấn, chiếm không còn thuộc chỉ giới xây dựng đường giao thông thì người đang sử dụng đất được xem xét cấp Giấy chứng nhận và phải thực hiện nghĩa vụ tài chính theo quy định [Điều 139, Khoản 1, Văn bản luat-dat-dai-2024].

### Phân tích
Trường hợp của bạn là lấn đất ra lề đường. Theo quy định chung, đây là hành vi vi phạm và phần đất lấn chiếm sẽ bị Nhà nước thu hồi, không được cấp Giấy chứng nhận [Điều 139, Khoản 1, Văn bản luat-dat-dai-2024].

Để được xem xét cấp Giấy chứng nhận cho phần đất này, bạn cần đáp ứng đồng thời các điều kiện sau:
1.  Hành vi lấn, chiếm đất phải xảy ra **trước ngày 01 tháng 7 năm 2014**.
2.  Hiện tại, quy hoạch sử dụng đất hoặc quy hoạch xây dựng tại khu vực đã được điều chỉnh và được cơ quan có thẩm quyền phê duyệt, theo đó phần đất bạn đang sử dụng **không còn thuộc chỉ giới xây dựng đường giao thông** nữa.

Nếu đáp ứng cả hai điều kiện trên, bạn có thể được xem xét cấp Giấy chứng nhận và sẽ phải nộp các khoản nghĩa vụ tài chính theo quy định của pháp luật [Điều 139, Khoản 1, Văn bản luat-dat-dai-2024].

### Kết luận
Bạn không được cấp Giấy chứng nhận cho phần đất lấn ra lề đường nếu phần đất đó vẫn thuộc chỉ giới xây dựng đường giao thông theo quy hoạch hiện hành.

Bạn chỉ có thể được xem xét cấp Giấy chứng nhận nếu việc lấn chiếm xảy ra trước ngày 01/7/2014 và quy hoạch đã được điều chỉnh sao cho phần đất đó không còn thuộc chỉ giới xây dựng nữa. Khi đó, bạn sẽ phải thực hiện nghĩa vụ tài chính theo quy định [Điều 139, Khoản 1, Văn bản luat-dat-dai-2024].
```

```json
[{"dieu": "139", "khoan": "1", "diem": null, "tiet": null, "van_ban": "luat-dat-dai-2024", "loai": "dieu"}]
```

3 khối giống hệt → 1 citation (dedupe [answer_generator.py:184-187](../../src/retrieval/answer_generator.py#L184-L187)).
**Hệ quả cho FT-04:** lặp lại cùng citation ở nhiều mục IRAC không bị phạt precision.

### Ví dụ E — thành phần lạ bị parser nuốt im lặng (V119)

*Câu hỏi:* `Lệ phí cấp Giấy chứng nhận quyền sử dụng đất lần đầu cho cá nhân là bao nhiêu?`

```
Lệ phí cấp Giấy chứng nhận quyền sử dụng đất lần đầu cho cá nhân phụ thuộc vào quy định của từng địa phương.

Ví dụ, tại một số địa phương có quy định như sau:

**1. Tại tỉnh Đồng Nai (áp dụng từ ngày 09/12/2024):**
*   Đối với hộ gia đình, cá nhân có đất thuộc các phường của thành phố Long Khánh và Biên Hòa: 30.000 đồng/giấy [Phụ lục, Mục I, Dòng 2, Văn bản nghi-quyet-21-2024-nq-hdnd-dong-nai].
*   Đối với hộ gia đình, cá nhân có đất thuộc các xã, thị trấn của các huyện và các xã của thành phố Long Khánh và Biên Hòa: 15.000 đồng/giấy [Phụ lục, Mục I, Dòng 3, Văn bản nghi-quyet-21-2024-nq-hdnd-dong-nai].

**2. Tại Thành phố Hồ Chí Minh:**
*   Đối với cá nhân, hộ gia đình tại quận: 25.000 đồng/giấy [Phụ lục 1C, Điểm a, Dòng 1, Văn bản nghi-quyet-124-2016-nq-hdnd-tp-hcm-datdai].
*   Đối với cá nhân, hộ gia đình tại huyện: 0 đồng [Phụ lục 1C, Điểm a, Dòng 1, Văn bản nghi-quyet-124-2016-nq-hdnd-tp-hcm-datdai].
```

```json
[{"dieu": "_default", "khoan": null, "diem": null, "tiet": null, "van_ban": "nghi-quyet-21-2024-nq-hdnd-dong-nai", "loai": "phu_luc"},
 {"dieu": "1C", "khoan": null, "diem": "a", "tiet": null, "van_ban": "nghi-quyet-124-2016-nq-hdnd-tp-hcm-datdai", "loai": "phu_luc"}]
```

**4 khối → 2 citation.** `Mục I` và `Dòng 2` / `Dòng 3` không khớp `_CITATION_PART_RE` nên bị bỏ,
khiến hai khối Đồng Nai trở nên **giống hệt nhau** sau khi parse rồi bị dedupe. Tương tự cặp TP.HCM.

Toàn bộ các khối chứa thành phần lạ trong 137 answer (chỉ 6 khối, thuộc 2 câu):

```
V119 | [Phụ lục, Mục I, Dòng 2, Văn bản nghi-quyet-21-2024-nq-hdnd-dong-nai]
V119 | [Phụ lục, Mục I, Dòng 3, Văn bản nghi-quyet-21-2024-nq-hdnd-dong-nai]
V119 | [Phụ lục 1C, Điểm a, Dòng 1, Văn bản nghi-quyet-124-2016-nq-hdnd-tp-hcm-datdai]
V119 | [Phụ lục 1C, Điểm a, Dòng 1, Văn bản nghi-quyet-124-2016-nq-hdnd-tp-hcm-datdai]
V131 | [Phụ lục I, Phần III, Mục I, Khoản 6, Văn bản nghi-dinh-151-2025-nd-cp]
V131 | [Phụ lục I, Phần III, Mục I, Khoản 6, Văn bản nghi-dinh-151-2025-nd-cp]
```

**Kết luận cho FT-04:** mẫu huấn luyện **không nên** dạy `Mục`/`Dòng`/`Phần` — chúng vô hình
với bộ chấm. Dùng đúng 6 từ khoá parser hiểu.

### Ví dụ F — câu từ chối, 0 citation, ngữ cảnh RỖNG (V106)

*Câu hỏi:* `Thủ tục thành lập công ty TNHH một thành viên cần những giấy tờ gì?`

```
Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này.
```

`pred_citations`: `[]` · `context`: `""` · `top_k_count`: `0`

⚠️ **Chuỗi này KHÔNG do mô hình sinh.** Nó là hằng số cứng trong pipeline:
[src/pipeline.py:223](../../src/pipeline.py#L223) `if not norm_ids:` → return sớm với
[src/pipeline.py:233](../../src/pipeline.py#L233)
`answer="Không tìm thấy văn bản pháp luật liên quan đến câu hỏi này."` — **LLM không hề được gọi**.
Chi tiết ở §7 (điểm cần quyết định).

### Ví dụ G — câu từ chối do rào phạm vi corpus, CÓ ngữ cảnh (V105)

*Câu hỏi:* `Tôi muốn xin giấy phép xây dựng nhà ở trên mảnh đất của mình thì thủ tục như thế nào?`

```
Câu hỏi này không thuộc phạm vi tài liệu pháp luật mà hệ thống đang lập chỉ mục (đất đai, hộ tịch, nuôi con nuôi). Vui lòng tham khảo các văn bản pháp luật chuyên ngành tương ứng.
```

`pred_citations`: `[]` · `top_k_count`: `12` (ngữ cảnh KHÔNG rỗng)

Đây **là** output của mô hình, sao y nguyên văn câu bắt buộc trong system prompt
([context_assembler.py:373](../../src/retrieval/context_assembler.py#L373)).
V114 và V117 có answer **byte-identical** với V105 (cùng 179 ký tự).

### 3.2 Chuỗi trích dẫn đích — chốt lại

Dạng mà mô hình cục bộ cần học sinh ra, theo đúng thứ tự Gemini dùng:

```
[Điều {số}, Văn bản {slug}]
[Điều {số}, Khoản {số}, Văn bản {slug}]
[Điều {số}, Khoản {số}, Điểm {chữ}, Văn bản {slug}]
[Phụ lục {ký hiệu}, Văn bản {slug}]
[Phụ lục {ký hiệu}, Khoản {số}, Điểm {chữ}, Văn bản {slug}]
```

- Dấu phân cách: `, ` (phẩy + một khoảng trắng).
- `Văn bản` luôn ở **cuối**; giá trị là **slug** (`lowercase`, gạch ngang), không phải số hiệu.
- Không dùng `Tiết` (0/401 khối).
- Không dùng `Mục` / `Dòng` / `Phần` (parser bỏ qua).

> Ghi chú đối chiếu với plan: chuỗi `"Nguồn: [Điều X Khoản Y {norm_id}]"` mà các plan tháng 6
> ghi lại là **SAI** ở ba điểm — không có tiền tố `Nguồn:`, các thành phần **có dấu phẩy** ngăn cách,
> và slug **phải** có từ khoá `Văn bản` đứng trước. Dùng dạng cũ thì `parse_citations`
> trả về `[]` (thiếu `Văn bản` → loại ở [answer_generator.py:179](../../src/retrieval/answer_generator.py#L179)).

---

## 4. `cit_matches`, `aggregate` và các hàm chấm

**File:** [src/evaluation/metrics.py](../../src/evaluation/metrics.py)

### 4.1 Chuẩn hoá

`_norm_str` — [metrics.py:33-38](../../src/evaluation/metrics.py#L33-L38): `str(v).strip().lower()`,
chuỗi rỗng → `None`. Nghĩa là `"Luat-Dat-Dai-2024"` khớp `"luat-dat-dai-2024"`; **nhưng**
dấu tiếng Việt không bị bỏ → `"Điểm a"` vs `"a"` khác nhau.

### 4.2 `cit_matches` — single source of truth

[metrics.py:69-95](../../src/evaluation/metrics.py#L69-L95)

```python
def cit_matches(pred: dict, gt: dict, level: str = "khoan") -> bool:
```

- `van_ban` **và** `dieu` luôn phải khớp ([metrics.py:83-86](../../src/evaluation/metrics.py#L83-L86)).
- `level ∈ {"van_ban", "dieu", "khoan", "diem"}` (xem `_citation_key`, [metrics.py:41-62](../../src/evaluation/metrics.py#L41-L62); level lạ → `ValueError`).
- **Semantic wildcard:** `gt.khoan is None` → khớp mọi `pred.khoan` ([metrics.py:87-90](../../src/evaluation/metrics.py#L87-L90));
  tương tự `gt.diem` khi `level="diem"` ([metrics.py:91-94](../../src/evaluation/metrics.py#L91-L94)).
- **`loai` KHÔNG tham gia so khớp.** Phụ lục khớp qua `dieu` (ký hiệu Phụ lục hoặc `"_default"`).

### 4.3 `citation_score`, `norm_recall`, `negative_correct`

| Hàm | Dòng | Chữ ký |
|---|---|---|
| `citation_score` | [117-162](../../src/evaluation/metrics.py#L117-L162) | `(pred: list[dict], gt: list[dict], level: str = "khoan") -> CitationScore` |
| `norm_recall` | [165-175](../../src/evaluation/metrics.py#L165-L175) | `(pred: list[dict], gt: list[dict]) -> float` |
| `negative_correct` | [178-182](../../src/evaluation/metrics.py#L178-L182) | `(pred: list[dict], gt_type: str) -> bool` |

`CitationScore` TypedDict — [metrics.py:20-26](../../src/evaluation/metrics.py#L20-L26):
`{precision, recall, f1, pred_count, gt_count, match_count}`.

Ca biên của `citation_score` ([metrics.py:129-132](../../src/evaluation/metrics.py#L129-L132), 145-153):
- `gt` rỗng + `pred` rỗng → `p=r=f1=1.0`
- `gt` rỗng + `pred` khác rỗng → `p=0, r=1, f1=0`
- `gt` khác rỗng + `pred` rỗng → `p=1, r=0, f1=0`

`negative_correct` trả `False` (không phải `None`) khi `gt_type != "negative"` — [metrics.py:181](../../src/evaluation/metrics.py#L181).
Trong `run_evaluation` hàm chỉ được gọi khi `gap_type == "negative"`, ngược lại gán thẳng `None`
([run_evaluation.py:244-247](../../src/evaluation/run_evaluation.py#L244-L247)).

### 4.4 `aggregate` — yêu cầu tối thiểu (đã kiểm bằng thực nghiệm)

[metrics.py:189-258](../../src/evaluation/metrics.py#L189-L258) — `aggregate(per_question: list[dict]) -> dict`

Kiểm bằng cách dựng item tối giản và gọi hàm thật:

| Key | Bắt buộc? | Truy cập tại | Ghi chú |
|---|---|---|---|
| `citation_score.{precision,recall,f1}` | **CÓ** (`[...]`) | [209-211](../../src/evaluation/metrics.py#L209-L211) | thiếu → `KeyError` |
| `norm_recall` | **CÓ** | [217](../../src/evaluation/metrics.py#L217) | |
| `elapsed_seconds` | **CÓ** | [218-222](../../src/evaluation/metrics.py#L218-L222) | dùng cả cho p95 |
| `gap_type` | **CÓ** | [226, 233](../../src/evaluation/metrics.py#L226) | |
| `theme` | **CÓ** | [248](../../src/evaluation/metrics.py#L248) | |
| `negative_correct` | **CÓ nếu** `gap_type=="negative"` | [229](../../src/evaluation/metrics.py#L229) | đã kiểm: thiếu → `KeyError: 'negative_correct'` |
| `citation_score_dieu` | không | [213-215](../../src/evaluation/metrics.py#L213-L215) | dùng `.get()` → **thiếu thì `f1_dieu_mean = 0.0` một cách IM LẶNG** |
| `id`, `question`, `jurisdiction`, `difficulty` | không | — | `aggregate` không đọc |

⚠️ Bẫy: thiếu `citation_score_dieu` **không báo lỗi** mà cho cột "F1 cấp Điều" = 0.000 —
một trong bốn cột báo cáo của mục 4.7 sẽ sai mà không có dấu hiệu gì.

`aggregate([])` trả `{"count": 0}` ([metrics.py:200-201](../../src/evaluation/metrics.py#L200-L201)).

Output của `aggregate` (đo thật): `count`, `precision_mean`, `recall_mean`, `f1_mean`,
`precision_dieu_mean`, `recall_dieu_mean`, `f1_dieu_mean`, `norm_recall_mean`, `latency_mean_s`,
`latency_p95_s`, `negative_count`, `negative_correct_rate`, `by_gap`, `by_theme`.

Bốn cột của Bảng 4.5 ánh xạ: F1 Khoản = `f1_mean`; F1 Điều = `f1_dieu_mean`;
Norm Recall = `norm_recall_mean`; Từ chối đúng = `negative_correct_rate × negative_count`.

---

## 5. Schema item của results JSON

### 5.1 Vỏ file

Ghi tại [run_evaluation.py:526-540](../../src/evaluation/run_evaluation.py#L526-L540):

```json
{"system": "graphrag", "test_set": "data/evaluation/test_set_v2.json",
 "timestamp": "20260710-085236", "total_elapsed_s": 3012.8, "results": [ ... ]}
```

Tên file: `results_{system}{abl_tag}_{timestamp}.json`, `abl_tag=""` khi ablation `full`
([run_evaluation.py:525-526](../../src/evaluation/run_evaluation.py#L525-L526)).

### 5.2 Item — 20 key, dựng tại [run_evaluation.py:258-279](../../src/evaluation/run_evaluation.py#L258-L279)

Kiểm chứng: cả 137/137 item của **cả hai** file đều có đủ 20 key, không thừa không thiếu.

| Key | Kiểu | Nguồn |
|---|---|---|
| `id` | str | `item["id"]` |
| `question` | str | test set |
| `gap_type` | str | `gap1\|gap2\|gap3\|gap4\|negative` |
| `theme` | str | |
| `jurisdiction` | str | |
| `difficulty` | str | |
| `system` | str | `"graphrag"` / `"baseline"` |
| `answer` | str | output mô hình (hoặc hằng số, xem §7) |
| `pred_citations` | list[dict] | `parse_citations(answer)` |
| `ground_truth_citations` | list[dict] | test set |
| `citation_score` | dict | `citation_score(..., level="khoan")` — [241](../../src/evaluation/run_evaluation.py#L241) |
| `citation_score_dieu` | dict | `citation_score(..., level="dieu")` — [242](../../src/evaluation/run_evaluation.py#L242) |
| `norm_recall` | float | [243](../../src/evaluation/run_evaluation.py#L243) |
| `negative_correct` | bool \| null | null nếu không phải negative |
| `faithfulness` | dict \| null | [251-256](../../src/evaluation/run_evaluation.py#L251-L256) |
| `elapsed_seconds` | float | |
| `context_used` | bool | |
| `top_k_count` | int | |
| `context` | str | **chuỗi context y hệt cái đưa vào `generate_answer`** |
| `verifier` | dict \| null | null trong cả hai file |

Phân bố `gap_type` (giống hệt ở cả hai file): `gap1=32, gap2=31, gap3=30, gap4=30, negative=14`.

### 5.3 Ba cạm bẫy đã xác nhận

1. **`response_mode` KHÔNG được lưu.** `_run_one_graphrag` *có* trả nó về
   ([run_evaluation.py:84](../../src/evaluation/run_evaluation.py#L84)) nhưng dict `result`
   ([258-279](../../src/evaluation/run_evaluation.py#L258-L279)) không chép sang → mất.
   Xác nhận: `response_mode` không nằm trong 20 key. Đây đúng là vấn đề TASK-FT-01 §B mô tả.
   (Đo phụ: 13/137 answer có heading `### Vấn đề` — số liệu thô, việc khôi phục thuộc FT-01.)

2. **File chứa `NaN` — JSON không chuẩn.** Đếm được **118** lần chuỗi `NaN` trong file graphrag,
   tất cả ở `faithfulness.support_rate` (khi chạy Tier 1 không có judge). `json` của Python đọc
   được, nhưng parser strict (`json.loads(..., parse_constant=...)`, jq, nhiều thư viện JS) sẽ gãy.
   Khi FT-02 ghi file mới, `json.dump` mặc định cũng sinh `NaN` → nên tránh sinh giá trị `nan`.

3. **`context` là byte-identical với input mô hình.** GraphRAG:
   [pipeline.py:256](../../src/pipeline.py#L256) `context = assemble_context(...)` → truyền vào
   `generate_answer` ([pipeline.py:261-262](../../src/pipeline.py#L261-L262)) và trả ra
   ([pipeline.py:300](../../src/pipeline.py#L300)). Baseline: cùng biến `context` tại
   [naive_rag.py:325](../../src/baseline/naive_rag.py#L325) → [344](../../src/baseline/naive_rag.py#L344) → [359](../../src/baseline/naive_rag.py#L359).
   → Giả định nền của §4 kế hoạch ("phát lại, không chạy lại") **đứng vững**.

---

## 6. Khuôn header block ngữ cảnh

### 6.1 GraphRAG

Sinh tại [context_assembler.py:229-231](../../src/retrieval/context_assembler.py#L229-L231),
nhãn từ `_format_citation_label` ([98-138](../../src/retrieval/context_assembler.py#L98-L138)),
các block nối bằng `"\n\n"` ([context_assembler.py:245](../../src/retrieval/context_assembler.py#L245)).

Khuôn:

```
--- [Tier {N} | Hiệu lực: {YYYY-MM-DD}] {Điều ...}, {Khoản ...}. ({norm_slug}) ---
{text}
```

Biến thể hết hiệu lực ([context_assembler.py:132-135](../../src/retrieval/context_assembler.py#L132-L135)):

```
--- [Tier {N} | Hiệu lực: {YYYY-MM-DD} → {YYYY-MM-DD} (HẾT HIỆU LỰC)] ... ---
```

Đối chiếu với dữ liệu thật — **2 199 header** trong 137 context, khớp 100%, không có ngoại lệ:

| n | Khuôn |
|---:|---|
| 2 154 | `[Tier N \| Hiệu lực: D]` |
| 45 | `[Tier N \| Hiệu lực: D → D (HẾT HIỆU LỰC)]` |

Ví dụ nguyên văn (đầu `context` của V001):

```
--- [Tier 4 | Hiệu lực: 2024-09-30] Điều 3. Hạn mức giao đất ở cho cá nhân trên địa bàn Thành phố, Khoản 3. (quyet-dinh-69-2024-qd-ubnd-tp-hcm) ---
Điều 3. Hạn mức giao đất ở cho cá nhân trên địa bàn Thành phố
Khoản 3.
Các xã của các huyện Bình Chánh, Hóc Môn, Củ Chi, Nhà Bè, Cần Giờ: không quá 250 m2/cá nhân.
```

**Slug nằm trong ngoặc đơn ở CUỐI header** — đúng là chỗ system prompt bắt mô hình chép ra
([context_assembler.py:390](../../src/retrieval/context_assembler.py#L390)). Đây chính là cơ chế
"chép từ ngữ cảnh" mà TASK-FT-04 dựa vào.

### 6.2 Block cảnh báo sửa đổi

`_format_amendments_warning` — [context_assembler.py:145-167](../../src/retrieval/context_assembler.py#L145-L167).
Xen giữa header và text ([context_assembler.py:229](../../src/retrieval/context_assembler.py#L229)).
Có mặt ở **104/137** item. Nguyên văn (từ `context` của V001):

```
--- [Tier 2 | Hiệu lực: 2024-08-01] Điều 10. Quy định về nhận quyền sử dụng đất tại khu vực hạn chế tiếp cận đất đai, Khoản 1. (nghi-dinh-102-2024-nd-cp) ---
[AMENDMENT WARNING — nội dung Component này đã/sắp bị sửa đổi:]
  - 226/2025/NĐ-CP (điểm c khoản 4 Điều 7, hiệu lực 2025-08-15): bãi bỏ cụm từ ", thị trấn"
  - 226/2025/NĐ-CP (điểm a khoản 4 Điều 7, hiệu lực 2025-08-15): thay từ "đảo" bằng cụm từ "đặc khu"
  - 49/2026/NĐ-CP (tiết g1 điểm g khoản 3 Điều 16, hiệu lực 2026-01-31): bãi bỏ điểm a khoản 4 Điều 7 Nghị định số 226/2025/NĐ-CP
Điều 10. Quy định về nhận quyền sử dụng đất tại khu vực hạn chế tiếp cận đất đai
Khoản 1.
...
```

### 6.3 Baseline (khuôn KHÁC — quan trọng cho cột Naive RAG của ma trận)

[naive_rag.py:252-268](../../src/baseline/naive_rag.py#L252-L268), header tại
[naive_rag.py:267](../../src/baseline/naive_rag.py#L267):

```
--- Văn bản: {norm_id}, chunk {idx} ---
{text}
```

Nguyên văn (đầu `context` của V001, file baseline):

```
--- Văn bản: quyet-dinh-69-2024-qd-ubnd-tp-hcm, chunk 1 ---
ết giao đất ở cho cá nhân.

## Điều 3. Hạn mức giao đất ở cho cá nhân trên địa bàn Thành phố

### Khoản 1.
...
```

**Không có** Tier, ngày hiệu lực, hay đường dẫn Điều/Khoản trong header; text giữ nguyên
heading markdown của `data/raw/*.md` và bị cắt giữa từ (chunk cố định 512 ký tự).
Slug ở đây đứng **sau** `Văn bản: `, không phải trong ngoặc đơn. Mẫu huấn luyện dạy "chép slug
từ ngoặc đơn cuối header" (§6.1) sẽ **không** chuyển giao thẳng sang khuôn baseline — cần lưu ý
khi diễn giải hàng cục bộ × Naive RAG.

---

## 7. Điểm CHƯA XÁC ĐỊNH — cần quyết định trước khi làm FT-02

### 7.1 ⚠️ 10 câu "ngữ cảnh rỗng" chưa từng đi qua mô hình sinh

Kế hoạch §TASK-FT-02 viết: *"Giữ nguyên 14 câu bẫy phủ định, kể cả 10 câu có `context` rỗng
(V106–V113, V115, V116 — `top_k_count=0`, truy hồi cố ý trả rỗng để hệ từ chối trả lời)."*

Kiểm chứng trên code + dữ liệu:

- 10 item có `top_k_count == 0` đúng là `V106, V107, V108, V109, V110, V111, V112, V113, V115, V116`.
- **Cả 10** có `answer` giống hệt nhau, 59 ký tự, và **bằng đúng hằng số** ở
  [pipeline.py:233](../../src/pipeline.py#L233).
- Chuỗi đó **không xuất hiện** ở bất kỳ item nào khác trong 137.
- Nhánh [pipeline.py:223-237](../../src/pipeline.py#L223-L237) `return` **trước**
  `assemble_context` (dòng 256) và **trước** `generate_answer` (dòng 261).

→ Với 10 câu này, Gemini **không được gọi**. "Từ chối đúng" ở đây là hành vi của *truy hồi*,
không phải của *mô hình sinh*. Phát lại chúng qua một mô hình cục bộ với `context=""` **không**
tái tạo mẻ gốc mà tạo ra một phép đo khác hẳn — và sẽ làm cột "Từ chối đúng" của hàng cục bộ
không so được với hàng Gemini.

Ba lựa chọn, **không tự chọn**:

- **(a)** Sao chép hằng số cho 10 câu này ở mọi hàng của ma trận (giữ tính so sánh được của cột
  "Từ chối đúng"; trung thực với kiến trúc: nhánh này thuộc truy hồi, mà truy hồi đã bị đóng băng).
- **(b)** Thật sự đưa `context=""` vào mô hình cục bộ (đo được "mô hình nhỏ có bịa khi ngữ cảnh
  rỗng không" — đúng mối lo trong kế hoạch — nhưng **không đối xứng** với hàng Gemini, phải ghi rõ).
- **(c)** Chạy cả hai và báo cáo riêng.

Còn lại 4 câu negative (V005, V105, V114, V117) **có** đi qua mô hình sinh → phát lại bình thường.

### 7.2 `format_ok_rate` chưa có định nghĩa vận hành

Kế hoạch §3.1 định nghĩa "parse ra được ít nhất một trích dẫn hợp lệ". Nhưng có **19/137** item
GraphRAG (và **42/137** baseline) mà Gemini trả 0 citation **một cách ĐÚNG** (câu từ chối, câu
ngoài phạm vi). Nếu tính máy móc thì Gemini bị `format_ok_rate ≈ 0.86` dù không sai định dạng lần nào.

Chưa xác định: `format_ok` nên tính trên tập nào — toàn bộ 137, hay chỉ các câu có
`ground_truth_citations` khác rỗng? Đây là quyết định thuộc FT-02/FT-03, ghi lại để không quên.

### 7.3 `build_messages` hay `build_prompt` cho llama.cpp

`build_messages` trả (system, user) — hợp với chat template có system role.
`build_prompt` ([context_assembler.py:418-425](../../src/retrieval/context_assembler.py#L418-L425))
nối lại thành một chuỗi. Mô hình cục bộ nào có/không có system role → chưa xác định, phụ thuộc
mô hình chốt ở FT-03. Kế hoạch §TASK-FT-02 ghi `build_messages` nên mặc định dùng hàm đó.

### 7.4 Chưa kiểm: hai file 10/07 có phải bộ dùng cho `V2_RESULTS.md` không

`docs/V2_RESULTS.md` báo GraphRAG N=3. Timestamp `20260710-085236` là **một** trong các lần chạy;
xác định lần nào vào bảng nào nằm ngoài phạm vi FT-00 và không ảnh hưởng hợp đồng API (schema và
cú pháp trích dẫn giống nhau giữa các lần chạy cùng phiên bản code).

---

## 8. Phụ lục — cách tái lập các con số trong tài liệu này

Mọi số liệu ở trên sinh ra từ việc đọc file JSON và gọi hàm thật, ví dụ:

```python
import json
from src.retrieval.answer_generator import parse_citations

d = json.load(open("data/evaluation/results_graphrag_20260710-085236.json", encoding="utf-8"))
bad = [it["id"] for it in d["results"] if parse_citations(it["answer"]) != it["pred_citations"]]
assert bad == []          # round-trip §0
```

Cần `anthropic`, `neo4j`, `qdrant-client` đã cài (chỉ để import chạy được — **không** cần
database chạy). Đã xác nhận `from src.retrieval.context_assembler import build_messages`
import sạch khi Neo4j/Qdrant đều tắt.
