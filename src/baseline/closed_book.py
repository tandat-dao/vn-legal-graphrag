"""
Closed-book baseline (E2a) — LLM trả lời KHÔNG có retrieval.

Trả lời câu hỏi pháp lý CHỈ bằng tri thức tham số của LLM (không tra cứu tài
liệu). Trả lời câu hỏi khoa học: "hệ có CẦN retrieval không?".

Kỳ vọng (docs/EVALUATION_ARCHITECTURE.md §E2a): sụp mạnh ở Gap 2 & Gap 4 — LLM
không thể biết quy định địa phương (hạn mức đất tỉnh X) hay hiệu lực thời điểm
(văn bản nào còn/hết hiệu lực) từ pretraining. Citation phần lớn sẽ KHÔNG khớp
slug corpus (LLM cite theo số hiệu, không biết id slug) → F1 thấp = bằng chứng
"tri thức này buộc phải đến từ kiến trúc retrieval".

Prompt RIÊNG (không dùng build_messages của RAG): prompt RAG cấm bịa ngoài context
→ closed-book sẽ từ chối mọi thứ (strawman không công bằng). Ở đây CHO PHÉP LLM
dùng kiến thức sẵn có, nhưng vẫn yêu cầu format citation để đo được.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import anthropic

from src.retrieval.answer_generator import (
    MODEL,
    _cache_get,
    _cache_put,
    _prompt_hash,
    parse_citations,
)

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1200
_TEMPERATURE = 0.0

_SYSTEM = (
    "Bạn là trợ lý pháp luật Việt Nam. Bạn KHÔNG được cung cấp tài liệu tra cứu "
    "nào — hãy trả lời câu hỏi CHỈ dựa trên kiến thức pháp luật sẵn có của bạn.\n"
    "Yêu cầu:\n"
    "- Trả lời ngắn gọn, đúng trọng tâm câu hỏi.\n"
    "- Nếu bạn biết điều khoản/văn bản cụ thể, hãy trích dẫn theo định dạng "
    "[Điều X, Khoản Y, Văn bản <tên hoặc số hiệu>].\n"
    "- Nếu KHÔNG chắc chắn hoặc không biết, hãy nói rõ 'Tôi không chắc chắn' thay "
    "vì bịa ra số liệu, điều khoản hoặc văn bản.\n"
    "- Đặc biệt thận trọng với quy định phụ thuộc ĐỊA PHƯƠNG (mức phí, hạn mức đất "
    "theo tỉnh) và HIỆU LỰC theo thời điểm — nếu không nắm chắc, nói rõ là tùy địa "
    "phương/thời điểm."
)


def run_closedbook_query(
    question: str,
    llm_client: anthropic.Anthropic,
    cache_dir: Path | None = None,
    mode: str = "general",
) -> dict:
    """Trả lời closed-book (không retrieval). Trả về dict khớp shape baseline."""
    t0 = time.perf_counter()
    user = f"Câu hỏi: {question}"
    cache_key = _prompt_hash(_SYSTEM + "\n\n" + user, MODEL)
    cached = _cache_get(cache_dir, cache_key)
    if cached is not None:
        answer = cached["answer"]
        logger.info(f"closed-book: cache HIT ({cache_key}) — $0 API")
    else:
        msg = llm_client.messages.create(
            model=MODEL,
            max_tokens=_MAX_TOKENS,
            temperature=_TEMPERATURE,
            system=[{"type": "text", "text": _SYSTEM,
                     "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        answer = msg.content[0].text
        _cache_put(cache_dir, cache_key, {"answer": answer})

    return {
        "answer": answer,
        "citations": parse_citations(answer),
        "context_used": False,          # closed-book: KHÔNG có context
        "top_k_count": 0,
        "context": "",
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
