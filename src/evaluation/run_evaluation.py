"""
Evaluation runner — TASK-17
Chạy GraphRAG và/hoặc Naive RAG baseline trên test set, lưu kết quả per-question
+ markdown summary để so sánh.

Usage:
    # Chạy cả 2 hệ thống trên test set Đất đai
    python -m src.evaluation.run_evaluation --test-set data/evaluation/test_set_dat_dai.json

    # Chỉ chạy 1 hệ thống
    python -m src.evaluation.run_evaluation --test-set <path> --systems graphrag
    python -m src.evaluation.run_evaluation --test-set <path> --systems baseline

    # Dry run nhanh (n câu đầu)
    python -m src.evaluation.run_evaluation --test-set <path> --limit 3
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.evaluation.metrics import (
    aggregate,
    citation_score,
    negative_correct,
    norm_recall,
    render_summary_md,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-system runners
# ---------------------------------------------------------------------------

_JURIS_SUFFIX = {
    "toan-quoc": "trên cả nước Việt Nam",
    "tp-hcm": "tại Thành phố Hồ Chí Minh",
    "dong-nai": "tại tỉnh Đồng Nai",
}


def _augment_question(question: str, jurisdiction: str) -> str:
    """Phụ trợ jurisdiction vào câu hỏi khi pipeline yêu cầu confirmation.

    Mô phỏng user trả lời confirmation prompt với jurisdiction lấy từ test_set.
    Chỉ append nếu suffix chưa xuất hiện trong câu.
    """
    suffix = _JURIS_SUFFIX.get(jurisdiction, "")
    if not suffix or suffix.lower() in question.lower():
        return question
    base = question.rstrip("?.! ")
    return f"{base} {suffix}?"


def _run_one_graphrag(item: dict, clients) -> dict:
    """Chạy GraphRAG; nếu confirmation_needed thì augment + retry 1 lần."""
    from src.pipeline import run_pipeline
    neo4j_driver, qdrant_client, anthropic_client, model = clients

    res = run_pipeline(
        item["question"],
        neo4j_driver=neo4j_driver,
        qdrant_client=qdrant_client,
        anthropic_client=anthropic_client,
        model=model,
    )

    retried = False
    if res["confirmation_needed"]:
        aug_q = _augment_question(item["question"], item["jurisdiction"])
        if aug_q != item["question"]:
            logger.info(f"  [retry] confirmation_needed → augment: '{aug_q[:80]}...'")
            res2 = run_pipeline(
                aug_q,
                neo4j_driver=neo4j_driver,
                qdrant_client=qdrant_client,
                anthropic_client=anthropic_client,
                model=model,
            )
            # Cộng dồn latency của cả 2 lần gọi để fair
            res2["elapsed_seconds"] = round(res["elapsed_seconds"] + res2["elapsed_seconds"], 2)
            res = res2
            retried = True

    return {
        "answer": res["answer"],
        "citations": res["citations"],
        "elapsed_seconds": res["elapsed_seconds"],
        "confirmation_needed": res["confirmation_needed"],
        "confirmation_retried": retried,
        "context_used": res["context_used"],
        "top_k_count": res["top_k_count"],
    }


def _run_one_baseline(item: dict, clients) -> dict:
    from src.baseline.naive_rag import run_baseline_query
    _, qdrant_client, anthropic_client, model = clients
    res = run_baseline_query(
        item["question"],
        qdrant_client=qdrant_client,
        anthropic_client=anthropic_client,
        model=model,
    )
    return {
        "answer": res["answer"],
        "citations": res["citations"],
        "elapsed_seconds": res["elapsed_seconds"],
        "confirmation_needed": False,
        "confirmation_retried": False,
        "context_used": res["context_used"],
        "top_k_count": res["top_k_count"],
    }


# ---------------------------------------------------------------------------
# Shared client factory (tránh load model nhiều lần)
# ---------------------------------------------------------------------------

def _build_shared_clients():
    import anthropic
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
    anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = load_model()
    return neo4j_driver, qdrant_client, anthropic_client, model


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run_system_on_test_set(
    test_set: list[dict],
    system: str,
    clients,
) -> list[dict]:
    """Chạy 1 hệ thống trên test set, tính metric per-question.

    Returns:
        List per-question result dict.
    """
    assert system in {"graphrag", "baseline"}
    runner = _run_one_graphrag if system == "graphrag" else _run_one_baseline

    results = []
    for i, item in enumerate(test_set, 1):
        qid = item["id"]
        logger.info(f"[{system}] {i}/{len(test_set)} {qid}: {item['question'][:60]}...")
        try:
            sys_out = runner(item, clients)
        except Exception as e:
            logger.exception(f"[{system}] {qid} CRASHED: {e}")
            sys_out = {
                "answer": f"<<ERROR: {e}>>",
                "citations": [],
                "elapsed_seconds": 0.0,
                "confirmation_needed": False,
                "confirmation_retried": False,
                "context_used": False,
                "top_k_count": 0,
            }

        gt_cits = item.get("ground_truth_citations", [])
        cs = citation_score(sys_out["citations"], gt_cits, level="khoan")
        nr = norm_recall(sys_out["citations"], gt_cits)
        nc = (
            negative_correct(sys_out["citations"], item["gap_type"])
            if item["gap_type"] == "negative" else None
        )

        result = {
            "id": qid,
            "question": item["question"],
            "gap_type": item["gap_type"],
            "theme": item["theme"],
            "jurisdiction": item["jurisdiction"],
            "difficulty": item["difficulty"],
            "system": system,
            "answer": sys_out["answer"],
            "pred_citations": sys_out["citations"],
            "ground_truth_citations": gt_cits,
            "citation_score": cs,
            "norm_recall": nr,
            "negative_correct": nc,
            "elapsed_seconds": sys_out["elapsed_seconds"],
            "confirmation_needed": sys_out["confirmation_needed"],
            "confirmation_retried": sys_out["confirmation_retried"],
            "context_used": sys_out["context_used"],
            "top_k_count": sys_out["top_k_count"],
        }
        results.append(result)

        logger.info(
            f"  → F1={cs['f1']:.2f} NormR={nr:.2f} cit={len(sys_out['citations'])}/{len(gt_cits)} "
            f"{sys_out['elapsed_seconds']:.1f}s"
        )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run TASK-17 evaluation")
    parser.add_argument("--test-set", required=True, type=Path)
    parser.add_argument(
        "--systems",
        default="graphrag,baseline",
        help="Hệ thống chạy, cách bởi dấu phẩy. Mặc định: graphrag,baseline",
    )
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N câu đầu (0=full)")
    parser.add_argument("--out-dir", type=Path, default=Path("data/evaluation/"))
    args = parser.parse_args()

    if not args.test_set.exists():
        print(f"❌ test-set không tồn tại: {args.test_set}", file=sys.stderr)
        return 2

    test_set = json.loads(args.test_set.read_text(encoding="utf-8"))
    if args.limit > 0:
        test_set = test_set[: args.limit]

    systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    invalid = set(systems) - {"graphrag", "baseline"}
    if invalid:
        print(f"❌ Hệ thống không hợp lệ: {invalid}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    logger.info(f"Build shared clients (Neo4j + Qdrant + Anthropic + BGE-M3)...")
    clients = _build_shared_clients()

    all_aggs = {}
    try:
        for system in systems:
            t0 = time.perf_counter()
            results = run_system_on_test_set(test_set, system, clients)
            elapsed = time.perf_counter() - t0
            logger.info(f"[{system}] hoàn thành {len(results)} câu trong {elapsed:.1f}s")

            # Lưu per-question
            out_path = args.out_dir / f"results_{system}_{timestamp}.json"
            out_path.write_text(
                json.dumps(
                    {
                        "system": system,
                        "test_set": str(args.test_set),
                        "timestamp": timestamp,
                        "total_elapsed_s": round(elapsed, 2),
                        "results": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            logger.info(f"[{system}] đã lưu {out_path}")

            agg = aggregate(results)
            all_aggs[system] = agg
            logger.info(f"[{system}] aggregate: {json.dumps({k: v for k, v in agg.items() if not isinstance(v, dict)}, indent=2)}")

        # Markdown summary nếu chạy cả 2 hệ thống
        if "graphrag" in all_aggs and "baseline" in all_aggs:
            md = render_summary_md(
                all_aggs["graphrag"],
                all_aggs["baseline"],
                test_set_file=str(args.test_set),
                timestamp=timestamp,
            )
            md_path = args.out_dir / f"metrics_summary_{timestamp}.md"
            md_path.write_text(md, encoding="utf-8")
            logger.info(f"Markdown summary: {md_path}")
            print("\n" + md)

    finally:
        clients[0].close()  # neo4j_driver
        clients[1].close()  # qdrant_client

    return 0


if __name__ == "__main__":
    sys.exit(main())
