# Rubric chấm chất lượng câu trả lời — E2c

> Thang chấm cho phần **đánh giá chất lượng câu trả lời** (E2c) của khâu đánh giá.
> Thay cho BERTScore (đo "giống câu tham chiếu" — proxy gián tiếp) bằng chấm trực
> tiếp "đúng và hữu ích không". Dùng cho: (1) người chấm trên MẪU NHỎ ~20–30 câu,
> (2) validate LLM-judge qua kappa rồi mới mở rộng máy ra toàn bộ.
> **Phiên bản 1.0 | 2026-07-07 — CHỜ [A] DUYỆT trước khi chấm.**

---

## 0. Nguyên tắc chấm (đọc trước)

- **Chấm MÙ:** người chấm KHÔNG được biết câu trả lời do hệ nào sinh ra (GraphRAG /
  baseline / closed-book…). Phiếu chấm sẽ ẩn danh + xáo trộn thứ tự.
- **Chấm ĐỘC LẬP:** mỗi người chấm riêng, không bàn với nhau trước khi xong (để đo
  được agreement thật). Bàn bạc thống nhất chỉ SAU khi đã nộp điểm.
- **Mỗi câu trả lời chấm theo từng chiều dưới đây**, cho điểm 1–5 (hoặc 0/1 với
  Hallucination). Có ô ghi chú lý do (khuyến khích, nhất là điểm thấp).
- **Cách neo thang điểm:** Nhóm A (pháp lý) neo đủ cả 5 mức — chấm mịn. Nhóm B
  (người dùng) neo 1–3–5; điểm **2 = trung gian giữa 1 và 3**, **4 = trung gian
  giữa 3 và 5** (vẫn cho 2/4 khi câu trả lời rơi vào khoảng giữa).
- **Ai chấm chiều nào:** xem Mục 3. KHÔNG chấm chiều ngoài chuyên môn của mình
  (người không chuyên luật KHÔNG chấm chiều pháp lý).

---

## 1. Nhóm A — Chiều PHÁP LÝ (chấm bởi: bạn học luật + [A]/[B])

### A1. Factual Correctness — Đúng pháp luật (1–5)
Nội dung câu trả lời có đúng quy định pháp luật hiện hành không?
- **5** — Hoàn toàn đúng, không sai sót về nội dung quy định.
- **4** — Đúng căn bản; sai sót nhỏ không ảnh hưởng kết luận.
- **3** — Đúng một phần; có sai sót đáng kể HOẶC thiếu điều kiện/ngoại lệ quan trọng.
- **2** — Phần lớn sai hoặc gây hiểu nhầm nghiêm trọng.
- **1** — Sai hoàn toàn / trái quy định.

### A2. Completeness — Đầy đủ pháp lý (1–5)
Câu trả lời có bao quát các khía cạnh mà câu hỏi đòi hỏi không (điều kiện, thẩm
quyền, ngoại lệ, mốc thời gian… tùy câu)?
- **5** — Trọn vẹn mọi khía cạnh cốt lõi của câu hỏi.
- **4** — Đầy đủ ý chính; chỉ bỏ sót một khía cạnh phụ nhỏ, không ảnh hưởng tính dùng được.
- **3** — Trả lời ý chính nhưng bỏ sót khía cạnh phụ ĐÁNG KỂ hoặc một số trường hợp/ngoại lệ.
- **2** — Bỏ sót nhiều nội dung; chỉ chạm bề mặt câu hỏi.
- **1** — Bỏ sót phần cốt lõi của câu hỏi.

### A3. Citation Accuracy — Chính xác trích dẫn (1–5)
Các trích dẫn Điều/Khoản/Văn bản có đúng vị trí và đủ nguồn không?
- **5** — Mọi trích dẫn đúng vị trí và đủ nguồn; không thiếu nguồn quan trọng, không thừa nguồn lạc.
- **4** — Trích dẫn đúng, đủ nguồn chính; chỉ sai/thừa/thiếu MỘT nguồn phụ nhỏ.
- **3** — Có trích dẫn đúng nhưng THIẾU nguồn quan trọng HOẶC THỪA nguồn không liên quan.
- **2** — Phần lớn trích dẫn sai vị trí hoặc thiếu; chỉ lác đác một nguồn đúng.
- **1** — Không trích dẫn / trích dẫn sai hết / dẫn văn bản không tồn tại.

### A4. Hallucination — Bịa đặt (0 hoặc 1) *(nhị phân)*
- **1 = CÓ bịa** — có ít nhất một điều khoản / số liệu / văn bản / tên gọi KHÔNG
  tồn tại hoặc bịa đặt sai lệch so với quy định.
- **0 = KHÔNG bịa.**
> Đây là cờ an toàn quan trọng nhất: một câu mượt mà nhưng bịa 1 điều luật vẫn phải
> bị đánh dấu 1.

---

## 2. Nhóm B — Chiều NGƯỜI DÙNG (chấm bởi: người thân / người không chuyên luật)

> Bạn là NGƯỜI DÂN đi hỏi thủ tục. Chấm theo cảm nhận của người dùng cuối — KHÔNG
> cần biết luật đúng hay sai (phần đó đã có chuyên gia lo).

### B1. Clarity — Rõ ràng, dễ hiểu (1–5)
- **5** — Đọc một lần hiểu ngay; mạch lạc; không rối thuật ngữ.
- **3** — Hiểu được nhưng phải đọc lại vài chỗ / hơi rối / nhiều thuật ngữ khó.
- **1** — Khó hiểu; không rõ kết luận cuối là gì.

### B2. Usefulness — Hữu ích, hành động được (1–5)
- **5** — Đọc xong biết chính xác phải làm gì tiếp theo (đi đâu, nộp gì, bao nhiêu tiền…).
- **3** — Có ích một phần nhưng còn mơ hồ về hành động cụ thể.
- **1** — Đọc xong vẫn không biết phải làm gì.

---

## 3. Ai chấm chiều nào — và kappa

| Người chấm | Chấm chiều | Ghi chú |
|---|---|---|
| **Bạn học luật (ngoài nhóm)** | A1–A4 (pháp lý) | chuẩn vàng pháp lý — uy tín độc lập |
| **[A] / [B]** | A1–A4 (pháp lý) | cần ≥2 người chấm A để tính kappa pháp lý |
| **Người thân 1, 2, … (không chuyên luật)** | B1–B2 (người dùng) | cần ≥2 người để tính kappa người-dùng |

- **Kappa (agreement) tính RIÊNG mỗi nhóm chiều:** pháp lý (giữa bạn-luật và [A]/[B]),
  người-dùng (giữa các người thân). Cần ≥2 người/nhóm — nếu chỉ 1 người thì không có kappa.
- **LLM-judge** (máy chấm) sẽ được chấm trên CÙNG mẫu, rồi so kappa với người ở
  chiều tương ứng. Kappa cao → tin máy, mở rộng ra toàn 150 câu. Kappa thấp → không
  dùng máy, ghi finding trung thực (giống D-19).

---

## 4. Quy tắc đặc biệt cho câu NEGATIVE (từ chối)

Với câu hỏi ngoài phạm vi (subtype `obvious`/`trap`), đáp án ĐÚNG = hệ **từ chối
hoặc cảnh báo ngoài scope**. Chấm điều chỉnh:
- **A1 (Đúng pháp lý):** 5 nếu hệ từ chối/cảnh báo đúng cách; 1 nếu hệ **bịa** một
  câu trả lời cho câu ngoài phạm vi (nguy hiểm nhất).
- **A3 (Citation):** câu từ chối đúng → không cần citation → chấm 5 (hoặc N/A).
- **A4 (Hallucination):** 1 nếu hệ bịa điều khoản để trả lời câu ngoài scope.
- B1/B2 vẫn chấm bình thường (câu từ chối có rõ ràng, có hữu ích không).

---

## 5. Cỡ mẫu & chọn mẫu (đề xuất)

- **~24–30 câu** cho mẫu người chấm, **phân tầng** để phủ: mỗi gap vài câu + vài
  negative + vài underspecified/composite (nơi chất lượng câu trả lời khác biệt rõ).
- **⚠️ CÙNG MỘT MẪU cho MỌI người chấm** — tất cả người chấm (bạn luật, [A]/[B],
  các người thân) chấm trên **đúng cùng N câu đó**, KHÔNG chia câu cho mỗi người.
  Đây là điều kiện BẮT BUỘC để tính kappa (chỉ đo được đồng thuận khi chấm cùng
  item). Cái chia theo người là *chiều chấm* (nhóm A vs nhóm B), không phải *câu*.
- Mỗi câu kèm câu trả lời của **các hệ đưa vào so sánh** (tối thiểu GraphRAG vs
  1–2 baseline), ẩn danh + xáo trộn. → khối lượng chấm = N câu × số hệ (VD 25 × 3
  = 75 câu trả lời/người). Cân số hệ đưa vào chấm mù với sức người thật.
- Chọn mẫu bằng seed cố định (tái lập). Sinh phiếu bằng `human_eval.py` (sắp build)
  — một mẫu duy nhất → sinh phiếu cho từng người, tất cả phủ đúng cùng item.

---

*Liên hệ: D-22 (kiến trúc E0–E3, E2c) · D-19 (tiền lệ LLM-judge thất bại → vì sao
phải validate qua kappa) · docs/EVALUATION_ARCHITECTURE.md §E2c.*
