"""TASK-FT-04 — Sinh dữ liệu huấn luyện QLoRA cho mô hình sinh cục bộ.

    thangvip/vietnamese-legal-qa (9 715 dòng / 29 145 cặp QA)
      → lọc rò rỉ (32 văn bản corpus + n-gram với 137 câu test_set_v2)
      → lọc độ dài
      → suy slug/Điều/Khoản CƠ KHÍ (finetune/slug.py, không LLM)
      → đóng gói 4-6 điều cùng văn bản, điều gold lẫn giữa distractor
      → dựng prompt bằng CHÍNH src…build_messages (cùng hàm replay.py dùng)
      → nối khối trích dẫn đúng cú pháp parse_citations đọc được
      → finetune/data/{train,val}.jsonl

Ba ràng buộc quyết định chất lượng bộ dữ liệu này (kế hoạch §TASK-FT-04):

1. **Dạy CHÉP TỪ NGỮ CẢNH, không dạy NHỚ.** Slug ở đây là slug tổng hợp, không
   có trong corpus 32 văn bản — nhưng nó LUÔN xuất hiện trong header ngữ cảnh
   của chính mẫu đó. Kỹ năng học được là "tìm block đúng, chép slug ở header ra
   khối trích dẫn", và kỹ năng đó chuyển giao sang 32 văn bản thật.
2. **Cả hai khuôn header, tỉ lệ cân bằng.** Chỉ dạy khuôn GraphRAG thì mô hình
   đọc cột Naive RAG kém hơn vì lý do ĐỊNH DẠNG → Δ ở hàng "cục bộ đã tinh
   chỉnh" phồng lên giả tạo (§9.2(4)).
3. **9% mẫu TỪ CHỐI** (70/30 giữa `no_basis` và `out_of_scope`). Bộ thangvip
   không có mẫu từ chối nào; 5 000 mẫu toàn câu trả lời được sẽ dạy mô hình
   "luôn luôn trả lời" — phiên 1 của FT-03 đã đo đúng hướng này: few-shot toàn
   ví dụ trả lời được kéo `tu_choi_dung` từ 0.667 (zero-shot) xuống 0.333.
   Nhưng chỉ **4/127** câu eval thật sự đi qua mô hình sinh ở nhánh phủ định,
   trong khi F1 cấp Khoản đo trên **123** câu → 20% từ chối là đem 123 câu ra
   đánh cược để bảo vệ 4 câu. Xem comment cạnh `FRAC_REFUSAL` và
   `reports/dataset_stats.md` §4.2.

Chạy:
    python -m finetune.build_dataset            # 5 000 mẫu, seed 42
    python -m finetune.build_dataset --n 200 --no-report    # thử nhanh
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# PHẢI đặt TRƯỚC khi import context_assembler — INCLUDE_SCHEMA_B đọc bằng
# os.getenv NGAY LÚC IMPORT MODULE (context_assembler.py:23). Train và eval phải
# dùng CÙNG hình dạng system prompt, nếu không là dạy một đằng chấm một nẻo.
# ---------------------------------------------------------------------------
os.environ["INCLUDE_SCHEMA_B"] = "false"

from src.baseline.naive_rag import fixed_chunker  # noqa: E402
from src.retrieval import context_assembler  # noqa: E402
from src.retrieval.answer_generator import parse_citations  # noqa: E402
from src.retrieval.context_assembler import build_messages  # noqa: E402

from finetune.slug import (  # noqa: E402
    build_slug_map,
    extract_so_hieu,
    normalize_doc_name,
    strip_diacritics,
)

assert context_assembler.INCLUDE_SCHEMA_B is False, (
    "INCLUDE_SCHEMA_B=True — system prompt khác lúc eval. context_assembler đã bị "
    "import ở đâu đó TRƯỚC khi build_dataset.py set env."
)

REPO = Path(__file__).resolve().parents[1]
RAW_DIR = REPO / "data/raw"
TEST_SET = REPO / "data/evaluation/test_set_v2.json"
OUT_DIR = REPO / "finetune/data"
REPORT_DIR = REPO / "finetune/reports"

HF_DATASET = "thangvip/vietnamese-legal-qa"

# ---------------------------------------------------------------------------
# Hằng số
# ---------------------------------------------------------------------------
SEED = 42
N_TOTAL = 5000
# 9% mẫu từ chối (450/5000), giữ tỉ lệ 70/30 no_basis / out_of_scope (xem dưới).
# Trước đây là 0.20 (1 000 mẫu). Lý do hạ:
#   Chỉ 4/127 câu eval thật sự đi qua mô hình sinh ở nhánh phủ định — 10/14 câu bẫy
#   do nhánh truy hồi RỖNG quyết định (`if not norm_ids`, pipeline.py:223), mô hình
#   chưa từng được gọi. Trong khi F1 cấp Khoản đo trên 123 câu. Huấn luyện 20% từ
#   chối là đem 123 câu ra đánh cược để bảo vệ 4 câu.
#   Vẫn nghiêng về `no_basis` vì V005 — ca no_basis DUY NHẤT trong eval — là ca mà
#   cả Gemini cũng trả lời quá đà (`negative_correct=False`); còn ba ca
#   `out_of_scope` được chi phối bởi danh sách chặn TƯỜNG MINH ở
#   src/retrieval/context_assembler.py:368-373 nên cần ít mẫu hơn để học.
FRAC_REFUSAL = 0.09      # kế hoạch mục D
FRAC_GRAPHRAG = 0.50     # kế hoạch mục C — hai khuôn header cân bằng
FRAC_VAL = 0.05          # tách theo doc_name: văn bản trong val không có ở train
RESPONSE_MODE = "general"  # 13/127 câu eval là irac — quá nhỏ để đáng dựng đáp án 4 heading

MIN_ARTICLE_CHARS = 200
MAX_ARTICLE_CHARS = 50_000
MAX_GOLD_CHARS = 8_000     # điều gold dài hơn thế thì một mình nó đã vượt ngân sách
MIN_PACK = 4               # kế hoạch: gộp 4-6 điều cùng doc_name
MAX_PACK = 6

# Độ dài context mục tiêu — token_budget.md §2.7.2 (token Qwen2.5), quy ra ký tự
# bằng 2.87 ký tự/token (token_budget.md §2.3). KHÔNG dùng CHARS_PER_TOKEN=3.5
# của context_assembler: hằng số đó đánh giá thấp số token thật.
CHARS_PER_TOKEN = 2.87
# Mốc mục tiêu đặt CAO HƠN mốc muốn đạt: trung vị `article_content` của bộ nguồn
# chỉ 853 ký tự, nhiều văn bản không có đủ điều dài để lấp đầy ngân sách trong
# trần 6 điều → phân phối thực tế luôn nằm dưới mốc đặt ra.
TARGET_GRAPHRAG_TOK = [(0.45, 2800, 4200), (0.45, 4200, 7000), (0.10, 7000, 8000)]
# Hệ số 2.87 ký tự/token đo trên context GraphRAG; chunk baseline giữ nguyên
# heading markdown của data/raw nên "đặc" hơn (~3.3 ký tự/token) → mốc đặt theo
# ký tự phải nâng lên tương ứng, nếu không p50 hụt ~15% (đã đo ở mẻ trước).
TARGET_BASELINE_TOK = [(0.50, 1350, 2060), (0.45, 2060, 2600), (0.05, 2600, 2800)]

# Trần cứng cho phần context. Block của điều gold luôn được giữ bất kể ngân sách
# (bỏ nó đi thì trích dẫn mất chỗ bám), nên một điều gold dài có thể đẩy ngữ cảnh
# vượt xa mục tiêu → chặn ở đây và bỏ mẫu, để bộ sinh thử cặp QA khác.
HARD_MAX_CTX_CHARS = int(8_400 * 2.87)

# Tỉ lệ tái tạo hai biến thể của khuôn GraphRAG (api_contract.md §6.1-6.2).
# CHỈ áp lên block distractor → không bao giờ mâu thuẫn với đáp án gold.
P_HET_HIEU_LUC = 0.05   # 45/2199 header thực tế
P_AMENDMENT = 0.40      # 104/137 item thực tế có ít nhất một block cảnh báo

# ---------------------------------------------------------------------------
# Hai chuỗi TỪ CHỐI — NGUYÊN VĂN, không tự chế
# ---------------------------------------------------------------------------
# (1) Rào phạm vi corpus. Nguyên văn field `answer` của V105 / V114 / V117 trong
#     results_graphrag_20260710-085236.json — ba câu byte-identical, ĐÃ đi qua mô
#     hình sinh và từ chối đúng. Cũng chính là câu bắt buộc ở
#     src/retrieval/context_assembler.py:373.
REFUSAL_OUT_OF_SCOPE = (
    "Câu hỏi này không thuộc phạm vi tài liệu pháp luật mà hệ thống đang lập chỉ "
    "mục (đất đai, hộ tịch, nuôi con nuôi). Vui lòng tham khảo các văn bản pháp "
    "luật chuyên ngành tương ứng."
)
# (2) Thiếu căn cứ trong CONTEXT. Nguyên văn quy tắc bắt buộc ở
#     src/retrieval/context_assembler.py:379. Đây là ca mà mục D dựng ra: ngữ cảnh
#     CÓ tài liệu liên quan nhưng KHÔNG đủ để kết luận.
REFUSAL_NO_BASIS = "Tôi không đủ thông tin để cung cấp câu trả lời chính xác cho bạn."

# KHÔNG dùng hằng số ở src/pipeline.py:233 ("Không tìm thấy văn bản pháp luật liên
# quan đến câu hỏi này.") — đó là nhánh truy hồi RỖNG, mô hình sinh chưa từng được
# gọi (api_contract.md §7.1). Khác ca hoàn toàn.

# Lĩnh vực mà system prompt liệt kê là NGOÀI PHẠM VI (context_assembler.py:367-371).
# Văn bản rơi vào đây bị loại KHỎI pool trả lời được và CHỈ dùng cho mẫu từ chối
# loại out-of-scope → giám sát nhất quán, không có hai nhãn trái nhau trên cùng
# một bề mặt đầu vào.
OUT_OF_SCOPE_KEYWORDS = [
    "cong chung", "thue", "chung khoan", "kinh doanh bao hiem", "bao hiem tien gui",
    "to chuc tin dung", "ngan hang", "doanh nghiep", "dau tu", "dau gia", "dau thau",
    "cong doan", "lao dong", "to tung", "thi hanh an", "xu ly vi pham hanh chinh",
    "dac xa", "tam giu", "trong tai thuong mai", "no cong", "chung khoan",
]

# ---------------------------------------------------------------------------
# Regex phân rã văn bản
# ---------------------------------------------------------------------------
_DIEU_HEAD_RE = re.compile(r"^\s*Điều\s+(\d+[a-zđ]?)\s*[\.\:]\s*(.*)$")
_KHOAN_RE = re.compile(r"^\s*(\d{1,2})\.\s+(.*)$")
_DIEM_RE = re.compile(r"^\s*([a-zđ])\)\s+(.*)$")

_ANS_DIEU_RE = re.compile(r"[Đđ]iều\s+(\d+[a-zđ]?)")
_ANS_KHOAN_RE = re.compile(r"[Kk]hoản\s+(\d{1,2})")
_ANS_DIEM_RE = re.compile(r"[Đđ]iểm\s+([a-zđ])\b")

# "Theo Khoản 1 Điều 5 Luật X, ..." / "Theo quy định tại Điều 12 Luật Y, ..."
_OPENER_RE = re.compile(
    r"^Theo\s+(?:quy\s+định\s+(?:tại\s+)?)?"
    r"(?:khoản|điểm|điều|Khoản|Điểm|Điều)[^,\.]{0,150},\s*"
)

DROP_REASONS = [
    "leak_doc_corpus",
    "leak_question_ngram",
    "khong_suy_duoc_slug",
    "article_qua_dai",
    "article_qua_ngan",
    "qa_co_ngoac_vuong",
    "qa_khong_suy_duoc_dieu",
    "qa_khoan_khong_ton_tai",
    "doc_ngoai_pham_vi",
    "doc_thieu_dieu_de_dong_goi",
]


# ---------------------------------------------------------------------------
# Cấu trúc trung gian
# ---------------------------------------------------------------------------
@dataclass
class Article:
    doc_name: str
    slug: str
    dieu: str
    tieu_de: str
    # [(khoan_no|None, text, {diem: text})] — khoan_no None = đoạn mở đầu không đánh số
    khoan: list[tuple[str | None, str, dict[str, str]]]
    raw: str

    @property
    def khoan_set(self) -> set[str]:
        return {k for k, _, _ in self.khoan if k}

    @property
    def n_chars(self) -> int:
        return len(self.raw)


@dataclass
class Sample:
    sample_id: str
    doc_name: str
    slug: str
    header_format: str          # "graphrag" | "baseline"
    kind: str                   # "answerable" | "refusal_no_basis" | "refusal_out_of_scope"
    question: str
    context: str
    answer: str
    citations: list[dict]       # kỳ vọng của parse_citations(answer)
    n_blocks: int
    difficulty: str = ""
    question_type: str = ""
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Bước 1 — lọc rò rỉ
# ---------------------------------------------------------------------------
def load_blocklist() -> tuple[set[str], set[str], list[dict]]:
    """Đọc frontmatter `id` + `title` của data/raw/*.md → danh sách 32 văn bản.

    Trả (tên chuẩn hoá bị chặn, số hiệu bị chặn, bảng chi tiết để in báo cáo).
    """
    blocked_names: set[str] = set()
    blocked_so_hieu: set[str] = set()
    rows: list[dict] = []
    for path in sorted(RAW_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue  # mapping_table.md / review_log.md / crossref_decisions.md
        fm = text.split("---", 2)[1]
        meta = {
            k: v.strip().strip('"')
            for k, v in re.findall(r"^(\w+):\s*(.*)$", fm, re.M)
        }
        norm_id = meta.get("id", "")
        title = meta.get("title", "")
        if not norm_id:
            continue

        # Khoá 1 — số hiệu pháp lý trong title ("Nghị định 102/2024/NĐ-CP").
        so_hieu = extract_so_hieu(title)
        if so_hieu:
            blocked_so_hieu.add(so_hieu)

        # Khoá 2 — tên văn bản đã bỏ số/năm: "Luật Đất đai 2013" -> "luat dat dai".
        name = normalize_doc_name(title)
        name = re.sub(r"\b\d[\d/a-z-]*\b", " ", name)
        name = re.sub(r"\b(nghi dinh|nghi quyet|thong tu|quyet dinh|so)\b", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        if len(name.split()) >= 2:
            blocked_names.add(name)

        rows.append({"id": norm_id, "title": title, "so_hieu": so_hieu, "ten_chan": name})
    return blocked_names, blocked_so_hieu, rows


def doc_bi_ro_ri(doc_name: str, blocked_names: set[str], blocked_so_hieu: set[str]) -> str | None:
    """Trả lý do chặn, hoặc None nếu văn bản sạch."""
    norm = normalize_doc_name(doc_name)
    so_hieu = extract_so_hieu(doc_name)
    if so_hieu and so_hieu in blocked_so_hieu:
        return f"trung so hieu {so_hieu}"
    for name in blocked_names:
        if name and name in norm:
            return f"trung ten '{name}'"
    return None


def _ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    toks = strip_diacritics(text).lower()
    toks = re.sub(r"[^a-z0-9\s]", " ", toks).split()
    return {tuple(toks[i : i + n]) for i in range(len(toks) - n + 1)}


def load_test_question_ngrams(n: int = 5) -> tuple[set[tuple[str, ...]], list[set[str]]]:
    data = json.loads(TEST_SET.read_text(encoding="utf-8"))
    grams: set[tuple[str, ...]] = set()
    token_sets: list[set[str]] = []
    for item in data:
        q = item["question"]
        grams |= _ngrams(q, n)
        toks = set(re.sub(r"[^a-z0-9\s]", " ", strip_diacritics(q).lower()).split())
        token_sets.append(toks)
    return grams, token_sets


def question_bi_ro_ri(
    question: str,
    test_grams: set[tuple[str, ...]],
    test_tokens: list[set[str]],
    jaccard_max: float = 0.6,
) -> str | None:
    if _ngrams(question, 5) & test_grams:
        return "trung 5-gram voi test_set_v2"
    toks = set(re.sub(r"[^a-z0-9\s]", " ", strip_diacritics(question).lower()).split())
    if not toks:
        return "cau hoi rong"
    for ref in test_tokens:
        inter = len(toks & ref)
        union = len(toks | ref)
        if union and inter / union >= jaccard_max:
            return f"jaccard >= {jaccard_max} voi test_set_v2"
    return None


def la_ngoai_pham_vi(doc_name: str) -> bool:
    norm = normalize_doc_name(doc_name)
    return any(kw in norm for kw in OUT_OF_SCOPE_KEYWORDS)


# ---------------------------------------------------------------------------
# Bước 3 — phân rã Điều / Khoản / Điểm (cơ khí)
# ---------------------------------------------------------------------------
def parse_article(doc_name: str, slug: str, content: str) -> Article | None:
    lines = content.split("\n")
    m = _DIEU_HEAD_RE.match(lines[0])
    if not m:
        return None
    dieu, tieu_de = m.group(1), m.group(2).strip()

    khoan: list[tuple[str | None, str, dict[str, str]]] = []
    cur_no: str | None = None
    cur_lines: list[str] = []
    cur_diem: dict[str, str] = {}
    cur_diem_key: str | None = None

    def flush() -> None:
        text = "\n".join(cur_lines).strip()
        if text or cur_diem:
            khoan.append((cur_no, text, dict(cur_diem)))

    for line in lines[1:]:
        km = _KHOAN_RE.match(line)
        if km:
            flush()
            cur_no, cur_lines, cur_diem, cur_diem_key = km.group(1), [km.group(2)], {}, None
            continue
        dm = _DIEM_RE.match(line)
        if dm and cur_no is not None:
            cur_diem_key = dm.group(1)
            cur_diem[cur_diem_key] = dm.group(2)
            cur_lines.append(line.strip())
            continue
        if line.strip():
            cur_lines.append(line.strip())
            if cur_diem_key:
                cur_diem[cur_diem_key] += " " + line.strip()
    flush()

    if not khoan:
        return None
    return Article(doc_name, slug, dieu, tieu_de, khoan, content.strip())


def suy_citation(answer: str, art: Article) -> list[dict] | None:
    """Suy (Điều, Khoản, Điểm) từ prose của `answer`. None = không dùng được mẫu.

    Không suy được Khoản thì GIỮ Ở CẤP ĐIỀU, không bịa.
    """
    dieu_hits = {d for d in _ANS_DIEU_RE.findall(answer)}
    if dieu_hits and dieu_hits != {art.dieu}:
        # Đáp án nhắc tới Điều khác Điều nguồn → không chắc trích dẫn thuộc về đâu.
        return None

    khoan_hits = [k for k in _ANS_KHOAN_RE.findall(answer) if k in art.khoan_set]
    khoan_hits = list(dict.fromkeys(khoan_hits))[:2]

    if not khoan_hits:
        return [{"dieu": art.dieu, "khoan": None, "diem": None, "tiet": None,
                 "van_ban": art.slug, "loai": "dieu"}]

    diem: str | None = None
    if len(khoan_hits) == 1:
        # Chỉ gán Điểm khi KHÔNG mơ hồ: đúng một Khoản và Điểm đó có thật trong Khoản đó.
        diem_hits = _ANS_DIEM_RE.findall(answer)
        diem_map = next((d for k, _, d in art.khoan if k == khoan_hits[0]), {})
        valid = [d for d in dict.fromkeys(diem_hits) if d in diem_map]
        if len(valid) == 1:
            diem = valid[0]

    out = []
    for i, k in enumerate(khoan_hits):
        out.append({"dieu": art.dieu, "khoan": k, "diem": diem if i == 0 else None,
                    "tiet": None, "van_ban": art.slug, "loai": "dieu"})
    return out


# ---------------------------------------------------------------------------
# Bước 4-5 — đóng gói ngữ cảnh + dựng đáp án
# ---------------------------------------------------------------------------
def fmt_citation(c: dict) -> str:
    """(dieu, khoan, diem, van_ban) → khối trích dẫn parse_citations đọc được.

    Cú pháp đích api_contract.md §3.2, xác minh trên 401/401 khối thực tế:
    phân cách `, `, "Văn bản" luôn CUỐI, giá trị là slug. KHÔNG dùng `Tiết`
    (0/401 khối) và KHÔNG dùng `Mục`/`Dòng`/`Phần` (parser bỏ qua im lặng).
    """
    parts = [f"Điều {c['dieu']}"]
    if c.get("khoan"):
        parts.append(f"Khoản {c['khoan']}")
    if c.get("diem"):
        parts.append(f"Điểm {c['diem']}")
    parts.append(f"Văn bản {c['van_ban']}")
    return "[" + ", ".join(parts) + "]"


_OPENERS = [
    None,                                   # giữ nguyên câu mở đầu gốc ("Theo …")
    "",                                     # bỏ hẳn, vào thẳng nội dung
    "Căn cứ quy định hiện hành, ",
    "Pháp luật hiện hành quy định như sau: ",
    "Quy định pháp luật xác định rằng ",
    "Trả lời câu hỏi của bạn: ",
]


def da_dang_hoa_mo_dau(answer: str, rng: random.Random) -> str:
    """Gần như đáp án nào trong bộ nguồn cũng bắt đầu bằng "Theo…" — mô hình sẽ
    nhiễm tic đó. Thay bằng một trong sáu câu mở đầu, cơ khí và tất định."""
    opener = rng.choice(_OPENERS)
    if opener is None:
        return answer
    m = _OPENER_RE.match(answer)
    if not m:
        return answer
    rest = answer[m.end():].strip()
    if not rest:
        return answer
    if opener == "":
        return rest[0].upper() + rest[1:]
    return opener + rest[0].lower() + rest[1:]


def _block_text_graphrag(art: Article, khoan_no: str | None, khoan_text: str) -> tuple[str, str]:
    """Trả (đường dẫn cho header, phần thân) đúng khuôn assemble_context."""
    if khoan_no:
        path = f"Điều {art.dieu}. {art.tieu_de}, Khoản {khoan_no}."
        body = f"Điều {art.dieu}. {art.tieu_de}\nKhoản {khoan_no}.\n{khoan_text}"
    else:
        path = f"Điều {art.dieu}. {art.tieu_de}"
        body = f"Điều {art.dieu}. {art.tieu_de}\n{khoan_text}"
    return path, body


_AMEND_SUMMARIES = [
    'bãi bỏ cụm từ ", thị trấn"',
    'thay từ "cơ quan" bằng cụm từ "cơ quan có thẩm quyền"',
    "bổ sung quy định về thời hạn giải quyết hồ sơ",
    "sửa đổi mức thu áp dụng từ ngày có hiệu lực",
]


def _amendment_warning(rng: random.Random, year: int) -> str:
    """Khuôn NGUYÊN VĂN của `_format_amendments_warning` (context_assembler.py:145-167).

    Nội dung là TỔNG HỢP — chỉ để mô hình quen bề mặt chuỗi này (có ở 104/137 item
    ngữ cảnh thật). Luôn gắn vào block DISTRACTOR nên không mâu thuẫn đáp án gold.
    """
    so = f"{rng.randint(10, 250)}/{year + rng.randint(0, 2)}/NĐ-CP"
    loc = f"khoản {rng.randint(1, 6)} Điều {rng.randint(1, 20)}"
    date = f"{year + rng.randint(0, 2)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
    return (
        "[AMENDMENT WARNING — nội dung Component này đã/sắp bị sửa đổi:]\n"
        f"  - {so} ({loc}, hiệu lực {date}): {rng.choice(_AMEND_SUMMARIES)}"
    )


def pack_graphrag(
    arts: list[Article], gold_idx: int, year: int, target_chars: int, rng: random.Random
) -> tuple[str, int]:
    """Ngữ cảnh khuôn GraphRAG (api_contract.md §6.1).

        --- [Tier 1 | Hiệu lực: YYYY-MM-DD] Điều N. Tên, Khoản K. (slug) ---
        <thân>
    """
    valid_from = f"{year}-01-01"
    het_hieu_luc_idx = -1
    if rng.random() < P_HET_HIEU_LUC:
        others = [i for i in range(len(arts)) if i != gold_idx]
        if others:
            het_hieu_luc_idx = rng.choice(others)
    amend_idx = -1
    if rng.random() < P_AMENDMENT:
        others = [i for i in range(len(arts)) if i != gold_idx]
        if others:
            amend_idx = rng.choice(others)

    blocks: list[str] = []
    used = 0
    for i, art in enumerate(arts):
        if i == het_hieu_luc_idx:
            meta = f"Tier 1 | Hiệu lực: {valid_from} → {year + rng.randint(3, 8)}-01-01 (HẾT HIỆU LỰC)"
        else:
            meta = f"Tier 1 | Hiệu lực: {valid_from}"
        for kh_no, kh_text, _ in art.khoan:
            if not kh_text.strip():
                continue
            path, body = _block_text_graphrag(art, kh_no, kh_text)
            if i == amend_idx and kh_no == art.khoan[0][0]:
                body = _amendment_warning(rng, year) + "\n" + body
            block = f"--- [{meta}] {path} ({art.slug}) ---\n{body}"
            # Block của điều gold LUÔN được giữ; distractor mới bị ngân sách chặn.
            if used + len(block) > target_chars and i != gold_idx and blocks:
                continue
            blocks.append(block)
            used += len(block) + 2
    return "\n\n".join(blocks), len(blocks)


def _markdown_body(art: Article) -> str:
    """Thân văn bản theo đúng dạng data/raw/*.md — baseline chunk trên chuỗi này."""
    out = [f"## Điều {art.dieu}. {art.tieu_de}", ""]
    for kh_no, kh_text, _ in art.khoan:
        if kh_no:
            out += [f"### Khoản {kh_no}.", "", kh_text, ""]
        elif kh_text.strip():
            out += [kh_text, ""]
    return "\n".join(out)


def pack_baseline(
    arts: list[Article], gold_idx: int, gold_khoan: str | None,
    target_chars: int, rng: random.Random
) -> tuple[str, int]:
    """Ngữ cảnh khuôn baseline (api_contract.md §6.3).

        --- Văn bản: slug, chunk i ---
        <512 ký tự thô, cắt giữa từ>

    Dùng CHÍNH `fixed_chunker` của src/baseline/naive_rag.py (512/50), không viết lại.
    """
    body = "\n\n".join(_markdown_body(a) for a in arts)
    chunks = fixed_chunker(body)
    if not chunks:
        return "", 0

    # Chunk nào chứa Khoản gold — phải có mặt, nếu không trích dẫn không grounded.
    gold_art = arts[gold_idx]
    if gold_khoan:
        needle = f"### Khoản {gold_khoan}."
    else:
        needle = f"## Điều {gold_art.dieu}."
    must = [i for i, c in enumerate(chunks) if needle in c]
    if not must:
        must = [i for i, c in enumerate(chunks) if f"Điều {gold_art.dieu}." in c][:1]
    keep = set(must[:2])
    # Chunk kề ngay sau chunk gold: nội dung của Khoản thường tràn sang.
    for i in list(keep):
        if i + 1 < len(chunks):
            keep.add(i + 1)

    pool = [i for i in range(len(chunks)) if i not in keep]
    rng.shuffle(pool)
    used = sum(len(chunks[i]) + 45 for i in keep)
    for i in pool:
        if used + len(chunks[i]) + 45 > target_chars:
            continue
        keep.add(i)
        used += len(chunks[i]) + 45

    slug = gold_art.slug
    blocks = [f"--- Văn bản: {slug}, chunk {i} ---\n{chunks[i]}" for i in sorted(keep)]
    return "\n\n".join(blocks), len(blocks)


def _pick_target(spec: list[tuple[float, int, int]], rng: random.Random) -> int:
    r = rng.random()
    acc = 0.0
    for w, lo, hi in spec:
        acc += w
        if r <= acc:
            return int(rng.uniform(lo, hi) * CHARS_PER_TOKEN)
    lo, hi = spec[-1][1], spec[-1][2]
    return int(rng.uniform(lo, hi) * CHARS_PER_TOKEN)


def chon_pack(
    pool: list[Article], gold: Article, target_chars: int, rng: random.Random
) -> list[Article]:
    """Chọn 4-6 điều CÙNG văn bản, ưu tiên tổ hợp có tổng độ dài gần mục tiêu.

    Trung vị `article_content` của bộ nguồn chỉ 853 ký tự — gộp 4 điều ngẫu nhiên
    ra ~3 400 ký tự (~1 200 token), thấp hơn nhiều so với p50 4 200 token của ngữ
    cảnh thật. Nên ưu tiên điều DÀI trước, vẫn giữ trần 6 điều của kế hoạch.
    """
    others = [a for a in pool if a is not gold]
    rng.shuffle(others)
    others.sort(key=lambda a: -a.n_chars)
    chosen = [gold]
    used = gold.n_chars
    for a in others:
        if len(chosen) >= MAX_PACK:
            break
        if used >= target_chars and len(chosen) >= MIN_PACK:
            break
        chosen.append(a)
        used += a.n_chars
    rng.shuffle(chosen)  # điều gold lẫn giữa distractor ở vị trí NGẪU NHIÊN
    return chosen


# ---------------------------------------------------------------------------
# Dựng mẫu hoàn chỉnh
# ---------------------------------------------------------------------------
def dung_answer(prose: str, cits: list[dict], rng: random.Random) -> str:
    text = da_dang_hoa_mo_dau(prose.strip(), rng).rstrip()
    text = text.rstrip(".").rstrip()
    cite_str = " ".join(fmt_citation(c) for c in cits)
    return f"{text} {cite_str}."


def to_record(s: Sample) -> dict:
    """Một dòng jsonl đúng định dạng `finetune/train_qlora.py` nhận.

    `load_rows` ([train_qlora.py:69-91](train_qlora.py)) chấp nhận đúng hai dạng:
    `{"messages": [...]}` hoặc ba trường rời `system` / `user` / `assistant`;
    khoá khác thì `raise ValueError`. Dùng `messages` — một danh sách phẳng.

    Không cần tách `prompt` / `completion`: `train_qlora.py` tự render chat
    template (TRL >= 0.24 không còn tự nhận diện dataset dạng messages) rồi dùng
    `train_on_responses_only` để che phần prompt khỏi hàm mất mát.
    """
    system, user = build_messages(s.question, s.context, RESPONSE_MODE)
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": s.answer},
        ]
    }


# ---------------------------------------------------------------------------
# Pipeline chính
# ---------------------------------------------------------------------------
def build(n_total: int = N_TOTAL, seed: int = SEED) -> tuple[list[Sample], dict]:
    from datasets import load_dataset

    rng = random.Random(seed)
    drops: Counter = Counter()

    blocked_names, blocked_so_hieu, block_rows = load_blocklist()
    test_grams, test_tokens = load_test_question_ngrams()
    print(f"blocklist: {len(block_rows)} văn bản corpus, "
          f"{len(blocked_names)} khoá tên, {len(blocked_so_hieu)} số hiệu")

    ds = load_dataset(HF_DATASET)["train"]
    slug_map = build_slug_map(list(ds["doc_name"]))
    print(f"nguồn: {len(ds)} dòng, {len(set(ds['doc_name']))} doc_name, "
          f"{len(slug_map)} suy được slug")

    # ---- lọc + phân rã ----
    by_doc: dict[str, list[Article]] = defaultdict(list)
    qa_pool: list[tuple[Article, dict]] = []
    doc_leak_reason: dict[str, str] = {}
    docs_out_of_scope: set[str] = set()

    for row in ds:
        doc = row["doc_name"]
        if doc not in slug_map:
            drops["khong_suy_duoc_slug"] += 1
            continue
        if doc not in doc_leak_reason:
            doc_leak_reason[doc] = doc_bi_ro_ri(doc, blocked_names, blocked_so_hieu) or ""
        if doc_leak_reason[doc]:
            drops["leak_doc_corpus"] += 1
            continue

        content = row["article_content"]
        if len(content) > MAX_ARTICLE_CHARS:
            drops["article_qua_dai"] += 1
            continue
        if len(content) < MIN_ARTICLE_CHARS:
            drops["article_qua_ngan"] += 1
            continue

        art = parse_article(doc, slug_map[doc], content)
        if art is None:
            drops["article_qua_ngan"] += 1
            continue
        by_doc[doc].append(art)

        if la_ngoai_pham_vi(doc):
            docs_out_of_scope.add(doc)

        for qa in row["generated_qa_pairs"]:
            q, a = (qa.get("question") or "").strip(), (qa.get("answer") or "").strip()
            if not q or not a:
                continue
            if "[" in a or "]" in a or "[" in q or "]" in q:
                # Ngoặc vuông trong prose sẽ được parse_citations bắt như một khối
                # → phá round-trip. Bỏ hẳn, rẻ hơn là đi vá.
                drops["qa_co_ngoac_vuong"] += 1
                continue
            reason = question_bi_ro_ri(q, test_grams, test_tokens)
            if reason:
                drops["leak_question_ngram"] += 1
                continue
            cits = suy_citation(a, art)
            if cits is None:
                drops["qa_khong_suy_duoc_dieu"] += 1
                continue
            qa_pool.append((art, {"question": q, "answer": a, "citations": cits,
                                  "difficulty": qa.get("difficulty", ""),
                                  "question_type": qa.get("question_type", "")}))

    # Văn bản không đủ điều để đóng gói.
    for doc, arts in list(by_doc.items()):
        if len(arts) < MIN_PACK:
            drops["doc_thieu_dieu_de_dong_goi"] += len(arts)
            del by_doc[doc]
    qa_pool = [(a, q) for a, q in qa_pool if a.doc_name in by_doc]

    # Văn bản ngoài phạm vi: CHỈ dùng cho mẫu từ chối out-of-scope.
    qa_in_scope = [(a, q) for a, q in qa_pool if a.doc_name not in docs_out_of_scope]
    qa_out_scope = [(a, q) for a, q in qa_pool if a.doc_name in docs_out_of_scope]
    drops["doc_ngoai_pham_vi"] += len(qa_out_scope)

    print(f"sau lọc: {len(by_doc)} văn bản, {len(qa_pool)} cặp QA dùng được "
          f"({len(qa_in_scope)} trong phạm vi / {len(qa_out_scope)} ngoài phạm vi)")

    # ---- sinh mẫu ----
    n_refusal = int(round(n_total * FRAC_REFUSAL))
    n_answerable = n_total - n_refusal
    # 70/30 giữa no_basis và out_of_scope — GIỮ NGUYÊN khi đổi FRAC_REFUSAL.
    n_refusal_oos = min(int(round(n_refusal * 0.30)), len(qa_out_scope))
    n_refusal_nb = n_refusal - n_refusal_oos

    rng.shuffle(qa_in_scope)
    rng.shuffle(qa_out_scope)

    samples: list[Sample] = []
    used_in_scope = 0

    docs_in_scope = sorted({a.doc_name for a, _ in qa_in_scope})

    def make(idx: int, art: Article, qa: dict, kind: str, graphrag: bool) -> Sample | None:
        spec = TARGET_GRAPHRAG_TOK if graphrag else TARGET_BASELINE_TOK
        target = _pick_target(spec, rng)

        if kind == "refusal_out_of_scope":
            # Tái tạo ĐÚNG cấu hình của V105 / V114 / V117: câu hỏi thuộc lĩnh vực
            # NGOÀI phạm vi corpus, còn ngữ cảnh là văn bản KHÁC mà hệ thống có lập
            # chỉ mục. Đóng gói cùng văn bản với câu hỏi sẽ dạy sai — ở mẻ thật,
            # truy hồi trả về đất đai trong khi câu hỏi hỏi về thuế/lệ phí.
            if not docs_in_scope:
                return None
            ctx_doc = rng.choice(docs_in_scope)
            pool = by_doc[ctx_doc]
            fake_gold = max(pool, key=lambda a: a.n_chars)
            arts = chon_pack(pool, fake_gold, target, rng)
            gold_idx = arts.index(fake_gold)
            cits = []
            answer = REFUSAL_OUT_OF_SCOPE
        elif kind == "answerable":
            if art.n_chars > MAX_GOLD_CHARS:
                return None
            pool = by_doc[art.doc_name]
            arts = chon_pack(pool, art, target, rng)
            gold_idx = arts.index(art)
            cits = qa["citations"]
            answer = dung_answer(qa["answer"], cits, rng)
        else:
            # Mục D: đóng gói 4-6 điều CÙNG văn bản nhưng LOẠI ĐIỀU GOLD RA.
            # Ngữ cảnh có tài liệu liên quan mà không đủ để kết luận.
            pool = by_doc[art.doc_name]
            others = [a for a in pool if a is not art]
            if len(others) < MIN_PACK:
                return None
            fake_gold = others[0]
            arts = chon_pack(others, fake_gold, target, rng)
            if art in arts:
                return None
            gold_idx = arts.index(fake_gold)
            cits = []
            answer = REFUSAL_NO_BASIS

        art_ctx = arts[gold_idx]
        year_tail = art_ctx.slug.rsplit("-", 1)[-1]
        year = int(year_tail) if year_tail.isdigit() else 2020

        if graphrag:
            ctx, n_blocks = pack_graphrag(arts, gold_idx, year, target, rng)
        else:
            gold_khoan = cits[0]["khoan"] if cits else None
            ctx, n_blocks = pack_baseline(arts, gold_idx, gold_khoan, target, rng)
        if not ctx or len(ctx) > HARD_MAX_CTX_CHARS:
            return None

        # Điều gold phải THẬT SỰ vắng mặt trong ngữ cảnh của mẫu "thiếu căn cứ".
        # (Với mẫu ngoài phạm vi thì ngữ cảnh vốn đã thuộc văn bản khác hẳn.)
        if kind == "refusal_no_basis" and f"Điều {art.dieu}." in ctx:
            return None
        # Ngược lại: mẫu trả lời được PHẢI có điều gold trong ngữ cảnh, nếu không
        # là đang dạy mô hình trích dẫn thứ nó không nhìn thấy.
        if kind == "answerable" and f"Điều {art.dieu}." not in ctx:
            return None

        return Sample(
            sample_id=f"FT{idx:05d}",
            doc_name=art_ctx.doc_name if kind == "refusal_out_of_scope" else art.doc_name,
            slug=art_ctx.slug if kind == "refusal_out_of_scope" else art.slug,
            header_format="graphrag" if graphrag else "baseline",
            kind=kind,
            question=qa["question"],
            context=ctx,
            answer=answer,
            citations=cits,
            n_blocks=n_blocks,
            difficulty=qa.get("difficulty", ""),
            question_type=qa.get("question_type", ""),
            meta={
                "dieu_gold": art.dieu,
                "doc_cau_hoi": art.doc_name,   # khác doc_name khi kind=refusal_out_of_scope
                "n_dieu_pack": len(arts),
                "target_chars": target,
            },
        )

    plan: list[tuple[str, int]] = (
        [("answerable", 1)] * n_answerable
        + [("refusal_no_basis", 1)] * n_refusal_nb
        + [("refusal_out_of_scope", 1)] * n_refusal_oos
    )
    rng.shuffle(plan)

    oos_cursor = 0
    idx = 0
    for i_plan, (kind, _) in enumerate(plan):
        if i_plan % 250 == 0:
            print(f"  sinh mẫu: {i_plan}/{len(plan)}", end="\r")
        graphrag = rng.random() < FRAC_GRAPHRAG
        for _try in range(12):
            if kind == "refusal_out_of_scope":
                if not qa_out_scope:
                    break
                art, qa = qa_out_scope[oos_cursor % len(qa_out_scope)]
                oos_cursor += 1
            else:
                if not qa_in_scope:
                    break
                art, qa = qa_in_scope[used_in_scope % len(qa_in_scope)]
                used_in_scope += 1
            s = make(idx, art, qa, kind, graphrag)
            if s is not None:
                samples.append(s)
                idx += 1
                break

    stats = {
        "seed": seed,
        "n_yeu_cau": n_total,
        "drops": dict(drops),
        "blocklist": block_rows,
        "n_doc_sau_loc": len(by_doc),
        "n_qa_dung_duoc": len(qa_pool),
        "n_qa_trong_pham_vi": len(qa_in_scope),
        "n_qa_ngoai_pham_vi": len(qa_out_scope),
        "doc_ngoai_pham_vi": sorted(docs_out_of_scope),
    }
    return samples, stats


# ---------------------------------------------------------------------------
# Kiểm tra bắt buộc (DoD 2 + 3)
# ---------------------------------------------------------------------------
def kiem_tra(samples: list[Sample], blocked_names: set[str], blocked_so_hieu: set[str]) -> None:
    # DoD 2 — 0 mẫu còn khớp danh sách chặn.
    for s in samples:
        assert doc_bi_ro_ri(s.doc_name, blocked_names, blocked_so_hieu) is None, (
            f"{s.sample_id}: doc_name còn khớp blocklist — {s.doc_name}"
        )

    # DoD 3 — 100% khối trích dẫn parse được VÀ round-trip đúng (Điều, Khoản, Điểm, slug).
    for s in samples:
        got = parse_citations(s.answer)
        assert got == s.citations, (
            f"{s.sample_id}: round-trip SAI\n  dựng : {s.citations}\n  parse: {got}\n"
            f"  answer: {s.answer[:300]}"
        )
        if s.kind == "answerable":
            assert got, f"{s.sample_id}: mẫu trả lời được mà parse ra 0 citation"
            for c in got:
                assert c["van_ban"] == s.slug
                # Slug PHẢI có trong ngữ cảnh — nếu không thì đang dạy mô hình bịa
                # slug từ trí nhớ, lỗi thiết kế nặng nhất của task này.
                assert c["van_ban"] in s.context, (
                    f"{s.sample_id}: slug {c['van_ban']} KHÔNG có trong context"
                )
                # Điều được trích PHẢI xuất hiện trong ngữ cảnh.
                assert f"Điều {c['dieu']}." in s.context, (
                    f"{s.sample_id}: Điều {c['dieu']} KHÔNG có trong context"
                )
        else:
            assert got == [], f"{s.sample_id}: mẫu từ chối mà vẫn sinh citation"


# ---------------------------------------------------------------------------
# Ghi file
# ---------------------------------------------------------------------------
def tach_train_val(samples: list[Sample], rng: random.Random) -> tuple[list[Sample], list[Sample]]:
    """Tách theo `doc_name`: văn bản xuất hiện ở val KHÔNG có ở train."""
    docs = sorted({s.doc_name for s in samples})
    rng.shuffle(docs)
    val_docs: set[str] = set()
    n_target = int(len(samples) * FRAC_VAL)
    n_val = 0
    counts = Counter(s.doc_name for s in samples)
    for d in docs:
        if n_val >= n_target:
            break
        val_docs.add(d)
        n_val += counts[d]
    train = [s for s in samples if s.doc_name not in val_docs]
    val = [s for s in samples if s.doc_name in val_docs]
    return train, val


def ghi_jsonl(samples: list[Sample], path: Path, meta_path: Path) -> None:
    with path.open("w", encoding="utf-8") as f, meta_path.open("w", encoding="utf-8") as g:
        for s in samples:
            f.write(json.dumps(to_record(s), ensure_ascii=False) + "\n")
            g.write(json.dumps({
                "sample_id": s.sample_id, "doc_name": s.doc_name, "slug": s.slug,
                "header_format": s.header_format, "kind": s.kind,
                "citations": s.citations, "n_blocks": s.n_blocks,
                "difficulty": s.difficulty, "question_type": s.question_type,
                **s.meta,
            }, ensure_ascii=False) + "\n")


def doc_lai_jsonl(ten: str) -> list[Sample]:
    """Dựng lại `Sample` từ file đã ghi — để chạy lại riêng phần báo cáo.

    `user_prompt` có khuôn cố định (api_contract.md §1.2) nên tách ngược được:
        CONTEXT:\\n{context}\\n\\nCÂU HỎI: {question}\\n\\nTRẢ LỜI:
    """
    out: list[Sample] = []
    with (OUT_DIR / f"{ten}.jsonl").open(encoding="utf-8") as f, \
         (OUT_DIR / f"{ten}_meta.jsonl").open(encoding="utf-8") as g:
        for line, mline in zip(f, g):
            rec, meta = json.loads(line), json.loads(mline)
            _, msg_user, msg_assistant = rec["messages"]
            body = msg_user["content"][len("CONTEXT:\n"):-len("\n\nTRẢ LỜI:")]
            ctx, _, question = body.rpartition("\n\nCÂU HỎI: ")
            out.append(Sample(
                sample_id=meta["sample_id"], doc_name=meta["doc_name"], slug=meta["slug"],
                header_format=meta["header_format"], kind=meta["kind"],
                question=question, context=ctx,
                answer=msg_assistant["content"], citations=meta["citations"],
                n_blocks=meta["n_blocks"], difficulty=meta.get("difficulty", ""),
                question_type=meta.get("question_type", ""),
                meta={k: v for k, v in meta.items() if k not in
                      {"sample_id", "doc_name", "slug", "header_format", "kind",
                       "citations", "n_blocks", "difficulty", "question_type"}},
            ))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TASK-FT-04 — sinh dữ liệu huấn luyện")
    ap.add_argument("--n", type=int, default=N_TOTAL)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--report-only", action="store_true",
                    help="không sinh lại dữ liệu, chỉ dựng lại báo cáo từ jsonl đã ghi")
    args = ap.parse_args()

    if args.report_only:
        train = doc_lai_jsonl("train")
        val = doc_lai_jsonl("val")
        samples = train + val
        blocked_names, blocked_so_hieu, block_rows = load_blocklist()
        kiem_tra(samples, blocked_names, blocked_so_hieu)
        print(f"đọc lại {len(samples)} mẫu — blocklist OK, round-trip OK")
        stats = json.loads((REPORT_DIR / "dataset_build.json").read_text(encoding="utf-8"))
        from finetune.dataset_report import viet_bao_cao
        viet_bao_cao(samples, train, val, stats, REPORT_DIR, random.Random(args.seed))
        print(f"đã ghi báo cáo → {REPORT_DIR}")
        return 0

    samples, stats = build(args.n, args.seed)
    print(f"sinh được {len(samples)}/{args.n} mẫu")

    blocked_names, blocked_so_hieu, _ = load_blocklist()
    kiem_tra(samples, blocked_names, blocked_so_hieu)
    print("kiểm tra: blocklist OK, round-trip parse_citations OK (100%)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train, val = tach_train_val(samples, random.Random(args.seed))
    ghi_jsonl(train, OUT_DIR / "train.jsonl", OUT_DIR / "train_meta.jsonl")
    ghi_jsonl(val, OUT_DIR / "val.jsonl", OUT_DIR / "val_meta.jsonl")
    print(f"đã ghi train={len(train)} val={len(val)} → {OUT_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "dataset_build.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not args.no_report:
        from finetune.dataset_report import viet_bao_cao
        viet_bao_cao(samples, train, val, stats, REPORT_DIR, random.Random(args.seed))
        print(f"đã ghi báo cáo → {REPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
