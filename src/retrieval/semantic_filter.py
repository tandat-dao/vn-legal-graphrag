"""
Semantic Filtering — TASK-12
Hybrid search: Dense (BGE-M3) + Keyword (slug overlap) → RRF fusion.

Thuật toán:
  1. Dense search: encode câu hỏi → Qdrant query_points
     filter: content_type="text_unit" AND norm_id IN norm_ids
     → top 2*top_k candidates với dense_score
  2. Keyword scoring: slugify query tokens → overlap vs norm_id + component_id payload
     → keyword_rank
  3. RRF: score = 1/(k+dense_rank) + 1/(k+keyword_rank), k=60
  4. Return top_k theo rrf_score

norm_ids filter (P2): dùng norm_id (~13 IDs) thay vì component_id (~300 IDs).
BGE-M3 tự chọn TextUnit tốt nhất trong mỗi norm — không bị per-norm cap cắt xén.

ScoredTextUnit là output TypedDict — text_unit_id cho phép TASK-13 fetch text từ Neo4j.
"""
import logging
import re
import unicodedata
from typing import TypedDict

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from src.ingestion.vectorizer import encode_text

logger = logging.getLogger(__name__)

_RRF_K = 60
_DENSE_POOL_MULTIPLIER = 2   # lấy 2*top_k từ dense search trước khi re-rank
_DENSE_POOL_MIN = 50         # pool tối thiểu để đảm bảo đủ ứng viên dense
_KEYWORD_SCROLL_LIMIT = 200  # scroll tối đa cho keyword path


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class ScoredTextUnit(TypedDict):
    text_unit_id: str     # 16-char hex — dùng để fetch text từ Neo4j trong TASK-13
    rrf_score: float
    norm_id: str
    component_id: str
    jurisdiction: str
    tier: int | None
    theme: str
    valid_from: str | None
    valid_to: str | None


# ---------------------------------------------------------------------------
# Keyword helpers
# ---------------------------------------------------------------------------

def _slugify_tokens(text: str) -> set[str]:
    """Chuyển text thành set token ASCII không dấu — dùng cho keyword matching.

    Ví dụ: "Nghị định 102/2024/NĐ-CP" → {"nghi", "dinh", "102", "2024", "nd", "cp"}

    Lưu ý: đ/Đ không decompose theo NFKD nên phải replace thủ công trước.
    """
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return {t for t in re.split(r"[^a-z0-9]+", ascii_text) if len(t) > 1}


def _keyword_score(query_tokens: set[str], payload: dict) -> float:
    """Tỉ lệ query tokens xuất hiện trong norm_id + component_id của payload.

    Cho phép bắt số hiệu văn bản chính xác (Gap 3 — exact citation matching).
    """
    if not query_tokens:
        return 0.0
    payload_text = f"{payload.get('norm_id', '')} {payload.get('component_id', '')}"
    payload_tokens = _slugify_tokens(payload_text)
    overlap = len(query_tokens & payload_tokens)
    return overlap / len(query_tokens)


# ---------------------------------------------------------------------------
# RRF
# ---------------------------------------------------------------------------

def _rrf_score(dense_rank: int, keyword_rank: int, k: int = _RRF_K) -> float:
    return 1.0 / (k + dense_rank) + 1.0 / (k + keyword_rank)


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------

def _qdrant_id_to_hex(qdrant_id: int) -> str:
    """Chuyển Qdrant integer point ID về lại 16-char hex (text_unit_id)."""
    return format(qdrant_id, "016x")


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def _scroll_keyword_candidates(
    qdrant_client: QdrantClient,
    search_filter: Filter,
    query_tokens: set[str],
    limit: int,
) -> list:
    """Scroll text_units trong norm_ids, score theo keyword, trả về top `limit` điểm."""
    points, _ = qdrant_client.scroll(
        "legal_texts",
        scroll_filter=search_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    # Sắp xếp theo keyword score giảm dần, giữ lại top `limit`
    scored = sorted(
        points,
        key=lambda p: _keyword_score(query_tokens, p.payload),
        reverse=True,
    )
    return scored


def hybrid_search(
    question: str,
    norm_ids: list[str],
    qdrant_client: QdrantClient,
    model,
    top_k: int = 10,
) -> list[ScoredTextUnit]:
    """Hybrid search: Dense (BGE-M3) + Keyword (slug scroll) → RRF fusion → Top-k.

    Hai path độc lập:
    - Dense path: semantic embedding search → top dense_pool results
    - Keyword path: scroll all text_units trong norm_ids → score theo slug overlap → top keyword_pool
    RRF merger: điểm không có trong list → rank cuối (len+1).

    Args:
        question: Câu hỏi tiếng Việt gốc từ người dùng.
        norm_ids: List norm_ids từ Sub-graph Extraction (TASK-11, P2 fix).
                  Dùng filter norm_id IN norm_ids thay vì component_id IN lccids.
        qdrant_client: Qdrant client đã kết nối.
        model: BGE-M3 model đã load.
        top_k: Số kết quả tối đa trả về.

    Returns:
        List ScoredTextUnit sắp xếp theo rrf_score giảm dần.
        Trả về [] nếu norm_ids rỗng hoặc không có kết quả.
    """
    if not norm_ids:
        logger.warning("hybrid_search: norm_ids rỗng — trả về []")
        return []

    dense_pool = max(top_k * _DENSE_POOL_MULTIPLIER, _DENSE_POOL_MIN)
    query_tokens = _slugify_tokens(question)

    search_filter = Filter(
        must=[
            FieldCondition(key="content_type", match=MatchValue(value="text_unit")),
            FieldCondition(key="norm_id", match=MatchAny(any=norm_ids)),
        ]
    )

    # --- Path 1: Dense search ---
    query_vector = encode_text(model, question)
    dense_results = qdrant_client.query_points(
        "legal_texts",
        query=query_vector,
        limit=dense_pool,
        query_filter=search_filter,
    ).points

    # --- Path 2: Keyword search (scroll + slug scoring) ---
    keyword_results = _scroll_keyword_candidates(
        qdrant_client, search_filter, query_tokens, _KEYWORD_SCROLL_LIMIT
    )

    if not dense_results and not keyword_results:
        logger.info("hybrid_search: cả hai path đều rỗng")
        return []

    logger.info(
        f"hybrid_search: dense={len(dense_results)}, keyword={len(keyword_results)} candidates"
    )

    # --- RRF merger ---
    # Xây rank map cho mỗi path
    dense_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(dense_results)}
    keyword_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(keyword_results)}

    # Tập hợp tất cả point IDs từ cả hai path
    all_ids: dict[int, object] = {}
    for p in dense_results:
        all_ids[p.id] = p
    for p in keyword_results:
        if p.id not in all_ids:
            all_ids[p.id] = p

    dense_fallback = len(dense_results)    # rank khi không có trong dense list
    keyword_fallback = len(keyword_results)  # rank khi không có trong keyword list

    scored: list[tuple[float, object]] = []
    for pid, point in all_ids.items():
        dr = dense_rank_map.get(pid, dense_fallback)
        kr = keyword_rank_map.get(pid, keyword_fallback)
        score = _rrf_score(dr, kr)
        scored.append((score, point))

    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Build output ---
    results: list[ScoredTextUnit] = []
    for rrf_score_val, point in scored[:top_k]:
        payload = point.payload
        results.append(
            ScoredTextUnit(
                text_unit_id=_qdrant_id_to_hex(point.id),
                rrf_score=round(rrf_score_val, 6),
                norm_id=payload.get("norm_id", ""),
                component_id=payload.get("component_id", ""),
                jurisdiction=payload.get("jurisdiction", ""),
                tier=payload.get("tier"),
                theme=payload.get("theme", ""),
                valid_from=payload.get("valid_from"),
                valid_to=payload.get("valid_to"),
            )
        )

    if results:
        logger.info(
            f"hybrid_search: top-{len(results)} | "
            f"best rrf={results[0]['rrf_score']:.4f} norm={results[0]['norm_id']}"
        )
    return results
