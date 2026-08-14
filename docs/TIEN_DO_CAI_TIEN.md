# Tiến độ cải tiến sau phản biện

**Nhánh:** `cai-tien-sau-phan-bien` · **Cập nhật:** 2026-08-15 (đêm)

> Đọc §1 nếu vừa bật máy. Đọc §2 nếu chỉ muốn biết kết quả.

---

## 1. KHÔI PHỤC MÔI TRƯỜNG

```bash
cd ~/Documents/University/2526_Sem2/Thesis/vn-legal-graphrag
docker compose up -d                    # neo4j 7687 + qdrant 6333 (tự bật lại)
docker start graphrag-neo4j-thunghiem   # BẢN SAO 7688 — KHÔNG tự bật lại
```

Container bản sao tạo bằng `docker run` nên không có `restart: unless-stopped`
— **phải bật tay** sau mỗi lần khởi động máy.

Mọi lệnh đo trỏ vào bản sao: `NEO4J_URI=bolt://localhost:7688 <lệnh>`.
CSDL demo ở `data/neo4j/` **chưa bao giờ bị ghi vào**.

---

## 2. KẾT QUẢ — ĐỘ BAO PHỦ ĐIỀU KHOẢN ĐÁP ÁN TRONG NGỮ CẢNH

Đo trên 121–123 câu có đáp án, **tất định, không gọi bộ sinh**. Số đo trên đơn
vị THỰC SỰ lọt vào ngữ cảnh sau khi cắt theo ngưỡng token.

### Chuỗi cộng dồn (cùng harness)

| bước | cấu hình | cấp Khoản | Δ tích luỹ | thắng/thua |
|---|---|---|---|---|
| 0 | hiện tại | **0,747** | — | — |
| 1 | + bao đóng dẫn chiếu `khoan` | 0,797 | +0,050 | 11 / **0** |
| 2 | + ngưỡng token 12000 + tiêu ngân sách trống | 0,814 | +0,067 | 17 / **0** |
| 3 | + cross-encoder xếp lại trong văn bản | **0,849** | **+0,102** | 8 / **0** |

**Mỗi bước 0 câu thua.** Cả bốn gap đều dương.

Guard phạm vi đo riêng (harness mới, ghép cặp 123 câu): **+0,016 đến +0,026**,
4 câu từ 0 lên trọn vẹn, 2 câu thua một phần.

### Quét tham số (137 câu là tập phát triển — xem §6)

| tham số | kết quả | ghi chú |
|---|---|---|
| **Hệ số độ hiếm khái niệm → TẮT** | **+0,041** | Lớn nhất. Xem cảnh báo bên dưới |
| **Pool dense 50 → 100** | **+0,017** | Bão hoà tại 100 (200/400 không hơn) |
| **Ngân sách dẫn chiếu 5 → 10** | **+0,008** | Bão hoà tại 10; giảm còn 3 thì −0,008 |
| Hằng số RRF (10/30/60/150) | +0,000 | Hoà tuyệt đối 123/123 |
| Trần tầng | +0,000 | Nới đều lên 10 thì **−0,010**, 4 câu thua |
| Ngưỡng từ khoá (0,3–1,0) | +0,000 | Hoà tuyệt đối 123/123 |

**Bốn trong sáu núm hoàn toàn không ảnh hưởng** — bản thân điều đó là một phát
biểu về hệ: nó không nhạy với tinh chỉnh vặt, các mức tăng thật đến từ cơ chế
chứ không từ dò tham số.

#### ⚠️ Về hệ số độ hiếm — đọc kỹ trước khi báo cáo

Tắt hẳn `_RARITY_ALPHA` cho **+0,041**, mức tăng lớn nhất từ mọi tham số. Nhưng
đây là cơ chế mà luận văn ghi là đóng góp (D-13 / TASK-15: nút `Concept`, cạnh
`MAPS_TO_CONCEPT`, ánh xạ bản thể luận bằng LLM).

**Đừng phát biểu "cơ chế đó tệ".** Phân rã theo gap cho thấy đánh đổi có cấu trúc:

| gap | Δ khi tắt độ hiếm |
|---|---|
| gap1 đa lĩnh vực | **+0,159** |
| gap3 đa tầng | **−0,011** |
| gap2 / gap4 | +0,008 / +0,000 |

11 câu thắng **toàn bộ nằm ở gap1**; 4 câu thua **toàn bộ nằm ở gap3**.

Diễn giải đúng: **hệ số độ hiếm không vô dụng, nó bị đặt sai chỗ** — có ích khi
khái niệm thật sự phân biệt được (câu đa tầng), làm méo khi không (câu đa lĩnh
vực). Gap1 đông hơn nên tổng là dương khi tắt.

Hướng sửa đúng là **bật độ hiếm có điều kiện** thay vì bỏ hẳn — chưa thử, để
vòng sau.

### Cấu hình tốt nhất

```
refers_mode = "khoan"          # chỉ dẫn chiếu đích danh khoản
budget_mode = "fill"           # tiêu ngân sách top_k còn trống ở bước cuối
rerank_mode = "trong-norm"     # cross-encoder xếp lại TRONG văn bản đã chọn
CONTEXT_MAX_TOKENS = 12000     # thay 6000
guard phạm vi = bật            # câu không nêu địa phương → cho phép mọi tỉnh
```

**Mặc định tất cả vẫn TẮT** — hành vi demo và mọi số cũ không đổi.

---

## 3. NHỮNG GÌ ĐÃ CHỨNG MINH

**Nút thắt thật là ngưỡng token, không phải trần phân bổ.** Chuỗi chẩn đoán ba
vòng: `top_k=25` chưa bao giờ chạm (số chết) → `_MAX_PER_NORM=3` cắn 99% câu
nhưng nới ra vô ích → `_MAX_PER_TIER` cắn 36/38 câu nhưng nới ra thì **tệ đi**
→ thủ phạm là `CONTEXT_MAX_TOKENS=6000`, cắt theo `rrf_score` tăng dần tức cắt
ĐÚNG phần mọi cơ chế vừa nạp vào.

**Ngưỡng token đã bão hoà.** 12000 / 18000 / 30000 cho kết quả y hệt và dùng
token y hệt (5674). 12000 **không phải giá trị dò ra**, nó chỉ là "đủ lớn để
không cắt gì" → câu hỏi "sao chọn 12000" tự tan.

**Đảo ngược được D-20.** Ở đó cross-encoder cắm vào khâu truy hồi nên kéo đoạn
đúng từ vựng nhưng SAI văn bản lên, làm độ bao phủ văn bản tụt 0,071 và bị loại.
Cùng mô hình đó đặt **bên trong văn bản đã chọn** thì +0,034 và 0 câu thua.
*Kết quả âm cũ cho biết cơ chế không được đặt ở đâu; phép đo mới cho biết nó
phải đặt ở đâu.* Đây là lập luận mạnh nhất của cả đợt.

**Ba cơ chế cộng hưởng, không độc lập.** Cross-encoder dùng một mình có 6 câu
thua; bỏ luôn dẫn chiếu thì 12 câu thua và Δ âm. Phải trình bày như một khối.

**Việc 4 — summary máy sinh không làm tụt gì.** So ghép cặp 121 câu, **0 câu
thua** ở cả 4 cấu hình, 120/121 câu y hệt. Đáp cả hai góp ý của cô: tín hiệu
định tuyến của summary người viết là thứ máy tái tạo được → không phải nạng
giấu mặt, và khâu đó tự động hoá được.

**Hai lỗi thật đã tìm ra và sửa:**
- Bộ lập kế hoạch lấy **năm sự việc xảy ra** làm mốc lọc hiệu lực. V031 "lấn
  đất từ 2010 … NAY quy hoạch đã điều chỉnh" → chốt mốc 2010 → loại sạch Luật
  ĐĐ 2024. Hai câu V031/V032 trước đây có `norm_ids` **rỗng hoàn toàn**.
- Câu không nêu địa phương bị chốt `toan-quoc` → loại sạch văn bản cấp tỉnh,
  mà nhiều câu (lệ phí, hạn mức) có đáp án nằm đúng ở cấp tỉnh.

---

## 4. KẾT QUẢ ÂM — 8 cái, đều có chẩn đoán

| # | hướng | vì sao âm |
|---|---|---|
| 1 | Chia ngân sách theo số văn bản Giai đoạn 2 | Bề rộng Giai đoạn 2 gần như HẰNG SỐ (min 9, trung vị 10) → công thức không bao giờ kích hoạt |
| 2 | Nới trần tầng | −0,005, có câu thua. Trần tầng đang làm đúng việc; nới ra thì một tầng lấn, mất đa dạng đa tầng |
| 3 | Hạn ngạch theo khía cạnh | Khía cạnh ĐÃ được phủ sẵn ở 22/23 câu — cơ chế không có gì để sửa |
| 4 | Nới `top_n` Giai đoạn 1 (5→10) | 11/220 thiếu ở CẢ HAI mức, y hệt. Giai đoạn 2 vốn đã mở rộng theo đồ thị |
| 5 | Dẫn chiếu cấp Điều (nở ra các khoản) | 2975 cạnh không đóng góp gì mà còn tốn ngữ cảnh; toàn bộ giá trị ở 496 cạnh đích danh khoản |
| 6 | Bậc vào REFERS_TO làm tín hiệu "điều khoản nền" | Phân bố quá tập trung (Điều 137 chiếm 13–17, TB 2,4); tín hiệu không phụ thuộc câu hỏi → thiên lệch tĩnh, D-10 cảnh báo |
| 7 | Mở rộng truy vấn khẩu ngữ → thuật ngữ | Lệch từ vựng gần như không có: câu hỏi GT đã dùng đúng từ của kho |
| 8 | Tập bổ sung điều khoản chuyển tiếp | Mốc gốc đã 1,000 — tập không phân biệt được gì (lỗi soạn đề: viết câu hỏi TỪ nguyên văn điều khoản) |

Cộng với D-12 / D-19 / D-20 cũ → dự án có **11 kết quả âm có chẩn đoán**. Đây
là tài sản khi bảo vệ, không phải điểm yếu.

---

## 5. CÒN LẠI — VIỆC QUAN TRỌNG NHẤT CHƯA LÀM

**CHƯA CHẠY QUA BỘ SINH LẦN NÀO.** Toàn bộ số trên là **độ bao phủ** — trần của
những gì bộ sinh *có thể* trích dẫn, không phải thứ nó *thực sự* trích. Thang
này **không đo độ chính xác**, mà nút thắt F1 của hệ là **trích dẫn thừa**
(D-18). Nhồi thêm ngữ cảnh hoàn toàn có thể làm precision tụt và F1 đi xuống dù
bao phủ đi lên.

Đây là việc duy nhất còn lại giữa "+0,102 độ bao phủ" và một con số F1 trình
bày được. Lưu ý Gemini **không tất định** (D-24) nên tập nhỏ sẽ nhiễu.

**Việc 3 (phát hiện thay đổi + điều khoản chuyển tiếp)** không đo bằng thang
này được — nó là đóng góp về **hành vi**, không phải truy hồi. Trình bày bằng
câu demo + bộ số đếm: cảnh báo nổ 12/125 câu (9,6%), im ở 113 câu; 2 cặp phát
hiện đều là cặp thay thế thật; kho có 53 điều khoản chuyển tiếp mà hệ chưa
trích dẫn cái nào trong 137 câu.

---

## 6. LƯU Ý PHƯƠNG PHÁP — ĐỌC KỸ

Chủ nhiệm đề tài đã quyết định dùng **137 câu GT làm TẬP PHÁT TRIỂN** và soạn
GT mới làm tập kiểm thử. Hệ quả bắt buộc:

- **Số trong `V3_RESULTS.md` KHÔNG còn dùng để báo cáo cho hệ đã tinh chỉnh.**
  Phải đo lại trên tập mới.
- **Tập GT mới phải soạn mà KHÔNG nhìn vào chỗ hệ đã tinh chỉnh thắng/thua**,
  nếu không thì lặp lại đúng vấn đề.
- Trong báo cáo phải nói rõ: 137 câu là tập phát triển, tập mới là tập kiểm thử.
- Khi soạn tập mới, **cố ý viết khẩu ngữ hơn** — tập hiện tại do nhóm soạn nên
  thừa hưởng từ vựng chính quy của nhóm, không phản ánh người dùng thật.

### Bẫy đo lường đã gặp — đừng lặp lại

**Đo sai chỗ.** Harness ban đầu đo đơn vị `hybrid_search` CHỌN, không phải đơn
vị SỐNG SÓT sau khi cắt token. Sai số rất lớn: `+0,053` thật ra là `+0,004`, và
biến thể tưởng thắng hoá ra có 7 câu thua.

**Harness lệch pipeline.** Harness gọi thẳng `extract_subgraph` nên bỏ qua lớp
thời gian → lọc chặt hơn hệ thật. Đã tách `ap_dung_lop_thoi_gian()` dùng chung.

**Mẫu nhỏ dẫn tới kết luận sai — hai lần.** 26 câu: đối chứng +0,000 → kết luận
sai rằng toàn bộ cải thiện nhờ dẫn chiếu; đủ 121 câu thì đối chứng +0,014.
38 câu: "tiêu hết ngân sách" +0,035 → hoá ra ảo do đo sai chỗ.

**Luôn phải có nhánh đối chứng.** Không có nó thì không tách được "nhờ cơ chế"
với "nhờ được thêm ngữ cảnh".

---

## 7. FILE KẾT QUẢ

| file | nội dung |
|---|---|
| `refers_full137.json` | việc 1, 4 chế độ dẫn chiếu + đối chứng |
| `budget_full137.json` | việc 2 vòng 1 (âm) |
| `kethop_thuc137.json` | vòng 3, đo đúng trên đơn vị sống sót (harness cũ) |
| `token_full137.json` | vòng 4, nới ngưỡng token |
| `tokenbaohoa_full137.json` | vòng 5, chứng minh bão hoà |
| `rerank_full137.json` | cross-encoder đủ 121 câu |
| `aspect_full137.json` | việc 5 (âm) |
| `summaryauto_full137.json` | việc 4 |
| `kethop_moc_moi.json` | mốc sạch harness mới |
| `guardjuris_full137.json` | guard phạm vi |
| `chuyentiep_ket_qua.json` | tập bổ sung chuyển tiếp |
| `test_set_chuyen_tiep.json` | 12 câu bổ sung — **5 câu lĩnh vực [B] cần [B] duyệt** |

Chạy lại: `--bo {refers,budget,budget2,token,token-bao-hoa,rerank,ket-hop,aspect,chuyen-tiep,sweep-*,stack-cuoi}`
và cờ `--summary-type`, `--guard-juris`.

---

## 8. QUYẾT ĐỊNH CÒN TREO

- **Bật cấu hình mới làm mặc định?** Chưa nên — phải chạy bộ sinh trước để chắc
  precision không tụt.
- **Gỡ hay giữ ba cơ chế âm** (`budget_mode="graph"`, hạn ngạch khía cạnh, dẫn
  chiếu cấp Điều)? Tiền lệ D-20 nói nên gỡ khỏi đường chạy chính.
- **Guard phạm vi**: 4 thắng trọn vẹn đổi 2 thua một phần — bật hay không.
- **Suy đoán bản kế nhiệm** (việc 3) là heuristic theo thời gian; đồ thị chưa
  có cạnh "thay thế" tường minh. Cách chắc hơn là khai báo trong frontmatter.
