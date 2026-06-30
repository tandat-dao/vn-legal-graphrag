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


def make_llm_client(api_key: str | None = None, *, enable_fallback: bool | None = None):
    """Client LLM cho retrieval/demo path — Anthropic thuần hoặc bọc Gemini fallback.

    enable_fallback:
      - None (mặc định): đọc env `LLM_FALLBACK_ENABLED` (mặc định "false").
      - True/False: override tường minh.

    QUAN TRỌNG: mặc định TẮT để EVAL luôn thuần Claude (reproducible). Chỉ DEMO
    bật fallback. Thiếu `GEMINI_API_KEY` → tự degrade về Anthropic thuần + cảnh báo.
    """
    anthropic_client = make_anthropic_client(api_key)

    if enable_fallback is None:
        enable_fallback = os.getenv("LLM_FALLBACK_ENABLED", "false").lower() == "true"
    if not enable_fallback:
        return anthropic_client

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.warning(
            "LLM_FALLBACK_ENABLED bật nhưng thiếu GEMINI_API_KEY → chạy Anthropic thuần"
        )
        return anthropic_client

    from src.utils.gemini_fallback import FallbackLLMClient

    logger.info("LLM client: BẬT Gemini fallback (dự phòng khi Claude sập)")
    return FallbackLLMClient(anthropic_client, gemini_key)
