# GT Authoring Guide — Bộ Ground Truth 150 câu (eval set v2)

> Chuẩn duy nhất để soạn/kiểm bộ GT 150 câu. Mọi câu đi vào `data/evaluation/test_set_v2.json`
> PHẢI tuân theo guide này. Kiểm tự động bằng `python -m src.evaluation.verify_gt`.

**Phiên bản 1.0 | 2026-07-06**

---

## 0. Provenance & nguyên tắc phương pháp luận (E0)

- **Tác giả & trách nhiệm:** GT do **[A] soạn và chịu trách nhiệm phần Đất đai**, **[B] soạn
  và chịu trách nhiệm phần Hộ tịch + Nuôi con nuôi**. Quy trình: soạn theo guide này →
  script verify citation cơ khí ngược corpus (`verify_gt.py`) → **review chéo** ([A] duyệt
  phần của [B] và ngược lại, kiểm thật từng câu theo review sheet) → freeze + pre-register.
- **Pre-register:** sau khi A+B duyệt xong, commit `test_set_v2.json` TRƯỚC khi chạy bất kỳ
  eval nào trên nó. Ghi commit hash vào E0. Không sửa GT sau khi đã thấy output hệ thống
  (nếu buộc phải sửa lỗi thật → ghi changelog công khai trong file).
- **Dev set vs Eval set:** bộ 26 câu cũ (`test_set_dat_dai.json`) đã lái các quyết định phát
  triển (D-10/D-11 sinh từ Q024/Q026) → từ nay là **DEV SET** (không dùng báo số cuối).
  Bộ 150 mới = **EVAL SET sạch** — soạn tươi, KHÔNG copy câu từ dev set (được phép trùng
  *chủ đề* nhưng phải khác câu chữ và khác điểm hỏi).
- **Nguồn sự thật:** citation verify ngược `data/raw/` (corpus = giới hạn tri thức của hệ).
  Web (vbpl.vn, dichvucong.gov.vn) chỉ dùng spot-check tính thời sự — nếu web mâu thuẫn
  corpus thì corpus thắng cho mục đích chấm điểm, nhưng ghi chú vào `notes` để cân nhắc
  cập nhật corpus.

## 1. Phân bổ 150 câu

| Nhóm | Số câu | gap_type | subtype | Ghi chú |
|---|:---:|---|---|---|
| Gap 1 — archetype song song | 25 | `gap1` | `archetype:<tên>` | ~8 archetype × 3 domain |
| Gap 2 — đa địa phương | 26 | `gap2` | — | đất đai nặng; minimal-pair HCM↔ĐN (dư 1 so kế hoạch: cặp đảo cận-nghèo hộ tịch đáng giữ) |
| Gap 3 — đa tầng | 25 | `gap3` | — | cả 3 domain, chuỗi Luật→NĐ→TT |
| Gap 4 — đa phiên bản | 25 | `gap4` | — | bám amendment thật trong corpus |
| Negative hiển nhiên | 8 | `negative` | `obvious` | ngoài 3 domain → phải từ chối |
| Negative-gài (ngoài scope) | 6 | `negative` | `trap` | trong lĩnh vực nhưng ngoài scope (D-05) |
| Thiếu-info (best-effort) | 8 | gap chính | `underspecified` | bảo vệ D-25 — không nêu jurisdiction |
| Hợp-thành đa-gap | 8 | gap chính | `composite` | câu người dùng thật, trộn ≥2 gap |
| Biến thể register (khẩu ngữ) | 19 | gap của cặp | `register` + `pair_id` | minimal-pair đổi văn phong (bớt 1 bù gap2) |
| **Tổng** | **150** | | | ✅ CHỐT 2026-07-06, verify --final PASS |

**Tag chồng (không đếm riêng):**
- `difficulty`: mỗi gap 25 câu phải có phổ ~8 easy / 10 medium / 7 hard.
- `synthesis`: đánh dấu ~15–20 câu có đáp án nhiều phần (nhiên liệu E2c người chấm).

**Phân bổ domain (mục tiêu, không ép cứng):** đất đai ~75 · hộ tịch ~45 · nuôi con nuôi ~30.
Nếu một ô không đủ câu *sạch* (VD Gap 2 cho NCN — không có văn bản địa phương) → dồn sang
domain khác trong cùng gap, ghi lý do vào mục Limitations.

## 2. Tám archetype Gap 1 (bắt buộc dùng chung 3 domain)

| # | Archetype | Câu mẫu khung |
|---|---|---|
| A1 | Thẩm quyền | "Cơ quan nào có thẩm quyền [thủ tục]?" |
| A2 | Hồ sơ/giấy tờ | "[Thủ tục] cần nộp những giấy tờ gì?" |
| A3 | Điều kiện | "Điều kiện để [thực hiện X] là gì?" |
| A4 | Thời hạn giải quyết | "[Thủ tục] được giải quyết trong bao lâu?" |
| A5 | Lệ phí | "Làm [thủ tục] mất phí bao nhiêu / có mất phí không?" |
| A6 | Trình tự | "Các bước thực hiện [thủ tục] như thế nào?" |
| A7 | Trường hợp từ chối/không được | "Trường hợp nào [X] không được giải quyết?" |
| A8 | Nơi nộp/hình thức | "Nộp hồ sơ [thủ tục] ở đâu / có làm online được không?" |

→ Mỗi archetype xuất hiện ở **cả 3 domain** với cùng dạng câu (so like-with-like cho E2b).
25 câu = 8 archetype × 3 domain + 1 câu bù (chọn archetype giàu nội dung nhất).

## 3. Schema JSON (mở rộng tương thích ngược)

```json
{
  "id": "V001",
  "question": "…câu hỏi tự nhiên…",
  "theme": "dat-dai | ho-tich | nuoi-con-nuoi | null (negative-obvious)",
  "jurisdiction": "toan-quoc | tp-hcm | dong-nai | null (underspecified)",
  "gap_type": "gap1 | gap2 | gap3 | gap4 | negative",
  "subtype": "archetype:tham-quyen | obvious | trap | underspecified | composite | register | null",
  "pair_id": "V0xx (chỉ minimal-pair/register) | null",
  "difficulty": "easy | medium | hard",
  "synthesis": false,
  "ground_truth_answer": "…bám chữ văn bản, đủ giàu nếu synthesis=true…",
  "ground_truth_citations": [
    { "dieu": "3", "khoan": "1", "van_ban": "id-van-ban-trong-corpus" },
    { "dieu": "1B", "khoan": "1", "van_ban": "…", "loai": "phu_luc" }
  ],
  "relevant_component_ids": [],
  "notes": "vị trí đáp án + Verify OK <ngày> + reviewer",
  "review": { "verified_by": null, "date": null }
}
```

Quy ước citation Phụ lục (khớp `parse_citations` của harness): `loai: "phu_luc"`,
`dieu` = ký hiệu phụ lục ("1B", "I") hoặc `"_default"` nếu phụ lục không có ký hiệu;
`khoan` optional (gt.khoan=null là wildcard theo `cit_matches`).

Quy ước: id mới prefix **V** (V001–V150) để không đụng Q001–Q026 của dev set. `gap_type`
giữ đúng 5 giá trị cũ → harness (`metrics.aggregate`, `negative_correct`) không cần sửa;
mọi phân loại mới nằm ở `subtype`/`pair_id`/`synthesis` (field phụ, additive).
Câu `underspecified` để `jurisdiction: null` — eval KHÔNG bơm force_jurisdiction cho nhóm
này (đo hành vi best-effort thật).

## 4. Năm nguyên tắc (cấp BỘ) — tóm tắt

1. **Phân tầng theo gap** — 25/gap, không dồn cục; CI hẹp đủ khẳng định per-gap.
2. **Archetype song song 3 domain** — so cùng loại với cùng loại (E2b).
3. **Minimal-pairs** — đổi đúng 1 biến (jurisdiction / hiệu lực / register) → nhân quả.
4. **Negative 2 lớp** — hiển nhiên (ngoài domain) + gài (trong lĩnh vực, ngoài scope).
5. **Verify ngược corpus + pre-register** — GT sai tệ hơn GT ít.

## 5. Sáu bước (cấp CÂU) — tóm tắt

1. Chọn Điều/Khoản trong `data/raw/` có câu trả lời rõ.
2. Đặt câu hỏi tự nhiên (như người dân hỏi) + gán gap/subtype.
3. Viết đáp án bám chữ văn bản — không chế, không thêm ngoài corpus.
4. **Trích citation + verify ngược corpus** — (a) heading tồn tại, (b) nội dung khớp.
   Chạy `python -m src.evaluation.verify_gt` để kiểm (a) tự động; (b) người kiểm.
5. Điền metadata (theme/jurisdiction/difficulty/synthesis/notes).
6. Ráp schema, thêm vào `test_set_v2.json`; freeze sau khi A+B duyệt.

## 6. Định nghĩa difficulty

- **easy** — đáp án nằm gọn trong 1 Điều/Khoản, tra thẳng.
- **medium** — cần 2–3 vị trí trong cùng 1 văn bản, hoặc 2 văn bản có liên kết trực tiếp.
- **hard** — tổng hợp đa tầng (≥2 tier) / đa văn bản / có yếu tố sửa đổi-hiệu lực; đáp án
  nhiều phần.

## 7. Quy ước từng nhóm đặc biệt

- **Negative-obvious:** chủ đề ngoài 3 domain (xây dựng, thuế TNCN, hôn nhân...). GT answer
  = câu từ chối chuẩn; `ground_truth_citations: []`; `theme: null`.
- **Negative-trap:** đúng lĩnh vực nhưng ngoài scope corpus có chủ đích — VD đất **lâm nghiệp**
  (D-05 loại), nuôi con nuôi **có yếu tố nước ngoài** nếu corpus không phủ. PHẢI ghi trong
  `notes` lý do nó ngoài scope (trích D-05 / phạm vi thu thập).
- **Underspecified:** cố tình bỏ jurisdiction ở câu đất đai. GT answer = đáp án khung
  ("tùy địa phương: HCM là X, Đồng Nai là Y" hoặc nêu quy tắc chung + cảnh báo tùy tỉnh).
  Chấm theo hành vi: có nêu sự phụ thuộc địa phương / không đoán bừa một tỉnh.
- **Composite:** trộn ≥2 gap trong 1 câu (VD địa phương + hiện hành + đa tầng). `gap_type`
  = gap chiếm trọng số lớn nhất; liệt kê các gap phụ trong `notes`.
- **Register:** viết lại một câu chuẩn sang khẩu ngữ ("sang tên sổ đỏ", "cho con làm con
  nuôi", "làm lại giấy khai sinh"). GIỮ NGUYÊN đáp án + citation của câu gốc; `pair_id`
  trỏ về câu gốc.

## 8. Quy trình review chéo của [A] và [B]

Mỗi câu trong review sheet hiện: câu hỏi + đáp án + citation + **trích đoạn văn bản gốc**
đặt cạnh. Người review kiểm 4 điều, tick vào `review.verified_by`:
1. Đáp án đúng luật (theo corpus)? 2. Citation đúng vị trí, không thiếu/thừa?
3. gap_type/subtype gán hợp lý? 4. Câu hỏi tự nhiên, không mớm đáp án?
Review CHÉO: [B] duyệt phần đất đai của [A]; [A] duyệt phần hộ tịch+NCN của [B] —
người soạn không tự gác cổng phần mình. Câu bị sửa → chạy lại `verify_gt`.

---
*Liên hệ: D-22 (kiến trúc E0–E3), D-25 (bỏ Confirmation Loop → nhóm underspecified),
5 nguyên tắc + 6 bước thảo luận 2026-07-06.*
