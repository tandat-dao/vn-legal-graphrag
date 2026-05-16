"""
Answer Generator — TASK-13 (phần 2)
Gửi prompt vào Claude Sonnet 4.6, parse citations từ raw output.

Citation format trong câu trả lời: [Điều X, Khoản Y, Văn bản Z]
parse_citations() extract thành list[dict] với keys: dieu, khoan, van_ban.
"""
import logging
import re

import anthropic

from src.retrieval.context_assembler import build_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_ANSWER_TOKENS = 3000

# Regex bắt citation đa dạng định dạng:
#   [Điều X, Văn bản Z]
#   [Điều X, Khoản Y, Văn bản Z]
#   [Điều X, Khoản Y, Điểm Z, Văn bản W]
#   [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
#   [Phụ lục X, Văn bản Z]
#   [Phụ lục X, Khoản Y, Văn bản Z]
# Group 1: loại đầu (Điều | Phụ lục), Group 2: số/ký hiệu
# Group 3: Khoản (optional), Group 4: Điểm (optional), Group 5: Tiết (optional)
# Group 6: Văn bản id
_CITATION_RE = re.compile(
    r"\[(Điều|Phụ lục)\s+([^,\]]+)"
    r"(?:,\s*Khoản\s+([^,\]]+))?"
    r"(?:,\s*Điểm\s+([^,\]]+))?"
    r"(?:,\s*Tiết\s+([^,\]]+))?"
    r",\s*Văn bản\s+([^\]]+)\]",
    re.IGNORECASE,
)


def parse_citations(raw_answer: str) -> list[dict]:
    """Extract citations từ câu trả lời LLM.

    Hỗ trợ các định dạng:
        [Điều X, Văn bản Z]
        [Điều X, Khoản Y, Văn bản Z]
        [Điều X, Khoản Y, Điểm Z, Văn bản W]
        [Điều X, Khoản Y, Điểm Z, Tiết K, Văn bản W]
        [Phụ lục X, Văn bản Z]
        [Phụ lục X, Khoản Y, Văn bản Z]

    Returns:
        List dict với keys: dieu, khoan, diem (optional), tiet (optional),
        van_ban, loai. `loai` = "dieu" | "phu_luc"; `dieu` chứa số/ký hiệu
        của Điều hoặc Phụ lục để backward compat.
    """
    citations = []
    for match in _CITATION_RE.finditer(raw_answer):
        loai_raw = match.group(1).strip().lower()
        loai = "phu_luc" if loai_raw.startswith("phụ") else "dieu"
        number = match.group(2).strip()
        khoan = match.group(3).strip() if match.group(3) else None
        diem = match.group(4).strip() if match.group(4) else None
        tiet = match.group(5).strip() if match.group(5) else None
        van_ban = match.group(6).strip()
        c = {
            "dieu": number,
            "khoan": khoan,
            "diem": diem,
            "tiet": tiet,
            "van_ban": van_ban,
            "loai": loai,
        }
        citations.append(c)
    return citations


def generate_answer(
    question: str,
    context: str,
    llm_client: anthropic.Anthropic,
) -> dict:
    """Gửi prompt vào Claude Sonnet 4.6, trả về answer + citations.

    Args:
        question: Câu hỏi tiếng Việt của người dùng.
        context: Context string từ assemble_context().
        llm_client: Anthropic client đã khởi tạo.

    Returns:
        Dict với keys:
          - answer (str): Câu trả lời tiếng Việt với citations inline.
          - citations (list[dict]): Danh sách citations đã parse.
          - context_used (bool): True nếu context không rỗng.
    """
    if not context.strip():
        logger.warning("generate_answer: context rỗng — LLM sẽ trả lời không có nguồn")

    prompt = build_prompt(question, context)

    message = llm_client.messages.create(
        model=MODEL,
        max_tokens=MAX_ANSWER_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_answer = message.content[0].text.strip()
    citations = parse_citations(raw_answer)

    logger.info(
        f"generate_answer: {len(raw_answer)} chars, {len(citations)} citations"
    )

    return {
        "answer": raw_answer,
        "citations": citations,
        "context_used": bool(context.strip()),
    }
