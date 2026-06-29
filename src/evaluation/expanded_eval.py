"""
Expanded evaluation analysis ($0) — Tier 0 metric expansion.

Đọc 2 results JSON (graphrag + baseline) đã chạy sẵn → KHÔNG gọi API, KHÔNG DB.
Bổ sung các thang đo mà `metrics.aggregate` chưa surface, phục vụ chương Evaluation:

  1. Paired significance — N=26 nhỏ → +Δ F1 có ý nghĩa thống kê không?
     (paired bootstrap 95% CI + Wilcoxon signed-rank + win/loss/tie count)
  2. Citation behavior — over-citation rate, mean pred/gt count, precision–recall gap
     (chẩn đoán "ưu/nhược": precision thấp = cite thừa; recall thấp = bỏ sót)
  3. Per-gap + per-jurisdiction breakdown (Gap 1/2/3/4) — tái dùng cit_matches.
  4. Báo cáo Markdown tiếng Anh hợp nhất cho luận văn.

Deterministic: bootstrap dùng seed cố định → tái lập đúng số.

CLI:
  python -m src.evaluation.expanded_eval                     # auto-pick latest pair
  python -m src.evaluation.expanded_eval --graphrag G.json --baseline B.json --out report.md
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

_EVAL_DIR = Path("data/evaluation")
_TEST_SET = _EVAL_DIR / "test_set_dat_dai.json"
_BOOTSTRAP_ITERS = 10000
_BOOTSTRAP_SEED = 42


# ---------------------------------------------------------------------------
# Load + align
# ---------------------------------------------------------------------------

def _canonical_meta(test_set: Path = _TEST_SET) -> dict[str, dict]:
    """{id: {gap_type, jurisdiction, theme}} từ test set HIỆN TẠI — single source of
    truth. Cần thiết vì nhãn gap_type lưu trong run cũ có thể lệch (gap4 từng gộp
    vào gap3 trước khi relabel)."""
    if not test_set.exists():
        return {}
    ts = json.loads(test_set.read_text(encoding="utf-8"))
    return {x["id"]: {"gap_type": x.get("gap_type"), "jurisdiction": x.get("jurisdiction"),
                      "theme": x.get("theme")} for x in ts}


def _load(path: Path, meta_by_id: dict[str, dict] | None = None) -> tuple[dict, list[dict]]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    results = obj.get("results", [])
    if meta_by_id:  # đồng bộ nhãn theo test set hiện tại
        for q in results:
            m = meta_by_id.get(q["id"])
            if m:
                q["gap_type"], q["jurisdiction"], q["theme"] = (
                    m["gap_type"], m["jurisdiction"], m["theme"])
    return obj, results


def _latest(system: str) -> Path | None:
    cands = sorted(_EVAL_DIR.glob(f"results_{system}_*.json"))
    # chỉ giữ file N==26 single-run (uniq ids == 26)
    best = None
    for f in cands:
        try:
            res = json.loads(f.read_text(encoding="utf-8")).get("results", [])
        except Exception:
            continue
        ids = [r["id"] for r in res]
        if len(ids) == 26 and len(set(ids)) == 26:
            best = f
    return best


def _index_by_id(results: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in results}


def _f1k(q: dict) -> float:
    return q["citation_score"]["f1"]


def _f1d(q: dict) -> float:
    return q.get("citation_score_dieu", {}).get("f1", 0.0)


def _normr(q: dict) -> float:
    return q["norm_recall"]


# ---------------------------------------------------------------------------
# Significance (paired, $0, deterministic)
# ---------------------------------------------------------------------------

def _paired_deltas(g_idx, b_idx, metric_fn, *, exclude_negative=True) -> tuple[list[float], list[str]]:
    """g - b per question, trên các id chung. Bỏ câu negative (F1 cite trivially 1)."""
    deltas, ids = [], []
    for qid in sorted(set(g_idx) & set(b_idx)):
        gq, bq = g_idx[qid], b_idx[qid]
        if exclude_negative and gq.get("gap_type") == "negative":
            continue
        deltas.append(metric_fn(gq) - metric_fn(bq))
        ids.append(qid)
    return deltas, ids


def _bootstrap_ci(deltas: list[float], iters=_BOOTSTRAP_ITERS, seed=_BOOTSTRAP_SEED, alpha=0.05):
    """Paired bootstrap CI cho mean(delta). Resample câu hỏi có hoàn lại."""
    arr = np.asarray(deltas, dtype=float)
    if arr.size == 0:
        return (0.0, 0.0, 0.0)
    rng = np.random.default_rng(seed)
    means = arr[rng.integers(0, arr.size, size=(iters, arr.size))].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return (float(arr.mean()), float(lo), float(hi))


def _wilcoxon_p(deltas: list[float]) -> float:
    """Wilcoxon signed-rank two-sided p. NaN nếu mọi delta = 0."""
    arr = np.asarray(deltas, dtype=float)
    if np.allclose(arr, 0.0):
        return float("nan")
    try:
        return float(stats.wilcoxon(arr, zero_method="wilcox", alternative="two-sided").pvalue)
    except ValueError:
        return float("nan")


def _win_loss_tie(deltas: list[float], eps=1e-9) -> tuple[int, int, int]:
    w = sum(1 for d in deltas if d > eps)
    l = sum(1 for d in deltas if d < -eps)
    t = sum(1 for d in deltas if abs(d) <= eps)
    return w, l, t


def _significance_block(g_idx, b_idx) -> dict:
    out = {}
    for name, fn in [("f1_khoan", _f1k), ("f1_dieu", _f1d), ("norm_recall", _normr)]:
        deltas, ids = _paired_deltas(g_idx, b_idx, fn)
        mean, lo, hi = _bootstrap_ci(deltas)
        w, l, t = _win_loss_tie(deltas)
        out[name] = {
            "n": len(deltas), "mean_delta": mean, "ci_lo": lo, "ci_hi": hi,
            "wilcoxon_p": _wilcoxon_p(deltas), "win": w, "loss": l, "tie": t,
            "ci_excludes_zero": (lo > 0 or hi < 0),
        }
    return out


# ---------------------------------------------------------------------------
# Citation behavior
# ---------------------------------------------------------------------------

def _citation_behavior(results: list[dict]) -> dict:
    """Chẩn đoán over/under-citation trên câu có GT (bỏ negative)."""
    preds, gts, precs, recs, over = [], [], [], [], 0
    n = 0
    for q in results:
        if q.get("gap_type") == "negative":
            continue
        cs = q["citation_score"]
        preds.append(cs["pred_count"]); gts.append(cs["gt_count"])
        precs.append(cs["precision"]); recs.append(cs["recall"])
        if cs["pred_count"] > cs["match_count"]:   # có pred không khớp GT
            over += 1
        n += 1
    if n == 0:
        return {}
    return {
        "n": n,
        "mean_pred": statistics.mean(preds),
        "mean_gt": statistics.mean(gts),
        "mean_precision": statistics.mean(precs),
        "mean_recall": statistics.mean(recs),
        "pr_gap": statistics.mean(recs) - statistics.mean(precs),
        "over_cite_rate": over / n,
    }


# ---------------------------------------------------------------------------
# Per-gap / per-jurisdiction breakdown (graphrag vs baseline)
# ---------------------------------------------------------------------------

def _group_means(results: list[dict], key: str) -> dict[str, dict]:
    groups = defaultdict(list)
    for q in results:
        groups[q.get(key, "?")].append(q)
    out = {}
    for g, qs in groups.items():
        non_neg = qs  # giữ cả negative cho jurisdiction; F1 trên gap dùng tất cả
        out[g] = {
            "n": len(qs),
            "f1_khoan": statistics.mean(_f1k(q) for q in qs),
            "f1_dieu": statistics.mean(_f1d(q) for q in qs),
            "norm_recall": statistics.mean(_normr(q) for q in qs),
        }
    return out


def _faithfulness_mean(results: list[dict]) -> float | None:
    vals = [q["faithfulness"]["faithful_rate"] for q in results
            if isinstance(q.get("faithfulness"), dict)
            and not math.isnan(q["faithfulness"].get("faithful_rate", float("nan")))]
    return statistics.mean(vals) if vals else None


def _overall(results: list[dict]) -> dict:
    non_neg = [q for q in results if q.get("gap_type") != "negative"]
    lat = [q["elapsed_seconds"] for q in results]
    return {
        "f1_khoan": statistics.mean(_f1k(q) for q in non_neg),
        "f1_dieu": statistics.mean(_f1d(q) for q in non_neg),
        "precision_khoan": statistics.mean(q["citation_score"]["precision"] for q in non_neg),
        "recall_khoan": statistics.mean(q["citation_score"]["recall"] for q in non_neg),
        "norm_recall": statistics.mean(_normr(q) for q in non_neg),
        "faithfulness": _faithfulness_mean(results),
        "latency_mean": statistics.mean(lat),
        "latency_p95": sorted(lat)[int(0.95 * (len(lat) - 1))],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _fmt(v, nd=3):
    if v is None:
        return "N/A"
    if isinstance(v, float) and math.isnan(v):
        return "—"
    return f"{v:.{nd}f}"


def _stars(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def build_report(g_meta, g_res, b_meta, b_res) -> str:
    g_idx, b_idx = _index_by_id(g_res), _index_by_id(b_res)
    g_ov, b_ov = _overall(g_res), _overall(b_res)
    sig = _significance_block(g_idx, b_idx)
    g_beh, b_beh = _citation_behavior(g_res), _citation_behavior(b_res)

    L = []
    L.append("# Expanded Evaluation Report (Tier 0, $0 offline)")
    L.append("")
    L.append(f"- **GraphRAG run**: `{g_meta.get('timestamp')}` — N={len(g_res)}")
    L.append(f"- **Baseline run**: `{b_meta.get('timestamp')}` — N={len(b_res)}")
    L.append(f"- Test set: `{g_meta.get('test_set')}`")
    L.append(f"- Bootstrap: {_BOOTSTRAP_ITERS} resamples, seed={_BOOTSTRAP_SEED} (deterministic)")
    L.append("")

    # 1. Overall
    L.append("## 1. Overall comparison")
    L.append("")
    L.append("| Metric | GraphRAG | Baseline | Δ (G−B) |")
    L.append("|---|---:|---:|---:|")
    rows = [
        ("Citation F1 — Khoản (strict)", "f1_khoan"),
        ("Citation Precision — Khoản", "precision_khoan"),
        ("Citation Recall — Khoản", "recall_khoan"),
        ("Citation F1 — Điều (routing)", "f1_dieu"),
        ("Norm-level Recall", "norm_recall"),
        ("Faithfulness (faithful_rate)", "faithfulness"),
        ("Latency mean (s)", "latency_mean"),
        ("Latency p95 (s)", "latency_p95"),
    ]
    for label, key in rows:
        g, b = g_ov.get(key), b_ov.get(key)
        d = (g - b) if isinstance(g, (int, float)) and isinstance(b, (int, float)) else None
        L.append(f"| {label} | {_fmt(g)} | {_fmt(b)} | {_fmt(d) if d is not None else 'N/A'} |")
    L.append("")
    L.append("> Citation metrics tính trên câu có GT (loại negative). Faithfulness chỉ có ở GraphRAG run.")
    L.append("")

    # 2. Significance
    L.append("## 2. Statistical significance (paired, per-question)")
    L.append("")
    L.append("Paired bootstrap 95% CI của mean(Δ) + Wilcoxon signed-rank (two-sided). "
             "CI không chứa 0 ⇒ khác biệt vững ở mức 95%.")
    L.append("")
    L.append("| Metric | n | mean Δ | 95% CI | Wilcoxon p | sig | Win/Loss/Tie |")
    L.append("|---|---:|---:|---|---:|:--:|---:|")
    for name, label in [("f1_khoan", "F1 Khoản"), ("f1_dieu", "F1 Điều"), ("norm_recall", "Norm Recall")]:
        s = sig[name]
        ci = f"[{_fmt(s['ci_lo'])}, {_fmt(s['ci_hi'])}]"
        flag = _stars(s["wilcoxon_p"])
        L.append(f"| {label} | {s['n']} | {_fmt(s['mean_delta'])} | {ci} | "
                 f"{_fmt(s['wilcoxon_p'])} | {flag} | {s['win']}/{s['loss']}/{s['tie']} |")
    L.append("")
    L.append("> Ký hiệu: `***` p<0.001, `**` p<0.01, `*` p<0.05, `ns` không ý nghĩa.")
    L.append("")

    # 3. Citation behavior
    L.append("## 3. Citation behavior (over/under-citation)")
    L.append("")
    L.append("| Metric | GraphRAG | Baseline |")
    L.append("|---|---:|---:|")
    for label, k in [
        ("Mean predicted citations / Q", "mean_pred"),
        ("Mean GT citations / Q", "mean_gt"),
        ("Mean precision", "mean_precision"),
        ("Mean recall", "mean_recall"),
        ("Recall − Precision gap", "pr_gap"),
        ("Over-citation rate (% Q with unmatched preds)", "over_cite_rate"),
    ]:
        L.append(f"| {label} | {_fmt(g_beh.get(k))} | {_fmt(b_beh.get(k))} |")
    L.append("")
    L.append("> P–R gap > 0 ⇒ recall vượt precision (xu hướng cite thừa). "
             "Over-citation rate cao ⇒ nhiều câu kéo citation ngoài GT.")
    L.append("")

    # 4. Per-gap
    L.append("## 4. Per-gap breakdown (F1 Khoản)")
    L.append("")
    g_gap, b_gap = _group_means(g_res, "gap_type"), _group_means(b_res, "gap_type")
    L.append("| Gap | N | G F1(Kh) | B F1(Kh) | Δ | G F1(Đ) | G NormR |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    gap_label = {"gap1": "Gap1 đa lĩnh vực", "gap2": "Gap2 địa phương",
                 "gap3": "Gap3 đa tầng", "gap4": "Gap4 phiên bản", "negative": "Negative"}
    for gap in sorted(set(g_gap) | set(b_gap)):
        g, b = g_gap.get(gap, {}), b_gap.get(gap, {})
        d = g.get("f1_khoan", 0) - b.get("f1_khoan", 0)
        L.append(f"| {gap_label.get(gap, gap)} | {g.get('n', b.get('n', 0))} | "
                 f"{_fmt(g.get('f1_khoan'))} | {_fmt(b.get('f1_khoan'))} | {_fmt(d)} | "
                 f"{_fmt(g.get('f1_dieu'))} | {_fmt(g.get('norm_recall'))} |")
    L.append("")

    # 5. Per-jurisdiction (Gap 2 focus)
    L.append("## 5. Per-jurisdiction breakdown (Gap 2 focus)")
    L.append("")
    g_j, b_j = _group_means(g_res, "jurisdiction"), _group_means(b_res, "jurisdiction")
    L.append("| Jurisdiction | N | G F1(Kh) | B F1(Kh) | Δ | G NormR | B NormR |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for j in sorted(set(g_j) | set(b_j)):
        g, b = g_j.get(j, {}), b_j.get(j, {})
        d = g.get("f1_khoan", 0) - b.get("f1_khoan", 0)
        L.append(f"| {j} | {g.get('n', b.get('n', 0))} | {_fmt(g.get('f1_khoan'))} | "
                 f"{_fmt(b.get('f1_khoan'))} | {_fmt(d)} | {_fmt(g.get('norm_recall'))} | "
                 f"{_fmt(b.get('norm_recall'))} |")
    L.append("")

    # 6. Auto interpretation
    L.append("## 6. Interpretation")
    L.append("")
    sk = sig["f1_khoan"]
    verdict = ("statistically significant" if sk["ci_excludes_zero"]
               else "NOT statistically significant at 95%")
    L.append(f"- **Headline**: GraphRAG F1 Khoản {_fmt(g_ov['f1_khoan'])} vs baseline "
             f"{_fmt(b_ov['f1_khoan'])} (Δ {_fmt(sk['mean_delta'])}), 95% CI "
             f"[{_fmt(sk['ci_lo'])}, {_fmt(sk['ci_hi'])}] → **{verdict}**; "
             f"win/loss/tie = {sk['win']}/{sk['loss']}/{sk['tie']}.")
    if g_beh and b_beh:
        L.append(f"- **Citation behavior**: baseline over-citation rate "
                 f"{_fmt(b_beh['over_cite_rate'])} vs GraphRAG {_fmt(g_beh['over_cite_rate'])}; "
                 f"GraphRAG mean preds {_fmt(g_beh['mean_pred'])} vs baseline {_fmt(b_beh['mean_pred'])}.")
    # best/worst gap for graphrag
    if g_gap:
        best = max((k for k in g_gap if k != "negative"), key=lambda k: g_gap[k]["f1_khoan"])
        worst = min((k for k in g_gap if k != "negative"), key=lambda k: g_gap[k]["f1_khoan"])
        L.append(f"- **Per-gap**: strongest = {gap_label.get(best, best)} "
                 f"(F1 {_fmt(g_gap[best]['f1_khoan'])}); weakest = {gap_label.get(worst, worst)} "
                 f"(F1 {_fmt(g_gap[worst]['f1_khoan'])}).")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Expanded evaluation analysis ($0, offline)")
    ap.add_argument("--graphrag", type=Path, help="results_graphrag_*.json (mặc định: latest N=26)")
    ap.add_argument("--baseline", type=Path, help="results_baseline_*.json (mặc định: latest N=26)")
    ap.add_argument("--out", type=Path, help="Ghi report Markdown (mặc định: in stdout)")
    args = ap.parse_args()

    g_path = args.graphrag or _latest("graphrag")
    b_path = args.baseline or _latest("baseline")
    if not g_path or not b_path:
        print("❌ Không tìm thấy cặp results JSON N=26 (graphrag + baseline).")
        return 2
    print(f"GraphRAG: {g_path.name}\nBaseline: {b_path.name}\n")

    meta = _canonical_meta()
    g_meta, g_res = _load(g_path, meta)
    b_meta, b_res = _load(b_path, meta)
    report = build_report(g_meta, g_res, b_meta, b_res)

    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"✅ Đã ghi {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
