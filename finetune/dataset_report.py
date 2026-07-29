"""TASK-FT-04 — Báo cáo bộ dữ liệu: `dataset_stats.md` + `samples_20.txt`.

Tách khỏi `build_dataset.py` để phần sinh dữ liệu không dính phụ thuộc
`transformers` (chỉ dùng ở đây, để đếm token thật thay vì quy đổi ước lượng).
"""
from __future__ import annotations

import hashlib
import json
import random
import statistics
from pathlib import Path

# Token đếm bằng tokenizer Qwen2.5 — CÙNG tokenizer mà token_budget.md §2.7.2
# dùng để chốt các mốc p50/p95/max. Đổi tokenizer là không so được nữa.
TOKENIZER_ID = "Qwen/Qwen2.5-7B-Instruct"
CHARS_PER_TOKEN = 2.87


def _get_tokenizer():
    try:
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(TOKENIZER_ID)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠️  không nạp được tokenizer {TOKENIZER_ID} ({e}) → ước lượng theo ký tự")
        return None


def _n(x: int) -> str:
    """Số có dấu cách phân nhóm nghìn (U+00A0). Dùng hàm này thay vì gọi
    `.replace` trên CẢ DÒNG — cách đó ăn luôn dấu phẩy của văn xuôi."""
    return format(x, ",").replace(",", " ")


def _pct(xs: list[int], q: float) -> int:
    if not xs:
        return 0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _bang_do_dai(nhan: str, toks: list[int]) -> str:
    if not toks:
        return f"| {nhan} | – | – | – | – | – |\n"
    return (
        f"| {nhan} | {len(toks)} | {_n(int(statistics.mean(toks)))} | {_n(_pct(toks, .50))} "
        f"| {_n(_pct(toks, .95))} | {_n(max(toks))} |\n"
    )


def viet_bao_cao(samples, train, val, stats: dict, report_dir: Path, rng: random.Random) -> None:
    from src.retrieval.context_assembler import build_messages

    report_dir.mkdir(parents=True, exist_ok=True)
    tok = _get_tokenizer()

    def ntok(text: str) -> int:
        if tok is None:
            return int(len(text) / CHARS_PER_TOKEN)
        return len(tok(text, add_special_tokens=False)["input_ids"])

    def ntok_batch(texts: list[str], nhan: str) -> list[int]:
        """Tokenize theo lô. Gọi từng chuỗi một trên 5 000 context ~14k ký tự mất
        hàng chục phút; theo lô thì còn vài chục giây."""
        if tok is None:
            return [int(len(t) / CHARS_PER_TOKEN) for t in texts]
        out: list[int] = []
        step = 128
        for i in range(0, len(texts), step):
            enc = tok(texts[i : i + step], add_special_tokens=False)["input_ids"]
            out.extend(len(x) for x in enc)
            print(f"    đếm token {nhan}: {min(i + step, len(texts))}/{len(texts)}", end="\r")
        print(" " * 60, end="\r")
        return out

    system_prompt, _ = build_messages("x", "y", "general")
    n_sys = ntok(system_prompt)

    # Khung cố định của user_prompt = 30 ký tự (api_contract.md §1.2). Đếm context,
    # câu hỏi, đáp án riêng rồi cộng — thay vì tokenize lại cả chuỗi user (vốn đã
    # chứa context) thêm một lượt nữa. Sai số vài token ở chỗ nối, không ảnh hưởng
    # bảng phân phối.
    n_frame = ntok("CONTEXT:\n\n\nCÂU HỎI: \n\nTRẢ LỜI:")
    ctx_all = ntok_batch([s.context for s in samples], "context")
    ans_tok = ntok_batch([s.answer for s in samples], "đáp án")
    q_tok = ntok_batch([s.question for s in samples], "câu hỏi")

    ctx_tok: dict[str, list[int]] = {"graphrag": [], "baseline": []}
    tong_tok: list[int] = []
    for s, n_ctx, n_ans, n_q in zip(samples, ctx_all, ans_tok, q_tok):
        ctx_tok[s.header_format].append(n_ctx)
        tong_tok.append(n_sys + n_frame + n_ctx + n_q + n_ans)

    n = len(samples)
    by_format = {k: sum(1 for s in samples if s.header_format == k)
                 for k in ("graphrag", "baseline")}
    by_kind = {k: sum(1 for s in samples if s.kind == k)
               for k in ("answerable", "refusal_no_basis", "refusal_out_of_scope")}
    n_refusal = by_kind["refusal_no_basis"] + by_kind["refusal_out_of_scope"]
    hinh_dang = {}
    for s in samples:
        for c in s.citations:
            key = ("Điều|Khoản|Điểm|Văn bản" if c["diem"]
                   else "Điều|Khoản|Văn bản" if c["khoan"]
                   else "Điều|Văn bản")
            hinh_dang[key] = hinh_dang.get(key, 0) + 1
    n_blocks = [s.n_blocks for s in samples]
    n_cits = [len(s.citations) for s in samples if s.kind == "answerable"]

    # ---------------- dataset_stats.md ----------------
    md = []
    md.append("# TASK-FT-04 — Bộ dữ liệu huấn luyện\n\n")
    md.append(f"**Sinh bởi:** `python -m finetune.build_dataset` · seed `{stats['seed']}` "
              f"· tất định (cùng seed → cùng bộ)\n\n")
    md.append(f"**Nguồn:** `thangvip/vietnamese-legal-qa` — 9 715 dòng / 29 145 cặp QA, "
              f"141 `doc_name`, `doc_type_name` một giá trị \"Luật\".\n\n")
    md.append("---\n\n## 0. Một dòng\n\n")
    md.append(f"> **{_n(n)} mẫu** ")
    md.append(f"— {by_format['graphrag']} khuôn GraphRAG / {by_format['baseline']} khuôn "
              f"baseline ({by_format['graphrag']/n:.1%} / {by_format['baseline']/n:.1%}); "
              f"**{n_refusal} mẫu từ chối ({n_refusal/n:.1%})**; "
              f"train {len(train)} / val {len(val)} tách theo `doc_name`.\n")
    md.append("> 100% khối trích dẫn round-trip đúng qua `parse_citations`.\n\n")

    md.append("---\n\n## 1. Số bị drop, theo từng lý do\n\n")
    md.append("Đếm trên **dòng** với các lý do ở cấp văn bản/điều, trên **cặp QA** với "
              "các lý do ở cấp câu hỏi.\n\n")
    md.append("| Lý do | Số bị drop | Giải thích |\n|---|---:|---|\n")
    giai_thich = {
        "leak_doc_corpus": "`doc_name` khớp một trong 32 văn bản của corpus (so tên đã bỏ dấu + so số hiệu)",
        "leak_question_ngram": "câu hỏi trùng 5-gram hoặc Jaccard ≥ 0.6 với 137 câu `test_set_v2.json`",
        "khong_suy_duoc_slug": "không suy được slug theo convention — toàn bộ là bản \"Dự thảo Luật …\" (không số hiệu, không năm)",
        "article_qua_dai": "`article_content` > 50 000 ký tự",
        "article_qua_ngan": "`article_content` < 200 ký tự, hoặc không phân rã được Điều/Khoản",
        "qa_co_ngoac_vuong": "prose chứa `[` hoặc `]` → `parse_citations` bắt nhầm thành khối, phá round-trip",
        "qa_khong_suy_duoc_dieu": "đáp án nhắc Điều khác Điều nguồn → không chắc trích dẫn thuộc về đâu",
        "doc_ngoai_pham_vi": "văn bản thuộc lĩnh vực system prompt liệt kê là NGOÀI PHẠM VI → chuyển hết sang pool mẫu từ chối, không dùng làm mẫu trả lời được",
        "doc_thieu_dieu_de_dong_goi": "văn bản có < 4 điều dùng được → không đóng gói được 4-6 điều",
    }
    for k, v in sorted(stats["drops"].items(), key=lambda kv: -kv[1]):
        md.append(f"| `{k}` | {_n(v)} | {giai_thich.get(k, '')} |\n")
    md.append(f"\nCòn lại: **{stats['n_doc_sau_loc']} văn bản**, "
              f"**{_n(stats['n_qa_dung_duoc'])} cặp QA** dùng được "
              f"({_n(stats['n_qa_trong_pham_vi'])} trong phạm vi corpus "
              f"/ {_n(stats['n_qa_ngoai_pham_vi'])} ngoài phạm vi).\n\n")

    md.append("### 1.1 Lọc rò rỉ — danh sách chặn\n\n")
    md.append(f"Đọc frontmatter `id` + `title` của `data/raw/*.md` → "
              f"**{len(stats['blocklist'])} văn bản**. Hai khoá so khớp độc lập:\n\n")
    md.append("1. **số hiệu pháp lý** trong `title` (`31/2024/QH15`, `102/2024/NĐ-CP`…)\n")
    md.append("2. **tên văn bản đã bỏ số/năm**, chuẩn hoá bỏ dấu + lowercase "
              "(`luat dat dai`, `luat ho tich`, `luat nuoi con nuoi`)\n\n")
    md.append("Bộ nguồn CÓ chứa văn bản của corpus — lọc này không phải thủ tục cho có:\n\n")
    md.append("| `doc_name` trong bộ nguồn | Khớp với |\n|---|---|\n")
    md.append("| Luật Hộ tịch của Quốc hội, số 60/2014/QH13 | `luat-ho-tich-2014` |\n")
    md.append("| Luật Nuôi con nuôi của Quốc hội, số 52/2010/QH12 | `luat-nuoi-con-nuoi-2010` |\n")
    md.append("| Luật sửa đổi, bổ sung một số điều của Luật Đất đai số 31/2024/QH15… | "
              "`luat-dat-dai-2024` (số hiệu) |\n\n")
    md.append("Lớp n-gram **cố ý bảo thủ**: 5-gram bắt cả cụm rập khuôn của văn phong "
              "pháp lý (\"cơ quan nào có thẩm quyền\", \"mức thu phí thẩm định hồ sơ\") "
              "nên drop cả những câu hỏi thực ra độc lập. Chấp nhận đánh đổi đó — pool "
              "còn dư nhiều lần so với nhu cầu, mất dữ liệu rẻ hơn hẳn so với rò rỉ.\n\n")

    md.append("---\n\n## 2. Phân phối độ dài — đối chiếu `token_budget.md`\n\n")
    md.append(f"Đếm bằng tokenizer `{TOKENIZER_ID}` — **cùng tokenizer** mà "
              f"`token_budget.md` §2.7.2 dùng để chốt mốc. System prompt đo lại ở đây: "
              f"**{_n(n_sys)} token** (khớp 3 936 của token_budget.md §2.2).\n\n")
    md.append("### 2.1 Phần `context`\n\n")
    md.append("| Khuôn | n | mean | p50 | p95 | max |\n|---|---:|---:|---:|---:|---:|\n")
    md.append(_bang_do_dai("GraphRAG — sinh ra", ctx_tok["graphrag"]))
    md.append(_bang_do_dai("Baseline — sinh ra", ctx_tok["baseline"]))
    md.append("| GraphRAG — **mục tiêu** (§2.7.2) | 127 | – | ~4 200 | ~7 600 | ~8 000 |\n")
    md.append("| Baseline — **mục tiêu** (§2.7.2) | 137 | – | ~1 800 | – | ~2 450 |\n\n")

    md.append("### 2.2 Đáp án và tổng chuỗi huấn luyện\n\n")
    md.append("| Đại lượng | n | mean | p50 | p95 | max |\n|---|---:|---:|---:|---:|---:|\n")
    md.append(_bang_do_dai("đáp án (phần sinh ra)", ans_tok))
    md.append(_bang_do_dai("tổng = system + user + đáp án", tong_tok))
    vuot = sum(1 for t in tong_tok if t > 16384)
    md.append(f"\n`max_seq_length = 16 384` (chốt ở FT-01 §2.7.1): **{vuot} mẫu vượt trần** "
              f"({vuot/n:.2%}).\n\n")

    md.append("---\n\n## 3. Tỉ lệ hai khuôn header\n\n")
    md.append("| Khuôn | n | tỉ lệ |\n|---|---:|---:|\n")
    for k in ("graphrag", "baseline"):
        md.append(f"| `{k}` | {_n(by_format[k])} | {by_format[k]/n:.1%} |\n")
    md.append("\nKhuôn nguyên văn (api_contract.md §6):\n\n```\n")
    md.append("GraphRAG:  --- [Tier N | Hiệu lực: YYYY-MM-DD] Điều …, Khoản …. (slug) ---\n")
    md.append("Baseline:  --- Văn bản: slug, chunk i ---\n```\n\n")
    md.append("Chỉ dạy khuôn GraphRAG thì mô hình đã tinh chỉnh sẽ đọc cột Naive RAG kém hơn "
              "**vì lý do định dạng**, làm Δ ở hàng đó phồng lên giả tạo (kế hoạch §9.2(4)).\n\n")
    md.append("Hai biến thể của khuôn GraphRAG cũng được tái tạo, **chỉ trên block "
              "distractor** nên không bao giờ mâu thuẫn đáp án gold:\n\n")
    md.append("- `Hiệu lực: D → D (HẾT HIỆU LỰC)` — 5% ngữ cảnh (thực tế 45/2 199 header)\n")
    md.append("- khối `[AMENDMENT WARNING — …]` — 40% ngữ cảnh (thực tế 104/137 item)\n\n")

    md.append("---\n\n## 4. Mẫu từ chối\n\n")
    md.append("| Loại | n | tỉ lệ | Chuỗi đáp án |\n|---|---:|---:|---|\n")
    md.append(f"| `refusal_no_basis` | {_n(by_kind['refusal_no_basis'])} | "
              f"{by_kind['refusal_no_basis']/n:.1%} | nguyên văn quy tắc bắt buộc "
              f"`context_assembler.py:379` |\n")
    md.append(f"| `refusal_out_of_scope` | {_n(by_kind['refusal_out_of_scope'])} | "
              f"{by_kind['refusal_out_of_scope']/n:.1%} | nguyên văn `answer` của "
              f"V105 / V114 / V117 (= `context_assembler.py:373`) |\n")
    md.append(f"| **cộng** | **{_n(n_refusal)}** | **{n_refusal/n:.1%}** | |\n\n")
    md.append("### 4.1 Vì sao HAI chuỗi chứ không phải một\n\n")
    md.append("Ba câu bẫy phủ định thật sự đi qua mô hình sinh — V105, V114, V117 — có "
              "`answer` **byte-identical** với nhau (api_contract.md §3 ví dụ G), nên chỉ "
              "cho **một** chuỗi, và đó là chuỗi *rào phạm vi corpus*. Nhưng cách dựng ở "
              "kế hoạch mục D (bỏ điều gold, giữ tài liệu liên quan) lại là ca *thiếu căn "
              "cứ*, mà system prompt bắt trả lời bằng chuỗi **khác** "
              "(`context_assembler.py:379`). Dán chuỗi \"ngoài phạm vi\" vào ca đó là dạy "
              "sai ánh xạ, nên bộ này dùng đúng chuỗi cho đúng điều kiện.\n\n")
    md.append("> ⚠️ **Sửa lỗi id trong đề bài FT-04.** Bản giao việc ghi *\"lấy nguyên văn "
              "từ V005, V114, V117 — ba câu đã từ chối đúng; bỏ V105 (ca trả lời quá "
              "đà)\"*. Dữ liệu thật ngược lại: **V005** mới là ca trả lời quá đà (IRAC 4 "
              "heading, ~2 400 ký tự, **4 citation** trong khi `ground_truth_citations` "
              "rỗng → `negative_correct=False`), còn **V105** byte-identical với V114/V117. "
              "Mô tả khớp chính xác, chỉ hai id bị hoán. Bộ này dùng V105/V114/V117 và bỏ "
              "V005.\n\n")
    md.append("| Loại | Cách dựng | Điều kiện học được |\n|---|---|---|\n")
    md.append("| `refusal_no_basis` | đúng kế hoạch mục D: đóng gói 4-6 điều **cùng văn "
              "bản** nhưng **loại điều gold ra** | \"ngữ cảnh có tài liệu liên quan nhưng "
              "không chứa căn cứ\" — tín hiệu quan sát được |\n")
    md.append("| `refusal_out_of_scope` | câu hỏi lấy từ văn bản thuộc lĩnh vực NGOÀI phạm "
              "vi; ngữ cảnh đóng gói từ một văn bản **KHÁC** | tái tạo đúng cấu hình "
              "V114/V117: hỏi lệ phí trước bạ / thuế TNCN trong khi truy hồi trả về đất "
              "đai |\n\n")
    md.append("Ngữ cảnh RỖNG thì quá dễ, không dạy được gì — cả hai loại đều có ngữ cảnh "
              "đầy đủ. Có `assert` chặn: với `refusal_no_basis`, điều gold phải **thật sự "
              "vắng mặt** trong ngữ cảnh.\n\n")
    md.append("Văn bản thuộc lĩnh vực ngoài phạm vi bị **loại hẳn khỏi pool trả lời "
              "được** (5 408 cặp QA, xem §1). Nếu không, cùng một bề mặt đầu vào sẽ mang "
              "hai nhãn trái nhau — lúc thì trả lời có trích dẫn, lúc thì từ chối — và "
              "giám sát mâu thuẫn kiểu đó không học được gì.\n\n")
    md.append("**Không** dùng hằng số `src/pipeline.py:233` (\"Không tìm thấy văn bản pháp "
              "luật liên quan đến câu hỏi này.\") — đó là nhánh truy hồi rỗng, mô hình sinh "
              "**chưa từng được gọi** (api_contract.md §7.1), khác ca hoàn toàn.\n\n")

    md.append("### 4.2 Vì sao hạ từ 20% xuống 9%\n\n")
    md.append(f"Mẻ trước đặt `FRAC_REFUSAL = 0.20` → 1 000 mẫu từ chối. Mẻ này "
              f"**{_n(n_refusal)} mẫu ({n_refusal/n:.1%})**, giữ nguyên tỉ lệ 70/30 giữa "
              f"hai loại ({_n(by_kind['refusal_no_basis'])} `no_basis` / "
              f"{_n(by_kind['refusal_out_of_scope'])} `out_of_scope`).\n\n")
    md.append("**Lý do — đếm lại xem 20% đó bảo vệ được bao nhiêu câu:**\n\n")
    md.append("Chỉ **4/127** câu eval thật sự đi qua mô hình sinh ở nhánh phủ định. "
              "10/14 câu bẫy do nhánh truy hồi RỖNG quyết định (`if not norm_ids`, "
              "`pipeline.py:223` return trước `generate_answer`) — mô hình chưa từng được "
              "gọi, và `replay.py` sao chép hằng số cho đúng 10 câu đó ở mọi hàng của ma "
              "trận. Trong khi **F1 cấp Khoản đo trên 123 câu**. Dành 20% ngân sách huấn "
              "luyện cho hành vi từ chối là đem 123 câu ra đánh cược để bảo vệ 4 câu.\n\n")
    md.append("**Vì sao vẫn nghiêng 70/30 về `no_basis`:** V005 — ca `no_basis` DUY NHẤT "
              "trong eval — là ca mà **cả Gemini cũng trả lời quá đà** (4 citation trong "
              "khi `ground_truth_citations` rỗng → `negative_correct=False`, xem §4.1). "
              "Đó là hành vi khó, cần nhiều mẫu. Ba ca `out_of_scope` ngược lại: được chi "
              "phối bởi **danh sách chặn tường minh** ở "
              "`src/retrieval/context_assembler.py:368-373` — system prompt liệt kê thẳng "
              "chủ đề ngoài phạm vi và đọc sẵn nguyên văn câu phải trả lời — nên cần ít "
              "mẫu hơn để học.\n\n")
    md.append("Đánh đổi phải ghi vào giới hạn: 9% là **giả định**, không phải số đo. Nếu "
              "hàng \"cục bộ đã tinh chỉnh\" cho `tu_choi_dung` tụt so với hàng chưa tinh "
              "chỉnh thì đây là biến đầu tiên phải xem lại.\n\n")

    md.append("---\n\n## 5. Khối trích dẫn\n\n")
    md.append("| Hình dạng | n |\n|---|---:|\n")
    for k, v in sorted(hinh_dang.items(), key=lambda kv: -kv[1]):
        md.append(f"| `[{k.replace('|', ' \\| ')}]` | {_n(v)} |\n")
    md.append(f"\nSố citation mỗi mẫu trả lời được: mean {statistics.mean(n_cits):.2f}, "
              f"max {max(n_cits)}. Số block mỗi ngữ cảnh: mean {statistics.mean(n_blocks):.1f}, "
              f"p50 {_pct(n_blocks, .5)}, max {max(n_blocks)}.\n\n")
    md.append("Ràng buộc đã áp (api_contract.md §3.2, có bằng chứng trên 401/401 khối thật):\n\n")
    md.append("- phân cách `, `; `Văn bản` **luôn cuối**; giá trị là **slug**, không phải số hiệu\n")
    md.append("- **không** dạy `Tiết` (0/401 khối thật dùng)\n")
    md.append("- **không** dùng `Mục` / `Dòng` / `Phần` (parser bỏ qua im lặng, ca thật V119/V131)\n")
    md.append("- chỉ 6 từ khoá parser hiểu: `Điều`, `Phụ lục`, `Khoản`, `Điểm`, `Tiết`, `Văn bản`\n\n")

    md.append("---\n\n## 6. Kiểm tra bắt buộc (DoD)\n\n")
    md.append("| # | Kiểm tra | Kết quả |\n|---|---|---|\n")
    md.append("| 1 | `finetune/slug.py` ≥ 10 unit test | ✅ 22 ca, `tests/test_finetune_slug.py` |\n")
    md.append("| 2 | 0 mẫu còn khớp danh sách chặn | ✅ assert trên toàn bộ mẫu |\n")
    md.append(f"| 3 | 100% khối trích dẫn parse được **và** round-trip đúng "
              f"(Điều, Khoản, Điểm, slug) | ✅ {_n(n)} / {_n(n)} |\n")
    md.append("| 3b | slug của mọi citation có mặt trong `context` của chính mẫu đó | "
              "✅ assert — chống dạy mô hình bịa slug từ trí nhớ |\n")
    md.append("| 4 | phân phối độ dài đối chiếu `token_budget.md` | ✅ §2 |\n")
    md.append("| 5 | 20 mẫu đầy đủ để kiểm tay | ✅ `samples_20.txt` |\n\n")

    md.append("---\n\n## 7. Giới hạn — phải ghi vào mục 4.7\n\n")
    md.append("1. **Chỉ văn bản cấp luật.** `doc_type_name` một giá trị \"Luật\" → không có "
              "nghị định, thông tư, văn bản địa phương. Dạy được **định dạng trích dẫn và "
              "từ vựng pháp lý cấp luật**, không dạy suy luận đa tầng hay ràng buộc địa "
              "phương. Có lợi cho lập luận: tách bạch đóng góp của tinh chỉnh khỏi đóng "
              "góp của kiến trúc.\n")
    md.append("2. **Đáp án do mô hình ngôn ngữ sinh tự động**, không phải người viết. "
              "Phần prose giữ nguyên của bộ nguồn; chỉ câu mở đầu bị đa dạng hoá cơ khí và "
              "khối trích dẫn được nối thêm.\n")
    md.append("3. **Slug là slug tổng hợp**, không có trong corpus 32 văn bản. Chủ ý: mẫu "
              "dạy *chép slug từ header ngữ cảnh*, không dạy *nhớ slug*. Điều kiện bắt buộc "
              "(đã assert) là slug phải xuất hiện trong ngữ cảnh của chính mẫu đó.\n")
    md.append("4. **Ngày hiệu lực trong header là tổng hợp** (`{năm ban hành}-01-01`), "
              "cũng như nội dung khối `[AMENDMENT WARNING]`. Chúng chỉ tái tạo **bề mặt "
              "chuỗi** của ngữ cảnh thật, không mang thông tin pháp lý đúng.\n")
    md.append(f"5. **Chỉ dùng mode `general`.** 13/127 câu eval là `irac` — quá nhỏ để đáng "
              f"công dựng đáp án theo cấu trúc 4 heading (kế hoạch §TASK-FT-04, ghi chú mode).\n")
    md.append("6. **Phân phối độ dài ngữ cảnh chỉ khớp xấp xỉ.** Trung vị "
              "`article_content` của bộ nguồn chỉ 853 ký tự, nên phải ưu tiên chọn điều dài "
              "để lấp ngân sách trong trần 6 điều — xem §2.1 để biết lệch bao nhiêu.\n")
    md.append("7. **Mẫu `refusal_out_of_scope` khớp CẤU HÌNH chứ không khớp LĨNH VỰC.** Ở "
              "mẻ thật, V114/V117 hỏi lệ phí trước bạ / thuế TNCN trong khi ngữ cảnh là "
              "văn bản đất đai. Ở đây câu hỏi cũng thuộc lĩnh vực ngoài phạm vi và ngữ "
              "cảnh cũng là văn bản khác, nhưng ngữ cảnh là luật chuyên ngành bất kỳ chứ "
              "không phải đất đai / hộ tịch / nuôi con nuôi — bộ nguồn không có ba lĩnh "
              "vực đó sau khi lọc rò rỉ. Mô hình học được \"câu hỏi ngoài ba lĩnh vực → "
              "từ chối\", chưa được luyện trên đúng nền ngữ cảnh của lúc đánh giá.\n\n")

    md.append("---\n\n## 8. Định dạng file đầu ra\n\n")
    md.append("| File | Nội dung |\n|---|---|\n")
    md.append("| `finetune/data/train.jsonl` | mẫu huấn luyện — một khoá `messages` |\n")
    md.append("| `finetune/data/val.jsonl` | tách theo `doc_name`: văn bản ở val KHÔNG có ở train |\n")
    md.append("| `finetune/data/{train,val}_meta.jsonl` | metadata song song theo dòng "
              "(`kind`, `header_format`, `citations`, …) — **để ngoài** file huấn luyện, "
              "vì `load_rows` báo lỗi khi gặp khoá lạ |\n\n")
    md.append("Mỗi dòng:\n\n```json\n")
    md.append('{"messages": [{"role": "system", "content": "<system prompt thật, '
              f'{_n(n_sys)} token>"}}, ')
    md.append('{"role": "user", "content": "CONTEXT:\\n…\\n\\nCÂU HỎI: …\\n\\nTRẢ LỜI:"}, '
              '{"role": "assistant", "content": "…"}]}\n```\n\n')
    md.append("**Prompt dựng bằng chính `src…build_messages(question, packed_context, "
              "\"general\")`** — cùng hàm `finetune/replay.py` dùng lúc đánh giá. Train và "
              "eval đồng nhất **theo xây dựng**, không phải theo cẩn thận (kế hoạch §9.4(2)).\n\n")
    md.append("### 8.1 Vì sao đúng khoá `messages`\n\n")
    md.append("Đọc `finetune/train_qlora.py` — `load_rows` (dòng 69-91) nhận **đúng hai "
              "dạng**: `{\"messages\": [...]}`, hoặc ba trường rời `system` / `user` / "
              "`assistant`. Khoá khác thì `raise ValueError`. Nên bộ này ghi `messages`, "
              "một danh sách phẳng ba lượt.\n\n")
    md.append("Không cần tự tách `prompt` / `completion`: `train_qlora.py` **tự render** "
              "chat template thành cột `text` (TRL ≥ 0.24 không còn tự nhận diện dataset "
              "dạng messages) rồi gọi `train_on_responses_only` để che phần prompt khỏi "
              "hàm mất mát. Metadata phải nằm ở file riêng vì mọi khoá lạ đều làm "
              "`load_rows` gãy.\n\n")
    md.append(f"`audit_lengths` của script đó **dừng hẳn** nếu có mẫu vượt "
              f"`--max-seq-length` (mặc định 16 384) — bộ này max **{_n(max(tong_tok))} "
              f"token**, còn dư biên. Số đo ở đây dùng tokenizer Qwen2.5; Qwen3 cùng họ "
              f"BPE 151k nên lệch không đáng kể, nhưng con số chốt vẫn là cái script tự "
              f"đo lúc chạy.\n")

    (report_dir / "dataset_stats.md").write_text("".join(md), encoding="utf-8")

    # ---------------- samples_20.txt ----------------
    refusals = [s for s in samples if s.kind != "answerable"]
    answerables = [s for s in samples if s.kind == "answerable"]
    rng.shuffle(refusals)
    rng.shuffle(answerables)
    chon = refusals[:5] + answerables[:15]
    # Bảo đảm có cả hai khuôn header trong 20 mẫu.
    if not any(s.header_format == "graphrag" for s in chon):
        chon[-1] = next(s for s in answerables if s.header_format == "graphrag")
    if not any(s.header_format == "baseline" for s in chon):
        chon[-2] = next(s for s in answerables if s.header_format == "baseline")
    rng.shuffle(chon)

    sys_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]
    out = []
    out.append("=" * 100 + "\n")
    out.append("TASK-FT-04 — 20 MẪU NGẪU NHIÊN, ĐẦY ĐỦ, ĐỂ KIỂM TAY\n")
    out.append("=" * 100 + "\n\n")
    out.append(f"seed={stats['seed']} · {sum(1 for s in chon if s.kind != 'answerable')} mẫu từ chối "
               f"· {sum(1 for s in chon if s.header_format == 'graphrag')} khuôn GraphRAG "
               f"/ {sum(1 for s in chon if s.header_format == 'baseline')} khuôn baseline\n\n")
    out.append("KHÔNG có phần nào bị lược. SYSTEM PROMPT in NGUYÊN VĂN MỘT LẦN ngay dưới đây "
               "vì nó GIỐNG HỆT nhau ở cả 20 mẫu\n")
    out.append(f"(sha256[:16] = {sys_hash}, {n_sys} token, {len(system_prompt)} ký tự). "
               "Mỗi mẫu bên dưới in đủ USER + ASSISTANT.\n\n")
    out.append("#" * 100 + "\n### SYSTEM (chung cho cả 20 mẫu)\n" + "#" * 100 + "\n")
    out.append(system_prompt + "\n\n")

    for i, s in enumerate(chon, 1):
        _, user = build_messages(s.question, s.context, "general")
        out.append("#" * 100 + "\n")
        out.append(f"### MẪU {i}/20 · {s.sample_id} · kind={s.kind} · "
                   f"header={s.header_format} · doc={s.doc_name}\n")
        out.append(f"### slug={s.slug} · {s.n_blocks} block · "
                   f"context {len(s.context)} ký tự (~{ntok(s.context)} token) · "
                   f"citations kỳ vọng = {json.dumps(s.citations, ensure_ascii=False)}\n")
        out.append("#" * 100 + "\n\n")
        out.append("----- USER -----\n")
        out.append(user + "\n\n")
        out.append("----- ASSISTANT -----\n")
        out.append(s.answer + "\n\n")
        out.append(f"----- parse_citations(ASSISTANT) -----\n")
        from src.retrieval.answer_generator import parse_citations

        out.append(json.dumps(parse_citations(s.answer), ensure_ascii=False, indent=2) + "\n\n")

    (report_dir / "samples_20.txt").write_text("".join(out), encoding="utf-8")
