"""
Term Grounding Validator — phát hiện thuật ngữ giả (fabricated terminology)
trong câu trả lời LLM.

Vấn đề: LLM có thể tự tạo tên gọi cho khái niệm/nguyên tắc pháp lý mà không
có trong corpus (VD: "nguyên tắc cắt ngang", "span-regime", "doctrine X").
Module này extract các candidate thuật ngữ và kiểm tra grounding trong:
  (1) Context retrieve được (direct grounding — bằng chứng mạnh nhất)
  (2) Corpus rộng — `data/raw/*.md` (broader grounding — fallback)

Approach: detection-then-validate, không depend vào LLM judge (zero-cost).

Public API:
    extract_candidate_terms(answer: str) -> list[Candidate]
    validate_terms(candidates, context, corpus_text) -> list[Validation]
    grounding_rate(validations) -> float
    validate_answer(answer, context, corpus_text) -> dict   # all-in-one

CLI:
    python -m src.evaluation.term_validator <results_json> [--corpus data/raw]
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


# ---------------------------------------------------------------------------
# Candidate term extraction
# ---------------------------------------------------------------------------

# Pattern 1: cụm trong dấu ngoặc kép "..." dài 2-7 từ — thường dùng define thuật ngữ
_QUOTED_TERM_RE = re.compile(r'["“]([\w\s\-]{4,60})["”]')

# Pattern 2: "nguyên tắc X", "quy tắc X", "học thuyết X", "doctrine X", "principle X"
#   — danh từ định danh + tên (≤5 từ)
_NAMED_PRINCIPLE_RE = re.compile(
    r'\b(?:nguyên tắc|quy tắc|học thuyết|doctrine|principle|nguyên lý)\s+'
    r'([a-zA-ZÀ-ỹ][\wÀ-ỹ\s\-]{2,40}?)(?=[,.;:!?\]\)"]|$|\s+(?:được|của|là|theo|trong|và|hoặc))',
    re.IGNORECASE
)

# Pattern 3: cụm trong ngoặc đơn (...) sau danh từ — short label/shortcut
#   chỉ flag nếu cụm trong ngoặc ngắn (≤5 từ) và KHÔNG chứa ký tự đặc biệt như ",", "—", "/"
#   (giúp tránh false positive: "(VD: ...)", "(Tier 1 > ...)")
_PARENTHETICAL_LABEL_RE = re.compile(
    r'\(([a-zA-ZÀ-ỹ][\wÀ-ỹ\s\-]{2,30})\)'
)

# Pattern 4: cụm in đậm **X** ngắn ≤4 từ, có thể là tên thuật ngữ
_BOLD_TERM_RE = re.compile(r'\*\*([a-zA-ZÀ-ỹ][\wÀ-ỹ\s\-]{2,30})\*\*')

# Stop-list: cụm rất phổ biến không phải thuật ngữ pháp lý chuyên ngành
# (KHÔNG cần flag dù chúng không xuất hiện trong context)
_STOPLIST = {
    # Lưu ý / cảnh báo
    "lưu ý", "lưu ý quan trọng", "lưu ý đặc biệt", "lưu ý thực tiễn",
    "lưu ý chung", "lưu ý phân biệt", "lưu ý thêm",
    # Format header phổ biến
    "tóm tắt", "kết luận", "khuyến nghị", "bối cảnh", "ghi chú",
    "trả lời", "câu hỏi", "phạm vi", "ý nghĩa thực tiễn",
    "cơ sở pháp lý", "căn cứ pháp lý", "định nghĩa", "phân tích",
    # Common adjectives/adverbs
    "có sửa đổi", "không có", "có hiệu lực", "đã hết hiệu lực",
    "đang có hiệu lực", "bản gốc", "bản sửa đổi",
}

# Function words / common prefixes — cụm bắt đầu bằng các từ này hiếm khi là
# thuật ngữ định danh, thường là mô tả/giới từ. Dùng để filter parenthetical+bold.
_NON_TERM_PREFIXES = (
    # Function words
    "không ", "có ", "đã ", "đang ", "phải ", "được ", "sẽ ",
    "rất ", "ít ", "nhiều ", "mọi ", "các ", "những ",
    "tại ", "trong ", "ngoài ", "trên ", "dưới ", "với ", "theo ",
    "từ ", "đến ", "về ", "cho ", "của ", "bởi ", "do ",
    "nếu ", "khi ", "trước ", "sau ", "kể từ ",
    # Quantifiers / common modifiers
    "phù hợp ", "đầy đủ ", "bắt buộc ", "tự nguyện ",
    "tối thiểu ", "tối đa ", "ít nhất ", "nhiều nhất ",
    # Common groupers (descriptive)
    "nhóm ", "loại ", "trường hợp ", "tuyến ", "số ", "khu vực ",
    "phụ lục ", "mục ", "chương ", "phần ",
    # Examples
    "vd:", "ví dụ", "ví dụ:",
)

# Function words / common substrings ở bất kỳ vị trí — flag là descriptive
_NON_TERM_SUBSTRINGS = (
    " không ", " và ", " hoặc ", " cũng ", " mà ", " đã ", " sẽ ",
    " được ", " phải ", " bắt buộc ", " quá ",
)


def _looks_like_term(s: str) -> bool:
    """Heuristic: cụm có signature giống thuật ngữ định danh không?

    Loại các cụm hiển nhiên là descriptive/measurement/heading:
    - Có chứa chữ số → measurement (200 m², 30%, ...)
    - Bắt đầu bằng function word / prefix mô tả
    - Chứa substring chỉ rõ là câu mô tả
    - Quá dài (>5 từ)
    """
    s = s.strip().lower()
    if re.search(r"\d", s):
        return False
    words = s.split()
    if len(words) > 5:
        return False
    if any(s.startswith(p) for p in _NON_TERM_PREFIXES):
        return False
    if any(sub in f" {s} " for sub in _NON_TERM_SUBSTRINGS):
        return False
    return True


class Candidate(TypedDict):
    term: str          # thuật ngữ raw
    term_norm: str     # normalized (lowercase, NFC, trimmed)
    pattern: str       # tên pattern bắt được
    snippet: str       # 30-char context ở 2 phía để hiển thị


def _normalize(s: str) -> str:
    """Lowercase + NFC + strip + collapse whitespace."""
    s = unicodedata.normalize("NFC", s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _safe_snippet(text: str, span: tuple[int, int], width: int = 30) -> str:
    start = max(0, span[0] - width)
    end = min(len(text), span[1] + width)
    s = text[start:end].replace("\n", " ")
    return f"…{s}…"


def extract_candidate_terms(answer: str) -> list[Candidate]:
    """Extract candidate terms từ answer text.

    Returns list các Candidate dict — đã dedupe theo term_norm.
    """
    seen: set[str] = set()
    out: list[Candidate] = []

    # 2 nhóm pattern:
    # - HIGH-PRECISION: signature mạnh là "thuật ngữ định danh" → KHÔNG dùng _looks_like_term filter
    #   (named_principle pre-fix bằng "nguyên tắc/quy tắc/học thuyết" đã đủ chắc)
    # - HEURISTIC: chỉ flag nếu thêm thoả _looks_like_term (loại false positive)
    high_precision = [
        ("named_principle", _NAMED_PRINCIPLE_RE),
    ]
    heuristic = [
        ("quoted", _QUOTED_TERM_RE),
        ("parenthetical", _PARENTHETICAL_LABEL_RE),
        ("bold", _BOLD_TERM_RE),
    ]

    def _try_add(term: str, pat_name: str, span: tuple[int, int], use_filter: bool) -> None:
        term_norm = _normalize(term)
        if term_norm in _STOPLIST:
            return
        if not re.search(r"[a-zA-ZÀ-ỹ]", term):
            return
        if len(term_norm) < 3:
            return
        if re.match(r"^(văn bản|điều|khoản|điểm|tiết|chương|mục|phụ lục)\b", term_norm):
            return
        if use_filter and not _looks_like_term(term_norm):
            return
        if term_norm in seen:
            return
        seen.add(term_norm)
        out.append(Candidate(
            term=term,
            term_norm=term_norm,
            pattern=pat_name,
            snippet=_safe_snippet(answer, span),
        ))

    for pat_name, regex in high_precision:
        for m in regex.finditer(answer):
            _try_add(m.group(1).strip(), pat_name, m.span(), use_filter=False)
    for pat_name, regex in heuristic:
        for m in regex.finditer(answer):
            _try_add(m.group(1).strip(), pat_name, m.span(), use_filter=True)
    return out


# ---------------------------------------------------------------------------
# Grounding validation
# ---------------------------------------------------------------------------

class Validation(TypedDict):
    term: str
    term_norm: str
    pattern: str
    grounded_in_context: bool
    grounded_in_corpus: bool
    grounded: bool        # OR của 2 cái trên
    snippet: str


def _contains(haystack_norm: str, needle_norm: str) -> bool:
    """Substring check sau khi normalize cả 2."""
    return needle_norm in haystack_norm


def validate_terms(
    candidates: list[Candidate],
    context: str,
    corpus_text: str | None = None,
) -> list[Validation]:
    """Check mỗi candidate có grounding trong context và/hoặc corpus."""
    ctx_norm = _normalize(context)
    corpus_norm = _normalize(corpus_text) if corpus_text else ""

    out: list[Validation] = []
    for c in candidates:
        t = c["term_norm"]
        in_ctx = _contains(ctx_norm, t)
        in_corp = _contains(corpus_norm, t) if corpus_norm else False
        out.append(Validation(
            term=c["term"],
            term_norm=t,
            pattern=c["pattern"],
            grounded_in_context=in_ctx,
            grounded_in_corpus=in_corp,
            grounded=in_ctx or in_corp,
            snippet=c["snippet"],
        ))
    return out


def grounding_rate(validations: list[Validation]) -> float:
    if not validations:
        return 1.0  # no candidates → vacuously grounded
    grounded = sum(1 for v in validations if v["grounded"])
    return grounded / len(validations)


def validate_answer(
    answer: str,
    context: str,
    corpus_text: str | None = None,
) -> dict:
    """All-in-one: extract → validate → tính metric.

    Returns dict với:
      - candidates_total: int
      - grounded_count: int
      - ungrounded_count: int
      - grounding_rate: float in [0, 1]
      - ungrounded_terms: list[Validation] — chi tiết các term bị flag
    """
    candidates = extract_candidate_terms(answer)
    validations = validate_terms(candidates, context, corpus_text)
    ungrounded = [v for v in validations if not v["grounded"]]
    return {
        "candidates_total": len(validations),
        "grounded_count": len(validations) - len(ungrounded),
        "ungrounded_count": len(ungrounded),
        "grounding_rate": grounding_rate(validations),
        "ungrounded_terms": ungrounded,
    }


# ---------------------------------------------------------------------------
# Corpus loader (cho CLI)
# ---------------------------------------------------------------------------

def load_corpus_text(corpus_dir: Path) -> str:
    """Concat toàn bộ *.md trong data/raw/ — dùng làm broader grounding."""
    chunks: list[str] = []
    for md in corpus_dir.glob("*.md"):
        try:
            chunks.append(md.read_text(encoding="utf-8"))
        except Exception:
            continue
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Validate terminology grounding trong eval results.")
    ap.add_argument("results_json", type=Path, help="File results_graphrag_*.json")
    ap.add_argument("--corpus", type=Path, default=Path("data/raw"),
                    help="Thư mục corpus *.md để check broader grounding (mặc định data/raw)")
    ap.add_argument("--max-snippet-print", type=int, default=80,
                    help="Cắt snippet hiển thị (default 80 chars)")
    args = ap.parse_args()

    print(f"Loading results: {args.results_json}")
    data = json.loads(args.results_json.read_text(encoding="utf-8"))
    results = data["results"] if isinstance(data, dict) and "results" in data else data

    print(f"Loading corpus: {args.corpus}")
    corpus_text = load_corpus_text(args.corpus)
    print(f"  Corpus loaded: {len(corpus_text)} chars\n")

    total_cands = total_ungrounded = 0
    flagged_questions: list[tuple[str, dict]] = []
    for r in results:
        qid = r.get("id", "?")
        ans = r.get("answer", "")
        ctx = r.get("context", "")
        result = validate_answer(ans, ctx, corpus_text)
        total_cands += result["candidates_total"]
        total_ungrounded += result["ungrounded_count"]
        if result["ungrounded_count"] > 0:
            flagged_questions.append((qid, result))

    print("=" * 70)
    print(f"SUMMARY: {len(results)} câu | {total_cands} candidate terms | "
          f"{total_ungrounded} ungrounded ({total_ungrounded/total_cands*100 if total_cands else 0:.1f}%)")
    print("=" * 70)

    if not flagged_questions:
        print("\n✅ Không phát hiện thuật ngữ giả nào.")
        return

    for qid, result in flagged_questions:
        print(f"\n--- {qid} (grounding_rate={result['grounding_rate']:.2f}) ---")
        for v in result["ungrounded_terms"]:
            print(f"  ⚠  [{v['pattern']}] '{v['term']}'")
            print(f"     context: {v['snippet'][:args.max_snippet_print]}")


if __name__ == "__main__":
    main()
