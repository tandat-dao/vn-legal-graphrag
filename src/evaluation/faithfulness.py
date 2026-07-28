"""
Faithfulness metric — đo tính trung thực của citations trong answer.

2 tier metric:

  **Tier 1 — Citation Existence Rate** (deterministic, $0 API):
    % pred citations có chunk match trong context (xét theo header
    "--- ... Điều X Khoản Y ... (van-ban-id) ---" do assemble_context tạo).
    Mục đích: catch hallucination thô — LLM cite chunk KHÔNG có trong context.

  **Tier 2 — Citation Support Rate** (LLM-as-judge, ~$0.001/check):
    Cho mỗi citation tồn tại, hỏi judge: claim trong answer text adjacent
    citation có được CHUNK CONTENT support không? Catch hallucination tinh
    vi (cite chunk có nhưng nội dung không match).

Aggregate metrics:
  - existence_rate = #existing / #total_cited
  - support_rate = #supported / #existing
  - faithful_rate (combined) = #(existing AND supported) / #total_cited

Mục đích cho luận văn:
  - F1/NormR đo ĐÚNG VỊ TRÍ citation
  - Faithfulness đo ĐÚNG NỘI DUNG được cite — orthogonal dimension
  - Discussion chapter: F1 cao + Faithfulness thấp = system cite vị trí
    đúng nhưng diễn giải sai; F1 thấp + Faithfulness cao = retrieval miss
    target nhưng những gì cite được vẫn đúng.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TypedDict

import anthropic

logger = logging.getLogger(__name__)

# Model nhẹ cho judge — Haiku 4.5 rẻ + nhanh
JUDGE_MODEL = "claude-haiku-4-5-20251001"


class FaithfulnessResult(TypedDict):
    existence_rate: float       # % citations có chunk match trong context
    support_rate: float         # % existing citations được context support
    faithful_rate: float        # % citations existing AND supported
    citations_total: int
    citations_existing: int
    citations_supported: int
    per_citation: list[dict]    # detail từng citation


# ---------------------------------------------------------------------------
# Tier 1: Citation Existence Rate (deterministic)
# ---------------------------------------------------------------------------

def _norm(s: str | None) -> str | None:
    """Chuẩn hoá để compare: lowercase + strip."""
    if s is None:
        return None
    s = str(s).strip().lower()
    return s or None


def _citation_in_context(citation: dict, context: str) -> bool:
    """Check một citation (dieu, khoan, van_ban) có header tương ứng trong context.

    Context format từ assemble_context: mỗi block có header dạng:
      --- [Tier X | Hiệu lực: ...] Điều Y. <title> > Khoản Z. ... (van-ban-id) ---

    Logic: tìm 1 header match (case-insensitive) cùng van_ban + dieu + (khoan
    nếu specified). Hỗ trợ Phụ lục (loai='phu_luc'): khi dieu='_default'
    (sentinel cho Phụ lục duy nhất) hoặc loai='phu_luc', match "phụ lục" trong
    header thay vì "điều X".
    """
    vb = _norm(citation.get("van_ban"))
    dieu = _norm(citation.get("dieu"))
    khoan = _norm(citation.get("khoan"))
    loai = _norm(citation.get("loai"))
    if not vb:
        return False
    if not dieu and loai != "phu_luc":
        return False

    is_phu_luc = loai == "phu_luc" or dieu == "_default"
    # Extract headers
    headers = re.findall(r"^---[^\n]*$", context, flags=re.MULTILINE)
    for h in headers:
        h_low = h.lower()
        if vb not in h_low:
            continue
        if is_phu_luc:
            # Match "phụ lục" + optional "{dieu}" nếu dieu khác '_default'
            if "phụ lục" not in h_low:
                continue
            if dieu and dieu != "_default":
                if f"phụ lục {dieu}" not in h_low:
                    continue
        else:
            # Tìm "điều {dieu}." (có dấu chấm sau số để tránh "Điều 1" match "Điều 10")
            if f"điều {dieu}." not in h_low:
                continue
        if khoan is not None:
            if f"khoản {khoan}." not in h_low:
                continue
        return True
    return False


# ---------------------------------------------------------------------------
# Tier 2: Citation Support Rate (LLM-as-judge)
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM_PROMPT = """Bạn là chuyên gia thẩm định citation pháp luật. Nhiệm vụ: kiểm tra xem một citation trong câu trả lời có được context (đoạn văn bản pháp luật được trích) THỰC SỰ support không.

Quy tắc đánh giá:
- SUPPORTED: nội dung claim quanh citation được context chunk này khẳng định (đồng nghĩa hoặc trích dẫn nguyên văn). Số liệu, danh từ, điều kiện đều khớp.
- UNSUPPORTED: claim KHÔNG được context chunk này khẳng định, hoặc context nói khác (số liệu khác, đối tượng khác, điều kiện khác).
- PARTIAL: context support một phần (vd: đúng đối tượng nhưng sai số liệu) — coi như UNSUPPORTED để strict.

Output JSON ONLY:
{"verdict": "SUPPORTED"|"UNSUPPORTED", "reason": "<1-2 câu giải thích ngắn>"}"""


def _extract_chunk_for_citation(citation: dict, context: str) -> str | None:
    """Lấy nội dung chunk (text + header) tương ứng citation từ context.

    Search trong header block đầy đủ (không phải chỉ first 300 chars) vì header
    của Component sửa đổi (VD NĐ 49 Điều 13) có thể dài 250+ chars trước khi
    đến "Khoản X" suffix. Hỗ trợ Phụ lục: match "phụ lục" khi loai='phu_luc'.
    """
    vb = _norm(citation.get("van_ban"))
    dieu = _norm(citation.get("dieu"))
    khoan = _norm(citation.get("khoan"))
    diem = _norm(citation.get("diem"))
    loai = _norm(citation.get("loai"))
    if not vb:
        return None
    if not dieu and loai != "phu_luc":
        return None
    is_phu_luc = loai == "phu_luc" or dieu == "_default"
    # Split context theo header blocks
    blocks = re.split(r"(?=^---[^\n]*$)", context, flags=re.MULTILINE)

    def _match(block: str, with_diem: bool) -> bool:
        first_line_end = block.find("\n")
        header = (block[:first_line_end] if first_line_end > 0 else block).lower()
        if vb not in header:
            return False
        if is_phu_luc:
            if "phụ lục" not in header:
                return False
            if dieu and dieu != "_default" and f"phụ lục {dieu}" not in header:
                return False
        else:
            if f"điều {dieu}." not in header:
                return False
        if khoan is not None and f"khoản {khoan}." not in header:
            return False
        if with_diem and diem is not None and f"điểm {diem}." not in header:
            return False
        return True

    # Pass 1 — khớp tới cấp Điểm (tránh trả nhầm Điểm khác cùng Điều/Khoản).
    # Pass 2 — nới lỏng: ngữ cảnh có thể chỉ chứa khối ở cấp Khoản.
    for with_diem in (True, False):
        if with_diem and diem is None:
            continue
        for block in blocks:
            if _match(block, with_diem):
                return block.strip()
    return None


def _extract_answer_snippet(citation: dict, answer: str, window: int = 200) -> str:
    """Lấy snippet quanh nơi citation xuất hiện trong answer text.

    Hỗ trợ cả citation Điều ([Điều X, Khoản Y, ...]) lẫn Phụ lục ([Phụ lục I, ...]
    / [Phụ lục, Khoản 2, ...]). Trước đây chỉ bắt regex `Điều` → citation Phụ lục
    luôn rơi vào fallback (400 ký tự đầu answer) → judge nhìn sai ngữ cảnh → flag
    oan (quan sát Q008 chạy Tier 2). Dispatch theo `loai` để fix.
    """
    dieu = citation.get("dieu", "") or ""
    khoan = citation.get("khoan", "")
    vb = citation.get("van_ban", "")
    loai = citation.get("loai")
    vb_esc = re.escape(vb)

    patterns: list[str] = []
    if loai == "phu_luc":
        # [Phụ lục I, ...] hoặc [Phụ lục, ...] (dieu='_default' khi Phụ lục không số)
        head = r"\[Phụ\s*lục"
        if dieu and dieu != "_default":
            head += rf"\s+{re.escape(dieu)}"
        if khoan:
            patterns.append(head + rf"[^\]]*Khoản\s+{re.escape(khoan)}[^\]]*{vb_esc}\]")
        patterns.append(head + rf"[^\]]*{vb_esc}\]")
    else:
        if khoan:
            patterns.append(rf"\[Điều\s+{re.escape(dieu)},\s*Khoản\s+{re.escape(khoan)}[^\]]*{vb_esc}\]")
        patterns.append(rf"\[Điều\s+{re.escape(dieu)}[^\]]*{vb_esc}\]")

    for pat in patterns:
        m = re.search(pat, answer, re.IGNORECASE)
        if m:
            start = max(0, m.start() - window)
            end = min(len(answer), m.end() + 50)
            return answer[start:end]
    # Fallback: trả về toàn answer (truncated)
    return answer[: window * 2]


def _judge_citation(
    citation: dict,
    answer: str,
    chunk: str,
    llm_client: anthropic.Anthropic,
) -> dict:
    """Hỏi LLM judge: chunk có support claim quanh citation trong answer không?"""
    snippet = _extract_answer_snippet(citation, answer)
    user_prompt = f"""CITATION cần đánh giá: {citation}

ĐOẠN ANSWER (xung quanh citation):
{snippet}

CONTEXT CHUNK được cite:
{chunk[:1500]}

Đoạn answer trên cite chunk này có được chunk THỰC SỰ support không?"""
    try:
        message = llm_client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=200,
            system=_JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].lstrip("json").strip()
        # Robust JSON parse — handle multi-line reason strings từ LLM
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: regex extract verdict + reason
            verdict_m = re.search(r'"verdict"\s*:\s*"(SUPPORTED|UNSUPPORTED)"', raw, re.IGNORECASE)
            reason_m = re.search(r'"reason"\s*:\s*"([^"]*)', raw)
            if verdict_m:
                parsed = {
                    "verdict": verdict_m.group(1).upper(),
                    "reason": reason_m.group(1) if reason_m else raw[:200],
                }
            else:
                # Last resort: detect SUPPORTED/UNSUPPORTED keyword anywhere
                if "SUPPORTED" in raw.upper() and "UNSUPPORTED" not in raw.upper():
                    parsed = {"verdict": "SUPPORTED", "reason": raw[:200]}
                else:
                    parsed = {"verdict": "UNSUPPORTED", "reason": raw[:200]}
        return {
            "supported": parsed.get("verdict") == "SUPPORTED",
            "reason": parsed.get("reason", ""),
        }
    except Exception as e:
        logger.warning(f"_judge_citation lỗi: {e}")
        return {"supported": False, "reason": f"judge_error: {e}"}


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def evaluate_faithfulness(
    citations: list[dict],
    answer: str,
    context: str,
    llm_client: anthropic.Anthropic | None = None,
    tier2: bool = True,
) -> FaithfulnessResult:
    """Đánh giá faithfulness của citations cho 1 câu trả lời.

    Args:
        citations: list pred citations từ parse_citations.
        answer: full answer text từ generate_answer.
        context: full context từ assemble_context.
        llm_client: Anthropic client cho Tier 2. Nếu None hoặc tier2=False,
                    chỉ tính Tier 1.
        tier2: enable Tier 2 LLM judge.

    Returns:
        FaithfulnessResult với existence_rate, support_rate, faithful_rate +
        per-citation detail.
    """
    if not citations:
        return FaithfulnessResult(
            existence_rate=1.0, support_rate=1.0, faithful_rate=1.0,
            citations_total=0, citations_existing=0, citations_supported=0,
            per_citation=[],
        )

    per_citation = []
    n_existing = 0
    n_supported = 0
    enable_t2 = tier2 and llm_client is not None

    for c in citations:
        exists = _citation_in_context(c, context)
        entry = {"citation": c, "existing": exists}
        if exists:
            n_existing += 1
            if enable_t2:
                chunk = _extract_chunk_for_citation(c, context)
                if chunk:
                    judge = _judge_citation(c, answer, chunk, llm_client)
                    entry["supported"] = judge["supported"]
                    entry["reason"] = judge["reason"]
                    if judge["supported"]:
                        n_supported += 1
                else:
                    entry["supported"] = False
                    entry["reason"] = "chunk_extract_failed"
            else:
                entry["supported"] = None  # không đánh giá
        else:
            entry["supported"] = False
            entry["reason"] = "citation_not_in_context"
        per_citation.append(entry)

    n_total = len(citations)
    existence_rate = n_existing / n_total if n_total else 1.0
    if enable_t2:
        support_rate = n_supported / n_existing if n_existing else 1.0
        faithful_rate = n_supported / n_total if n_total else 1.0
    else:
        # Khi không enable Tier 2, support_rate không đo được; faithful_rate
        # quy về existence_rate (chỉ catch hallucination thô).
        support_rate = float("nan")
        faithful_rate = existence_rate
        n_supported = n_existing  # placeholder để aggregate hợp lý

    return FaithfulnessResult(
        existence_rate=existence_rate,
        support_rate=support_rate,
        faithful_rate=faithful_rate,
        citations_total=n_total,
        citations_existing=n_existing,
        citations_supported=n_supported,
        per_citation=per_citation,
    )
