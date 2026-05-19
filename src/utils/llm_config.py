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

import os

import anthropic

# Số lần SDK retry trên 429/5xx/529 với exponential backoff.
ANTHROPIC_MAX_RETRIES = 8


def make_anthropic_client(api_key: str | None = None) -> anthropic.Anthropic:
    """Factory chuẩn cho Anthropic client với retry config đồng nhất."""
    return anthropic.Anthropic(
        api_key=api_key or os.getenv("ANTHROPIC_API_KEY"),
        max_retries=ANTHROPIC_MAX_RETRIES,
    )
