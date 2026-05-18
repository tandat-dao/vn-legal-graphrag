"""
Migration một lần: cập nhật CTV cũ thiếu property valid_to → sentinel '9999-12-31'.

Lý do: graph_builder cũ truyền None vào upsert_ctv → Neo4j SET v.valid_to = null
khiến property bị REMOVE entirely (Neo4j quirk). Query với v.valid_to phát warning
"missing property". Migration này set property tồn tại với sentinel far-future.

Idempotent: chạy nhiều lần OK; chỉ cập nhật node thiếu property.

Usage:
    python -m src.utils.migrate_valid_to_sentinel
"""
import logging
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

from src.ingestion.graph_builder import VALID_TO_SENTINEL

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def migrate(driver) -> int:
    """Cập nhật CTV chưa có property valid_to → sentinel. Trả về số node đã cập nhật."""
    with driver.session() as session:
        # Count CTV thiếu valid_to (trước)
        before = session.run(
            "MATCH (v:CTV) WHERE v.valid_to IS NULL RETURN count(v) AS n"
        ).single()["n"]
        logger.info(f"CTV thiếu valid_to (trước migration): {before}")

        if before == 0:
            logger.info("Không có gì để migrate. Exit.")
            return 0

        result = session.run(
            "MATCH (v:CTV) WHERE v.valid_to IS NULL SET v.valid_to = $sentinel RETURN count(v) AS n",
            sentinel=VALID_TO_SENTINEL,
        )
        updated = result.single()["n"]
        logger.info(f"Cập nhật {updated} CTV nodes → valid_to = '{VALID_TO_SENTINEL}'")

        # Verify sau
        after = session.run(
            "MATCH (v:CTV) WHERE v.valid_to IS NULL RETURN count(v) AS n"
        ).single()["n"]
        logger.info(f"CTV thiếu valid_to (sau migration): {after}")
        assert after == 0, f"Migration không hoàn tất, còn {after} node thiếu"
        return updated


def main() -> int:
    load_dotenv()
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    try:
        updated = migrate(driver)
        logger.info(f"✅ Migration done — {updated} CTV nodes cập nhật")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
