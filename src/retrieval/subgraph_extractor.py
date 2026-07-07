"""
Sub-graph Extractor — TASK-11
Nhận QueryPlan từ TASK-10, trả về norm_ids qua 2 bước:

Stage 1 — Qdrant semantic search:
    Encode câu hỏi bằng BGE-M3 → search summary vectors
    filter content_type="summary" + theme → top-N seed norm_ids

Stage 2 — Neo4j graph traversal:
    Từ seed norm_ids, mở rộng qua [:IMPLEMENTS|AMENDS*1..4] (undirected)
    Lọc cứng theo jurisdiction qua [:APPLIES_TO]
    Lọc temporal theo CTV.valid_from / CTV.valid_to
    → trả về DISTINCT norm_ids (dùng làm Qdrant filter cho Stage 3)

Thiết kế norm_id filter (P2):
    Thay vì filter component_id IN [300+ hashes], dùng norm_id IN [~13 norms].
    Cho phép BGE-M3 dense search tự chọn TextUnit tốt nhất trong mỗi norm —
    tránh per-norm cap cắt xén ngẫu nhiên các điều khoản quan trọng.

Cypher Stage 2 (template):

    UNWIND $seed_ids AS seed_id
    MATCH (seed:Norm {id: seed_id})
    MATCH (related:Norm)
    WHERE related.id = seed_id
       OR EXISTS { MATCH (seed)-[:IMPLEMENTS|AMENDS*1..4]-(related) }
    MATCH (related)-[:APPLIES_TO]->(j:Jurisdiction)
    WHERE j.name IN $allowed_jurisdictions
    MATCH (related)-[:HAS_COMPONENT]->(c:Component)-[:HAS_CTV]->(v:CTV)
    WHERE ($temporal IS NULL OR v.valid_from <= $temporal)
      AND ($temporal IS NULL OR v.valid_to >= $temporal)
    RETURN DISTINCT related.id AS norm_id, c.id AS component_id

Chiến lược traversal (composed-edge derivation closure):
    Stage 1 tìm norm khớp câu hỏi nhất qua summary embedding.
    Stage 2 mở rộng qua BAO ĐÓNG (transitive closure) của tập edge derivation
    {IMPLEMENTS, AMENDS}, undirected, depth tối đa 4 hop.

    Nguyên lý: trong KG pháp lý, quan hệ phái sinh giữa các văn bản có thể đi qua
    CHUỖI HỖN HỢP nhiều loại edge — hướng dẫn thi hành của văn bản sửa đổi cũng là
    một phần của hệ thống pháp lý hiệu lực, cần được retrieve cùng nhau.

    Ví dụ chain 2 loại edge cần bắt được (trước fix Cypher cũ không bắt được):
        (NĐ 50/2026) -[:IMPLEMENTS]-> (NQ 254) -[:AMENDS]-> (Luật ĐĐ)
        → seed=Luật ĐĐ phải reach được NĐ 50/2026 qua 2 hop AMENDS+IMPLEMENTS.

    Đảm bảo Gap 3 (đa tầng): NQ 254 K3 Đ4 (bãi bỏ HĐND) và NĐ 50/2026 Đ6 (tỷ lệ
    30%/50%/100% tiền SDĐ) đều vào search space khi user hỏi về "điều kiện CMĐSDĐ"
    có seed Stage 1 chỉ là Luật ĐĐ.
"""
import logging

from neo4j import Driver
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.ingestion.vectorizer import encode_text
from src.retrieval.ablation_config import FULL, AblationConfig
from src.retrieval.query_planner import QueryPlan

# Mọi tỉnh — dùng khi ablation no-jurisdiction (bỏ hard-filter địa phương)
_ALL_JURISDICTIONS = ["toan-quoc", "tp-hcm", "dong-nai"]

logger = logging.getLogger(__name__)

LCCID_LIMIT = 500            # cảnh báo nếu stage2_component_ids() vượt mức này
MAX_COMPONENTS_PER_NORM = 100  # cap per-norm trong stage2_component_ids() (dùng để test/debug)

# jurisdiction → danh sách jurisdiction được phép (quốc gia luôn được bao gồm)
# "multi-juris": dùng cho câu hỏi so sánh chéo nhiều tỉnh (VD Q018: HCM vs ĐN)
#   — pipeline include tất cả jurisdictions để LLM có context đầy đủ.
_JURISDICTION_ALLOW = {
    "toan-quoc": ["toan-quoc"],
    "tp-hcm": ["toan-quoc", "tp-hcm"],
    "dong-nai": ["toan-quoc", "dong-nai"],
    "multi-juris": ["toan-quoc", "tp-hcm", "dong-nai"],
}

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

LCCIDs = list[str]

# ---------------------------------------------------------------------------
# Stage 1 — Qdrant semantic search trên summary vectors
# ---------------------------------------------------------------------------

def _build_stage2_cypher(rels: list[str]) -> str:
    """Sinh Cypher traversal Stage 2 theo danh sách quan hệ (ablation-aware).

    rels rỗng (no-traversal) → chỉ lấy seed norm, không mở rộng.
    rels=['IMPLEMENTS','AMENDS'] (full) → bao đóng derivation như cũ (D-09).
    rels=['AMENDS'] (no-implements) / ['IMPLEMENTS'] (no-amends) → cắt cấp cạnh.
    """
    if rels:
        rel_pat = "|".join(rels)
        expand = f"   OR EXISTS {{ MATCH (seed)-[:{rel_pat}*1..4]-(related) }}"
    else:
        expand = ""  # chỉ seed norm
    return f"""
UNWIND $seed_ids AS seed_id
MATCH (seed:Norm {{id: seed_id}})
MATCH (related:Norm)
WHERE related.id = seed_id
{expand}
MATCH (related)-[:APPLIES_TO]->(j:Jurisdiction)
WHERE j.name IN $allowed_jurisdictions
MATCH (related)-[:HAS_COMPONENT]->(c:Component)-[:HAS_CTV]->(v:CTV)
WHERE ($temporal IS NULL OR v.valid_from <= $temporal)
  AND ($temporal IS NULL OR v.valid_to IS NULL OR v.valid_to >= $temporal)
RETURN DISTINCT related.id AS norm_id, c.id AS component_id
"""


# Cypher mặc định (full) — giữ tên cũ cho tương thích, dựng sẵn 1 lần
_STAGE2_CYPHER = _build_stage2_cypher(["IMPLEMENTS", "AMENDS"])


def stage1_norm_ids(
    question: str,
    query_plan: QueryPlan,
    qdrant_client: QdrantClient,
    model,
    top_n: int = 5,
    min_score: float = 0.3,
    ablation: AblationConfig = FULL,
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
    # Ablation no-theme (Gap 1): bỏ hard-filter theme → search summary toàn corpus
    if ablation.no_theme:
        vector = encode_text(model, question)
        must_conditions = [
            FieldCondition(key="content_type", match=MatchValue(value="summary")),
        ]
        results = qdrant_client.query_points(
            "legal_texts", query=vector, limit=top_n,
            query_filter=Filter(must=must_conditions),
        ).points
        norm_ids = [r.payload["norm_id"] for r in results if r.score >= min_score]
        if not norm_ids and results:
            norm_ids = [results[0].payload["norm_id"]]
        logger.info(f"Stage 1 [no-theme]: {len(norm_ids)} norm_ids = {norm_ids}")
        return norm_ids

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
    ablation: AblationConfig = FULL,
) -> LCCIDs:
    """Stage 2: từ seed norm_ids, duyệt graph → Component IDs.

    Chiến lược undirected traversal: mở rộng qua bao đóng {IMPLEMENTS, AMENDS}
    qua [:IMPLEMENTS|AMENDS*1..4], depth tối đa 4 hop.
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
    # Ablation no-jurisdiction (Gap 2): cho phép mọi tỉnh; no-temporal (Gap 4b): temporal=None
    allowed = (_ALL_JURISDICTIONS if ablation.no_jurisdiction
               else _JURISDICTION_ALLOW.get(jurisdiction, ["toan-quoc"]))
    temporal = None if ablation.no_temporal else query_plan.get("temporal")
    cypher = _build_stage2_cypher(ablation.traversal_rels)

    params = {
        "seed_ids": norm_ids,
        "allowed_jurisdictions": allowed,
        "temporal": temporal,
    }

    with neo4j_driver.session() as session:
        rows = session.run(cypher, **params).data()

    # Nhóm theo norm và áp dụng per-norm cap để tránh luật lớn (tier 1) thống trị pool
    norm_to_components: dict[str, list[str]] = {}
    for row in rows:
        nid = row["norm_id"]
        cid = row["component_id"]
        if nid not in norm_to_components:
            norm_to_components[nid] = []
        norm_to_components[nid].append(cid)

    component_ids: list[str] = []
    for nid, cids in norm_to_components.items():
        # Sort deterministic (SHA256 hex) trước khi cap
        capped = sorted(set(cids))[:MAX_COMPONENTS_PER_NORM]
        if len(set(cids)) > MAX_COMPONENTS_PER_NORM:
            logger.info(
                f"Stage 2: norm '{nid}' có {len(set(cids))} components → "
                f"capped xuống {MAX_COMPONENTS_PER_NORM}"
            )
        component_ids.extend(capped)

    component_ids = list(set(component_ids))

    if len(component_ids) > LCCID_LIMIT:
        logger.warning(
            f"Stage 2: {len(component_ids)} LCCIDs vượt giới hạn {LCCID_LIMIT}"
        )

    logger.info(
        f"Stage 2: {len(component_ids)} component_ids từ {len(norm_to_components)} norms "
        f"(jurisdiction={jurisdiction}, temporal={temporal}, cap={MAX_COMPONENTS_PER_NORM}/norm)"
    )
    return component_ids


# ---------------------------------------------------------------------------
# Stage 2b — norm_ids cho Qdrant filter (P2 fix)
# ---------------------------------------------------------------------------

def stage2_norm_ids(
    norm_ids: list[str],
    query_plan: QueryPlan,
    neo4j_driver: Driver,
    ablation: AblationConfig = FULL,
) -> list[str]:
    """Stage 2 (norm_ids variant): từ seed norm_ids, duyệt graph → unique norm_ids liên quan.

    Cùng Cypher và filter (jurisdiction + temporal) với stage2_component_ids(),
    nhưng trả về DISTINCT norm_ids thay vì component_ids.
    Dùng làm Qdrant filter `norm_id IN [...]` cho Stage 3 hybrid_search().

    Lợi thế so với component_id filter:
    - ~13 norm_ids thay vì ~300 component_id hashes → filter nhẹ hơn
    - BGE-M3 dense search tự chọn TextUnit tốt nhất trong mỗi norm
    - Không bị per-norm cap cắt xén ngẫu nhiên các điều khoản quan trọng

    Args:
        norm_ids: Danh sách seed norm_ids từ Stage 1.
        query_plan: QueryPlan chứa jurisdiction và temporal.
        neo4j_driver: Neo4j driver đã kết nối.

    Returns:
        List norm_ids DISTINCT (sau filter jurisdiction + temporal).
    """
    if not norm_ids:
        logger.warning("stage2_norm_ids: norm_ids rỗng — trả về []")
        return []

    jurisdiction = query_plan.get("jurisdiction") or "toan-quoc"
    allowed = (_ALL_JURISDICTIONS if ablation.no_jurisdiction
               else _JURISDICTION_ALLOW.get(jurisdiction, ["toan-quoc"]))
    temporal = None if ablation.no_temporal else query_plan.get("temporal")
    cypher = _build_stage2_cypher(ablation.traversal_rels)

    params = {
        "seed_ids": norm_ids,
        "allowed_jurisdictions": allowed,
        "temporal": temporal,
    }

    with neo4j_driver.session() as session:
        rows = session.run(cypher, **params).data()

    result_norm_ids = list({row["norm_id"] for row in rows})

    logger.info(
        f"Stage 2 (norm_ids): {len(result_norm_ids)} norms "
        f"(jurisdiction={jurisdiction}, temporal={temporal}): {result_norm_ids}"
    )
    return result_norm_ids


# ---------------------------------------------------------------------------
# Stage 3 — Ontology Mapping Graph Filter (Soft Boost Candidates)
# ---------------------------------------------------------------------------

_GRAPH_BOOST_CYPHER = """
UNWIND $norm_ids AS nid
MATCH (n:Norm {id: nid})-[:HAS_COMPONENT]->(comp:Component)
MATCH (p:Procedure {id: $proc_id})-[:REQUIRES_CONCEPT]->(c:Concept)<-[:MAPS_TO_CONCEPT]-(comp)
RETURN DISTINCT comp.id AS component_id
"""

def stage3_graph_component_ids(
    norm_ids: list[str],
    query_plan: QueryPlan,
    neo4j_driver: Driver,
) -> list[str]:
    """Stage 3: lấy các component_id được map trực tiếp với các Concept của Procedure."""
    proc_id = query_plan.get("procedure")
    if not proc_id or not norm_ids:
        return []
        
    with neo4j_driver.session() as session:
        rows = session.run(_GRAPH_BOOST_CYPHER, norm_ids=norm_ids, proc_id=proc_id).data()
    
    comp_ids = [row["component_id"] for row in rows]
    logger.info(f"Stage 3: {len(comp_ids)} graph_component_ids mapped for procedure {proc_id}")
    return comp_ids


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract_subgraph(
    question: str,
    query_plan: QueryPlan,
    neo4j_driver: Driver,
    qdrant_client: QdrantClient,
    model,
    top_n: int = 5,
    ablation: AblationConfig = FULL,
) -> tuple[list[str], list[str]]:
    """Orchestrator: Stage 1 + Stage 2 + Stage 3.

    Args:
        question: Câu hỏi tiếng Việt gốc từ người dùng.
        query_plan: QueryPlan đã được plan_query() tạo ra.
        neo4j_driver: Neo4j driver đã kết nối.
        qdrant_client: Qdrant client đã kết nối.
        model: BGE-M3 model đã load.
        top_n: Số norm_ids tối đa Stage 1 trả về.

    Returns:
        tuple (norm_ids, graph_component_ids):
        - norm_ids: Danh sách văn bản liên quan (Qdrant filter).
        - graph_component_ids: Các điều khoản được Soft Boost qua Ontology Mapping.
    """
    seed_norm_ids = stage1_norm_ids(question, query_plan, qdrant_client, model, top_n,
                                    ablation=ablation)
    # Ablation dense-only (sàn): bỏ toàn bộ mở rộng graph + graph-boost, chỉ seed Stage 1
    if ablation.dense_only:
        logger.info("extract_subgraph [dense-only]: bỏ Stage 2/3, chỉ seed norms")
        return seed_norm_ids, []
    result_norm_ids = stage2_norm_ids(seed_norm_ids, query_plan, neo4j_driver,
                                      ablation=ablation)
    graph_comp_ids = stage3_graph_component_ids(result_norm_ids, query_plan, neo4j_driver)
    return result_norm_ids, graph_comp_ids
