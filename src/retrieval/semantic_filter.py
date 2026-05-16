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
_KEYWORD_MIN_SCORE = 0.5     # ngưỡng tối thiểu để text_unit được tham gia keyword path
                              # — tránh nhiễu khi query chứa "tp"/"hcm" match nhẹ với norm_id
_MAX_PER_NORM = 3             # tối đa N TextUnit từ cùng 1 norm trong top-k output
                              # — tránh norm lớn (Luật ĐĐ 2024, ~2800 TU) chiếm hết slot
                              # — đảm bảo các norm match dense kém (NĐ 50, QĐ 69) vẫn có
                              # representation thay vì bị 1-2 norm match tốt đè trong cùng tier
                              # — với ~13 norm trong pool: 13×3=39 slot tiềm năng > top_k=25,
                              # đủ chỗ cho mọi norm có RRF reasonable, đảm bảo norm-breadth

# Tier Diversity Constraint: stratified cap per tier để đảm bảo top-k bao phủ
# đa tầng pháp lý (Luật + NĐ + TT + QĐ địa phương). Câu trả lời pháp lý cho
# thủ tục hành chính thường cần tổng hợp đa tầng:
#   - Tier 1: định nghĩa khung pháp lý
#   - Tier 2: nghị định hướng dẫn chi tiết
#   - Tier 3: thông tư cụ thể
#   - Tier 4: quy định địa phương (hạn mức, lệ phí)
# Cap này NGĂN một tier (đặc biệt Tier 4 với nhiều norms địa phương) áp đảo
# top-k và đẩy các tier khác (NĐ 50/2026 Đ6 30/50/100% — Tier 2) khỏi context.
#
# Khác với "tier multiplier" có rủi ro nhầm Lex Superior (conflict-resolution)
# với Information Relevance (Lex Specialis): diversity constraint TÔN TRỌNG
# cả 2 nguyên tắc bằng cách đảm bảo chỗ cho mọi tier, để LLM tự suy luận
# qua header [Tier X | Hiệu lực: ...] khi có mâu thuẫn.
_MAX_PER_TIER = {1: 8, 2: 8, 3: 6, 4: 8}
_MAX_PER_TIER_DEFAULT = 25    # tier=None hoặc ngoài 1-4: không cap

# Regex strip địa danh jurisdiction khỏi query trước dense encoding (P3 fix).
# Jurisdiction đã được xử lý ở Stage 2 (Neo4j APPLIES_TO + norm_id filter).
# Giữ lại "tại TP.HCM" trong dense query gây locality bias: BGE-M3 ưu tiên
# text units địa phương (lệ phí, bảng giá) và đẩy Điều 121/122 ra khỏi top-k.
_JURISDICTION_STRIP_RE = re.compile(
    r"\b(?:tại|ở|trên\s+địa\s+bàn(?:\s+tỉnh)?)\s+"
    r"(?:TP\.?\s*HCM|TP\.?\s*Hồ\s+Chí\s+Minh|Thành\s+phố\s+Hồ\s+Chí\s+Minh|TPHCM"
    r"|Đồng\s+Nai|tỉnh\s+Đồng\s+Nai)",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Query preprocessing
# ---------------------------------------------------------------------------

def _strip_jurisdiction_for_dense(question: str) -> str:
    """Strip địa danh jurisdiction khỏi câu hỏi trước khi encode dense vector.

    Ví dụ:
        "Điều kiện CMĐSDĐ tại TP.HCM là gì?" → "Điều kiện CMĐSDĐ là gì?"
        "Quy trình cấp sổ đỏ ở Đồng Nai"    → "Quy trình cấp sổ đỏ"

    Trả về question gốc nếu sau khi strip không còn nội dung.
    """
    stripped = _JURISDICTION_STRIP_RE.sub("", question)
    stripped = re.sub(r" {2,}", " ", stripped).strip()
    return stripped or question


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

def _rrf_score(dense_rank: int, keyword_rank: int, k: int = _RRF_K, is_graph_boosted: bool = False, tier: int = 1) -> float:
    base_score = 1.0 / (k + dense_rank) + 1.0 / (k + keyword_rank)
    
    # Bảo toàn phân phối: Dùng phép nhân trọng số (Multiplier)
    # Tier 4 -> x1.4 | Tier 1 -> x1.1
    tier_multiplier = 1.0 + (tier * 0.1)
    
    # Graph Boost -> x100.0 (Đẩy vọt nhóm Graph lên trên nhóm Vector thuần)
    graph_multiplier = 100.0 if is_graph_boosted else 1.0
    
    return base_score * tier_multiplier * graph_multiplier


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
    min_score: float = _KEYWORD_MIN_SCORE,
) -> list:
    """Scroll text_units trong norm_ids, chỉ giữ text_unit có keyword score ≥ min_score.

    Mục đích: keyword path chỉ kích hoạt khi user citate cụ thể (vd "Nghị định 102/2024").
    Generic query → keyword_results = [] → RRF dùng pure dense ranking, không bị nhiễu
    bởi "tp"/"hcm" trong query khớp lệch với norm_id địa phương.
    """
    points, _ = qdrant_client.scroll(
        "legal_texts",
        scroll_filter=search_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    scored = [(p, _keyword_score(query_tokens, p.payload)) for p in points]
    filtered = [(p, s) for p, s in scored if s >= min_score]
    filtered.sort(key=lambda ps: ps[1], reverse=True)
    return [p for p, _ in filtered]


def hybrid_search(
    question: str,
    norm_ids: list[str],
    qdrant_client: QdrantClient,
    model,
    top_k: int = 10,
    graph_component_ids: list[str] = None,
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
        procedure: Loại thủ tục (từ QueryPlanner) để mở rộng dense query (tùy chọn).

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

    # --- Path 1: Dense search (dùng query đã strip jurisdiction) ---
    question_for_dense = _strip_jurisdiction_for_dense(question)
    
    query_vector = encode_text(model, question_for_dense)
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

    # --- Path 3: Graph Boost explicit fetch ---
    graph_results = []
    if graph_component_ids:
        graph_filter = Filter(
            must=[
                FieldCondition(key="content_type", match=MatchValue(value="text_unit")),
                FieldCondition(key="norm_id", match=MatchAny(any=norm_ids)),
                FieldCondition(key="component_id", match=MatchAny(any=graph_component_ids)),
            ]
        )
        points, _ = qdrant_client.scroll(
            "legal_texts",
            scroll_filter=graph_filter,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )
        graph_results = points

    if not dense_results and not keyword_results and not graph_results:
        logger.info("hybrid_search: tất cả các path đều rỗng")
        return []

    logger.info(
        f"hybrid_search: dense={len(dense_results)}, keyword={len(keyword_results)}, graph={len(graph_results)} candidates"
    )

    # --- RRF merger ---
    # Xây rank map cho mỗi path
    dense_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(dense_results)}
    keyword_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(keyword_results)}

    # Tập hợp tất cả point IDs từ cả 3 path
    all_ids: dict[int, object] = {}
    for p in dense_results:
        all_ids[p.id] = p
    for p in keyword_results:
        if p.id not in all_ids:
            all_ids[p.id] = p
    for p in graph_results:
        if p.id not in all_ids:
            all_ids[p.id] = p

    dense_fallback = len(dense_results)    # rank khi không có trong dense list
    keyword_fallback = len(keyword_results)  # rank khi không có trong keyword list
    graph_boost_set = set(graph_component_ids or [])

    scored: list[tuple[float, object]] = []
    for pid, point in all_ids.items():
        dr = dense_rank_map.get(pid, dense_fallback)
        kr = keyword_rank_map.get(pid, keyword_fallback)
        comp_id = point.payload.get("component_id", "")
        tier = point.payload.get("tier") or 1
        is_boosted = comp_id in graph_boost_set
        score = _rrf_score(dr, kr, is_graph_boosted=is_boosted, tier=tier)
        scored.append((score, point))

    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Build output: 2-pass allocation (norm-breadth + RRF-depth) ---
    #
    # Pass 1 (breadth): top-1 per norm — đảm bảo MỌI norm trong pool có ≥1
    #   representation. Khắc phục bug khi một số norm match dense kém (NĐ 50,
    #   QĐ 69 cho query "Điều kiện CMĐSDĐ") bị các norm match tốt đè trong
    #   cùng tier dù chúng chứa thông tin quan trọng (tiền SDĐ 30/50/100%,
    #   hạn mức 160m²).
    #
    # Pass 2 (depth): fill remaining slots theo RRF order, respect cả 2 cap.
    #
    # Cả 2 pass đều tôn trọng per-tier cap (đa dạng tầng pháp lý) và per-norm
    # cap (chống dominance). Pass 1 ưu tiên BREADTH; Pass 2 ưu tiên RELEVANCE.
    results: list[ScoredTextUnit] = []
    norm_count: dict[str, int] = {}
    tier_count: dict[int | None, int] = {}
    used_point_ids: set = set()

    def _try_add(rrf_score_val, point) -> bool:
        """Thêm point vào results nếu thỏa cả 2 cap. Trả True nếu thêm thành công."""
        if len(results) >= top_k:
            return False
        payload = point.payload
        nid = payload.get("norm_id", "")
        tier = payload.get("tier")
        if norm_count.get(nid, 0) >= _MAX_PER_NORM:
            return False
        tier_max = _MAX_PER_TIER.get(tier, _MAX_PER_TIER_DEFAULT)
        if tier_count.get(tier, 0) >= tier_max:
            return False
        norm_count[nid] = norm_count.get(nid, 0) + 1
        tier_count[tier] = tier_count.get(tier, 0) + 1
        used_point_ids.add(point.id)
        results.append(
            ScoredTextUnit(
                text_unit_id=_qdrant_id_to_hex(point.id),
                rrf_score=round(rrf_score_val, 6),
                norm_id=nid,
                component_id=payload.get("component_id", ""),
                jurisdiction=payload.get("jurisdiction", ""),
                tier=payload.get("tier"),
                theme=payload.get("theme", ""),
                valid_from=payload.get("valid_from"),
                valid_to=payload.get("valid_to"),
            )
        )
        return True

    # Pass 1: top-1 per norm (breadth guarantee)
    seen_norms_in_pass1: set = set()
    for rrf_score_val, point in scored:
        if len(results) >= top_k:
            break
        nid = point.payload.get("norm_id", "")
        if nid in seen_norms_in_pass1:
            continue
        if _try_add(rrf_score_val, point):
            seen_norms_in_pass1.add(nid)
    pass1_count = len(results)

    # Pass 2: fill remaining by RRF order (skip already used)
    for rrf_score_val, point in scored:
        if len(results) >= top_k:
            break
        if point.id in used_point_ids:
            continue
        _try_add(rrf_score_val, point)

    if results:
        norm_dist = {n: c for n, c in norm_count.items()}
        tier_dist = {t: c for t, c in sorted(tier_count.items(), key=lambda x: (x[0] is None, x[0]))}
        logger.info(
            f"hybrid_search: top-{len(results)} | pass1(breadth)={pass1_count}, "
            f"pass2(depth)={len(results) - pass1_count} | "
            f"caps: per_norm={_MAX_PER_NORM}, per_tier={_MAX_PER_TIER} | "
            f"best rrf={results[0]['rrf_score']:.4f} | tier_dist={tier_dist} | norm_dist={norm_dist}"
        )
    return results

