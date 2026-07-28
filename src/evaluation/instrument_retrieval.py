"""
Instrumentation cho temporal/H2_dieu downstream bottleneck.

Mục đích: định vị bottleneck giữa Stage 1 (đã verify ĐÚNG) và final pred citations
cho các câu thất bại trong canonical run 20260519:
  - Q022, Q023: thiếu old regime trong final pred dù Stage 1 surface đúng
  - Q024: pred wrong Điều entirely (Điều 116 K5 không xuất hiện)
  - Q026: pred wrong Khoản của đúng Điều (AMENDED_BY)

Phương pháp: chạy lại Stage 1/2/3 cho mỗi câu, dump intermediate state. KHÔNG gọi
LLM, KHÔNG ghi vào DB → an toàn, miễn phí.

Output: dump JSON + summary markdown vào data/evaluation/RETRIEVAL_DEBUG_<timestamp>/
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# Câu hỏi target — focus failure cases với root cause cần định vị
TARGET_QUESTIONS = [
    {
        "id": "Q022",
        "question": "Hồ sơ giao đất ở của tôi nộp tháng 6/2024 nhưng đến nay (tháng 10/2024) vẫn chưa có quyết định cuối cùng, áp dụng hạn mức theo Quyết định 18/2016 hay Quyết định 69/2024?",
        "jurisdiction": "tp-hcm",
        "expected_norms": ["quyet-dinh-18-2016-qd-ubnd-tp-hcm", "quyet-dinh-69-2024-qd-ubnd-tp-hcm"],
        "investigation": "Stage 1 OK (QĐ 18 rank #1). Tại đâu old regime bị drop?",
    },
    {
        "id": "Q023",
        "question": "Hồ sơ cấp Giấy chứng nhận quyền sử dụng đất nộp năm 2023 nhưng chưa giải quyết xong, hiện áp dụng Luật Đất đai 2013 hay Luật Đất đai 2024?",
        "jurisdiction": "toan-quoc",
        "expected_norms": ["luat-dat-dai-2013", "luat-dat-dai-2024"],
        "investigation": "Stage 1 OK (Luật 2013 rank #1). Tại đâu old regime bị drop?",
    },
    {
        "id": "Q024",
        "question": "Năm 2024, Luật Đất đai 2024 quy định căn cứ cho phép chuyển mục đích sử dụng đất là gì?",
        "jurisdiction": "toan-quoc",
        "expected_norms": ["luat-dat-dai-2024"],
        "expected_component_substr": "dieu-116-khoan-5",
        "investigation": "Pred miss Điều 116 K5 entirely → hybrid search không rank Điều 116 K5 vào top-k?",
    },
    {
        "id": "Q026",
        "question": "Khoản 1 Điều 13 Nghị định 102/2024/NĐ-CP đã được văn bản nào sửa đổi và hiệu lực từ ngày nào?",
        "jurisdiction": "toan-quoc",
        "expected_norms": ["nghi-dinh-102-2024-nd-cp", "nghi-dinh-49-2026-nd-cp"],
        "expected_component_substr": "dieu-13-khoan-1",
        "investigation": "Pred has Khoản 11/12 thay vì Khoản 1 — H2_khoan. Top-k có Khoản 1 không?",
    },
]


def _build_clients():
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    from src.ingestion.vectorizer import load_model

    neo4j_driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    model = load_model()
    return neo4j_driver, qdrant_client, model


def instrument_one(item: dict, clients) -> dict:
    """Chạy 3 stage retrieval cho 1 câu, dump intermediate state.

    Returns:
        Dict với keys: stage1_results, stage2_norms, stage3_top_k, summary.
    """
    from src.retrieval.query_planner import plan_query
    from src.retrieval.semantic_filter import hybrid_search
    from src.retrieval.subgraph_extractor import (
        stage1_norm_ids,
        stage2_norm_ids,
        stage3_graph_component_ids,
    )
    from src.utils.llm_config import make_anthropic_client

    neo4j_driver, qdrant_client, model = clients
    anthropic_client = make_anthropic_client()

    # Plan query (gọi LLM 1 lần — vẫn cần để có đúng query_plan)
    qp = plan_query(item["question"], anthropic_client, neo4j_driver=neo4j_driver)
    # Force jurisdiction như eval mode
    qp["jurisdiction"] = item["jurisdiction"]

    # Apply temporal layer (sao chép từ pipeline.py)
    from src.pipeline import _resolve_temporal_anchor
    ti = qp.get("temporal_intent", {}) or {}
    if ti.get("has_temporal_context"):
        case_status = ti.get("case_status")
        anchor = ti.get("temporal_anchor")
        if case_status in ("do-dang", "moi"):
            qp["temporal"] = None
            temporal_reason = f"broad (case_status={case_status})"
        else:
            qp["temporal"] = _resolve_temporal_anchor(anchor)
            temporal_reason = f"strict={qp['temporal']}" if qp["temporal"] else f"broad (vague anchor={anchor})"
    else:
        temporal_reason = "no_temporal_context"

    # --- Stage 1 ---
    seed_norms = stage1_norm_ids(item["question"], qp, qdrant_client, model, top_n=10)

    # --- Stage 2: traverse graph + filter jurisdiction + temporal ---
    result_norms = stage2_norm_ids(seed_norms, qp, neo4j_driver)

    # --- Stage 3: graph component boost ---
    graph_comp_ids = stage3_graph_component_ids(result_norms, qp, neo4j_driver)

    # --- Hybrid search ---
    scored_units = hybrid_search(
        item["question"],
        result_norms,
        qdrant_client,
        model,
        top_k=25,
        graph_component_ids=graph_comp_ids,
        neo4j_driver=neo4j_driver,
        procedure_id=qp.get("procedure"),
    )

    # Component_id là hash hex — cần fetch label từ Neo4j để debug human-readable
    comp_ids_in_top_k = [r.get("component_id") for r in scored_units[:25] if r.get("component_id")]
    label_map: dict[str, str] = {}
    if comp_ids_in_top_k:
        with neo4j_driver.session() as sess:
            rows = sess.run(
                "MATCH (c:Component) WHERE c.id IN $ids "
                "OPTIONAL MATCH (c)<-[:HAS_COMPONENT]-(n:Norm) "
                "OPTIONAL MATCH (c)-[:HAS_CTV]->(v:CTV)-[:HAS_TEXT_UNIT]->(t:TextUnit) "
                "WITH c, n, t LIMIT 1000 "
                "RETURN c.id AS cid, c.label AS label, n.id AS norm_id, t.text AS text",
                ids=comp_ids_in_top_k,
            ).data()
            for row in rows:
                if row["cid"] not in label_map:
                    label_map[row["cid"]] = {
                        "label": row.get("label") or "(no label)",
                        "norm_id": row.get("norm_id"),
                        "text_preview": (row.get("text") or "")[:120].replace("\n", " "),
                    }

    # Summarize for diagnostics
    top_k_summary = []
    for r in scored_units[:25]:
        cid = r.get("component_id") or ""
        meta = label_map.get(cid, {})
        top_k_summary.append({
            "norm_id": r.get("norm_id"),
            "component_id": cid,
            "component_label": meta.get("label", "(unknown)"),
            "rrf_score": round(r.get("rrf_score", 0), 4),
            "text_preview": meta.get("text_preview", ""),
        })

    # Check coverage of expected norms / components
    expected_norms = set(item.get("expected_norms", []))
    norms_in_top_k = {u["norm_id"] for u in top_k_summary}
    missing_norms = expected_norms - norms_in_top_k

    # Match expected component by LABEL substring (e.g. "Điều 116" + "Khoản 5")
    expected_substr = item.get("expected_component_substr")
    matching_components = []
    if expected_substr:
        # expected_substr in format "dieu-X-khoan-Y" — convert to label patterns
        # Try matching both forms: label OR id substring
        import re as _re
        m = _re.match(r"dieu-([^-]+)-khoan-(.+)", expected_substr)
        if m:
            dieu_num, khoan_num = m.group(1), m.group(2)
            for u in top_k_summary:
                lbl = u.get("component_label", "")
                if f"Điều {dieu_num}" in lbl and f"Khoản {khoan_num}" in lbl:
                    matching_components.append(u)

    return {
        "id": item["id"],
        "question": item["question"],
        "investigation": item["investigation"],
        "query_plan": {
            "theme": qp.get("theme"),
            "procedure": qp.get("procedure"),
            "jurisdiction": qp.get("jurisdiction"),
            "temporal": qp.get("temporal"),
            "temporal_reason": temporal_reason,
            "temporal_intent": qp.get("temporal_intent"),
        },
        "stage1_seed_norms": seed_norms,
        "stage2_result_norms": result_norms,
        "stage3_graph_components": graph_comp_ids[:20],  # cap để dễ đọc
        "stage3_graph_components_count": len(graph_comp_ids),
        "hybrid_top_25": top_k_summary,
        "expected_norms": list(expected_norms),
        "expected_component_substr": expected_substr,
        "norms_missing_from_top_k": list(missing_norms),
        "expected_component_matches_in_top_k": matching_components,
    }


def render_summary(dumps: list[dict]) -> str:
    """Render markdown summary để dễ đọc bằng mắt người."""
    lines = ["# Retrieval Instrumentation — Downstream Bottleneck Diagnostics", ""]
    lines.append("> Dump Stage 1/2/3 cho 4 câu thất bại để định vị bottleneck giữa retrieval")
    lines.append("> đúng (Stage 1 verified) và pred citations sai (canonical run).")
    lines.append("")

    for d in dumps:
        lines.append("---")
        lines.append("")
        lines.append(f"## {d['id']} — {d['question'][:80]}...")
        lines.append("")
        lines.append(f"**Investigation:** {d['investigation']}")
        lines.append("")

        qp = d["query_plan"]
        lines.append(f"**Query Plan:** theme=`{qp['theme']}`, jurisdiction=`{qp['jurisdiction']}`, "
                     f"temporal=`{qp['temporal']}` ({qp['temporal_reason']})")
        lines.append("")

        lines.append(f"**Stage 1 — Seed norms (top-10):** `{d['stage1_seed_norms']}`")
        lines.append("")
        lines.append(f"**Stage 2 — Result norms (sau jurisdiction + temporal filter, qua graph traversal):** "
                     f"`{d['stage2_result_norms']}`")
        lines.append("")
        lines.append(f"**Stage 3 — Graph components (qua [:IMPLEMENTS|AMENDS]):** "
                     f"{d['stage3_graph_components_count']} items, "
                     f"first 20: `{d['stage3_graph_components']}`")
        lines.append("")

        # Coverage check
        if d["norms_missing_from_top_k"]:
            lines.append(f"### ⚠️ MISSING từ top-25: `{d['norms_missing_from_top_k']}`")
            lines.append("")
            lines.append("→ Hybrid search KHÔNG đưa các norm này vào top-25 dù Stage 2 đã include.")
            lines.append("Hypothesis: BGE-M3 similarity của các chunks norm này thấp hơn các norm khác trong pool.")
            lines.append("")
        else:
            lines.append("### ✅ Tất cả expected norms có mặt trong top-25")
            lines.append("")

        if d["expected_component_substr"]:
            matches = d["expected_component_matches_in_top_k"]
            if matches:
                lines.append(f"### ✅ Component '{d['expected_component_substr']}' có trong top-25:")
                for m in matches:
                    lines.append(f"  - rrf_score={m['rrf_score']} `{m['component_label']}` (norm={m['norm_id']})")
            else:
                lines.append(f"### ❌ Component '{d['expected_component_substr']}' KHÔNG có trong top-25")
                lines.append("→ Bottleneck nằm ở hybrid_search ranking — chunk này không score đủ cao.")
            lines.append("")

        lines.append("**Top-15 hybrid search results:**")
        lines.append("")
        lines.append("| # | rrf_score | norm_id | component (label) | text preview |")
        lines.append("|---|---|---|---|---|")
        for i, u in enumerate(d["hybrid_top_25"][:15], 1):
            preview = u['text_preview'].replace('|', '\\|').replace('\n',' ')[:60]
            label = (u.get('component_label') or '(unknown)').replace('|','\\|')[:60]
            lines.append(f"| {i} | {u['rrf_score']} | `{u['norm_id']}` | {label} | {preview} |")
        lines.append("")

    return "\n".join(lines)


def main():
    load_dotenv(".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(f"data/evaluation/RETRIEVAL_DEBUG_{timestamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Build clients...")
    clients = _build_clients()
    try:
        dumps = []
        for item in TARGET_QUESTIONS:
            logger.info(f"=== Instrumenting {item['id']} ===")
            d = instrument_one(item, clients)
            dumps.append(d)
            # Save individual JSON
            (out_dir / f"{item['id']}.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # Render summary
        summary = render_summary(dumps)
        (out_dir / "SUMMARY.md").write_text(summary, encoding="utf-8")
        logger.info(f"✓ Dumps written to {out_dir}")
        print("\n" + summary)
    finally:
        clients[0].close()
        clients[1].close()


if __name__ == "__main__":
    main()
