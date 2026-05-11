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
MAX_ANSWER_TOKENS = 1500

# Regex bắt [Điều X, Khoản Y, Văn bản Z] hoặc [Điều X, Văn bản Z]
_CITATION_RE = re.compile(
    r"\[Điều\s+([^,\]]+)"          # bắt buộc: Điều X
    r"(?:,\s*Khoản\s+([^,\]]+))?"  # tùy chọn: Khoản Y
    r",\s*Văn bản\s+([^\]]+)\]",   # bắt buộc: Văn bản Z
    re.IGNORECASE,
)


def parse_citations(raw_answer: str) -> list[dict]:
    """Extract citations từ câu trả lời LLM.

    Pattern: [Điều X, Khoản Y, Văn bản Z] hoặc [Điều X, Văn bản Z]

    Returns:
        List dict với keys: dieu, khoan (có thể None), van_ban.
    """
    citations = []
    for match in _CITATION_RE.finditer(raw_answer):
        dieu = match.group(1).strip()
        khoan = match.group(2).strip() if match.group(2) else None
        van_ban = match.group(3).strip()
        citations.append({"dieu": dieu, "khoan": khoan, "van_ban": van_ban})
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
