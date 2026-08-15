"""
Retrieval-metric harness ($0) + go/no-go cho direction 2 (finetune embedding).

Đo CHẤT LƯỢNG RETRIEVAL (không generation → KHÔNG tốn Sonnet) trên candidate pool:
  - Recall@k + MRR ở cấp Điều và Khoản, so GT.
  - So sánh DENSE (BGE-M3 hiện tại) vs CROSS-ENCODER rerank (teacher) trên cùng pool.

Mục đích go/no-go: nếu cross-encoder NÂNG Recall@k/MRR rõ → có "đích" để distill
xuống BGE-M3 (finetune đáng làm). Nếu không → skip finetune, ghi limitation.

Chi phí: planner dùng cache (.planner_cache → ~$0), dense + cross-encoder chạy
LOCAL ($0). Cross-encoder tải model ~600MB lần đầu (CPU — MPS treo).

CLI:
  python -m src.evaluation.retrieval_eval --test-set data/evaluation/test_set_dat_dai.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from src.ingestion.vectorizer import encode_text, load_model
from src.utils.llm_config import make_llm_client
from src.retrieval.query_planner import plan_query
from src.retrieval.subgraph_extractor import extract_subgraph
from src.retrieval.semantic_filter import _strip_jurisdiction_for_dense, _qdrant_id_to_hex
from src.evaluation.metrics import cit_matches

load_dotenv()


# ---------------------------------------------------------------------------
# Map retrieved chunk → citation {van_ban, dieu, khoan, loai}
# ---------------------------------------------------------------------------

def _chunk_to_citation(norm_id: str, context_path: list) -> dict:
    """Parse (dieu, khoan, loai) từ context_path để match với GT qua cit_matches."""
    dieu = khoan = None
    loai = "dieu"
    for part in (context_path[1:] if context_path else []):
        p = str(part)
        m = re.match(r"\s*Điều\s+(\w+)", p, re.IGNORECASE)
        if m:
            dieu, loai = m.group(1), "dieu"; continue
        m = re.match(r"\s*Khoản\s+(\w+)", p, re.IGNORECASE)
        if m:
            khoan = m.group(1); continue
        m = re.match(r"\s*Phụ\s*lục\s+(\w+)", p, re.IGNORECASE)
        if m:
            dieu, loai = m.group(1), "phu_luc"; continue
        if re.match(r"\s*Phụ\s*lục", p, re.IGNORECASE):
            loai = "phu_luc"; dieu = dieu or "_default"
    return {"van_ban": norm_id, "dieu": dieu, "khoan": khoan, "loai": loai}


_CTX_PATH_CYPHER = "MATCH (t:TextUnit) WHERE t.id IN $ids RETURN t.id AS id, t.text AS text, t.context_path AS cp, t.norm_id AS norm_id"


def _fetch_chunk_meta(text_unit_ids: list[str], neo4j_driver) -> dict[str, dict]:
    """{id: {text, context_path(list), norm_id}} cho candidate chunks."""
    if not text_unit_ids:
        return {}
    with neo4j_driver.session() as s:
        rows = s.run(_CTX_PATH_CYPHER, ids=text_unit_ids).data()
    out = {}
    for r in rows:
        cp = r["cp"]
        if isinstance(cp, str):
            try:
                cp = json.loads(cp)
            except Exception:
                cp = [cp]
        out[r["id"]] = {"text": r["text"] or "", "context_path": cp or [], "norm_id": r["norm_id"] or ""}
    return out


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------

def _recall_at_k(cands: list[dict], gt: list[dict], level: str, k: int) -> float:
    """GT-coverage trong top-k: #GT được phủ / #GT."""
    topk = cands[:k]
    covered = sum(1 for g in gt if any(cit_matches(c, g, level) for c in topk))
    return covered / len(gt)


def _mrr(cands: list[dict], gt: list[dict], level: str) -> float:
    for i, c in enumerate(cands, 1):
        if any(cit_matches(c, g, level) for g in gt):
            return 1.0 / i
    return 0.0


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def _build_clients():
    neo4j = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    qdrant = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"),
                          port=int(os.getenv("QDRANT_PORT", "6333")))
    # Bộ lập kế hoạch PHẢI theo cùng nhà cung cấp với mẻ sinh đem ra so sánh.
    # Trước đây hàm này cố định Anthropic trong khi các mẻ sinh chạy
    # `--llm-mode gemini` → hai bên dùng KẾ HOẠCH TRUY VẤN KHÁC NHAU, nên
    # "độ bao phủ" đo được không phải là ngữ cảnh mà bộ sinh thực sự nhận.
    llm_client = make_llm_client(mode=os.getenv("LLM_MODE", "claude"))
    model = load_model()
    return neo4j, qdrant, llm_client, model


def run(test_set: list[dict], do_rerank: bool = True, pool: int = 50, ks=(5, 10)):
    neo4j, qdrant, anthropic_client, model = _build_clients()
    reranker_model = None
    if do_rerank:
        from src.retrieval.reranker import load_reranker, rerank as _rerank
        reranker_model = load_reranker()  # tải 1 lần (CPU)

    rows = []
    try:
        for item in test_set:
            if item.get("gap_type") == "negative":
                continue
            gt = item.get("ground_truth_citations", [])
            if not gt:
                continue
            q = item["question"]
            plan = plan_query(q, anthropic_client, neo4j_driver=neo4j)
            plan = dict(plan)
            plan["jurisdiction"] = item.get("jurisdiction") or plan.get("jurisdiction")
            norm_ids, _ = extract_subgraph(q, plan, neo4j, qdrant, model)
            gt_norms = {g.get("van_ban") for g in gt}
            norm_hit = 1.0 if gt_norms & set(norm_ids) else 0.0

            row = {"id": item["id"], "norm_recall": norm_hit,
                   "dense": None, "rerank": None}
            if norm_ids:
                # Dense pool trong norm_ids
                qf = Filter(must=[
                    FieldCondition(key="content_type", match=MatchValue(value="text_unit")),
                    FieldCondition(key="norm_id", match=MatchAny(any=norm_ids)),
                ])
                qv = encode_text(model, _strip_jurisdiction_for_dense(q))
                points = qdrant.query_points("legal_texts", query=qv, limit=pool,
                                             query_filter=qf).points
                ids = [_qdrant_id_to_hex(p.id) for p in points]
                meta = _fetch_chunk_meta(ids, neo4j)
                # dense order
                dense_cits = []
                cand_for_rerank = []
                for p, tid in zip(points, ids):
                    m = meta.get(tid, {})
                    cit = _chunk_to_citation(m.get("norm_id") or p.payload.get("norm_id", ""),
                                             m.get("context_path", []))
                    dense_cits.append(cit)
                    cand_for_rerank.append({"cit": cit, "text": m.get("text", "")})
                row["dense"] = _metrics(dense_cits, gt, ks)
                if do_rerank and cand_for_rerank:
                    rr = _rerank(q, cand_for_rerank, model=reranker_model)
                    rerank_cits = [c["cit"] for c in rr]
                    row["rerank"] = _metrics(rerank_cits, gt, ks)
            rows.append(row)
            _log_row(row, ks)
    finally:
        neo4j.close()
    return rows


def _metrics(cands: list[dict], gt: list[dict], ks) -> dict:
    out = {"mrr_dieu": _mrr(cands, gt, "dieu"), "mrr_khoan": _mrr(cands, gt, "khoan")}
    for k in ks:
        out[f"recall_dieu@{k}"] = _recall_at_k(cands, gt, "dieu", k)
        out[f"recall_khoan@{k}"] = _recall_at_k(cands, gt, "khoan", k)
    return out


def _log_row(row, ks):
    d, r = row.get("dense"), row.get("rerank")
    def fmt(m): return f"R@{ks[0]}d={m[f'recall_dieu@{ks[0]}']:.2f} MRRd={m['mrr_dieu']:.2f}" if m else "—"
    print(f"  {row['id']:<6} normR={row['norm_recall']:.0f} | dense[{fmt(d)}] | rerank[{fmt(r)}]")


def _aggregate(rows, ks):
    def mean(key_path):
        vals = []
        for r in rows:
            m = r.get(key_path[0])
            if m is not None:
                vals.append(m[key_path[1]])
        return sum(vals) / len(vals) if vals else 0.0
    print("\n=== AGGREGATE (n={}) — DENSE vs RERANK ($0) ===".format(len(rows)))
    print(f"{'Metric':<18}{'DENSE':>9}{'RERANK':>9}{'Δ':>9}")
    metrics = ["mrr_dieu", "mrr_khoan"] + \
              [f"recall_dieu@{k}" for k in ks] + [f"recall_khoan@{k}" for k in ks]
    for mk in metrics:
        md, mr = mean(("dense", mk)), mean(("rerank", mk))
        print(f"{mk:<18}{md:>9.3f}{mr:>9.3f}{mr-md:>+9.3f}")
    nr = sum(r["norm_recall"] for r in rows) / len(rows) if rows else 0.0
    print(f"\n[Stage 1/2 norm_recall = {nr:.3f} — chặn trên cho mọi chunk metric]")


def main() -> int:
    ap = argparse.ArgumentParser(description="Retrieval-metric harness ($0) — dense vs cross-encoder")
    ap.add_argument("--test-set", required=True, type=Path)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--pool", type=int, default=50, help="Kích thước dense candidate pool")
    ap.add_argument("--no-rerank", action="store_true", help="Chỉ đo dense (bỏ cross-encoder)")
    args = ap.parse_args()
    if not args.test_set.exists():
        print(f"❌ không thấy {args.test_set}", file=sys.stderr); return 2
    ts = json.loads(args.test_set.read_text(encoding="utf-8"))
    if args.limit > 0:
        ts = ts[: args.limit]
    ks = (5, 10)
    print(f"Retrieval eval ($0) trên {len(ts)} câu | pool={args.pool} | rerank={not args.no_rerank}\n")
    rows = run(ts, do_rerank=not args.no_rerank, pool=args.pool, ks=ks)
    _aggregate(rows, ks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
