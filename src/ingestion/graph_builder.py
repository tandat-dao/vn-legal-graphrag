"""
Graph Builder — TASK-07
Đọc AST từ Parser, tạo toàn bộ node và edge trong Neo4j theo schema Ontology.

Schema: 6 node (Theme, Norm, Component, CTV, TextUnit, Jurisdiction)
        6 edge (INCLUDES, IMPLEMENTS, HAS_COMPONENT, HAS_CTV, HAS_TEXT_UNIT, APPLIES_TO)

Idempotent: chạy lại không tạo duplicate (dùng MERGE cho tất cả node và edge).
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, ManagedTransaction

from src.ingestion.parser import TextUnit, generate_id, parse_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_NON_NORM_FILES = {"crossref_decisions.md", "mapping_table.md", "review_log.md"}


# ---------------------------------------------------------------------------
# Upsert — Nodes
# ---------------------------------------------------------------------------

def upsert_theme(tx: ManagedTransaction, theme_name: str) -> None:
    tx.run("MERGE (:Theme {name: $name})", name=theme_name)


def upsert_jurisdiction(tx: ManagedTransaction, name: str) -> None:
    tx.run("MERGE (:Jurisdiction {name: $name})", name=name)


def upsert_norm(tx: ManagedTransaction, metadata: dict) -> None:
    tx.run(
        """
        MERGE (n:Norm {id: $id})
        SET n.title      = $title,
            n.tier       = $tier,
            n.valid_from = $valid_from,
            n.valid_to   = $valid_to,
            n.summary    = $summary
        """,
        id=metadata["id"],
        title=metadata.get("title"),
        tier=metadata.get("tier"),
        valid_from=metadata.get("valid_from"),
        valid_to=metadata.get("valid_to"),
        summary=metadata.get("summary"),
    )


def upsert_component(tx: ManagedTransaction, component_id: str, label: str) -> None:
    tx.run(
        """
        MERGE (c:Component {id: $id})
        SET c.label = $label
        """,
        id=component_id,
        label=label,
    )


def upsert_ctv(tx: ManagedTransaction, ctv_data: dict) -> None:
    tx.run(
        """
        MERGE (v:CTV {id: $id})
        SET v.valid_from = $valid_from,
            v.valid_to   = $valid_to,
            v.status     = $status
        """,
        id=ctv_data["id"],
        valid_from=ctv_data.get("valid_from"),
        valid_to=ctv_data.get("valid_to"),
        status=ctv_data["status"],
    )


def upsert_text_unit(tx: ManagedTransaction, text_unit: TextUnit) -> None:
    tx.run(
        """
        MERGE (t:TextUnit {id: $id})
        SET t.text         = $text,
            t.context_path = $context_path,
            t.norm_id      = $norm_id
        """,
        id=text_unit["id"],
        text=text_unit["text"],
        context_path=text_unit["context_path"],
        norm_id=text_unit["context_path"][0],
    )


# ---------------------------------------------------------------------------
# Upsert — Edges
# ---------------------------------------------------------------------------

def create_edges(
    tx: ManagedTransaction,
    *,
    norm_id: str,
    theme_name: str,
    jurisdiction: str,
    implements: str | None,
    component_id: str,
    ctv_id: str,
    text_unit_id: str,
) -> None:
    """Tạo tất cả 6 loại edge liên quan đến một TextUnit cụ thể.

    INCLUDES và APPLIES_TO được MERGE lặp lại cho từng TextUnit nhưng hoàn toàn
    idempotent — Neo4j bỏ qua nếu edge đã tồn tại.
    IMPLEMENTS được tạo chỉ khi implements không null VÀ target Norm đã tồn tại.
    """
    # Theme -[:INCLUDES]-> Norm
    tx.run(
        "MATCH (th:Theme {name: $theme}), (n:Norm {id: $norm_id}) "
        "MERGE (th)-[:INCLUDES]->(n)",
        theme=theme_name,
        norm_id=norm_id,
    )
    # Norm -[:APPLIES_TO]-> Jurisdiction
    tx.run(
        "MATCH (n:Norm {id: $norm_id}), (j:Jurisdiction {name: $jur}) "
        "MERGE (n)-[:APPLIES_TO]->(j)",
        norm_id=norm_id,
        jur=jurisdiction,
    )
    # Norm -[:IMPLEMENTS]-> Norm  (chỉ tạo nếu target đã tồn tại)
    if implements:
        tx.run(
            "MATCH (n:Norm {id: $norm_id}), (p:Norm {id: $parent}) "
            "MERGE (n)-[:IMPLEMENTS]->(p)",
            norm_id=norm_id,
            parent=implements,
        )
    # Norm -[:HAS_COMPONENT]-> Component
    tx.run(
        "MATCH (n:Norm {id: $norm_id}), (c:Component {id: $comp_id}) "
        "MERGE (n)-[:HAS_COMPONENT]->(c)",
        norm_id=norm_id,
        comp_id=component_id,
    )
    # Component -[:HAS_CTV]-> CTV
    tx.run(
        "MATCH (c:Component {id: $comp_id}), (v:CTV {id: $ctv_id}) "
        "MERGE (c)-[:HAS_CTV]->(v)",
        comp_id=component_id,
        ctv_id=ctv_id,
    )
    # CTV -[:HAS_TEXT_UNIT]-> TextUnit
    tx.run(
        "MATCH (v:CTV {id: $ctv_id}), (t:TextUnit {id: $tu_id}) "
        "MERGE (v)-[:HAS_TEXT_UNIT]->(t)",
        ctv_id=ctv_id,
        tu_id=text_unit_id,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_ingestion(data_dir: str) -> None:
    """Chạy toàn bộ ingestion pipeline từ data/raw/ vào Neo4j.

    Hai-pass để xử lý [:IMPLEMENTS] đúng thứ tự:
    Pass 1 — upsert tất cả nodes + edges (IMPLEMENTS chỉ khi target đã tồn tại).
    Pass 2 — tạo lại [:IMPLEMENTS] cho tất cả file (lúc này mọi Norm đã có mặt).

    Raises:
        Exception: bất kỳ lỗi Neo4j nào được re-raise sau khi log.
    """
    load_dotenv()
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
    )
    logger.info("Kết nối Neo4j thành công.")

    try:
        # Bước 0: parse tất cả file trước khi mở kết nối ghi
        all_results: list[dict] = []
        for filepath in sorted(Path(data_dir).glob("*.md")):
            if filepath.name in _NON_NORM_FILES:
                continue
            result = parse_file(str(filepath))
            all_results.append(result)
            logger.info(f"Parsed {filepath.name}: {len(result['nodes'])} TextUnits")

        with driver.session() as session:
            # Pass 1: upsert tất cả nodes + edges (trừ IMPLEMENTS nếu target chưa tồn tại)
            for result in all_results:
                meta = result["metadata"]
                norm_id = meta["id"]
                valid_from = meta.get("valid_from") or ""

                with session.begin_transaction() as tx:
                    upsert_theme(tx, meta["theme"])
                    upsert_jurisdiction(tx, meta["jurisdiction"])
                    upsert_norm(tx, meta)

                    for node in result["nodes"]:
                        comp_id = node["id"]
                        # CTV ID phân biệt theo phiên bản (valid_from) để Phase 2 thêm CTV cũ
                        ctv_id = generate_id(node["context_path"] + [valid_from])
                        label = " > ".join(node["context_path"][1:])

                        upsert_component(tx, comp_id, label)
                        upsert_ctv(tx, {
                            "id": ctv_id,
                            "valid_from": meta.get("valid_from"),
                            "valid_to": meta.get("valid_to"),
                            "status": "active",
                        })
                        upsert_text_unit(tx, node)

                        create_edges(
                            tx,
                            norm_id=norm_id,
                            theme_name=meta["theme"],
                            jurisdiction=meta["jurisdiction"],
                            implements=meta.get("implements"),
                            component_id=comp_id,
                            ctv_id=ctv_id,
                            text_unit_id=node["id"],
                        )

                    tx.commit()
                logger.info(f"Pass 1 — ingested {norm_id}: {len(result['nodes'])} TextUnits")

            # Pass 2: tạo lại [:IMPLEMENTS] — lúc này tất cả Norm đã tồn tại
            implements_count = 0
            with session.begin_transaction() as tx:
                for result in all_results:
                    meta = result["metadata"]
                    if meta.get("implements"):
                        tx.run(
                            "MATCH (n:Norm {id: $id}), (p:Norm {id: $parent}) "
                            "MERGE (n)-[:IMPLEMENTS]->(p)",
                            id=meta["id"],
                            parent=meta["implements"],
                        )
                        implements_count += 1
                tx.commit()
            logger.info(f"Pass 2 — {implements_count} [:IMPLEMENTS] edges đã xử lý.")

        logger.info(
            f"run_ingestion() hoàn thành — {len(all_results)} văn bản được nạp vào Neo4j."
        )

    except Exception as e:
        logger.error(f"Lỗi ingestion: {e}")
        raise
    finally:
        driver.close()


if __name__ == "__main__":
    run_ingestion("data/raw")
