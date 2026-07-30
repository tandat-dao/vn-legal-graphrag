# SỐ LIỆU CHỐT v3 — sau khi sửa lỗi phân loại địa phương

> **Trạng thái:** đây là bộ số **thay thế** `docs/V2_RESULTS.md` cho Chương 4 và Chương 5.
> Ngày chạy: 29/07/2026. Ba mẻ độc lập, đủ 137 câu, mô hình Gemini, `--no-llm-cache`.
> Tệp kết quả: `data/evaluation/results_graphrag_final{1,2,3}_20260729-*.json`
>
> Bộ câu hỏi vàng **KHÔNG thay đổi** — vẫn là bản đã đóng băng, SHA256 `bd2c5eaf…f146`,
> tag `gt-v2-freeze`. Chỉ mã nguồn thay đổi (xem mục 1).

---

## 1. Lỗi đã sửa và vì sao nó quan trọng

**Vị trí:** `src/retrieval/query_planner.py`, lời nhắc hệ thống của bộ lập kế hoạch.

**Luật cũ:** *"Nếu câu hỏi liên quan Hộ tịch hoặc Nuôi con nuôi: **LUÔN** gán jurisdiction = toan-quoc."*

**Vì sao sai:** luật này viết ở giai đoạn kho ngữ liệu **chỉ có văn bản địa phương ở lĩnh vực đất đai**. Khi kho mở rộng đa lĩnh vực, hộ tịch có thêm nghị quyết lệ phí cấp tỉnh (`nghi-quyet-11-2023-nq-hdnd-dong-nai`, `nghi-quyet-124-2016-nq-hdnd-tp-hcm-hotich`) nhưng luật không được rà lại.

**Chuỗi hậu quả:** chữ "LUÔN" khiến mô hình trả `toan-quoc` **ngay cả khi câu hỏi ghi rõ tên tỉnh** → bộ lọc cứng ở giai đoạn 2 chỉ cho phép văn bản toàn quốc → gạt sạch văn bản cấp tỉnh → **F1 = 0.000** trên các câu hộ tịch có yếu tố địa phương.

**Bằng chứng truy vết:** với V019, V008, V067, V007 — câu hỏi đều ghi rõ "Đồng Nai", đáp án tham chiếu đều là NQ 11/2023 Đồng Nai, hệ chỉ trích dẫn văn bản toàn quốc. Ablation `no-jurisdiction` (chỉ khác duy nhất ở danh sách địa phương được phép) lấy được đúng văn bản → chứng minh văn bản nằm trong tầm duyệt và bị chặn bởi bộ lọc.

**Kiểm chứng sau khi sửa:** 7/7 câu mẫu phân loại đúng địa phương; bốn câu trên đi từ 0.000 lên 1.000.

**Luật mới:** ưu tiên cao nhất là tên địa phương nêu trong câu hỏi, bất kể lĩnh vực; `toan-quoc` chỉ còn là **mặc định** khi câu hỏi không nêu địa phương.

---

## 2. Kết quả tổng thể (3 mẻ, 137 câu)

| Thước đo | v2 (còn lỗi) | **v3 (đã sửa)** | Thay đổi |
|---|---|---|---|
| **F1 cấp Khoản** | 0.578 ± 0.004 | **0.617 ± 0.001** | +0.039 |
| F1 cấp Điều | 0.596 ± 0.006 | **0.638 ± 0.002** | +0.042 |
| Norm Recall | 0.771 ± 0.016 | **0.829 ± 0.005** | +0.058 |
| Từ chối đúng câu phủ định | 13/14 | 13/14 | — |

Độ lệch chuẩn giảm mạnh (0.004 → 0.001): sau khi bỏ luật cứng, hệ ổn định hơn giữa các lần chạy.

Chi tiết ba mẻ: F1 cấp Khoản 0.6162 / 0.6172 / 0.6180.

**Precision 0.562 · Recall 0.674 · số trích dẫn trung bình 2.38** (đáp án tham chiếu trung bình 1.79).

> ⚠️ Lưu ý khi trình bày precision: mã tính `precision = 0` khi hệ không đưa ra
> trích dẫn nào (quy ước mặc định của scikit-learn). Naive RAG bỏ trống ở 31/123 câu
> còn GraphRAG chỉ 5/123, nên quy ước này **phạt baseline nặng hơn**. F1 không bị
> ảnh hưởng bởi quy ước. **Nên lấy F1 làm thang so sánh, tránh xây lập luận trên precision.**

---

## 3. So với Naive RAG — ghép cặp theo từng câu

Trung bình từng câu qua cả 3 mẻ của mỗi hệ, rồi mới ghép cặp. 123 câu có đáp án tham chiếu (loại 14 câu phủ định).

| | v2 | **v3** |
|---|---|---|
| Δ (GraphRAG − Naive RAG) | +0.143 | **+0.187** |
| Khoảng tin cậy 95% | [0.061, 0.225] | **[0.108, 0.264]** |
| Wilcoxon p | 0.0015 (\*\*) | **0.00003 (\*\*\*)** |
| Thắng / Thua / Hòa | 65 / 36 / 22 | **67 / 32 / 24** |

Bootstrap 10000 lần lấy mẫu lại, seed cố định 42.

---

## 4. Theo nhóm thách thức

| Nhóm | n | GraphRAG | Naive RAG | Δ |
|---|---|---|---|---|
| Đa lĩnh vực | 32 | 0.545 | 0.479 | +0.066 |
| **Đa địa phương** | 31 | 0.667 | 0.414 | **+0.252** |
| Đa tầng | 30 | 0.544 | 0.372 | +0.173 |
| **Đa phiên bản** | 30 | 0.571 | 0.309 | **+0.262** |
| Câu phủ định | 14 | 0.929 | 0.786 | +0.143 |

**Cả bốn thách thức đều dương.** Ở v2, nhóm đa địa phương từng bị kết luận là "cơ chế không phát huy tác dụng" — kết luận đó **sai** và do lỗi ở mục 1 gây ra.

## 5. Theo lĩnh vực

| Lĩnh vực | F1 v2 | **F1 v3** | NormR v3 |
|---|---|---|---|
| Đất đai | 0.603 | 0.591 | 0.768 |
| **Hộ tịch** | 0.561 | **0.707** | 0.932 |
| Nuôi con nuôi | 0.373 | 0.398 | 0.768 |

Hộ tịch tăng mạnh nhất — đúng lĩnh vực chịu lỗi. Đất đai không đổi trong sai số.

---

## 6. Bậc tham chiếu "GraphRAG cơ bản"

Bậc mới, đáp ứng yêu cầu của GVHD: giữ nguyên **ba giai đoạn truy hồi** nhưng tắt đồng thời **ba bộ lọc** (lĩnh vực, địa phương, thời điểm). Cấu hình `graphrag-basic` trong `ablation_config.py`.

| | GraphRAG đầy đủ (v3) | GraphRAG cơ bản |
|---|---|---|
| F1 cấp Khoản | **0.617** | 0.610 |
| Norm Recall | **0.829** | 0.827 |
| Từ chối đúng | **13/14** | 9/14 |

*(Bậc cơ bản chạy 1 mẻ, `results_graphrag_graphrag-basic_20260728-215033.json`.)*

**Kết luận:** ba bộ lọc vừa cho F1 cao hơn vừa giữ khả năng từ chối. Ở v2, bậc cơ bản từng **vượt** bản đầy đủ (0.610 so với 0.578) — đó là hệ quả của lỗi ở mục 1, không phải bằng chứng bộ lọc vô ích.

⚠️ **Đặt tên cho đúng:** bậc này **vẫn dùng Ontology** (đồ thị theo lược đồ 9 thực thể/10 quan hệ, duyệt theo quan hệ có kiểu). Không được gọi là "GraphRAG không dùng Ontology".

---

## 7. Phân tích bổ sung (dùng cho Chương 4 và 5)

### 7.1 Độ nhạy với độ chặt của thang đo

Nới quy tắc chấm, áp dụng **y hệt cho mọi hệ**:

| Hệ | Chặt (Khoản) | Cấp Điều | Chấm từng phần |
|---|---|---|---|
| GraphRAG | 0.578 | 0.596 | 0.603 |
| Naive RAG | 0.435 | 0.459 | 0.460 |
| BM25 | 0.571 | 0.593 | 0.598 |
| Oracle | 0.858 | 0.858 | 0.858 |

*(Chấm từng phần: đúng tới Khoản 1.0 · đúng Điều sai Khoản 0.6 · đúng văn bản sai Điều 0.3. Số ở bảng này tính trên bộ v2.)*

Khoảng cách GraphRAG − Naive RAG gần như bất biến: **+0.143 → +0.137 → +0.142**.

**Kết luận cho báo cáo:** ưu thế của mô hình đề xuất **không phải hệ quả của việc chọn thang đo nghiêm khắc**. Oracle không nhích chút nào (+0.000) → phần còn thiếu là lỗi thật, không phải sai lệch về độ mịn.

### 7.2 Trần của khâu sinh — tách lỗi truy hồi khỏi lỗi sinh

Tính trên bộ v2: tỉ lệ đáp án tham chiếu **có mặt trong ngữ cảnh** so với tỉ lệ **được trích dẫn**.

| Hệ | Trần truy hồi | Thực tế | Hụt do khâu sinh |
|---|---|---|---|
| GraphRAG | 0.746 | 0.675 | 0.070 |
| Naive RAG | 0.574 | 0.519 | 0.056 |
| BM25 | 0.811 | 0.738 | 0.074 |

**Đóng góp của kiến trúc nằm ở khâu truy hồi: 0.746 so với 0.574 — hơn +0.172.**

Tách theo lĩnh vực (GraphRAG): đất đai hụt 0.009 · hộ tịch 0.025 · **nuôi con nuôi 0.257**. Nuôi con nuôi truy hồi **tốt nhất** (trần 0.833) nhưng mất nhiều nhất ở khâu sinh.

### 7.3 Dư địa còn lại

45 văn bản đáp án bị bỏ sót: **26 (58%) đã nằm sẵn trong ngữ cảnh** mà mô hình không dẫn → lỗi khâu sinh, không phải truy hồi.

Nếu loại bỏ được mọi trích dẫn thừa: F1 từ 0.583 lên **0.705** (+0.12) — lớn hơn mọi cải tiến truy hồi còn khả dĩ.

**Hướng phát triển ưu tiên: cơ chế thẩm định TÍNH CẦN THIẾT của trích dẫn**, không phải mở rộng truy hồi.

---

## 8. Kết quả phủ định mới (bổ sung vào Chương 4)

| Hướng | Đo được | Kết luận |
|---|---|---|
| Bộ kiểm chứng Tier 1 (lọc trích dẫn không có căn cứ) | +0.002, loại 1/881 trích dẫn | Vô dụng ở đây: tỉ lệ tồn tại đã 99.9%, không có gì để lọc |
| Cắt bớt trích dẫn theo thứ tự | +0.005 (giữ 2 đầu) | Cái thừa không nằm ở vị trí cố định |
| Lọc từ khóa "nước ngoài" cho nuôi con nuôi | +0.017 trên lĩnh vực, **+0.003 toàn bộ** | Chỉ giải thích 37% ca sai; không đáng đưa vào luồng chính |

Ba kết quả này cùng nhóm với các kết quả phủ định đã có (D-12 nhãn từ khóa, D-19 verifier tầng 2, D-20 cross-encoder, D-24 bơm cấu trúc).

---

## 9. Việc phải cập nhật

- [ ] **Chương 4** — toàn bộ bảng số; đặc biệt **mục 4.3 phải viết lại kết luận** về bộ lọc địa phương
- [ ] **Chương 5** — mục hạn chế; thêm hướng phát triển ở 7.3
- [ ] **Poster** — bảng kết quả, bậc thang, tỉ lệ câu thua
- [ ] **README** (repo công khai) và **docs/V2_RESULTS.md**
- [ ] Tóm tắt đề tài trên ELIT nếu có nêu số

## 10. Điểm đáng nói khi bảo vệ

Lỗi này được tìm ra bằng **truy ngược có phương pháp**, không phải tình cờ: ablation cho kết quả nghịch lý (+0.182 ở nhóm đa địa phương) → không chấp nhận kết luận "cơ chế vô dụng" → truy từng câu → phát hiện hệ chỉ trích dẫn văn bản toàn quốc → đối chiếu mã nguồn → tìm ra giả định lỗi thời.

Câu chuyện *một giả định đúng ở giai đoạn đơn lĩnh vực trở thành sai khi hệ mở rộng đa lĩnh vực* chính là minh chứng cho giá trị của kiến trúc hướng Ontology: lược đồ tường minh khiến lỗi loại này **truy ra được**, thay vì chìm trong một mô hình hộp đen.
