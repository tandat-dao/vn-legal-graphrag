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

## 5. ĐÃ CHẠY QUA BỘ SINH — F1 KHÔNG CẢI THIỆN

**Đây là kết quả quan trọng nhất, và nó âm.** 40 câu ngẫu nhiên (seed 42),
Gemini, ghép cặp:

| cấu hình | F1 | precision | recall | số trích dẫn |
|---|---|---|---|---|
| mốc | 0,633 | 0,615 | 0,728 | 2,17 |
| mốc + verifier | 0,633 | 0,615 | 0,728 | 2,17 |
| cải tiến | 0,627 | 0,600 | **0,773** | 2,83 |
| **cải tiến + verifier** | **0,635** | 0,607 | **0,773** | 2,75 |

Cải tiến + verifier so với mốc: **+0,002, thắng 9 thua 9 → nhiễu.**

### Đọc đúng kết quả này

**Truy hồi tốt lên thật.** Recall +0,046 khi chạy qua bộ sinh, đúng như độ bao
phủ (+0,102) dự báo. Độ bao phủ văn bản +0,013.

**Nhưng F1 không nhúc nhích**, vì bộ sinh nhận nhiều ngữ cảnh hơn thì **trích
dẫn rộng tay hơn** — 2,17 → 2,83 trích dẫn/câu (+30%). Precision tụt vừa đủ để
triệt tiêu recall tăng.

**Verifier không cứu được.** Trên mốc nó không đổi gì (mọi trích dẫn đã có căn
cứ); trên bản cải tiến chỉ vớt lại 0,007 precision. Lý do: các trích dẫn thừa
**đều có trong ngữ cảnh** — chúng đúng căn cứ nhưng không nằm trong đáp án
chuẩn. Verifier tầng 1 kiểm tính *có căn cứ* nên không bắt được loại này. Đúng
kết luận D-19: cần **bộ chấm mức liên quan / cần thiết**, không phải bộ chấm
mức hỗ trợ. Giờ đã có số chứng minh đó là nút thắt thật.

### Điều này KHÔNG phủ nhận cải tiến truy hồi

Nó **định vị chính xác** nút thắt còn lại: nằm ở khâu **sinh**, không phải khâu
truy hồi. Luận văn đã nói trích dẫn thừa là nguyên nhân trội của precision thấp
(D-18); đợt này chứng minh thêm rằng **cải tiến truy hồi một mình không vượt
qua được nó**.

### Việc tiếp theo rõ ràng

1. **Bộ chấm mức cần thiết** ở khâu sinh (D-19 đã đặt tên, chưa ai làm). Đây là
   thứ duy nhất có khả năng biến +0,046 recall thành F1 dương.
2. Hoặc **siết prompt** để bộ sinh trích dè dặt hơn khi ngữ cảnh rộng.
3. Chạy N=3 để chắc, nhưng độ lớn hiệu ứng ~0 nên khó lật.

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

---

## 9. PHIÊN 15/08 — MẺ CHỐT 137 CÂU + TẬP KIỂM THỬ v4

### 9.1 Mẻ chốt cộng dồn — 123 câu (`chot_137.json`)

Đo cộng dồn từng bước trên **cùng một harness**, tất định, không gọi mô hình:

| bước | bao phủ Khoản | bao phủ Điều | so mốc |
|---|---|---|---|
| mốc hiện tại | 0,738 | 0,809 | — |
| + dẫn chiếu + token 12000 + fill | 0,802 | 0,854 | +0,064 · 18T/0B |
| + cross-encoder trong-norm | 0,835 | 0,892 | +0,098 · 21T/0B |
| + pool 100 + tắt độ hiếm | **0,873** | **0,919** | **+0,136 · 28T/0B** |

**28 thắng / 0 thua.** Đây là con số truy hồi mạnh nhất của đợt cải tiến.

### 9.2 Tập kiểm thử v4 — 32 câu, quy ước "chuỗi dẫn chiếu"

**Độ bao phủ** (`v4_baophu.json`, bộ `ket-hop`, **trần 6000 token**):

| cấu hình | bao phủ Khoản |
|---|---|
| mốc | 0,790 |
| + REFERS_TO | **0,883** (+0,093 · 5T/0B) |
| + tiêu hết ngân sách | 0,790 (+0,000) |
| + cả hai | 0,846 |

Toàn bộ mức tăng nằm ở **gap3: 0,53 → 0,74**. Ba gap kia đã 1,00.

REFERS_TO trên v2 được +0,050, trên v4 được +0,093 — quy ước mới ghi công gần
gấp đôi cho **cùng một cơ chế**. **Nhưng đây là kết quả được kỳ vọng theo thiết
kế**, vì v4 được soạn dựa trên chính các cạnh REFERS_TO. Nó chứng minh quy ước
nhất quán, **không** chứng minh độc lập rằng hệ mạnh hơn. Hội đồng có quyền vặn
điểm này — phải chủ động nêu trong báo cáo.

**Sinh — mốc** (`results_graphrag_20260815-083636.json`, Gemini, 28 câu dương):

| | |
|---|---|
| F1 Khoản | 0,574 |
| F1 Điều | 0,614 |
| NormR | 0,964 |
| câu âm đúng | 4/4 |
| trích dẫn TB | 2,71 |

### 9.3 Hai lỗi phương pháp đã phát hiện và sửa

**Bộ `ket-hop` chạy ở 6000 token.** "Tiêu hết ngân sách" chỉ ăn khi trần token
đã nới lên 12000, nên mẻ v4 §9.2 đo nó trong điều kiện nó vốn không hoạt động →
+0,000 là **artefact của cấu hình**, không phải kết luận về cơ chế. Bộ `chot`
(đủ 12000 + cross-encoder + pool 100 + tắt độ hiếm) đã xếp hàng nhưng **chưa
chạy xong**.

**Harness giấu lỗi hệ thống.** `refers_eval` bỏ qua câu có `norm_ids` rỗng →
W007 (bộ lập kế hoạch trả `theme=None`) bị loại khỏi thống kê thay vì tính 0,
thổi phồng mọi mức bao phủ tuyệt đối. **Đã sửa**: ghi 0 cho mọi biến thể và in
cảnh báo. Các số v4 ở §9.2 là số **trước** khi sửa → còn cao hơn thực tế một
chút; chạy lại sẽ ra thấp hơn.

### 9.4 ĐANG DANG DỞ — CÁCH CHẠY TIẾP

Máy tắt lúc mẻ **sinh · cải tiến trên v4** đang chạy → mẻ này **mất, phải chạy
lại**. Hai lệnh còn thiếu (Docker + bản sao Neo4j cổng 7688 phải bật trước):

```bash
PIPE_CONTEXT_MAX_TOKENS=12000 SF_RARITY_ALPHA=0 SF_DENSE_POOL_MIN=100 \
NEO4J_URI=bolt://localhost:7688 \
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  -m src.evaluation.run_evaluation \
  --test-set data/evaluation/test_set_v4.json --systems graphrag \
  --llm-mode gemini --faithfulness-tier 0 \
  --refers-mode khoan --budget-mode fill --chuyen-tiep --verify --verify-tier 1
```

```bash
NEO4J_URI=bolt://localhost:7688 \
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  -m src.evaluation.refers_eval \
  --test-set data/evaluation/test_set_v4.json --bo chot \
  --out data/evaluation/v4_chot.json
```

So kết quả mẻ 1 với mốc `results_graphrag_20260815-083636.json` (F1 0,574),
ghép theo `id`. **Câu hỏi quyết định vẫn chưa có lời đáp:** quy ước v4 có làm
các cải tiến truy hồi hiện ra thành F1 dương hay không — trên v2 chúng chỉ được
+0,002.

**Lưu ý về mẫu:** 28 câu dương là tập nhỏ và Gemini không tất định. Chênh dưới
±0,03 thì **không kết luận**, phải chạy N=3.

**Tập v4 vẫn chưa có người rà** (`review.da_duyet=false` toàn bộ, 15 câu thuộc
lĩnh vực [B]) → chưa dùng làm số chính thức được.

---

## 10. PHÉP TÁCH 15/08 — CÔ LẬP NGUYÊN NHÂN F1 GIẢM

### 10.1 Mâu thuẫn cần giải thích

Trên **cùng tập v4, cùng cấu hình**:

| | Δ | thắng/thua |
|---|---|---|
| truy hồi (độ bao phủ) | **+0,167** | 9T/0B |
| sinh (F1 Khoản) | **−0,070** | 6T/13B |

Hệ lấy về đúng hơn hẳn rồi trích dẫn tệ đi.

### 10.2 Năm nhánh tách (v4, 28 câu dương, Gemini)

| nhánh | cấu hình | trích dẫn TB | Δ F1 | CI95 |
|---|---|---|---|---|
| mốc | — | 2,71 | — | — |
| **C** | chỉ token 12000 | 2,71 | **0,000** | — |
| **A** | chỉ `REFERS_TO` | 3,18 | −0,002 | chứa 0 |
| **D** | A + pool 100 + tắt độ hiếm | 3,68 | −0,029 | chứa 0 |
| **E** | **chỉ `fill`** | 4,04 | **−0,115** | **[−0,195; −0,038]** |
| B | tất cả, token 6000 | 4,64 | −0,093 | [−0,161; −0,024] |
| đủ bộ | B + token 12000 | 4,61 | −0,070 | [−0,137; −0,001] |

### 10.3 Ba kết luận

**Trần token KHÔNG phải thủ phạm.** Nhánh C giống mốc y hệt (0/0 khác biệt) vì
trên v4 ngữ cảnh dài nhất chỉ 5146 token — trần 6000 chưa từng cắn. Giả thuyết
ban đầu ("nới token cho mọi câu là nguyên nhân") **sai**, đã ghi lại để không
lặp lại.

**`fill` là thủ phạm duy nhất có ý nghĩa thống kê.** Một mình nó tệ hơn cả gói
đầy đủ, trong khi độ bao phủ nó mua thêm là **+0,000**. Quan trọng nhất:
`fill` làm **recall cũng giảm** (−0,018) và NormR −0,036 → đây không phải đánh
đổi precision lấy recall mà là **đơn vị sai lấn chỗ đơn vị đúng**, vì bỏ trần
per_norm cho phép một văn bản chiếm hết ngân sách. → **BÁC BỎ (D-29)**.

**`REFERS_TO` giữ lại.** Hòa tổng thể (−0,002, CI chứa 0) nhưng lãi đúng chỗ
nó được thiết kế cho: gap3 +0,041, gap4 +0,067; lỗ ở gap1/gap2 là nơi bao phủ
vốn đã 1,00 và mọi thứ thêm vào đều là nhiễu.

### 10.4 Nút thắt thật: bộ sinh chọn trích dẫn

- đáp án chuẩn v4 cần trung bình **1,57** điều khoản
- hệ ở cấu hình mốc đã trích **2,71** (thừa 1,7 lần)
- quan hệ gần tuyến tính: **mỗi +1 trích dẫn ≈ −0,03 F1**

Bộ sinh trích theo **lượng ngữ cảnh nhận được**, không theo **nhu cầu câu hỏi**.
Vì vậy mọi cải thiện truy hồi đều bị chặn lại ở khâu này.

**Đây là kết quả có giá trị cho khóa luận**: nó tách bạch được hai khâu và chỉ
đúng khâu đang nghẽn, bằng số liệu có nhánh đối chứng — mạnh hơn một con F1
nhích lên mà không giải thích được.

### 10.5 Việc tiếp theo

1. **Bản vá tiết chế trích dẫn** (`scratchpad/vá_tietche.md`) — tinh chỉnh trên
   **v2**, chạy v4 **đúng một lần** để v4 giữ tư cách tập kiểm thử.
2. **Lỗi bộ lập kế hoạch**: W007 "đăng ký giám hộ" → `theme=None` → giai đoạn 1
   rỗng → bao phủ 0. Prompt chỉ mô tả 6 thủ tục, không mô tả phạm vi lĩnh vực.
3. **v4 cần người rà** — 32/32 câu `da_duyet=false`, 15 câu thuộc lĩnh vực [B].
   Tập do máy soạn và chính máy đó đã tinh chỉnh hệ trên v2 → chưa đủ tư cách
   làm bằng chứng độc lập.

---

## 11. ĐANG LÀM — VIỆC 2: TIẾT CHẾ TRÍCH DẪN

**Trạng thái 15/08 trưa:** đang chạy nhánh mốc, CHƯA sửa prompt.

### Thiết kế phép đo

Hai nhánh khác nhau **đúng một biến** (nội dung prompt), cùng mẫu 60 câu v2
seed 42, cùng cấu hình truy hồi `--refers-mode khoan`:

| nhánh | prompt | trạng thái |
|---|---|---|
| mốc | hiện tại | đang chạy (chạy TRƯỚC khi sửa để không nhiễm) |
| tiết chế | + quy tắc tiết chế | chưa chạy |

Nội dung bản vá: `scratchpad/vá_tietche.md`. Chèn vào
`context_assembler.py` sau khối "QUY TẮC VỀ CẤU TRÚC CITATION".

### Kỷ luật tập dữ liệu — KHÔNG ĐƯỢC PHÁ

- Tinh chỉnh **chỉ trên v2**. Người dùng đã cho phép dùng v2 làm tập phát triển.
- **v4 chỉ chạy MỘT lần** sau khi prompt đã chốt. Nếu chỉnh prompt theo kết quả
  v4 thì mất tập kiểm thử giữ kín duy nhất và mọi con số v4 hết giá trị.

### Rủi ro phải theo dõi

Quy tắc "quá 3 trích dẫn là dấu hiệu trích tràn lan" có thể **cắt mất** chuỗi
dẫn chiếu dài hợp lệ (dạng W007 — điều khoản đáp án chỉ trỏ sang chỗ khác, không
chứa nội dung nào). Phải xem **recall theo gap3 riêng**, không chỉ nhìn F1 tổng.
Nếu recall gap3 tụt thì nới quy tắc, đừng giữ vì F1 tổng đẹp.

### Lệnh chạy lại nếu mất phiên

```bash
NEO4J_URI=bolt://localhost:7688 \
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  -m src.evaluation.run_evaluation \
  --test-set data/evaluation/test_set_v2.json --systems graphrag \
  --llm-mode gemini --faithfulness-tier 0 --sample 60 --seed 42 \
  --refers-mode khoan
```

So hai mẻ: `python -m src.evaluation.so_ket_qua <mốc.json> <tiết-chế.json>`

---

## 12. VIỆC 2 — TIẾT CHẾ TRÍCH DẪN: KẾT QUẢ ÂM, KÈM TRẦN ĐO ĐƯỢC

Thiết kế: hai nhánh khác nhau **đúng một biến** (nội dung prompt), cùng mẫu 60
câu v2 seed 42, cùng `--refers-mode khoan`. Nhánh mốc chạy TRƯỚC khi sửa prompt.

### 12.1 Ba cách thử, cả ba đều không ăn

| cách | F1 | CI95 | trích dẫn TB |
|---|---|---|---|
| mốc | 0,571 | — | 2,40 |
| prompt tiết chế vòng 1 | 0,593 | [−0,026; +0,070] | 2,33 |
| prompt tiết chế vòng 2 (bắt phân loại a/b/c) | 0,577 | [−0,032; +0,044] | 2,35 |

Vòng 2 **kém hơn** vòng 1 dù chỉ thị chặt hơn. Số trích dẫn gần như không đổi
qua cả ba → **bộ sinh không phản ứng với chỉ thị bằng lời**.

### 12.2 Trần lý thuyết — phần quan trọng nhất

Tính offline ($0) trên chính mẻ mốc:

| chiến lược cắt tỉa | F1 |
|---|---|
| giữ nguyên | 0,571 |
| giữ 1 / 2 / 3 / 4 trích dẫn đầu | 0,555 / 0,576 / 0,560 / 0,572 |
| **cắt hoàn hảo ("bộ lọc thần thánh")** | **0,742** |

Cắt theo **vị trí** vô giá trị (±0,005). Nhưng cắt **đúng** đáng giá **+0,171** —
lớn hơn mọi thứ đợt cải tiến này đạt được. **Dư địa có thật và rất lớn**; cái
thiếu là biết trích dẫn nào đúng.

### 12.3 Tín hiệu rẻ có thay được bộ chấm không? — KHÔNG

Kiểm tra thứ hạng truy hồi của từng trích dẫn (132 trích dẫn):

- trích dẫn ĐÚNG: hạng trung vị **3,0**
- trích dẫn SAI: hạng trung vị **5,0**

Có tách biệt, nhưng quá yếu. Mô phỏng lọc theo ngưỡng hạng:

| ngưỡng | <3 | <5 | <8 | <10 | <15 | <25 | không lọc |
|---|---|---|---|---|---|---|---|
| F1 | 0,369 | 0,433 | 0,452 | 0,458 | 0,519 | 0,601 | 0,604 |

**Hại đơn điệu.** Mọi ngưỡng đều tệ hơn không lọc.

### 12.4 Quyết định

**Gỡ bản vá prompt.** Không chứng minh được thắng thì không đổi hệ — đổi sẽ làm
mọi số liệu cũ mất khả năng so sánh mà chẳng đổi lấy được gì. Tiền lệ D-12/D-20.

**Ghi lại +0,171 làm mục tiêu đo được cho hướng phát triển tiếp**: bộ chấm mức
cần thiết của trích dẫn. D-19 đã cho thấy bộ chấm dạng "có được chứng minh
không" KHÔNG làm được việc này (citation thừa vẫn "được chứng minh"). Bộ chấm
phải hỏi **"có CẦN không"**, không phải "có ĐÚNG không".

---

## 13. VIỆC 3 — HAI LỖI THẬT ĐÃ SỬA

### 13.1 Bộ lập kế hoạch bỏ trống lĩnh vực khi không khớp thủ tục

Prompt chỉ liệt kê 6 thủ tục được lập chỉ mục sâu, **không mô tả phạm vi từng
lĩnh vực**. Gặp việc hộ tịch nằm ngoài 6 thủ tục đó (giám hộ, khai tử, cải
chính), model trả `theme=null` → Giai đoạn 1 không lọc được lĩnh vực → trả rỗng
→ **bao phủ 0**. Tái lập 3/3 lần.

Sửa: thêm mô tả phạm vi từng theme + quy tắc 0 "theme xác định ĐỘC LẬP với
procedure, không được trả null chỉ vì không tìm thấy procedure".

Kết quả (v4, planner Gemini): W007 từ **bị loại khỏi thống kê** → **0,50** ở mốc
và **1,00** khi bật dẫn chiếu. Các câu đối chứng (khai sinh, đất đai, nuôi con
nuôi) không xê dịch.

### 13.2 Harness đo bao phủ dùng SAI nhà cung cấp

`retrieval_eval._build_clients` **cố định Anthropic** cho bộ lập kế hoạch, trong
khi mọi mẻ sinh chạy `--llm-mode gemini`. Hai bên do đó dùng **kế hoạch truy vấn
khác nhau** → con số "độ bao phủ" KHÔNG phải ngữ cảnh mà bộ sinh thực sự nhận,
và phép so "bao phủ +0,167 nhưng F1 −0,070" có một confound chưa được kiểm soát.

Sửa: `_build_clients` đọc `LLM_MODE` (mặc định `claude`, không đổi hành vi cũ).

**Số đo lại trên v4 với planner đồng bộ Gemini** (n=28, đã gồm W007):

| cấu hình | bao phủ Khoản |
|---|---|
| mốc | 0,792 |
| **+ REFERS_TO** | **0,917** (+0,125) |

gap3: 0,551 → 0,821.

> Mọi số bao phủ ghi ở §9–§10 đều đo bằng planner Claude. Chúng vẫn hợp lệ để so
> **giữa các biến thể với nhau** (cùng planner), nhưng KHÔNG được đặt cạnh số F1
> của các mẻ sinh Gemini như thể cùng một hệ. Từ nay dùng `LLM_MODE=gemini`.

---

## 14. HỆ QUẢ CỦA §13.2 — MỘT SỐ LIỆU ĐÃ BÁO CÁO BỊ LẬT

Sau khi harness dùng đúng nhà cung cấp, đo lại `REFERS_TO` (mốc → +dẫn chiếu,
trần 6000, không cross-encoder):

| tập | planner Claude (SAI) | planner Gemini (ĐÚNG) |
|---|---|---|
| v2 — 123 câu chấm được | +0,050 | **+0,018** (10T/3B) |
| v4 — 28 câu | +0,093 | **+0,125** |

Trên v2, per-gap với planner đúng: gap1 **+0,078**, gap3 **+0,072**,
gap4 **+0,000**, gap2 **−0,081**.

### Vì sao v4 cao gấp bảy lần v2 — và vì sao KHÔNG được lấy v4 làm số chính

v4 được soạn **từ chính các cạnh `REFERS_TO`** trong đồ thị (xem
`docs/GT_V4_QUY_UOC.md` §4). Nó được xây để ghi công cho đúng cơ chế đang đo.
Chênh lệch +0,125 so với +0,018 phản ánh **cách soạn tập**, không phải năng lực
hệ thống.

**Quy tắc trình bày:** lấy **v2 làm số chính** (+0,018). v4 chỉ được nêu kèm
cảnh báo tự-ưu-ái này. Nói ngược lại là tự tô hồng.

### Số cộng dồn §9 (+0,136 · 28T/0B) ĐANG BỊ NGHI NGỜ

Số đó cũng đo bằng planner Claude. Đang chạy lại bộ chốt đầy đủ trên 137 câu với
planner Gemini (`v2_chot_gemini.json`). **Không đưa +0,136 vào báo cáo cho tới
khi có số đo lại.**

---

## 15. SỐ CHỐT CỦA ĐỢT CẢI TIẾN (planner đồng bộ Gemini, 123 câu v2)

### 15.1 Cấu hình THỰC SỰ ĐEM DÙNG — bỏ `fill` theo D-29

| bước | bao phủ Khoản | Δ | T/B |
|---|---|---|---|
| mốc hiện tại | 0,741 | — | — |
| + dẫn chiếu `REFERS_TO` | 0,759 | +0,018 | 10/3 |
| + cross-encoder trong-norm | 0,806 | +0,065 | 17/5 |
| + pool 100 + tắt độ hiếm | **0,851** | **+0,109** | **25/4** |

Per-gap: gap1 **+0,185**, gap3 **+0,169**, gap2 +0,069, gap4 +0,011.

### 15.2 So với bản có `fill`

| | bao phủ | Δ | token ngữ cảnh TB |
|---|---|---|---|
| mốc | 0,741 | — | 3520 |
| đủ bộ, KHÔNG fill | 0,851 | +0,109 | 4343 |
| đủ bộ, CÓ fill | 0,870 | +0,129 | 6253 |

`fill` mua thêm **+0,020 bao phủ** bằng cách nhồi thêm **~1900 token**, và cái
giá ở khâu sinh là **−0,115 F1** (§10). Đổi chác tệ → giữ nguyên quyết định bác
bỏ ở D-29.

### 15.3 Con số nên dùng trong báo cáo

> **Độ bao phủ điều khoản đúng: 0,741 → 0,851 (+0,109), 25 thắng / 4 thua trên
> 123 câu.** Đóng góp lớn nhất ở gap1 (+0,185) và gap3 (+0,169).

Kèm theo BẮT BUỘC nêu: mức tăng bao phủ này **không chuyển thành F1** —
xem §10 và §12. Đó mới là phát hiện chính.

### 15.4 Ba cảnh báo phải nói trước hội đồng

1. **Bao phủ ≠ F1.** Cùng tập, cùng cấu hình: bao phủ +0,167 (v4) / +0,109 (v2)
   nhưng F1 −0,070. Nút thắt đã chuyển sang khâu chọn trích dẫn của bộ sinh.
2. **v4 tự ưu ái.** Soạn từ chính các cạnh `REFERS_TO` → dùng v2 làm số chính.
3. **v4 chưa có người rà**, 32/32 câu `da_duyet=false`.
