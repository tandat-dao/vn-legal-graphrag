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
from src.evaluation.report_builder import build_human_report

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-system runners
# ---------------------------------------------------------------------------

def _run_one_graphrag(item: dict, clients, llm_cache_dir: Path | None = None,
                      response_mode: str = "auto",
                      verify: bool = False, verify_tier: int = 1,
                      ablation=None) -> dict:
    """Chạy GraphRAG, inject ground-truth jurisdiction từ test_set.

    Eval mode: `force_jurisdiction` bơm jurisdiction từ test_set khi câu hỏi không
    nêu địa phương. Đo retrieval + generation. Hệ 1Q-1A luôn chạy best-effort
    (không còn Confirmation Loop).

    verify/verify_tier: bật Verifier agent (ablation ±verifier). Mặc định off.
    """
    from src.pipeline import run_pipeline
    from src.retrieval.ablation_config import FULL
    neo4j_driver, qdrant_client, anthropic_client, model = clients

    resolved_mode = None if response_mode == "auto" else response_mode
    res = run_pipeline(
        item["question"],
        neo4j_driver=neo4j_driver,
        qdrant_client=qdrant_client,
        anthropic_client=anthropic_client,
        model=model,
        force_jurisdiction=item["jurisdiction"],
        llm_cache_dir=llm_cache_dir,
        response_mode=resolved_mode,
        verify=verify,
        verify_tier=verify_tier,
        ablation=ablation or FULL,
    )

    return {
        "answer": res["answer"],
        "citations": res["citations"],
        "elapsed_seconds": res["elapsed_seconds"],
        "context_used": res["context_used"],
        "top_k_count": res["top_k_count"],
        "context": res.get("context", ""),  # needed cho faithfulness eval
        "response_mode": res.get("response_mode", response_mode),
        "verifier": res.get("verifier"),  # thống kê verifier (None nếu verify=False)
    }


def _run_one_baseline(item: dict, clients, llm_cache_dir: Path | None = None,
                      response_mode: str = "auto") -> dict:
    from src.baseline.naive_rag import run_baseline_query
    _, qdrant_client, anthropic_client, model = clients
    resolved_mode = "general" if response_mode == "auto" else response_mode
    res = run_baseline_query(
        item["question"],
        qdrant_client=qdrant_client,
        anthropic_client=anthropic_client,
        model=model,
        llm_cache_dir=llm_cache_dir,
        mode=resolved_mode,
    )
    return {
        "answer": res["answer"],
        "citations": res["citations"],
        "elapsed_seconds": res["elapsed_seconds"],
        "context_used": res["context_used"],
        "top_k_count": res["top_k_count"],
        "context": res.get("context", ""),
    }


def _run_one_closedbook(item: dict, clients, llm_cache_dir: Path | None = None,
                        response_mode: str = "auto") -> dict:
    """Closed-book baseline (E2a): LLM trả lời KHÔNG retrieval."""
    from src.baseline.closed_book import run_closedbook_query
    _, _, anthropic_client, _ = clients
    mode = "general" if response_mode == "auto" else response_mode
    return run_closedbook_query(item["question"], anthropic_client, llm_cache_dir, mode)


def _run_one_oracle(item: dict, clients, llm_cache_dir: Path | None = None,
                    response_mode: str = "auto", text_index=None) -> dict:
    """Oracle baseline (E2a): generator chạy trên context = GT chunks (trần chẩn đoán)."""
    from src.evaluation.oracle import run_oracle_query
    _, _, anthropic_client, _ = clients
    mode = "general" if response_mode == "auto" else response_mode
    return run_oracle_query(item["question"], item.get("ground_truth_citations", []),
                            text_index, anthropic_client, llm_cache_dir, mode)


def _run_one_bm25(item: dict, clients, llm_cache_dir: Path | None = None,
                  response_mode: str = "auto") -> dict:
    """BM25 baseline (E2a): retrieval LEXICAL thay dense (lazy-build corpus 1 lần)."""
    from src.baseline.bm25_rag import run_bm25_query
    _, _, anthropic_client, _ = clients
    mode = "general" if response_mode == "auto" else response_mode
    return run_bm25_query(item["question"], anthropic_client,
                          cache_dir=llm_cache_dir, mode=mode)


# ---------------------------------------------------------------------------
# Shared client factory (tránh load model nhiều lần)
# ---------------------------------------------------------------------------

def _build_shared_clients(llm_mode: str = "claude"):
    from neo4j import GraphDatabase
    from qdrant_client import QdrantClient

    from src.ingestion.vectorizer import load_model
    from src.utils.llm_config import make_llm_client

    neo4j_driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    qdrant_client = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )
    # Client HỆ THỐNG (GraphRAG + Baseline) theo llm_mode. Judge dựng riêng (Claude cố định).
    anthropic_client = make_llm_client(mode=llm_mode)
    model = load_model()
    return neo4j_driver, qdrant_client, anthropic_client, model


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def run_system_on_test_set(
    test_set: list[dict],
    system: str,
    clients,
    llm_cache_dir: Path | None = None,
    faithfulness_tier: int = 0,  # 0=skip, 1=existence only, 2=existence+LLM judge
    response_mode: str = "auto",
    verify: bool = False,
    verify_tier: int = 1,
    ablation=None,
) -> list[dict]:
    """Chạy 1 hệ thống trên test set, tính metric per-question.

    Args:
        faithfulness_tier: 0=skip Faithfulness; 1=Tier 1 (deterministic existence
            check, $0); 2=Tier 1 + Tier 2 (LLM-as-judge, ~1 Haiku call per citation).

    Returns:
        List per-question result dict.
    """
    _RUNNERS = {
        "graphrag": _run_one_graphrag,
        "baseline": _run_one_baseline,
        "closed-book": _run_one_closedbook,
        "oracle": _run_one_oracle,
        "bm25": _run_one_bm25,
    }
    assert system in _RUNNERS, f"system '{system}' không hợp lệ: {list(_RUNNERS)}"
    runner = _RUNNERS[system]

    # Oracle cần text index của corpus (build MỘT LẦN, tái dùng cả test set)
    oracle_text_index = None
    if system == "oracle":
        from src.evaluation.build_review_sheet import build_text_index
        oracle_text_index = build_text_index(Path("data/raw"))

    # Faithfulness setup (lazy import để không break khi không dùng)
    judge_client = None
    if faithfulness_tier >= 1:
        from src.evaluation.faithfulness import evaluate_faithfulness
        if faithfulness_tier >= 2:
            # Judge = Gemini Flash (FAITHFULNESS_JUDGE_MODEL), tách khỏi generator
            # (Pro) về model/tham số nhưng CÙNG NHÀ với hệ thống → không còn tính
            # độc lập như judge Claude trước đây (D-24). Ghi rõ khi báo cáo số
            # Tier 2; Tier 1 deterministic không dính rủi ro này.
            from src.utils.gemini_fallback import _build_gemini_client
            judge_client = _build_gemini_client(os.getenv("GEMINI_API_KEY"))

    results = []
    for i, item in enumerate(test_set, 1):
        qid = item["id"]
        logger.info(f"[{system}] {i}/{len(test_set)} {qid}: {item['question'][:60]}...")
        try:
            runner_kwargs = dict(llm_cache_dir=llm_cache_dir, response_mode=response_mode)
            if system == "graphrag":
                # Verifier + ablation chỉ áp dụng cho GraphRAG (component hệ thống ta).
                runner_kwargs.update(verify=verify, verify_tier=verify_tier,
                                     ablation=ablation)
            elif system == "oracle":
                runner_kwargs.update(text_index=oracle_text_index)
            sys_out = runner(item, clients, **runner_kwargs)
        except Exception as e:
            logger.exception(f"[{system}] {qid} CRASHED: {e}")
            sys_out = {
                "answer": f"<<ERROR: {e}>>",
                "citations": [],
                "elapsed_seconds": 0.0,
                "context_used": False,
                "top_k_count": 0,
                "context": "",
            }

        gt_cits = item.get("ground_truth_citations", [])
        cs_khoan = citation_score(sys_out["citations"], gt_cits, level="khoan")
        cs_dieu = citation_score(sys_out["citations"], gt_cits, level="dieu")
        nr = norm_recall(sys_out["citations"], gt_cits)
        nc = (
            negative_correct(sys_out["citations"], item["gap_type"])
            if item["gap_type"] == "negative" else None
        )

        # Faithfulness eval (optional)
        faithfulness = None
        if faithfulness_tier >= 1:
            faithfulness = evaluate_faithfulness(
                sys_out["citations"], sys_out["answer"], sys_out.get("context", ""),
                llm_client=judge_client,
                tier2=(faithfulness_tier >= 2),
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
            "citation_score": cs_khoan,
            "citation_score_dieu": cs_dieu,
            "norm_recall": nr,
            "negative_correct": nc,
            "faithfulness": faithfulness,
            "elapsed_seconds": sys_out["elapsed_seconds"],
            "context_used": sys_out["context_used"],
            "top_k_count": sys_out["top_k_count"],
            "context": sys_out.get("context", ""),  # save cho future faithfulness re-eval
            "verifier": sys_out.get("verifier"),    # thống kê verifier (None nếu off)
        }
        results.append(result)

        faith_str = ""
        if faithfulness:
            faith_str = f" Faith[exist={faithfulness['existence_rate']:.2f}]"
            if faithfulness_tier >= 2:
                faith_str = f" Faith[exist={faithfulness['existence_rate']:.2f} support={faithfulness['support_rate']:.2f}]"
        logger.info(
            f"  → F1_khoan={cs_khoan['f1']:.2f} F1_dieu={cs_dieu['f1']:.2f} "
            f"NormR={nr:.2f}{faith_str} cit={len(sys_out['citations'])}/{len(gt_cits)} "
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
        help="Hệ thống chạy, cách bởi dấu phẩy: graphrag | baseline (naive RAG) | "
             "bm25 (E2a, lexical) | closed-book (E2a, không retrieval) | "
             "oracle (E2a, context=GT chunks). Mặc định: graphrag,baseline",
    )
    parser.add_argument("--limit", type=int, default=0, help="Chỉ chạy N câu đầu (0=full)")
    parser.add_argument("--out-dir", type=Path, default=Path("data/evaluation/"))
    parser.add_argument(
        "--reuse-results",
        type=Path,
        nargs="+",
        default=None,
        help="Re-compute metric từ file results_*.json đã chạy (skip LLM). "
             "Truyền 1 hoặc 2 file (graphrag + baseline). Tiết kiệm API khi sửa metric.",
    )
    parser.add_argument(
        "--llm-cache-dir",
        type=Path,
        default=Path("data/evaluation/.llm_cache/"),
        help="Thư mục lưu LLM cache. Cache HIT khi hash(prompt) trùng → $0 API. "
             "Auto-invalidate khi retrieval thay đổi (prompt khác). Default bật.",
    )
    parser.add_argument(
        "--no-llm-cache",
        action="store_true",
        help="Tắt LLM cache (luôn gọi API). Dùng khi test latency hoặc cần kết quả non-deterministic mới.",
    )
    parser.add_argument(
        "--clear-llm-cache",
        action="store_true",
        help="Xóa toàn bộ cache trước khi chạy. Dùng khi thay đổi prompt template.",
    )
    parser.add_argument(
        "--response-mode",
        default="auto",
        choices=["auto", "general", "irac"],
        help="Chế độ trả lời: auto (planner tự chọn), general (gọn), irac (tư vấn IRAC). "
             "Mặc định auto. Dùng general/irac để so sánh A/B 2 mode.",
    )
    parser.add_argument(
        "--faithfulness-tier",
        type=int, default=0, choices=[0, 1, 2],
        help="Faithfulness metric tier: 0=skip (default), 1=existence-only ($0), "
             "2=existence+LLM-judge (~1 Haiku call per citation). Đo %% citation "
             "có chunk match context (Tier 1) và semantic support (Tier 2).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Bật Verifier agent lọc citation cho GraphRAG (ablation ±verifier). "
             "Mặc định TẮT (= hành vi cũ).",
    )
    parser.add_argument(
        "--verify-tier",
        type=int, default=1, choices=[0, 1, 2],
        help="Tier verifier: 0=no-op, 1=grounding ($0, mặc định), "
             "2=grounding + LLM support judge (TỐN ~1 Haiku call per citation).",
    )
    parser.add_argument(
        "--llm-mode", choices=["claude", "claude-fallback", "gemini", "gemini-fallback"], default="claude",
        help="LLM cho HỆ THỐNG (GraphRAG + Baseline): claude (mặc định, reproducible) | "
             "claude-fallback | gemini end-to-end. Judge giữ Claude cố định (thước đo).",
    )
    parser.add_argument(
        "--sample", type=int, default=0,
        help="Chọn NGẪU NHIÊN N câu (0=không). Khác --limit (N câu đầu). Dùng với --seed.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed cho --sample.")
    parser.add_argument(
        "--ablation", default="full",
        help="E1 ablation (chỉ GraphRAG): full | no-theme | no-jurisdiction | "
             "no-implements | no-amends | no-temporal | no-traversal | dense-only | "
             "graphrag-basic (giữ 3 giai đoạn, tắt đồng thời 3 bộ lọc — bậc E2).",
    )
    args = parser.parse_args()

    if not args.test_set.exists():
        print(f"❌ test-set không tồn tại: {args.test_set}", file=sys.stderr)
        return 2

    test_set = json.loads(args.test_set.read_text(encoding="utf-8"))
    if args.sample > 0:
        import random
        rng = random.Random(args.seed)
        test_set = rng.sample(test_set, min(args.sample, len(test_set)))
        logger.info(f"SAMPLE {len(test_set)} câu ngẫu nhiên (seed={args.seed}): "
                    f"{[it['id'] for it in test_set]}")
    if args.limit > 0:
        test_set = test_set[: args.limit]

    # --- Reuse mode: re-compute metric từ results JSON cũ, không gọi LLM ---
    if args.reuse_results:
        logger.info(f"REUSE MODE: re-compute metric từ {len(args.reuse_results)} file, KHÔNG gọi API")
        args.out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        all_aggs = {}
        all_results: dict[str, list[dict]] = {}
        for path in args.reuse_results:
            data = json.loads(path.read_text(encoding="utf-8"))
            system = data["system"]
            old_results = data["results"]
            # Build map id -> answer+citations để re-compute metric
            test_by_id = {it["id"]: it for it in test_set}
            new_results = []
            from src.retrieval.answer_generator import parse_citations
            for old in old_results:
                item = test_by_id.get(old["id"])
                if not item:
                    continue
                # Re-parse citations từ answer text với regex hiện tại (parser có thể đã sửa).
                # Nếu answer rỗng (eval cũ crash) → fall back về pred_citations đã lưu.
                if old.get("answer", "").strip() and not old["answer"].startswith("<<ERROR"):
                    pred_cits = parse_citations(old["answer"])
                else:
                    pred_cits = old.get("pred_citations", [])
                gt_cits = item.get("ground_truth_citations", [])
                from src.evaluation.metrics import citation_score as _cs
                cs_khoan = _cs(pred_cits, gt_cits, level="khoan")
                cs_dieu = _cs(pred_cits, gt_cits, level="dieu")
                nr = norm_recall(pred_cits, gt_cits)
                nc = negative_correct(pred_cits, item["gap_type"]) if item["gap_type"] == "negative" else None
                new_results.append({
                    **old,
                    # Force-refresh metadata từ test_set hiện tại (Q024 đổi gap_type, GT đổi, v.v.)
                    "gap_type": item["gap_type"],
                    "theme": item.get("theme", old.get("theme")),
                    "jurisdiction": item.get("jurisdiction", old.get("jurisdiction")),
                    "difficulty": item.get("difficulty", old.get("difficulty")),
                    "ground_truth_citations": gt_cits,
                    "pred_citations": pred_cits,  # re-parsed với parser hiện tại
                    "citation_score": cs_khoan,
                    "citation_score_dieu": cs_dieu,
                    "norm_recall": nr,
                    "negative_correct": nc,
                })
            agg = aggregate(new_results)
            all_aggs[system] = agg
            all_results[system] = new_results
            out_path = args.out_dir / f"results_{system}_reused_{timestamp}.json"
            out_path.write_text(json.dumps({
                "system": system, "test_set": str(args.test_set),
                "timestamp": timestamp, "reused_from": str(path),
                "results": new_results,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"[{system}] re-computed → {out_path}")
            logger.info(f"[{system}] aggregate: F1_kh={agg['f1_mean']:.3f} F1_di={agg['f1_dieu_mean']:.3f} NormR={agg['norm_recall_mean']:.3f}")

        if "graphrag" in all_aggs and "baseline" in all_aggs:
            md = render_summary_md(all_aggs["graphrag"], all_aggs["baseline"],
                                    test_set_file=str(args.test_set), timestamp=timestamp + "-reused")
            md_path = args.out_dir / f"metrics_summary_reused_{timestamp}.md"
            md_path.write_text(md, encoding="utf-8")
            logger.info(f"Markdown summary: {md_path}")
            print("\n" + md)

        if all_results:
            report_path = args.out_dir / f"REPORT_reused_{timestamp}.md"
            build_human_report(
                test_set,
                all_results,
                report_path,
                timestamp=timestamp + " (reused)",
                test_set_file=str(args.test_set),
                run_config={
                    "mode": "REUSE — re-compute metric từ results_*.json cũ, KHÔNG gọi LLM",
                    "reused_files": [str(p) for p in args.reuse_results],
                },
            )
            logger.info(f"Human-readable report: {report_path}")
        return 0

    systems = [s.strip() for s in args.systems.split(",") if s.strip()]
    from src.retrieval.ablation_config import get_ablation
    ablation_cfg = get_ablation(args.ablation)
    if ablation_cfg.name != "full":
        logger.info(f"ABLATION MODE: {ablation_cfg.name} "
                    f"(kỳ vọng sụp {ablation_cfg.gap_target or '—'})")
    invalid = set(systems) - {"graphrag", "baseline", "closed-book", "oracle", "bm25"}
    if invalid:
        print(f"❌ Hệ thống không hợp lệ: {invalid}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # --- LLM cache setup ---
    llm_cache_dir = None if args.no_llm_cache else args.llm_cache_dir
    if args.clear_llm_cache and llm_cache_dir and llm_cache_dir.exists():
        import shutil
        shutil.rmtree(llm_cache_dir)
        logger.info(f"LLM cache cleared: {llm_cache_dir}")
    if llm_cache_dir:
        logger.info(f"LLM cache enabled: {llm_cache_dir} (cache HIT → $0 API)")
    else:
        logger.info("LLM cache DISABLED — sẽ tốn API cho mọi câu")

    logger.info(f"Build shared clients (Neo4j + Qdrant + LLM[{args.llm_mode}] + BGE-M3)...")
    clients = _build_shared_clients(llm_mode=args.llm_mode)

    all_aggs = {}
    all_results: dict[str, list[dict]] = {}
    try:
        for system in systems:
            t0 = time.perf_counter()
            results = run_system_on_test_set(
                test_set, system, clients,
                llm_cache_dir=llm_cache_dir,
                faithfulness_tier=args.faithfulness_tier,
                response_mode=args.response_mode,
                verify=args.verify,
                verify_tier=args.verify_tier,
                ablation=ablation_cfg,
            )
            all_results[system] = results
            elapsed = time.perf_counter() - t0
            logger.info(f"[{system}] hoàn thành {len(results)} câu trong {elapsed:.1f}s")

            # Lưu per-question (gắn tên ablation vào filename để không ghi đè run full)
            abl_tag = "" if ablation_cfg.name == "full" else f"_{ablation_cfg.name}"
            out_path = args.out_dir / f"results_{system}{abl_tag}_{timestamp}.json"
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

        # Human-readable report: gộp câu hỏi + GT + answer + citations của TẤT CẢ
        # hệ thống đã chạy. Sinh ra ngay cả khi chỉ chạy 1 hệ thống.
        # run_config: minh bạch các flag ảnh hưởng kết quả để người đọc biết
        # eval đã chạy dưới điều kiện nào (reproducibility).
        if all_results:
            from src.utils.llm_config import ANTHROPIC_MAX_RETRIES
            run_config = {
                "systems": ",".join(systems),
                "limit": args.limit or "full",
                "ablation": ablation_cfg.name,
                "force_jurisdiction": "ground-truth (bơm khi câu hỏi không nêu địa phương)",
                "llm_cache": "ON" if llm_cache_dir else "OFF",
                "anthropic_max_retries": ANTHROPIC_MAX_RETRIES,
            }
            report_path = args.out_dir / f"REPORT_{timestamp}.md"
            build_human_report(
                test_set,
                all_results,
                report_path,
                timestamp=timestamp,
                test_set_file=str(args.test_set),
                run_config=run_config,
            )
            logger.info(f"Human-readable report: {report_path}")

    finally:
        clients[0].close()  # neo4j_driver
        clients[1].close()  # qdrant_client

    return 0


if __name__ == "__main__":
    sys.exit(main())
