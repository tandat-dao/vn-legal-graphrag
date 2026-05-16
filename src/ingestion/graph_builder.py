"""
Graph Builder — TASK-07
Đọc AST từ Parser, tạo toàn bộ node và edge trong Neo4j theo schema Ontology.

Schema: 6 node (Theme, Norm, Component, CTV, TextUnit, Jurisdiction)
        7 edge (INCLUDES, IMPLEMENTS, AMENDS, HAS_COMPONENT, HAS_CTV, HAS_TEXT_UNIT, APPLIES_TO)

AMENDS vs IMPLEMENTS:
  - IMPLEMENTS: norm con hướng dẫn thi hành norm cha  (NĐ 102 -[:IMPLEMENTS]-> Luật ĐĐ)
  - AMENDS: norm mới sửa đổi/bổ sung norm cũ          (NQ 254 -[:AMENDS]-> Luật ĐĐ)
  Nguồn: `amended_by_norms` trong YAML frontmatter.

Idempotent: chạy lại không tạo duplicate (dùng MERGE cho tất cả node và edge).
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, ManagedTransaction

from src.ingestion.parser import TextUnit, generate_id, parse_file
from src.ingestion.ontology_mapper import map_component_to_concepts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_NON_NORM_FILES = {"crossref_decisions.md", "mapping_table.md", "review_log.md"}


# ---------------------------------------------------------------------------
# Upsert — Ontology Nodes
# ---------------------------------------------------------------------------

def upsert_ontology(tx: ManagedTransaction, core_data: dict) -> None:
    for concept in core_data.get("concepts", []):
        tx.run(
            "MERGE (c:Concept {id: $id}) SET c.name = $name",
            id=concept["id"], name=concept["name"]
        )
    for proc in core_data.get("procedures", []):
        tx.run(
            "MERGE (p:Procedure {id: $id}) SET p.name = $name",
            id=proc["id"], name=proc["name"]
        )
        for req_concept_id in proc.get("required_concepts", []):
            tx.run(
                """
                MATCH (p:Procedure {id: $proc_id})
                MATCH (c:Concept {id: $concept_id})
                MERGE (p)-[:REQUIRES_CONCEPT]->(c)
                """,
                proc_id=proc["id"], concept_id=req_concept_id
            )

# ---------------------------------------------------------------------------
# Upsert — Document Nodes
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
            # Pass 0: Khởi tạo Core Ontology
            ontology_path = Path("data/ontology/core_v1.json")
            if ontology_path.exists():
                with open(ontology_path, "r", encoding="utf-8") as f:
                    core_data = json.load(f)
                with session.begin_transaction() as tx:
                    upsert_ontology(tx, core_data)
                    tx.commit()
                logger.info("Pass 0 — Khởi tạo Core Ontology thành công.")
            else:
                logger.warning("Pass 0 — Bỏ qua do không tìm thấy core_v1.json")

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
                            "MATCH (n:Norm {id: $id}) MATCH (p:Norm {id: $parent}) "
                            "MERGE (n)-[:IMPLEMENTS]->(p)",
                            id=meta["id"],
                            parent=meta["implements"],
                        )
                        implements_count += 1
                tx.commit()
            logger.info(f"Pass 2 — {implements_count} [:IMPLEMENTS] edges đã xử lý.")

            # Pass 3: tạo [:AMENDS] edges từ amended_by_norms trong frontmatter
            # AMENDS: norm sửa đổi -[:AMENDS]-> norm bị sửa đổi
            # Ví dụ: (nghi-quyet-254-2025-qh15)-[:AMENDS]->(luat-dat-dai-2024)
            amends_count = 0
            with session.begin_transaction() as tx:
                for result in all_results:
                    meta = result["metadata"]
                    amended_by = meta.get("amended_by_norms")
                    if amended_by and isinstance(amended_by, list):
                        for amending_norm_id in amended_by:
                            if not isinstance(amending_norm_id, str):
                                continue
                            tx.run(
                                "MATCH (amender:Norm {id: $amender_id}) MATCH (target:Norm {id: $target_id}) "
                                "MERGE (amender)-[:AMENDS]->(target)",
                                amender_id=amending_norm_id,
                                target_id=meta["id"],
                            )
                            amends_count += 1
                tx.commit()
            logger.info(f"Pass 3 — {amends_count} [:AMENDS] edges đã xử lý.")

            # Pass 4: Ontology Mapping (Bottom-up LLM Classification)
            # Dùng Claude Haiku để gán nhãn từng Component vào các Concept có sẵn.
            ontology_path = Path("data/ontology/core_v1.json")
            if ontology_path.exists():
                logger.info("Pass 4 — Bắt đầu Ontology Mapping (LLM Classification)...")
                anthropic_client = __import__("anthropic").Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                with open(ontology_path, "r", encoding="utf-8") as f:
                    core_data = json.load(f)
                
                # Tính lũy đẳng (Idempotency): Tải trước danh sách các component đã map
                with session.begin_transaction() as tx:
                    mapped_records = tx.run(
                        """
                        MATCH (c:Component)
                        WHERE c.ontology_mapped = true OR EXISTS { MATCH (c)-[:MAPS_TO_CONCEPT]->() }
                        RETURN DISTINCT c.id AS comp_id
                        """
                    ).data()
                    mapped_set = {r["comp_id"] for r in mapped_records}
                logger.info(f"Pass 4 — Bỏ qua {len(mapped_set)} components đã map từ lần chạy trước để tiết kiệm chi phí.")
                
                mapping_count = 0
                total_nodes = sum(len(res["nodes"]) for res in all_results)
                processed = 0
                batch_size = 50

                for result in all_results:
                    tx = session.begin_transaction()
                    try:
                        for idx, node in enumerate(result["nodes"]):
                            comp_id = node["id"]
                            
                            # Idempotency: Skip nếu đã map
                            if comp_id in mapped_set:
                                processed += 1
                                continue
                                
                            text = node["text"]
                            if not text.strip():
                                processed += 1
                                continue
                            
                            mapped_concepts = map_component_to_concepts(anthropic_client, text, core_data)
                            
                            # Đánh dấu đã quét LLM (dù có ra mảng rỗng hay không)
                            tx.run(
                                "MATCH (c:Component {id: $comp_id}) SET c.ontology_mapped = true",
                                comp_id=comp_id
                            )
                            
                            for concept_id in mapped_concepts:
                                tx.run(
                                    """
                                    MATCH (c:Component {id: $comp_id})
                                    MATCH (concept:Concept {id: $concept_id})
                                    MERGE (c)-[:MAPS_TO_CONCEPT]->(concept)
                                    """,
                                    comp_id=comp_id, concept_id=concept_id
                                )
                                mapping_count += 1
                            
                            processed += 1
                            if processed % 100 == 0:
                                logger.info(f"  Đã map {processed}/{total_nodes} components...")
                            
                            # Batch commit sau mỗi 50 node
                            if (idx + 1) % batch_size == 0:
                                tx.commit()
                                tx = session.begin_transaction()

                        # Commit những node còn lại của văn bản
                        tx.commit()
                    except Exception as e:
                        if not tx.closed():
                            tx.rollback()
                        logger.error(f"Lỗi ở văn bản {result['metadata']['id']}, rollback lô hiện tại: {e}")
                        raise e
                logger.info(f"Pass 4 — Hoàn thành {mapping_count} [:MAPS_TO_CONCEPT] edges.")
            else:
                logger.warning("Pass 4 — Bỏ qua do không có core_v1.json")

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
