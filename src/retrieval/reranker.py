"""
Cross-encoder Reranker — direction 2 (retrieval precision).

Mục đích: vá giới hạn embedding bi-encoder ở disambiguation cấp Điều (P-08, Q022):
BGE-M3 không phân biệt được các Điều có label gần giống ("hạn mức đất ở cho hộ
gia đình cá nhân" vs "cho người có công"). Cross-encoder mã hóa CHUNG (query, chunk)
nên attention bidirectional có thể phân biệt — đây là lớp rerank kinh điển
"retrieve (bi-encoder) → rerank (cross-encoder)".

Tính chất: chạy **LOCAL, $0 inference** (không gọi API). Model mặc định
`BAAI/bge-reranker-v2-m3` — cùng họ BGE-M3, đa ngôn ngữ (hỗ trợ tiếng Việt).

Vai trò kép (xem IMPROVEMENT_ROADMAP): (1) lớp rerank trong retrieval; (2) "teacher"
sinh hard-negative + soft-label để distill xuống bi-encoder khi finetune embedding.

LƯU Ý: `load_reranker()` tải model (~600MB) ở lần gọi ĐẦU TIÊN — lazy, chỉ xảy ra
khi thực sự rerank live. Import module / unit test (truyền model mock) KHÔNG tải gì.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# Cache model toàn cục (load 1 lần, tái dùng) — giống vectorizer.load_model.
_RERANKER: Any | None = None


def load_reranker(model_name: str | None = None):
    """Lazy-load CrossEncoder (local). Tải model ~600MB ở lần gọi đầu.

    Dùng MPS (Apple Silicon) > CUDA > CPU, đồng bộ với pipeline BGE-M3.
    """
    global _RERANKER
    if _RERANKER is None:
        from sentence_transformers import CrossEncoder
        import torch

        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
        name = model_name or RERANKER_MODEL
        logger.info(f"load_reranker: tải CrossEncoder '{name}' trên {device} (lần đầu ~600MB)")
        _RERANKER = CrossEncoder(name, device=device)
    return _RERANKER


def rerank(
    query: str,
    candidates: list[dict],
    *,
    model: Any | None = None,
    top_k: int | None = None,
    text_key: str = "text",
) -> list[dict]:
    """Xếp lại candidates theo điểm cross-encoder (query, text) giảm dần.

    Args:
        query: câu hỏi gốc.
        candidates: list dict, mỗi dict có field `text_key` chứa nội dung chunk
            (cùng metadata khác — được giữ nguyên trong output).
        model: CrossEncoder (hoặc bất kỳ object có `.predict(pairs)`); None → lazy
            load model thật (tải ~600MB). Truyền mock trong test để $0 + offline.
        top_k: nếu set, chỉ trả top_k sau khi rerank.
        text_key: tên field chứa text trong mỗi candidate.

    Returns:
        List candidates (copy) đã sort theo `rerank_score` giảm dần, mỗi phần tử
        thêm key `rerank_score` (float). Giữ nguyên thứ tự đầu vào khi điểm bằng nhau
        (sort ổn định). Rỗng nếu candidates rỗng.
    """
    if not candidates:
        return []
    model = model or load_reranker()
    pairs = [[query, c.get(text_key, "") or ""] for c in candidates]
    scores = model.predict(pairs)

    scored = []
    for c, s in zip(candidates, scores):
        c2 = dict(c)
        c2["rerank_score"] = float(s)
        scored.append(c2)
    # sort ổn định theo điểm giảm dần (giữ thứ tự gốc khi hòa điểm)
    scored.sort(key=lambda x: -x["rerank_score"])
    if top_k is not None:
        scored = scored[:top_k]
    logger.info(f"rerank: {len(candidates)} candidates → top {len(scored)} (cross-encoder)")
    return scored
