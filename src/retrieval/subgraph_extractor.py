"""
Sub-graph Extractor — TASK-11
Nhận QueryPlan từ TASK-10, trả về LCCIDs (list Component IDs) qua 2 bước:

Stage 1 — Qdrant semantic search:
    Encode câu hỏi bằng BGE-M3 → search summary vectors
    filter content_type="summary" + theme → top-N norm_ids

Stage 2 — Neo4j graph traversal:
    Từ seed norm_ids, mở rộng qua [:IMPLEMENTS] (cả chiều lên và xuống)
    Lọc cứng theo jurisdiction qua [:APPLIES_TO]
    Lọc temporal theo CTV.valid_from / CTV.valid_to
    → trả về DISTINCT Component IDs

Cypher Stage 2 (template):

    UNWIND $seed_ids AS seed_id
    MATCH (seed:Norm {id: seed_id})
    MATCH (related:Norm)
    WHERE related.id = seed_id
       OR (seed)-[:IMPLEMENTS*0..4]->(related)
    MATCH (related)-[:APPLIES_TO]->(j:Jurisdiction)
    WHERE j.name IN $allowed_jurisdictions
    MATCH (related)-[:HAS_COMPONENT]->(c:Component)-[:HAS_CTV]->(v:CTV)
    WHERE ($temporal IS NULL OR v.valid_from <= $temporal)
      AND ($temporal IS NULL OR v.valid_to IS NULL OR v.valid_to >= $temporal)
    RETURN DISTINCT c.id AS component_id

Chiến lược traversal (bottom-up):
    Stage 1 tìm norm CỤ THỂ nhất (tier cao) khớp câu hỏi.
    Stage 2 leo lên luật cha (upward-only) — không mở rộng xuống implementors.
    Tránh LCCID explosion khi seed là Luật (tier 1) với 15+ implementors.
"""
import logging

from neo4j import Driver
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.ingestion.vectorizer import encode_text
from src.retrieval.query_planner import QueryPlan

logger = logging.getLogger(__name__)

LCCID_LIMIT = 200  # cảnh báo nếu vượt mức này

# jurisdiction → danh sách jurisdiction được phép (quốc gia luôn được bao gồm)
_JURISDICTION_ALLOW = {
    "toan-quoc": ["toan-quoc"],
    "tp-hcm": ["toan-quoc", "tp-hcm"],
    "dong-nai": ["toan-quoc", "dong-nai"],
}

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

LCCIDs = list[str]

# ---------------------------------------------------------------------------
# Stage 1 — Qdrant semantic search trên summary vectors
# ---------------------------------------------------------------------------

_STAGE2_CYPHER = """
UNWIND $seed_ids AS seed_id
MATCH (seed:Norm {id: seed_id})
MATCH (related:Norm)
WHERE related.id = seed_id
   OR (seed)-[:IMPLEMENTS*0..4]->(related)
MATCH (related)-[:APPLIES_TO]->(j:Jurisdiction)
WHERE j.name IN $allowed_jurisdictions
MATCH (related)-[:HAS_COMPONENT]->(c:Component)-[:HAS_CTV]->(v:CTV)
WHERE ($temporal IS NULL OR v.valid_from <= $temporal)
  AND ($temporal IS NULL OR v.valid_to IS NULL OR v.valid_to >= $temporal)
RETURN DISTINCT c.id AS component_id
"""


def stage1_norm_ids(
    question: str,
    query_plan: QueryPlan,
    qdrant_client: QdrantClient,
    model,
    top_n: int = 3,
    min_score: float = 0.3,
) -> list[str]:
    """Stage 1: encode câu hỏi → search summary vectors → trả về top-N norm_ids.

    Args:
        question: Câu hỏi tiếng Việt gốc từ người dùng.
        query_plan: QueryPlan đã được plan_query() tạo ra.
        qdrant_client: Qdrant client đã kết nối.
        model: BGE-M3 model đã load.
        top_n: Số norm_ids tối đa trả về.
        min_score: Ngưỡng similarity tối thiểu; kết quả dưới ngưỡng bị loại.
                   Fallback: luôn giữ ít nhất top-1 dù dưới ngưỡng.

    Returns:
        List norm_ids được sắp xếp theo độ liên quan giảm dần.
    """
    theme = query_plan.get("theme")
    if not theme:
        logger.warning("stage1_norm_ids: theme=None — không thể filter, trả về []")
        return []

    vector = encode_text(model, question)

    must_conditions = [
        FieldCondition(key="content_type", match=MatchValue(value="summary")),
        FieldCondition(key="theme", match=MatchValue(value=theme)),
    ]

    results = qdrant_client.query_points(
        "legal_texts",
        query=vector,
        limit=top_n,
        query_filter=Filter(must=must_conditions),
    ).points

    scores = [r.score for r in results]
    norm_ids = [r.payload["norm_id"] for r in results if r.score >= min_score]

    # Fallback: giữ ít nhất top-1 dù dưới ngưỡng
    if not norm_ids and results:
        norm_ids = [results[0].payload["norm_id"]]

    logger.info(
        f"Stage 1: top-{top_n} scores={[round(s, 3) for s in scores]}, "
        f"threshold={min_score} → {len(norm_ids)} norm_ids = {norm_ids}"
    )
    return norm_ids


# ---------------------------------------------------------------------------
# Stage 2 — Neo4j graph traversal → Component IDs
# ---------------------------------------------------------------------------

def stage2_component_ids(
    norm_ids: list[str],
    query_plan: QueryPlan,
    neo4j_driver: Driver,
) -> LCCIDs:
    """Stage 2: từ seed norm_ids, duyệt graph → Component IDs.

    Chiến lược bottom-up: chỉ đi lên (seed → luật cha) qua [:IMPLEMENTS*0..4].
    Không mở rộng xuống implementors để tránh LCCID explosion.
    Lọc cứng theo jurisdiction và temporal.

    Args:
        norm_ids: Danh sách norm_ids từ Stage 1.
        query_plan: QueryPlan chứa jurisdiction và temporal.
        neo4j_driver: Neo4j driver đã kết nối.

    Returns:
        List component_id (DISTINCT), tối đa LCCID_LIMIT.
    """
    if not norm_ids:
        logger.warning("stage2_component_ids: norm_ids rỗng — trả về []")
        return []

    jurisdiction = query_plan.get("jurisdiction") or "toan-quoc"
    allowed = _JURISDICTION_ALLOW.get(jurisdiction, ["toan-quoc"])
    temporal = query_plan.get("temporal")

    params = {
        "seed_ids": norm_ids,
        "allowed_jurisdictions": allowed,
        "temporal": temporal,
    }

    with neo4j_driver.session() as session:
        rows = session.run(_STAGE2_CYPHER, **params).data()

    component_ids = [r["component_id"] for r in rows]

    if len(component_ids) > LCCID_LIMIT:
        logger.warning(
            f"Stage 2: {len(component_ids)} LCCIDs vượt giới hạn {LCCID_LIMIT} — "
            f"kết quả có thể quá rộng, gây noise. Cân nhắc giảm top_n Stage 1."
        )

    logger.info(
        f"Stage 2: {len(component_ids)} component_ids "
        f"(jurisdiction={jurisdiction}, temporal={temporal})"
    )
    return component_ids


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract_subgraph(
    question: str,
    query_plan: QueryPlan,
    neo4j_driver: Driver,
    qdrant_client: QdrantClient,
    model,
    top_n: int = 3,
) -> LCCIDs:
    """Orchestrator: Stage 1 + Stage 2 → LCCIDs.

    Args:
        question: Câu hỏi tiếng Việt gốc từ người dùng.
        query_plan: QueryPlan đã được plan_query() tạo ra.
        neo4j_driver: Neo4j driver đã kết nối.
        qdrant_client: Qdrant client đã kết nối.
        model: BGE-M3 model đã load.
        top_n: Số norm_ids tối đa Stage 1 trả về.

    Returns:
        LCCIDs — list Component IDs dùng làm đầu vào cho Semantic Filtering.
    """
    norm_ids = stage1_norm_ids(question, query_plan, qdrant_client, model, top_n)
    return stage2_component_ids(norm_ids, query_plan, neo4j_driver)
