# Test Set Schema — TASK-15

File `test_set.json` là array các object. Mỗi object là một câu hỏi đánh giá kèm ground truth, dùng cho Phase 4 evaluation (so sánh GraphRAG vs Naive Baseline).

## Cấu trúc một câu hỏi

```json
{
  "id": "Q001",
  "question": "Điều kiện chuyển mục đích sử dụng đất từ đất nông nghiệp sang đất ở tại TP.HCM?",
  "theme": "dat-dai",
  "jurisdiction": "tp-hcm",
  "gap_type": "gap2",
  "difficulty": "medium",
  "ground_truth_answer": "Cần đáp ứng đồng thời: (1) phù hợp quy hoạch SDĐ, (2) có quyết định cho phép của UBND cấp huyện, ... [tóm tắt 3-6 câu]",
  "ground_truth_citations": [
    {"dieu": "121", "khoan": "5", "van_ban": "luat-dat-dai-2024"},
    {"dieu": "4", "khoan": "3", "van_ban": "nghi-quyet-254-2025-qh15"}
  ],
  "relevant_component_ids": [],
  "notes": "Gap 2: TP.HCM dùng NQ 254 (lex posterior); Đồng Nai cùng câu hỏi sẽ có ground truth khác"
}
```

## Quy ước field

| Field | Bắt buộc | Kiểu | Giá trị / ràng buộc |
|---|---|---|---|
| `id` | ✓ | string | Format `Q\d{3}` (Q001..Q999). Unique. |
| `question` | ✓ | string | Tiếng Việt, đặt như người dùng cuối hỏi |
| `theme` | ✓ | string | `dat-dai` \| `ho-tich` \| `nuoi-con-nuoi` (xem VALID_THEMES trong CLAUDE.md) |
| `jurisdiction` | ✓ | string | `toan-quoc` \| `tp-hcm` \| `dong-nai` |
| `gap_type` | ✓ | string | `gap1` \| `gap2` \| `gap3` \| `negative` (xem bên dưới) |
| `difficulty` | ✓ | string | `easy` \| `medium` \| `hard` |
| `ground_truth_answer` | ✓ | string | Tóm tắt 3-6 câu — dùng cho Answer Quality (LLM-as-judge) |
| `ground_truth_citations` | ✓ | array | List dict `{dieu, khoan?, diem?, van_ban}`. `negative` cho phép `[]` |
| `relevant_component_ids` | optional | array | Component IDs trong Neo4j — điền sau khi chạy parser xong (dùng cho Recall@K) |
| `notes` | optional | string | Ghi chú lý do chọn câu này, edge case, lex rule áp dụng |

### `ground_truth_citations[i]` schema

```json
{"dieu": "X", "khoan": "Y", "diem": "z", "van_ban": "id-norm"}
```

- `dieu` bắt buộc (string, có thể là `"44a"`, `"PL-I"` cho Phụ lục)
- `khoan`, `diem` optional
- `van_ban` bắt buộc, là `id` của Norm — phải tồn tại trong `data/raw/*.md` (frontmatter `id`)

Format này khớp với output của [parse_citations()](src/retrieval/answer_generator.py#L40) để Citation Accuracy có thể so trực tiếp.

## Phân loại `gap_type`

| Loại | Định nghĩa | Đặc điểm câu hỏi |
|---|---|---|
| `gap1` | **Đa lĩnh vực** — câu hỏi rơi đúng 1 trong 3 themes; kiểm tra routing không nhiễu | Câu hỏi tiêu chuẩn, có 1 theme rõ ràng |
| `gap2` | **Đa địa phương** — cùng nội dung nhưng ground truth khác giữa TP.HCM và Đồng Nai | Phải nêu rõ tỉnh trong câu; thường có cặp Q_HCM / Q_DN |
| `gap3` | **Đa tầng văn bản** — đáp án đòi hỏi tổng hợp ≥ 2 văn bản khác tier (VD: Luật + Nghị định + Thông tư) | `ground_truth_citations` chứa ≥ 2 `van_ban` thuộc tier khác nhau |
| `negative` | **Câu hỏi không có đáp án trong corpus** — kiểm tra mô hình có "bịa" không | `ground_truth_citations: []`, `ground_truth_answer` nêu rõ "không có quy định" |

## DoD checklist (theo TASK-15)

- [ ] Tổng ≥ 30 câu
- [ ] ≥ 10 câu `theme="dat-dai"`
- [ ] ≥ 10 câu `theme` ∈ {`ho-tich`, `nuoi-con-nuoi`}
- [ ] ≥ 5 câu `gap_type="negative"`
- [ ] ≥ 3 câu `gap_type="gap2"` có cặp TP.HCM / Đồng Nai ground truth khác nhau
- [ ] ≥ 3 câu `gap_type="gap3"` với ≥ 2 `van_ban` khác tier
- [ ] Mỗi câu non-negative có ≥ 1 citation
- [ ] Cross-check 2 thành viên — sign-off trong [review_log.md](data/raw/review_log.md)

Script `python src/evaluation/validate_test_set.py data/evaluation/test_set.json` kiểm tự động các điều kiện đếm/format.

## Quy trình soạn

1. [A] (Đất đai) soạn ≥ 10 câu vào `test_set_dat_dai.json` theo template
2. [B] (Hộ tịch + Nuôi con nuôi) soạn ≥ 10 câu vào `test_set_ho_tich_nuoi_con_nuoi.json`
3. Cả hai cùng soạn negative cases (≥ 5)
4. Verify ground truth bằng cách mở `data/raw/[van_ban].md` đọc trực tiếp, không trust memory
5. Chạy `validate_test_set.py` trên từng file
6. Cross-review: [A] đọc test set [B] và ngược lại, ghi sign-off vào `review_log.md`
7. Merge thành `test_set.json` cuối cùng → chạy validator full
