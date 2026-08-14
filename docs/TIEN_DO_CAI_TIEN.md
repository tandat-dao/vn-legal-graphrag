# Tiến độ cải tiến sau phản biện

**Nhánh:** `cai-tien-sau-phan-bien` · **Cập nhật:** 2026-08-14

> File này để mở lại phiên làm việc sau khi tắt máy. Đọc §1 trước.

---

## 1. KHÔI PHỤC MÔI TRƯỜNG SAU KHI BẬT MÁY

```bash
cd ~/Documents/University/2526_Sem2/Thesis/vn-legal-graphrag
docker compose up -d                    # neo4j 7687 + qdrant 6333 (tự bật lại)
docker start graphrag-neo4j-thunghiem   # BẢN SAO 7688 — KHÔNG tự bật lại
```

**Quan trọng:** container `graphrag-neo4j-thunghiem` tạo bằng `docker run`, không
có `restart: unless-stopped` như hai container trong `docker-compose.yml`, nên
**phải bật tay** sau mỗi lần khởi động máy. Kiểm bằng:

```bash
docker ps --format "{{.Names}} {{.Status}}"
```

Mọi lệnh đo đều phải trỏ vào bản sao, KHÔNG đụng CSDL demo:

```bash
NEO4J_URI=bolt://localhost:7688 <lệnh>
```

Bản sao nằm ở `data/neo4j-thu-nghiem/` (523MB, đã gitignore). CSDL demo ở
`data/neo4j/` — **không được ghi vào**.

---

## 2. TRẠNG THÁI 5 VIỆC

| # | việc | trạng thái |
|---|---|---|
| 1 | Dẫn chiếu `REFERS_TO` | **XONG, kết quả dương** (+0,050 một mình) |
| 2 | Ngân sách ngữ cảnh | **XONG** — hai vòng âm, vòng ba dương nhờ nới ngưỡng token |
| 3 | Phiên bản kề + điều khoản chuyển tiếp | **XONG phần cơ chế**, chưa đo (GT không có câu nào cần) |
| 4 | Ablation summary do máy sinh | **XONG — không tụt, 0 câu thua** |
| 5 | Hạn ngạch theo khía cạnh | **XONG phần code**, đang đo |
| + | Cross-encoder xếp lại trong văn bản | **Đang đo đủ 137 câu** (mẫu 40 cho +0,029) |

### Việc 4 — kết quả

Sinh 32 summary bằng Gemini (chỉ cho máy thứ tự động lấy được, KHÔNG cho xem
summary người viết) → so ghép cặp trên 121 câu:

| cấu hình | người | máy | Δ | thắng/thua/hoà |
|---|---|---|---|---|
| off | 0,747 | 0,751 | +0,004 | 1 / **0** / 120 |
| khoan | 0,784 | 0,788 | +0,004 | 1 / **0** / 120 |
| tiêu hết ngân sách | 0,743 | 0,747 | +0,004 | 1 / **0** / 120 |
| khoan+tiêu hết | 0,751 | 0,771 | +0,021 | 3 / **0** / 118 |

**Không câu nào tệ đi**, 120/121 câu y hệt. Phát biểu đúng là **"không tụt"**,
không phải "tốt hơn" — chênh +0,004 chỉ do 1 câu đổi.

Kết luận cho hội đồng: tín hiệu định tuyến mà summary người viết cung cấp là thứ
máy tái tạo được → không phải cái nạng giấu mặt, và khâu đó tự động hoá được.
Đáp CẢ HAI góp ý của cô (tính đúng đắn của phần người làm + tự động hoá).

**Phạm vi:** chỉ nói về định tuyến ở Giai đoạn 1 — cũng là công dụng duy nhất
của trường `summary` trong hệ.

Quan sát ngược trực giác: máy nêu số Điều đích danh **nhiều gấp 16 lần** người
(158 so với 9 trên toàn corpus). Khác biệt thật là người đưa **nội dung**
(QĐ 69/2024: "tối đa 160 m² tại các quận"), máy đưa **con trỏ** ("đối tượng nêu
tại Điều 2"). Số liệu cho thấy khác biệt đó không đổi kết quả định tuyến.

Chạy lại: `--summary-type summary_auto` (sinh lại bằng
`python -m src.evaluation.summary_ablation --sinh`).

---

## 3. CẤU HÌNH TỐT NHẤT HIỆN TẠI

```
refers_mode = "khoan"          # bao đóng dẫn chiếu, chỉ dẫn chiếu đích danh khoản
budget_mode = "fill"           # tiêu phần ngân sách top_k còn trống ở bước cuối
CONTEXT_MAX_TOKENS = 12000     # thay 6000
rerank_mode = "trong-norm"     # cross-encoder xếp lại trong văn bản (CHƯA đủ bằng chứng)
```

Độ bao phủ điều khoản đáp án trong ngữ cảnh, **121 câu**, đo trên đơn vị THỰC SỰ
sống sót sau khi cắt token:

| cấu hình | cấp Khoản | Δ | thắng/thua |
|---|---|---|---|
| hiện tại (6000) | 0,747 | — | — |
| chỉ nới token 12000 | 0,761 | +0,014 | 3 / 0 |
| khoan + 12000 | 0,797 | +0,050 | 11 / 0 |
| **khoan + fill + 12000** | **0,814** | **+0,067** | **17 / 0** |

Theo gap (cấu hình tốt nhất): gap1 +0,073 · gap2 +0,066 · gap3 +0,122 · gap4 +0,011.
**Cả bốn gap đều dương, không câu nào thua.**

---

## 4. NHỮNG GÌ ĐÃ CHỨNG MINH ĐƯỢC

**Ngưỡng token đã bão hoà.** 12000 / 18000 / 30000 cho kết quả y hệt (0,814) và
dùng token y hệt (5674). 12000 KHÔNG phải giá trị dò ra — nó chỉ là "đủ lớn để
không cắt gì". Phía truy hồi đã chạm trần với các cơ chế hiện có.

**Nút thắt thật là `CONTEXT_MAX_TOKENS`, không phải trần phân bổ.** Chuỗi chẩn
đoán qua ba vòng:
- `top_k = 25` — 0/137 câu chạm tới. Số chết.
- `_MAX_PER_NORM = 3` — 99% câu đụng, nhưng nới ra không giúp.
- `_MAX_PER_TIER` — 36/38 câu đụng; nới ra thì **tệ đi** (−0,005, có câu thua),
  vì một tầng lấn và mất đa dạng đa tầng.
- `CONTEXT_MAX_TOKENS = 6000` — cắt theo `rrf_score` tăng dần, tức cắt ĐÚNG phần
  mà mọi cơ chế nạp thêm vừa đưa vào. Đây mới là ràng buộc điều khiển.

**Phần còn thiếu nằm ở đâu** (54/216 trích dẫn đáp án vẫn không lấy được):
- 13% — văn bản không vào được Giai đoạn 2 (vấn đề định tuyến)
- **87% — văn bản ĐÚNG đã có, nhưng điều khoản đáp án thua các điều khoản khác
  của chính văn bản đó** → đây là lever lớn nhất còn lại

---

## 5. VIỆC ĐANG DỞ — LÀM TIẾP TỪ ĐÂY

### 5.1 Chạy đủ 121 câu cho cross-encoder xếp lại trong văn bản

Mẫu 40 câu (34 có đáp án) cho **+0,029, 1 thắng 0 thua**, gap1 +0,100. Dương
nhưng **chỉ 1/34 câu đổi** — quá mỏng để kết luận. Bài học từ chính buổi này:
mẫu nhỏ đã hai lần dẫn tới kết luận sai.

```bash
RERANKER_DEVICE=cpu NEO4J_URI=bolt://localhost:7688 \
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  -m src.evaluation.refers_eval --test-set data/evaluation/test_set_v2.json \
  --bo rerank --out data/evaluation/rerank_full137.json
```

Chạy CPU nên chậm — mẫu 40 mất ~45 phút, đủ 137 câu dự kiến **2,5–3 giờ**.
Nên chạy nền qua đêm.

### 5.2 Bắt buộc: chạy qua BỘ SINH

Thang độ bao phủ **tăng đơn điệu theo lượng ngữ cảnh** nên không dùng làm tiêu
chí dừng được, và nó **không đo độ chính xác**. Mà nút thắt F1 của hệ là **trích
dẫn thừa** (D-18). Nhồi ngữ cảnh có thể làm precision tụt → F1 tụt dù bao phủ tăng.

Chưa chạy lần nào. Cần chạy `run_evaluation` với cấu hình tốt nhất trên một tập
con, so với mốc. Lưu ý Gemini **không tất định** (D-24) nên tập nhỏ sẽ nhiễu.

### 5.3 Việc 4 — ablation summary do máy sinh

Chưa động tới. Sinh lại 35 summary bằng máy → collection Qdrant RIÊNG (đừng đụng
`legal_texts`) → chạy lại → xem lệch bao nhiêu.

---

## 6. BẪY ĐO LƯỜNG ĐÃ GẶP — ĐỪNG LẶP LẠI

**Đo sai chỗ.** Harness ban đầu đo đơn vị `hybrid_search` CHỌN, không phải đơn vị
SỐNG SÓT sau khi `assemble_context` cắt theo token. Sai số rất lớn: `+0,053` thật
ra là `+0,004`, và biến thể tưởng thắng hoá ra có 7 câu thua. Đã sửa bằng
`assemble_context_chi_tiet()` trả kèm danh sách đơn vị giữ lại.

**Mẫu nhỏ dẫn tới kết luận sai — hai lần.**
- 26 câu: nhánh đối chứng được +0,000 → tôi kết luận toàn bộ cải thiện nhờ dẫn
  chiếu. Chạy đủ 121 câu thì đối chứng được +0,014, tức ~40% mức tăng chỉ là do
  thêm ngữ cảnh.
- 38 câu: "tiêu hết ngân sách" được +0,035 → hoá ra là ảo do đo sai chỗ.

**Luôn phải có nhánh đối chứng.** Không có nó thì không tách được "nhờ cơ chế" với
"nhờ được thêm ngữ cảnh".

**Không dò tham số trên GT đã đóng băng.** `docs/GT_FREEZE.md`, tag `gt-v2-freeze`.
Dò trên đó rồi báo cáo trên đó là hỏng con số chính của khoá luận.

---

## 7. FILE KẾT QUẢ ĐÃ LƯU

| file | nội dung |
|---|---|
| `data/evaluation/refers_full137.json` | việc 1, 4 chế độ dẫn chiếu + đối chứng |
| `data/evaluation/budget_full137.json` | việc 2 vòng 1 (kết quả âm) |
| `data/evaluation/kethop_full137.json` | vòng 3, đo SAI chỗ (giữ để đối chiếu) |
| `data/evaluation/kethop_thuc137.json` | vòng 3, đo ĐÚNG trên đơn vị sống sót |
| `data/evaluation/token_full137.json` | vòng 4, nới ngưỡng token |
| `data/evaluation/tokenbaohoa_full137.json` | vòng 5, chứng minh bão hoà |
| `data/evaluation/rerank_sample40.json` | vòng 6, cross-encoder (mẫu, chưa đủ) |

Bộ biến thể chạy lại được qua `--bo`: `refers` `budget` `budget2` `token`
`token-bao-hoa` `rerank` `ket-hop` (xem `src/evaluation/refers_eval.py`).

---

## 8. CHƯA LÀM — QUYẾT ĐỊNH CÒN TREO

- **Chưa đổi mặc định.** Cả ba cơ chế và ngưỡng 12000 đều **mặc định TẮT**; hành
  vi demo và mọi số liệu cũ KHÔNG đổi. Chỉ bật khi đã chạy qua bộ sinh và chắc
  precision không tụt.
- **Việc 2 giữ hay gỡ?** Chế độ `graph` đã chứng minh không kích hoạt (+0,000).
  Theo tiền lệ D-20 thì nên gỡ khỏi đường chạy chính, nhưng đang giữ để tái lập
  kết quả âm. Cần chốt.
- **Suy đoán bản kế nhiệm theo thời gian** (việc 3) là heuristic — đồ thị không có
  cạnh "thay thế" tường minh. Cách chắc hơn là khai báo trong frontmatter.
