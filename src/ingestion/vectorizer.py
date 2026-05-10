"""
Vectorizer — TASK-08
Encode TextUnit và Norm summary bằng BGE-M3, upsert vào Qdrant collection "legal_texts".

Hai loại vector:
  - content_type="text_unit" : 1 vector/TextUnit — dùng cho Stage 2 retrieval
  - content_type="summary"   : 1 vector/Norm    — dùng cho Stage 1 routing

ID vector trong Qdrant = int(TextUnit.id, 16) để map 1-1 với Neo4j TextUnit nodes.
"""
import logging
import os

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.ingestion.parser import generate_id

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

COLLECTION_NAME = "legal_texts"
VECTOR_DIM = 1024
BATCH_SIZE = 100


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def load_model(model_name: str = "BAAI/bge-m3"):
    """Load BGE-M3 từ HuggingFace (cache lần đầu, local từ lần sau)."""
    from sentence_transformers import SentenceTransformer
    logger.info(f"Loading model {model_name} ...")
    model = SentenceTransformer(model_name)
    logger.info("Model loaded.")
    return model


def encode_text(model, text: str) -> list[float]:
    """Encode 1 đoạn text thành vector 1024 chiều."""
    return model.encode(text, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_text_unit_payload(row: dict) -> dict:
    """Tạo Qdrant payload cho vector content_type='text_unit'.

    row phải chứa: text_unit_id, norm_id, component_id, jurisdiction,
                   tier, theme, valid_from, valid_to.
    """
    return {
        "content_type": "text_unit",
        "norm_id": row["norm_id"],
        "component_id": row["component_id"],
        "jurisdiction": row["jurisdiction"],
        "tier": row["tier"],
        "theme": row["theme"],
        "valid_from": row["valid_from"],
        "valid_to": row["valid_to"],
    }


def build_summary_payload(norm_node: dict) -> dict:
    """Tạo Qdrant payload cho vector content_type='summary'.

    norm_node phải chứa: norm_id, tier, theme, jurisdiction, valid_from.
    """
    return {
        "content_type": "summary",
        "norm_id": norm_node["norm_id"],
        "tier": norm_node["tier"],
        "theme": norm_node["theme"],
        "jurisdiction": norm_node["jurisdiction"],
        "valid_from": norm_node["valid_from"],
    }


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------

def _ensure_collection(client: QdrantClient) -> None:
    """Tạo collection nếu chưa tồn tại."""
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        logger.info(f"Tạo Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}).")
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' đã tồn tại.")


def _hex_to_qdrant_id(hex_id: str) -> int:
    """Chuyển 16-char hex ID thành unsigned integer để dùng làm Qdrant point ID."""
    return int(hex_id, 16)


def upsert_vectors(
    client: QdrantClient,
    collection_name: str,
    points: list[PointStruct],
) -> None:
    """Upsert batch vectors vào Qdrant (idempotent)."""
    client.upsert(collection_name=collection_name, points=points)


# ---------------------------------------------------------------------------
# Data fetchers from Neo4j
# ---------------------------------------------------------------------------

def _fetch_text_units(driver: Driver) -> list[dict]:
    """Lấy tất cả TextUnit kèm metadata cần thiết cho payload."""
    query = """
        MATCH (th:Theme)-[:INCLUDES]->(n:Norm)-[:HAS_COMPONENT]->(c:Component)
              -[:HAS_CTV]->(v:CTV)-[:HAS_TEXT_UNIT]->(t:TextUnit)
        MATCH (n)-[:APPLIES_TO]->(j:Jurisdiction)
        RETURN t.id        AS text_unit_id,
               t.text      AS text,
               n.id        AS norm_id,
               c.id        AS component_id,
               j.name      AS jurisdiction,
               n.tier      AS tier,
               th.name     AS theme,
               v.valid_from AS valid_from,
               v.valid_to   AS valid_to
    """
    with driver.session() as session:
        return session.run(query).data()


def _fetch_norms(driver: Driver) -> list[dict]:
    """Lấy tất cả Norm có summary kèm metadata cho payload."""
    query = """
        MATCH (th:Theme)-[:INCLUDES]->(n:Norm)-[:APPLIES_TO]->(j:Jurisdiction)
        WHERE n.summary IS NOT NULL
        RETURN n.id        AS norm_id,
               n.summary   AS summary,
               n.tier      AS tier,
               th.name     AS theme,
               j.name      AS jurisdiction,
               n.valid_from AS valid_from
    """
    with driver.session() as session:
        return session.run(query).data()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_vectorization(neo4j_driver: Driver, qdrant_client: QdrantClient) -> None:
    """Encode TextUnit và Norm summary, upsert vào Qdrant.

    Idempotent: chạy lại sẽ overwrite các vector hiện có (upsert).
    """
    model = load_model()
    _ensure_collection(qdrant_client)

    # --- Stage 2 vectors: text_unit ---
    logger.info("Fetch TextUnit nodes từ Neo4j ...")
    text_units = _fetch_text_units(neo4j_driver)
    logger.info(f"{len(text_units)} TextUnit nodes cần encode.")

    points_batch: list[PointStruct] = []
    for i, row in enumerate(text_units):
        vector = encode_text(model, row["text"])
        payload = build_text_unit_payload(row)
        points_batch.append(
            PointStruct(
                id=_hex_to_qdrant_id(row["text_unit_id"]),
                vector=vector,
                payload=payload,
            )
        )
        if len(points_batch) == BATCH_SIZE:
            upsert_vectors(qdrant_client, COLLECTION_NAME, points_batch)
            points_batch = []
            logger.info(f"  Upserted {i + 1}/{len(text_units)} text_unit vectors ...")

    if points_batch:
        upsert_vectors(qdrant_client, COLLECTION_NAME, points_batch)

    logger.info(f"Stage 2 xong: {len(text_units)} text_unit vectors upserted.")

    # --- Stage 1 vectors: summary ---
    logger.info("Fetch Norm nodes từ Neo4j ...")
    norms = _fetch_norms(neo4j_driver)
    logger.info(f"{len(norms)} Norm summary cần encode.")

    points_batch = []
    for norm in norms:
        vector = encode_text(model, norm["summary"])
        payload = build_summary_payload(norm)
        summary_id = generate_id([norm["norm_id"], "summary"])
        points_batch.append(
            PointStruct(
                id=_hex_to_qdrant_id(summary_id),
                vector=vector,
                payload=payload,
            )
        )

    if points_batch:
        upsert_vectors(qdrant_client, COLLECTION_NAME, points_batch)

    logger.info(f"Stage 1 xong: {len(norms)} summary vectors upserted.")
    logger.info("run_vectorization() hoàn thành.")


if __name__ == "__main__":
    load_dotenv()
    neo4j_driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
    )
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    try:
        run_vectorization(neo4j_driver, qdrant_client)
    finally:
        neo4j_driver.close()
