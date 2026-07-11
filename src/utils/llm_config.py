"""
Cấu hình tập trung cho Anthropic SDK client.

Mục đích: tránh hardcode magic numbers lặp ở nhiều site (pipeline.py, naive_rag.py,
run_evaluation.py). Bất kỳ instantiation `anthropic.Anthropic(...)` nào trong codebase
PHẢI dùng `make_anthropic_client()` hoặc import `ANTHROPIC_MAX_RETRIES` để đảm bảo
behavior retry/timeout đồng nhất → kết quả eval reproducible.

Lý do `max_retries=8`: API Anthropic occasionally trả 529 Overloaded; SDK default=2
không đủ — eval run dài (~25 câu × 2 hệ thống) có thể crash. Exponential backoff
với 8 retries cho ~vài phút wait trước khi raise — đủ cho hầu hết transient outage.
"""
from __future__ import annotations

import logging
import os

import anthropic

logger = logging.getLogger(__name__)

# Số lần SDK retry trên 429/5xx/529 với exponential backoff.
ANTHROPIC_MAX_RETRIES = 8


def make_anthropic_client(api_key: str | None = None) -> anthropic.Anthropic:
    """Factory chuẩn cho Anthropic client với retry config đồng nhất."""
    return anthropic.Anthropic(
        api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        max_retries=ANTHROPIC_MAX_RETRIES,
    )


VALID_LLM_MODES = ("claude", "claude-fallback", "gemini", "gemini-fallback")


def make_llm_client(api_key: str | None = None, *, mode: str | None = None):
    """Client LLM cho retrieval/demo path — chọn 1 trong 4 mode.

    mode:
      - "claude" (MẶC ĐỊNH): thuần Claude, KHÔNG fallback. Dùng cho EVAL → reproducible.
      - "claude-fallback": Claude chính + Gemini khi Claude drop (lỗi hạ tầng).
      - "gemini": Gemini end-to-end (planner + generator chạy Gemini, KHÔNG đụng Claude).
      - "gemini-fallback": Gemini chính + Claude khi Gemini drop (429/5xx) — cho DEMO
        bảo vệ chạy Gemini nhưng vẫn sống khi Vertex hết quota.
      - None → đọc env `LLM_MODE` (mặc định "claude").

    QUAN TRỌNG: mặc định "claude" để EVAL luôn thuần Claude. Demo chọn mode khác.
    Thiếu cấu hình Gemini (không key + không vertex) → *-fallback tự degrade về Claude
    thuần + cảnh báo.
    """
    if mode is None:
        mode = os.getenv("LLM_MODE", "claude").lower()
    if mode not in VALID_LLM_MODES:
        logger.warning(f"make_llm_client: mode={mode!r} không hợp lệ → dùng 'claude'")
        mode = "claude"

    gemini_key = os.getenv("GEMINI_API_KEY")
    use_vertex = os.getenv("GEMINI_USE_VERTEX", "false").lower() == "true"
    gemini_ready = bool(gemini_key) or use_vertex  # vertex dùng ADC, không cần api_key

    if mode == "gemini":
        from src.utils.gemini_fallback import GeminiClient
        logger.info("LLM client: GEMINI end-to-end")
        return GeminiClient(gemini_key)

    anthropic_client = make_anthropic_client(api_key)
    if mode == "claude":
        return anthropic_client

    if mode == "gemini-fallback":
        if not gemini_ready:
            logger.warning(
                "mode=gemini-fallback nhưng thiếu cấu hình Gemini (GEMINI_API_KEY/Vertex) "
                "→ chạy Anthropic thuần"
            )
            return anthropic_client
        from src.utils.gemini_fallback import FallbackGeminiClient
        logger.info("LLM client: Gemini + Claude fallback (dự phòng khi Gemini sập/hết quota)")
        return FallbackGeminiClient(gemini_key, anthropic_client)

    # claude-fallback
    if not gemini_ready:
        logger.warning(
            "mode=claude-fallback nhưng thiếu cấu hình Gemini (GEMINI_API_KEY/Vertex) "
            "→ chạy Anthropic thuần"
        )
        return anthropic_client
    from src.utils.gemini_fallback import FallbackLLMClient
    logger.info("LLM client: Claude + Gemini fallback (dự phòng khi Claude sập)")
    return FallbackLLMClient(anthropic_client, gemini_key)
