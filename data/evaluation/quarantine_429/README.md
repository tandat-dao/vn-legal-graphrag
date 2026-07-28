# ⛔ QUARANTINE — kết quả NHIỄM lỗi Gemini 429, KHÔNG DÙNG

Các file trong thư mục này sinh ra trong mẻ đêm 09→10/07/2026 khi Vertex Gemini
hết quota (`429 RESOURCE_EXHAUSTED`) — nhiều câu có answer = `<<ERROR: 429 ...>>`
→ F1 sụp GIẢ TẠO. **Tuyệt đối không dùng cho báo cáo hay phân tích.**

| File | Số câu hỏng |
|---|---|
| results_baseline_20260709-230729.json | 126 |
| results_graphrag_20260710-001154.json | 91 |
| results_graphrag_20260710-013031.json | 9 |
| results_baseline_20260710-013031.json | 7 |

Kết quả CANONICAL (0 lỗi 429) xem `docs/V2_RESULTS.md` §1 — liệt kê đích danh file.
Cách kiểm 1 file bất kỳ: đếm `RESOURCE_EXHAUSTED` trong trường `answer`.
