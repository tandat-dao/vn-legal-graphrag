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

# ---------------------------------------------------------------------------
# Structured Citation Extraction — for Pass -1 boost
# ---------------------------------------------------------------------------
# Khi câu hỏi đề cập trực tiếp tham chiếu cấu trúc ("Khoản X Điều Y", "Điều Y"),
# Pass -1 ép Components matching cấu trúc này vào output trước cả Pass 0
# (dense floor). Lý do: user (chuyên viên pháp lý) thường truy vấn trực tiếp
# điều khoản; embedding similarity có thể không xếp đúng chunk lên đầu do
# label dài và mâu thuẫn với câu hỏi tự nhiên.
#
# Phải robust với: dấu thanh tiếng Việt (Khoản/Khoản), dạng số (1/01), Điểm.
_STRUCT_CITE_KHOAN_RE = re.compile(
    r"[Kk]ho[ảà]n\s+(\d+\w*)\s+(?:c[ủù]a\s+)?[ĐĐdd]i[ềê]u\s+(\d+\w*)",
)
_STRUCT_CITE_DIEU_ONLY_RE = re.compile(
    r"[ĐĐdd]i[ềê]u\s+(\d+\w*)"
)


def _extract_struct_cites(question: str) -> list[tuple[str, str | None]]:
    """Trả về list (dieu, khoan|None) từ câu hỏi.

    Quy tắc:
      - "Khoản X Điều Y" hoặc "Khoản X của Điều Y" → (Y, X)
      - "Điều Y" trần (không có Khoản đi kèm) → (Y, None)
      - Loại trùng: nếu (Y, X) đã có thì bỏ qua (Y, None)

    Returns:
        List of tuples sorted để deterministic.
    """
    pairs: list[tuple[str, str | None]] = []
    seen_dieu_with_khoan: set[str] = set()
    # Pass khoan+dieu trước (specific hơn)
    for m in _STRUCT_CITE_KHOAN_RE.finditer(question):
        khoan, dieu = m.group(1), m.group(2)
        key = (dieu, khoan)
        if key not in pairs:
            pairs.append(key)
            seen_dieu_with_khoan.add(dieu)
    # Sau đó dieu-only (skip nếu đã có khoan của dieu đó)
    for m in _STRUCT_CITE_DIEU_ONLY_RE.finditer(question):
        dieu = m.group(1)
        if dieu in seen_dieu_with_khoan:
            continue
        key_dieu_only = (dieu, None)
        if key_dieu_only not in pairs:
            pairs.append(key_dieu_only)
    return pairs


def _fetch_components_matching_cites(
    cites: list[tuple[str, str | None]],
    norm_ids: list[str],
    neo4j_driver,
) -> dict[str, dict]:
    """Fetch Component IDs matching structured citation patterns trong norms.

    Cho mỗi (dieu, khoan|None), tìm Components có label STARTS WITH 'Điều {dieu}.'
    AND (nếu khoan != None) CONTAINS 'Khoản {khoan}.'.

    Returns:
        Dict {component_id: {label, norm_id, dieu, khoan}}.
    """
    if not cites or not norm_ids or neo4j_driver is None:
        return {}
    result: dict[str, dict] = {}
    with neo4j_driver.session() as sess:
        for dieu, khoan in cites:
            dieu_pat = f"Điều {dieu}."
            if khoan is not None:
                khoan_pat = f"Khoản {khoan}."
                rows = sess.run(
                    "MATCH (n:Norm)-[:HAS_COMPONENT]->(c:Component) "
                    "WHERE n.id IN $norms AND c.label STARTS WITH $dieu_pat "
                    "AND c.label CONTAINS $khoan_pat "
                    "RETURN c.id AS cid, c.label AS label, n.id AS norm_id",
                    norms=norm_ids, dieu_pat=dieu_pat, khoan_pat=khoan_pat,
                ).data()
            else:
                rows = sess.run(
                    "MATCH (n:Norm)-[:HAS_COMPONENT]->(c:Component) "
                    "WHERE n.id IN $norms AND c.label STARTS WITH $dieu_pat "
                    "RETURN c.id AS cid, c.label AS label, n.id AS norm_id",
                    norms=norm_ids, dieu_pat=dieu_pat,
                ).data()
            for r in rows:
                if r["cid"] not in result:
                    result[r["cid"]] = {
                        "label": r["label"], "norm_id": r["norm_id"],
                        "dieu": dieu, "khoan": khoan,
                    }
    return result


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

_RARITY_ALPHA = 1.5            # hệ số trọng số cho concept rarity boost
                              # multiplier = 1 + α × rarity_score
                              # α=1.5 đủ mạnh để pull Điều chuyên sâu (ít concept hiếm
                              # trong norm) lên trên Điều tổng quát (concept phổ biến)


def _rrf_score(
    dense_rank: int,
    keyword_rank: int,
    k: int = _RRF_K,
    is_graph_boosted: bool = False,
    tier: int = 1,
    rarity_score: float = 0.0,
) -> float:
    base_score = 1.0 / (k + dense_rank) + 1.0 / (k + keyword_rank)

    # Tier multiplier: ưu tiên quy định địa phương (Lex Specialis)
    # Tier 4 -> x1.4 | Tier 1 -> x1.1
    tier_multiplier = 1.0 + (tier * 0.1)

    # Graph Boost -> x100.0 (đẩy nhóm graph-mapped lên trên Vector thuần)
    graph_multiplier = 100.0 if is_graph_boosted else 1.0

    # Concept Rarity boost (TF-IDF trên đồ thị):
    # Component bao phủ concept HIẾM trong norm của nó = chuyên sâu = boost.
    # Khắc phục bias dense embedding ưu ái Điều tổng quát (Phạm vi, Đối tượng)
    # đè Điều chuyên sâu chứa số liệu cụ thể (30/50/100%, 160m²).
    rarity_multiplier = 1.0 + _RARITY_ALPHA * rarity_score

    return base_score * tier_multiplier * graph_multiplier * rarity_multiplier


# ---------------------------------------------------------------------------
# Concept Rarity (TF-IDF trên đồ thị)
# ---------------------------------------------------------------------------

def _fetch_norm_concept_stats(norm_ids: list[str], neo4j_driver) -> tuple[dict, dict]:
    """Fetch concept frequency stats cho từng norm trong pool.

    Args:
        norm_ids: List norm_ids trong retrieval pool.
        neo4j_driver: Neo4j driver.

    Returns:
        Tuple (norm_total_components, norm_concept_count):
        - norm_total_components: {norm_id: total số Component có ≥1 concept mapped}
        - norm_concept_count: {(norm_id, concept_id): số Component trong norm có concept này}
    """
    if not norm_ids:
        return {}, {}
    cypher = """
    UNWIND $norm_ids AS nid
    MATCH (n:Norm {id: nid})-[:HAS_COMPONENT]->(c:Component)
    OPTIONAL MATCH (c)-[:MAPS_TO_CONCEPT]->(con:Concept)
    RETURN nid AS norm_id, c.id AS comp_id, collect(DISTINCT con.id) AS concepts
    """
    with neo4j_driver.session() as s:
        rows = s.run(cypher, norm_ids=norm_ids).data()

    norm_total: dict[str, int] = {}
    norm_concept_count: dict[tuple[str, str], int] = {}
    for row in rows:
        nid = row["norm_id"]
        concepts = [c for c in row["concepts"] if c is not None]
        if concepts:  # chỉ đếm component có ≥1 concept mapped
            norm_total[nid] = norm_total.get(nid, 0) + 1
            for concept in concepts:
                key = (nid, concept)
                norm_concept_count[key] = norm_concept_count.get(key, 0) + 1
    return norm_total, norm_concept_count


def _fetch_component_concepts(component_ids: list[str], neo4j_driver) -> dict[str, list[str]]:
    """Fetch concept mapping cho từng component candidate.

    Returns:
        {component_id: [concept_id, ...]}
    """
    if not component_ids:
        return {}
    cypher = """
    UNWIND $cids AS cid
    MATCH (c:Component {id: cid})
    OPTIONAL MATCH (c)-[:MAPS_TO_CONCEPT]->(con:Concept)
    RETURN cid AS comp_id, collect(DISTINCT con.id) AS concepts
    """
    with neo4j_driver.session() as s:
        rows = s.run(cypher, cids=list(set(component_ids))).data()
    return {r["comp_id"]: [c for c in r["concepts"] if c is not None] for r in rows}


def _fetch_required_concepts(procedure_id: str, neo4j_driver) -> set[str]:
    """Fetch concept ids mà procedure require."""
    if not procedure_id:
        return set()
    cypher = """
    MATCH (p:Procedure {id: $pid})-[:REQUIRES_CONCEPT]->(c:Concept)
    RETURN collect(c.id) AS concepts
    """
    with neo4j_driver.session() as s:
        res = s.run(cypher, pid=procedure_id).data()
    if not res:
        return set()
    return set(res[0]["concepts"])


def _compute_rarity(
    comp_concepts: list[str],
    norm_id: str,
    required_concepts: set[str],
    norm_total: dict[str, int],
    norm_concept_count: dict[tuple[str, str], int],
) -> float:
    """Tính concept rarity score cho 1 component — dùng MAX rarity.

    Rarity(C, norm) = 1 - (count(C in norm) / total_components(norm))
    Score = MAX rarity(C, norm) cho C ∈ comp_concepts ∩ required_concepts

    Nguyên lý TF-IDF (graph variant) — MAX thay vì SUM:
    Một component được boost theo concept HIẾM NHẤT mà nó bao phủ trong norm.
    Lý do dùng MAX không dùng SUM: SUM thưởng cho component có NHIỀU concept
    (kể cả concept phổ biến), gây bias về Điều tổng quát ("Phạm vi điều chỉnh",
    "Đối tượng áp dụng" — gắn nhiều concept một cách lướt qua). MAX phản ánh
    đúng degree of SPECIALIZATION: component "chuyên sâu" về 1 concept hiếm
    (vd: hạn mức 160m² của QĐ 69 Đ3) được boost mạnh, không bị diluted bởi
    concept phổ biến đi kèm.

    Score nằm trong [0, 1].
    """
    if not comp_concepts or not required_concepts or not norm_id:
        return 0.0
    total = norm_total.get(norm_id, 0)
    if total == 0:
        return 0.0
    relevant = set(comp_concepts) & required_concepts
    if not relevant:
        return 0.0
    max_rarity = 0.0
    for concept in relevant:
        count = norm_concept_count.get((norm_id, concept), 0)
        rarity = 1.0 - (count / total) if total > 0 else 0.0
        if rarity > max_rarity:
            max_rarity = rarity
    return max_rarity


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
    neo4j_driver=None,
    procedure_id: str | None = None,
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

    # --- Path -1: Structured Citation explicit fetch ---
    # Khi câu hỏi đề cập trực tiếp "Khoản X Điều Y" / "Điều Y", fetch Components
    # matching cấu trúc này → ép vào output trước (Pass -1 trong allocation phase).
    # Đây là **additive boost** (không filter strict): nếu pattern không match,
    # priority_points = [] và pipeline fallback về dense/keyword/graph + Pass 0/1/2.
    struct_cites = _extract_struct_cites(question)
    priority_points = []
    priority_comp_meta: dict[str, dict] = {}
    if struct_cites and neo4j_driver is not None:
        priority_comp_meta = _fetch_components_matching_cites(struct_cites, norm_ids, neo4j_driver)
        if priority_comp_meta:
            cite_filter = Filter(
                must=[
                    FieldCondition(key="content_type", match=MatchValue(value="text_unit")),
                    FieldCondition(key="norm_id", match=MatchAny(any=norm_ids)),
                    FieldCondition(key="component_id", match=MatchAny(any=list(priority_comp_meta.keys()))),
                ]
            )
            pts, _ = qdrant_client.scroll(
                "legal_texts",
                scroll_filter=cite_filter,
                limit=200,
                with_payload=True,
                with_vectors=False,
            )
            priority_points = pts
        logger.info(
            f"hybrid_search Path -1 (struct cite): cites={struct_cites} → "
            f"{len(priority_comp_meta)} comps → {len(priority_points)} text_units"
        )

    if not dense_results and not keyword_results and not graph_results and not priority_points:
        logger.info("hybrid_search: tất cả các path đều rỗng")
        return []

    logger.info(
        f"hybrid_search: dense={len(dense_results)}, keyword={len(keyword_results)}, graph={len(graph_results)} candidates"
    )

    # --- RRF merger ---
    # Xây rank map cho mỗi path
    dense_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(dense_results)}
    keyword_rank_map: dict[int, int] = {p.id: rank for rank, p in enumerate(keyword_results)}

    # Tập hợp tất cả point IDs từ cả 4 path (dense, keyword, graph, priority)
    all_ids: dict[int, object] = {}
    for p in dense_results:
        all_ids[p.id] = p
    for p in keyword_results:
        if p.id not in all_ids:
            all_ids[p.id] = p
    for p in graph_results:
        if p.id not in all_ids:
            all_ids[p.id] = p
    for p in priority_points:
        if p.id not in all_ids:
            all_ids[p.id] = p

    dense_fallback = len(dense_results)    # rank khi không có trong dense list
    keyword_fallback = len(keyword_results)  # rank khi không có trong keyword list
    graph_boost_set = set(graph_component_ids or [])

    # Concept Rarity stats: fetch một lần cho toàn pool, dùng làm TF-IDF graph signal.
    # Chỉ activate khi có neo4j_driver + procedure_id (backward compat).
    norm_total: dict[str, int] = {}
    norm_concept_count: dict[tuple[str, str], int] = {}
    component_concepts: dict[str, list[str]] = {}
    required_concepts: set[str] = set()
    rarity_enabled = neo4j_driver is not None and procedure_id is not None
    if rarity_enabled:
        candidate_norm_ids = list({p.payload.get("norm_id", "") for p in all_ids.values() if p.payload.get("norm_id")})
        candidate_comp_ids = list({p.payload.get("component_id", "") for p in all_ids.values() if p.payload.get("component_id")})
        norm_total, norm_concept_count = _fetch_norm_concept_stats(candidate_norm_ids, neo4j_driver)
        component_concepts = _fetch_component_concepts(candidate_comp_ids, neo4j_driver)
        required_concepts = _fetch_required_concepts(procedure_id, neo4j_driver)
        logger.info(
            f"hybrid_search: rarity stats — {len(norm_total)} norms, "
            f"{len(component_concepts)} components mapped, {len(required_concepts)} required concepts"
        )

    scored: list[tuple[float, object]] = []
    for pid, point in all_ids.items():
        dr = dense_rank_map.get(pid, dense_fallback)
        kr = keyword_rank_map.get(pid, keyword_fallback)
        comp_id = point.payload.get("component_id", "")
        nid = point.payload.get("norm_id", "")
        tier = point.payload.get("tier") or 1
        is_boosted = comp_id in graph_boost_set
        rarity = 0.0
        if rarity_enabled:
            rarity = _compute_rarity(
                component_concepts.get(comp_id, []),
                nid,
                required_concepts,
                norm_total,
                norm_concept_count,
            )
        score = _rrf_score(dr, kr, is_graph_boosted=is_boosted, tier=tier, rarity_score=rarity)
        scored.append((score, point))

    scored.sort(key=lambda x: x[0], reverse=True)

    # --- Build output: 3-pass allocation (dense-floor + RRF-breadth + RRF-depth) ---
    #
    # Pass 0 (DENSE FLOOR — added 2026-05-19): top-1 per norm theo DENSE RANK.
    #   Lý do: bảo toàn pure semantic match — embedding similarity là ground
    #   signal mạnh nhất, KG/graph boost (procedure mapping ở Stage 3) chỉ là
    #   context augmentation, KHÔNG được override. Đã quan sát: Q024 GT
    #   "Điều 116 K5 Luật ĐĐ 2024" rank #2 trong dense bị drop khỏi top-25 vì
    #   graph_boost của procedure "chuyen-muc-dich-su-dung-dat" đẩy Điều
    #   121/123/227 lên đầu RRF, chiếm hết per-norm cap (3). Pass 0 ép top-1
    #   dense per norm vào output trước khi RRF re-rank chạy.
    #
    # Pass 1 (breadth): top-1 per norm THEO RRF — bổ sung norms chưa được
    #   Pass 0 cover (norms không có chunk trong dense_results vì dense_pool
    #   hữu hạn — nhưng có trong keyword/graph paths).
    #
    # Pass 2 (depth): fill remaining slots theo RRF order, respect cả 2 cap.
    #
    # Cả 3 pass đều tôn trọng per-tier cap (đa dạng tầng pháp lý) và per-norm
    # cap (chống dominance).
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

    # Helper: tính lại RRF score cho 1 point (dùng trong Pass 0 để log + try_add)
    def _rrf_for(point) -> float:
        pid = point.id
        dr = dense_rank_map.get(pid, dense_fallback)
        kr = keyword_rank_map.get(pid, keyword_fallback)
        comp_id = point.payload.get("component_id", "")
        nid_ = point.payload.get("norm_id", "")
        tier = point.payload.get("tier") or 1
        is_boosted = comp_id in graph_boost_set
        rarity = 0.0
        if rarity_enabled:
            rarity = _compute_rarity(
                component_concepts.get(comp_id, []),
                nid_,
                required_concepts,
                norm_total,
                norm_concept_count,
            )
        return _rrf_score(dr, kr, is_graph_boosted=is_boosted, tier=tier, rarity_score=rarity)

    # Pass -1 (STRUCTURED CITATION BOOST): force priority components vào output
    # Lý do: khi user gõ trực tiếp "Khoản X Điều Y" (chuyên viên pháp lý), retrieval
    # PHẢI bảo đảm chunk khớp cấu trúc xuất hiện trong context, bất kể dense rank
    # hay graph_boost ưu tiên gì khác. Quan sát Q026: GT là "Đ13 K1 NĐ 49" nhưng
    # dense top của NĐ 49 = K11/K12 vì label dài 200+ chars chứa metadata sửa
    # đổi → mô hình embedding match toàn label, không phân biệt được Khoản.
    pass_neg1_count = 0
    if priority_points:
        for point in priority_points:
            if len(results) >= top_k:
                break
            rrf_val = _rrf_for(point)
            if _try_add(rrf_val, point):
                pass_neg1_count += 1

    # Pass 0 (DENSE FLOOR): top-1 per norm theo DENSE RANK
    seen_norms_in_pass0: set = set()
    for point in dense_results:  # already sorted by dense score desc
        if len(results) >= top_k:
            break
        nid = point.payload.get("norm_id", "")
        if nid in seen_norms_in_pass0:
            continue
        if point.id in used_point_ids:
            seen_norms_in_pass0.add(nid)
            continue
        rrf_val = _rrf_for(point)
        if _try_add(rrf_val, point):
            seen_norms_in_pass0.add(nid)
    pass0_count = len(results) - pass_neg1_count

    # Pass 1: top-1 per norm theo RRF (bổ sung norms chưa có trong Pass 0)
    seen_norms_in_pass1: set = set(seen_norms_in_pass0)
    for rrf_score_val, point in scored:
        if len(results) >= top_k:
            break
        nid = point.payload.get("norm_id", "")
        if nid in seen_norms_in_pass1:
            continue
        if _try_add(rrf_score_val, point):
            seen_norms_in_pass1.add(nid)
    pass1_count = len(results) - pass0_count

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
            f"hybrid_search: top-{len(results)} | pass-1(struct-cite)={pass_neg1_count}, "
            f"pass0(dense-floor)={pass0_count}, pass1(rrf-breadth)={pass1_count}, "
            f"pass2(depth)={len(results) - pass_neg1_count - pass0_count - pass1_count} | "
            f"caps: per_norm={_MAX_PER_NORM}, per_tier={_MAX_PER_TIER} | "
            f"best rrf={results[0]['rrf_score']:.4f} | tier_dist={tier_dist} | norm_dist={norm_dist}"
        )
    return results

